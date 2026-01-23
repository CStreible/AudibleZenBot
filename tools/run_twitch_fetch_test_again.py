#!/usr/bin/env python3
import os
import sys
# Ensure project root is on sys.path so `core` package is importable
sys.path.insert(0, os.getcwd())
from core.twitch_emotes import get_manager
from core.config import ConfigManager

mgr = get_manager()
hashes = ['87e9f2193ae04e6eb9c59293cda6b40e','db665b77cefb486183a4938305b6bab6']

# Attempt to populate credentials from environment or saved config
client_id = os.environ.get('TWITCH_CLIENT_ID')
oauth = os.environ.get('TWITCH_OAUTH_TOKEN')
if not client_id or not oauth:
    try:
        cfg = ConfigManager()
        pc = cfg.get_platform_config('twitch') or {}
        client_id = client_id or pc.get('client_id') or pc.get('clientId')
        oauth = oauth or pc.get('oauth_token') or pc.get('access_token')
        print('Loaded credentials from config:', bool(client_id), bool(oauth))
    except Exception:
        print('ConfigManager not available or failed to load config')

print('TWITCH_CLIENT_ID:', client_id)
print('TWITCH_OAUTH_TOKEN present:', bool(oauth))
print('Calling fetch_emote_sets for:', hashes)
try:
    # inject creds into manager if available
    if client_id:
        try:
            mgr.client_id = client_id
        except Exception:
            pass
    if oauth:
        try:
            mgr.oauth_token = oauth
        except Exception:
            pass
    mgr.fetch_emote_sets(hashes)
    print('fetch_emote_sets returned; id_map size=', len(mgr.id_map))
    matches = []
    for mid, em in mgr.id_map.items():
        try:
            name = em.get('name') or em.get('emote_name') or em.get('code')
        except Exception:
            name = None
        if name and ('audibl7' in name or name in ('audibl7Guitar','audibl7BassGuitar')):
            matches.append((mid, name))
    print('Matches for audibl7 tokens:', matches)
except Exception as e:
    print('Error during fetch_emote_sets:', e)

# Print tail of twitch_emote_sets.log if present
logp = os.path.join(os.getcwd(), 'logs', 'twitch_emote_sets.log')
print('\n-- twitch_emote_sets.log tail --')
if os.path.exists(logp):
    try:
        with open(logp, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read().splitlines()
        for l in lines[-60:]:
            print(l)
    except Exception as e:
        print('Failed to read log:', e)
else:
    print('Log file not found:', logp)
