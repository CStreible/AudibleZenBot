"""
BTTV and FFZ emote manager.

Provides minimal fetching of global and channel emotes for BetterTTV (BTTV)
and FrankerFaceZ (FFZ). Caches emote metadata and assets under
`resources/emotes` and exposes a simple lookup by name returning a
data URI suitable for embedding in HTML.

This implementation is intentionally small and resilient — failures are
logged and do not raise.
"""
from typing import Optional, Dict
import os
import json
import time
import base64
from core.http_session import make_retry_session
from core.logger import get_logger
import hashlib

logger = get_logger('BTTV_FFZ')


def _log_data_uri(source: str, key: str, broadcaster_id: Optional[str], data_uri: Optional[str]):
    try:
        import time as _t
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        out = os.path.join(log_dir, 'emote_data_uri.log')
        snippet = None
        length = 0
        if data_uri:
            length = len(data_uri)
            snippet = data_uri[:400]
        with open(out, 'a', encoding='utf-8', errors='replace') as f:
            f.write(f"{_t.time():.3f} SOURCE={source} key={repr(key)} broadcaster={repr(broadcaster_id)} len={length} snippet={repr(snippet)}\n")
    except Exception:
        try:
            logger.debug('failed to write emote data uri log')
        except Exception:
            pass


class BTTVFFZManager:
    def __init__(self):
        self.session = make_retry_session()
        self.cache_dir = os.path.join('resources', 'emotes')
        os.makedirs(self.cache_dir, exist_ok=True)

        # name -> { 'url': ..., 'id': ..., 'source': 'bttv'|'ffz' }
        self.name_map: Dict[str, Dict] = {}
        self._last_global_fetch = 0

    def fetch_bttv_global(self):
        try:
            if time.time() - self._last_global_fetch < 60 * 60:
                return
            url = 'https://api.betterttv.net/3/cached/emotes/global'
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json() or []
                for e in data:
                    name = e.get('code')
                    if not name:
                        continue
                    src = e.get('imageType') or ''
                    url_template = e.get('url') or e.get('images', {}).get('url')
                    # BTTV provides id; construct CDN URL
                    eid = e.get('id')
                    url_final = f'https://cdn.betterttv.net/emote/{eid}/3x' if eid else url_template
                    self.name_map[name] = {'url': url_final, 'id': eid, 'source': 'bttv'}
            self._last_global_fetch = time.time()
        except Exception as e:
            logger.debug(f'fetch_bttv_global failed: {e}')

    def fetch_bttv_channel(self, broadcaster_id: str):
        try:
            if not broadcaster_id:
                return
            url = f'https://api.betterttv.net/3/cached/users/twitch/{broadcaster_id}'
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json() or {}
                emotes = data.get('channelEmotes', []) + data.get('sharedEmotes', [])
                for e in emotes:
                    name = e.get('code')
                    eid = e.get('id')
                    if not name:
                        continue
                    url_final = f'https://cdn.betterttv.net/emote/{eid}/3x'
                    self.name_map[name] = {'url': url_final, 'id': eid, 'source': 'bttv'}
        except Exception as e:
            logger.debug(f'fetch_bttv_channel failed: {e}')

    def fetch_ffz_global(self):
        try:
            # FFZ global emotes can be retrieved from the 'sets' endpoint
            url = 'https://api.frankerfacez.com/v1/set/global'
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json() or {}
                sets = data.get('sets', {})
                for sid, sdata in sets.items():
                    emoticons = sdata.get('emoticons', [])
                    for e in emoticons:
                        name = e.get('name')
                        urls = e.get('urls') or {}
                        if not name:
                            continue
                        # pick highest available scale
                        url_final = None
                        if '4' in urls:
                            url_final = 'https:' + urls['4']
                        elif '2' in urls:
                            url_final = 'https:' + urls['2']
                        elif '1' in urls:
                            url_final = 'https:' + urls['1']
                        if url_final:
                            self.name_map[name] = {'url': url_final, 'id': e.get('id'), 'source': 'ffz'}
        except Exception as e:
            logger.debug(f'fetch_ffz_global failed: {e}')

    def fetch_ffz_channel(self, broadcaster_id: str):
        try:
            if not broadcaster_id:
                return
            url = f'https://api.frankerfacez.com/v1/room/id/{broadcaster_id}'
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json() or {}
                sets = data.get('sets', {})
                for sid, sdata in sets.items():
                    emoticons = sdata.get('emoticons', [])
                    for e in emoticons:
                        name = e.get('name')
                        urls = e.get('urls') or {}
                        if not name:
                            continue
                        url_final = None
                        if '4' in urls:
                            url_final = 'https:' + urls['4']
                        elif '2' in urls:
                            url_final = 'https:' + urls['2']
                        elif '1' in urls:
                            url_final = 'https:' + urls['1']
                        if url_final:
                            self.name_map[name] = {'url': url_final, 'id': e.get('id'), 'source': 'ffz'}
        except Exception as e:
            logger.debug(f'fetch_ffz_channel failed: {e}')

    def ensure_channel(self, broadcaster_id: Optional[str] = None):
        # Always fetch globals once
        try:
            self.fetch_bttv_global()
            self.fetch_ffz_global()
            if broadcaster_id:
                self.fetch_bttv_channel(broadcaster_id)
                self.fetch_ffz_channel(broadcaster_id)
        except Exception:
            pass

    def get_emote_data_uri_by_name(self, name: str, broadcaster_id: Optional[str] = None, use_disk_cache: bool = True) -> Optional[str]:
        try:
            # Ensure we have some candidate maps
            self.ensure_channel(broadcaster_id)
            info = self.name_map.get(name)
            # If not found, perform a short synchronous fetch+retry to reduce race windows
            if not info:
                try:
                    # fetch globals and channel values once more
                    self.fetch_bttv_global()
                    self.fetch_ffz_global()
                    if broadcaster_id:
                        self.fetch_bttv_channel(broadcaster_id)
                        self.fetch_ffz_channel(broadcaster_id)
                    # small grace period for network callbacks
                    time.sleep(0.20)
                    info = self.name_map.get(name)
                except Exception:
                    pass
            if not info:
                return None
            url = info.get('url')
            if not url:
                return None
            ext = 'png'
            if url.lower().endswith('.gif'):
                ext = 'gif'
            src = info.get('source') or 'bttv_ffz'
            # readable sanitized base (keep letters, numbers, dash, underscore, dot)
            base_part = f"{src}_{name}"
            safe_base = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in base_part)
            # truncate to a reasonable length to avoid long filenames
            if len(safe_base) > 50:
                safe_base = safe_base[:50]
            # append a short deterministic hash of the original name to guarantee uniqueness
            h = hashlib.sha1(name.encode('utf-8')).hexdigest()[:8]
            safe_fname = f"{safe_base}_{h}.{ext}"
            fpath = os.path.join(self.cache_dir, safe_fname)

            # If disk caching is disabled, fetch and return a data URI without writing
            if not use_disk_cache:
                try:
                    r = self.session.get(url, timeout=10)
                    if r.status_code == 200 and getattr(r, 'content', None):
                        b = r.content
                        mime = 'image/gif' if url.lower().endswith('.gif') else 'image/png'
                        result = f'data:{mime};base64,' + base64.b64encode(b).decode()
                        _log_data_uri(info.get('source') or 'bttv_ffz', name, broadcaster_id, result)
                        return result
                    else:
                        logger.debug(f'BTTV/FFZ fetch failed for {name}: {getattr(r, "status_code", "ERR")}')
                        return None
                except Exception as e:
                    logger.debug(f'BTTV/FFZ download error for {name}: {e}')
                    return None

            # Disk-cached path (existing behavior)
            if not os.path.exists(fpath) or (time.time() - os.path.getmtime(fpath)) > 60*60*24:
                try:
                    r = self.session.get(url, timeout=10)
                    if r.status_code == 200 and r.content:
                        with open(fpath, 'wb') as wf:
                            wf.write(r.content)
                    else:
                        logger.debug(f'BTTV/FFZ fetch failed for {name}: {getattr(r, "status_code", "ERR")}')
                        return None
                except Exception as e:
                    logger.debug(f'BTTV/FFZ download error for {name}: {e}')
                    return None
            with open(fpath, 'rb') as f:
                b = f.read()
            mime = 'image/gif' if fpath.lower().endswith('.gif') else 'image/png'
            result = f'data:{mime};base64,' + base64.b64encode(b).decode()
            _log_data_uri(info.get('source') or 'bttv_ffz', name, broadcaster_id, result)
            return result
        except Exception as e:
            logger.debug(f'get_emote_data_uri_by_name error: {e}')
            _log_data_uri(info.get('source') or 'bttv_ffz', name, broadcaster_id, None)
            return None


# module-level singleton
_mgr: Optional[BTTVFFZManager] = None


def get_manager() -> BTTVFFZManager:
    global _mgr
    if _mgr is None:
        _mgr = BTTVFFZManager()
    return _mgr
