import faulthandler
import threading
import time
import sys
import os

# Ensure logs dir exists
log_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(log_dir, exist_ok=True)
thread_dump_path = os.path.join(log_dir, 'thread_dumps.log')

# Enable faulthandler
faulthandler.enable(all_threads=True)

# Background dumper: writes all-thread tracebacks periodically
_stop = False

def _dumper():
    with open(thread_dump_path, 'a', encoding='utf-8', errors='replace') as f:
        while not _stop:
            f.write(f"--- Thread dump at {time.time():.3f}\n")
            try:
                faulthandler.dump_traceback(all_threads=True, file=f)
            except Exception as e:
                f.write(f"faulthandler.dump_traceback failed: {e}\n")
            f.write("--- End dump\n\n")
            f.flush()
            time.sleep(2.0)

_thread = threading.Thread(target=_dumper, daemon=True)
_thread.start()

# Start a stopper thread that will attempt a graceful QApplication quit
import runpy
import traceback

def _stopper(delay=10):
    time.sleep(delay)
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            try:
                app.quit()
            except Exception:
                pass
    except Exception:
        pass

stopper = threading.Thread(target=_stopper, args=(10,), daemon=True)
stopper.start()

# Run the app (this runs in the main thread so Qt stays happy)
try:
    # Ensure the project root is on sys.path so local packages like `core`
    # can be imported when running via runpy.
    proj_root = os.getcwd()
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)
    runpy.run_path(os.path.join(proj_root, 'main.py'), run_name='__main__')
except SystemExit:
    pass
except Exception:
    traceback.print_exc()
finally:
    # Signal dumper to stop and do a final dump
    _stop = True
    try:
        with open(thread_dump_path, 'a', encoding='utf-8', errors='replace') as f:
            f.write(f"--- Final dump at {time.time():.3f}\n")
            try:
                faulthandler.dump_traceback(all_threads=True, file=f)
            except Exception as e:
                f.write(f"faulthandler.dump_traceback failed: {e}\n")
            f.write("--- End final dump\n\n")
    except Exception:
        pass
    # Give dumper a moment to exit
    time.sleep(0.5)
