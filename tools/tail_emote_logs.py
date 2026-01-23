import time, os, sys

LOG_FILES = [
    ('connector', os.path.join('logs', 'connector_incoming.log')),
    ('render_trace', os.path.join('logs', 'chat_page_render_trace.log')),
    ('emote_debug', os.path.join('logs', 'emote_debug.log')),
    ('resolve_debug', os.path.join('logs', 'emote_resolve_debug.log')),
]

# Ensure log directory exists
os.makedirs('logs', exist_ok=True)

# Open files and seek to end
files = []
for prefix, path in LOG_FILES:
    try:
        f = open(path, 'a+', encoding='utf-8', errors='replace')
        f.seek(0, os.SEEK_END)
        files.append((prefix, path, f))
    except Exception as e:
        print(f"[tailer] failed to open {path}: {e}")

print('[tailer] started. Ctrl-C to stop.')
try:
    while True:
        for prefix, path, f in files:
            try:
                where = f.tell()
                line = f.readline()
                if not line:
                    f.seek(where)
                else:
                    sys.stdout.write(f'[{prefix}] {line}')
                    sys.stdout.flush()
            except Exception:
                pass
        time.sleep(0.25)
except KeyboardInterrupt:
    print('\n[tailer] stopped by user')
    for _, _, f in files:
        try:
            f.close()
        except Exception:
            pass
