"""
Trovo Platform Connector
"""

from platform_connectors.base_connector import BasePlatformConnector

import asyncio
import json
import websockets
try:
    import requests
except Exception:
    requests = None
import random
import string
import time
import os
from platform_connectors.qt_compat import QThread, pyqtSignal
import threading
from core.logger import get_logger
from platform_connectors.connector_utils import connect_with_retry, startup_allowed, safe_emit

# Structured logger for this module
logger = get_logger('TrovoConnector')
try:
    from core.http_session import make_retry_session
except Exception:
    make_retry_session = None

# Ensure `connect` exists on the imported `websockets` module for environments
# where a local stub or different websockets version is used. Tests patch
# `platform_connectors.*.websockets.connect` so this makes that attribute
# consistently available.
try:
    import websockets as _ws
    if not hasattr(_ws, 'connect'):
        import importlib as _il
        _stub = _il.import_module('websockets_stub')
        setattr(_ws, 'connect', getattr(_stub, 'connect'))
except Exception:
    pass

# Provide a minimal dummy requests module if `requests` is not installed so
# runtime code can catch `requests.exceptions.RequestException` without
# raising NameError at import time.
if requests is None:
    class _DummyRequestsExceptions:
        class RequestException(Exception):
            pass

    class _DummyRequestsSession:
        def post(self, *args, **kwargs):
            raise _DummyRequestsExceptions.RequestException("requests not installed")

        def get(self, *args, **kwargs):
            raise _DummyRequestsExceptions.RequestException("requests not installed")

        def delete(self, *args, **kwargs):
            raise _DummyRequestsExceptions.RequestException("requests not installed")

    class _DummyRequestsModule:
        exceptions = _DummyRequestsExceptions()

        @staticmethod
        def Session(*args, **kwargs):
            return _DummyRequestsSession()

    requests = _DummyRequestsModule()


