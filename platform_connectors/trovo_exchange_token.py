try:
    import requests
except Exception:
    requests = None
from core.logger import get_logger

logger = get_logger(__name__)
try:
    from core.http_session import make_retry_session
except Exception:
    make_retry_session = None

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
    try:
        session = make_retry_session() if make_retry_session else (requests.Session() if requests is not None else None)
        if session is None:
            logger.error("[Trovo OAuth] 'requests' library not available in environment")
            return None
        resp = session.post(TROVO_TOKEN_URL, headers=headers, json=data, timeout=10)
    except Exception as e:
        logger.exception(f"[Trovo OAuth] Network error exchanging code: {e}")
        return None
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.error(f"[Trovo OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    code = "6ea05778baf9b07755d84541de8dced4"  # Replace with your code if needed
    token_data = exchange_code_for_token(code)
    if token_data:
        logger.info("Access Token Response:")
        logger.debug(f"{token_data}")
    else:
        logger.error("Failed to obtain access token.")