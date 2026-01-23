import sys
import os
import time

# Ensure repo root on path
sys.path.insert(0, os.getcwd())
from core.twitch_emotes import TwitchEmoteManager

mgr = TwitchEmoteManager(config=None)
calls = []

def fake_fetch(batch):
    print('fake_fetch called with', batch)
    calls.append(list(batch))
    try:
        with open('scripts/repro_throttler_out.txt', 'a', encoding='utf-8') as f:
            f.write('called:' + ','.join(batch) + '\n')
            f.flush()
    except Exception:
        pass
    # Force an exception to surface in the worker for diagnostics
    if 'direct' not in batch:
        raise RuntimeError('fake_fetch-exception')
    # raise to make worker log the exception (diagnostic)
    # raise RuntimeError('boom')

mgr.fetch_emote_sets = fake_fetch
print('before schedule, throttler_thread:', mgr._throttler_thread)
print('fetch_emote_sets callable:', mgr.fetch_emote_sets)
# Call directly to verify instance attribute works
print('calling fetch_emote_sets directly...')
mgr.fetch_emote_sets(['direct'])
scheduled = mgr.schedule_emote_set_fetch(['a','b','c'])
print('scheduled:', scheduled)
# wait
timeout = time.time() + 2
while time.time() < timeout:
    if calls:
        break
    time.sleep(0.02)
print('calls after wait:', calls)
mgr.stop_emote_set_throttler()
print('done')
