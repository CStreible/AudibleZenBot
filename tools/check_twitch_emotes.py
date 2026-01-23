import sys, os, json

# Ensure project root is on sys.path so `core` imports resolve
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from core.twitch_emotes import get_manager

mgr = get_manager()
print('client_id:', bool(getattr(mgr, 'client_id', None)))
print('oauth_token:', bool(getattr(mgr, 'oauth_token', None)))
print('cache_dir:', getattr(mgr, 'cache_dir', None))
print('initial id_map size:', len(getattr(mgr, 'id_map', {})))

hashes = ['db665b77cefb486183a4938305b6bab6','87e9f2193ae04e6eb9c59293cda6b40e']
try:
    mgr.fetch_emote_sets(hashes)
    print('after fetch_emote_sets id_map size:', len(mgr.id_map))
except Exception as e:
    print('fetch_emote_sets error:', repr(e))

broadcaster_id = '853763018'
try:
    mgr.fetch_channel_emotes(broadcaster_id)
    print('after fetch_channel_emotes id_map size:', len(mgr.id_map))
except Exception as e:
    print('fetch_channel_emotes error:', repr(e))

matches = []
for k,v in mgr.id_map.items():
    name = None
    if isinstance(v, dict):
        name = v.get('name') or v.get('emote_name') or v.get('code')
    if name and ('audibl' in name.lower() or 'guitar' in name.lower()):
        matches.append((k,name))
print('matches:', json.dumps(matches))

sample_keys = list(mgr.id_map.keys())[:20]
print('sample ids:', json.dumps(sample_keys))
