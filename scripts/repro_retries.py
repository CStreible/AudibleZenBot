import time
from unittest.mock import MagicMock
from core.twitch_emotes import TwitchEmoteManager, PrefetchError

mgr = TwitchEmoteManager(config={})

calls = {'count': 0}

def side_effect(batch):
    calls['count'] += 1
    print('SIDE_EFFECT called count=', calls['count'], 'batch=', batch)
    if calls['count'] < 3:
        raise PrefetchError('rate_limited', 'HTTP 429')
    return None

mgr.fetch_emote_sets = MagicMock(side_effect=side_effect)

# Patch time.sleep to no-op in this process
import time as _time
_orig_sleep = _time.sleep
_time.sleep = lambda s: None

mgr.schedule_emote_set_fetch(['1','2','3'])
mgr.start_emote_set_throttler()

timeout = time.time() + 2.0
while time.time() < timeout and calls['count'] < 3:
    _orig_sleep(0.01)

mgr.stop_emote_set_throttler()
print('final calls', calls)
