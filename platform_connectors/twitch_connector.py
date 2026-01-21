"""
Twitch Platform Connector
Connects to Twitch IRC chat using websockets
"""

import asyncio
import os
import re
import time
import requests
import json
from typing import Optional
from platform_connectors.qt_compat import QThread, pyqtSignal
from platform_connectors.base_connector import BasePlatformConnector
from core.badge_manager import get_badge_manager
import websockets
from core.logger import get_logger
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Structured logger for this module
logger = get_logger('TwitchConnector')


def _make_retry_session(total: int = 3, backoff_factor: float = 1.0):
    """Create a requests.Session with urllib3 Retry configured.

    Returns a session configured to retry on common transient HTTP errors.
    """
    session = requests.Session()
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST", "DELETE", "PUT", "PATCH")
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


class TwitchConnector(BasePlatformConnector):
    """Connector for Twitch chat via IRC"""
    # Singleton instance for streamer connector (non-bot). Bot connectors may be multiple.
    _streamer_instance = None

    def __new__(cls, config=None, is_bot_account=False):
        # If creating a streamer connector and one already exists, return it.
        if not is_bot_account:
            inst = cls._streamer_instance
            if inst is not None:
                try:
                    from core.logger import get_logger
                    _logger = get_logger('TwitchConnector')
                    _logger.debug(f"[TwitchConnector][TRACE] __new__: reusing existing streamer connector id={id(inst)}")
                except Exception:
                    pass
                return inst
        # Otherwise create a fresh instance
        obj = super().__new__(cls)
        if not is_bot_account:
            cls._streamer_instance = obj
        return obj
    
    # Default Twitch credentials
    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = ""
    DEFAULT_ACCESS_TOKEN = "vwjvk83rarr5x8sw4agwgc3ciq09br"
    DEFAULT_REFRESH_TOKEN = "olha5lgahozz0eqhe8me2c1sbkhn9qli9o4wxezitgj96212ul"
    
    def __init__(self, config=None, is_bot_account=False):
        # Avoid re-running __init__ when singleton __new__ returns existing instance.
        # Use object.__getattribute__ to read the flag without invoking PyQt's
        # machinery (which requires QObject.__init__ to have been called).
        try:
            initialized = object.__getattribute__(self, '_initialized')
        except Exception:
            initialized = False

        if initialized:
            try:
                logger.debug(f"[TwitchConnector][TRACE] __init__: skipping re-init for existing connector id={id(self)} is_bot={is_bot_account}")
            except Exception:
                pass
            return

        # First-time init — call superclass init
        super().__init__()
        self.worker_thread = None
        self.worker = None
        self.eventsub_worker_thread = None
        self.eventsub_worker = None
        # Track last worker creation time to avoid rapid duplicate workers
        self._last_worker_created = 0.0
        self.config = config
        self.is_bot_account = is_bot_account
        self.oauth_token = self.DEFAULT_ACCESS_TOKEN
        self.refresh_token = self.DEFAULT_REFRESH_TOKEN
        self.client_id = self.DEFAULT_CLIENT_ID
        self.client_secret = self.DEFAULT_CLIENT_SECRET
        self.username = None
        self.broadcaster_id = None
        # Use separate config sections for bot and streamer
        section = 'bot_refresh_token' if self.is_bot_account else 'streamer_refresh_token'
        if self.config:
            platform_cfg = self.config.get_platform_config('twitch')
            token = platform_cfg.get('oauth_token', '')
            if token:
                self.oauth_token = token
            refresh = platform_cfg.get(section, '')
            if refresh:
                self.refresh_token = refresh
            logger.info(f"[TwitchConnector] refresh set to: {refresh[:20] if refresh else 'None'}...")
            username = platform_cfg.get('username', '')
            if username:
                self.username = username
            # Load client credentials from config if present
            try:
                cid = platform_cfg.get('client_id', '')
                csec = platform_cfg.get('client_secret', '')
                if cid:
                    self.client_id = cid
                if csec:
                    self.client_secret = csec
            except Exception:
                pass
        # Recent local echoes to suppress duplicate incoming IRC echo
        self._recent_local_echoes = []  # list of (message_lower, timestamp)
        # Recent message_id tracking to dedupe messages across workers
        # Maps message_id -> timestamp
        self._recent_message_ids = {}
        # Time window (seconds) to consider a message_id a duplicate
        self._recent_message_window = 30.0
        # Max entries to keep in the recent ids map to avoid unbounded growth
        self._max_recent_message_ids = 10000
        try:
            logger.debug(f"[TwitchConnector][TRACE] __init__: id={id(self)} is_bot={self.is_bot_account} username={self.username}")
        except Exception:
            pass
        # Mark initialized so future __init__ calls (from reused singleton) are no-ops
        try:
            self._initialized = True
        except Exception:
            pass
    
    def set_token(self, token: str):
        """Set OAuth token for authentication"""
        section = 'twitch'  # canonical platform section
        token_prefix = token[:20] if token else "None"
        logger.info(f"[TwitchConnector] set_token called with: {token_prefix}...")
        if token:
            self.oauth_token = token
            logger.info(f"[TwitchConnector] Token updated to: {self.oauth_token[:20]}...")
            if self.config:
                # Persist token under the canonical 'twitch' platform keys.
                if self.is_bot_account:
                    self.config.set_platform_config('twitch', 'bot_token', token)
                else:
                    self.config.set_platform_config('twitch', 'oauth_token', token)
        else:
            # If config is blank, use default
            config_token = self.config.get_platform_config(section).get('oauth_token', '') if self.config else ''
            if not config_token:
                self.oauth_token = self.DEFAULT_ACCESS_TOKEN

    def set_username(self, username: str):
        self.username = username
        # Persist username to config for correct account type (canonical keys)
        if self.config:
            if self.is_bot_account:
                self.config.set_platform_config('twitch', 'bot_username', username)
            else:
                self.config.set_platform_config('twitch', 'username', username)
        # Emit a signal to update the UI if available (for bot or streamer)
        if hasattr(self, 'connection_status'):
            # True means connected, triggers UI update in ConnectionsPage
            self.connection_status.emit(True)
    
    def set_bot_username(self, bot_username: str):
        """Set the bot username for authentication (used when joining a different channel)"""
        self.bot_username = bot_username
    
    def connect(self, username: str):
        """Connect to Twitch chat"""
        # Early-return if already connected to the same channel and worker is running
        try:
            already_connected = getattr(self, 'connected', False)
            same_user = getattr(self, 'username', None) == username
            worker_running = bool(getattr(self, 'worker', None) and getattr(self.worker, 'running', False))
            if already_connected and same_user and worker_running:
                try:
                    logger.debug(f"[TwitchConnector][TRACE] connect: already connected for {username} connector_id={id(self)} worker_id={id(self.worker)} is_bot={self.is_bot_account}")
                except Exception:
                    pass
                return True
        except Exception:
            pass

        # Not already connected (or different username) - ensure prior state cleared
        self.disconnect()
        self.username = username
        
        # Ensure we have a valid token
        if not self.oauth_token or self.oauth_token == "":
            self.oauth_token = self.DEFAULT_ACCESS_TOKEN
        
        # Try to refresh token if needed
        # Bot accounts can refresh using their own refresh token
        if not self.is_bot_account:
            self.refresh_access_token()
        else:
            # Bot account: check if we have a refresh token for the bot
            logger.debug(f"[TwitchConnector] Bot account refresh check: refresh_token={self.refresh_token[:20] if self.refresh_token else 'None'}...")
            if self.refresh_token and self.refresh_token != self.DEFAULT_REFRESH_TOKEN:
                logger.info(f"[TwitchConnector] Bot account has refresh token, attempting refresh...")
                refresh_result = self.refresh_access_token()
                if refresh_result is False:
                    logger.error(f"[TwitchConnector] ⚠️ Bot token refresh failed with invalid token. Connection aborted.")
                    logger.error(f"[TwitchConnector] Bot needs to log out and log back in to get fresh credentials.")
                    return False
            else:
                logger.debug(f"[TwitchConnector] Bot account has no refresh token or using default, skipping refresh")
        
        # Fetch Twitch badges
        try:
            badge_manager = get_badge_manager()
            badge_manager.fetch_twitch_badges(self.client_id, self.oauth_token)
        except Exception as e:
            logger.exception(f"Error fetching badges: {e}")
        
        # Create worker thread for async connection
        # For bot accounts, we might connect to a different channel than our username
        # Use bot_username if set (for bot accounts), otherwise use username (for streamer)
        nick_for_auth = getattr(self, 'bot_username', username)
        logger.info(f"[TwitchConnector] Connecting: channel={username}, nick={nick_for_auth}, has_bot_username={hasattr(self, 'bot_username')}")

        # Connector-level dedupe: avoid creating multiple workers in quick succession
        try:
            now = time.time()
            if now - getattr(self, '_last_worker_created', 0) < 1.0:
                logger.debug(f"[TwitchConnector][TRACE] Skipping worker creation; last created {now - self._last_worker_created:.3f}s ago")
                return
        except Exception:
            pass

        # If a worker object already exists but is not running, prefer to reuse it
        # by wiring it up to a fresh QThread and starting it again rather than
        # allocating a new worker object. This helps preserve any persistent
        # state on the worker and reduces duplicate worker instances during
        # reconnect handoffs.
        try:
            existing_worker = getattr(self, 'worker', None)
            if existing_worker and not getattr(existing_worker, 'running', False):
                try:
                    logger.debug(f"[TwitchConnector][TRACE] Reusing existing worker object id={id(existing_worker)} for connector_id={id(self)}")
                except Exception:
                    pass
                # Ensure connector reference and nick are up-to-date
                try:
                    existing_worker.connector = self
                except Exception:
                    pass

                # Create a fresh thread and move the existing worker into it
                self.worker_thread = QThread()
                existing_worker.moveToThread(self.worker_thread)

                # Wire signals similar to fresh creation
                if not self.is_bot_account:
                    existing_worker.message_signal.connect(self.onMessageReceived)
                    try:
                        existing_worker.set_metadata_callback(self.onMessageReceivedWithMetadata)
                    except Exception:
                        pass
                    existing_worker.set_deletion_callback(self.onMessageDeleted)
                else:
                    logger.info(f"[TwitchConnector] Bot account: skipping incoming message wiring for {nick_for_auth}")

                existing_worker.status_signal.connect(self.onStatusChanged)
                existing_worker.error_signal.connect(self.onError)

                self.worker_thread.started.connect(existing_worker.run)
                self.worker_thread.start()

                try:
                    self._last_worker_created = time.time()
                    logger.debug(f"[TwitchConnector][TRACE] Reused worker started timestamp set to {self._last_worker_created:.3f}")
                except Exception:
                    pass

                # Keep self.worker pointing at the reused worker
                self.worker = existing_worker
                return
        except Exception:
            pass

        # Always use EventSub for incoming chat messages for streamer connectors
        if not self.is_bot_account:
            logger.info(f"[TwitchConnector] Starting EventSub worker for channel chat (streamer): {username}")
            try:
                self.eventsub_worker = TwitchEventSubWorker(
                    self.oauth_token,
                    self.client_id,
                    username
                )
                self.eventsub_worker_thread = QThread()
                self.eventsub_worker.moveToThread(self.eventsub_worker_thread)
                # Wire EventSub signals similar to normal path
                self.eventsub_worker.redemption_signal.connect(self.onRedemption)
                self.eventsub_worker.event_signal.connect(self.onEvent)
                self.eventsub_worker.status_signal.connect(self.onEventSubStatus)
                self.eventsub_worker.error_signal.connect(self.onError)
                try:
                    self.eventsub_worker.reauth_signal.connect(self._on_eventsub_reauth_requested)
                except Exception:
                    pass
                self.eventsub_worker_thread.started.connect(self.eventsub_worker.run)
                self.eventsub_worker_thread.start()
                # Do not create IRC worker for streamer connectors (EventSub handles incoming chat)
                return
            except Exception as e:
                logger.exception(f"[TwitchConnector] Failed to start EventSub worker: {e}")

        # IRC/TwitchWorker removed: we no longer create an IRC worker for incoming or outgoing chat.
        # Incoming chat is provided exclusively via EventSub (started earlier for streamer connectors).
        # Outgoing/bot sends use the Helix REST API in `send_message()` below.
        self.worker = None
        
        # Only start EventSub worker for streamer account
        if not self.is_bot_account:
            logger.info(f"[TwitchConnector] Starting EventSub worker for channel points")
            self.eventsub_worker = TwitchEventSubWorker(
                self.oauth_token,
                self.client_id,
                username
            )
            self.eventsub_worker_thread = QThread()
            self.eventsub_worker.moveToThread(self.eventsub_worker_thread)
            self.eventsub_worker.redemption_signal.connect(self.onRedemption)
            self.eventsub_worker.event_signal.connect(self.onEvent)
            self.eventsub_worker.status_signal.connect(self.onEventSubStatus)
            self.eventsub_worker.error_signal.connect(self.onError)
            # Connect reauth request signal to prompt the user on main thread
            try:
                self.eventsub_worker.reauth_signal.connect(self._on_eventsub_reauth_requested)
            except Exception:
                pass
            self.eventsub_worker_thread.started.connect(self.eventsub_worker.run)
            self.eventsub_worker_thread.start()
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token
        
        Returns:
            True: Token refreshed successfully
            False: Token refresh failed with invalid token (400)
            None: No refresh attempted (no refresh token)
        """
        if not self.refresh_token:
            return None

        # Defensive: ensure client creds present
        # Try to populate client creds from config if missing
        if (not self.client_id or not self.client_secret) and self.config:
            try:
                pcfg = self.config.get_platform_config('twitch') or {}
                if not self.client_id:
                    self.client_id = pcfg.get('client_id', '')
                if not self.client_secret:
                    self.client_secret = pcfg.get('client_secret', '')
            except Exception:
                pass

        if not self.client_id or not self.client_secret:
            logger.warning("[TwitchConnector] Missing client_id or client_secret; cannot refresh token")
            return False

        try:
            # Use a session with retries for transient network issues
            session = requests.Session()
            retries = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("POST",))
            adapter = HTTPAdapter(max_retries=retries)
            session.mount('https://', adapter)
            session.mount('http://', adapter)

            response = session.post(
                'https://id.twitch.tv/oauth2/token',
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Update in-memory tokens
                self.oauth_token = data.get('access_token', self.oauth_token)
                new_refresh = data.get('refresh_token')
                if new_refresh:
                    self.refresh_token = new_refresh

                logger.info("[TwitchConnector] Token refreshed successfully")
                # Restart EventSub worker (if running) so it picks up the refreshed token
                try:
                    if getattr(self, 'eventsub_worker', None):
                        logger.info("[TwitchConnector] Restarting EventSub worker to pick up refreshed token")
                        try:
                            # Use the helper to stop the worker/thread safely
                            self._stop_eventsub_worker(timeout_ms=5000)
                        except Exception as e:
                            logger.exception(f"[TwitchConnector] Error stopping eventsub worker: {e}")

                        # Start a fresh EventSub worker with the new token
                        try:
                            self.eventsub_worker = TwitchEventSubWorker(
                                self.oauth_token,
                                self.client_id,
                                getattr(self, 'username', None)
                            )
                            self.eventsub_worker_thread = QThread()
                            self.eventsub_worker.moveToThread(self.eventsub_worker_thread)
                            self.eventsub_worker.redemption_signal.connect(self.onRedemption)
                            self.eventsub_worker.event_signal.connect(self.onEvent)
                            self.eventsub_worker.status_signal.connect(self.onEventSubStatus)
                            self.eventsub_worker.error_signal.connect(self.onError)
                            try:
                                self.eventsub_worker.reauth_signal.connect(self._on_eventsub_reauth_requested)
                            except Exception:
                                pass
                            self.eventsub_worker_thread.started.connect(self.eventsub_worker.run)
                            self.eventsub_worker_thread.start()
                        except Exception as e:
                            logger.exception(f"[TwitchConnector] Error restarting EventSub worker: {e}")
                except Exception:
                    pass

                # Persist rotated tokens to config for both bot and streamer keys
                try:
                    if self.config:
                        # Primary canonical keys used elsewhere in the app
                        if self.is_bot_account:
                            self.config.set_platform_config('twitch', 'bot_token', self.oauth_token)
                            self.config.set_platform_config('twitch', 'bot_refresh_token', self.refresh_token)
                        else:
                            self.config.set_platform_config('twitch', 'oauth_token', self.oauth_token)
                            self.config.set_platform_config('twitch', 'streamer_refresh_token', self.refresh_token)
                except Exception as e:
                    logger.warning(f"[TwitchConnector] Warning: failed to persist refreshed token: {e}")

                return True
            elif response.status_code == 400:
                # Invalid refresh token (common when rotation happened elsewhere)
                logger.warning("⚠️ Token refresh failed: Invalid refresh token")
                logger.debug(f"[DEBUG] Refresh token used: {self.refresh_token}")
                logger.debug(f"Response: {response.text}")
                return False
            else:
                logger.error(f"[TwitchConnector] Token refresh failed: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                # Treat non-400 failures as transient so caller can decide
                return None

        except requests.exceptions.RequestException as e:
            # Network-level/transient failure - do not treat as invalid token
            logger.exception(f"[TwitchConnector] Network error refreshing token: {e}")
            return None
        except Exception as e:
            logger.exception(f"[TwitchConnector] Error refreshing token: {e}")
            return None

    def _on_eventsub_reauth_requested(self, oauth_url: str):
        """Handle EventSub worker request to re-authorize the app.

        Shows a confirmation dialog to the user on the main thread; opens the
        provided `oauth_url` in the browser if the user accepts.
        """
        try:
            from PyQt6.QtWidgets import QMessageBox
            import webbrowser

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Re-authorize Twitch for EventSub")
            msg.setText("AudibleZenBot needs additional Twitch permissions to receive Channel Points, Cheers, and Follower events.")
            msg.setInformativeText("Click 'Re-authorize' to open Twitch and grant the required permissions.")
            reauth_btn = msg.addButton("Re-authorize", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(reauth_btn)
            msg.exec()

            if msg.clickedButton() == reauth_btn:
                try:
                    # Start a lightweight temporary local HTTP server on localhost:8888
                    # to accept the OAuth redirect. Run in a daemon thread so it
                    # doesn't block the UI. The handler will shut the server down
                    # after serving one request.
                    import threading
                    from http.server import HTTPServer, BaseHTTPRequestHandler

                    # Capture parent connector for use inside handler
                    parent_connector = self

                    class _OneShotHandler(BaseHTTPRequestHandler):
                        def do_GET(self):
                            from urllib.parse import urlparse, parse_qs
                            qs = parse_qs(urlparse(self.path).query)
                            code = qs.get('code', [None])[0]

                            # Default: respond to browser so user isn't left waiting
                            def _respond(status, body_bytes):
                                try:
                                    self.send_response(status)
                                    self.send_header('Content-type', 'text/html')
                                    self.end_headers()
                                    self.wfile.write(body_bytes)
                                except Exception:
                                    pass

                            try:
                                if not code:
                                    _respond(200, b'<html><body><h1>No authorization code found.</h1></body></html>')
                                    return

                                # Exchange authorization code for tokens
                                redirect_uri = 'http://localhost:8888/callback'
                                try:
                                    session = requests.Session()
                                    resp = session.post(
                                        'https://id.twitch.tv/oauth2/token',
                                        data={
                                            'client_id': parent_connector.client_id,
                                            'client_secret': parent_connector.client_secret,
                                            'grant_type': 'authorization_code',
                                            'code': code,
                                            'redirect_uri': redirect_uri
                                        },
                                        timeout=10
                                    )
                                except requests.exceptions.RequestException:
                                    _respond(500, b'<html><body><h1>Authorization error.</h1></body></html>')
                                    return

                                if resp.status_code != 200:
                                    _respond(500, b'<html><body><h1>Authorization failed.</h1><p>Could not exchange code for tokens.</p></body></html>')
                                    return

                                data = resp.json()
                                # Update connector tokens in-memory
                                parent_connector.oauth_token = data.get('access_token', parent_connector.oauth_token)
                                new_refresh = data.get('refresh_token')
                                if new_refresh:
                                    parent_connector.refresh_token = new_refresh

                                # Persist rotated tokens to config
                                try:
                                    if getattr(parent_connector, 'config', None):
                                        if getattr(parent_connector, 'is_bot_account', False):
                                            parent_connector.config.set_platform_config('twitch', 'bot_token', parent_connector.oauth_token)
                                            parent_connector.config.set_platform_config('twitch', 'bot_refresh_token', parent_connector.refresh_token)
                                        else:
                                            parent_connector.config.set_platform_config('twitch', 'oauth_token', parent_connector.oauth_token)
                                            parent_connector.config.set_platform_config('twitch', 'streamer_refresh_token', parent_connector.refresh_token)
                                except Exception:
                                    pass

                                _respond(200, b'<html><body><h1>Authorization complete.</h1><p>You may close this window and return to AudibleZenBot.</p></body></html>')

                                # Restart EventSub worker so it picks up refreshed token
                                try:
                                    # Stop existing worker if present using helper
                                    try:
                                        parent_connector._stop_eventsub_worker(timeout_ms=5000)
                                    except Exception:
                                        logger.exception("[TwitchConnector] Error stopping parent eventsub worker from callback handler")

                                    # Start fresh worker
                                    try:
                                        parent_connector.eventsub_worker = TwitchEventSubWorker(
                                            parent_connector.oauth_token,
                                            parent_connector.client_id,
                                            getattr(parent_connector, 'username', None)
                                        )
                                        parent_connector.eventsub_worker_thread = QThread()
                                        parent_connector.eventsub_worker.moveToThread(parent_connector.eventsub_worker_thread)
                                        parent_connector.eventsub_worker.redemption_signal.connect(parent_connector.onRedemption)
                                        parent_connector.eventsub_worker.event_signal.connect(parent_connector.onEvent)
                                        parent_connector.eventsub_worker.status_signal.connect(parent_connector.onEventSubStatus)
                                        parent_connector.eventsub_worker.error_signal.connect(parent_connector.onError)
                                        try:
                                            parent_connector.eventsub_worker.reauth_signal.connect(parent_connector._on_eventsub_reauth_requested)
                                        except Exception:
                                            pass
                                        parent_connector.eventsub_worker_thread.started.connect(parent_connector.eventsub_worker.run)
                                        parent_connector.eventsub_worker_thread.start()
                                    except Exception:
                                        logger.exception("[TwitchConnector] Error starting parent eventsub worker from callback handler")
                                except Exception:
                                    logger.exception("[TwitchConnector] Unexpected error restarting parent eventsub worker from callback handler")

                            finally:
                                # Ensure server shuts down after handling
                                try:
                                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                                except Exception:
                                    pass

                        def log_message(self, format, *args):
                            return

                    try:
                        server = HTTPServer(('localhost', 8888), _OneShotHandler)
                        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                        server_thread.start()
                        logger.info("[EventSub] Started temporary local OAuth callback server on port 8888")
                    except OSError as e:
                        logger.warning(f"[EventSub] Could not start temporary callback server on port 8888: {e}")
                        server = None

                    try:
                        webbrowser.open(oauth_url)
                        logger.info("[EventSub] Opened browser for re-authorization")
                    except Exception as e:
                        logger.exception(f"[EventSub] Failed to open browser: {e}")
                except Exception as e:
                    logger.exception(f"[TwitchConnector] Error launching re-auth browser/server: {e}")
        except Exception as e:
            logger.exception(f"[TwitchConnector] Error showing re-auth dialog: {e}")
        
        try:
            # Use a session with retries to be resilient to transient network issues
            session = requests.Session()
            retries = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("POST",))
            adapter = HTTPAdapter(max_retries=retries)
            session.mount('https://', adapter)
            session.mount('http://', adapter)

            response = session.post(
                'https://id.twitch.tv/oauth2/token',
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token', self.oauth_token)
                new_refresh = data.get('refresh_token')
                if new_refresh:
                    self.refresh_token = new_refresh
                logger.info(f"Twitch token refreshed successfully")
                # Restart EventSub worker (if running) so it picks up the refreshed token
                try:
                    if getattr(self, 'eventsub_worker', None):
                        logger.info("[TwitchConnector] Restarting EventSub worker to pick up refreshed token")
                        try:
                            self._stop_eventsub_worker(timeout_ms=5000)
                        except Exception as e:
                            logger.exception(f"[TwitchConnector] Error stopping eventsub worker: {e}")

                        try:
                            self.eventsub_worker = TwitchEventSubWorker(
                                self.oauth_token,
                                self.client_id,
                                getattr(self, 'username', None)
                            )
                            self.eventsub_worker_thread = QThread()
                            self.eventsub_worker.moveToThread(self.eventsub_worker_thread)
                            self.eventsub_worker.redemption_signal.connect(self.onRedemption)
                            self.eventsub_worker.event_signal.connect(self.onEvent)
                            self.eventsub_worker.status_signal.connect(self.onEventSubStatus)
                            self.eventsub_worker.error_signal.connect(self.onError)
                            try:
                                self.eventsub_worker.reauth_signal.connect(self._on_eventsub_reauth_requested)
                            except Exception:
                                pass
                            self.eventsub_worker_thread.started.connect(self.eventsub_worker.run)
                            self.eventsub_worker_thread.start()
                        except Exception as e:
                            logger.exception(f"[TwitchConnector] Error restarting EventSub worker: {e}")
                except Exception:
                    pass
                return True
            elif response.status_code == 400:
                logger.warning(f"⚠️ Token refresh failed: Invalid refresh token")
                logger.debug(f"[DEBUG] Refresh token used: {self.refresh_token}")
                logger.debug(f"Response: {response.text}")
                return False
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error refreshing token (network): {e}")
            return None
        except Exception as e:
            logger.exception(f"Error refreshing token: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from Twitch"""
        try:
            logger.debug(f"[TwitchConnector][TRACE] disconnect called: connector_id={id(self)} worker_id={id(self.worker) if getattr(self, 'worker', None) is not None else None} connected={getattr(self, 'connected', False)} is_bot={getattr(self, 'is_bot_account', False)}")
        except Exception:
            pass
        if self.worker:
            try:
                self.worker.stop()
            except Exception as e:
                logger.exception(f"[TwitchConnector] Error stopping worker: {e}")
        if self.worker_thread:
            try:
                if self.worker_thread.isRunning():
                    self.worker_thread.quit()
                    self.worker_thread.wait(5000)  # Wait up to 5 seconds
                    if self.worker_thread.isRunning():
                        logger.warning(f"[TwitchConnector] Warning: Worker thread did not stop in time. Forcing terminate()")
                        self.worker_thread.terminate()
                        self.worker_thread.wait(2000)  # Wait up to 2 seconds after terminate
                        if self.worker_thread.isRunning():
                            logger.error(f"[TwitchConnector] Error: Worker thread still running after terminate()")
            except Exception as e:
                logger.exception(f"[TwitchConnector] Error stopping worker thread: {e}")
        if self.eventsub_worker:
            try:
                self.eventsub_worker.stop()
            except Exception as e:
                logger.exception(f"[TwitchConnector] Error stopping eventsub worker: {e}")
        if self.eventsub_worker_thread:
            try:
                self.eventsub_worker_thread.quit()
                self.eventsub_worker_thread.wait()
            except Exception as e:
                logger.exception(f"[TwitchConnector] Error stopping eventsub worker thread: {e}")
        self.connected = False
        self.connection_status.emit(False)
        self.worker = None
        self.worker_thread = None
        self.eventsub_worker = None
        self.eventsub_worker_thread = None
        try:
            logger.debug(f"[TwitchConnector][TRACE] disconnected: connector_id={id(self)}")
        except Exception:
            pass
    
    def _stop_eventsub_worker(self, timeout_ms: int = 5000):
        """Safely stop the EventSub worker and its thread.

        Attempts a graceful `quit()` + `wait()` on the QThread and falls
        back to `terminate()` if the thread doesn't stop within `timeout_ms`.
        Clears references to the worker and thread on completion.
        """
        try:
            # Ask worker to stop first (worker.stop should be idempotent)
            if getattr(self, 'eventsub_worker', None):
                try:
                    self.eventsub_worker.stop()
                except Exception:
                    logger.exception("[TwitchConnector] Exception while stopping eventsub_worker")

            # Then stop the thread cleanly
            if getattr(self, 'eventsub_worker_thread', None):
                try:
                    if self.eventsub_worker_thread.isRunning():
                        self.eventsub_worker_thread.quit()
                        self.eventsub_worker_thread.wait(timeout_ms)
                        if self.eventsub_worker_thread.isRunning():
                            logger.warning("[TwitchConnector] EventSub thread did not stop in time; forcing terminate()")
                            self.eventsub_worker_thread.terminate()
                            self.eventsub_worker_thread.wait(2000)
                            if self.eventsub_worker_thread.isRunning():
                                logger.error("[TwitchConnector] EventSub thread still running after terminate()")
                except Exception:
                    logger.exception("[TwitchConnector] Exception while stopping eventsub_worker_thread")

            # Clear references so a fresh worker can be created
            self.eventsub_worker = None
            self.eventsub_worker_thread = None
        except Exception:
            logger.exception("[TwitchConnector] Unexpected error while stopping EventSub worker")
    def send_message(self, message: str):
        """Send a message to Twitch chat"""
        logger.debug(f"[TwitchConnector] send_message called via REST API: message={message[:50]}")

        # Ensure we have broadcaster ID cached
        try:
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {self.oauth_token}'
            }

            # Get broadcaster ID if not cached
            if not hasattr(self, 'broadcaster_id') or not self.broadcaster_id:
                if not getattr(self, 'username', None):
                    logger.warning("[TwitchConnector] Cannot send message: missing connector username (broadcaster login)")
                    return False
                session = _make_retry_session()
                try:
                    user_response = session.get(
                        'https://api.twitch.tv/helix/users',
                        headers=headers,
                        params={'login': self.username},
                        timeout=10
                    )
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[Twitch] Network error fetching broadcaster ID: {e}")
                    return False

                if user_response.status_code == 200:
                    users = user_response.json().get('data', [])
                    if users:
                        self.broadcaster_id = users[0]['id']
                        logger.info(f"[Twitch] Cached broadcaster_id: {self.broadcaster_id}")
                    else:
                        logger.warning(f"[Twitch] Could not find user ID for {self.username}")
                        return False
                else:
                    logger.error(f"[Twitch] Failed to get broadcaster ID: {user_response.status_code}")
                    return False

            # Determine moderator_id: prefer bot username if available (for bot connectors)
            moderator_id = self.broadcaster_id
            try:
                if self.is_bot_account:
                    bot_login = getattr(self, 'bot_username', None) or getattr(self, 'username', None)
                    if bot_login and bot_login.lower() != getattr(self, 'username', '').lower():
                        session = _make_retry_session()
                        try:
                            bot_resp = session.get(
                                'https://api.twitch.tv/helix/users',
                                headers=headers,
                                params={'login': bot_login},
                                timeout=10
                            )
                        except requests.exceptions.RequestException:
                            bot_resp = None
                        if bot_resp and bot_resp.status_code == 200:
                            bdata = bot_resp.json().get('data', [])
                            if bdata:
                                moderator_id = bdata[0]['id']
                # Fallback: moderator_id stays as broadcaster_id
            except Exception:
                pass

            # Send chat message via Helix API
            session = _make_retry_session()
            try:
                resp = session.post(
                    'https://api.twitch.tv/helix/chat/messages',
                    headers=headers,
                    params={
                        'broadcaster_id': self.broadcaster_id,
                        'moderator_id': moderator_id
                    },
                    json={'content': message},
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Twitch] Network error sending chat message: {e}")
                return False

            if resp.status_code in (200, 201, 204):
                logger.info(f"[Twitch] Message sent via Helix API: {message[:50]}")
                return True
            else:
                logger.error(f"[Twitch] Failed to send message: {resp.status_code} - {resp.text}")
                return False

        except Exception as e:
            logger.exception(f"[TwitchConnector] send_message error: {e}")
            return False
    
    def delete_message(self, message_id: str):
        """Delete a message from Twitch chat"""
        if not message_id:
            return
        
        try:
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {self.oauth_token}'
            }
            
            # Get broadcaster ID if not cached
            if not hasattr(self, 'broadcaster_id') or not self.broadcaster_id:
                # Fetch broadcaster ID from username
                try:
                    session = _make_retry_session()
                    user_response = session.get(
                        'https://api.twitch.tv/helix/users',
                        headers=headers,
                        params={'login': self.username},
                        timeout=10
                    )
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[Twitch] Network error fetching broadcaster ID: {e}")
                    return

                if user_response.status_code == 200:
                    users = user_response.json().get('data', [])
                    if users:
                        self.broadcaster_id = users[0]['id']
                        logger.info(f"[Twitch] Cached broadcaster_id: {self.broadcaster_id}")
                    else:
                        logger.warning(f"[Twitch] Could not find user ID for {self.username}")
                        return
                else:
                    logger.error(f"[Twitch] Failed to get broadcaster ID: {user_response.status_code}")
                    return
            
            # Delete message via Twitch API
            try:
                session = _make_retry_session()
                response = session.delete(
                    f'https://api.twitch.tv/helix/moderation/chat',
                    headers=headers,
                    params={
                        'broadcaster_id': self.broadcaster_id,
                        'moderator_id': self.broadcaster_id,
                        'message_id': message_id
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Twitch] Network error deleting message: {e}")
                return False
            
            if response.status_code == 204:
                logger.info(f"[Twitch] Message deleted: {message_id}")
                return True
            else:
                logger.error(f"[Twitch] Failed to delete message: {response.status_code}")
                logger.debug(f"[Twitch] Response body: {response.text}")
                logger.debug(f"[Twitch] Broadcaster ID: {self.broadcaster_id}")
                return False
        except Exception as e:
            logger.exception(f"[Twitch] Error deleting message: {e}")
            return False
    
    def get_custom_reward(self, reward_id: str):
        """Fetch custom reward details from Twitch API"""
        try:
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {self.oauth_token}'
            }

            # Get broadcaster ID if not cached
            if not getattr(self, 'broadcaster_id', None):
                # Fetch broadcaster ID from username
                try:
                    session = _make_retry_session()
                    user_response = session.get(
                        'https://api.twitch.tv/helix/users',
                        headers=headers,
                        params={'login': self.username},
                        timeout=10
                    )
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[Twitch] Network error fetching broadcaster ID: {e}")
                    return None

                if user_response.status_code == 200:
                    users = user_response.json().get('data', [])
                    if users:
                        self.broadcaster_id = users[0]['id']
                    else:
                        logger.warning(f"[Twitch] No user found for login: {self.username}")
                        return None
                else:
                    logger.error(f"[Twitch] Failed to get broadcaster ID: {user_response.status_code}")
                    return None

            # Fetch custom reward details
            try:
                session = _make_retry_session()
                response = session.get(
                    'https://api.twitch.tv/helix/channel_points/custom_rewards',
                    headers=headers,
                    params={
                        'broadcaster_id': self.broadcaster_id,
                        'id': reward_id
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Twitch] Network error fetching custom reward: {e}")
                return None

            if response.status_code == 200:
                rewards = response.json().get('data', [])
                if rewards:
                    reward = rewards[0]
                    return {
                        'title': reward.get('title', 'Unknown Reward'),
                        'cost': reward.get('cost', 0)
                    }
                else:
                    logger.warning(f"[Twitch] No reward found for ID: {reward_id}")
                    return None
            else:
                logger.error(f"[Twitch] Failed to fetch reward: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.exception(f"[Twitch] Error fetching custom reward: {e}")
            return None
    
    def ban_user(self, username: str, user_id: Optional[str] = None):
        """Ban a user from Twitch chat"""
        if not username:
            return
        
        try:
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {self.oauth_token}',
                'Content-Type': 'application/json'
            }
            
            # Get user ID if not provided
            if not user_id:
                try:
                    session = _make_retry_session()
                    user_response = session.get(
                        'https://api.twitch.tv/helix/users',
                        headers=headers,
                        params={'login': username},
                        timeout=10
                    )
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[Twitch] Network error fetching user ID for ban: {e}")
                    return
                if user_response.status_code == 200:
                        users = user_response.json().get('data', [])
                        if users:
                            user_id = users[0]['id']
            
            if not user_id:
                logger.warning(f"[Twitch] Could not find user ID for {username}")
                return
            
            # Get broadcaster ID if not cached
            if not hasattr(self, 'broadcaster_id') or not self.broadcaster_id:
                # Fetch broadcaster ID from username
                try:
                    session = _make_retry_session()
                    broadcaster_response = session.get(
                        'https://api.twitch.tv/helix/users',
                        headers=headers,
                        params={'login': self.username},
                        timeout=10
                    )
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[Twitch] Network error fetching broadcaster ID for ban: {e}")
                    return
                if broadcaster_response.status_code == 200:
                    users = broadcaster_response.json().get('data', [])
                    if users:
                        self.broadcaster_id = users[0]['id']
                        logger.info(f"[Twitch] Cached broadcaster_id: {self.broadcaster_id}")
                    else:
                        logger.warning(f"[Twitch] Could not find broadcaster ID for {self.username}")
                        return
                else:
                    logger.error(f"[Twitch] Failed to get broadcaster ID: {broadcaster_response.status_code}")
                    return
            
            # Ban user via Twitch API
            try:
                session = _make_retry_session()
                response = session.post(
                    'https://api.twitch.tv/helix/moderation/bans',
                    headers=headers,
                    json={
                        'data': {
                            'user_id': user_id,
                            'broadcaster_id': self.broadcaster_id,
                            'moderator_id': self.broadcaster_id
                        }
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Twitch] Network error banning user: {e}")
                return
            if response.status_code == 200:
                logger.info(f"[Twitch] User banned: {username}")
            else:
                logger.error(f"[Twitch] Failed to ban user: {response.status_code}")
        except Exception as e:
            logger.exception(f"[Twitch] Error banning user: {e}")
    
    def onMessageReceived(self, username: str, message: str):
        """Handle received message"""
        self.message_received.emit('twitch', username, message, {})
    
    def onMessageReceivedWithMetadata(self, username: str, message: str, metadata: dict):
        """Handle received message with metadata"""
        # Suppress incoming IRC echo that matches a recent local echo (sent by this streamer)
        try:
            now = time.time()
            msg_l = message.strip().lower() if message else ''
            for m, ts in list(self._recent_local_echoes):
                if m == msg_l and (now - ts) < 5.0:
                    logger.debug(f"[TwitchConnector][TRACE] Suppressing incoming IRC echo matching local echo: {message}")
                    try:
                        self._recent_local_echoes.remove((m, ts))
                    except Exception:
                        pass
                    return
            # prune old entries
            self._recent_local_echoes = [(m, t) for (m, t) in self._recent_local_echoes if (now - t) < 10.0]
            # Connector-level dedupe by message_id to avoid duplicate delivery
            try:
                msg_id = None
                if metadata:
                    msg_id = metadata.get('message_id') or metadata.get('id')
                if msg_id:
                    prev_ts = self._recent_message_ids.get(msg_id)
                    if prev_ts and (now - prev_ts) < self._recent_message_window:
                        logger.debug(f"[TwitchConnector][TRACE] Suppressing duplicate message_id={msg_id} age={now-prev_ts:.3f}s")
                        return
                    # record this id
                    try:
                        self._recent_message_ids[msg_id] = now
                        # prune oldest entries if map grows too large
                        if len(self._recent_message_ids) > self._max_recent_message_ids:
                            # remove oldest 10%
                            items = sorted(self._recent_message_ids.items(), key=lambda kv: kv[1])
                            for k, _ in items[: max(1, len(items)//10)]:
                                try:
                                    del self._recent_message_ids[k]
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
        logger.debug(f"[TwitchConnector] onMessageReceivedWithMetadata: {username}, {message}, {metadata}")
        # TRACE: explicit incoming trace for debugging send vs receive timing
        try:
            logger.debug(f"[TwitchConnector][TRACE][INCOMING] username={username} message_preview={message[:120]} metadata_keys={list(metadata.keys())}")
        except Exception:
            logger.debug("[TwitchConnector][TRACE][INCOMING] failed to print metadata preview")
        # Diagnostic: emitter instance id
        try:
            logger.debug(f"[TwitchConnector][TRACE][EMITTER] id={id(self)} username_attr={getattr(self, 'username', None)} is_bot={getattr(self, 'is_bot_account', False)}")
        except Exception:
            pass
        # Persistent diagnostic log to ensure messages are recorded even if stdout is lost
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            diag_file = os.path.join(log_dir, 'connector_incoming.log')
            with open(diag_file, 'a', encoding='utf-8', errors='replace') as df:
                df.write(f"{time.time():.3f} connector_id={id(self)} username={username} message_preview={repr(message)[:200]} metadata_keys={list(metadata.keys())}\n")
        except Exception:
            pass
        self.message_received_with_metadata.emit('twitch', username, message, metadata)

    
    def onMessageDeleted(self, message_id: str):
        """Handle message deletion event from platform"""
        logger.info(f"[TwitchConnector] Message deleted by platform/moderator: {message_id}")
        self.message_deleted.emit('twitch', message_id)
    
    def onRedemption(self, username: str, reward_title: str, reward_cost: int, user_input: str):
        """Handle channel points redemption from EventSub"""
        import datetime
        logger.info(f"[TwitchConnector] Redemption: {username} redeemed {reward_title} ({reward_cost} points)")
        
        # Format message
        if user_input:
            message = f"🌟 redeemed {reward_title} ({reward_cost} points) - \"{user_input}\""
        else:
            message = f"🌟 redeemed {reward_title} ({reward_cost} points)"
        
        # Create metadata
        metadata = {
            'timestamp': datetime.datetime.now(),
            'event_type': 'redemption',
            'color': None,
            'badges': [],
            'message_id': None,
            'reward_title': reward_title,
            'reward_cost': reward_cost
        }
        
        self.message_received_with_metadata.emit('twitch', username, message, metadata)
    
    def onEvent(self, event_type: str, username: str, event_data: dict):
        """Handle general EventSub events"""
        import datetime
        logger.info(f"[TwitchConnector] Event: {event_type} - {username}")
        
        # Format message based on event type
        if event_type == 'stream.online':
            message = f"📡 went live!"
            username = event_data.get('broadcaster_name', username)
        elif event_type == 'follow':
            message = f"💜 followed the channel"
        elif event_type == 'subscribe':
            tier = event_data.get('tier', '1000')
            tier_name = {'1000': 'Tier 1', '2000': 'Tier 2', '3000': 'Tier 3'}.get(tier, 'Tier 1')
            is_gift = event_data.get('is_gift', False)
            if is_gift:
                message = f"⭐ received a gifted subscription ({tier_name})"
            else:
                message = f"⭐ subscribed ({tier_name})"
        elif event_type == 'gift':
            tier = event_data.get('tier', '1000')
            tier_name = {'1000': 'Tier 1', '2000': 'Tier 2', '3000': 'Tier 3'}.get(tier, 'Tier 1')
            total = event_data.get('total', 1)
            cumulative = event_data.get('cumulative_total')
            if total == 1:
                message = f"🎁 gifted a subscription ({tier_name})"
            else:
                message = f"🎁 gifted {total} subscriptions ({tier_name})"
            if cumulative:
                message += f" [Total: {cumulative}]"
        elif event_type == 'cheer':
            bits = event_data.get('bits', 0)
            cheer_message = event_data.get('message', '')
            if cheer_message:
                message = f"💎 cheered {bits} bits - \"{cheer_message}\""
            else:
                message = f"💎 cheered {bits} bits"
        else:
            message = f"Event: {event_type}"
        
        # Create metadata
        metadata = {
            'timestamp': datetime.datetime.now(),
            'event_type': event_type,
            'color': None,
            'badges': [],
            'message_id': None
        }
        metadata.update(event_data)
        
        self.message_received_with_metadata.emit('twitch', username, message, metadata)
    
    def onEventSubStatus(self, connected: bool):
        """Handle EventSub connection status"""
        logger.info(f"[TwitchConnector] EventSub connected: {connected}")
    
    def onStatusChanged(self, connected: bool):
        """Handle connection status change"""
        self.connected = connected
        self.connection_status.emit(connected)
    
    def onError(self, error: str):
        """Handle error"""
        self.error_occurred.emit(error)


class TwitchWorker(QThread):
    """Worker thread for Twitch IRC connection"""
    
    message_signal = pyqtSignal(str, str)  # username, message
    status_signal = pyqtSignal(bool)  # connected
    error_signal = pyqtSignal(str)  # error

    def set_metadata_callback(self, callback):
        self._metadata_callback = callback
        try:
            logger.debug(f"[TwitchWorker][TRACE] set_metadata_callback: worker_id={id(self)} connector_id={id(getattr(self, 'connector', None))} callback_set={callback is not None}")
        except Exception:
            pass
    
    def set_deletion_callback(self, callback):
        """Set callback for message deletion events"""
        self._deletion_callback = callback
    
    IRC_SERVER = 'wss://irc-ws.chat.twitch.tv:443'
    
    def __init__(self, channel: str, oauth_token: Optional[str] = None, 
                 client_id: Optional[str] = None, refresh_token: Optional[str] = None,
                 client_secret: Optional[str] = None, nick: Optional[str] = None, connector=None):
        super().__init__()
        self.channel = channel.lower()
        self.oauth_token = oauth_token
        self.client_id = client_id
        self.refresh_token = refresh_token
        self.client_secret = client_secret
        self.connector = connector  # Reference to connector for API calls
        # Initialize callbacks to known defaults to avoid attribute errors
        self._metadata_callback = None
        self._deletion_callback = None
        # When True, allow this worker to forward parsed messages to a streamer handler
        # (used when a bot connector is explicitly wired to a streamer connector)
        self._forward_to_streamer = False
        # If a connector was provided and appears to be a streamer connector,
        # attach its metadata callback as a safe fallback in case connect()
        # did not explicitly call `set_metadata_callback` (race / reconnection path).
        try:
            if self.connector and hasattr(self.connector, 'onMessageReceivedWithMetadata') and not getattr(self.connector, 'is_bot_account', False):
                self._metadata_callback = getattr(self.connector, 'onMessageReceivedWithMetadata')
                logger.debug(f"[TwitchWorker][TRACE] __init__: worker_id={id(self)} auto-attached metadata_callback to connector_id={id(self.connector)}")
        except Exception:
            pass
        self.running = False
        self.ws = None
        self.loop = None
        # Use provided nick or fallback to channel name
        self.bot_nick = nick.lower() if nick else channel.lower()
        self.last_token_refresh = time.time()
        
        # Message reliability features
        self.seen_message_ids = set()  # Track processed messages
        self.max_seen_ids = 10000  # Prevent unbounded growth
        self.last_message_time = None  # For health monitoring
        # Timestamp of last successfully parsed PRIVMSG (seconds since epoch)
        # Used to allow a short grace period to flush parsed messages before reconnecting
        self._last_parsed_time = None
        self.connection_timeout = 300  # 5 minutes
        # Guard to avoid printing authentication success multiple times per worker
        self._auth_printed = False
    
    def run(self):
        """Run the Twitch IRC connection"""
        self.running = True
        
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # Always try real connection (we have default credentials)
            self.loop.run_until_complete(self.connect_to_twitch())
        except Exception as e:
            self.error_signal.emit(f"Connection error: {str(e)}")
            self.status_signal.emit(False)
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()
    
    async def connect_to_twitch(self):
        """Connect to Twitch IRC via WebSocket with unlimited retry"""
        retry_count = 0
        
        while self.running:
            try:
                async with websockets.connect(self.IRC_SERVER) as websocket:
                    self.ws = websocket
                    retry_count = 0  # Reset on successful connection
                    
                    # Authenticate
                    await self.authenticate()
                    
                    # Join channel
                    await websocket.send(f'JOIN #{self.channel}')
                    
                    self.status_signal.emit(True)
                    logger.info(f"Connected to Twitch channel: {self.channel}")
                    
                    # Start health monitoring
                    health_task = asyncio.create_task(self.health_check_loop(websocket))
                    
                    # Listen for messages with buffer for partial messages
                    last_refresh_check = time.time()
                    message_buffer = ''  # Buffer for partial IRC messages
                    messages_received = 0
                    messages_parsed = 0
                    
                    while self.running:
                        try:
                            # Check if token needs refresh (every 30 minutes)
                            if time.time() - last_refresh_check > 1800:
                                await self.refresh_token_if_needed()
                                last_refresh_check = time.time()
                            
                            raw_data = await asyncio.wait_for(
                                websocket.recv(), 
                                timeout=1.0
                            )
                            self.last_message_time = time.time()  # Update health timestamp
                            messages_received += 1
                            # Optional raw IRC logging for diagnostics. Enable by setting
                            # environment variable AZB_RAW_IRC_LOG=1 before launching the app.
                            try:
                                if os.environ.get('AZB_RAW_IRC_LOG') == '1':
                                    log_dir = os.path.join(os.getcwd(), 'logs')
                                    os.makedirs(log_dir, exist_ok=True)
                                    fname = os.path.join(log_dir, f"raw_irc_{self.channel}.log")
                                    with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                                        f.write(f"{self.last_message_time:.3f} worker={id(self)} {repr(raw_data)}\n")
                            except Exception:
                                pass
                            
                            # IRC messages can arrive concatenated or split
                            # Add to buffer and process complete messages
                            message_buffer += raw_data
                            
                            # Split by line breaks (IRC standard)
                            while '\r\n' in message_buffer:
                                message, message_buffer = message_buffer.split('\r\n', 1)
                                if message.strip():  # Only process non-empty
                                    await self.handle_message(message)
                                    messages_parsed += 1
                            
                            # Log stats periodically
                            if messages_received % 100 == 0:
                                logger.debug(f"[Twitch Stats] Received: {messages_received}, Parsed: {messages_parsed}, Buffer size: {len(message_buffer)}")
                            
                        except asyncio.TimeoutError:
                            continue
                        except websockets.ConnectionClosed:
                            logger.info(f"[Twitch] Connection closed. Stats - Received: {messages_received}, Parsed: {messages_parsed}")
                            break
                    
                    # Cancel health monitoring
                    health_task.cancel()
                    try:
                        await health_task
                    except asyncio.CancelledError:
                        pass
                    
                    # If we exit cleanly, don't retry
                    if not self.running:
                        break
                            
            except Exception as e:
                retry_count += 1
                wait_time = min(2 ** retry_count, 300)  # Cap at 5 minutes
                self.error_signal.emit(f"WebSocket error (attempt {retry_count}): {str(e)}")
                if self.running:
                    logger.info(f"Retrying Twitch connection in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    break
                    
        self.status_signal.emit(False)
        self.ws = None
        # Also update the connector directly in case Qt signal delivery is
        # not active (headless or non-Qt test runners).
        try:
            if self.connector:
                try:
                    self.connector.connected = False
                except Exception:
                    pass
                try:
                    self.connector.connection_status.emit(False)
                except Exception:
                    pass
        except Exception:
            pass
    
    async def refresh_token_if_needed(self):
        """Refresh token during active connection"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return
        
        try:
            # Use a short-lived session with retries to avoid transient failures
            session = requests.Session()
            retries = Retry(total=2, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("POST",))
            adapter = HTTPAdapter(max_retries=retries)
            session.mount('https://', adapter)
            session.mount('http://', adapter)

            response = session.post(
                'https://id.twitch.tv/oauth2/token',
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token', self.oauth_token)
                new_refresh = data.get('refresh_token')
                if new_refresh:
                    self.refresh_token = new_refresh
                logger.info("Token refreshed during connection")
        except Exception as e:
            logger.exception(f"Error refreshing token: {e}")
    
    async def health_check_loop(self, websocket):
        """Monitor connection health and force reconnect if dead"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.last_message_time:
                    time_since_last = time.time() - self.last_message_time
                    
                    if time_since_last > self.connection_timeout:
                        logger.warning(f"[Twitch] Connection appears dead ({int(time_since_last)}s since last message)")
                        logger.info(f"[Twitch] Forcing reconnection...")
                        # If we parsed a message very recently, give a short grace
                        try:
                            grace = 1.5
                            if self._last_parsed_time:
                                since_parsed = time.time() - self._last_parsed_time
                                if since_parsed < grace:
                                    wait = grace - since_parsed
                                    logger.debug(f"[Twitch] Recent parsed message (\n{since_parsed:.3f}s ago); waiting {wait:.3f}s to flush before reconnect")
                                    await asyncio.sleep(wait)
                        except Exception:
                            pass
                        await websocket.close()
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[Twitch] Health check error: {e}")
    
    async def authenticate(self):
        """Authenticate with Twitch IRC"""
        if not self.ws:
            return
        
        # Remove 'oauth:' prefix if present
        token = self.oauth_token
        if token.startswith('oauth:'):
            token = token[6:]
        
        token_prefix = token[:20] if token else "None"
        logger.debug(f"[TwitchWorker] Authenticating with token: {token_prefix}... as {self.bot_nick}")
        
        # Send authentication
        await self.ws.send(f'PASS oauth:{token}')
        await self.ws.send(f'NICK {self.bot_nick}')
        
        # Request capabilities for better message parsing
        await self.ws.send('CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership')
        
        logger.info(f"Authenticated with Twitch as {self.bot_nick}")
    
    async def handle_message(self, raw_message: str):
        """Parse and handle IRC message"""
        # Handle PING - keep connection alive
        if raw_message.startswith('PING'):
            if self.ws is not None:
                await self.ws.send('PONG :tmi.twitch.tv')
            return
        
        # Log successful authentication (match numeric 001 code only)
        parts = raw_message.split()
        if len(parts) > 1 and parts[1] == '001':
            # Print exactly once per worker instance to avoid duplicate stdout lines
            if not getattr(self, '_auth_printed', False):
                try:
                    logger.info(f"Twitch authentication successful for {self.bot_nick}")
                except Exception:
                    logger.info("Twitch authentication successful!")
                self._auth_printed = True
            return
        
        # Log join confirmation
        if f'JOIN #{self.channel}' in raw_message:
            logger.info(f"Successfully joined #{self.channel}")
            # If a connector object is attached, mark it connected and
            # emit the connection status so non-Qt callers can observe it
            try:
                if self.connector:
                    try:
                        self.connector.connected = True
                    except Exception:
                        pass
                    try:
                        self.connector.connection_status.emit(True)
                    except Exception:
                        pass
            except Exception:
                pass
            return
        
        # Check for error messages (NOTICE, msg_banned, msg_suspended, etc.)
        if 'NOTICE' in raw_message or 'msg_banned' in raw_message or 'msg_suspended' in raw_message:
            logger.warning(f"⚠️ Twitch IRC Notice/Error: {raw_message}")
            # Detect login/authentication failure and auto-refresh token
            if (
                'Login authentication failed' in raw_message
                or 'Login unsuccessful' in raw_message
                or 'authentication failed' in raw_message
                or 'Error logging in' in raw_message
                or 'Improperly formatted auth' in raw_message
            ):
                logger.warning("[TwitchWorker] Detected authentication failure. Attempting token refresh and reconnect...")
                if self.connector and hasattr(self.connector, 'refresh_access_token'):
                    refresh_result = self.connector.refresh_access_token()
                    if refresh_result:
                        # Save new tokens and username to config if available
                        if hasattr(self.connector, 'config') and self.connector.config:
                            # Persist under canonical twitch platform keys
                            if getattr(self.connector, 'is_bot_account', False):
                                self.connector.config.set_platform_config('twitch', 'bot_token', self.connector.oauth_token)
                                self.connector.config.set_platform_config('twitch', 'bot_refresh_token', self.connector.refresh_token)
                                if getattr(self.connector, 'username', None):
                                    self.connector.config.set_platform_config('twitch', 'bot_username', self.connector.username)
                            else:
                                self.connector.config.set_platform_config('twitch', 'oauth_token', self.connector.oauth_token)
                                self.connector.config.set_platform_config('twitch', 'streamer_refresh_token', self.connector.refresh_token)
                                if getattr(self.connector, 'username', None):
                                    self.connector.config.set_platform_config('twitch', 'username', self.connector.username)
                            logger.info("[TwitchWorker] Saved refreshed tokens and username to config.")
                        logger.info("[TwitchWorker] Token refreshed. Reconnecting...")
                        # Give a small grace window to flush any recently parsed messages
                        try:
                            grace = 1.5
                            if self._last_parsed_time:
                                since_parsed = time.time() - self._last_parsed_time
                                if since_parsed < grace:
                                    wait = grace - since_parsed
                                    logger.debug(f"[TwitchWorker] Waiting {wait:.3f}s to flush parsed messages before reconnect")
                                    await asyncio.sleep(wait)
                        except Exception:
                            pass
                        # Force reconnect by stopping and restarting
                        self.running = False
                        # Optionally, emit error or status signal here
                        # self.error_signal.emit('Twitch token refreshed, reconnecting...')
                    else:
                        logger.warning("[TwitchWorker] Token refresh failed. Manual re-authentication required.")
                return
            return
        
        # Parse CLEARMSG (message deletion)
        if 'CLEARMSG' in raw_message:
            result = self.parse_clearmsg(raw_message)
            if result:
                message_id = result
                logger.info(f"[Twitch] Message deleted by moderator: {message_id}")
                if hasattr(self, '_deletion_callback') and self._deletion_callback:
                    self._deletion_callback(message_id)
            return
        
        # Parse USERNOTICE (events like subs, raids, bits, etc.)
        if 'USERNOTICE' in raw_message:
            result = self.parse_usernotice(raw_message)
            if result:
                username, message, metadata = result
                logger.info(f"[Twitch] Event: {username}: {message}")
                logger.debug(f"[Twitch Event Metadata] {metadata.get('event_type', 'unknown')}")
                self.message_signal.emit(username, message)
                if hasattr(self, '_metadata_callback') and self._metadata_callback:
                    self._metadata_callback(username, message, metadata)
            return
        
        # Parse PRIVMSG (chat messages)
        if 'PRIVMSG' in raw_message:
            result = self.parse_privmsg(raw_message)
            if result:
                username, message, metadata = result
                try:
                    # record last parsed time to allow short grace before reconnect
                    self._last_parsed_time = time.time()
                except Exception:
                    pass
                
                # Check for bits in chat messages (Cheers)
                if 'bits=' in raw_message and metadata.get('bits'):
                    bits = metadata['bits']
                    metadata['event_type'] = 'bits'
                    metadata['amount'] = bits
                    message = f"💎 cheered {bits} bits: {message}"
                    logger.info(f"[Twitch] Bits: {username} - {bits}")
                
                logger.debug(f"[Twitch] {username}: {message}")  # Debug log
                logger.debug(f"[Twitch Metadata] Color: {metadata.get('color')}, Badges: {metadata.get('badges')}")  # Debug metadata
                
                # Emit signal with error handling
                try:
                    self.message_signal.emit(username, message)
                    # Diagnostic: show which worker/connector will call metadata callback
                    try:
                        has_cb = hasattr(self, '_metadata_callback') and self._metadata_callback
                        logger.debug(f"[TwitchWorker][TRACE] handle_message: worker_id={id(self)} connector_id={id(getattr(self, 'connector', None))} has_metadata_callback={bool(has_cb)}")
                    except Exception:
                        pass

                    if has_cb:
                        try:
                            # Normally we skip invoking metadata callbacks for bot
                            # connectors to avoid duplicate UI messages. However,
                            # if this worker was explicitly wired to forward to a
                            # streamer handler (flag `_forward_to_streamer`), allow
                            # the callback to run so parsed messages reach the UI.
                            is_bot = getattr(self, 'connector', None) and getattr(self.connector, 'is_bot_account', False)
                            forward_allowed = getattr(self, '_forward_to_streamer', False)
                            if is_bot and not forward_allowed:
                                try:
                                    logger.debug(f"[TwitchWorker][TRACE] Skipping metadata callback for bot worker_id={id(self)} connector_id={id(getattr(self, 'connector', None))}")
                                except Exception:
                                    pass
                            else:
                                # Durable log: record that this worker is invoking the metadata callback
                                try:
                                    log_dir = os.path.join(os.getcwd(), 'logs')
                                    os.makedirs(log_dir, exist_ok=True)
                                    fname = os.path.join(log_dir, 'connector_incoming.log')
                                    with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                                        f.write(f"{time.time():.3f} worker={id(self)} connector_id={id(getattr(self, 'connector', None))} username={username} preview={repr(message)[:200]} metadata_keys={list(metadata.keys())}\n")
                                except Exception:
                                    pass
                                try:
                                    self._metadata_callback(username, message, metadata)
                                except Exception as e:
                                    logger.exception(f"[TwitchWorker] [ERROR] Error calling metadata callback: {e}")
                                    import traceback
                                    traceback.print_exc()
                        except Exception as e:
                            logger.exception(f"[TwitchWorker] [ERROR] Error in metadata handling: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        # Defensive fallback: if no metadata callback was set
                        # but the worker has a connector reference that appears
                        # to be a streamer connector, call its handler directly.
                        try:
                            conn = getattr(self, 'connector', None)
                            if conn:
                                # If connector is a streamer connector, call it directly
                                if hasattr(conn, 'onMessageReceivedWithMetadata') and not getattr(conn, 'is_bot_account', False):
                                    logger.debug(f"[TwitchWorker][TRACE] Fallback: invoking connector.onMessageReceivedWithMetadata for connector_id={id(conn)}")
                                    try:
                                        # Durable log for fallback invocation
                                        try:
                                            log_dir = os.path.join(os.getcwd(), 'logs')
                                            os.makedirs(log_dir, exist_ok=True)
                                            fname = os.path.join(log_dir, 'connector_incoming.log')
                                            with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                                                f.write(f"{time.time():.3f} worker={id(self)} fallback_connector_id={id(conn)} username={username} preview={repr(message)[:200]} metadata_keys={list(metadata.keys())}\n")
                                        except Exception:
                                            pass
                                        try:
                                            conn.onMessageReceivedWithMetadata(username, message, metadata)
                                        except Exception as e:
                                            logger.exception(f"[TwitchWorker] ✗ Error in fallback connector callback: {e}")
                                    except Exception:
                                        pass
                                else:
                                    # Do NOT forward messages from bot connectors to streamer handlers.
                                    try:
                                        if getattr(conn, 'is_bot_account', False):
                                            try:
                                                logger.debug(f"[TwitchWorker][TRACE] Fallback: bot connector detected, not forwarding message from worker_id={id(self)}")
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                except Exception as e:
                    logger.exception(f"[Twitch] ✗ Error emitting message signal: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # CRITICAL: Parse failure - don't silently drop the message!
                logger.warning(f"[Twitch] ⚠️ PARSE FAILURE - Message will be dropped!")
                logger.debug(f"[Twitch] Raw IRC (first 500 chars): {raw_message[:500]}")
    
    def parse_clearmsg(self, raw_message: str):
        """Parse CLEARMSG to extract deleted message ID
        
        CLEARMSG format: @target-msg-id=xxx-xxx-xxx :tmi.twitch.tv CLEARMSG #channel :message text
        """
        try:
            # Extract target-msg-id from IRC tags
            if raw_message.startswith('@') and 'target-msg-id=' in raw_message:
                tag_part = raw_message.split(' ', 1)[0]
                for tag in tag_part[1:].split(';'):
                    if tag.startswith('target-msg-id='):
                        message_id = tag.split('=', 1)[1]
                        return message_id
        except Exception as e:
            logger.exception(f"[Twitch] Error parsing CLEARMSG: {e}")
        return None
    
    def parse_usernotice(self, raw_message: str):
        """Parse USERNOTICE to extract event information (subs, raids, channel points, etc.)
        
        USERNOTICE format: @badge-info=;badges=;...;msg-id=raid;... :tmi.twitch.tv USERNOTICE #channel :message
        """
        try:
            import datetime
            
            # Initialize metadata
            metadata = {
                'timestamp': datetime.datetime.now(),
                'color': None,
                'badges': [],
                'message_id': None
            }
            
            # Extract IRC tags (required for USERNOTICE)
            tags = {}
            if raw_message.startswith('@'):
                tag_part = raw_message.split(' ', 1)[0]
                for tag in tag_part[1:].split(';'):
                    if '=' in tag:
                        key, value = tag.split('=', 1)
                        tags[key] = value
                        metadata[key] = value
                
                # Extract message ID
                if 'id' in tags:
                    metadata['message_id'] = tags['id']
                
                # Extract color
                if 'color' in tags and tags['color']:
                    metadata['color'] = tags['color']
                
                # Extract badges
                if 'badges' in tags and tags['badges']:
                    badge_list = []
                    for badge_pair in tags['badges'].split(','):
                        if '/' in badge_pair:
                            badge_list.append(badge_pair)
                    metadata['badges'] = badge_list
            
            # Get the event type from msg-id tag
            msg_id = tags.get('msg-id', '')
            
            # Extract username (login or display-name)
            username = tags.get('display-name') or tags.get('login', 'Unknown')
            
            # Default message
            message = ""
            
            # Handle different event types
            if msg_id == 'raid':
                viewers = tags.get('msg-param-viewerCount', '0')
                metadata['event_type'] = 'raid'
                metadata['viewers'] = viewers
                message = f"📢 raided with {viewers} viewer{'s' if int(viewers) != 1 else ''}"
            
            elif msg_id in ['sub', 'resub']:
                months = tags.get('msg-param-cumulative-months', '1')
                metadata['event_type'] = 'subscription'
                metadata['months'] = months
                message = f"⭐ subscribed ({months} month{'s' if int(months) > 1 else ''})"
            
            elif msg_id in ['subgift', 'anonsubgift']:
                recipient = tags.get('msg-param-recipient-display-name', 'someone')
                metadata['event_type'] = 'subscription'
                message = f"💝 gifted a sub to {recipient}"
                if msg_id == 'anonsubgift':
                    username = 'Anonymous'
            
            elif msg_id in ['submysterygift', 'anonsubmysterygift']:
                gift_count = tags.get('msg-param-mass-gift-count', tags.get('msg-param-sender-count', '1'))
                metadata['event_type'] = 'subscription'
                metadata['gift_count'] = gift_count
                message = f"💝 gifted {gift_count} subscription{'s' if int(gift_count) != 1 else ''} to the community!"
                if msg_id == 'anonsubmysterygift':
                    username = 'Anonymous'
            
            elif msg_id == 'ritual' and tags.get('msg-param-ritual-name') == 'new_chatter':
                metadata['event_type'] = 'highlight'
                message = "🎉 is new to the chat!"
            
            elif msg_id == 'bitsbadgetier':
                threshold = tags.get('msg-param-threshold', '0')
                metadata['event_type'] = 'bits'
                metadata['threshold'] = threshold
                message = f"💎 unlocked a new bits badge tier ({threshold})!"
            
            # Channel point redemptions (AUTOMATIC REWARDS ONLY via IRC)
            # NOTE: Custom channel points rewards require EventSub subscription
            # IRC only receives automatic rewards like "Highlight My Message"
            elif msg_id in ['highlighted-message', 'skip-subs-mode-message']:
                metadata['event_type'] = 'redemption'
                
                # Try to extract the actual message if present
                message_match = re.search(r'USERNOTICE #\w+ :(.+)', raw_message)
                actual_message = message_match.group(1) if message_match else ""
                
                # Get reward details from API if available
                reward_name = 'Highlight My Message'  # Default for highlighted-message
                reward_cost = 'unknown'
                
                custom_reward_id = tags.get('custom-reward-id')
                if custom_reward_id and self.connector:
                    reward_info = self.connector.get_custom_reward(custom_reward_id)
                    if reward_info:
                        reward_name = reward_info['title']
                        reward_cost = str(reward_info['cost'])
                
                # Format: username redeemed <reward name> (<points>)
                # If user message included, highlight it at the end
                if actual_message:
                    message = f"🌟 redeemed {reward_name} ({reward_cost} points) - \"{actual_message}\""
                else:
                    message = f"🌟 redeemed {reward_name} ({reward_cost} points)"
            
            # Community pay forward
            elif msg_id == 'communitypayforward':
                prior_gifter = tags.get('msg-param-prior-gifter-display-name', 'someone')
                metadata['event_type'] = 'subscription'
                message = f"💝 paid forward a gift sub from {prior_gifter}"
            
            # Standard gift paid upgrade
            elif msg_id == 'standardpayforward':
                metadata['event_type'] = 'subscription'
                message = "💝 paid forward a gift sub"
            
            # Gift upgrade (user continuing a gifted sub)
            elif msg_id in ['giftpaidupgrade', 'primepaidupgrade']:
                metadata['event_type'] = 'subscription'
                message = "⭐ continued their subscription"
            
            # Announcement (special message type)
            elif msg_id == 'announcement':
                message_match = re.search(r'USERNOTICE #\w+ :(.+)', raw_message)
                actual_message = message_match.group(1) if message_match else ""
                metadata['event_type'] = 'highlight'
                message = f"📣 {actual_message}"
            
            else:
                # Unknown event type - try to extract any message
                message_match = re.search(r'USERNOTICE #\w+ :(.+)', raw_message)
                if message_match:
                    message = message_match.group(1)
                else:
                    message = f"triggered event: {msg_id}"
            
            return username, message, metadata
            
        except Exception as e:
            logger.exception(f"[Twitch] Error parsing USERNOTICE: {e}")
            logger.debug(f"[Twitch] Raw message: {raw_message}")
        
        return None
    
    def parse_privmsg(self, raw_message: str):
        """Parse PRIVMSG to extract username, message, and metadata (color, badges)"""
        try:
            import datetime
            
            # Initialize metadata
            metadata = {
                'timestamp': datetime.datetime.now(),
                'color': None,
                'badges': [],
                'emotes': None,
                'message_id': None
            }
            
            # Extract IRC tags if present (starts with @)
            tags = {}
            if raw_message.startswith('@'):
                tag_part = raw_message.split(' ', 1)[0]
                for tag in tag_part[1:].split(';'):
                    if '=' in tag:
                        key, value = tag.split('=', 1)
                        tags[key] = value
                        metadata[key] = value  # Store all tags in metadata
                
                # Extract message ID from tags (needed for deletion)
                if 'id' in tags and tags['id']:
                    metadata['message_id'] = tags['id']
                
                # Extract color from tags
                if 'color' in tags and tags['color']:
                    metadata['color'] = tags['color']
                
                # Extract badges from tags (keep badge/version format)
                if 'badges' in tags and tags['badges']:
                    badge_list = []
                    for badge_pair in tags['badges'].split(','):
                        if '/' in badge_pair:
                            # Keep the full badge/version format (e.g., 'broadcaster/1')
                            badge_list.append(badge_pair)
                    metadata['badges'] = badge_list
                
                # Extract emotes from tags
                if 'emotes' in tags and tags['emotes']:
                    metadata['emotes'] = tags['emotes']

                # Persist pretty-printed incoming PRIVMSG tags for debugging and
                # note whether fragments are present. This helps inspect incoming
                # IRC tag JSON and quickly find messages that included a
                # `fragments` payload.
                try:
                    import json as _json, time as _time, os as _os
                    log_dir = _os.path.join(_os.getcwd(), 'logs')
                    _os.makedirs(log_dir, exist_ok=True)
                    pname = _os.path.join(log_dir, f"privmsg_{self.channel}.log")
                    with open(pname, 'a', encoding='utf-8') as _wf:
                        _wf.write(f"{_time.time():.3f} PRIVMSG raw={raw_message!r}\n")
                        try:
                            _wf.write(_json.dumps(tags, indent=2, ensure_ascii=False))
                        except Exception:
                            _wf.write(str(tags))
                        _wf.write('\n\n')
                except Exception:
                    pass

                # Flag in metadata if fragments tag is present (will be parsed later)
                try:
                    metadata['has_fragments'] = bool(tags.get('fragments'))
                except Exception:
                    metadata['has_fragments'] = False

            # Prefer reconstructing the message from `fragments` tag when available.
            # IRC tag values are escaped using IRCv3 tag escaping (e.g. `\s` for space,
            # `\:` for semicolon, `\\` for backslash, `\r`/`\n` for CR/LF). We
            # provide a small unescape helper and attempt to parse `fragments` as
            # JSON. If that fails, fall back to the `text` tag, and finally to the
            # parsed body from the PRIVMSG payload.
            def _irc_tag_unescape(s: str) -> str:
                try:
                    return s.replace('\\s', ' ').replace('\\:', ';').replace('\\\\', '\\').replace('\\r', '\r').replace('\\n', '\n')
                except Exception:
                    return s

            prebuilt_message = None
            try:
                fr = tags.get('fragments') if tags else None
                if fr:
                    # Unescape then try to parse JSON array of fragments.
                    # Build an ordered message string and an `emotes` mapping
                    # keyed by emote id -> list of "start-end" ranges
                    try:
                        un = _irc_tag_unescape(fr)
                        import json
                        frag = json.loads(un)
                        if isinstance(frag, (list, tuple)):
                            parts = []
                            emotes_map = {}
                            # get twitch manager if available to resolve ids/sets
                            try:
                                from core.twitch_emotes import get_manager as _get_mgr
                                _t_mgr = _get_mgr()
                            except Exception:
                                _t_mgr = None

                            for f in frag:
                                if isinstance(f, str):
                                    parts.append(f)
                                    continue
                                if not isinstance(f, dict):
                                    continue

                                ftype = (f.get('type') or '').lower()
                                # Text fragment
                                if ftype == 'text' and 'text' in f:
                                    parts.append(f.get('text') or '')
                                    continue

                                # Emote fragment (structure may be nested under 'emote')
                                emobj = f.get('emote') if 'emote' in f else f
                                if emobj and (ftype == 'emote' or 'id' in emobj or 'emote_id' in emobj):
                                    em_id = None
                                    try:
                                        em_id = str(emobj.get('id') or emobj.get('emote_id') or emobj.get('emoteId') or '')
                                    except Exception:
                                        em_id = None

                                    em_text = None
                                    try:
                                        em_text = emobj.get('text') or emobj.get('name') or emobj.get('code') or ''
                                    except Exception:
                                        em_text = ''

                                    # Append the textual placeholder so positions align
                                    start = len(''.join(parts))
                                    placeholder = em_text or ''
                                    parts.append(placeholder)
                                    end = len(''.join(parts)) - 1

                                    if em_id:
                                        have_emote = False
                                        try:
                                            if _t_mgr and str(em_id) in getattr(_t_mgr, 'id_map', {}):
                                                have_emote = True
                                        except Exception:
                                            have_emote = False

                                        # If emote not known but emote_set present, try to fetch the set
                                        try:
                                            em_set = emobj.get('emote_set_id') or emobj.get('emote_set') or emobj.get('emote_set_ids')
                                        except Exception:
                                            em_set = None

                                        if not have_emote and em_set and _t_mgr:
                                            try:
                                                # schedule immediate fetch (will perform immediate fetch
                                                # when no throttler worker is active) and populate id_map
                                                _t_mgr.schedule_emote_set_fetch(em_set)
                                                if str(em_id) in getattr(_t_mgr, 'id_map', {}):
                                                    have_emote = True
                                            except Exception:
                                                pass

                                        if have_emote:
                                            try:
                                                lst = emotes_map.get(str(em_id)) or []
                                                lst.append(f"{start}-{end}")
                                                emotes_map[str(em_id)] = lst
                                            except Exception:
                                                pass
                                        else:
                                            # emote not available; we'll leave the placeholder text
                                            # which will be escaped by the renderer later
                                            pass
                                    continue

                                # Fallback: if fragment has 'text' key, use it
                                if 'text' in f:
                                    parts.append(f.get('text') or '')
                                    continue

                            prebuilt_message = ''.join(parts).strip()
                            # attach emotes_map to metadata if any
                            if emotes_map:
                                metadata['emotes'] = emotes_map

                            # Persist pretty-printed fragments JSON to logs for later inspection
                            try:
                                import json as _json, time as _time, os as _os
                                log_dir = _os.path.join(_os.getcwd(), 'logs')
                                _os.makedirs(log_dir, exist_ok=True)
                                fname = _os.path.join(log_dir, f"fragments_{self.channel}.log")
                                with open(fname, 'a', encoding='utf-8') as wf:
                                    wf.write(f"{_time.time():.3f} FRAGMENTS worker={id(self)} message_id={metadata.get('message_id')!r}\n")
                                    wf.write(_json.dumps(frag, indent=2, ensure_ascii=False))
                                    wf.write('\n\n')
                            except Exception:
                                pass

                            # expose parsed fragments for callers/tests
                            try:
                                metadata['fragments_json'] = frag
                            except Exception:
                                pass
                        elif isinstance(frag, dict) and 'text' in frag:
                            prebuilt_message = str(frag.get('text') or '').strip()
                    except Exception:
                        prebuilt_message = None

                if not prebuilt_message:
                    # Try `text` tag (escaped) as a fallback
                    txt = tags.get('text') if tags else None
                    if txt:
                        prebuilt_message = _irc_tag_unescape(txt).strip()
            except Exception:
                prebuilt_message = None
            
            # Prepare body without leading tags when present
            body = raw_message
            try:
                if raw_message.startswith('@'):
                    body = raw_message.split(' ', 1)[1]
            except Exception:
                body = raw_message

            # IRC format can be:
            # Simple: :username!username@username.tmi.twitch.tv PRIVMSG #channel :message
            # With tags: @badge-info=;badges=;color=#... :username!username@username.tmi.twitch.tv PRIVMSG #channel :message
            
            # Try with tags first - more permissive:
            # - capture anything up to '!' as username (allows unicode/symbols)
            # - accept any non-space channel name after PRIVMSG
            # - capture the remainder after the first ':' following PRIVMSG as the message
            match = re.search(r':([^!]+)!.*?PRIVMSG\s+([^\s]+)\s+:(.+)', body)

            if match:
                username = match.group(1)
                # group(2) is the channel, group(3) is the message
                # If we reconstructed message from tags, prefer that.
                if prebuilt_message:
                    message = prebuilt_message
                else:
                    message = match.group(3).strip()
                logger.debug(f"[Twitch Parser] [OK] Parsed: {username}: {message[:50]}")
                try:
                    import time, os
                    log_dir = os.path.join(os.getcwd(), 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    fname = os.path.join(log_dir, f"parsed_irc_{self.channel}.log")
                    with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                        f.write(f"{time.time():.3f} PARSED worker={id(self)} username={username!r} preview={message[:200]!r}\n")
                except Exception:
                    pass
                return username, message, metadata
            
            # Try simpler fallback pattern (handle odd tag ordering or missing parts)
            if 'PRIVMSG' in body and ':' in body:
                try:
                    # Capture channel and message after PRIVMSG
                    m = re.search(r'PRIVMSG\s+([^\s]+)\s+:(.+)', body)
                    username_match = re.search(r':([^!]+)!', body)
                    if m and username_match:
                        username = username_match.group(1)
                        if prebuilt_message:
                            message = prebuilt_message
                        else:
                            message = m.group(2).strip()
                        logger.debug(f"[Twitch Parser] [OK] Parsed (alt): {username}: {message[:50]}")
                        try:
                            import time, os
                            log_dir = os.path.join(os.getcwd(), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            fname = os.path.join(log_dir, f"parsed_irc_{self.channel}.log")
                            with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                                f.write(f"{time.time():.3f} PARSED_ALT worker={id(self)} username={username!r} preview={message[:200]!r}\n")
                        except Exception:
                            pass
                        return username, message, metadata
                except Exception:
                    pass
            
            # If we get here, parsing failed - dump diagnostics (always persist parse failures)
            logger.warning(f"[Twitch Parser] [FAIL] Failed to parse PRIVMSG")
            logger.debug(f"[Twitch Parser] Raw: {raw_message[:200]}")
            try:
                log_dir = os.path.join(os.getcwd(), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                fname = os.path.join(log_dir, f"raw_irc_parse_fail_{self.channel}.log")
                with open(fname, 'a', encoding='utf-8', errors='replace') as f:
                    f.write(f"{time.time():.3f} PARSE_FAIL worker={id(self)} {repr(raw_message)}\n")
            except Exception:
                pass
                
        except Exception as e:
            logger.exception(f"[Twitch Parser] [ERROR] Exception parsing message: {e}")
            logger.debug(f"[Twitch Parser] Raw message: {raw_message[:200]}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        if self.loop and self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
    
    async def send_message_async(self, message: str):
        """Send message to Twitch chat (async)"""
        if self.ws and self.running:
            logger.debug(f"[TwitchWorker] Sending PRIVMSG to #{self.channel}: {message[:50]}")
            await self.ws.send(f'PRIVMSG #{self.channel} :{message}')
            logger.debug(f"[TwitchWorker] Message sent to Twitch IRC")
        else:
            logger.warning(f"[TwitchWorker] [WARN] Cannot send: ws={self.ws is not None}, running={self.running}")
    
    def send_message(self, message: str):
        """Send message to Twitch chat"""
        logger.debug(f"[TwitchWorker] send_message called: loop={self.loop is not None}, ws={self.ws is not None}")
        if self.loop and self.ws:
            asyncio.run_coroutine_threadsafe(
                self.send_message_async(message), 
                self.loop
            )
            logger.debug(f"[TwitchWorker] Message queued to event loop")
            return True
        else:
            logger.warning(f"[TwitchWorker] [WARN] Cannot queue message: loop={self.loop is not None}, ws={self.ws is not None}")
            return False


class TwitchEventSubWorker(QThread):
    """Worker thread for Twitch EventSub WebSocket connection"""
    
    redemption_signal = pyqtSignal(str, str, int, str)  # username, reward_title, reward_cost, user_input
    event_signal = pyqtSignal(str, str, dict)  # event_type, username, event_data
    status_signal = pyqtSignal(bool)  # connected
    error_signal = pyqtSignal(str)  # error
    # Request the main thread to open re-auth flow; payload is the oauth_url
    reauth_signal = pyqtSignal(str)
    
    EVENTSUB_URL = 'wss://eventsub.wss.twitch.tv/ws'
    
    def __init__(self, oauth_token: str, client_id: str, broadcaster_login: str):
        super().__init__()
        self.oauth_token = oauth_token
        self.client_id = client_id
        self.broadcaster_login = broadcaster_login
        self.broadcaster_id = None
        self.running = False
        self.ws = None
        self.loop = None
        self.session_id = None
        self.subscription_id = None
        # Populated by validate_token()
        self.validated_scopes = None
    
    def run(self):
        """Main event loop"""
        logger.info(f"[EventSub] Worker starting...")
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.connect_and_listen())
        except Exception as e:
            logger.exception(f"[EventSub] Error in event loop: {e}")
            self.error_signal.emit(f"EventSub error: {e}")
        finally:
            self.loop.close()
            logger.info(f"[EventSub] Worker stopped")
    
    async def validate_token(self):
        """Validate OAuth token and show granted scopes"""
        try:
            try:
                session = _make_retry_session()
                response = session.get(
                    'https://id.twitch.tv/oauth2/validate',
                    headers={'Authorization': f'OAuth {self.oauth_token}'},
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[EventSub] Network error validating token: {e}")
                return

            if response.status_code == 200:
                data = response.json()
                scopes = data.get('scopes', [])
                # remember scopes for later diagnostic logging
                self.validated_scopes = scopes
                # remember raw token info and type (user vs app)
                self.token_info = data
                # token is a user token when a user_id or login is present
                self.token_user_id = data.get('user_id') or data.get('login')
                self.token_type = 'user' if self.token_user_id else 'app'
                logger.info(f"[EventSub] Token validated. Granted scopes:")
                for scope in scopes:
                    logger.info(f"[EventSub]    [OK] {scope}")

                # Check for required scopes. Requirements differ for user vs app (client credentials) tokens.
                if getattr(self, 'token_type', 'user') == 'user':
                    required_scopes = {
                        'user:read:chat': 'User Read Chat',
                        'chat:read': 'Chat Read',
                        'chat:edit': 'Chat Edit',
                        'channel:read:redemptions': 'Channel Points Redemptions',
                        'channel:read:subscriptions': 'Subscribers & Gift Subs',
                        'bits:read': 'Cheers/Bits',
                        'moderator:read:followers': 'Followers'
                    }
                else:
                    # App (client credentials) tokens should use bot scopes
                    required_scopes = {
                        'channel:bot': 'Channel Bot',
                        'user:bot': 'User Bot'
                    }

                missing = []
                for scope, name in required_scopes.items():
                    if scope not in scopes:
                        missing.append(f"{scope} ({name})")

                if missing:
                    logger.warning(f"[EventSub] [WARN] Missing scopes:")
                    for scope in missing:
                        logger.warning(f"[EventSub]    [MISSING] {scope}")
                    logger.warning(f"[EventSub] To fix this: visit Twitch connections and re-authorize the app with required scopes")
                    try:
                        import webbrowser
                        # Construct an OAuth URL to help the user re-authorize with required scopes
                        try:
                            from core.config import ConfigManager
                            _cfg = ConfigManager()
                            _tcfg = _cfg.get_platform_config('twitch') or {}
                            twitch_client_id = _tcfg.get('client_id', '')
                        except Exception:
                            twitch_client_id = ''
                        # Use localhost:8888 for Twitch reauth by default (non-ngrok local flow)
                        redirect_uri = "http://localhost:8888/callback"
                        # Build scope list depending on token type. Do NOT include EventSub subscription types
                        # like `channel.chat.message` in the OAuth scope request; those are subscription types only.
                        if getattr(self, 'token_type', 'user') == 'user':
                            scopes_needed = [
                                'user:read:email',
                                'user:read:chat',
                                'chat:read',
                                'chat:edit',
                                'channel:read:subscriptions',
                                'channel:manage:broadcast',
                                'channel:read:redemptions',
                                'bits:read',
                                'moderator:read:followers',
                                'user:write:chat'
                            ]
                        else:
                            # App tokens should request bot scopes relevant to server-side actions
                            scopes_needed = [
                                'channel:bot',
                                'user:bot'
                            ]

                        scope_string = " ".join(scopes_needed)
                        from urllib.parse import urlencode
                        params = {
                            'response_type': 'code',
                            'client_id': twitch_client_id,
                            'redirect_uri': redirect_uri,
                            'scope': scope_string,
                            'force_verify': 'true'
                        }
                        oauth_url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
                        logger.info(f"[EventSub] Requesting re-authorize with required scopes")
                        try:
                            # Emit a signal to request reauthorization UI in the main thread
                            self.reauth_signal.emit(oauth_url)
                        except Exception as e:
                            logger.exception(f"[EventSub] Could not emit reauth signal: {e}")
                    except Exception as e:
                        logger.exception(f"[EventSub] Could not open browser for re-auth: {e}")
                else:
                    logger.info(f"[EventSub] [OK] All required scopes present")
            else:
                # Print full response body to aid triage
                body = response.text
                logger.warning(f"[EventSub] [WARN] Token validation failed: {response.status_code} - {body}")
        except Exception as e:
            logger.exception(f"[EventSub] Error validating token: {e}")
    
    async def connect_and_listen(self):
        """Connect to EventSub and listen for events"""
        retry_count = 0
        max_retries = 5
        
        while self.running and retry_count < max_retries:
            try:
                logger.info(f"[EventSub] Connecting to {self.EVENTSUB_URL}...")
                
                async with websockets.connect(self.EVENTSUB_URL) as ws:
                    self.ws = ws
                    self.status_signal.emit(True)
                    logger.info(f"[EventSub] Connected!")
                    
                    # Wait for welcome message
                    welcome_msg = await ws.recv()
                    welcome_data = json.loads(welcome_msg)
                    
                    if welcome_data.get('metadata', {}).get('message_type') == 'session_welcome':
                        self.session_id = welcome_data['payload']['session']['id']
                        logger.info(f"[EventSub] Session ID: {self.session_id}")
                        
                        # Validate token and show granted scopes
                        await self.validate_token()
                        
                        # Get broadcaster ID
                        await self.get_broadcaster_id()
                        
                        if self.broadcaster_id:
                            # Subscribe to channel points redemptions
                            await self.subscribe_to_redemptions()
                        else:
                            logger.warning(f"[EventSub] ⚠ Could not get broadcaster ID")
                    
                    # Listen for messages
                    while self.running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=10)
                            await self.handle_message(message)
                        except asyncio.TimeoutError:
                            # Send keepalive ping
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.info(f"[EventSub] Connection closed")
                            break
                    
            except Exception as e:
                logger.exception(f"[EventSub] Connection error: {e}")
                retry_count += 1
                if self.running and retry_count < max_retries:
                    logger.info(f"[EventSub] Retrying in 5 seconds... ({retry_count}/{max_retries})")
                    await asyncio.sleep(5)
            finally:
                self.ws = None
                self.status_signal.emit(False)
        
        logger.debug(f"[EventSub] Connection loop ended")
    
    async def get_broadcaster_id(self):
        """Get broadcaster user ID from username"""
        try:
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {self.oauth_token}'
            }
            
            try:
                session = _make_retry_session()
                response = session.get(
                    'https://api.twitch.tv/helix/users',
                    headers=headers,
                    params={'login': self.broadcaster_login},
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[EventSub] Network error fetching broadcaster ID: {e}")
                return
            
            if response.status_code == 200:
                users = response.json().get('data', [])
                if users:
                    self.broadcaster_id = users[0]['id']
                    logger.info(f"[EventSub] Broadcaster ID: {self.broadcaster_id}")
                else:
                    logger.warning(f"[EventSub] No user found for login: {self.broadcaster_login}")
            else:
                logger.error(f"[EventSub] Failed to get user ID: {response.status_code}")
        except Exception as e:
            logger.exception(f"[EventSub] Error getting broadcaster ID: {e}")
    
    async def subscribe_to_redemptions(self):
        """Subscribe to EventSub events"""
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.oauth_token}',
            'Content-Type': 'application/json'
        }
        
        # List of subscriptions to create
        subscriptions = [
            {
                'name': 'channel points redemptions',
                'type': 'channel.channel_points_custom_reward_redemption.add',
                'version': '1',
                'condition': {'broadcaster_user_id': self.broadcaster_id}
            },
            {
                'name': 'stream online',
                'type': 'stream.online',
                'version': '1',
                'condition': {'broadcaster_user_id': self.broadcaster_id}
            },
            {
                'name': 'followers',
                'type': 'channel.follow',
                'version': '2',
                'condition': {
                    'broadcaster_user_id': self.broadcaster_id,
                    'moderator_user_id': self.broadcaster_id
                }
            },
            {
                'name': 'subscribers',
                'type': 'channel.subscribe',
                'version': '1',
                'condition': {'broadcaster_user_id': self.broadcaster_id}
            },
            {
                'name': 'gift subscriptions',
                'type': 'channel.subscription.gift',
                'version': '1',
                'condition': {'broadcaster_user_id': self.broadcaster_id}
            },
            {
                'name': 'cheers',
                'type': 'channel.cheer',
                'version': '1',
                'condition': {'broadcaster_user_id': self.broadcaster_id}
            }
            ,
            # Note: channel.chat.message subscription appended below so we can include an optional
            # `user_id` condition when token validation reveals a user context.
        ]

        # Build and append the chat messages subscription, optionally scoping to the token's user_id
        try:
            chat_condition = {'broadcaster_user_id': self.broadcaster_id}
            token_user_id = None
            if hasattr(self, 'token_info') and isinstance(self.token_info, dict):
                token_user_id = self.token_info.get('user_id')
            if token_user_id:
                chat_condition['user_id'] = str(token_user_id)

            subscriptions.append({
                'name': 'chat messages',
                'type': 'channel.chat.message',
                'version': '1',
                'condition': chat_condition
            })
        except Exception:
            # Fallback: subscribe without user_id
            subscriptions.append({
                'name': 'chat messages',
                'type': 'channel.chat.message',
                'version': '1',
                'condition': {'broadcaster_user_id': self.broadcaster_id}
            })
        
        # Subscribe to each event type
        for sub in subscriptions:
            try:
                # Build transport block. Default to websocket transport (session_id).
                # If the worker is configured to use webhook transport (e.g., via
                # `self.transport_mode == 'webhook'`), use the webhook shape instead.
                transport = {
                    'method': 'websocket',
                    'session_id': self.session_id
                }
                if getattr(self, 'transport_mode', None) == 'webhook':
                    # Expect `self.callback_url` and `self.callback_secret` to be provided
                    callback = getattr(self, 'callback_url', None)
                    secret = getattr(self, 'callback_secret', None)
                    if callback:
                        transport = {
                            'method': 'webhook',
                            'callback': callback,
                            'secret': secret or ''
                        }

                subscription_data = {
                    'type': sub['type'],
                    'version': sub['version'],
                    'condition': sub['condition'],
                    'transport': transport
                }
                
                logger.info(f"[EventSub] Subscribing to {sub['name']}...")
                try:
                    session = _make_retry_session()
                    response = session.post(
                        'https://api.twitch.tv/helix/eventsub/subscriptions',
                        headers=headers,
                        json=subscription_data,
                        timeout=10
                    )
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[EventSub] Network error subscribing to {sub['name']}: {e}")
                    continue
                
                if response.status_code == 202:
                    result = response.json()
                    sub_id = result['data'][0]['id']
                    logger.info(f"[EventSub] [OK] Subscribed to {sub['name']}! ID: {sub_id}")
                else:
                    # Log full response body and masked token + current validated scopes (if available)
                    body = response.text
                    def _mask_token(tkn: str) -> str:
                        if not tkn:
                            return '<empty token>'
                        if len(tkn) <= 10:
                            return tkn[:4] + '...' + tkn[-2:]
                        return tkn[:6] + '...' + tkn[-4:]

                    masked = _mask_token(self.oauth_token)
                    scopes = self.validated_scopes if self.validated_scopes is not None else []
                    logger.warning(f"[EventSub] [WARN] {sub['name']} subscription failed: {response.status_code} - {body}")
                    logger.debug(f"[EventSub]    Masked token: {masked}")
                    logger.debug(f"[EventSub]    Validated scopes: {scopes}")
            except Exception as e:
                logger.exception(f"[EventSub] Error subscribing to {sub['name']}: {e}")
    
    async def handle_message(self, message: str):
        """Handle incoming EventSub message"""
        try:
            data = json.loads(message)
            message_type = data.get('metadata', {}).get('message_type')
            
            if message_type == 'session_keepalive':
                # Keepalive message, no action needed
                pass
            
            elif message_type == 'notification':
                # Event notification
                event = data.get('payload', {}).get('event', {})
                subscription_type = data.get('payload', {}).get('subscription', {}).get('type')
                
                if subscription_type == 'channel.channel_points_custom_reward_redemption.add':
                    # Channel points redemption
                    username = event.get('user_name', event.get('user_login', 'Unknown'))
                    reward = event.get('reward', {})
                    reward_title = reward.get('title', 'Unknown Reward')
                    reward_cost = reward.get('cost', 0)
                    user_input = event.get('user_input', '')
                    
                    logger.info(f"[EventSub] Redemption: {username} -> {reward_title} ({reward_cost})")
                    self.redemption_signal.emit(username, reward_title, reward_cost, user_input)
                
                elif subscription_type == 'stream.online':
                    # Stream went online
                    broadcaster_name = event.get('broadcaster_user_name', event.get('broadcaster_user_login', 'Broadcaster'))
                    stream_type = event.get('type', 'live')
                    logger.info(f"[EventSub] Stream online: {broadcaster_name} ({stream_type})")
                    self.event_signal.emit('stream.online', broadcaster_name, {'type': stream_type})
                
                elif subscription_type == 'channel.follow':
                    # New follower
                    username = event.get('user_name', event.get('user_login', 'Unknown'))
                    logger.info(f"[EventSub] New follower: {username}")
                    self.event_signal.emit('follow', username, {})
                
                elif subscription_type == 'channel.subscribe':
                    # New subscriber
                    username = event.get('user_name', event.get('user_login', 'Unknown'))
                    tier = event.get('tier', '1000')
                    is_gift = event.get('is_gift', False)
                    logger.info(f"[EventSub] New subscriber: {username} (Tier: {tier}, Gift: {is_gift})")
                    self.event_signal.emit('subscribe', username, {'tier': tier, 'is_gift': is_gift})
                
                elif subscription_type == 'channel.subscription.gift':
                    # User gifted subscriptions
                    username = event.get('user_name', event.get('user_login', 'Anonymous'))
                    if event.get('is_anonymous', False):
                        username = 'Anonymous'
                    tier = event.get('tier', '1000')
                    total = event.get('total', 1)
                    cumulative_total = event.get('cumulative_total')
                    logger.info(f"[EventSub] Gift subs: {username} gifted {total} (Tier: {tier})")
                    self.event_signal.emit('gift', username, {'tier': tier, 'total': total, 'cumulative_total': cumulative_total})
                
                elif subscription_type == 'channel.cheer':
                    # User cheered
                    username = event.get('user_name', event.get('user_login', 'Anonymous'))
                    if event.get('is_anonymous', False):
                        username = 'Anonymous'
                    bits = event.get('bits', 0)
                    cheer_message = event.get('message', '')
                    logger.info(f"[EventSub] Cheer: {username} - {bits} bits")
                    self.event_signal.emit('cheer', username, {'bits': bits, 'message': cheer_message})

                elif (isinstance(subscription_type, str) and ('chat' in subscription_type and 'message' in subscription_type)) or subscription_type in ('channel.chat_message', 'channel.chat.message'):
                    # Channel chat message delivered via EventSub websocket
                    # Be defensive about field names - different versions may use different keys
                    # Prefer structured `fragments` when present (EventSub provides these
                    # for richer message contents including emotes and mentions). If
                    # fragments aren't available, fall back to legacy text fields.
                    fragments = event.get('fragments') or event.get('message_fragments') or None
                    if fragments and isinstance(fragments, list):
                        try:
                            # Reconstruct a human-readable message by concatenating
                            # the `text` field from each fragment in order. Preserve
                            # spacing as provided by the fragments' text values.
                            message_text = ''.join([f.get('text', '') for f in fragments])
                        except Exception:
                            message_text = ''
                    else:
                        message_text = event.get('message') or event.get('text') or event.get('body') or event.get('content') or ''
                    username = event.get('user_name') or event.get('user_login') or event.get('display_name') or event.get('broadcaster_user_name') or 'Unknown'
                    message_id = event.get('id') or event.get('message_id') or event.get('msg_id')
                    timestamp = event.get('timestamp') or event.get('created_at') or None

                    logger.info(f"[EventSub] Chat message from {username}: {message_text}")
                    try:
                        from .connector_utils import emit_chat
                        metadata = {
                            'message_id': message_id,
                            'user_id': event.get('user_id') or event.get('user_login'),
                            'timestamp': timestamp,
                            'badges': [],
                            'fragments': fragments if fragments is not None else []
                        }
                        emit_chat(self, 'twitch', username, message_text, metadata)
                    except Exception as e:
                        logger.exception(f"[EventSub] Failed to emit chat message: {e}")
            
            elif message_type == 'session_reconnect':
                # Server requesting reconnect
                reconnect_url = data.get('payload', {}).get('session', {}).get('reconnect_url')
                logger.info(f"[EventSub] Server requested reconnect to: {reconnect_url}")
            
        except Exception as e:
            logger.exception(f"[EventSub] Error handling message: {e}")
    
    def stop(self):
        """Stop the EventSub worker"""
        logger.info(f"[EventSub] Stopping worker...")
        self.running = False
        if self.ws and self.loop is not None:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
