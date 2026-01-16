"""
Placeholder server for port 8889 (Kick webhooks)
This prevents ngrok errors when the Kick connector is not active
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        print(f"[Port 8889] Received webhook POST")
        return jsonify({"status": "received"}), 200
    return "Kick webhook server placeholder - waiting for connection", 200

if __name__ == '__main__':
    print("[Port 8889] Starting placeholder server...")
    app.run(port=8889, host='0.0.0.0')
