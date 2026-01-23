"""
YouTube OAuth2 Authorization Flow (Automated with Local Server)
Gets OAuth token for YouTube Data API v3 access
"""
try:
    import requests
except Exception:
    requests = None
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import BaseHTTPRequestHandler
import threading
from typing import Any
from core.logger import get_logger

logger = get_logger(__name__)
try:
    from core import callback_server
except Exception:
    callback_server = None
try:
    from core.http_session import make_retry_session
except Exception:
    make_retry_session = None

# YouTube OAuth credentials: prefer values from config if present
YOUTUBE_REDIRECT_URI = "http://localhost:8080"
try:
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from core.config import ConfigManager
    cfg = ConfigManager()
    _yc = cfg.get_platform_config('youtube') or {}
    YOUTUBE_CLIENT_ID = _yc.get('client_id', '')
    YOUTUBE_CLIENT_SECRET = _yc.get('client_secret', '')
except Exception:
    YOUTUBE_CLIENT_ID = ''
    YOUTUBE_CLIENT_SECRET = ''
YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Required scopes for YouTube chat
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

# Compatibility: expose an event/container similar to other callback modules
last_code_event = threading.Event()
last_code_container: dict[str, Any] = {}


def _make_handler(container: dict, event: threading.Event):
    def _handler(req):
        try:
            code = req.args.get('code')
        except Exception:
            code = None
        if code:
            container['code'] = code
            try:
                event.set()
            except Exception:
                pass
            return ("Authorization code received. You may close this window.", 200)
        return ("No authorization code found.", 400)
    return _handler

def get_authorization_url():
    """Generate YouTube OAuth authorization URL"""
    if not YOUTUBE_CLIENT_ID:
        raise RuntimeError("YouTube client_id is not set in config (platforms.youtube.client_id)")
    params = {
        "response_type": "code",
        "client_id": YOUTUBE_CLIENT_ID,
        "redirect_uri": YOUTUBE_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"{YOUTUBE_AUTH_URL}?{urlencode(params)}"
    return url

def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token"""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": YOUTUBE_REDIRECT_URI
    }
    
    logger.debug(f"Exchanging code with redirect_uri: {YOUTUBE_REDIRECT_URI}")
    try:
        session = make_retry_session() if make_retry_session else (requests.Session() if requests is not None else None)
        if session is None:
            logger.error("[YouTube OAuth] 'requests' library not available in environment")
            return None
        resp = session.post(YOUTUBE_TOKEN_URL, headers=headers, data=data, timeout=10)
    except Exception as e:
        logger.exception(f"[YouTube OAuth] Network error exchanging code: {e}")
        return None
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.error(f"[YouTube OAuth] Error: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    logger.info("YouTube OAuth2 Authorization Flow (Automated)")

    # Register callback route on shared callback server if available
    port = 8080
    try:
        if callback_server:
            handler = _make_handler(last_code_container, last_code_event)
            callback_server.register_route('/callback', handler, methods=['GET'])
            # Start shared server on configured port if available
            try:
                from core.config import ConfigManager
                cfg = ConfigManager()
                port = int(cfg.get('ngrok.callback_port', 8080))
            except Exception:
                port = 8080
            callback_server.start_server(port)
            logger.info(f"[YouTube OAuth] Registered /callback on shared server (port {port})")
        else:
            # Fallback to simple HTTPServer for manual runs
            from http.server import HTTPServer
            server = HTTPServer(('localhost', 8080), BaseHTTPRequestHandler)
            server_thread = threading.Thread(target=server.handle_request)
            server_thread.daemon = True
            server_thread.start()
            logger.info("Local temporary server running (fallback)")
    except Exception as e:
        logger.exception(f"[YouTube OAuth] Failed to start callback handler: {e}")

    logger.info("Opening browser for authorization...")
    url = get_authorization_url()
    webbrowser.open(url)

    logger.info("Waiting for authorization... (120s timeout)")

    got = last_code_event.wait(timeout=120)
    if not got or 'code' not in last_code_container:
        logger.error("Timeout: No authorization code received.")
        exit(1)

    auth_code = last_code_container.get('code')
    logger.info(f"Authorization code received: {auth_code[:20]}...")
    logger.info("Exchanging code for token...")
    token_data = exchange_code_for_token(auth_code)

    if token_data:
        try:
            config = ConfigManager()
            config.set_platform_config('youtube', 'oauth_token', token_data.get('access_token', ''))
            config.set_platform_config('youtube', 'refresh_token', token_data.get('refresh_token', ''))
            logger.info("YouTube oauth_token and refresh_token saved to config.json")
        except Exception as e:
            logger.exception(f"Error saving tokens to config: {e}")
    else:
        logger.error("Failed to obtain access token.")
