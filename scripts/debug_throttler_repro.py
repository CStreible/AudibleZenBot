import time
import sys
import os
# ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.twitch_emotes import TwitchEmoteManager

calls = []

def fake_fetch(batch):
    print('fake_fetch called with', batch)
    calls.append(list(batch))

m = TwitchEmoteManager(config=None)
m.fetch_emote_sets = fake_fetch

print('Scheduling fetch')
m.schedule_emote_set_fetch(['x','y','z'])
print('_fetch_emote_sets_override present:', getattr(m, '_fetch_emote_sets_override', None))
print('Starting throttler')
m.start_emote_set_throttler()

# Wait a bit for worker
time.sleep(2.0)

print('Stopping')
m.stop_emote_set_throttler()
print('Calls:', calls)