class TrovoConnector(BasePlatformConnector):
    """Connector for Trovo chat"""
    def connect(self, channel_name):
        """Connect to Trovo chat with thread-safe worker creation."""
        logger.info(f"[TrovoConnector] connect() called for channel: {channel_name}")
        with self._worker_lock:
            if not self.access_token:
                logger.warning("[TrovoConnector] No access token set. Cannot connect.")
                return

            # Skip refresh if we just set a fresh token via OAuth
            if self._skip_next_refresh:
                logger.debug(f"[TrovoConnector] Skipping refresh, using fresh OAuth token")
                self._skip_next_refresh = False
            elif self.refresh_token and self.config:
                # Try to refresh token if we have a refresh token, but skip if token was just saved recently
                trovo_config = self.config.get_platform_config('trovo')
                token_timestamp = trovo_config.get('streamer_token_timestamp', 0)
                age_seconds = time.time() - token_timestamp if token_timestamp else 999999

                if age_seconds > 10:  # Only refresh if token is older than 10 seconds
                    logger.info(f"[TrovoConnector] Token is {age_seconds:.0f}s old, attempting refresh...")
                    self.refresh_access_token()
                else:
                    logger.debug(f"[TrovoConnector] Token is fresh ({age_seconds:.0f}s old), skipping refresh")

            # If already connected and worker running for same channel, skip
            try:
                already_connected = getattr(self, 'connected', False)
                same_channel = getattr(self, 'channel', None) == channel_name
                worker_running = bool(getattr(self, 'worker', None) and getattr(self.worker, 'running', False))
                if already_connected and same_channel and worker_running:
                    try:
                        logger.debug(f"[TrovoConnector][TRACE] connect: already connected for {channel_name} worker_id={id(self.worker)}")
                    except Exception:
                        pass
                    return
            except Exception:
                pass

            # Remember the channel
            self.channel = channel_name

            logger.info(f"[TrovoConnector] Starting TrovoWorker for channel: {channel_name}")
            # Pass config into worker so it can persist discovered channel/user IDs
            self.worker = TrovoWorker(self.access_token, channel_name, config=self.config)
            # Wire incoming messages. For bot connectors, if ChatManager attached
            # a streamer_connector, forward incoming messages to the streamer's
            # onMessageReceivedWithMetadata to avoid duplicate UI emissions.
            try:
                streamer_conn = getattr(self, 'streamer_connector', None)
            except Exception:
                streamer_conn = None

            if self.is_bot_account and streamer_conn and hasattr(streamer_conn, 'onMessageReceivedWithMetadata'):
                try:
                    # Forward bot worker messages directly to streamer handler
                    def _forward_to_streamer(u, m, md, _sc=streamer_conn):
                        try:
                            _sc.onMessageReceivedWithMetadata('trovo', u, m, md)
                        except Exception:
                            pass
                    self.worker.message_signal.connect(_forward_to_streamer)
                    logger.debug(f"[TrovoConnector][TRACE] Bot worker messages forwarded to streamer connector id={id(streamer_conn)}")
                except Exception:
                    # Fallback to local handler if forwarding fails
                    try:
                        self.worker.message_signal.connect(self.onMessageReceived)
                    except Exception:
                        pass
            else:
                # Normal wiring: the connector handles its own incoming messages
                try:
                    self.worker.message_signal.connect(self.onMessageReceived)
                except Exception:
                    pass

            try:
                self.worker.status_signal.connect(self.onStatusChanged)
            except Exception:
                pass
            try:
                self.worker.deletion_signal.connect(self.onMessageDeleted)
            except Exception:
                pass
            try:
                if not startup_allowed():
                    logger.info("[TrovoConnector] CI mode: skipping TrovoWorker.start()")
                    return
                self.worker.start()
            except Exception as e:
                logger.error(f"[TrovoConnector] Error starting TrovoWorker: {e}")
                self.worker = None
                return

    # Hard-coded fallback Trovo access token removed for security; prefer config values
    DEFAULT_ACCESS_TOKEN = ""
    CLIENT_ID = ""
    CLIENT_SECRET = ""

    def __init__(self, config=None):
        super().__init__()
        self.worker_thread = None
        self.worker = None
        # Lock to prevent concurrent worker creation/teardown
        self._worker_lock = threading.Lock()
        self.config = config
        self.access_token = self.DEFAULT_ACCESS_TOKEN
        self.refresh_token = None
        self.is_bot_account = False  # Track if this is a bot connector
        self.last_status = False
        self.message_cache = {}  # Cache message_id -> user_id mapping for deletion
        self._skip_next_refresh = False  # Skip refresh after fresh OAuth login
        # Load token from config if available
        if self.config:
            trovo_config = self.config.get_platform_config('trovo')
            token = trovo_config.get('access_token', '')
            if token:
                self.access_token = token
            refresh = trovo_config.get('refresh_token', '')
            if refresh:
                self.refresh_token = refresh
            # Load client credentials from config if present
            try:
                cid = trovo_config.get('client_id', '')
                csecret = trovo_config.get('client_secret', '')
                if cid:
                    self.CLIENT_ID = cid
                if csecret:
                    self.CLIENT_SECRET = csecret
            except Exception:
                pass

    def set_token(self, token: str, refresh_token: str = None, is_bot: bool = False):
        """Set OAuth access token for Trovo chat"""
        if token:
            self.access_token = token
            self.is_bot_account = is_bot
            self._skip_next_refresh = True  # Skip refresh since we just got a fresh token
            # Store bot's refresh token if provided
            if refresh_token:
                self.refresh_token = refresh_token
                logger.info(f"[Trovo] {'Bot' if is_bot else 'Streamer'} token and refresh token set")
            # Don't save to config - bot token is already saved as 'bot_token' in config
            # and we don't want to overwrite the streamer's 'access_token'
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            logger.warning("[Trovo] No refresh token available")
            return False
        
        try:
            headers = {
                'Accept': 'application/json',
                'Client-ID': self.CLIENT_ID,
                'Content-Type': 'application/json'
            }

            data = {
                'client_secret': self.CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }

            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    'https://open-api.trovo.live/openplatform/refreshtoken',
                    headers=headers,
                    json=data,
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Trovo] Network error refreshing token: {e}")
                return False

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token', '')
                new_refresh = token_data.get('refresh_token', '')
                if new_refresh:
                    self.refresh_token = new_refresh

                # Persist refreshed tokens using ConfigManager to avoid races
                if self.config:
                    self.config.set_platform_config('trovo', 'access_token', self.access_token)
                    self.config.set_platform_config('trovo', 'refresh_token', self.refresh_token)
                    logger.info(f"[Trovo] Saved refreshed tokens via ConfigManager")

                logger.info("[Trovo] Access token refreshed successfully")
                return True
            else:
                logger.error(f"[Trovo] Token refresh failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.exception(f"[Trovo] Error refreshing token: {e}")
            return False
    
    def delete_message(self, message_id: str):
        """Delete a message from Trovo chat
        
        Trovo API requires: DELETE /openplatform/channels/{channelID}/messages/{messageID}/users/{uID}
        The message_id format from chat is: timestamp_channelID_channelID_messageID_sequence
        We need to extract channelID, messageID, and need to get uID from somewhere
        """
        if not message_id or not self.access_token:
            logger.warning(f"[Trovo] Cannot delete message - missing message_id or access_token")
            return
        
        try:
            # Parse Trovo message ID format: timestamp_channelID_channelID_messageID_sequence
            parts = message_id.split('_')
            if len(parts) < 5:
                logger.warning(f"[Trovo] Invalid message_id format: {message_id}")
                return
            
            # Extract channel_id and message_id from the composite ID
            # Format: timestamp_channelID_channelID_actualMessageID_sequence
            channel_id = parts[1]  # Second part is channel ID
            actual_message_id = parts[3]  # Fourth part is the actual message ID
            
            # Get user_id from cache
            user_id = self.message_cache.get(message_id)
            if not user_id:
                logger.warning(f"[Trovo] Cannot delete message: user_id not found in cache")
                logger.debug(f"[Trovo] Message ID: {message_id}, Channel ID: {channel_id}, Msg ID: {actual_message_id}")
                return
            
            headers = {
                'Accept': 'application/json',
                'Client-ID': self.CLIENT_ID,
                'Authorization': f'OAuth {self.access_token}'
            }
            
            # DELETE /openplatform/channels/{channelID}/messages/{messageID}/users/{uID}
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.delete(
                    f'https://open-api.trovo.live/openplatform/channels/{channel_id}/messages/{actual_message_id}/users/{user_id}',
                    headers=headers,
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Trovo] Network error deleting message: {e}")
                return False

            if response.status_code == 200:
                logger.info(f"[Trovo] Message deleted: {message_id}")
                # Remove from cache after successful deletion
                if message_id in self.message_cache:
                    del self.message_cache[message_id]
                return True
            else:
                logger.error(f"[Trovo] Failed to delete message: {response.status_code}")
                logger.debug(f"[Trovo] Response: {response.text}")
                return False
        except Exception as e:
            logger.exception(f"[Trovo] Error deleting message: {e}")
            return False
    
    def onMessageDeleted(self, message_id: str):
        """Handle message deleted by platform/moderator"""
        logger.info(f"[TrovoConnector] Message deleted by platform: {message_id}")
        safe_emit(self.message_deleted, 'trovo', message_id)

    def disconnect(self):
        """Disconnect from Trovo and stop worker thread safely"""
        with getattr(self, '_worker_lock', threading.Lock()):
            try:
                logger.debug(f"[TrovoConnector][TRACE] disconnect called: worker={getattr(self, 'worker', None)} connected={getattr(self, 'connected', False)}")
            except Exception:
                pass
            if getattr(self, 'worker', None):
                try:
                    self.worker.stop()
                except Exception as e:
                    logger.error(f"[TrovoConnector] Error stopping worker: {e}")
                try:
                    # Wait up to 5 seconds for the thread to finish
                    self.worker.wait(5000)
                except Exception:
                    pass
            self.connected = False
            try:
                safe_emit(self.connection_status, False)
            except Exception:
                pass
            self.worker = None

    def ban_user(self, username: str, user_id: str = None):
        """Ban a user from Trovo chat"""
        if not user_id or not self.access_token:
            logger.warning(f"[Trovo] Cannot ban user: missing user_id or access_token")
            return
        
        try:
            headers = {
                'Client-ID': 'b239c1cc698e04e93a164df321d142b3',
                'Authorization': f'OAuth {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Ban user via Trovo API
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    'https://open-api.trovo.live/openplatform/chat/ban',
                    headers=headers,
                    json={
                        'user_id': user_id,
                        'duration': 0  # 0 = permanent ban
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Trovo] Network error banning user: {e}")
                return
            
            if response.status_code == 200:
                logger.info(f"[Trovo] User banned: {username}")
            else:
                logger.error(f"[Trovo] Failed to ban user: {response.status_code}")
        except Exception as e:
            logger.exception(f"[Trovo] Error banning user: {e}")
    
    def onMessageReceived(self, username: str, message: str, metadata: dict):
        logger.debug(f"[TrovoConnector] onMessageReceived: {username}, {message}, metadata: {metadata}")
        
        # Cache message_id -> user_id mapping for deletion
        msg_id = metadata.get('message_id')
        user_id = metadata.get('user_id')
        if msg_id and user_id:
            self.message_cache[msg_id] = user_id
            # Limit cache size to prevent memory growth
            if len(self.message_cache) > 1000:
                # Remove oldest half
                keys_to_remove = list(self.message_cache.keys())[:500]
                for key in keys_to_remove:
                    del self.message_cache[key]
        
        # Emit via connector signal
        safe_emit(self.message_received_with_metadata, 'trovo', username, message, metadata)
    
    def onStatusChanged(self, connected: bool):
        self.connected = connected
        self.last_status = connected
        safe_emit(self.connection_status, connected)
    
    def send_message(self, message: str):
        """Send a message to Trovo chat via REST API"""
        if not self.access_token:
            logger.warning("[Trovo] Cannot send message: No access token")
            return False
        
        if not self.config:
            logger.warning("[Trovo] Cannot send message: No config available")
            return False
        
        try:
            # Diagnostic: persistent send log entry (pre-send)
            try:
                log_dir = os.path.join(os.getcwd(), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                    sf.write(f"{time.time():.3f} platform=trovo used={'bot' if self.is_bot_account else 'streamer'} token_prefix={self.access_token[:12] if self.access_token else 'None'} preview={repr(message)[:200]}\n")
            except Exception:
                pass

            # Debug: Show which token is being used
            token_prefix = self.access_token[:12] if self.access_token else "None"
            logger.debug(f"[Trovo] send_message: Using token (first 12 chars): {token_prefix}...")

            # Get config (don't reload to preserve in-memory token)
            trovo_config = self.config.get_platform_config('trovo')
            logger.debug(f"[Trovo] send_message: Config keys: {list(trovo_config.keys())}")

            # Try multiple possible field names for channel_id
            channel_id = (
                trovo_config.get('streamer_channel_id') or 
                trovo_config.get('channel_id') or
                trovo_config.get('streamer_user_id') or
                trovo_config.get('user_id')
            )
            logger.debug(f"[Trovo] send_message: channel_id from config = {channel_id}")

            if not channel_id:
                logger.warning(f"[Trovo] Cannot send message: No channel_id found in config. Available keys: {list(trovo_config.keys())}")
                return False

            headers = {
                'Accept': 'application/json',
                'Client-ID': self.CLIENT_ID,
                'Authorization': f'OAuth {self.access_token}',
                'Content-Type': 'application/json'
            }

            data = {
                'content': message,
                'channel_id': str(channel_id)
            }

            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    'https://open-api.trovo.live/openplatform/chat/send',
                    headers=headers,
                    json=data,
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[Trovo] Network error sending message: {e}")
                # Persist failure then return
                try:
                    log_dir = os.path.join(os.getcwd(), 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                        sf.write(f"{time.time():.3f} platform=trovo event=send_network_error err={repr(str(e))}\n")
                except Exception:
                    pass
                return False

            # Persist the HTTP response for offline diagnosis
            try:
                log_dir = os.path.join(os.getcwd(), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                    sf.write(f"{time.time():.3f} platform=trovo event=send_response status={response.status_code} used={'bot' if self.is_bot_account else 'streamer'} channel_id={channel_id} resp_preview={repr(response.text)[:200]}\n")
            except Exception:
                pass

            if response.status_code == 200:
                logger.info(f"[Trovo] Message sent successfully: {message[:50]}...")
                return True
            elif response.status_code == 401:
                # Token expired - try to refresh and retry
                logger.warning(f"[Trovo] Token expired (401), attempting refresh...")
                if self.refresh_access_token():
                    logger.info(f"[Trovo] Token refreshed, retrying send...")
                    # Update headers with new token
                    headers['Authorization'] = f'OAuth {self.access_token}'
                    try:
                        response = session.post(
                            'https://open-api.trovo.live/openplatform/chat/send',
                            headers=headers,
                            json=data,
                            timeout=10
                        )
                    except requests.exceptions.RequestException as e:
                        logger.exception(f"[Trovo] Network error retrying send after refresh: {e}")
                        return False
                    if response.status_code == 200:
                        logger.info(f"[Trovo] Message sent successfully after token refresh: {message[:50]}...")
                        try:
                            log_dir = os.path.join(os.getcwd(), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                                sf.write(f"{time.time():.3f} platform=trovo event=send_response status={response.status_code} used={'bot' if self.is_bot_account else 'streamer'} channel_id={channel_id} resp_preview={repr(response.text)[:200]}\n")
                        except Exception:
                            pass
                        return True
                    else:
                        logger.error(f"[Trovo] Failed after token refresh: {response.status_code} - {response.text}")
                        try:
                            log_dir = os.path.join(os.getcwd(), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                                sf.write(f"{time.time():.3f} platform=trovo event=send_response status={response.status_code} used={'bot' if self.is_bot_account else 'streamer'} channel_id={channel_id} resp_preview={repr(response.text)[:200]}\n")
                        except Exception:
                            pass
                        return False
                else:
                    logger.error(f"[Trovo] Failed to refresh token")
                    return False
            else:
                logger.error(f"[Trovo] Failed to send message: {response.status_code} - {response.text}")
                try:
                    log_dir = os.path.join(os.getcwd(), 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                        sf.write(f"{time.time():.3f} platform=trovo event=send_response status={response.status_code} used={'bot' if self.is_bot_account else 'streamer'} channel_id={channel_id} resp_preview={repr(response.text)[:200]}\n")
                except Exception:
                    pass
                return False

        except Exception as e:
            logger.exception(f"[Trovo] Error sending message: {e}")
            try:
                log_dir = os.path.join(os.getcwd(), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                    sf.write(f"{time.time():.3f} platform=trovo event=send_exception err={repr(str(e))} used={'bot' if self.is_bot_account else 'streamer'}\n")
            except Exception:
                pass
            return False



class TrovoWorker(QThread):
    """Worker thread for Trovo chat via WebSocket"""
    message_signal = pyqtSignal(str, str, dict)  # username, message, metadata
    status_signal = pyqtSignal(bool)
    deletion_signal = pyqtSignal(str)  # message_id


    TROVO_CHAT_WS_URL = "wss://open-chat.trovo.live/chat"
    TROVO_CHAT_TOKEN_URL = "https://open-api.trovo.live/openplatform/chat/token"

    def __init__(self, access_token: str, channel: str = None, config=None, connector=None):
        super().__init__()
        self.access_token = access_token
        self.channel = channel
        self.channel_name = channel
        self.config = config
        # No connector reference by default; worker emits on itself
        self.running = False
        self.loop = None
        self.ws = None
        self.chat_token = None
        self.ping_gap = 30  # default seconds
        self.connection_time = None  # Track when we connected to filter old messages
        
        # Message reliability features
        self.seen_message_ids = set()  # Track processed messages
        self.max_seen_ids = 10000  # Prevent unbounded growth
        self.last_message_time = None  # For health monitoring
        self.connection_timeout = 180  # 3 minutes

    def run(self):
        logger.info("[TrovoWorker] Starting run()")
        self.running = True
        safe_emit(self.status_signal, True)
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                # Step 1: Get chat token
                self.chat_token = self.get_chat_token()
                if not self.chat_token:
                    logger.error("[TrovoWorker] Failed to get chat token. Aborting connection.")
                    return
                self.loop.run_until_complete(self.connect_to_trovo())
            except Exception as e:
                logger.exception(f"[TrovoWorker] Error in worker run inner loop: {e}")
            finally:
                if self.loop and not self.loop.is_closed():
                    self.loop.close()
        except Exception as e:
            logger.exception(f"[TrovoWorker] Exception in run(): {e}")
            return

    def get_chat_token(self):
        access_token = (self.access_token or "").strip()
        logger.debug("[TrovoWorker] Entered get_chat_token()")
        try:
            logger.debug(f"[TrovoWorker] Access token length: {len(access_token)}; starts with: {access_token[:8]}")
            headers = {
                "Accept": "application/json",
                "Client-ID": "b239c1cc698e04e93a164df321d142b3",
                "Client-Id": "b239c1cc698e04e93a164df321d142b3",
                "Authorization": f"OAuth {access_token}"
            }
            logger.debug(f"[TrovoWorker] Requesting chat token with headers: {headers}")
            try:
                session = make_retry_session() if make_retry_session else requests.Session()
                try:
                    resp = session.get(self.TROVO_CHAT_TOKEN_URL, headers=headers, timeout=10)
                except requests.exceptions.RequestException as e:
                    logger.exception(f"[TrovoWorker] Network error requesting chat token: {e}")
                    return None
                logger.debug(f"[TrovoWorker] Response status: {resp.status_code}")
                logger.debug(f"[TrovoWorker] Response headers: {resp.headers}")
                logger.debug(f"[TrovoWorker] Response body: {resp.text}")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("token")

                # If access token expired, attempt a refresh (one retry)
                if resp.status_code == 401:
                    logger.warning("[TrovoWorker] Chat token request unauthorized (401). Trying refresh if available.")
                    try:
                        # Try to obtain refresh token from config
                        refresh_token = None
                        if self.config:
                            trovo_cfg = self.config.get_platform_config('trovo')
                            refresh_token = trovo_cfg.get('refresh_token')
                        # If we have a refresh token, request a new access token
                        if refresh_token:
                            refresh_headers = {
                                'Accept': 'application/json',
                                'Client-ID': TrovoConnector.CLIENT_ID,
                                'Content-Type': 'application/json'
                            }
                            refresh_data = {
                                'client_secret': TrovoConnector.CLIENT_SECRET,
                                'grant_type': 'refresh_token',
                                'refresh_token': refresh_token
                            }
                            session = make_retry_session() if make_retry_session else requests.Session()
                            try:
                                r = session.post(
                                    'https://open-api.trovo.live/openplatform/refreshtoken',
                                    headers=refresh_headers,
                                    json=refresh_data,
                                    timeout=10
                                )
                            except requests.exceptions.RequestException as e:
                                logger.exception(f"[TrovoWorker] Network error during refresh attempt: {e}")
                                return None
                            logger.debug(f"[TrovoWorker] Refresh response: {getattr(r, 'status_code', 'err')} {getattr(r, 'text', '')}")
                            if r.status_code == 200:
                                token_data = r.json()
                                new_access = token_data.get('access_token')
                                new_refresh = token_data.get('refresh_token')
                                if new_access:
                                    self.access_token = new_access
                                if new_refresh:
                                    # persist rotated refresh token
                                    self.refresh_token = new_refresh
                                if self.config:
                                    # update config atomically
                                    self.config.set_platform_config('trovo', 'access_token', self.access_token)
                                    if getattr(self, 'refresh_token', None):
                                        self.config.set_platform_config('trovo', 'refresh_token', self.refresh_token)
                                    logger.info("[TrovoWorker] Saved refreshed tokens via ConfigManager")
                                # Retry chat token request once with new access token
                                headers['Authorization'] = f"OAuth {self.access_token}"
                                try:
                                    retry = session.get(self.TROVO_CHAT_TOKEN_URL, headers=headers, timeout=10)
                                except requests.exceptions.RequestException as e:
                                    logger.exception(f"[TrovoWorker] Network error on retrying chat token: {e}")
                                    return None
                                logger.debug(f"[TrovoWorker] Retry response: {retry.status_code} {getattr(retry, 'text', '')}")
                                if retry.status_code == 200:
                                    data = retry.json()
                                    return data.get('token')
                                else:
                                    logger.debug(f"[TrovoWorker] Retry failed: {retry.status_code} {getattr(retry, 'text', '')}")
                                    return None
                            else:
                                logger.debug(f"[TrovoWorker] Refresh attempt failed: {r.status_code} {getattr(r, 'text', '')}")
                                return None
                        else:
                            logger.debug(f"[TrovoWorker] No refresh token available or refresh failed: {resp.text}")
                            return None
                    except Exception as e:
                        logger.exception(f"[TrovoWorker] Exception during refresh attempt: {e}")
                        return None
                else:
                    logger.error(f"[TrovoWorker] Failed to get chat token: {resp.status_code} {resp.text}")
                    return None
            except Exception as e:
                logger.exception(f"[TrovoWorker] Exception getting chat token: {e}")
                return None
        except Exception as e:
            logger.exception(f"[TrovoWorker] Exception in get_chat_token(): {e}")
            return None

    async def connect_to_trovo(self):
        try:
            # Disable built-in ping/pong since Trovo uses custom protocol
            async with connect_with_retry(websockets.connect, self.TROVO_CHAT_WS_URL, ping_interval=None) as ws:
                self.ws = ws
                logger.info("[TrovoWorker] Connected to Trovo chat WebSocket.")
                # Step 2: Send AUTH message
                nonce = self._random_nonce()
                auth_msg = {
                    "type": "AUTH",
                    "nonce": nonce,
                    "data": {"token": self.chat_token}
                }
                await ws.send(json.dumps(auth_msg))
                logger.debug(f"[TrovoWorker] Sent AUTH message with nonce {nonce}")
                # Wait for RESPONSE
                response = await ws.recv()
                logger.debug(f"[TrovoWorker] AUTH response: {response}")
                # Set connection time to filter old messages
                self.connection_time = time.time()
                self.last_message_time = time.time()
                logger.info(f"[TrovoWorker] Connection established at {self.connection_time}")
                # Start ping task
                ping_task = asyncio.create_task(self.ping_loop(ws))
                # Start health monitoring
                health_task = asyncio.create_task(self.health_check_loop(ws))
                # Listen for messages
                await self.listen(ws)
                ping_task.cancel()
                health_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass
                try:
                    await health_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.exception(f"[TrovoWorker] WebSocket connection error: {e}")

    async def ping_loop(self, ws):
        while self.running:
            await asyncio.sleep(self.ping_gap)
            nonce = self._random_nonce()
            ping_msg = {"type": "PING", "nonce": nonce}
            try:
                await ws.send(json.dumps(ping_msg))
                logger.debug(f"[TrovoWorker] Sent PING with nonce {nonce}")
            except Exception as e:
                logger.error(f"[TrovoWorker] Error sending PING: {e}")
                break

    async def listen(self, ws):
        while self.running:
            try:
                message = await ws.recv()
                self.last_message_time = time.time()  # Update health timestamp
                self.handle_message(message)
            except websockets.ConnectionClosed:
                logger.warning(f"[TrovoWorker] Connection closed")
                break
            except Exception as e:
                logger.exception(f"[TrovoWorker] Error receiving message: {e}")
                break

    def handle_message(self, raw_message):
        try:
            # Debug: Log all received messages
            logger.debug(f"[TrovoWorker] Received message: {raw_message[:200]}")
            data = json.loads(raw_message)
            msg_type = data.get("type")
            if msg_type == "PONG":
                # Adjust ping gap if provided
                gap = data.get("data", {}).get("gap")
                if gap:
                    self.ping_gap = gap
                logger.debug(f"[TrovoWorker] Received PONG, set ping gap to {self.ping_gap}s")
            elif msg_type == "CHAT":
                logger.debug(f"[TrovoWorker] Processing CHAT message: {data}")
                chats = data.get("data", {}).get("chats", [])
                logger.debug(f"[TrovoWorker] Found {len(chats)} chat messages")
                for chat in chats:
                    # Message deduplication
                    msg_id = chat.get("message_id") or chat.get("msg_id")
                    if msg_id:
                        if msg_id in self.seen_message_ids:
                            logger.debug(f"[TrovoWorker] Skipping duplicate message: {msg_id}")
                            continue
                        
                        # Add to seen messages
                        self.seen_message_ids.add(msg_id)
                        
                        # Limit size to prevent unbounded memory growth
                        if len(self.seen_message_ids) > self.max_seen_ids:
                            self.seen_message_ids = set(list(self.seen_message_ids)[self.max_seen_ids // 2:])
                            logger.debug(f"[TrovoWorker] Trimmed seen_message_ids to {len(self.seen_message_ids)}")
                    
                    # Filter old messages - only emit messages after connection time
                    send_time = chat.get("send_time", 0)
                    if self.connection_time and send_time < self.connection_time:
                        logger.debug(f"[TrovoWorker] Skipping old message (send_time: {send_time} < connection_time: {self.connection_time})")
                        continue
                    
                    username = chat.get("nick_name", chat.get("user_name", "TrovoUser"))
                    message = chat.get("content", "")
                    user_id = chat.get("uid") or chat.get("user_id") or chat.get("sender_id")
                    chat_type = chat.get("type", 0)  # Trovo uses type codes for events
                    
                    # Auto-save streamer's user_id as channel_id for sending messages
                    if username.lower().replace('_', '') == self.channel_name.lower().replace('_', ''):
                        if user_id and self.config:
                            trovo_config = self.config.get_platform_config('trovo')
                            if not trovo_config.get('streamer_user_id'):
                                # Use ConfigManager to save atomically
                                self.config.set_platform_config('trovo', 'streamer_user_id', str(user_id))
                                logger.info(f"[TrovoWorker] Auto-saved streamer_user_id: {user_id}")
                    
                    # Parse badges from medals and roles
                    badges = []
                    medals = chat.get("medals", [])
                    roles = chat.get("roles", [])
                    
                    # Add medals as badges (filter out empty strings)
                    if isinstance(medals, list):
                        badges.extend([m for m in medals if m and m.strip()])
                    
                    # Add roles as badges
                    if isinstance(roles, list):
                        badges.extend([r for r in roles if r and r.strip()])
                    
                    # Build metadata
                    metadata = {
                        'badges': badges,
                        'color': None,  # Trovo doesn't provide color in chat messages
                        'timestamp': send_time,
                        'avatar': chat.get('avatar', ''),
                        'sub_tier': chat.get('sub_tier', '0'),
                        'message_id': msg_id,
                        'user_id': user_id
                    }
                    
                    # Detect Trovo events based on type or content
                    # Type 5001 = Subscription
                    if chat_type == 5001 or 'subscribed' in message.lower():
                        months = chat.get('num', 1)
                        metadata['event_type'] = 'subscription'
                        metadata['months'] = months
                        message = f"⭐ subscribed for {months} month{'s' if months > 1 else ''}"
                        logger.info(f"[TrovoWorker] Subscription: {username} - {months} months")
                    
                    # Type 5002 = Follow
                    elif chat_type == 5002 or 'followed' in message.lower():
                        metadata['event_type'] = 'follow'
                        message = "🎯 followed the stream"
                        logger.info(f"[TrovoWorker] Follow: {username}")
                    
                    # Type 5003 = Gift (subscription gift)
                    elif chat_type == 5003 or chat.get('gift_type'):
                        gift_num = chat.get('num', 1)
                        metadata['event_type'] = 'subscription'
                        message = f"💝 gifted {gift_num} subscription{'s' if gift_num > 1 else ''}"
                        logger.info(f"[TrovoWorker] Gift subs: {username} - {gift_num}")
                    
                    # Type 5004 = Spell (Trovo's version of bits/donations)
                    elif chat_type == 5004 or chat.get('value_type') == 'spell':
                        spell_value = chat.get('value', 0)
                        spell_name = chat.get('gift', 'spell')
                        metadata['event_type'] = 'spell'
                        metadata['amount'] = spell_value
                        metadata['spell_name'] = spell_name
                        message = f"✨ cast {spell_name} ({spell_value} mana)"
                        logger.info(f"[TrovoWorker] Spell: {username} - {spell_name} ({spell_value})")
                    
                    # Type 5005 = Magic Chat (highlighted message)
                    elif chat_type == 5005 or chat.get('magic_chat_id'):
                        metadata['event_type'] = 'magic_chat'
                        message = f"🌟 {message}"
                        logger.info(f"[TrovoWorker] Magic Chat: {username}")
                    
                    # Type 5006 = Raid
                    elif chat_type == 5006 or 'raid' in message.lower():
                        viewers = chat.get('viewer_count', 0)
                        metadata['event_type'] = 'raid'
                        metadata['viewers'] = viewers
                        message = f"📢 raided with {viewers} viewer{'s' if viewers != 1 else ''}"
                        logger.info(f"[TrovoWorker] Raid: {username} - {viewers} viewers")
                    
                    logger.debug(f"[TrovoWorker] Emitting message from {username}: {message} with badges: {badges}")
                    from .connector_utils import emit_chat
                    emit_chat(self, 'trovo', username, message, metadata)
            elif msg_type == "MESSAGE_DELETE" or msg_type == "DELETE":
                # Handle message deletion events
                logger.debug(f"[TrovoWorker] Processing deletion message: {data}")
                delete_data = data.get("data", {})
                
                # Try to get message_id from various possible fields
                deleted_msg_id = (
                    delete_data.get("message_id") or 
                    delete_data.get("msg_id") or
                    delete_data.get("id")
                )
                
                if deleted_msg_id:
                    logger.info(f"[TrovoWorker] Message deleted by moderator: {deleted_msg_id}")
                    safe_emit(self.deletion_signal, str(deleted_msg_id))
                else:
                    logger.warning(f"[TrovoWorker] ⚠ Deletion event missing message_id")
            else:
                logger.debug(f"[TrovoWorker] Unknown message type: {msg_type}")
        except json.JSONDecodeError as e:
            logger.warning(f"[TrovoWorker] ⚠ Invalid JSON received: {e}")
        except KeyError as e:
            logger.warning(f"[TrovoWorker] ⚠ Missing required field: {e}")
        except Exception as e:
            logger.exception(f"[TrovoWorker] ⚠ Error handling message: {type(e).__name__}: {e}")

    def _random_nonce(self, length=12):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    async def health_check_loop(self, websocket):
        """Monitor connection health and force reconnect if dead"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.last_message_time:
                    time_since_last = time.time() - self.last_message_time
                    
                    if time_since_last > self.connection_timeout:
                        logger.warning(f"[TrovoWorker] Connection appears dead ({int(time_since_last)}s since last message)")
                        logger.info(f"[TrovoWorker] Forcing reconnection...")
                        await websocket.close()
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[TrovoWorker] Health check error: {e}")

    def stop(self):
        self.running = False
        if self.loop and self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)

        # Schedule cooperative shutdown and stop the loop
        try:
            if self.loop and not (self.loop.is_closed()):
                try:
                    asyncio.run_coroutine_threadsafe(self._shutdown_async(), self.loop)
                except Exception:
                    pass
                try:
                    self.loop.call_soon_threadsafe(self.loop.stop)
                except Exception:
                    pass
        except Exception:
            logger.exception("[TrovoWorker] Error scheduling shutdown on event loop")

    async def _shutdown_async(self):
        """Cooperative async shutdown for TrovoWorker: close websocket and cancel tasks."""
        try:
            self.running = False
            try:
                if self.ws:
                    await self.ws.close()
            except Exception:
                pass

            try:
                current = asyncio.current_task(loop=self.loop)
                tasks = [t for t in asyncio.all_tasks(loop=self.loop) if t is not current]
                if tasks:
                    for t in tasks:
                        try:
                            t.cancel()
                        except Exception:
                            pass
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass
        except Exception as e:
            logger.exception(f"[TrovoWorker] _shutdown_async error: {e}")


# Note: Trovo uses WebSocket connections
# Documentation: https://developer.trovo.live/
