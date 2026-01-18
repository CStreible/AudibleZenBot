import requests
import webbrowser
from urllib.parse import urlencode
from core.logger import get_logger

logger = get_logger(__name__)

TROVO_CLIENT_ID = ""
TROVO_CLIENT_SECRET = ""
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
    # Prefer configured client id if available
    client_id = TROVO_CLIENT_ID
    if not client_id:
        try:
            from core.config import ConfigManager
            cfg = ConfigManager()
            trovo_cfg = cfg.get_platform_config('trovo') or {}
            client_id = trovo_cfg.get('client_id', '')
        except Exception:
            client_id = ''
    params = {
        "response_type": "code",
        "client_id": client_id,
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
        logger.error(f"[Trovo OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    logger.info("Trovo OAuth2 Authorization Flow")
    url = get_authorization_url()
    logger.info(f"Open this URL in your browser and authorize the app:\n{url}\n")
    webbrowser.open(url)
    auth_code = input("Paste the authorization code from the redirect URL: ").strip()
    token_data = exchange_code_for_token(auth_code)
    if token_data:
        logger.info("Access Token Response:")
        logger.debug(f"{token_data}")
    else:
        logger.error("Failed to obtain access token.")
