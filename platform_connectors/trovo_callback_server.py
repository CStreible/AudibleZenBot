from flask import Flask, request
import threading

# Flask app for receiving Trovo OAuth redirect callbacks
app = Flask(__name__)

# Thread-safe container and event to signal code arrival to the rest of the process
last_code_event = threading.Event()
last_code_container = {}


@app.route('/callback')
def callback():
    code = request.args.get('code')
    print(f"[Trovo OAuth] Received callback with code: {code}")
    if code:
        # Store code and notify any waiting thread
        last_code_container['code'] = code
        try:
            last_code_event.set()
        except Exception:
            pass
        return f"Authorization code received: <b>{code}</b><br>You may close this window and return to AudibleZenBot."
    else:
        return "No authorization code found in the request."


if __name__ == '__main__':
    print("[Trovo Callback Server] Starting on http://localhost:8889")
    app.run(port=8889)
