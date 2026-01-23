import time
import threading
from core.twitch_emotes import TwitchEmoteManager

print('starting repro')
mgr = TwitchEmoteManager(config=None)

calls = []

def fake_fetch(batch):
    print('fake_fetch called in thread', threading.current_thread().name, 'batch=', batch)
    calls.append(list(batch))

mgr.fetch_emote_sets = fake_fetch

print('after monkeypatch, mgr.fetch_emote_sets =', repr(getattr(mgr, 'fetch_emote_sets', None)))

print('throttler before start:', mgr._throttler_thread)
mgr.schedule_emote_set_fetch(['x','y','z'])
print('scheduled')
# allow some time
for i in range(10):
    time.sleep(0.1)
    print('tick', i, 'calls:', calls)

mgr.stop_emote_set_throttler()
print('stopped', calls)
