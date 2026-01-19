import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.emotes import render_message

# Use the broadcaster id we found
broadcaster_id = '853763018'
msg = 'audibl7Guitar audibl7BassGuitar NotLikeThis VoHiYo <3'
html_out, has_img = render_message(msg, None, {'room-id': broadcaster_id})
print('has_img=', has_img)
print(html_out)

# tail debug logs
dbg = os.path.join(os.getcwd(), 'logs', 'emote_resolve_debug.log')
if os.path.exists(dbg):
    print('\n--- debug log tail ---')
    with open(dbg, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        for line in lines[-80:]:
            print(line.strip())
else:
    print('\nno debug log found')
