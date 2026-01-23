from core.twitch_emotes import TwitchEmoteManager
from unittest.mock import MagicMock

mgr = TwitchEmoteManager(config={})

mgr.fetch_emote_sets = MagicMock()
print('fetch_emote_sets attr at start:', repr(getattr(mgr, 'fetch_emote_sets', None)))

mgr.schedule_emote_set_fetch(['1','2','3'])
item = None
try:
    item = mgr._emote_set_queue.get_nowait()
except Exception as e:
    print('queue empty or error', e)

print('queued item repr:', repr(item))
if isinstance(item, tuple):
    print('tuple marker, batch_list:', item[1])
else:
    print('raw item type', type(item), item)
