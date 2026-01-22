import time
from core.twitch_emotes import get_manager

print('Obtaining manager...')
mgr = get_manager()
print('Throttler thread alive:', bool(getattr(mgr, '_throttler_thread', None) and getattr(mgr._throttler_thread, 'is_alive', lambda: False)()))

# Enqueue first batch (single set with interest)
items1 = [("33", ["445"]) ]
print('Scheduling first batch:', items1)
mgr.schedule_emote_set_fetch(items1)
print('After schedule: queue qsize=', mgr._emote_set_queue.qsize())

# Monitor for a short period
for i in range(8):
    print(f'[{i}] throttler_alive={bool(mgr._throttler_thread and mgr._throttler_thread.is_alive())} qsize={mgr._emote_set_queue.qsize()}')
    time.sleep(0.5)

# Enqueue second batch
items2 = [("9021eb5b-45a45dcd275a4a29be70e7492fae8e50", ["emotesv2_45a45dcd275a4a29be70e7492fae8e50"]) ]
print('Scheduling second batch:', items2)
mgr.schedule_emote_set_fetch(items2)
print('After second schedule: queue qsize=', mgr._emote_set_queue.qsize())

# Wait to allow throttler to process
for i in range(12):
    print(f'wait [{i}] qsize={mgr._emote_set_queue.qsize()}')
    time.sleep(0.5)

print('Done. Final qsize=', mgr._emote_set_queue.qsize())
print('Check logs/audiblezenbot.log and logs/chat_page_dom.log for throttler activity and cache events.')
