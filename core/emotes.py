"""
Minimal emote renderer used by tests. This implementation focuses on the
behaviour required by the unit tests: positional emote replacement from the
Twitch manager, name-based lookups via Twitch and BTTV/FFZ managers, and
emitting a structured `emotes_rendered_ext` signal.

This intentionally keeps the implementation small and defensive so tests
can reliably import and exercise `render_message` without network access.
"""
import html
import json
import re
import time
import threading
import os
import base64
import hashlib
from typing import Optional
from core.logger import get_logger

logger = get_logger('Emotes')


# In-memory emote name -> data-uri cache
class InMemoryEmoteMap:
    def __init__(self, t_mgr, broadcaster_id=None):
        self.lock = threading.Lock()
        self.map = {}  # name -> data-uri/info
        self.pattern = None
        self.t_mgr = t_mgr
        self.broadcaster_id = broadcaster_id

    def rebuild(self):
        with self.lock:
            entries = {}
            # Prefer Twitch names first. Use the manager's `name_map` keys
            # exactly as provided by the API (e.g. '<3', ':)') and resolve
            # to a lightweight info dict containing id/url/source. We avoid
            # fetching binary image data here; images will be fetched and
            # cached on first use to reduce startup network/disk activity.
            try:
                if self.t_mgr is not None:
                    for name, emid in list(getattr(self.t_mgr, 'name_map', {}).items() if getattr(self.t_mgr, 'name_map', None) else []):
                        try:
                            if not emid:
                                continue
                            emobj = getattr(self.t_mgr, 'id_map', {}).get(str(emid)) or {}
                            # Determine best candidate URL without downloading
                            try:
                                url = self.t_mgr._select_image_url(emobj)
                            except Exception:
                                url = None
                            entries[name] = {'id': str(emid), 'url': url, 'source': 'twitch'}
                        except Exception:
                            continue
            except Exception:
                pass

            # BTTV/FFZ support removed — only use Twitch manager entries

            self.map = entries
            # Build regex pattern sorted by length descending
            if self.map:
                names = sorted(list(self.map.keys()), key=lambda x: -len(x))
                escaped = [re.escape(n) for n in names]
                alt = '|'.join(escaped)
                # match when preceded by start or whitespace and followed by end or whitespace
                self.pattern = re.compile(r'(?:((?<=\s)|(?<=^))(' + alt + r')(?=(?:\s)|$))')
            else:
                self.pattern = None

    def replace_tokens(self, text):
        if not self.pattern:
            # No built pattern available — attempt a quick, non-blocking
            # fallback using the current managers' name_map entries so we
            # can match names present in memory without waiting for a
            # warm/rebuild signal.
            try:
                entries = {}
                if self.t_mgr is not None and getattr(self.t_mgr, 'name_map', None):
                    for name, emid in list(getattr(self.t_mgr, 'name_map', {}).items()):
                        try:
                            if not emid:
                                continue
                            entries[name] = {'id': str(emid), 'url': None, 'source': 'twitch'}
                        except Exception:
                            continue
                if self.b_mgr is not None and getattr(self.b_mgr, 'name_map', None):
                    for name, info in list(getattr(self.b_mgr, 'name_map', {}).items()):
                        if name in entries:
                            continue
                        try:
                            if isinstance(info, dict):
                                entries[name] = info
                            else:
                                entries[name] = {'id': None, 'url': info, 'source': 'bttv_ffz'}
                        except Exception:
                            continue
                if not entries:
                    # No manager entries available — try a fast local cache lookup
                    # for tokens that may have been cached previously on disk.
                    try:
                        cache_dir = None
                        if self.t_mgr and hasattr(self.t_mgr, 'cache_dir'):
                            cache_dir = getattr(self.t_mgr, 'cache_dir')
                        if not cache_dir and self.b_mgr and hasattr(self.b_mgr, 'cache_dir'):
                            cache_dir = getattr(self.b_mgr, 'cache_dir')
                        if not cache_dir:
                            cache_dir = os.path.join('resources', 'emotes')

                        def _find_cached_uri(tok):
                            try:
                                safe_tok = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in (tok or ''))
                                if not os.path.isdir(cache_dir):
                                    return None
                                for fname in os.listdir(cache_dir):
                                    if safe_tok and safe_tok in fname:
                                        fpath = os.path.join(cache_dir, fname)
                                        try:
                                            with open(fpath, 'rb') as f:
                                                b = f.read()
                                            mime = 'image/gif' if fpath.lower().endswith('.gif') else 'image/png'
                                            return f'data:{mime};base64,' + base64.b64encode(b).decode()
                                        except Exception:
                                            continue
                                return None
                            except Exception:
                                return None

                        # perform a simple substitution using cached files
                        def _cached_repl(m):
                            # Use the full match and replace the token inside it
                            # so we preserve surrounding whitespace exactly.
                            token = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
                            uri = _find_cached_uri(token)
                            if uri:
                                img = f'<img src="{uri}" alt="{html.escape(token)}" />'
                                return m.group(0).replace(token, img)
                            return m.group(0)

                        # attempt a direct substitution using files in cache_dir
                        try:
                            names = [re.escape(n) for n in []]
                            # reuse the original regex structure but with a generic alt
                            # that will match whatever token pattern the caller used
                            # (we can't build a precise alt without entries), so use
                            # the same boundary logic and a permissive token matcher
                            perm = re.compile(r'(?:((?<=\s)|(?<=^))(\S+?)(?=(?:\s)|$))')
                            return perm.sub(_cached_repl, text)
                        except Exception:
                            logger.debug('emotes: replace_tokens cache fallback failed')
                            return text
                    except Exception:
                        logger.debug('emotes: replace_tokens no pattern and no fallback entries')
                        return text

                names = sorted(list(entries.keys()), key=lambda x: -len(x))
                escaped = [re.escape(n) for n in names]
                alt = '|'.join(escaped)
                temp_pattern = re.compile(r'(?:((?<=\s)|(?<=^))(' + alt + r')(?=(?:\s)|$))')

                def _fallback_repl(m):
                    token = m.group(2)
                    info = entries.get(token)
                    uri = None
                    try:
                        if info:
                            uri = self._ensure_data_uri(token, info)
                    except Exception:
                        uri = None

                    if uri:
                        return m.group(1).replace(token, f'<img src="{uri}" alt="{html.escape(token)}" />')
                    return m.group(0)

                try:
                    return temp_pattern.sub(_fallback_repl, text)
                except Exception:
                    return text
            except Exception:
                logger.debug('emotes: replace_tokens fallback failed')
                return text
        def _repl(m):
            token = m.group(2)
            info = None
            try:
                logger.debug(f'emotes: replace_tokens token="{token}" present={token in self.map}')
            except Exception:
                pass
            try:
                info = self.map.get(token)
            except Exception:
                info = None

            uri = None
            try:
                if info:
                    uri = self._ensure_data_uri(token, info)
            except Exception:
                uri = None
            try:
                logger.debug(f'emotes: replace_tokens token="{token}" uri_present={bool(uri)}')
            except Exception:
                pass

            if uri:
                return m.group(1).replace(token, f'<img src="{uri}" alt="{html.escape(token)}" />')
            return m.group(0)

        return self.pattern.sub(_repl, text)

    def _ensure_data_uri(self, name, info):
        """Return a data URI for emote `name` using info dict.
        If a disk-cached image exists return it; otherwise fetch from
        the `url`, save to the emote cache, and return its data URI.
        """
        if not info:
            return None
        url = info.get('url')
        source = info.get('source') or 'unknown'
        eid = info.get('id')

        # determine cache dir
        cache_dir = None
        try:
            if self.t_mgr and hasattr(self.t_mgr, 'cache_dir'):
                cache_dir = getattr(self.t_mgr, 'cache_dir')
        except Exception:
            cache_dir = None
        if not cache_dir:
            try:
                if self.b_mgr and hasattr(self.b_mgr, 'cache_dir'):
                    cache_dir = getattr(self.b_mgr, 'cache_dir')
            except Exception:
                cache_dir = None
        if not cache_dir:
            cache_dir = os.path.join('resources', 'emotes')

        # BTTV/FFZ support removed — only Twitch images handled here

        # Twitch: compute same sanitized filename as Twitch manager and fetch+cache
        try:
            if not url and self.t_mgr and eid:
                try:
                    emobj = getattr(self.t_mgr, 'id_map', {}).get(str(eid)) or {}
                    url = self.t_mgr._select_image_url(emobj)
                except Exception:
                    url = None
        except Exception:
            url = url

        if not url:
            return None

        ext = 'gif' if url.lower().endswith('.gif') else 'png'

        # build sanitized filename consistent with Twitch's naming
        try:
            base_part = f"twitch_{eid}_{name}" if name else f"twitch_{eid}"
            safe_base = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in base_part)
            if len(safe_base) > 50:
                safe_base = safe_base[:50]
            h = hashlib.sha1((name or str(eid)).encode('utf-8')).hexdigest()[:8]
            safe_fname = f"{safe_base}_{h}.{ext}"
            fpath = os.path.join(cache_dir, safe_fname)
        except Exception:
            fpath = None

        try:
            logger.debug(f'emotes: _ensure_data_uri name={name!r} source={source!r} url={url!r} cache_dir={cache_dir!r} fpath={fpath!r}')
        except Exception:
            pass

        # If file exists, read and return data URI
        try:
            if fpath and os.path.exists(fpath):
                with open(fpath, 'rb') as f:
                    b = f.read()
                mime = 'image/gif' if fpath.lower().endswith('.gif') else 'image/png'
                return f'data:{mime};base64,' + base64.b64encode(b).decode()
        except Exception:
            pass

        # Otherwise fetch from network and save to disk
        try:
            # Prefer manager's request helper when available
            if self.t_mgr and hasattr(self.t_mgr, '_request_with_backoff'):
                r = self.t_mgr._request_with_backoff(url, timeout=10)
                status = getattr(r, 'status_code', None)
                if status == 200 and getattr(r, 'content', None):
                    b = r.content
                    try:
                        if fpath:
                            with open(fpath, 'wb') as wf:
                                wf.write(b)
                    except Exception:
                        pass
                    mime = 'image/gif' if url.lower().endswith('.gif') else 'image/png'
                    return f'data:{mime};base64,' + base64.b64encode(b).decode()
        except Exception:
            pass

        return None


