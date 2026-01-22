"""
Minimal Twitch emote manager used for prefetching in tests.

This implementation is intentionally small and resilient so unit tests
can run without requiring the full application stack.
"""
from typing import Optional, Dict, Set
import os
import time
import threading
import base64

try:
    from PyQt6.QtCore import QObject, QThread, pyqtSlot
except Exception:
    # Tests stub PyQt6.QtCore; if not available provide lightweight fallbacks
    class QObject:
        pass

    class QThread:
        def __init__(self):
            self.started = type('S', (), {'connect': lambda self, cb: None})()
            self.finished = type('S', (), {'connect': lambda self, cb: None})()

        def start(self):
            return None

    def pyqtSlot(*args, **kwargs):
        def _d(f):
            return f

        return _d

import core.http_session as http_session
try:
    try:
        logger = get_logger('twitch_emotes')
        logger.debug(f"import-time: core.http_session={repr(http_session)} factory={getattr(http_session, 'make_retry_session', None)}")
    except Exception:
        pass
except Exception:
    pass
try:
    from core.signals import signals as emote_signals
except Exception:
    emote_signals = None
from core.logger import get_logger
import traceback
import random
import json
import hashlib
import queue


class PrefetchError(Exception):
    """Exception raised for prefetch-specific failures with a standardized code."""
    def __init__(self, code: str, message: str = ''):
        super().__init__(message or code)
        self.code = code
        self.message = message or code

