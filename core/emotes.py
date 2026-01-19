"""
Unified emote renderer used by the chat page and overlay.

This module uses the Twitch emote manager and the BTTV/FFZ manager to
render a message into HTML with <img> tags for known emotes. It mirrors
the behaviour previously implemented in `ChatPage.replace_emotes_with_images`
but is exported as a reusable function for the overlay and other callers.
"""
import os
import html
import base64
import re
from typing import Optional
from core.logger import get_logger

logger = get_logger('Emotes')


def render_message(message: str, emotes_tag, metadata: Optional[dict] = None):
    """Render message text into HTML with emotes replaced by <img> tags.

    Returns a tuple: (final_html: str, has_img: bool)
    - `message`: original message text
    - `emotes_tag`: Twitch emotes tag (str or dict) or None
    - `metadata`: optional metadata (room-id / broadcaster id) used to fetch channel emotes
    """
    try:
        if not message:
            return ''

        # We'll reuse Twitch emote manager when available
        from core.twitch_emotes import get_manager as get_twitch_manager
        from core.bttv_ffz import get_manager as get_bttvffz_manager

        t_mgr = get_twitch_manager()
        b_mgr = get_bttvffz_manager()

        broadcaster_id = None
        if metadata and isinstance(metadata, dict):
            broadcaster_id = metadata.get('room-id') or metadata.get('room_id') or metadata.get('channel_id')

        # First, perform Twitch-positioned emote replacements (if any)
        positions = []
        if emotes_tag:
            if isinstance(emotes_tag, dict):
                for eid, ranges in emotes_tag.items():
                    for r in (ranges or []):
                        if not r:
                            continue
                        if '-' not in r:
                            continue
                        s, e = r.split('-', 1)
                        positions.append((int(s), int(e), str(eid)))
            elif isinstance(emotes_tag, str):
                for part in emotes_tag.split('/'):
                    if not part or ':' not in part:
                        continue
                    eid, rngs = part.split(':', 1)
                    for r in rngs.split(','):
                        if not r or '-' not in r:
                            continue
                        s, e = r.split('-', 1)
                        positions.append((int(s), int(e), str(eid)))

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
            # Numeric emote ids -> twitch
            try:
                int_eid = int(eid)
            except Exception:
                int_eid = None

            if int_eid is not None:
                # Ensure Twitch emote is available (may download/cache synchronously)
                try:
                    data_uri = t_mgr.get_emote_data_uri(str(int_eid), broadcaster_id=broadcaster_id)
                    if data_uri:
                        emote_html = f'<img src="{data_uri}" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                    else:
                        # Fallback to legacy CDN URL if manager couldn't provide data URI
                        emote_html = f'<img src="https://static-cdn.jtvnw.net/emoticons/v2/{int_eid}/default/dark/1.0" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                except Exception:
                    emote_html = f'<img src="https://static-cdn.jtvnw.net/emoticons/v2/{int_eid}/default/dark/1.0" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
            else:
                # emotesv2_<hash> or name-like ids: try to resolve via twitch manager first
                data_uri = None
                if eid.startswith('emotesv2_'):
                    try:
                        hash_part = eid.split('emotesv2_', 1)[1]
                        try:
                            t_mgr.fetch_emote_sets([hash_part])
                        except Exception:
                            pass
                        emote_text = message[s:e+1]
                        found_id = None
                        for mid, emobj in t_mgr.id_map.items():
                            try:
                                name = emobj.get('name') or emobj.get('emote_name') or emobj.get('code')
                                if name == emote_text:
                                    found_id = mid
                                    break
                            except Exception:
                                continue
                        if found_id:
                            data_uri = t_mgr.get_emote_data_uri(str(found_id))
                            if data_uri:
                                emote_html = f'<img src="{data_uri}" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                    except Exception:
                        pass

                # If still not resolved, attempt CDN/local fallbacks (reuse twitch manager cache logic)
                if not emote_html:
                    # Try local file fallback first
                    try:
                        base_dir = os.path.join('resources', 'emotes')
                        emote_text = message[s:e+1]
                        for cname in (eid, emote_text, f'twitch_{emote_text}'):
                            for ext in ('png', 'gif'):
                                candidate = os.path.join(base_dir, f"{cname}.{ext}")
                                if os.path.exists(candidate):
                                    with open(candidate, 'rb') as f:
                                        b = f.read()
                                    mime = 'image/gif' if candidate.lower().endswith('.gif') else 'image/png'
                                    data_uri = f'data:{mime};base64,' + base64.b64encode(b).decode()
                                    emote_html = f'<img src="{data_uri}" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                                    break
                            if emote_html:
                                break
                    except Exception:
                        pass

                # If still not resolved, attempt CDN patterns synchronously (try several known candidates)
                if not emote_html:
                    try:
                        from core.http_session import make_retry_session
                        session = make_retry_session()
                        hash_part = eid
                        if eid.startswith('emotesv2_'):
                            hash_part = eid.split('emotesv2_', 1)[1]
                        candidates = [
                            f'https://static-cdn.jtvnw.net/emoticons/v2/{hash_part}/default/dark/4.0',
                            f'https://static-cdn.jtvnw.net/emoticons/v2/{hash_part}/default/dark/3.0',
                            f'https://static-cdn.jtvnw.net/emoticons/v2/{hash_part}/default/dark/2.0',
                            f'https://static-cdn.jtvnw.net/emoticons/v2/{hash_part}/default/dark/1.0',
                            f'https://static-cdn.jtvnw.net/emoticons/v1/{hash_part}/1.0',
                        ]
                        fetched = False
                        for url in candidates:
                            try:
                                r = session.get(url, timeout=8)
                                if getattr(r, 'status_code', None) == 200 and getattr(r, 'content', None):
                                    content = r.content
                                    ext = 'gif' if 'gif' in (r.headers.get('Content-Type') or '') else 'png'
                                    mime = 'image/gif' if ext == 'gif' else 'image/png'
                                    data_uri = f'data:{mime};base64,' + base64.b64encode(content).decode()
                                    emote_html = f'<img src="{data_uri}" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                                    fetched = True
                                    break
                            except Exception:
                                continue
                        if not fetched:
                            # Try resolving via emote set (Helix) which may populate id_map
                            try:
                                if eid.startswith('emotesv2_'):
                                    t_mgr.fetch_emote_sets([eid.split('emotesv2_', 1)[1]])
                                else:
                                    # attempt a generic fetch (best-effort)
                                    t_mgr.fetch_emote_sets([eid])
                                # After fetch, try to find by name
                                emote_text = message[s:e+1]
                                found_id = None
                                for mid, emobj in t_mgr.id_map.items():
                                    try:
                                        name = emobj.get('name') or emobj.get('emote_name') or emobj.get('code')
                                        if name == emote_text:
                                            found_id = mid
                                            break
                                    except Exception:
                                        continue
                                if found_id:
                                    data_uri = t_mgr.get_emote_data_uri(str(found_id))
                                    if data_uri:
                                        emote_html = f'<img src="{data_uri}" alt="emote" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                            except Exception:
                                pass
                    except Exception:
                        pass

            if emote_html:
                out_parts.append(emote_html)
            else:
                out_parts.append(html.escape(message[s:e+1]))

            last = e + 1

        # Append remaining text
        if last < len(message):
            out_parts.append(html.escape(message[last:]))

        interim_html = ''.join(out_parts)

        # Now replace BTTV/FFZ emotes by name within the non-HTML parts.
        # We will perform token-based replacement on the message while preserving existing <img> tags.
        # Strategy: split interim_html on <img .../> tags, process text parts, then join back.
        parts = re.split(r'(<img[^>]*>)', interim_html)
        b_mgr.ensure_channel(broadcaster_id)
        for i, part in enumerate(parts):
            if part.startswith('<img'):
                continue
            # Replace tokens in this text part
            def repl_token(m):
                token = m.group(0)
                # Try BTTV/FFZ exact name match first
                data_uri = b_mgr.get_emote_data_uri_by_name(token, broadcaster_id=broadcaster_id)
                if data_uri:
                    return f'<img src="{data_uri}" alt="{token}" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                return token

            parts[i] = re.sub(r'\b(\S+)\b', repl_token, part)

        final_html = ''.join(parts)

        # Final targeted name-resolution: replace remaining visible tokens with known Twitch emote URIs
        try:
            tokens = re.findall(r"\b(\S+)\b", message)
            for t in tokens:
                if not t or len(t) < 2:
                    continue
                esc = html.escape(t)
                # If token no longer appears visibly (already replaced), skip
                if esc not in final_html:
                    continue
                try:
                    id_map = getattr(t_mgr, 'id_map', {}) or {}
                    matches = []
                    for mid, emobj in id_map.items():
                        try:
                            name = emobj.get('name') or emobj.get('emote_name') or emobj.get('code')
                            if name == t:
                                matches.append(mid)
                        except Exception:
                            continue
                    if not matches:
                        continue
                    for mid in matches:
                        try:
                            uri = t_mgr.get_emote_data_uri(str(mid), broadcaster_id=broadcaster_id)
                        except Exception:
                            uri = None
                        if uri:
                            tag = f'<img src="{uri}" alt="{t}" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />'
                            final_html = final_html.replace(esc, tag)
                            break
                except Exception:
                    continue
        except Exception:
            pass

        # Diagnostic: record render completion and any unresolved known emote tokens
        try:
            import time as _t
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            dbg = os.path.join(log_dir, 'emote_debug.log')

            # Determine message id if provided in metadata
            mid = None
            try:
                if metadata and isinstance(metadata, dict):
                    mid = metadata.get('message_id') or metadata.get('id')
            except Exception:
                mid = None

            has_img = '<img' in final_html

            # Find tokens that are known emotes but remained as text in final_html
            unresolved = []
            try:
                tokens = re.findall(r"\b(\S+)\b", message)
                for t in tokens:
                    # Skip tokens that are purely punctuation or short
                    if not t or len(t) < 2:
                        continue
                    resolved = False
                    try:
                        # Check BTTV/FFZ map
                        if b_mgr and getattr(b_mgr, 'name_map', None) and t in b_mgr.name_map:
                            resolved = True
                        # Check Twitch id_map by name
                        if not resolved and t_mgr and getattr(t_mgr, 'id_map', None):
                            for _id, emobj in t_mgr.id_map.items():
                                try:
                                    name = emobj.get('name') or emobj.get('emote_name') or emobj.get('code')
                                    if name == t:
                                        resolved = True
                                        break
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    # If this token is a known emote source but still appears in the HTML, mark unresolved
                    try:
                        esc = html.escape(t)
                        if resolved and esc in final_html:
                            unresolved.append(t)
                    except Exception:
                        continue
            except Exception:
                unresolved = []

            with open(dbg, 'a', encoding='utf-8', errors='replace') as df:
                df.write(f"{_t.time():.3f} RENDER_COMPLETE mid={repr(mid)} has_img={has_img} unresolved={repr(unresolved)} len_html={len(final_html)}\n")
        except Exception:
            try:
                logger.debug('Failed to write emote render completion log')
            except Exception:
                pass

        return final_html, has_img
    except Exception as e:
        logger.debug(f'render_message failed: {e}')
        return html.escape(message), ('<img' in html.escape(message))
