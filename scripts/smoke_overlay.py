import time
import requests

from scripts import headless_runner as hr

hr.overlay_server.start()

# push a test overlay message
hr.overlay_server.add_message('smoke', 'SmokeTester', 'Hello from smoke test', 'smoke-1')

for i in range(10):
    try:
        r = requests.get('http://127.0.0.1:5000/overlay', timeout=1)
        print('overlay status', r.status_code)
        r2 = requests.get('http://127.0.0.1:5000/overlay/messages', timeout=1)
        print('messages', r2.json())
        break
    except Exception as e:
        print('attempt', i, 'failed:', e)
        time.sleep(0.5)

# keep server alive briefly for manual inspection if needed
time.sleep(5)
