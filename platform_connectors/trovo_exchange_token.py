import requests

TROVO_CLIENT_ID = ""
TROVO_CLIENT_SECRET = ""
TROVO_REDIRECT_URI = "https://mistilled-declan-unendable.ngrok-free.dev/callback"
TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/exchangetoken"

def exchange_code_for_token(auth_code):
    headers = {
        "Accept": "application/json",
        "client-id": TROVO_CLIENT_ID,
        "Content-Type": "application/json"
    }
    # If client id not set at module-level, try reading from config
    if not TROVO_CLIENT_ID:
        try:
            from core.config import ConfigManager
            cfg = ConfigManager()
            trovo_cfg = cfg.get_platform_config('trovo') or {}
            cid = trovo_cfg.get('client_id', '')
            if cid:
                headers['client-id'] = cid
        except Exception:
            pass
    data = {
        "client_secret": TROVO_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": TROVO_REDIRECT_URI
    }
    resp = requests.post(TROVO_TOKEN_URL, headers=headers, json=data)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"[Trovo OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    code = "6ea05778baf9b07755d84541de8dced4"  # Replace with your code if needed
    token_data = exchange_code_for_token(code)
    if token_data:
        print("Access Token Response:")
        print(token_data)
    else:
        print("Failed to obtain access token.")