# Module-level singleton emote map rebuilt only on warm/image-cached signals
_global_emap = None

def _get_global_emap(t_mgr, broadcaster_id=None):
    global _global_emap
    try:
        if _global_emap is None:
            _global_emap = InMemoryEmoteMap(t_mgr, broadcaster_id=broadcaster_id)
            try:
                _global_emap.rebuild()
            except Exception:
                pass
            # Attempt to hook signals so rebuild occurs only on warms/caches
            try:
                from core.signals import signals as emote_signals
                def _on_warm(*a, **k):
                    try:
                        _global_emap.rebuild()
                    except Exception:
                        pass

                try:
                    emote_signals.emotes_global_warmed_ext.connect(_on_warm)
                except Exception:
                    pass
                try:
                    emote_signals.emotes_channel_warmed_ext.connect(_on_warm)
                except Exception:
                    pass
                try:
                    emote_signals.emote_image_cached_ext.connect(_on_warm)
                except Exception:
                    pass
            except Exception:
                pass
        else:
            # If caller requests a different broadcaster_id, update and rebuild
            try:
                if broadcaster_id and _global_emap.broadcaster_id != broadcaster_id:
                    _global_emap.broadcaster_id = broadcaster_id
                    try:
                        _global_emap.rebuild()
                    except Exception:
                        pass
            except Exception:
                pass

        return _global_emap
    except Exception:
        return None


