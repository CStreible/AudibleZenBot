from platform_connectors.twitch_connector import TwitchWorker
from core.twitch_emotes import get_manager
import json

# prepare manager with an emote id
m = get_manager()
m.id_map['25'] = {'id':'25','name':'<3','images':{'url_1x':'https://static-cdn.jtvnw.net/emoticons/v1/25/1.0'}}
# build fragments
frags = [
  {"type":"text","text":"Kappa "},
  {"type":"emote","emote":{"id":"25","name":"<3","text":"<3","emote_set_id":"100"}},
  {"type":"text","text":" done"}
]
js = json.dumps(frags, ensure_ascii=False)
# escape for IRC tag: \\ -> \\\\ then ; -> \: then space -> \s
esc = js.replace('\\','\\\\').replace(';','\\:').replace(' ','\\s').replace('\n','\\n').replace('\r','\\r')
raw = f"@fragments={esc} :tester!tester@test.tmi.twitch.tv PRIVMSG #channel :ignored"
w = TwitchWorker('testchan')
res = w.parse_privmsg(raw)
print('PARSE_RESULT:', res)
try:
  from core.emotes import render_message
  msg = res[1]
  meta = res[2]
  html, has_img = render_message(msg, meta.get('emotes'), meta)
  print('RENDERED HTML:', has_img, html)
except Exception as e:
  print('render failed', e)
