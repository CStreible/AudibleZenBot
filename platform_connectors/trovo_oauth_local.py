try:
    import requests
except Exception:
    requests = None
import webbrowser
from urllib.parse import urlencode
from core.logger import get_logger

logger = get_logger(__name__)
try:
    from core.http_session import make_retry_session
except Exception:
    make_retry_session = None

TROVO_CLIENT_ID = ""
TROVO_CLIENT_SECRET = ""
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
        "scope": "chat_connect+chat_send_self+manage_messages+channel_details_self+channel_update_self+user_details_self",
        "state": "trovo_state_123"
    }
    url = f"{TROVO_AUTH_URL}?{urlencode(params)}"
    return url

def exchange_code_for_token(auth_code):
    # Prefer configured client id/secret when module-level values are not set
    client_id = TROVO_CLIENT_ID
    client_secret = TROVO_CLIENT_SECRET
    try:
        if not client_id or not client_secret:
            from core.config import ConfigManager
            cfg = ConfigManager()
            trovo_cfg = cfg.get_platform_config('trovo') or {}
            client_id = client_id or trovo_cfg.get('client_id', '')
            client_secret = client_secret or trovo_cfg.get('client_secret', '')
    except Exception:
        client_id = client_id or ''
        client_secret = client_secret or ''

    headers = {
        "Accept": "application/json",
        "client-id": client_id
    }

    # Trovo token endpoint expects form-encoded POST parameters
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": TROVO_REDIRECT_URI
    }
    try:
        session = make_retry_session() if make_retry_session else (requests.Session() if requests is not None else None)
        if session is None:
            logger.error("[Trovo OAuth] 'requests' library not available in environment")
            return None
        # Save outgoing request (mask secret) for debugging
        try:
            import json, time
            dbg = {'ts': int(time.time()), 'url': TROVO_TOKEN_URL, 'headers': dict(headers), 'data': dict(data)}
            if 'client_secret' in dbg['data']:
                dbg['data']['client_secret'] = '***'
            try:
                with open('tools/trovo_oauth_local_request.json', 'w', encoding='utf-8') as f:
                    json.dump(dbg, f, indent=2)
            except Exception:
                pass
        except Exception:
            pass
        resp = session.post(TROVO_TOKEN_URL, headers=headers, data=data, timeout=10)
    except Exception as e:
        logger.exception(f"[Trovo OAuth] Network error exchanging code: {e}")
        return None
    if resp.status_code == 200:
        data = resp.json()
        # Normalize Trovo envelope {'data': [{...}]}
        try:
            if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                return data['data'][0]
        except Exception:
            pass
        return data
    else:
        logger.error(f"[Trovo OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    logger.info("Trovo OAuth2 Authorization Flow (Automated)")
    logger.info("IMPORTANT: Make sure the callback server is running!")
    logger.info("Run in another terminal: python platform_connectors/trovo_callback_server.py")
    logger.info("Or make sure ngrok is running: ngrok http 8889")

    url = get_authorization_url()
    logger.info(f"Open this URL in your browser and authorize the app:\n{url}\n")
    webbrowser.open(url)
    logger.info("After authorizing, check the callback server terminal for the code.")
    auth_code = input("Paste the authorization code: ").strip()
    token_data = exchange_code_for_token(auth_code)
    if token_data:
        logger.info("Access Token Response:")
        logger.debug(f"{token_data}")
        # Save to config.json
        try:
            import sys, os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from core.config import ConfigManager
            config = ConfigManager()
            config.set_platform_config('trovo', 'access_token', token_data.get('access_token', ''))
            config.set_platform_config('trovo', 'refresh_token', token_data.get('refresh_token', ''))
            logger.info("Trovo access_token and refresh_token saved to config.json")
        except Exception as e:
            logger.exception(f"Error saving tokens to config: {e}")
    else:
        logger.error("Failed to obtain access token.")