def render_message(message: str, emotes_tag, metadata: Optional[dict] = None):
    """Render `message` into HTML and replace known emotes with <img> tags.

    Returns (final_html: str, has_img: bool).
    - Supports Twitch positional `emotes_tag` (dict or string) for id-based
      replacement.
    - Falls back to manager name lookups via `get_emote_data_uri_by_name`.
    - Emits `core.signals.signals.emotes_rendered_ext` payload (best-effort).
    """
    try:
        if not message:
            return '', False

        # If EventSub provided structured fragments in metadata, prefer
        # rendering from fragments. This allows precise emote/mention
        # rendering and lets us fetch/cache emote assets on demand.
        try:
            frags = None
            if metadata and isinstance(metadata, dict):
                frags = metadata.get('fragments') or metadata.get('message_fragments')
            if frags and isinstance(frags, list):
                from core.twitch_emotes import get_manager as _get_twitch_manager
                mgr = _get_twitch_manager() if _get_twitch_manager is not None else None

                parts = []
                has_img = False
                broadcaster_id = None
                try:
                    broadcaster_id = metadata.get('room-id') or metadata.get('room_id') or metadata.get('channel_id')
                except Exception:
                    broadcaster_id = None

                for frag in frags:
                    try:
                        ftype = frag.get('type') if isinstance(frag, dict) else None
                        # Warn about unknown fragment types to aid diagnosis
                        try:
                            if ftype and ftype not in ('text', 'emote', 'cheermote'):
                                try:
                                    logger.warning(f"emotes: unknown fragment type: {ftype} fragment={json.dumps(frag, default=str)}")
                                except Exception:
                                    logger.warning(f"emotes: unknown fragment type: {ftype}")
                        except Exception:
                            pass
                        if not ftype or ftype == 'text':
                            parts.append(html.escape((frag.get('text') if isinstance(frag, dict) else str(frag)) or ''))
                            continue

                        if ftype == 'emote':
                            # Emote fragment handling: try cache, then fetch emote set
                            emobj = frag.get('emote') if isinstance(frag, dict) else {}
                            # Emote id may be under several keys
                            emote_id = None
                            try:
                                emote_id = str(emobj.get('id') or emobj.get('emote_id') or frag.get('id')) if isinstance(emobj, dict) else None
                            except Exception:
                                emote_id = None

                            emote_set = None
                            try:
                                emote_set = emobj.get('emote_set_id') or emobj.get('emote_set') or emobj.get('emote_set_ids')
                            except Exception:
                                emote_set = None

                            uri = None
                            try:
                                if mgr and emote_id:
                                    uri = mgr.get_emote_data_uri(emote_id, broadcaster_id=broadcaster_id)
                            except Exception:
                                uri = None

                            # If not found and emote_set present, synchronously fetch set and prefetch images
                            if not uri and emote_set and str(emote_set) not in ('', '0'):
                                try:
                                    # Ensure manager has data for the set
                                    mgr.fetch_emote_sets([emote_set])
                                except Exception:
                                    pass
                                try:
                                    # Collect ids that belong to this set and prefetch their images
                                    ids = []
                                    try:
                                        for k, v in (mgr.id_map.items() if getattr(mgr, 'id_map', None) else []):
                                            try:
                                                # normalize possible fields
                                                s = v.get('emote_set_id') or v.get('emote_set') or v.get('emote_set_ids')
                                                if not s:
                                                    continue
                                                # s can be list or string
                                                if isinstance(s, (list, tuple)):
                                                    if str(emote_set) in [str(x) for x in s]:
                                                        ids.append(k)
                                                else:
                                                    if str(s) == str(emote_set):
                                                        ids.append(k)
                                            except Exception:
                                                continue
                                    except Exception:
                                        ids = []
                                    if ids:
                                        try:
                                            mgr._prefetch_emote_images(ids)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                                # Retry locating the emote image after prefetch
                                try:
                                    if mgr and emote_id:
                                        uri = mgr.get_emote_data_uri(emote_id, broadcaster_id=broadcaster_id)
                                except Exception:
                                    uri = None

                            if uri:
                                has_img = True
                                parts.append(f'<img src="{uri}" alt="{html.escape(frag.get("text") or "emote")}" />')
                            else:
                                # Fallback: use emote text
                                try:
                                    logger.warning(f"emotes: could not resolve emote id={emote_id} set={emote_set}; falling back to text")
                                except Exception:
                                    pass
                                parts.append(html.escape(frag.get('text') or ''))
                            continue

                        # Other fragment types (mention, cheermote) - fallback to text for now
                        parts.append(html.escape((frag.get('text') if isinstance(frag, dict) else str(frag)) or ''))
                    except Exception:
                        try:
                            parts.append(html.escape(str(frag)))
                        except Exception:
                            parts.append('')

                return (''.join(parts), bool(has_img))
        except Exception:
            # If fragments rendering fails for any reason, fall back to legacy rendering
            pass
        # lazy imports to avoid import cycles in tests
        try:
            from core.twitch_emotes import get_manager as get_twitch_manager
        except Exception:
            get_twitch_manager = None

        t_mgr = get_twitch_manager() if get_twitch_manager is not None else None

        broadcaster_id = None
        if metadata and isinstance(metadata, dict):
            broadcaster_id = metadata.get('room-id') or metadata.get('room_id') or metadata.get('channel_id')

        # Parse positions from emotes_tag -> list of (s, e, id_or_token)
        positions = []
        if emotes_tag:
            try:
                if isinstance(emotes_tag, dict):
                    for eid, ranges in emotes_tag.items():
                        for r in (ranges or []):
                            if not r or '-' not in r:
                                continue
                            s, e = r.split('-', 1)
                            positions.append((int(s), int(e), str(eid)))
                elif isinstance(emotes_tag, str):
                    for part in emotes_tag.split('/'):
                        if not part:
                            continue
                        if ':' in part:
                            eid, rngs = part.split(':', 1)
                            for r in rngs.split(','):
                                if not r or '-' not in r:
                                    continue
                                s, e = r.split('-', 1)
                                positions.append((int(s), int(e), str(eid)))
                        else:
                            for r in part.split(','):
                                if not r or '-' not in r:
                                    continue
                                s, e = r.split('-', 1)
                                positions.append((int(s), int(e), part))
            except Exception:
                positions = []

        positions.sort(key=lambda x: x[0])

        out_parts = []
        last = 0

        for s, e, eid in positions:
            if s < last or s >= len(message):
                continue
            if e < s:
                continue
            if s > last:
                # Append raw text here; escape will be applied after
                # in-memory emote replacement so tokens like "<3" can
                # be matched against manager names.
                out_parts.append(message[last:s])

            emote_html = None
            # numeric id
            try:
                int_eid = int(eid)
            except Exception:
                int_eid = None

            if int_eid is not None:
                try:
                    if t_mgr:
                        data_uri = t_mgr.get_emote_data_uri(str(int_eid), broadcaster_id=broadcaster_id)
                    else:
                        data_uri = None
                    if data_uri:
                        emote_html = f'<img src="{data_uri}" alt="emote" />'
                except Exception:
                    emote_html = None
            else:
                # token-based or name fallback
                emote_text = message[s:e+1]
                found_id = None
                try:
                    if eid.startswith('emotesv2_') and t_mgr and eid in getattr(t_mgr, 'id_map', {}):
                        found_id = eid
                except Exception:
                    found_id = None

                if not found_id and t_mgr:
                    try:
                        # Avoid blocking synchronous network prefetches during
                        # render. Prefer a fast lookup from the manager's
                        # `name_map`. If the name isn't present, schedule a
                        # background channel/global prefetch and continue —
                        # the in-memory emote map will rebuild when warming
                        # completes via signals.
                        nm = None
                        try:
                            nm = t_mgr.name_map.get(emote_text) if getattr(t_mgr, 'name_map', None) else None
                        except Exception:
                            nm = None

                        if not nm:
                            try:
                                # schedule background warm; non-blocking
                                if broadcaster_id:
                                    try:
                                        t_mgr.prefetch_channel(str(broadcaster_id), background=True)
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        t_mgr.prefetch_global(background=True)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        else:
                            found_id = nm
                    except Exception:
                        pass

                if found_id and t_mgr:
                    try:
                        uri = t_mgr.get_emote_data_uri(str(found_id), broadcaster_id=broadcaster_id)
                        if uri:
                            emote_html = f'<img src="{uri}" alt="{html.escape(emote_text)}" />'
                    except Exception:
                        pass

            if emote_html:
                out_parts.append(emote_html)
            else:
                # Append raw token; will be escaped later if not replaced
                out_parts.append(message[s:e+1])

            last = e + 1

        if last < len(message):
            # Append raw trailing text so the in-memory replacements can
            # match tokens like "<3" before any escaping is applied.
            out_parts.append(message[last:])

        interim_html = ''.join(out_parts)

        # Replace remaining tokens in non-<img> parts using an in-memory emote map.
        # We operate on raw text so emoticon names like "<3" match the keys
        # in the managers. After replacement we escape any non-<img> text to
        # ensure safety.
        parts = re.split(r'(<img[^>]*>)', interim_html)

        # Build or reuse module-level in-memory map (rebuild only on warm signals)
        try:
            emap = _get_global_emap(t_mgr, broadcaster_id=broadcaster_id)
        except Exception:
            emap = None

        # Ensure the in-memory map reflects current managers/broadcaster now
        try:
            if emap is not None:
                try:
                    emap.rebuild()
                except Exception:
                    pass
        except Exception:
            pass

        for i, part in enumerate(parts):
            if part.startswith('<img'):
                # already safe HTML for an emote
                continue
            # Apply in-memory replacements on raw text
            try:
                if emap is not None:
                    replaced = emap.replace_tokens(part)
                else:
                    replaced = part
            except Exception:
                replaced = part

            # Now escape any text except the inserted <img> tags.
            try:
                subparts = re.split(r'(<img[^>]*>)', replaced)
                for j, sp in enumerate(subparts):
                    if sp.startswith('<img'):
                        continue
                    subparts[j] = html.escape(sp)
                parts[i] = ''.join(subparts)
            except Exception:
                parts[i] = html.escape(replaced)

        final_html = ''.join(parts)
        has_img = '<img' in final_html

        # Emit signal (best-effort)
        try:
            from core.signals import signals as emote_signals
            if hasattr(emote_signals, 'emotes_rendered_ext'):
                payload = {
                    'timestamp': int(time.time()),
                    'message_id': (metadata.get('message_id') if metadata and isinstance(metadata, dict) else None),
                    'has_img': has_img,
                    'len_html': len(final_html),
                }
                try:
                    emote_signals.emotes_rendered_ext.emit(payload)
                except Exception:
                    pass
        except Exception:
            pass

        return final_html, has_img

    except Exception:
        try:
            logger.debug('render_message unexpected error')
        except Exception:
            pass
        return html.escape(message), ('<img' in html.escape(message))
