import os
import sys
sys.path.insert(0, r'c:\Users\cstre\Dev\VS\AudibleZenBot')
from core.twitch_emotes import get_manager

mgr = get_manager()
# Known emote set hashes observed in logs
hashes = ['87e9f2193ae04e6eb9c59293cda6b40e', 'db665b77cefb486183a4938305b6bab6']
print('calling fetch_emote_sets with', hashes)
try:
    mgr.fetch_emote_sets(hashes)
    print('fetch_emote_sets completed')
    # Print a few entries from id_map
    ids = list(mgr.id_map.keys())[:20]
    print('id_map sample count=', len(ids))
    for i in ids:
        try:
            e = mgr.id_map.get(i)
            print('id=', i, 'name=', e.get('name') or e.get('emote_name') or e.get('code'))
        except Exception:
            continue
except Exception as e:
    print('fetch_emote_sets error', e)

# show the twitch_emote_sets.log if it exists
logf = os.path.join(os.getcwd(), 'logs', 'twitch_emote_sets.log')
if os.path.exists(logf):
    print('\n--- twitch_emote_sets.log tail ---')
    with open(logf, 'r', encoding='utf-8', errors='replace') as f:
        for line in f.readlines()[-200:]:
            print(line.strip())
else:
    print('\nno twitch_emote_sets.log found')
