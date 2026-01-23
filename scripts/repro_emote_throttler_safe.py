"""Repro harness for emote-set throttler (safe import).

This script removes the current working directory from sys.path before
importing project modules so local stub files like `requests.py` don't
shadow the real `requests` package.
"""

import sys
import os
import time

# Ensure the virtualenv site-packages are prioritized so installed packages
# (e.g., `requests`) are found before any local files that might shadow them.
try:
    import site as _site
    site_paths = []
    try:
        site_paths = _site.getsitepackages()
    except Exception:
        # Fall back to using sys.path entries that look like site-packages
        site_paths = [p for p in sys.path if p and ('site-packages' in p or 'dist-packages' in p)]
    for p in reversed(site_paths):
        try:
            if p and os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        except Exception:
            pass
except Exception:
    pass

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
