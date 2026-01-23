"""
OAuth Authentication Handler
Handles OAuth flows for platform authentication
"""

import webbrowser
import secrets
import hashlib
import base64
from urllib.parse import urlencode, parse_qs, urlparse
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
from http.server import BaseHTTPRequestHandler
import threading
from typing import Optional
try:
    from core import callback_server
except Exception:
    callback_server = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Compatibility placeholder - some code may still reference this class."""

    def log_message(self, format, *args):
        pass


class OAuthHandler(QObject):
    """Handles OAuth authentication flows"""
    
    auth_completed = pyqtSignal(str, str)  # platform, token
    auth_failed = pyqtSignal(str, str)  # platform, error
    
    # Platform OAuth configurations
    CONFIGS = {
        'twitch': {
            'auth_url': 'https://id.twitch.tv/oauth2/authorize',
            'token_url': 'https://id.twitch.tv/oauth2/token',
            'client_id': 'YOUR_TWITCH_CLIENT_ID',  # User must set this
            'redirect_uri': 'http://localhost:3000',
            'scopes': [
                'chat:read',
                'chat:edit',
                'user:edit:broadcast',
                'channel:manage:broadcast',
                # Ensure EventSub subscriptions work
                'channel:read:redemptions',
                'bits:read',
                'moderator:read:followers',
            ]
        },
        'youtube': {
            'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'client_id': 'YOUR_YOUTUBE_CLIENT_ID',  # User must set this
            'redirect_uri': 'http://localhost:3000',
            'scopes': ['https://www.googleapis.com/auth/youtube.readonly',
                      'https://www.googleapis.com/auth/youtube.force-ssl']
        },
        'twitter': {
            'auth_url': 'https://twitter.com/i/oauth2/authorize',
            'token_url': 'https://api.twitter.com/2/oauth2/token',
            'client_id': 'YnpWQ2s2Q1VuX1RVWG4wTlNvZTg6MTpjaQ',
            'client_secret': '52_s2M2njaNEGOymH0Bym9h7Ry6xPjOY9J4YuHPztrZrPROMZ8',
            'api_key': 'ZEqQ0iXfbNHDnubYxeyhX8fL4',
            'api_secret': 'MTerotKmlDR2ClhmtJvKcMNlLPYZU6WMN2LBymITVnUrs2z7C3',
            'redirect_uri': 'http://localhost:3000',
            'scopes': ['tweet.read', 'users.read', 'offline.access']
        }
    }
    
    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
    
    def authenticate(self, platform: str, client_id: str = None, client_secret: str = None):
        """
        Start OAuth authentication for a platform
        
        Args:
            platform: Platform identifier
            client_id: Optional client ID override
            client_secret: Optional client secret override
        """
        if platform not in self.CONFIGS:
            self.auth_failed.emit(platform, f"Platform {platform} not supported")
            return
        
        config = self.CONFIGS[platform].copy()

        # Ensure redirect_uri uses the configured callback port (ngrok/local)
        try:
            from core.config import ConfigManager
            cfg = ConfigManager()
            port = int(cfg.get('ngrok.callback_port', 8889))
        except Exception:
            port = 8889
        try:
            # Use a stable callback path so providers can be configured with a single redirect URI
            config['redirect_uri'] = f"http://localhost:{port}/oauth/{platform}"
        except Exception:
            pass
        
        # Override with provided credentials
        if client_id:
            config['client_id'] = client_id
        if client_secret:
            config['client_secret'] = client_secret
        
        # Check if client ID is set
        if config['client_id'].startswith('YOUR_'):
            self.auth_failed.emit(platform, 
                "Client ID not configured. Please set up OAuth credentials.")
            return
        
        # Generate PKCE parameters
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32)
        
        # Build authorization URL
        params = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'response_type': 'code',
            'scope': ' '.join(config['scopes']),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        # For YouTube/Google, force account selection prompt
        if platform == 'youtube':
            params['prompt'] = 'select_account'
        
        auth_url = f"{config['auth_url']}?{urlencode(params)}"
        
        # Start local server for callback
        self._start_callback_server(platform, config, code_verifier, state)
        
        # Open browser for authentication
        webbrowser.open(auth_url)
    
    def _start_callback_server(self, platform: str, config: dict,
                               code_verifier: str, state: str):
        """Start or register an OAuth callback route using the shared callback server.

        This registers a temporary route on the shared `core.callback_server` using
        a path that includes the platform and the generated `state` to avoid
        collisions when multiple flows run concurrently.
        """

        # If shared callback server isn't available, fall back to existing behavior
        if callback_server is None:
            # Fallback: no centralized server available; use existing HTTPServer approach
            def run_server():
                # Minimal blocking behavior - listen on localhost:3000 once
                from http.server import HTTPServer
                OAuthCallbackHandler.auth_code = None
                try:
                    server = HTTPServer(('localhost', 3000), OAuthCallbackHandler)
                    server.timeout = 120
                    server.handle_request()
                    code = getattr(OAuthCallbackHandler, 'auth_code', None)
                    if code:
                        self._exchange_code_for_token(platform, config, code, code_verifier)
                    else:
                        self.auth_failed.emit(platform, "No authorization code received")
                except Exception as e:
                    self.auth_failed.emit(platform, f"Callback server error: {e}")

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            return

        # Use the shared callback server
        path = f"/oauth/{platform}/{state}"
        # Also register a non-state path so providers that redirect to
        # /oauth/<platform>?code=... (without the state segment) are handled.
        path_no_state = f"/oauth/{platform}"
        event = threading.Event()
        container: dict[str, Optional[str]] = {'code': None}

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
                return ("Authentication successful. You may close this window.", 200)
            return ("No code","400")

        try:
            callback_server.register_route(path, _handler, methods=['GET'])
            # Register the base platform path too; some providers (Google) send
            # callbacks to /oauth/<platform> without including our generated state
            # in the path. Registering both ensures we receive the code in either case.
            callback_server.register_route(path_no_state, _handler, methods=['GET'])
            # Start server on configured callback port
            try:
                from core.config import ConfigManager
                cfg = ConfigManager()
                port = int(cfg.get('ngrok.callback_port', 8889))
            except Exception:
                port = 8889

            callback_server.start_server(port)

            # Wait for code with timeout
            got = event.wait(timeout=120)
            # Unregister routes to clean up
            try:
                callback_server.unregister_route(path)
            except Exception:
                pass
            try:
                callback_server.unregister_route(path_no_state)
            except Exception:
                pass

            if got and container.get('code'):
                self._exchange_code_for_token(platform, config, container['code'], code_verifier)
            else:
                self.auth_failed.emit(platform, "No authorization code received")
        except Exception as e:
            self.auth_failed.emit(platform, f"Failed to register callback route: {e}")
    
    def _exchange_code_for_token(self, platform: str, config: dict, 
                                 code: str, code_verifier: str):
        """Exchange authorization code for access token"""
        try:
            import requests
        except Exception:
            requests = None
        
        data = {
            'client_id': config['client_id'],
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code',
            'redirect_uri': config['redirect_uri']
        }
        
        # Add client secret if available
        if 'client_secret' in config:
            data['client_secret'] = config['client_secret']
        
        try:
            response = requests.post(config['token_url'], data=data)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                self.auth_completed.emit(platform, access_token)
            else:
                self.auth_failed.emit(platform, "No access token in response")
                
        except Exception as e:
            self.auth_failed.emit(platform, f"Token exchange failed: {str(e)}")
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier"""
        return secrets.token_urlsafe(64)
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
        return challenge


class SimpleAuthDialog(QDialog):
    """Simple dialog for manual token entry"""
    
    def __init__(self, platform: str, parent=None):
        super().__init__(parent)
        self.platform = platform
        self.token = None
        
        self.setWindowTitle(f"{platform.title()} Authentication")
        self.setModal(True)
        self.resize(500, 200)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        label = QLabel(
            f"<h3>{platform.title()} Authentication</h3>"
            f"<p>Follow these steps to get your token:</p>"
            f"<ol>"
            f"<li>Go to the {platform} developer portal</li>"
            f"<li>Generate an OAuth token with chat permissions</li>"
            f"<li>Paste the token below</li>"
            f"</ol>"
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Token input
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your OAuth token here")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.token_input)
        
        # Buttons
        button = QPushButton("Authenticate")
        button.clicked.connect(self.accept)
        layout.addWidget(button)
        
    def accept(self):
        """Handle dialog acceptance"""
        self.token = self.token_input.text().strip()
        super().accept()
    
    def get_token(self):
        """Get the entered token"""
        return self.token
