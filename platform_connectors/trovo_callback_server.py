from flask import Flask, request

app = Flask(__name__)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    print(f"[Trovo OAuth] Received callback with code: {code}")
    if code:
        return f"Authorization code received: <b>{code}</b><br>Copy this code and paste it into your OAuth script."
    else:
        return "No authorization code found in the request."

if __name__ == '__main__':
    print("[Trovo Callback Server] Starting on http://localhost:8889")
    app.run(port=8889)
