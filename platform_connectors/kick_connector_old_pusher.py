"""
Kick Platform Connector
Connects to Kick chat via OAuth2 and Webhooks API
Uses official Kick Developer API: https://docs.kick.com/
"""

import asyncio
import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from platform_connectors.base_connector import BasePlatformConnector
from PyQt6.QtCore import QThread, pyqtSignal
from core.logger import get_logger

# Structured logger for this module
logger = get_logger('KickOldPusher')
try:
    from core.http_session import make_retry_session
except Exception:
    make_retry_session = None


class KickConnector(BasePlatformConnector):
    """Connector for Kick chat using official OAuth2 + Webhooks API"""
    
    # Kick OAuth credentials from https://kick.com/settings/developer
    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = ""
    DEFAULT_REDIRECT_URI = "http://localhost:8888/callback"
    
    # Kick API endpoints
    OAUTH_BASE = "https://id.kick.com"
    API_BASE = "https://api.kick.com/public/v1"
    
    def __init__(self, config=None):
        super().__init__()
        self.worker_thread = None
        self.worker = None
        self.config = config
        self.client_id = self.DEFAULT_CLIENT_ID
        self.client_secret = self.DEFAULT_CLIENT_SECRET
        # Load client credentials from provided config if available
        try:
            if self.config:
                kc = self.config.get_platform_config('kick') or {}
                cid = kc.get('client_id', '')
                csec = kc.get('client_secret', '')
                if cid:
                    self.client_id = cid
                if csec:
                    self.client_secret = csec
                if cid or csec:
                    logger.debug(f"[KickOldPusher] Loaded client creds from config: client_id={'set' if cid else 'not set'}")
        except Exception:
            pass

        self.oauth_token = None
        self.refresh_token = None
    
    def set_token(self, token: str):
        """Set OAuth token"""
        self.oauth_token = token
    
    def set_refresh_token(self, refresh_token: str):
        """Set OAuth refresh token"""
        self.refresh_token = refresh_token
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return False

        # If client creds missing, try to load from config if available
        if (not self.client_id or not self.client_secret) and getattr(self, 'config', None):
            try:
                kc = self.config.get_platform_config('kick') or {}
                if not self.client_id:
                    self.client_id = kc.get('client_id', '')
                if not self.client_secret:
                    self.client_secret = kc.get('client_secret', '')
                if self.client_id or self.client_secret:
                    logger.debug("[KickOldPusher] Fallback: loaded client creds from config for refresh")
            except Exception:
                pass

        try:
            token_url = 'https://id.kick.com/oauth/token'
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    token_url,
                    data={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'refresh_token': self.refresh_token,
                        'grant_type': 'refresh_token'
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"KickOldPusher: Network error refreshing token: {e}")
                return False
            
            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token')
                logger.info("Kick token refreshed successfully")
                return True
            else:
                logger.warning(f"Kick token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"Error refreshing Kick token: {e}")
            return False
    
    def connect(self, username: str):
        """Connect to Kick chat"""
        self.username = username
        
        # Try to refresh token if we have a refresh token
        if self.refresh_token and not self.oauth_token:
            self.refresh_access_token()
        
        self.worker = KickWorker(username, self.oauth_token)
        self.worker_thread = QThread()
        
        self.worker.moveToThread(self.worker_thread)
        self.worker.message_signal.connect(self.onMessageReceived)
        self.worker.message_signal_with_metadata.connect(self.onMessageReceivedWithMetadata)
        self.worker.status_signal.connect(self.onStatusChanged)
        self.worker.error_signal.connect(self.onError)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()
    
    def disconnect(self):
        """Disconnect from Kick"""
        if self.worker:
            self.worker.stop()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.connected = False
        self.connection_status.emit(False)
    
    def send_message(self, message: str):
        """Send a message"""
        if self.worker and self.connected:
            self.worker.send_message(message)
    
    def onMessageReceived(self, username: str, message: str):
        # Emit using standardized signature: platform, username, message, metadata
        try:
            self.message_received.emit('kick', username, message, {})
        except Exception:
            logger.exception("KickOldPusher: failed to emit standardized message_received signal")
    
    def onMessageReceivedWithMetadata(self, username: str, message: str, metadata: dict):
        # Ensure standardized signature: platform, username, message, metadata
        try:
            self.message_received_with_metadata.emit('kick', username, message, metadata)
        except Exception:
            logger.exception("KickOldPusher: failed to emit standardized message_received_with_metadata signal")
    
    def onStatusChanged(self, connected: bool):
        self.connected = connected
        self.connection_status.emit(connected)
    
    def onError(self, error: str):
        self.error_occurred.emit(error)


class KickWorker(QThread):
    """Worker thread for Kick WebSocket connection"""
    
    message_signal = pyqtSignal(str, str)
    message_signal_with_metadata = pyqtSignal(str, str, dict)
    status_signal = pyqtSignal(bool)
    error_signal = pyqtSignal(str)
    
    def __init__(self, channel: str, oauth_token: str = None):
        super().__init__()
        self.channel = channel.lower()
        self.oauth_token = oauth_token
        self.running = False
        self.ws = None
        self.loop = None
        self.chatroom_id = None
    
    def run(self):
        # Prevent worker from running if disabled in config
        if hasattr(self, 'config') and self.config and self.config.get('platforms', {}).get('kick', {}).get('disabled', False):
            logger.info("KickWorker: Skipping run - platform is disabled")
            return
        """Run the Kick WebSocket connection"""
        self.running = True
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.connect_to_kick())
        except Exception as e:
            self.error_signal.emit(f"Connection error: {str(e)}")
            self.status_signal.emit(False)
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()
    
    async def connect_to_kick(self):
        """Connect to Kick WebSocket"""
        try:
            # Get chatroom ID from channel name
            logger.info(f"Fetching Kick chatroom ID for channel: {self.channel}")
            self.chatroom_id = await self.get_chatroom_id()
            if not self.chatroom_id:
                self.error_signal.emit(f"Failed to get Kick chatroom ID for {self.channel}")
                self.status_signal.emit(False)
                return
            
            logger.info(f"Got Kick chatroom ID: {self.chatroom_id}")
            
            # NOTE: Kick integration is currently experimental
            # Kick uses Pusher for WebSocket but frequently changes cluster configuration
            # and implements aggressive anti-bot measures.
            # 
            # Current known issues:
            # - Pusher app key eb1d5f283081a78b932c exists but cluster is not publicly documented
            # - All standard Pusher clusters (us2, us3, eu, ap1-4, mt1, sa1) return "not in this cluster" error
            # - May require browser automation or reverse engineering current JavaScript bundles
            #
            # TODO: Implement browser-based WebSocket extraction or find updated API documentation
            
            # Connect to Kick WebSocket - trying mt1 cluster (most common for Pusher)
            ws_url = 'wss://ws-mt1.pusher.com/app/eb1d5f283081a78b932c?protocol=7&client=js&version=8.4.0-rc2'
            logger.info(f"Connecting to Kick WebSocket: {ws_url}")
            logger.warning("NOTE: Kick WebSocket may fail due to cluster mismatch - this is a known issue")
            
            async with websockets.connect(ws_url) as websocket:
                self.ws = websocket
                
                # Subscribe to chat channel
                subscribe_msg = {
                    "event": "pusher:subscribe",
                    "data": {
                        "auth": "",
                        "channel": f"chatrooms.{self.chatroom_id}.v2"
                    }
                }
                await websocket.send(json.dumps(subscribe_msg))
                logger.debug(f"Sent subscription request for chatrooms.{self.chatroom_id}.v2")

                logger.info(f"Connected to Kick channel: {self.channel}")
                self.status_signal.emit(True)
                
                # Listen for messages
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        logger.debug(f"[Kick Raw] {message[:200]}")  # Print first 200 chars
                        await self.handle_message(message)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving message: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Kick connection error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_signal.emit(f"Connection error: {str(e)}")
            self.status_signal.emit(False)
    
    async def get_chatroom_id(self):
        """Get chatroom ID from channel name using cloudscraper to bypass Cloudflare"""
        try:
            url = f'https://kick.com/api/v2/channels/{self.channel}'
            logger.debug(f"Fetching from: {url}")
            
            # Use cloudscraper in a thread to avoid blocking
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
            
            # Run in executor since cloudscraper is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: scraper.get(url))
            
            logger.debug(f"Kick API response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                chatroom_id = data.get('chatroom', {}).get('id')
                logger.info(f"Successfully got chatroom ID: {chatroom_id}")
                return chatroom_id
            else:
                logger.warning(f"Kick API error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error getting chatroom ID: {e}")
            import traceback
            traceback.print_exc()
        return None
    
    async def handle_message(self, raw_message: str):
        """Handle incoming Kick message"""
        try:
            data = json.loads(raw_message)
            
            if data.get('event') == 'App\\Events\\ChatMessageEvent':
                message_data = json.loads(data.get('data', '{}'))
                sender = message_data.get('sender', {})
                username = sender.get('username', 'Unknown')
                content = message_data.get('content', '')
                
                # Extract metadata
                import datetime
                metadata = {
                    'timestamp': datetime.datetime.now(),
                    'color': sender.get('identity', {}).get('color'),
                    'badges': sender.get('identity', {}).get('badges', [])
                }
                
                logger.info(f"[Kick] {username}: {content}")
                self.message_signal.emit(username, content)
                self.message_signal_with_metadata.emit(username, content, metadata)
                
        except Exception as e:
            logger.error(f"Error handling Kick message: {e}")
    
    def send_message(self, message: str):
        """Send a message to Kick chat"""
        # TODO: Implement message sending via Kick API
        pass
    
    def stop(self):
        """Stop the worker"""
        self.running = False
