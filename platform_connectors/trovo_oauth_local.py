import requests
import webbrowser
from urllib.parse import urlencode

TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
TROVO_CLIENT_SECRET = "a6a9471aed462e984c85feb04e39882e"
TROVO_REDIRECT_URI = "https://mistilled-declan-unendable.ngrok-free.dev/callback"
TROVO_AUTH_URL = "https://open.trovo.live/page/login.html"
TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/exchangetoken"

SCOPES = [
    "chat_connect",
    "chat_send_self",
    "manage_messages",
    "channel_details_self",
    "channel_update_self",
    "user_details_self"
]

def get_authorization_url():
    params = {
        "response_type": "code",
        "client_id": TROVO_CLIENT_ID,
        "redirect_uri": TROVO_REDIRECT_URI,
        "scope": "chat_connect+chat_send_self+manage_messages+channel_details_self+channel_update_self+user_details_self",
        "state": "trovo_state_123"
    }
    url = f"{TROVO_AUTH_URL}?{urlencode(params)}"
    return url

def exchange_code_for_token(auth_code):
    headers = {
        "Accept": "application/json",
        "client-id": TROVO_CLIENT_ID,
        "Content-Type": "application/json"
    }
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
    print("Trovo OAuth2 Authorization Flow (Automated)")
    print("\n" + "="*60)
    print("IMPORTANT: Make sure the callback server is running!")
    print("Run in another terminal: python platform_connectors/trovo_callback_server.py")
    print("Or make sure ngrok is running: ngrok http 8889")
    print("="*60 + "\n")
    
    url = get_authorization_url()
    print(f"Open this URL in your browser and authorize the app:\n{url}\n")
    webbrowser.open(url)
    print("\nAfter authorizing, check the callback server terminal for the code.")
    auth_code = input("Paste the authorization code: ").strip()
    token_data = exchange_code_for_token(auth_code)
    if token_data:
        print("Access Token Response:")
        print(token_data)
        # Save to config.json
        try:
            import sys, os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from core.config import ConfigManager
            config = ConfigManager()
            config.set_platform_config('trovo', 'access_token', token_data.get('access_token', ''))
            config.set_platform_config('trovo', 'refresh_token', token_data.get('refresh_token', ''))
            print("Trovo access_token and refresh_token saved to config.json!")
        except Exception as e:
            print(f"Error saving tokens to config: {e}")
    else:
        print("Failed to obtain access token.")
