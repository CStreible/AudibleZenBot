import sys, html as _html
sys.path.insert(0, r'c:\Users\cstre\Dev\VS\AudibleZenBot')
from core.twitch_emotes import get_manager as get_twitch_manager

BID = '853763018'
msg = 'audibl7Guitar    audibl7BassGuitar    NotLikeThis    VoHiYo    <3'
print('orig=', msg)

t = get_twitch_manager()
try:
    t.fetch_channel_emotes(BID)
except Exception as e:
    print('fetch_channel_emotes failed', e)

id_map = getattr(t, 'id_map', {}) or {}
print('id_map_size=', len(id_map))

final = _html.escape(msg)
resolved = []
for token in ['audibl7Guitar', 'audibl7BassGuitar', 'NotLikeThis', 'VoHiYo']:
    matches = [mid for mid, em in id_map.items() if (em.get('name') or em.get('emote_name') or em.get('code')) == token]
    print('token=', token, 'matches=', matches)
    if matches:
        for mid in matches:
            try:
                uri = t.get_emote_data_uri(str(mid), broadcaster_id=BID)
            except Exception as e:
                uri = None
            print('  try mid', mid, 'uri?', bool(uri))
            if uri:
                tag = '<img src="%s" alt="%s" style="width:1.2em; height:1.2em; vertical-align:middle; margin:0 2px;" />' % (uri, token)
                final = final.replace(_html.escape(token), tag)
                resolved.append(token)
                break

print('resolved tokens=', resolved)
print('has_img=', '<img' in final)
print('len_final=', len(final))
print('final_preview=', final[:400])
