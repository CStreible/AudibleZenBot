"""
Placeholder server for port 8889 (Kick webhooks)
This prevents ngrok errors when the Kick connector is not active
"""
from flask import Flask, request, jsonify
from core.logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        logger.info("Received webhook POST on port 8889")
        return jsonify({"status": "received"}), 200
    return "Kick webhook server placeholder - waiting for connection", 200

if __name__ == '__main__':
    logger.info("Starting placeholder server on port 8889")
    app.run(port=8889, host='0.0.0.0')
