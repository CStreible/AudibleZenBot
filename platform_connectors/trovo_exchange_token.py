try:
    import requests
except Exception:
    requests = None
from core.logger import get_logger
import json
import time

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
        pass

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
        # Log outgoing request (mask client_secret) and persist debug info
        try:
            dbg = {
                'ts': int(time.time()),
                'url': TROVO_TOKEN_URL,
                'headers': dict(headers),
                'data': dict(data)
            }
            if 'client_secret' in dbg['data']:
                dbg['data']['client_secret'] = '***'
            try:
                with open('tools/trovo_exchange_debug_verbose.json', 'w', encoding='utf-8') as f:
                    json.dump(dbg, f, indent=2)
            except Exception:
                pass
        except Exception:
            pass

        resp = session.post(TROVO_TOKEN_URL, headers=headers, data=data, timeout=10)
    except Exception as e:
        logger.exception(f"[Trovo OAuth] Network error exchanging code: {e}")
        return None
    try:
        status = resp.status_code
    except Exception:
        status = None
    # Save response debug
    try:
        out = {
            'ts': int(time.time()),
            'status_code': status,
            'response_text': getattr(resp, 'text', None),
            'response_headers': dict(getattr(resp, 'headers', {})),
            'response_json': None
        }
        try:
            out['response_json'] = resp.json()
        except Exception:
            out['response_json'] = None
        try:
            with open('tools/trovo_exchange_response_verbose.json', 'w', encoding='utf-8') as f:
                json.dump(out, f, indent=2)
        except Exception:
            pass
    except Exception:
        pass

    if status == 200:
        data = resp.json()
        # Normalize Trovo's envelope format {'data': [{...}]} to a flat dict
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
    code = "6ea05778baf9b07755d84541de8dced4"  # Replace with your code if needed
    token_data = exchange_code_for_token(code)
    if token_data:
        logger.info("Access Token Response:")
        logger.debug(f"{token_data}")
    else:
        logger.error("Failed to obtain access token.")