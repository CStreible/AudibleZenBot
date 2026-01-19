"""
Minimal emote renderer used by tests. This implementation focuses on the
behaviour required by the unit tests: positional emote replacement from the
Twitch manager, name-based lookups via Twitch and BTTV/FFZ managers, and
emitting a structured `emotes_rendered_ext` signal.

This intentionally keeps the implementation small and defensive so tests
can reliably import and exercise `render_message` without network access.
"""
import html
import re
import time
from typing import Optional
from core.logger import get_logger

logger = get_logger('Emotes')


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

        # lazy imports to avoid import cycles in tests
        try:
            from core.twitch_emotes import get_manager as get_twitch_manager
        except Exception:
            get_twitch_manager = None
        try:
            from core.bttv_ffz import get_manager as get_bttvffz_manager
        except Exception:
            get_bttvffz_manager = None

        t_mgr = get_twitch_manager() if get_twitch_manager is not None else None
        b_mgr = get_bttvffz_manager() if get_bttvffz_manager is not None else None

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
                out_parts.append(html.escape(message[last:s]))

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
                        nm = t_mgr.get_emote_id_by_name(emote_text, broadcaster_id=broadcaster_id)
                        if nm:
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
                out_parts.append(html.escape(message[s:e+1]))

            last = e + 1

        if last < len(message):
            out_parts.append(html.escape(message[last:]))

        interim_html = ''.join(out_parts)

        # Replace remaining tokens in non-<img> parts using BTTV/FFZ then Twitch name lookup
        parts = re.split(r'(<img[^>]*>)', interim_html)
        for i, part in enumerate(parts):
            if part.startswith('<img'):
                continue

            def repl_token(m):
                token = m.group(0)
                # Try BTTV/FFZ first
                try:
                    if b_mgr:
                        uri = b_mgr.get_emote_data_uri_by_name(token, broadcaster_id=broadcaster_id)
                        if uri:
                            return f'<img src="{uri}" alt="{html.escape(token)}" />'
                except Exception:
                    pass
                try:
                    if t_mgr:
                        uri = t_mgr.get_emote_data_uri_by_name(token, broadcaster_id=broadcaster_id)
                        if uri:
                            return f'<img src="{uri}" alt="{html.escape(token)}" />'
                except Exception:
                    pass
                return token

            parts[i] = re.sub(r'(\S+)', repl_token, part)

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
