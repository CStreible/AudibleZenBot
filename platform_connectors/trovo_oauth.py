import requests
import webbrowser
from urllib.parse import urlencode

TROVO_CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
TROVO_CLIENT_SECRET = "a6a9471aed462e984c85feb04e39882e"
TROVO_REDIRECT_URI = "http://localhost:8080/callback"
TROVO_AUTH_URL = "https://open-api.trovo.live/openplatform/authorize"
TROVO_TOKEN_URL = "https://open-api.trovo.live/openplatform/token"

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
        "scope": " ".join(SCOPES),
        "state": "trovo_state_123"
    }
    url = f"{TROVO_AUTH_URL}?{urlencode(params)}"
    return url


def exchange_code_for_token_v2(auth_code):
    url = "https://open-api.trovo.live/openplatform/exchangetoken"
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
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"[Trovo OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    print("Trovo OAuth2 Authorization Flow")
    url = get_authorization_url()
    print(f"Open this URL in your browser and authorize the app:\n{url}\n")
    webbrowser.open(url)
    auth_code = input("Paste the authorization code from the redirect URL: ").strip()
    token_data = exchange_code_for_token(auth_code)
    if token_data:
        print("Access Token Response:")
        print(token_data)
    else:
        print("Failed to obtain access token.")
