"""
YouTube Platform Connector
Connects to YouTube Live Chat API
"""

import time
from platform_connectors.base_connector import BasePlatformConnector
from platform_connectors.qt_compat import QThread, pyqtSignal
from platform_connectors.connector_utils import startup_allowed, safe_emit
try:
    import requests
except Exception:
    requests = None
from core.logger import get_logger
try:
    from core.http_session import make_retry_session
except Exception:
    make_retry_session = None

# Dummy `requests` fallback so the module imports even when requests isn't installed.
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

logger = get_logger(__name__)


class YouTubeConnector(BasePlatformConnector):
    """Connector for YouTube Live Chat"""
    
    # Default YouTube OAuth credentials
    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = ""
    DEFAULT_PROJECT_ID = "audiblezenbot"
    DEFAULT_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
    DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
    DEFAULT_REDIRECT_URI = "http://localhost"
    
    def __init__(self, config=None):
        super().__init__()
        self.worker_thread = None
        self.worker = None
        self.config = config
        self.api_key = None
        self.oauth_token = None
        self.refresh_token = None
        self.client_id = self.DEFAULT_CLIENT_ID
        self.client_secret = self.DEFAULT_CLIENT_SECRET
        self.channel_id = None  # Store the actual YouTube channel ID
        
        # Load token from config if available
        if self.config:
            youtube_config = self.config.get_platform_config('youtube')
            token = youtube_config.get('oauth_token', '')
            if token:
                self.oauth_token = token
                logger.debug(f"[YouTubeConnector] Loaded OAuth token from config: {token[:10]}...")
            api_key = youtube_config.get('api_key', '')
            if api_key:
                self.api_key = api_key
                logger.debug(f"[YouTubeConnector] Loaded API key from config: {api_key[:10]}...")
            refresh = youtube_config.get('refresh_token', '')
            if refresh:
                self.refresh_token = refresh
                logger.debug(f"[YouTubeConnector] Loaded refresh token from config")
            # Load client credentials from config if present
            try:
                cid = youtube_config.get('client_id', '')
                csec = youtube_config.get('client_secret', '')
                if cid:
                    self.client_id = cid
                if csec:
                    self.client_secret = csec
            except Exception:
                pass
    
    def set_api_key(self, api_key: str):
        """Set YouTube Data API key"""
        self.api_key = api_key
    
    def set_token(self, token: str):
        """Set OAuth token"""
        self.oauth_token = token
        if self.config:
            self.config.set_platform_config('youtube', 'oauth_token', token)
    
    def set_refresh_token(self, refresh_token: str):
        """Set OAuth refresh token"""
        self.refresh_token = refresh_token
        if self.config:
            self.config.set_platform_config('youtube', 'refresh_token', refresh_token)
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return False
        
        try:
            session = make_retry_session() if make_retry_session else requests.Session()
            response = session.post(
                self.DEFAULT_TOKEN_URI,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': self.refresh_token,
                    'grant_type': 'refresh_token'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token')
                logger.info("YouTube token refreshed successfully")
                return True
            else:
                logger.error(f"YouTube token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"Error refreshing YouTube token: {e}")
            return False
    
    def connect(self, username: str):
        """Connect to YouTube Live Chat, ensuring no duplicate worker threads."""
        logger.info(f"[YouTubeConnector] Connecting to YouTube for channel: {username}")
        logger.debug(f"[YouTubeConnector] API Key: {'Set' if self.api_key else 'Not set'}")
        logger.debug(f"[YouTubeConnector] OAuth Token: {'Set' if self.oauth_token else 'Not set'}")

        self.username = username

        # Always disconnect/cleanup any previous worker/thread before starting a new one
        if self.worker:
            try:
                self.worker.stop()
            except Exception as e:
                logger.exception(f"[YouTubeConnector] Error stopping previous worker: {e}")
        if self.worker_thread:
            try:
                if self.worker_thread.isRunning():
                    self.worker_thread.quit()
                    self.worker_thread.wait(5000)
                    if self.worker_thread.isRunning():
                        logger.warning("[YouTubeConnector] WARNING: Previous worker thread did not stop in time!")
            except Exception as e:
                logger.exception(f"[YouTubeConnector] Error quitting previous worker thread: {e}")
        self.worker = None
        self.worker_thread = None

        # Try to refresh token if we have a refresh token
        if self.refresh_token and not self.oauth_token:
            logger.info("[YouTubeConnector] Attempting to refresh OAuth token...")
            self.refresh_access_token()

        # Check which account is authenticated
        if self.oauth_token:
            self.check_authenticated_user()

        def _resolve_channel_id_from_username(name: str):
            """Resolve a YouTube channel ID (UC...) from a human username or channel name.
            Returns channel ID string or None.
            """
            try:
                headers = {}
                params = {'part': 'id'}
                if self.oauth_token:
                    headers['Authorization'] = f'Bearer {self.oauth_token}'
                else:
                    params['forUsername'] = name
                # Try channels?forUsername first
                try:
                    session = make_retry_session() if make_retry_session else requests.Session()
                    resp = session.get(f'{YouTubeWorker.API_BASE}/channels', headers=headers, params=params, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get('items', [])
                        if items:
                            return items[0].get('id')
                except requests.exceptions.RequestException:
                    pass

                # Fallback: search for channel by query
                sparams = {'part': 'snippet', 'type': 'channel', 'q': name}
                if self.oauth_token:
                    headers['Authorization'] = f'Bearer {self.oauth_token}'
                else:
                    sparams['key'] = self.api_key
                try:
                    session = make_retry_session() if make_retry_session else requests.Session()
                    sresp = session.get(f'{YouTubeWorker.API_BASE}/search', headers=headers, params=sparams, timeout=5)
                    if sresp.status_code == 200:
                        sdata = sresp.json()
                        sitems = sdata.get('items', [])
                        if sitems:
                            cid = sitems[0].get('id', {}).get('channelId')
                            if cid:
                                return cid
                except requests.exceptions.RequestException:
                    pass
            except Exception:
                pass
            return None

        # Prefer explicit channel ID (starts with UC...)
        if username and isinstance(username, str) and username.startswith('UC') and len(username) == 24:
            channel_identifier = username
            logger.debug(f"[YouTubeConnector] Using provided channel ID: {channel_identifier}")
        else:
            # If a streamer channel_id is configured, prefer it
            platform_config = self.config.get_platform_config('youtube') if self.config else {}
            streamer_channel_id = platform_config.get('channel_id', '')
            if streamer_channel_id:
                channel_identifier = streamer_channel_id
                logger.debug(f"[YouTubeConnector] Using configured streamer channel_id: {channel_identifier}")
            else:
                # Attempt to resolve username to channel ID
                resolved = _resolve_channel_id_from_username(username)
                if resolved:
                    channel_identifier = resolved
                    logger.debug(f"[YouTubeConnector] Resolved username '{username}' to channel ID: {channel_identifier}")
                else:
                    channel_identifier = username
                    logger.debug(f"[YouTubeConnector] Using username as-is (may not resolve to channel ID): {channel_identifier}")

        # Create new worker and thread
        self.worker = YouTubeWorker(
            channel_identifier,
            self.api_key,
            self.oauth_token,
            self.client_id,
            self.client_secret,
            self.refresh_token
        )
        self.worker_thread = QThread()

        self.worker.moveToThread(self.worker_thread)
        self.worker.message_signal.connect(self.onMessageReceived)
        self.worker.deletion_signal.connect(self.onMessageDeleted)
        self.worker.status_signal.connect(self.onStatusChanged)
        self.worker.error_signal.connect(self.onError)

        self.worker_thread.started.connect(self.worker.run)
        if not startup_allowed():
            logger.info("[YouTubeConnector] CI mode: skipping YouTubeWorker thread start")
            return
        self.worker_thread.start()
    
    def check_authenticated_user(self):
        """Check which YouTube account is authenticated"""
        try:
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.get(
                    'https://www.googleapis.com/youtube/v3/channels',
                    headers={'Authorization': f'Bearer {self.oauth_token}'},
                    params={'part': 'snippet', 'mine': 'true'},
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTube] Network error checking authenticated user: {e}")
                return

            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    channel = data['items'][0]['snippet']
                    self.channel_id = data['items'][0]['id']
                    logger.info(f"[YouTube] ✓ Authenticated as: {channel.get('title')}")
                    logger.debug(f"[YouTube] Channel ID: {self.channel_id}")
                    logger.debug("[YouTube] Note: Can only delete messages if this is the channel owner or moderator")
                else:
                    logger.warning(f"[YouTube] ⚠ Warning: Could not determine authenticated channel")
            elif response.status_code == 401:
                logger.warning(f"[YouTube] ⚠ Authentication Error: OAuth token is invalid or expired")
                logger.info(f"[YouTube] ⚠ Please re-authenticate YouTube in the Connections page")
                logger.info(f"[YouTube] ⚠ Make sure to log in as the CHANNEL OWNER (not a viewer account)")
            else:
                logger.warning(f"[YouTube] ⚠ Warning: Could not verify authentication ({response.status_code})")
        except Exception as e:
            logger.exception(f"[YouTube] ⚠ Warning: Error checking authenticated user: {e}")
    
    def disconnect(self):
        """Disconnect from YouTube and ensure worker thread is fully stopped."""
        if self.worker:
            try:
                self.worker.stop()
            except Exception as e:
                logger.exception(f"[YouTubeConnector] Error stopping worker: {e}")
        if self.worker_thread:
            try:
                    if self.worker_thread.isRunning():
                        self.worker_thread.quit()
                        self.worker_thread.wait(8000)  # Wait up to 8 seconds for polite stop
                        if self.worker_thread.isRunning():
                            logger.warning("[YouTubeConnector] Worker thread did not stop in time! Forcing terminate().")
                            self.worker_thread.terminate()
                            self.worker_thread.wait(5000)
                            if self.worker_thread.isRunning():
                                logger.error("[YouTubeConnector] Worker thread STILL running after terminate().")
            except Exception as e:
                logger.exception(f"[YouTubeConnector] Error quitting worker thread: {e}")
        self.worker = None
        self.worker_thread = None
        self.connected = False
        safe_emit(self.connection_status, False)
    
    def send_message(self, message: str):
        """Send a message to YouTube chat"""
        try:
            # Prefer using the worker if available (worker handles live_chat_id and retries).
            if self.worker:
                try:
                    result = self.worker.send_message(message)
                    return bool(result)
                except Exception as e:
                    logger.exception(f"[YouTubeConnector] Worker send_message raised: {e}")
                    return False

            # If no worker exists but we have a token, we cannot reliably send without live_chat_id.
            logger.warning("[YouTubeConnector] send_message called but worker missing; cannot send without live_chat_id")
            return False
        except Exception as e:
            logger.exception(f"[YouTubeConnector] Exception while sending message: {e}")
            return False
    
    def delete_message(self, message_id: str):
        """Delete a message from YouTube chat
        
        Note: Requires channel owner or moderator permissions.
        The authenticated user must have permission to moderate the chat.
        """
        if not message_id or not self.oauth_token:
            logger.warning(f"[YouTube] Cannot delete message: missing message_id or oauth_token")
            return
        
        try:
            headers = {
                'Authorization': f'Bearer {self.oauth_token}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"[YouTube] Attempting to delete message: {message_id}")
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.delete(
                    f'{YouTubeWorker.API_BASE}/liveChat/messages',
                    headers=headers,
                    params={'id': message_id},
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTube] Network error deleting message: {e}")
                return
            
            # Check for token expiration
            if response.status_code == 401:
                logger.info(f"[YouTube] Token expired during delete, refreshing...")
                if self.worker and hasattr(self.worker, 'refresh_access_token'):
                    if self.worker.refresh_access_token():
                        self.oauth_token = self.worker.oauth_token
                        # Retry with new token
                        headers['Authorization'] = f'Bearer {self.oauth_token}'
                        try:
                            response = session.delete(
                                f'{YouTubeWorker.API_BASE}/liveChat/messages',
                                headers=headers,
                                params={'id': message_id},
                                timeout=10
                            )
                        except requests.exceptions.RequestException as e:
                            logger.exception(f"[YouTube] Network error retrying delete: {e}")
                            return
            
            if response.status_code == 204:
                logger.info(f"[YouTube] ✓ Message deleted successfully from YouTube's servers")
            elif response.status_code == 403:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Permission denied')
                logger.warning(f"[YouTube] ✗ Permission denied to delete message")
                logger.debug(f"[YouTube] Error: {error_msg}")
                logger.info(f"[YouTube] Note: You must authenticate as the channel owner or a moderator")
                logger.debug(f"[YouTube] Current auth may be for a viewer account")
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Bad request')
                logger.warning(f"[YouTube] ✗ Bad request: {error_msg}")
                logger.debug(f"[YouTube] Message ID may be invalid or already deleted")
            else:
                logger.error(f"[YouTube] ✗ Failed to delete message: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    logger.debug(f"[YouTube] Error details: {error_data}")
                except:
                    logger.debug(f"[YouTube] Response: {response.text}")
        except Exception as e:
            logger.exception(f"[YouTube] Error deleting message: {e}")
    
    def ban_user(self, username: str, user_id: str = None):
        """Ban a user from YouTube chat"""
        if not user_id or not self.oauth_token or not self.worker:
            logger.warning(f"[YouTube] Cannot ban user: missing requirements")
            return
        
        try:
            headers = {
                'Authorization': f'Bearer {self.oauth_token}',
                'Content-Type': 'application/json'
            }
            
            # Ban user via YouTube API
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    f'{YouTubeWorker.API_BASE}/liveChat/bans',
                    headers=headers,
                    params={'part': 'snippet'},
                    json={
                        'snippet': {
                            'liveChatId': self.worker.live_chat_id if hasattr(self.worker, 'live_chat_id') else '',
                            'type': 'permanent',
                            'bannedUserDetails': {
                                'channelId': user_id
                            }
                        }
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTube] Network error banning user: {e}")
                return

            if response.status_code == 200:
                logger.info(f"[YouTube] User banned: {username}")
            else:
                logger.error(f"[YouTube] Failed to ban user: {response.status_code}")
        except Exception as e:
            logger.exception(f"[YouTube] Error banning user: {e}")
    
    def onMessageReceived(self, username: str, message: str, metadata: dict):
        """Handle received message"""
        logger.debug(f"[YouTubeConnector] onMessageReceived: {username}, {message}, badges: {metadata.get('badges', [])}")
        safe_emit(self.message_received_with_metadata, 'youtube', username, message, metadata)
    
    def onMessageDeleted(self, message_id: str):
        """Handle message deletion event from YouTube
        
        NOTE: YouTube's Live Chat API rarely sends messageDeletedEvent through
        the polling endpoint, even with proper OAuth scopes. This handler will
        only trigger if YouTube actually sends the event (requires channel owner
        authentication with youtube.force-ssl scope and real-time session).
        
        For reliable deletion sync, messages are removed from UI immediately when
        the delete API call succeeds. Detecting deletions by OTHER moderators
        is not reliably supported by YouTube's API.
        """
        logger.debug(f"[YouTubeConnector] Message deleted by platform: {message_id}")
        safe_emit(self.message_deleted, 'youtube', message_id)
    
    def onStatusChanged(self, connected: bool):
        """Handle connection status change"""
        self.connected = connected
        safe_emit(self.connection_status, connected)
    
    def onError(self, error: str):
        """Handle error"""
        safe_emit(self.error_occurred, error)


class YouTubeWorker(QThread):
    """Worker thread for YouTube Live Chat connection"""
    
    message_signal = pyqtSignal(str, str, dict)  # username, message, metadata
    deletion_signal = pyqtSignal(str)  # message_id - emitted when message deleted
    status_signal = pyqtSignal(bool)
    error_signal = pyqtSignal(str)
    
    API_BASE = 'https://www.googleapis.com/youtube/v3'
    TOKEN_URI = 'https://oauth2.googleapis.com/token'
    
    def __init__(self, channel: str, api_key: str = None, oauth_token: str = None,
                 client_id: str = None, client_secret: str = None, refresh_token: str = None):
        super().__init__()
        self.channel = channel
        self.api_key = api_key
        self.oauth_token = oauth_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.running = False
        self.live_chat_id = None
        self.next_page_token = None
        self.processed_messages = set()
        
        # Message reliability features
        self.seen_message_ids = set()  # Track processed messages
        self.active_message_ids = set()  # Track currently active messages for deletion detection
        self.max_seen_ids = 10000  # Prevent unbounded growth
        self.last_message_time = None  # For health monitoring
        self.last_successful_poll = None  # Track polling health
        self.last_token_refresh = time.time()

    def _interruptible_sleep(self, total_seconds: float, interval: float = 0.25):
        """Sleep in short intervals checking self.running so the thread can stop promptly."""
        waited = 0.0
        while self.running and waited < total_seconds:
            time.sleep(min(interval, total_seconds - waited))
            waited += interval
    
    def run(self):
        # Prevent worker from running if disabled in config
        if hasattr(self, 'config') and self.config and self.config.get('platforms', {}).get('youtube', {}).get('disabled', False):
            logger.info("[YouTubeWorker] Skipping run: platform is disabled")
            return
        """Run the YouTube Live Chat connection"""
        logger.info(f"[YouTubeWorker] Starting worker for channel: {self.channel}")
        logger.debug(f"[YouTubeWorker] API Key: {'Set' if self.api_key else 'Not set'}")
        logger.debug(f"[YouTubeWorker] OAuth Token: {'Set' if self.oauth_token else 'Not set'}")
        self.running = True
        if not self.api_key and not self.oauth_token:
            error_msg = "No API key or OAuth token provided. Cannot connect to YouTube."
            logger.error(f"[YouTubeWorker] ERROR: {error_msg}")
            safe_emit(self.error_signal, error_msg)
            safe_emit(self.status_signal, False)
            return
        if self.api_key or self.oauth_token:
            # Real API connection
            retry_count = 0
            while self.running:
                try:
                    # Find active live broadcast
                    if not self.find_live_broadcast():
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 60)  # Cap at 1 minute
                        safe_emit(self.error_signal, f"No active live stream found (retrying in {wait_time}s)")
                        self._interruptible_sleep(wait_time)
                        continue
                    
                    # Reset retry count on success
                    retry_count = 0
                    safe_emit(self.status_signal, True)
                    
                    logger.debug(f"[YouTubeWorker] Starting message polling loop...")
                    
                    # Poll for messages
                    poll_count = 0
                    while self.running and self.live_chat_id:
                        try:
                            poll_count += 1
                            if poll_count % 10 == 1:  # Log every 10th poll
                                logger.debug(f"[YouTubeWorker] Poll #{poll_count} (live_chat_id: {self.live_chat_id[:20]}...)")
                            
                            # Refresh token if needed (every 50 minutes)
                            if time.time() - self.last_token_refresh > 3000:
                                if self.refresh_access_token():
                                    self.last_token_refresh = time.time()
                            
                            self.fetch_messages()
                            self.last_successful_poll = time.time()
                            self._interruptible_sleep(2)
                        except Exception as e:
                            logger.exception(f"[YouTubeWorker] Error in polling loop: {e}")
                            import traceback
                            traceback.print_exc()
                            safe_emit(self.error_signal, f"Error fetching messages: {str(e)}")
                            self._interruptible_sleep(5)
                            
                except Exception as e:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 300)  # Cap at 5 minutes
                    safe_emit(self.error_signal, f"Connection error (attempt {retry_count}): {str(e)}")
                    if self.running:
                        self._interruptible_sleep(wait_time)
                    else:
                        break
                    
            safe_emit(self.status_signal, False)
    
    def find_live_broadcast(self) -> bool:
        """Find the active live broadcast for the channel"""
        logger.debug(f"[YouTubeWorker] Searching for live broadcast on channel: {self.channel}")
        try:
            headers = {}
            params = {
                'part': 'snippet',
                'channelId': self.channel,
                'eventType': 'live',
                'type': 'video'
            }
            
            if self.oauth_token:
                headers['Authorization'] = f'Bearer {self.oauth_token}'
            else:
                params['key'] = self.api_key
            
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.get(
                    f'{self.API_BASE}/search',
                    headers=headers,
                    params=params,
                    timeout=5
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTubeWorker] Network error searching for live broadcast: {e}")
                safe_emit(self.error_signal, f"Network error searching for live broadcast: {e}")
                return False
            
            logger.debug(f"[YouTubeWorker] Search response status: {response.status_code}")
            
            # Check for quota exceeded error
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_code = error_data['error'].get('errors', [{}])[0].get('reason', '')
                        if error_code == 'quotaExceeded':
                            error_msg = "YouTube API quota exceeded. The daily limit has been reached. Please try again tomorrow or use a different API key."
                            logger.warning(f"[YouTubeWorker] QUOTA EXCEEDED: {error_msg}")
                            safe_emit(self.error_signal, error_msg)
                            self.is_active = False
                            return False
                except:
                    pass
            
            # Try to refresh token if unauthorized
            if response.status_code == 401 and self.oauth_token and self.refresh_token:
                logger.info(f"[YouTubeWorker] Token expired, attempting refresh...")
                if self.refresh_access_token():
                    logger.info(f"[YouTubeWorker] Token refreshed, retrying search...")
                    # Retry with new token
                    headers['Authorization'] = f'Bearer {self.oauth_token}'
                    try:
                        response = session.get(
                            f'{self.API_BASE}/search',
                            headers=headers,
                            params=params,
                            timeout=5
                        )
                        logger.debug(f"[YouTubeWorker] Retry response status: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        logger.exception(f"[YouTubeWorker] Network error retrying search: {e}")
                        safe_emit(self.error_signal, f"Network error retrying search: {e}")
                        return False
            
            if response.status_code != 200:
                logger.error(f"[YouTubeWorker] Search failed: {response.text}")
                response.raise_for_status()
            
            data = response.json()
            logger.debug(f"[YouTubeWorker] Search response: {data}")
            
            if 'items' in data and len(data['items']) > 0:
                video_id = data['items'][0]['id']['videoId']
                logger.info(f"[YouTubeWorker] ✓ Found live video: {video_id}")
                return self.get_live_chat_id(video_id)
            else:
                logger.info(f"[YouTubeWorker] No live broadcasts found for channel {self.channel}")
                if 'error' in data:
                    logger.error(f"[YouTubeWorker] API Error: {data['error']}")
            
            return False
            
        except Exception as e:
            safe_emit(self.error_signal, f"Error finding broadcast: {str(e)}")
            return False
    
    def get_live_chat_id(self, video_id: str) -> bool:
        """Get the live chat ID for a video"""
        logger.debug(f"[YouTubeWorker] Getting live chat ID for video: {video_id}")
        try:
            headers = {}
            params = {
                'part': 'liveStreamingDetails',
                'id': video_id
            }
            
            if self.oauth_token:
                headers['Authorization'] = f'Bearer {self.oauth_token}'
            else:
                params['key'] = self.api_key
            
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.get(
                    f'{self.API_BASE}/videos',
                    headers=headers,
                    params=params,
                    timeout=5
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTubeWorker] Network error getting chat ID: {e}")
                safe_emit(self.error_signal, f"Network error getting chat ID: {e}")
                return False

            if response.status_code != 200:
                logger.error(f"[YouTubeWorker] Get chat ID failed: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            data = response.json()
            logger.debug(f"[YouTubeWorker] Video details response: {data}")
            
            if 'items' in data and len(data['items']) > 0:
                live_details = data['items'][0].get('liveStreamingDetails', {})
                self.live_chat_id = live_details.get('activeLiveChatId')
                
                if self.live_chat_id:
                    logger.info(f"[YouTubeWorker] ✓ Got live chat ID: {self.live_chat_id}")
                    return True
                else:
                    logger.warning(f"[YouTubeWorker] ⚠ No activeLiveChatId in liveStreamingDetails: {live_details}")
            else:
                logger.warning(f"[YouTubeWorker] ⚠ No items in video details response")
            
            return False
            
        except Exception as e:
            safe_emit(self.error_signal, f"Error getting chat ID: {str(e)}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return False
        
        try:
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    self.TOKEN_URI,
                    data={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'refresh_token': self.refresh_token,
                        'grant_type': 'refresh_token'
                    },
                    timeout=5
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTubeWorker] Network error refreshing worker token: {e}")
                return False

            if response.status_code == 200:
                data = response.json()
                self.oauth_token = data.get('access_token')
                logger.info("YouTube worker token refreshed successfully")
                return True
            else:
                logger.error(f"YouTube worker token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"Error refreshing YouTube worker token: {e}")
            return False
    
    def fetch_messages(self):
        """Fetch new chat messages"""
        if not self.live_chat_id:
            logger.debug("[YouTubeWorker] No live chat ID, skipping fetch")
            return
        
        try:
            headers = {}
            params = {
                'liveChatId': self.live_chat_id,
                'part': 'snippet,authorDetails',
                'maxResults': 200
            }
            
            if self.next_page_token:
                params['pageToken'] = self.next_page_token
            
            if self.oauth_token:
                headers['Authorization'] = f'Bearer {self.oauth_token}'
            else:
                params['key'] = self.api_key
            
            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.get(
                    f'{self.API_BASE}/liveChat/messages',
                    headers=headers,
                    params=params,
                    timeout=2
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTubeWorker] Network error fetching messages: {e}")
                safe_emit(self.error_signal, f"Network error fetching messages: {e}")
                return
            
            # Check for quota exceeded error
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_code = error_data['error'].get('errors', [{}])[0].get('reason', '')
                        if error_code == 'quotaExceeded':
                            error_msg = "YouTube API quota exceeded. Stopping message polling."
                            logger.warning(f"[YouTubeWorker] QUOTA EXCEEDED: {error_msg}")
                            safe_emit(self.error_signal, error_msg)
                            self.is_active = False
                            return
                except:
                    pass
            
            if response.status_code != 200:
                logger.error(f"[YouTubeWorker] Fetch messages failed: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            data = response.json()
            
            # Debug: Log all event types in the response
            items = data.get('items', [])
            event_types = [item.get('snippet', {}).get('type') for item in items]
            if event_types and any(t != 'textMessageEvent' for t in event_types):
                logger.debug(f"[YouTubeWorker] Event types in response: {set(event_types)}")
            
            # Update next page token
            self.next_page_token = data.get('nextPageToken')
            polling_interval = data.get('pollingIntervalMillis', 2000) / 1000
            
            items = data.get('items', [])
            logger.debug(f"[YouTubeWorker] Fetched {len(items)} messages")
            
            # Track current batch of message IDs to detect deletions
            current_message_ids = set()
            
            # Process messages
            for item in items:
                # Debug: log item type
                snippet = item.get('snippet', {})
                message_type = snippet.get('type')
                
                # Log ALL non-text events for debugging
                if message_type and message_type != 'textMessageEvent':
                    logger.debug(f"[YouTubeWorker] Non-text event detected: type={message_type}")
                    logger.debug(f"[YouTubeWorker] Full snippet: {snippet}")
                
                # Message deduplication
                msg_id = item.get('id')
                if not msg_id:
                    continue
                
                current_message_ids.add(msg_id)
                
                if msg_id in self.seen_message_ids:
                    continue  # Skip duplicate
                
                # Add to seen messages
                self.seen_message_ids.add(msg_id)
                
                # Limit size to prevent unbounded memory growth
                if len(self.seen_message_ids) > self.max_seen_ids:
                    self.seen_message_ids = set(list(self.seen_message_ids)[self.max_seen_ids // 2:])
                
                snippet = item.get('snippet', {})
                message_type = snippet.get('type')
                
                # Check for deleted message events
                if message_type == 'messageDeletedEvent':
                    deleted_msg_id = snippet.get('messageDeletedDetails', {}).get('deletedMessageId')
                    if deleted_msg_id:
                        logger.info(f"[YouTubeWorker] Message deleted by moderator: {deleted_msg_id}")
                        safe_emit(self.deletion_signal, deleted_msg_id)
                        # Remove from active set
                        self.active_message_ids.discard(deleted_msg_id)
                    continue
                
                # Only process text messages
                if message_type != 'textMessageEvent':
                    continue
                
                # Add to active messages
                self.active_message_ids.add(msg_id)
                
                author_details = item.get('authorDetails', {})
                
                # Only process text messages
                if snippet.get('type') != 'textMessageEvent':
                    continue
                
                username = author_details.get('displayName', 'Unknown')
                message = snippet.get('displayMessage', '')
                
                # Validate essential data
                if not username or not message:
                    logger.debug(f"[YouTubeWorker] Skipping message with missing data: username={username}, message={message}")
                    continue
                # Parse badges from authorDetails
                badges = []
                if author_details.get('isChatOwner'):
                    badges.append('owner')
                if author_details.get('isChatModerator'):
                    badges.append('moderator')
                if author_details.get('isChatSponsor'):
                    badges.append('member')
                if author_details.get('isVerified'):
                    badges.append('verified')
                
                # Build metadata
                metadata = {
                    'badges': badges,
                    'color': None,  # YouTube doesn't provide color in API
                    'timestamp': snippet.get('publishedAt'),
                    'message_id': msg_id,
                    'user_id': author_details.get('channelId'),
                    'avatar': author_details.get('profileImageUrl')
                }
                
                self.last_message_time = time.time()  # Update health timestamp
                logger.debug(f"[YouTubeWorker] Chat: {username}: {message}")
                from .connector_utils import emit_chat
                emit_chat(self, 'youtube', username, message, metadata)
                
        except Exception as e:
            raise Exception(f"Message fetch error: {str(e)}")
    
    def stop(self):
        """Stop the worker"""
        self.running = False
    
    def send_message(self, message: str):
        """Send a message to YouTube chat"""
        if not self.live_chat_id or not self.oauth_token:
            logger.warning("[YouTubeWorker] Cannot send message: missing live_chat_id or oauth_token")
            return False

        try:
            # Debug: Show which token is being used
            token_prefix = self.oauth_token[:12] if self.oauth_token else "None"
            logger.debug(f"[YouTubeWorker] send_message: Using token (first 12 chars): {token_prefix}...")

            headers = {
                'Authorization': f'Bearer {self.oauth_token}',
                'Content-Type': 'application/json'
            }

            data = {
                'snippet': {
                    'liveChatId': self.live_chat_id,
                    'type': 'textMessageEvent',
                    'textMessageDetails': {
                        'messageText': message
                    }
                }
            }

            session = make_retry_session() if make_retry_session else requests.Session()
            try:
                response = session.post(
                    f'{self.API_BASE}/liveChat/messages?part=snippet',
                    headers=headers,
                    json=data,
                    timeout=10
                )
                response.raise_for_status()
                return True
            except requests.exceptions.RequestException as e:
                logger.exception(f"[YouTubeWorker] Network error sending message: {e}")
                safe_emit(self.error_signal, f"Failed to send message due to network error: {e}")
                return False
            except Exception as e:
                safe_emit(self.error_signal, f"Failed to send message: {str(e)}")
                return False

        except Exception as e:
            safe_emit(self.error_signal, f"Failed to send message: {str(e)}")
            return False
