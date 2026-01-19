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
    from core.signals import signals as emote_signals
except Exception:
    emote_signals = None
from core.logger import get_logger
import traceback
import random
import json
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

    def _headers(self):
        # Minimal headers; real app may add client-id / auth
        return {}

    def _request_with_backoff(self, url: str, params=None, timeout: int = 10, max_retries: int = 3):
        attempt = 0
        base = getattr(self, '_backoff_base', 0.05)
        # allow overriding via parameter; default to configured value
        max_attempts = int(max_retries or getattr(self, '_max_retries', 3))
        while True:
            try:
                sess = self._get_session()
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

            return r

    def _get_session(self):
        """Return an active HTTP session, creating it from the current
        `core.http_session.make_retry_session()` factory if needed.

        Creating the session lazily allows tests to replace the `core.http_session`
        module (via `sys.modules` or direct assignment) before the first
        network call; this reduces flakiness when tests run in parallel.
        """
        if self.session is None:
            try:
                self.session = http_session.make_retry_session()
            except Exception:
                # Fallback to a plain requests.Session if factory missing
                try:
                    import requests

                    self.session = requests.Session()
                except Exception:
                    self.session = None
        return self.session

    def fetch_global_emotes(self) -> None:
        url = 'https://api.twitch.tv/helix/chat/emotes/global'
        try:
            r = self._request_with_backoff(url, timeout=10)
            status = getattr(r, 'status_code', None)
            if status == 200:
                data = r.json().get('data', [])
                for e in data:
                    emid = e.get('id')
                    if emid:
                        self.id_map[emid] = e
                        name = e.get('name') or e.get('emote_name') or e.get('code')
                        if name:
                            self.name_map[name] = emid
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
            url = 'https://api.twitch.tv/helix/chat/emotes/set'
            batch_size = int(getattr(self, '_emote_set_batch_size', 25) or 25)
            # ensure list of strings
            sids = [str(s) for s in emote_set_ids]
            for i in range(0, len(sids), batch_size):
                batch = sids[i:i+batch_size]
                params = [('emote_set_id', sid) for sid in batch]
                r = self._request_with_backoff(url, params=params, timeout=10)
                status = getattr(r, 'status_code', None)
                if status == 200:
                    try:
                        js = r.json() if hasattr(r, 'json') else {}
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
                    for e in data:
                        try:
                            emid = e.get('id')
                            if emid:
                                self.id_map[str(emid)] = e
                                name = e.get('name') or e.get('emote_name') or e.get('code')
                                if name:
                                    self.name_map[name] = str(emid)
                        except Exception:
                            continue
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
            while not self._throttler_stop.is_set():
                try:
                    batch = self._emote_set_queue.get(timeout=0.1)
                except Exception:
                    batch = None
                if batch:
                    # Try to combine multiple queued batches into one request up to batch size
                    try:
                        combined = list(batch)
                        try:
                            while len(combined) < int(getattr(self, '_emote_set_batch_size', 25)):
                                more = self._emote_set_queue.get_nowait()
                                if more:
                                    combined.extend(more)
                        except Exception:
                            pass

                        # Retry with exponential backoff on transient failures and emit structured logs
                        max_attempts = int(getattr(self, '_max_retries', 3) or 3)
                        attempt = 0
                        base = float(getattr(self, '_backoff_base', 0.05) or 0.05)
                        start_ts = time.time()
                        last_err = None
                        while attempt <= max_attempts and not self._throttler_stop.is_set():
                            try:
                                self.fetch_emote_sets(combined)
                                last_err = None
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
                            time.sleep(self._batch_interval)
                        except Exception:
                            pass
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
        if isinstance(emote_set_ids, (str, int)):
            emote_set_ids = [str(emote_set_ids)]
        else:
            emote_set_ids = [str(s) for s in (emote_set_ids or [])]
        if not emote_set_ids:
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
                for i in range(0, len(emote_set_ids), batch_size):
                    batch = emote_set_ids[i:i+batch_size]
                    self._emote_set_queue.put(batch)
                return True
            else:
                # No active worker; perform immediate fetch (non-throttled)
                try:
                    self.fetch_emote_sets(emote_set_ids)
                    # Emit a best-effort structured payload similar to throttler
                    try:
                        payload = {
                            'status': 'ok',
                            'source': 'emote_set_throttler',
                            'timestamp': int(time.time()),
                            'duration_ms': 0,
                            'emote_set_count': len(emote_set_ids),
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
                            'emote_set_count': len(emote_set_ids),
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
                        name = e.get('name') or e.get('emote_name') or e.get('code')
                        if emid and name:
                            self.name_map[name] = emid
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
            emobj = self.id_map.get(str(eid)) or {}
            url = self._select_image_url(emobj)
            if not url:
                continue
            ext = 'png'
            if url.lower().endswith('.gif'):
                ext = 'gif'
            fname = f'twitch_{eid}.{ext}'
            fpath = os.path.join(self.cache_dir, fname)
            try:
                if os.path.exists(fpath) and (time.time() - os.path.getmtime(fpath)) < 60*60*24:
                    continue
            except Exception:
                pass
            try:
                r = self._request_with_backoff(url, timeout=10)
                status = getattr(r, 'status_code', None)
                if status == 200 and getattr(r, 'content', None):
                    try:
                        with open(fpath, 'wb') as wf:
                            wf.write(r.content)
                        # Emit structured signal that an image was cached
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
                    except Exception:
                        pass
                else:
                    try:
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

    def get_emote_data_uri(self, emote_id, broadcaster_id=None) -> Optional[str]:
        eid = str(emote_id)
        emobj = self.id_map.get(eid) or {}
        url = self._select_image_url(emobj)
        if not url:
            return None
        ext = 'png'
        if url.lower().endswith('.gif'):
            ext = 'gif'
        fname = f'twitch_{eid}.{ext}'
        fpath = os.path.join(self.cache_dir, fname)
        if not os.path.exists(fpath):
            try:
                r = self._request_with_backoff(url, timeout=10)
                status = getattr(r, 'status_code', None)
                if status == 200 and getattr(r, 'content', None):
                    with open(fpath, 'wb') as wf:
                        wf.write(r.content)
                else:
                    if status == 429:
                        raise PrefetchError('rate_limited', 'HTTP 429 while fetching emote data')
                    raise PrefetchError(f'http_{status}', f'HTTP {status} while fetching emote data')
            except Exception:
                return None
        try:
            with open(fpath, 'rb') as f:
                b = f.read()
            mime = 'image/gif' if fpath.lower().endswith('.gif') else 'image/png'
            return f'data:{mime};base64,' + base64.b64encode(b).decode()
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

    if _manager is None:
        _manager = TwitchEmoteManager(config=config)
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