class TwitchEmoteManager:
    def __init__(self, config=None):
        self.config = config
        # Create session lazily to allow tests to swap `core.http_session`
        # before the first network call (improves test isolation).
        self.session = None
        # Track which http_session factory produced `session` so tests can
        # replace `core.http_session` and force a new manager when needed.
        self._session_factory = None
        # Backoff base seconds (small default to keep tests fast)
        self._backoff_base = 0.05
        # configurable max retries (can be overridden via config)
        try:
            # support ConfigManager-like objects with .get
            if self.config and hasattr(self.config, 'get'):
                self._max_retries = int(self.config.get('twitch.prefetch.max_retries', 3) or 3)
                self._backoff_base = float(self.config.get('twitch.prefetch.backoff_base', self._backoff_base) or self._backoff_base)
            else:
                self._max_retries = 3
        except Exception:
            self._max_retries = 3
        # Throttler queue for emote_set requests (optional)
        self._emote_set_queue = queue.Queue()
        self._throttler_thread = None
        self._throttler_stop = threading.Event()
        # Event used to wake the throttler worker immediately when new
        # batches are enqueued so requests are processed promptly.
        self._throttler_wakeup = threading.Event()
        self._batch_interval = float(self.config.get('twitch.prefetch.batch_interval', 0.05) if (self.config and hasattr(self.config, 'get')) else 0.05)
        # Batch size for emote_set requests (tunable)
        self._emote_set_batch_size = 25
        self.id_map: Dict[str, dict] = {}
        self.name_map: Dict[str, str] = {}
        self._warmed_global = False
        self._warmed_channels: Set[str] = set()
        self._prefetch_threads = []
        self.cache_dir = os.path.join('resources', 'emotes')
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception:
            pass
        # Track last fetch times to avoid repeated warming; default to 0
        self._last_global_fetch = 0
        self._last_channel_fetch = {}
        # Ensure the background emote-set throttler is running by default so
        # UI calls that schedule set fetches enqueue into a live worker.
        try:
            self.start_emote_set_throttler()
        except Exception:
            pass

    def _headers(self):
        # Build minimal headers. Prefer explicit environment variables so
        # test runs can override without touching persistent config. If
        # not present, attempt to read stored platform config for Twitch.
        try:
            # Prefer environment overrides
            cid = os.environ.get('TWITCH_CLIENT_ID') or os.environ.get('TWITCH_CLIENTID') or os.environ.get('AUDIBLEZENBOT_TWITCH_CLIENT_ID')
            token = os.environ.get('TWITCH_OAUTH_TOKEN') or os.environ.get('TWITCH_TOKEN') or os.environ.get('AUDIBLEZENBOT_TWITCH_OAUTH')
            headers = {}
            if cid:
                headers['Client-ID'] = cid
            if token:
                headers['Authorization'] = f'Bearer {token}'
            if headers:
                return headers

            # Fallback: try reading from persisted config if available
            try:
                from core.config import ConfigManager
                cfg = ConfigManager()
                p = cfg.get_platform_config('twitch') or {}
                cid = cid or p.get('client_id') or p.get('clientid')
                # Try common token keys used across the app
                token = token or p.get('oauth_token') or p.get('bot_token') or p.get('access_token')
                if cid:
                    headers['Client-ID'] = cid
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                return headers
            except Exception:
                return {}
        except Exception:
            return {}

    def _request_with_backoff(self, url: str, params=None, timeout: int = 10, max_retries: int = 3):
        attempt = 0
        base = getattr(self, '_backoff_base', 0.05)
        # allow overriding via parameter; default to configured value
        max_attempts = int(max_retries or getattr(self, '_max_retries', 3))
        while True:
            try:
                sess = self._get_session()
                try:
                    logger = get_logger('twitch_emotes')
                    logger.debug(f"_request_with_backoff: using http_session module={repr(http_session)} factory={getattr(http_session, 'make_retry_session', None)} session={repr(sess)} url={url}")
                except Exception:
                    pass
                r = sess.get(url, headers=self._headers(), params=params, timeout=timeout)
            except Exception as e:
                # record attempts so callers can include attempts in payloads
                try:
                    self._last_request_attempts = attempt + 1
                except Exception:
                    pass
                try:
                    logger = get_logger('twitch_emotes')
                    logger.debug(f"Request to {url} failed on attempt {attempt + 1}: {e}")
                except Exception:
                    pass
                raise PrefetchError('network', 'Network error during request') from e

            status = getattr(r, 'status_code', None)
            if status == 429:
                if attempt < max_attempts:
                    # exponential backoff with jitter (+/-30%)
                    jitter = random.uniform(-0.3, 0.3)
                    sleep_for = base * (2 ** attempt) * (1.0 + jitter)
                    try:
                        time.sleep(max(0, sleep_for))
                    except Exception:
                        pass
                    attempt += 1
                    # record attempts so callers can inspect the retry count
                    try:
                        self._last_request_attempts = attempt + 0
                    except Exception:
                        pass
                    continue
                else:
                    try:
                        self._last_request_attempts = attempt + 1
                    except Exception:
                        pass
                    raise PrefetchError('rate_limited', 'HTTP 429')
            # record successful attempts
            try:
                self._last_request_attempts = attempt + 1
            except Exception:
                pass

            try:
                logger = get_logger('twitch_emotes')
                logger.debug(f"_request_with_backoff: received response status={getattr(r, 'status_code', None)} for url={url}")
            except Exception:
                pass

            return r

    def _get_session(self):
        """Return an active HTTP session, creating it from the current
        `core.http_session.make_retry_session()` factory if needed.

        Creating the session lazily allows tests to replace the `core.http_session`
        module (via `sys.modules` or direct assignment) before the first
        network call; this reduces flakiness when tests run in parallel.
        """
        # Always construct a fresh session from the current factory so tests
        # that swap `core.http_session` are guaranteed to be used. Creating
        # per-request sessions is acceptable for the test harness and avoids
        # stale session objects carrying over between tests.
        # If a test or caller has explicitly set `self.session`, prefer it
        # (this is used by integration tests which inject a stubbed session).
        try:
            if getattr(self, 'session', None) is not None:
                return self.session

            # Resolve the `core.http_session` module dynamically from sys.modules
            # so tests that replace `sys.modules['core.http_session']` are
            # observed even if the import-time binding didn't pick up the
            # replacement.
            import sys as _sys
            current_http = _sys.modules.get('core.http_session', http_session)
            factory = getattr(current_http, 'make_retry_session', None)
            sess = factory() if callable(factory) else None
            # remember the factory for detection in get_manager()
            self._session_factory = factory
            if sess is not None:
                return sess
        except Exception:
            pass

        # Fallback to a plain requests.Session per-call if no factory present
        try:
            import requests

            return requests.Session()
        except Exception:
            return None

    def fetch_global_emotes(self) -> None:
        # Throttle global fetches to at most once per hour
        try:
            if time.time() - getattr(self, '_last_global_fetch', 0) < 60 * 60:
                return
        except Exception:
            pass

        url = 'https://api.twitch.tv/helix/chat/emotes/global'
        try:
            r = self._request_with_backoff(url, timeout=10)
            status = getattr(r, 'status_code', None)
            if status == 200:
                data = r.json().get('data', [])
                for e in data:
                    try:
                        emid = e.get('id')
                        if emid:
                            # Cache by id only
                            self.id_map[str(emid)] = e
                            try:
                                logger = get_logger('twitch_emotes')
                                logger.debug(f"fetch_global_emotes: caching emote id={emid} name={e.get('name')}")
                            except Exception:
                                pass
                    except Exception:
                        continue
                # Prefetch representative images for globals
                try:
                    ids = [e.get('id') for e in data if e.get('id')]
                    try:
                        self._prefetch_emote_images(ids)
                    except PrefetchError:
                        # propagate to caller
                        raise
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    self._last_global_fetch = int(time.time())
                except Exception:
                    pass
            else:
                if status == 429:
                    raise PrefetchError('rate_limited', 'HTTP 429')
                raise PrefetchError(f'http_{status}', f'HTTP {status}')
        except PrefetchError:
            raise
        except Exception as e:
            raise PrefetchError('network', 'Network error during fetch_global_emotes') from e

    def fetch_emote_sets(self, emote_set_ids) -> None:
        if not emote_set_ids:
            return
        if isinstance(emote_set_ids, (str, int)):
            emote_set_ids = [str(emote_set_ids)]
        # Default behavior: batch and call immediately
        try:
            # Per Twitch Helix API: use the chat/emotes/set endpoint for emote sets
            url = 'https://api.twitch.tv/helix/chat/emotes/set'
            batch_size = int(getattr(self, '_emote_set_batch_size', 25) or 25)
            # ensure list of strings
            sids = [str(s) for s in emote_set_ids]
            for i in range(0, len(sids), batch_size):
                batch = sids[i:i+batch_size]
                params = [('emote_set_id', sid) for sid in batch]
                try:
                    logger = get_logger('twitch_emotes')
                    logger.debug(f"fetch_emote_sets: requesting emote_set_ids={batch} params={params} url={url}")
                except Exception:
                    pass
                r = self._request_with_backoff(url, params=params, timeout=10)
                status = getattr(r, 'status_code', None)
                try:
                    logger = get_logger('twitch_emotes')
                    logger.debug(f"fetch_emote_sets: received status={status} for emote_set_ids={batch}")
                except Exception:
                    pass
                if status == 200:
                    try:
                        js = r.json() if hasattr(r, 'json') else {}
                        # Log receipt of the emote-set response and how many entries
                        try:
                            logger = get_logger('twitch_emotes')
                            data = js.get('data', []) if isinstance(js, dict) else []
                            logger.info(f"fetch_emote_sets: received response for emote_set_ids={batch} count={len(data)}")
                        except Exception:
                            data = js.get('data', []) if isinstance(js, dict) else []
                        if not isinstance(data, (list, tuple)):
                            try:
                                logger = get_logger('twitch_emotes')
                                logger.debug(f"fetch_emote_sets: unexpected data format for emote_set_ids={batch}: {type(data)}")
                            except Exception:
                                pass
                            data = []
                    except Exception:
                        data = []
                    ids_to_prefetch = []
                    for e in data:
                        try:
                            emid = e.get('id')
                            if emid:
                                # Cache emote by id only
                                self.id_map[str(emid)] = e
                                ids_to_prefetch.append(str(emid))
                        except Exception:
                            continue
                    # Commit emote images to disk cache for this set (best-effort)
                    try:
                        if ids_to_prefetch:
                            try:
                                self._prefetch_emote_images(ids_to_prefetch)
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    if status == 429:
                        raise PrefetchError('rate_limited', 'HTTP 429')
                    raise PrefetchError(f'http_{status}', f'HTTP {status}')
        except PrefetchError:
            raise
        except Exception as e:
            raise PrefetchError('network', 'Network error during fetch_emote_sets') from e

    def start_emote_set_throttler(self):
        """Start the background worker that processes enqueued emote_set batches."""
        if self._throttler_thread and self._throttler_thread.is_alive():
            return

        self._throttler_stop.clear()

        def _worker():
            # Wrap the worker loop in robust exception handling so an unexpected
            # error in a thread doesn't crash the whole interpreter. We log and
            # emit a structured signal where possible, then either continue or
            # exit gracefully depending on the error.
            while not self._throttler_stop.is_set():
                try:
                    batch = None
                    try:
                        batch = self._emote_set_queue.get(timeout=0.1)
                    except Exception:
                        batch = None

                    if not batch:
                        continue
                    try:
                        logger = get_logger('twitch_emotes')
                        try:
                            qsize = self._emote_set_queue.qsize()
                        except Exception:
                            qsize = None
                        logger.debug(f"throttler: dequeued batch={batch} qsize={qsize}")
                    except Exception:
                        pass

                    # Try to combine multiple queued batches into one request up to batch size
                    try:
                        raw_items = list(batch)
                        try:
                            while len(raw_items) < int(getattr(self, '_emote_set_batch_size', 25)):
                                try:
                                    more = self._emote_set_queue.get_nowait()
                                except Exception:
                                    break
                                if more:
                                    raw_items.extend(more)
                        except Exception:
                            pass

                        # Normalize raw_items into a list of set ids and a mapping
                        # of set_id -> interested emote ids (may be empty lists).
                        combined = []
                        interest_map = {}
                        try:
                            for it in raw_items:
                                # support items that are either simple set_id strings
                                # or tuples/lists of (set_id, [interested_emote_ids])
                                if isinstance(it, (list, tuple)) and len(it) >= 1:
                                    sid = str(it[0])
                                    interested = []
                                    if len(it) >= 2 and isinstance(it[1], (list, tuple)):
                                        interested = [str(x) for x in it[1] if x]
                                else:
                                    sid = str(it)
                                    interested = []
                                if sid not in combined:
                                    combined.append(sid)
                                if interested:
                                    interest_map.setdefault(sid, []).extend(interested)
                        except Exception:
                            combined = [str(x) for x in raw_items]
                            interest_map = {}

                        # Retry with exponential backoff on transient failures and emit structured logs
                        max_attempts = int(getattr(self, '_max_retries', 3) or 3)
                        attempt = 0
                        base = float(getattr(self, '_backoff_base', 0.05) or 0.05)
                        start_ts = time.time()
                    except Exception:
                        # If combining failed, skip this batch iteration
                        continue

                    last_err = None
                    while attempt <= max_attempts and not self._throttler_stop.is_set():
                        try:
                            # Fetch all emote sets in this combined batch
                            # Snapshot existing id_map keys so we can detect
                            # which emote ids were populated by this fetch.
                            try:
                                before_keys = set(self.id_map.keys())
                            except Exception:
                                before_keys = set()
                            self.fetch_emote_sets(combined)
                            last_err = None
                            try:
                                new_keys = sorted(list(set(self.id_map.keys()) - before_keys))
                            except Exception:
                                new_keys = []
                            # Emit a lightweight metadata-ready signal so the UI
                            # can patch placeholders immediately from cache
                            try:
                                if new_keys and emote_signals is not None and hasattr(emote_signals, 'emote_set_metadata_ready_ext'):
                                    try:
                                        try:
                                            logger = get_logger('twitch_emotes')
                                            logger.debug(f"emote metadata ready: sets={combined} emote_ids={new_keys}")
                                        except Exception:
                                            pass
                                        payload_meta = {'timestamp': int(time.time()), 'set_ids': combined, 'emote_ids': new_keys}
                                        # Emit-side diagnostic for UI log correlation
                                        try:
                                            import os, time, json
                                            dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                            os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                            with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                                df.write(f"{time.time():.3f} META_EMIT payload={json.dumps(payload_meta)}\n")
                                                try:
                                                    df.flush(); os.fsync(df.fileno())
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                        emote_signals.emote_set_metadata_ready_ext.emit(payload_meta)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            # After successful fetch, if callers registered
                            # interest in specific emote ids for particular
                            # sets, ensure those specific emotes are cached
                            try:
                                if interest_map:
                                    for sid, wanted in interest_map.items():
                                        try:
                                            # For each wanted emote id, if metadata
                                            # now exists in id_map, ensure the image
                                            # is cached (idempotent).
                                            to_prefetch = [w for w in wanted if str(w) in self.id_map]
                                            if to_prefetch:
                                                try:
                                                    self._prefetch_emote_images(to_prefetch)
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                            break
                        except Exception as e:
                            last_err = e
                            code = getattr(e, 'code', None)
                            is_rate = code in ('rate_limited', 'network')
                            if is_rate and attempt < max_attempts:
                                jitter = random.uniform(-0.3, 0.3)
                                sleep_for = base * (2 ** attempt) * (1.0 + jitter)
                                try:
                                    time.sleep(max(0, sleep_for))
                                except Exception:
                                    pass
                                attempt += 1
                                continue
                            else:
                                try:
                                    logger = get_logger('twitch_emotes')
                                    logger.warning(f"Emote set batch failed after {attempt} attempts: {code}")
                                except Exception:
                                    pass
                                break
                    end_ts = time.time()
                    duration_ms = int((end_ts - start_ts) * 1000)
                    # Structured payload for throttler activity
                    try:
                        logger = get_logger('twitch_emotes')
                        payload = {
                            'status': 'ok' if last_err is None else 'error',
                            'source': 'emote_set_throttler',
                            'timestamp': int(time.time()),
                            'duration_ms': duration_ms,
                            'emote_set_count': len(combined),
                            'attempts': int(getattr(self, '_last_request_attempts', attempt + 1) or (attempt + 1)),
                            'cache_dir': self.cache_dir,
                        }
                        if last_err is not None:
                            try:
                                payload.update({'error': str(last_err), 'error_code': getattr(last_err, 'code', None), 'traceback': traceback.format_exc()})
                            except Exception:
                                payload.update({'error': str(last_err)})
                        if last_err is None:
                            logger.info(f"[twitch_emotes][INFO] Emote set batch processed: {payload}")
                        else:
                            logger.warning(f"[twitch_emotes][WARN] Emote set batch failed: {payload}")
                    except Exception:
                        pass
                    # Emit structured throttler signal if available
                    try:
                        if emote_signals is not None and hasattr(emote_signals, 'emote_set_batch_processed_ext'):
                            try:
                                emote_signals.emote_set_batch_processed_ext.emit(payload)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    finally:
                        try:
                            # Wait up to `_batch_interval`, but allow external
                            # callers to wake the worker immediately by setting
                            # `_throttler_wakeup` (set by `schedule_emote_set_fetch`).
                            try:
                                self._throttler_wakeup.wait(self._batch_interval)
                            except Exception:
                                time.sleep(self._batch_interval)
                        except Exception:
                            pass
                        try:
                            # Clear wake flag so subsequent waits will block
                            # until the next explicit wake or timeout.
                            self._throttler_wakeup.clear()
                        except Exception:
                            pass
                except Exception as e:
                    # Log unexpected exceptions, emit a best-effort signal and
                    # sleep briefly before continuing to avoid tight failure loops.
                    try:
                        logger = get_logger('twitch_emotes')
                        logger.exception(f"Uncaught exception in emote throttler worker: {e}")
                    except Exception:
                        pass
                    try:
                        if emote_signals is not None and hasattr(emote_signals, 'emote_set_batch_processed_ext'):
                            try:
                                emote_signals.emote_set_batch_processed_ext.emit({'status': 'error', 'error': str(e), 'source': 'emote_set_throttler'})
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        # Back off briefly to avoid hot loops on persistent errors
                        time.sleep(0.2)
                    except Exception:
                        pass
                    # If the stop flag is set, break out to allow clean shutdown
                    if self._throttler_stop.is_set():
                        break
            # Worker ending — clear thread reference for clean restart
            try:
                self._throttler_thread = None
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        self._throttler_thread = t
        t.start()

    def stop_emote_set_throttler(self, timeout: float = 1.0):
        try:
            self._throttler_stop.set()
            if self._throttler_thread and self._throttler_thread.is_alive():
                try:
                    self._throttler_thread.join(timeout)
                except Exception:
                    pass
        except Exception:
            pass

    def schedule_emote_set_fetch(self, emote_set_ids):
        """Enqueue emote_set_ids (list or single) to be fetched by the throttler."""
        # Preserve tuple/list items (e.g., (set_id, [interested_ids])) so
        # interest mappings survive through to the throttler worker. Only
        # coerce simple scalar inputs into a single-item list.
        if isinstance(emote_set_ids, (str, int)):
            emote_set_items = [str(emote_set_ids)]
        else:
            emote_set_items = list(emote_set_ids or [])
        if not emote_set_items:
            return False
        # start throttler lazily
        try:
            self.start_emote_set_throttler()
        except Exception:
            pass

        # If a throttler worker is running, enqueue batches so it processes them.
        # If no worker is active (common in simple test runs), perform an
        # immediate fetch so callers can observe `id_map` populated synchronously.
        try:
            th = getattr(self, '_throttler_thread', None)
            is_worker_alive = False
            try:
                is_worker_alive = bool(th and getattr(th, 'is_alive', lambda: False)())
            except Exception:
                is_worker_alive = False

            if is_worker_alive:
                batch_size = int(getattr(self, '_emote_set_batch_size', 25) or 25)
                for i in range(0, len(emote_set_items), batch_size):
                    batch = emote_set_items[i:i+batch_size]
                    try:
                        self._emote_set_queue.put(batch)
                    except Exception:
                        try:
                            get_logger('twitch_emotes').warning(f"schedule_emote_set_fetch: failed to enqueue batch={batch}")
                        except Exception:
                            pass
                    try:
                        logger = get_logger('twitch_emotes')
                        try:
                            qsize = self._emote_set_queue.qsize()
                        except Exception:
                            qsize = None
                        logger.debug(f"schedule_emote_set_fetch: enqueued batches for emote_set_ids={emote_set_items} qsize={qsize}")
                    except Exception:
                        pass
                    # Wake the throttler worker immediately so the queued
                    # batches are processed without waiting for the next
                    # timeout or an additional enqueue.
                    try:
                        self._throttler_wakeup.set()
                    except Exception:
                        pass
                return True
            else:
                # No active worker; perform immediate fetch (non-throttled)
                try:
                    # Normalize possible (set_id, [interested_emote_ids]) items
                    interest_map_immediate = {}
                    try:
                        normalized = []
                        for it in emote_set_items:
                            if isinstance(it, (list, tuple)) and len(it) >= 1:
                                sid = str(it[0])
                                normalized.append(sid)
                                if len(it) >= 2 and isinstance(it[1], (list, tuple)):
                                    interest_map_immediate[sid] = [str(x) for x in it[1] if x]
                            else:
                                normalized.append(str(it))
                    except Exception:
                        normalized = [str(x) for x in emote_set_ids]

                    try:
                        # Snapshot existing id_map keys so we can detect which
                        # emote ids were populated by this fetch for immediate
                        # notification to the UI.
                        try:
                            before_keys = set(self.id_map.keys())
                        except Exception:
                            before_keys = set()
                    except Exception:
                        before_keys = set()

                    self.fetch_emote_sets(normalized)

                    try:
                        try:
                            new_keys = sorted(list(set(self.id_map.keys()) - before_keys))
                        except Exception:
                            new_keys = []
                        logger = get_logger('twitch_emotes')
                        logger.debug(f"schedule_emote_set_fetch: immediate fetch for emote_set_ids={emote_set_ids} completed")
                    except Exception:
                        pass

                    # Emit metadata-ready payload for immediate path
                    try:
                        if new_keys and emote_signals is not None and hasattr(emote_signals, 'emote_set_metadata_ready_ext'):
                            try:
                                try:
                                    logger = get_logger('twitch_emotes')
                                    logger.debug(f"emote metadata ready (immediate): sets={normalized} emote_ids={new_keys}")
                                except Exception:
                                    pass
                                payload_meta = {'timestamp': int(time.time()), 'set_ids': normalized, 'emote_ids': new_keys}
                                # Emit-side diagnostic for UI log correlation
                                try:
                                    import os, time, json
                                    dlog = os.path.join(os.getcwd(), 'logs', 'chat_page_dom.log')
                                    os.makedirs(os.path.dirname(dlog), exist_ok=True)
                                    with open(dlog, 'a', encoding='utf-8', errors='replace') as df:
                                        df.write(f"{time.time():.3f} META_EMIT payload={json.dumps(payload_meta)}\n")
                                        try:
                                            df.flush(); os.fsync(df.fileno())
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                emote_signals.emote_set_metadata_ready_ext.emit(payload_meta)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # After immediate fetch, prefetch any interested emotes if their
                    # metadata was populated by the fetch_emote_sets call.
                    try:
                        if interest_map_immediate:
                            for sid, wanted in interest_map_immediate.items():
                                try:
                                    to_prefetch = [w for w in wanted if str(w) in self.id_map]
                                    if to_prefetch:
                                        try:
                                            self._prefetch_emote_images(to_prefetch)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # Emit a best-effort structured payload similar to throttler
                    try:
                        payload = {
                            'status': 'ok',
                            'source': 'emote_set_throttler',
                            'timestamp': int(time.time()),
                            'duration_ms': 0,
                            'emote_set_count': len(emote_set_items),
                            'attempts': int(getattr(self, '_last_request_attempts', 1) or 1),
                            'cache_dir': self.cache_dir,
                        }
                        if emote_signals is not None and hasattr(emote_signals, 'emote_set_batch_processed_ext'):
                            try:
                                emote_signals.emote_set_batch_processed_ext.emit(payload)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return True
                except Exception:
                    try:
                        # Emit error payload if available
                        payload = {
                            'status': 'error',
                            'source': 'emote_set_throttler',
                            'timestamp': int(time.time()),
                            'emote_set_count': len(emote_set_items),
                            'error': str(Exception),
                        }
                        if emote_signals is not None and hasattr(emote_signals, 'emote_set_batch_processed_ext'):
                            try:
                                emote_signals.emote_set_batch_processed_ext.emit(payload)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return False
        except Exception:
            return False

    def fetch_channel_emotes(self, broadcaster_id: str) -> None:
        if not broadcaster_id:
            return
        bid = str(broadcaster_id)
        # Throttle per-channel fetches to at most once per hour
        try:
            last = int(self._last_channel_fetch.get(bid, 0) or 0)
            if time.time() - last < 60 * 60:
                return
        except Exception:
            pass
        url = 'https://api.twitch.tv/helix/chat/emotes'
        params = {'broadcaster_id': broadcaster_id}
        try:
            r = self._request_with_backoff(url, params=params, timeout=10)
            status = getattr(r, 'status_code', None)
            if status == 200:
                data = r.json().get('data', [])
                emote_set_ids = set()
                for e in data:
                    try:
                        emid = e.get('id')
                        if emid:
                            self.id_map[str(emid)] = e
                        sid = e.get('emote_set_id') or e.get('emote_set') or e.get('emote_set_ids')
                        if sid:
                            if isinstance(sid, (list, tuple)):
                                for s in sid:
                                    if s:
                                        emote_set_ids.add(str(s))
                            else:
                                # handle comma-separated strings sometimes returned by APIs
                                if isinstance(sid, str) and ',' in sid:
                                    for part in sid.split(','):
                                        p = part.strip()
                                        if p:
                                            emote_set_ids.add(str(p))
                                else:
                                    emote_set_ids.add(str(sid))
                    except Exception:
                        continue
                # record last emote_set_count for richer payloads
                try:
                    self._last_emote_set_count = len(emote_set_ids)
                except Exception:
                    self._last_emote_set_count = 0

                if emote_set_ids:
                    try:
                        # Enqueue emote_set fetches to the global throttler so
                        # concurrent channel prefetches don't burst requests.
                        scheduled = self.schedule_emote_set_fetch(list(emote_set_ids))
                        if not scheduled:
                            # fallback to immediate fetch if scheduling failed
                            self.fetch_emote_sets(list(emote_set_ids))
                    except PrefetchError:
                        # propagate prefetch errors from immediate fallback
                        raise
                    except Exception:
                        # Swallow scheduling/fetch errors to keep warming robust
                        pass

                for e in data:
                    try:
                        emid = e.get('id')
                        if emid:
                            self.id_map[str(emid)] = e
                            try:
                                logger = get_logger('twitch_emotes')
                                logger.debug(f"fetch_channel_emotes: caching emote id={emid} name={e.get('name')} channel={bid}")
                            except Exception:
                                pass
                    except Exception:
                        continue
                # Prefetch representative images for channel emotes
                try:
                    ids = [e.get('id') for e in data if e.get('id')]
                    try:
                        self._prefetch_emote_images(ids)
                    except PrefetchError:
                        raise
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                if status == 429:
                    raise PrefetchError('rate_limited', 'HTTP 429')
                raise PrefetchError(f'http_{status}', f'HTTP {status}')
        except PrefetchError:
            raise
        except Exception:
            raise PrefetchError('network', 'Network error during fetch_channel_emotes')

        # end of fetch_channel_emotes
        try:
            # record last successful channel fetch time
            try:
                self._last_channel_fetch[bid] = int(time.time())
            except Exception:
                pass
        except Exception:
            pass

    def dump_channel_emotes(self, broadcaster_id: str) -> Optional[str]:
        """Fetch (best-effort) channel emotes and write a pretty JSON dump.

        Returns the path to the written file or None on failure.
        This is a best-effort helper used by CLI tooling and debugging.
        """
        if not broadcaster_id:
            return None
        bid = str(broadcaster_id)
        # Try to populate recent channel emote state but don't fail if network is unavailable
        try:
            try:
                self.fetch_channel_emotes(bid)
            except Exception:
                # swallow fetch errors; we'll still dump whatever we have
                pass
        except Exception:
            pass

        out_dir = os.path.join('logs')
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass
        out_path = os.path.join(out_dir, f'twitch_channel_emotes_dump_{bid}.json')

        try:
            # Limit size to a reasonable sample to avoid huge dumps
            id_map_sample = {}
            try:
                for k, v in list(self.id_map.items())[:200]:
                    try:
                        id_map_sample[k] = v
                    except Exception:
                        id_map_sample[k] = None
            except Exception:
                id_map_sample = {}

            dump = {
                'timestamp': int(time.time()),
                'broadcaster_id': bid,
                'id_map': id_map_sample,
                'name_map': dict(getattr(self, 'name_map', {}) or {}),
            }
            with open(out_path, 'w', encoding='utf-8') as wf:
                json.dump(dump, wf, indent=2, ensure_ascii=False)
            return out_path
        except Exception:
            return None

    def _select_image_url(self, emobj: dict) -> Optional[str]:
        # Determine best image URL for an emote object
        if not emobj:
            return None
        imgs = emobj.get('images') or {}
        if isinstance(imgs, dict):
            for key in ('url_1x', 'url_2x', 'url_4x', '1x', '2x', '4x'):
                v = imgs.get(key)
                if v:
                    return v
        for k in ('url', 'image_url', 'thumbnail_url'):
            v = emobj.get(k)
            if v and isinstance(v, str):
                return v
        emid = emobj.get('id')
        if emid:
            return f'https://static-cdn.jtvnw.net/emoticons/v2/{emid}/default/dark/1.0'
        return None

    def _prefetch_emote_images(self, emote_ids):
        if not emote_ids:
            return None
        subset = list(emote_ids)[:50]
        for eid in subset:
            emobj = self.id_map.get(str(eid))
            try:
                logger = get_logger('twitch_emotes')
            except Exception:
                logger = None

            if not emobj:
                try:
                    if logger:
                        logger.debug(f"_prefetch_emote_images: skipping emote {eid}: not in id_map")
                except Exception:
                    pass
                # No metadata for this emote id; nothing else we can do here
                # without additional context (emote_set id). UI or callers should
                # schedule `fetch_emote_sets` with the correct set ids when
                # available so the throttler can populate `id_map` and images.
                continue

            url = self._select_image_url(emobj)
            if not url:
                try:
                    if logger:
                        logger.debug(f"_prefetch_emote_images: no URL for emote {eid} (emobj keys={list(emobj.keys())})")
                except Exception:
                    pass
                continue
            ext = 'png'
            if url.lower().endswith('.gif'):
                ext = 'gif'
            # Use stable cache filename based only on platform and emote id
            safe_fname = f"twitch_{eid}.{ext}"
            fpath = os.path.join(self.cache_dir, safe_fname)
            try:
                if os.path.exists(fpath) and (time.time() - os.path.getmtime(fpath)) < 60*60*24:
                    try:
                        if logger:
                            logger.debug(f"_prefetch_emote_images: skipping cached recent file for emote {eid} path={fpath}")
                    except Exception:
                        pass
                    continue
            except Exception:
                pass
            try:
                try:
                    if logger:
                        logger.debug(f"_prefetch_emote_images: fetching emote {eid} url={url} fpath={fpath}")
                except Exception:
                    pass
                r = self._request_with_backoff(url, timeout=10)
                status = getattr(r, 'status_code', None)
                if status == 200 and getattr(r, 'content', None):
                    try:
                        # Always write prefetch images to disk (prefetch path)
                        with open(fpath, 'wb') as wf:
                            wf.write(r.content)
                        # Log to emote_cache.log the cached file (platform, emote id, filename)
                        try:
                            log_dir = os.path.join(os.getcwd(), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            cache_log = os.path.join(log_dir, 'emote_cache.log')
                            abs_path = os.path.abspath(fpath)
                            with open(cache_log, 'a', encoding='utf-8', errors='replace') as clf:
                                clf.write(f"{int(time.time())},twitch,{eid},{abs_path}\n")
                        except Exception:
                            pass
                        # Emit structured signal that an image was cached
                        try:
                            if logger:
                                try:
                                    size = os.path.getsize(fpath) if os.path.exists(fpath) else None
                                except Exception:
                                    size = None
                                logger.info(f"_prefetch_emote_images: cached emote {eid} -> {fpath} size={size}")
                        except Exception:
                            pass

                        try:
                            if emote_signals is not None and hasattr(emote_signals, 'emote_image_cached_ext'):
                                payload = {
                                    'timestamp': int(time.time()),
                                    'emote_id': str(eid),
                                    'path': fpath,
                                    'size': os.path.getsize(fpath) if os.path.exists(fpath) else None,
                                    'mime': 'image/gif' if fpath.lower().endswith('.gif') else 'image/png',
                                }
                                try:
                                    emote_signals.emote_image_cached_ext.emit(payload)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        # diagnostics removed: temporary per-cache META_CACHE_EMIT emissions
                    except Exception:
                        pass
                else:
                    try:
                        try:
                            if logger:
                                logger.debug(f"_prefetch_emote_images: fetch response for emote {eid} status={status}")
                        except Exception:
                            pass
                        if status == 429:
                            raise PrefetchError('rate_limited', 'HTTP 429 while fetching emote image')
                        raise PrefetchError(f'http_{status}', f'HTTP {status} while fetching emote image')
                    except PrefetchError:
                        raise
                    except Exception:
                        raise PrefetchError('network', 'Unknown error while fetching emote image')
            except PrefetchError:
                raise
            except Exception as e:
                raise PrefetchError('network', 'Network error while fetching emote image') from e
        return None

    # NOTE: CDN direct-download fallback removed intentionally. Emotes must be
    # resolved via the Get Emote Set API so caller-provided set fetches will
    # populate `id_map` and allow `_prefetch_emote_images` to cache images.

    def prefetch_emote_by_id(self, emote_id, background: bool = True, emote_set_ids=None):
        """Public helper to prefetch a single emote by id. Returns thread or None.

        Optional `emote_set_ids` lets callers (UI) provide the emote-set ids
        associated with the emote so the manager can schedule proper set
        fetches. This avoids treating an emote id as an emote_set_id.
        """
        if not emote_id:
            return None
        eid = str(emote_id)
        try:
            logger = get_logger('twitch_emotes')
        except Exception:
            logger = None

        # If the emote isn't known, prefer resolving it via its emote-set(s)
        # when the caller provided `emote_set_ids`. Only perform a short
        # channel/global warm when no set ids are available.
        try:
            if eid not in self.id_map:
                try:
                    if emote_set_ids:
                        if logger:
                            logger.debug(f"prefetch_emote_by_id: emote {eid} not in id_map; deferring to emote_set_ids={emote_set_ids}")
                    else:
                        if logger:
                            logger.debug(f"prefetch_emote_by_id: emote {eid} not in id_map; attempting channel/global warm as fallback")
                        try:
                            self.prefetch_global(background=False)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # If caller provided emote_set_ids (preferred), register interest by
        # providing (set_id, [emote_id]) tuples so the throttler can prefetch
        # the specific emote image after the Set metadata is fetched.
        try:
            if emote_set_ids:
                try:
                    if logger:
                        logger.debug(f"prefetch_emote_by_id: scheduling emote_set_fetch for {emote_set_ids} (caller-provided) with interest={eid}")
                except Exception:
                    pass
                try:
                    # Normalize to tuple form so `schedule_emote_set_fetch` and
                    # the throttler retain the mapping of set -> interested ids.
                    items = []
                    if isinstance(emote_set_ids, (str, int)):
                        items = [(str(emote_set_ids), [eid])]
                    else:
                        for s in emote_set_ids:
                            try:
                                items.append((str(s), [eid]))
                            except Exception:
                                continue
                    self.schedule_emote_set_fetch(items)
                except Exception:
                    pass
        except Exception:
            pass

        def _work():
            try:
                # Best-effort: try to cache the emote if metadata is already
                # present in `id_map`. Do NOT attempt direct CDN downloads.
                self._prefetch_emote_images([eid])
            except Exception:
                try:
                    if logger:
                        logger.exception(f"prefetch_emote_by_id: failed for {eid}")
                except Exception:
                    pass

        if background:
            t = threading.Thread(target=_work, daemon=True)
            t.start()
            self._prefetch_threads.append(t)
            return t
        else:
            _work()
            return None

    def get_emote_data_uri(self, emote_id, broadcaster_id=None) -> Optional[str]:
        eid = str(emote_id)
        emobj = self.id_map.get(eid) or {}
        url = self._select_image_url(emobj)
        if not url:
            return None
        ext = 'png'
        if url.lower().endswith('.gif'):
            ext = 'gif'
        # Use stable cache filename based only on platform and emote id
        safe_fname = f"twitch_{eid}.{ext}"
        fpath = os.path.join(self.cache_dir, safe_fname)

        # If the file exists, read and return it
        try:
            if os.path.exists(fpath):
                with open(fpath, 'rb') as f:
                    b = f.read()
                mime = 'image/gif' if fpath.lower().endswith('.gif') else 'image/png'
                return f'data:{mime};base64,' + base64.b64encode(b).decode()
        except Exception:
            pass

        # Fallback: fetch from network and return data URI without forcing a disk write
        try:
            r = self._request_with_backoff(url, timeout=10)
            status = getattr(r, 'status_code', None)
            if status == 200 and getattr(r, 'content', None):
                b = r.content
                mime = 'image/gif' if url.lower().endswith('.gif') else 'image/png'
                return f'data:{mime};base64,' + base64.b64encode(b).decode()
            else:
                if status == 429:
                    raise PrefetchError('rate_limited', 'HTTP 429 while fetching emote data')
                raise PrefetchError(f'http_{status}', f'HTTP {status} while fetching emote data')
        except Exception:
            return None

    def get_emote_id_by_name(self, name: str, broadcaster_id: Optional[str] = None) -> Optional[str]:
        """Return the emote id for a given emote name if known.

        Best-effort: will attempt a synchronous channel/global prefetch when
        a broadcaster_id is provided and the name is not already cached.
        """
        try:
            if not name:
                return None
            # Quick hit from existing map
            eid = self.name_map.get(name)
            if eid:
                return str(eid)

            # Try to warm channel/global lists synchronously to reduce races
            try:
                if broadcaster_id:
                    # perform a blocking prefetch for the channel
                    self.prefetch_channel(str(broadcaster_id), background=False)
                else:
                    # attempt a global prefetch as a last resort
                    self.prefetch_global(background=False)
                # small grace window for cache writes
                time.sleep(0.05)
            except Exception:
                pass

            eid = self.name_map.get(name)
            if eid:
                return str(eid)
            return None
        except Exception:
            return None

    def get_emote_data_uri_by_name(self, name: str, broadcaster_id: Optional[str] = None) -> Optional[str]:
        """Return a data URI for an emote by its name (best-effort)."""
        try:
            eid = self.get_emote_id_by_name(name, broadcaster_id=broadcaster_id)
            if not eid:
                return None
            return self.get_emote_data_uri(str(eid), broadcaster_id=broadcaster_id)
        except Exception:
            return None

    def prefetch_global(self, background: bool = True):
        def _work():
            err = None
            err_code = None
            tb = None
            start_ts = time.time()
            try:
                self.fetch_global_emotes()
            except PrefetchError as e:
                err = str(e.message if hasattr(e, 'message') else e)
                err_code = getattr(e, 'code', None)
                try:
                    tb = traceback.format_exc()
                except Exception:
                    tb = None
            except Exception as e:
                err = str(e)
                err_code = 'exception'
                try:
                    tb = traceback.format_exc()
                except Exception:
                    tb = None
            finally:
                end_ts = time.time()
                duration_ms = int((end_ts - start_ts) * 1000)
                try:
                    if not err:
                        self._warmed_global = True
                except Exception:
                    pass

                try:
                    logger = get_logger('twitch_emotes')
                    payload_log = {
                        'status': 'ok' if not err else 'error',
                        'source': 'global',
                        'timestamp': int(time.time()),
                        'duration_ms': duration_ms,
                        'emote_count': len(self.id_map),
                        'cache_dir': self.cache_dir,
                        'attempts': int(getattr(self, '_last_request_attempts', 1) or 1),
                    }
                    if err:
                        payload_log.update({'error': err, 'error_code': err_code})

                    if not err:
                        logger.info(f"[twitch_emotes][INFO] Global emotes warmed: {payload_log}")
                    else:
                        logger.warning(f"[twitch_emotes][WARN] Global emotes warm failed: {payload_log}")
                except Exception:
                    pass

                try:
                    if emote_signals is not None:
                        try:
                            try:
                                if not err:
                                    emote_signals.emotes_global_warmed.emit()
                            except Exception:
                                pass

                            payload = {
                                'status': 'ok' if not err else 'error',
                                'timestamp': int(time.time()),
                                'source': 'global',
                                'duration_ms': duration_ms,
                                'emote_count': len(self.id_map),
                                'cache_dir': self.cache_dir,
                                'attempts': int(getattr(self, '_last_request_attempts', 1) or 1),
                            }
                            if err:
                                payload.update({'error': err, 'error_code': err_code, 'traceback': tb})

                            if hasattr(emote_signals, 'emotes_global_warmed_ext'):
                                try:
                                    emote_signals.emotes_global_warmed_ext.emit(payload)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass

        if background:
            t = threading.Thread(target=_work, daemon=True)
            t.start()
            self._prefetch_threads.append(t)
            return t
        else:
            _work()
            return None

    def prefetch_channel(self, broadcaster_id: str, background: bool = True):
        if not broadcaster_id:
            return None
        bid = str(broadcaster_id)

        def _work():
            err = None
            err_code = None
            tb = None
            start_ts = time.time()
            try:
                try:
                    self.fetch_channel_emotes(bid)
                except PrefetchError as e:
                    err = str(e.message if hasattr(e, 'message') else e)
                    err_code = getattr(e, 'code', None)
                    try:
                        tb = traceback.format_exc()
                    except Exception:
                        tb = None
                except Exception as e:
                    err = str(e)
                    err_code = 'exception'
                    try:
                        tb = traceback.format_exc()
                    except Exception:
                        tb = None
            finally:
                end_ts = time.time()
                duration_ms = int((end_ts - start_ts) * 1000)

                try:
                    if not err:
                        self._warmed_channels.add(bid)
                except Exception:
                    pass

                try:
                    logger = get_logger('twitch_emotes')
                    payload_log = {
                        'status': 'ok' if not err else 'error',
                        'source': 'channel',
                        'broadcaster_id': bid,
                        'timestamp': int(time.time()),
                        'duration_ms': duration_ms,
                        'emote_count': len(self.id_map),
                        'emote_set_count': getattr(self, '_last_emote_set_count', 0),
                        'cache_dir': self.cache_dir,
                        'attempts': int(getattr(self, '_last_request_attempts', 1) or 1),
                    }
                    if err:
                        payload_log.update({'error': err, 'error_code': err_code})

                    if not err:
                        logger.info(f"[twitch_emotes][INFO] Channel emotes warmed: {payload_log}")
                    else:
                        logger.warning(f"[twitch_emotes][WARN] Channel emotes warm failed for {bid}: {payload_log}")
                except Exception:
                    pass

                try:
                    if emote_signals is not None:
                        try:
                            try:
                                if not err:
                                    emote_signals.emotes_channel_warmed.emit(bid)
                            except Exception:
                                pass

                            payload = {
                                'status': 'ok' if not err else 'error',
                                'timestamp': int(time.time()),
                                'broadcaster_id': bid,
                                'emote_count': len(self.id_map),
                            }
                            if err:
                                payload.update({'error': err, 'error_code': err_code, 'traceback': tb})

                            if hasattr(emote_signals, 'emotes_channel_warmed_ext'):
                                try:
                                    emote_signals.emotes_channel_warmed_ext.emit(payload)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass

        if background:
            t = threading.Thread(target=_work, daemon=True)
            t.start()
            self._prefetch_threads.append(t)
            return t
        else:
            _work()
            return None

    def shutdown(self, timeout: float = 1.0):
        """Attempt to cleanly stop any background prefetch workers.

        This method will try to quit QThreads (if present) and join
        regular threading.Thread objects. It is best-effort and
        intentionally tolerant of missing APIs so tests and headless
        environments remain robust.
        """
        try:
            self._shutting_down = True
        except Exception:
            pass

        threads = list(getattr(self, '_prefetch_threads', []) or [])
        for t in threads:
            try:
                # Prefer PyQt QThread-style shutdown if available
                if hasattr(t, 'quit') and callable(getattr(t, 'quit')):
                    try:
                        t.quit()
                    except Exception:
                        pass
                if hasattr(t, 'wait') and callable(getattr(t, 'wait')):
                    try:
                        # QThread.wait takes milliseconds in PyQt
                        try:
                            t.wait(int(timeout * 1000))
                        except TypeError:
                            t.wait()
                    except Exception:
                        pass

                # Fall back to standard threading join
                if isinstance(t, threading.Thread):
                    try:
                        t.join(timeout)
                    except Exception:
                        pass
                elif hasattr(t, 'join') and callable(getattr(t, 'join')):
                    try:
                        t.join(timeout)
                    except Exception:
                        pass
            except Exception:
                continue

        try:
            # Clear references so subsequent runs start fresh
            self._prefetch_threads = []
        except Exception:
            pass



# Module-level singleton
_manager: Optional[TwitchEmoteManager] = None


def get_manager(config: Optional[object] = None) -> TwitchEmoteManager:
    global _manager
    # If an existing manager has running background threads or throttler,
    # prefer creating a fresh instance to avoid cross-test interference
    try:
        if _manager is not None:
            # stop any background work and replace with a fresh manager
            try:
                # stop throttler first
                _manager.stop_emote_set_throttler()
            except Exception:
                pass
            try:
                _manager.shutdown(timeout=0.1)
            except Exception:
                pass
            # If any threads remain alive, discard the singleton so callers get a fresh manager
            alive = False
            try:
                for t in getattr(_manager, '_prefetch_threads', []) or []:
                    try:
                        if isinstance(t, threading.Thread) and t.is_alive():
                            alive = True
                            break
                    except Exception:
                        continue
            except Exception:
                alive = False
            if alive:
                _manager = None

    except Exception:
        _manager = None

    # If the http_session factory was swapped (tests often replace
    # `sys.modules['core.http_session']`), make sure the singleton is
    # recreated so it uses the new factory. Compare the known factory
    # stored on the manager with the current module's factory.
    try:
        if _manager is not None:
            # Resolve current http_session from sys.modules so test-time
            # replacements (tests swapping `sys.modules['core.http_session']`)
            # are detected and cause the singleton to be recreated.
            try:
                import sys as _sys
                current_http = _sys.modules.get('core.http_session', http_session)
                current_factory = getattr(current_http, 'make_retry_session', None)
            except Exception:
                current_factory = getattr(http_session, 'make_retry_session', None)

            known_factory = getattr(_manager, '_session_factory', None)
            if known_factory is not current_factory:
                try:
                    _manager.stop_emote_set_throttler()
                except Exception:
                    pass
                try:
                    _manager.shutdown(timeout=0.1)
                except Exception:
                    pass
                _manager = None
    except Exception:
        _manager = None

    if _manager is None:
        _manager = TwitchEmoteManager(config=config)
        try:
            # Start throttler and trigger a background global prefetch so
            # emotes are warmed early without blocking the main thread/UI.
            try:
                _manager.start_emote_set_throttler()
            except Exception:
                pass
            try:
                _manager.prefetch_global(background=True)
            except Exception:
                pass
        except Exception:
            pass
    return _manager


def reset_manager():
    """Reset the module-level manager used by tests.

    This stops background workers and clears the singleton so subsequent
    calls to `get_manager()` return a fresh instance that will pick up any
    test-time replacements of `core.http_session`.
    """
    global _manager
    try:
        if _manager is not None:
            try:
                _manager.stop_emote_set_throttler()
            except Exception:
                pass
            try:
                _manager.shutdown(timeout=0.1)
            except Exception:
                pass
    except Exception:
        pass
    _manager = None

