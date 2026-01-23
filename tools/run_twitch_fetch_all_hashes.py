#!/usr/bin/env python3
import os
import re
import sys
sys.path.insert(0, os.getcwd())
from core.twitch_emotes import get_manager
from core.config import ConfigManager

# gather unique hashes from logs
logdir = os.path.join(os.getcwd(), 'logs')
hashes = set()
if os.path.isdir(logdir):
    for fname in os.listdir(logdir):
        if not fname.endswith('.log'):
            continue
        path = os.path.join(logdir, fname)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    for m in re.finditer(r'emotesv2_([0-9a-fA-F]{8,})', line):
                        hashes.add(m.group(1))
        except Exception:
            continue

hashes = sorted(hashes)
print('Found hashes:', hashes)

mgr = get_manager()
# inject creds from config if present
try:
    cfg = ConfigManager()
    pc = cfg.get_platform_config('twitch') or {}
    client_id = pc.get('client_id') or pc.get('clientId')
    oauth = pc.get('oauth_token') or pc.get('access_token')
    if client_id:
        mgr.client_id = client_id
    if oauth:
        mgr.oauth_token = oauth
    print('Using client_id present:', bool(client_id), 'oauth present:', bool(oauth))
except Exception:
    print('No config creds available')

# Batch them in groups of up to 20 (Helix supports multiple params)
import time
from itertools import islice

def chunks(iterable, n):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            break
        yield chunk

for c in chunks(hashes, 20):
    print('\nFetching sets for:', c)
    try:
        mgr.fetch_emote_sets(c)
        print('id_map size now', len(mgr.id_map))
    except Exception as e:
        print('fetch failed for chunk:', e)
    time.sleep(0.2)

# print any matches by name in id_map
matches = []
for mid, em in mgr.id_map.items():
    try:
        name = em.get('name') or em.get('emote_name') or em.get('code')
    except Exception:
        name = None
    if name and 'audibl7' in name:
        matches.append((mid, name))

print('\nMatches by name containing audibl7:', matches)

# tail twitch_emote_sets.log
logp = os.path.join(logdir, 'twitch_emote_sets.log')
print('\n-- twitch_emote_sets.log tail --')
if os.path.exists(logp):
    with open(logp, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.read().splitlines()
    for l in lines[-200:]:
        print(l)
else:
    print('no log')
