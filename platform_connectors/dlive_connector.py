"""
DLive Platform Connector - WebSocket Subscriptions Implementation

DLive uses GraphQL subscriptions over WebSocket for real-time chat.
WebSocket endpoint: wss://graphigostream.prd.dlive.tv
Protocol: graphql-ws
"""

from platform_connectors.base_connector import BasePlatformConnector
from PyQt6.QtCore import QThread, pyqtSignal
import asyncio
import json
import time
import websockets
try:
    import requests
except Exception:
    requests = None
from core.logger import get_logger

logger = get_logger(__name__)


def _make_retry_session(total: int = 3, backoff_factor: float = 1.0):
    """Create a requests.Session with urllib3 Retry configured for transient errors."""
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry

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


class DLiveConnector(BasePlatformConnector):
    """Connector for DLive chat"""
    
    def __init__(self, config=None):
        super().__init__()
        self.worker = None
        self.config = config
        self.access_token = None
        
        # Load token from config if available
        if self.config:
            token = self.config.get_platform_config('dlive').get('access_token', '')
            if token:
                self.access_token = token
    
    def set_token(self, token: str):
        """Set access token for DLive API"""
        if token:
            self.access_token = token
            if self.config:
                self.config.set_platform_config('dlive', 'access_token', token)
    
    def connect(self, username: str):
        """Connect to DLive chat"""
        logger.info(f"[DLiveConnector] connect() called for username: {username}")
        self.username = username
        
        # Disconnect existing worker first to prevent duplicates
        if self.worker:
            logger.info(f"[DLiveConnector] Disconnecting existing worker before creating new one")
            self.disconnect()
        
        self.worker = DLiveWorker(username, self.access_token)
        self.worker.message_signal.connect(self.onMessageReceived)
        self.worker.deletion_signal.connect(self.onMessageDeleted)
        self.worker.status_signal.connect(self.onStatusChanged)
        self.worker.error_signal.connect(self.onError)
        self.worker.start()
    
    def disconnect(self):
        """Disconnect from DLive"""
        logger.info("[DLiveConnector] disconnect() called")
        if self.worker:
            self.worker.stop()
            self.worker.wait(5000)  # Wait up to 5 seconds
        
        self.connected = False
        self.connection_status.emit(False)
    
    def send_message(self, message: str):
        """Send a message to DLive chat"""
        if self.worker and self.connected:
            self.worker.send_message(message)
    
    def delete_message(self, message_id: str):
        """Delete a message from DLive chat
        
        Note: DLive's deleteMessage mutation requires an integer ID, but chat messages
        use UUID strings (e.g., "048ed640-bbe1-4261-9da6-9adb304c8a54"). 
        Message deletion may not be supported for regular chat messages.
        """
        if not message_id or not self.access_token:
            logger.warning(f"[DLive] Cannot delete message: missing message_id or access_token")
            return

        logger.info("[DLive] Message deletion not currently supported (API requires integer ID, messages use UUID)")
        logger.debug(f"[DLive] Message ID was: {message_id}")
        return False
    
    def ban_user(self, username: str, user_id: str = None):
        """Ban a user from DLive chat"""
        if not username or not self.access_token:
            return
        
        try:
            # DLive uses GraphQL for banning
            mutation = '''
            mutation BanStreamChatUser($streamer: String!, $username: String!) {
                banStreamChatUser(streamer: $streamer, username: $username) {
                    err {
                        message
                    }
                }
            }
            '''
            
            try:
                session = _make_retry_session()
                response = session.post(
                    'https://graphigo.prd.dlive.tv/',
                    headers={
                        'Authorization': self.access_token,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'query': mutation,
                        'variables': {
                            'streamer': self.username,
                            'username': username
                        }
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[DLive] Network error banning user: {e}")
                return

            if response.status_code == 200:
                logger.info(f"[DLive] User banned: {username}")
            else:
                logger.error(f"[DLive] Failed to ban user: {response.status_code}")
        except Exception as e:
            logger.exception(f"[DLive] Error banning user: {e}")
    
    def onMessageReceived(self, username: str, message: str, metadata: dict):
        logger.debug(f"[DLiveConnector] onMessageReceived: {username}, {message}, metadata: {metadata}")
        self.message_received_with_metadata.emit('dlive', username, message, metadata)
    
    def onMessageDeleted(self, message_id: str):
        """Handle message deletion event from DLive"""
        logger.info(f"[DLiveConnector] Message deleted by platform: {message_id}")
        self.message_deleted.emit('dlive', message_id)
    
    def onStatusChanged(self, connected: bool):
        self.connected = connected
        self.connection_status.emit(connected)
    
    def onError(self, error: str):
        logger.error(f"[DLiveConnector] Error: {error}")
        self.error_occurred.emit(error)


class DLiveWorker(QThread):
    """Worker thread for DLive WebSocket subscriptions"""
    
    message_signal = pyqtSignal(str, str, dict)  # username, message, metadata
    deletion_signal = pyqtSignal(str)  # message_id - emitted when message deleted
    status_signal = pyqtSignal(bool)
    error_signal = pyqtSignal(str)
    
    WS_URL = "wss://graphigostream.prd.dlive.tv"
    GRAPHQL_URL = "https://graphigo.prd.dlive.tv/"
    
    def __init__(self, username: str, access_token: str | None = None):
        super().__init__()
        self.displayname = username  # Display name (e.g., "AudibleZenLife")
        self.username = None  # Actual username (e.g., "dlive-igkpwvgtfc")
        self.access_token = access_token
        self.running = False
        self.loop = None
        self.connection_time = None
        self.ws = None
        self.subscription_id = "1"
        
        # Message deduplication tracking
        self.seen_message_ids = set()
        self.max_seen_ids = 10000  # Prevent unbounded memory growth
        
        # Health monitoring
        self.last_message_time = None
        self.health_check_interval = 30  # Check every 30 seconds
        self.connection_timeout = 120  # Consider dead after 2 minutes of silence
        # WebSocket open/connect timeout (seconds)
        self.open_timeout = 10
        # Ping interval for websockets (None -> library default)
        self.ping_interval = 20
    
    def resolve_username(self):
        """Resolve display name to actual DLive username"""
        try:
            logger.debug(f"[DLiveWorker] Resolving username for displayname: {self.displayname}")
            
            query = """
            query UserQuery($displayname: String!) {
                userByDisplayName(displayname: $displayname) {
                    username
                    displayname
                }
            }
            """
            
            # Parse token if it's stored as JSON
            token = self.access_token
            if token and token.startswith('{'):
                try:
                    token_data = json.loads(token)
                    token = token_data.get('token', token)
                except:
                    pass
            
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = token
            
            try:
                session = _make_retry_session()
                response = session.post(
                    self.GRAPHQL_URL,
                    headers=headers,
                    json={
                        "query": query,
                        "variables": {"displayname": self.displayname}
                    },
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                logger.exception(f"[DLiveWorker] Network error resolving username: {e}")
                return False
            
            if response.status_code == 200:
                data = response.json()
                user = data.get('data', {}).get('userByDisplayName')
                if user:
                    self.username = user.get('username')
                    logger.info(f"[DLiveWorker] ✓ Resolved username: {self.username}")
                    return True
                else:
                    logger.warning(f"[DLiveWorker] ❌ User not found: {self.displayname}")
                    return False
            else:
                logger.error(f"[DLiveWorker] ❌ Failed to resolve username: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"[DLiveWorker] ❌ Error resolving username: {e}")
            return False
    
    def run(self):
        # Prevent worker from running if disabled in config
        if hasattr(self, 'config') and self.config and self.config.get('platforms', {}).get('dlive', {}).get('disabled', False):
            logger.info("[DLiveWorker] Skipping run: platform is disabled")
            return
        logger.info("[DLiveWorker] Starting run()")
        self.running = True
        self.connection_time = time.time()
        # Resolve display name to actual username first
        if not self.resolve_username():
            self.error_signal.emit(f"Failed to resolve DLive username for: {self.displayname}")
            return
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            logger.debug("[DLiveWorker] Event loop created, connecting with auto-retry...")
            try:
                self.loop.run_until_complete(self.connect_with_retry())
            except Exception as e:
                import traceback
                logger.exception(f"[DLiveWorker] Error in event loop: {type(e).__name__}: {e}")
                logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
                self.error_signal.emit(str(e))
            finally:
                if self.loop and not self.loop.is_closed():
                    logger.debug("[DLiveWorker] Closing event loop")
                    self.loop.close()
        except Exception as e:
            import traceback
            logger.exception(f"[DLiveWorker] Exception in run(): {type(e).__name__}: {e}")
            logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
            self.error_signal.emit(str(e))
    
    async def connect_with_retry(self, max_retries=10):
        """Connect with automatic retry and exponential backoff"""
        retry_count = 0
        backoff = 1  # Start with 1 second
        
        while self.running and retry_count < max_retries:
            try:
                logger.info(f"[DLiveWorker] Connection attempt {retry_count + 1}/{max_retries}")
                await self.connect_and_listen()
                # If we get here, connect_and_listen returned without raising.
                # Treat that as a clean exit (no retry).
                logger.info("[DLiveWorker] connect_and_listen returned (clean exit)")
                break
            except asyncio.CancelledError:
                # Treat cancellation as transient and attempt retry with backoff
                retry_count += 1
                logger.warning(f"[DLiveWorker] Connection cancelled (attempt {retry_count}) - will retry")
            except Exception as e:
                retry_count += 1
                logger.warning(f"[DLiveWorker] Connection failed: {type(e).__name__}: {e}")

            # Common retry/backoff path for transient failures
            if retry_count < max_retries and self.running:
                # Exponential backoff with max 60 seconds
                wait_time = min(backoff * (2 ** (retry_count - 1)), 60)
                logger.info(f"[DLiveWorker] Retrying in {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                self.status_signal.emit(False)
                await asyncio.sleep(wait_time)
            elif retry_count >= max_retries:
                logger.error(f"[DLiveWorker] Max retries ({max_retries}) reached, giving up")
                self.error_signal.emit(f"Connection failed after {max_retries} attempts")
                self.status_signal.emit(False)
                break
    
    async def connect_and_listen(self):
        """Connect to WebSocket and listen for messages"""
        try:
            logger.info(f"[DLiveWorker] Connecting to: {self.WS_URL}")
            logger.debug(f"[DLiveWorker] Display Name: {self.displayname}")
            logger.debug(f"[DLiveWorker] Actual Username: {self.username}")
            logger.debug(f"[DLiveWorker] Has access token: {bool(self.access_token)}")
            
            # Parse token if it's stored as JSON
            token = self.access_token
            if token and token.startswith('{'):
                try:
                    token_data = json.loads(token)
                    token = token_data.get('token', token)
                    logger.debug(f"[DLiveWorker] Extracted token from JSON for WebSocket")
                except:
                    pass
            
            # Connect with graphql-ws subprotocol
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            # Use an explicit open timeout and a ping interval to surface
            # connection problems faster and avoid long hangs in connect().
            async with websockets.connect(
                self.WS_URL,
                subprotocols=["graphql-ws"],
                extra_headers=headers,
                open_timeout=self.open_timeout,
                ping_interval=self.ping_interval,
            ) as websocket:
                self.ws = websocket
                logger.info("[DLiveWorker] WebSocket connected")
                
                # Send connection_init
                init_payload = {}
                if token:
                    init_payload["Authorization"] = f"Bearer {token}"
                
                init_message = {
                    "type": "connection_init",
                    "payload": init_payload
                }
                await websocket.send(json.dumps(init_message))
                logger.debug("[DLiveWorker] Sent connection_init")
                
                # Wait for connection_ack
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                msg = json.loads(response)
                logger.debug(f"[DLiveWorker] Received: {msg.get('type')}")
                
                if msg.get("type") == "connection_ack":
                    logger.info("[DLiveWorker] Connection acknowledged")
                    self.status_signal.emit(True)
                    
                    # Subscribe to chat
                    await self.subscribe_to_chat(websocket)
                    
                    # Listen for messages
                    await self.listen_for_messages(websocket)
                else:
                    logger.warning(f"[DLiveWorker] Unexpected response: {msg}")
                    self.error_signal.emit("Connection not acknowledged")
                    self.status_signal.emit(False)
                    
        except websockets.exceptions.WebSocketException as e:
            logger.exception(f"[DLiveWorker] WebSocket error: {e}")
            self.error_signal.emit(f"WebSocket error: {e}")
            self.status_signal.emit(False)
            # Re-raise so the retry loop can handle backoff
            raise
        except asyncio.CancelledError:
            logger.warning(f"[DLiveWorker] Connection attempt cancelled")
            self.status_signal.emit(False)
            raise
        except Exception as e:
            import traceback
            logger.exception(f"[DLiveWorker] Connection error: {type(e).__name__}: {e}")
            logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
            self.error_signal.emit(f"Connection error: {e}")
            self.status_signal.emit(False)
            # Re-raise to allow connect_with_retry to perform backoff
            raise
    
    async def health_check_loop(self, websocket):
        """Monitor connection health and detect dead connections"""
        try:
            while self.running:
                await asyncio.sleep(self.health_check_interval)
                
                # Check if we've received any message recently
                if self.last_message_time:
                    time_since_last = time.time() - self.last_message_time
                    
                    if time_since_last > self.connection_timeout:
                        logger.warning(f"[DLiveWorker] ⚠ No messages for {time_since_last:.0f}s, connection may be dead")
                        logger.info(f"[DLiveWorker] Forcing reconnection...")
                        # Close the websocket to trigger reconnection
                        await websocket.close()
                        break
                    elif time_since_last > self.health_check_interval:
                        logger.debug(f"[DLiveWorker] Connection healthy (last message: {time_since_last:.0f}s ago)")
        except asyncio.CancelledError:
            logger.debug("[DLiveWorker] Health check cancelled")
        except Exception as e:
            logger.exception(f"[DLiveWorker] Health check error: {e}")
    
    async def subscribe_to_chat(self, websocket):
        """Subscribe to streamMessageReceived"""
        subscription = """
        subscription StreamMessageSubscription($streamer: String!) {
            streamMessageReceived(streamer: $streamer) {
                type
                ... on ChatText {
                    id
                    content
                    createdAt
                    sender {
                        displayname
                        username
                        avatar
                        partnerStatus
                    }
                }
                ... on ChatGift {
                    id
                    gift
                    amount
                    recentCount
                    sender {
                        displayname
                        username
                    }
                }
                ... on ChatFollow {
                    id
                    sender {
                        displayname
                        username
                    }
                }
                ... on ChatSubscription {
                    id
                    month
                    sender {
                        displayname
                        username
                    }
                }
            }
        }
        """
        
        subscribe_message = {
            "id": self.subscription_id,
            "type": "start",
            "payload": {
                "query": subscription,
                "variables": {
                    "streamer": self.username  # DLive requires lowercase username
                }
            }
        }
        
        await websocket.send(json.dumps(subscribe_message))
        logger.info(f"[DLiveWorker] Sent subscription for username: {self.username}")
        logger.debug(f"[DLiveWorker] Full subscription: {json.dumps(subscribe_message, indent=2)}")
        
        # Wait for responses (error or keep-alive)
        try:
            for _ in range(3):  # Check multiple messages
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                data = json.loads(response)
                msg_type = data.get('type')
                msg_id = data.get('id')
                
                logger.debug(f"[DLiveWorker] Post-subscribe response: type={msg_type}, id={msg_id}")
                
                if msg_type == 'error':
                    if msg_id == self.subscription_id:
                        logger.error(f"[DLiveWorker] ❌ SUBSCRIPTION ERROR: {json.dumps(data, indent=2)}")
                        self.error_signal.emit(f"Subscription failed: {data}")
                        return
                    else:
                        logger.warning(f"[DLiveWorker] Other error: {json.dumps(data, indent=2)}")
                elif msg_type == 'data' and msg_id == self.subscription_id:
                    logger.info(f"[DLiveWorker] ✓ Subscription active - received data message")
                    break
                elif msg_type == 'ka':
                    logger.debug(f"[DLiveWorker] Keep-alive received")
                    break
        except asyncio.TimeoutError:
            logger.debug(f"[DLiveWorker] No error after 9s - subscription likely successful")
        except Exception as e:
            logger.exception(f"[DLiveWorker] Error checking subscription: {e}")
    
    async def listen_for_messages(self, websocket):
        """Listen for incoming messages with health monitoring"""
        logger.info(f"[DLiveWorker] Now listening for chat messages...")
        logger.debug(f"[DLiveWorker] TIP: Send a test message in your DLive chat to verify it works!")
        logger.debug(f"[DLiveWorker] NOTE: Messages only appear when stream is LIVE and someone chats")
        
        # Start health monitoring in background
        health_task = asyncio.create_task(self.health_check_loop(websocket))
        
        try:
            message_count = 0
            while self.running:
                try:
                    # Use timeout to periodically check if we're still running
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    message_count += 1
                    self.last_message_time = time.time()  # Update timestamp
                    
                    logger.debug(f"[DLiveWorker] RAW MESSAGE #{message_count}: {message[:200]}...")
                    data = json.loads(message)
                    
                    msg_type = data.get("type")
                    msg_id = data.get("id", "N/A")
                    logger.debug(f"[DLiveWorker] Parsed message type: {msg_type}, id: {msg_id}")
                    
                    if msg_type == "data":
                        # Process subscription data
                        payload = data.get("payload", {})
                        logger.debug(f"[DLiveWorker] Data payload: {json.dumps(payload, indent=2)[:500]}")
                        
                        if "errors" in payload:
                            logger.warning(f"[DLiveWorker] Subscription errors: {payload['errors']}")
                            continue
                        
                        # Extract message
                        stream_msg = payload.get("data", {}).get("streamMessageReceived")
                        if stream_msg:
                            logger.debug(f"[DLiveWorker] Processing stream message: {stream_msg}")
                            try:
                                # streamMessageReceived returns a LIST of messages
                                if isinstance(stream_msg, list):
                                    for msg in stream_msg:
                                        self.process_message(msg)
                                else:
                                    # Single message (shouldn't happen but handle it)
                                    self.process_message(stream_msg)
                            except Exception as e:
                                logger.exception(f"[DLiveWorker] ⚠ Error processing message (continuing): {e}")
                                import traceback
                                logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
                                # Don't stop listening - continue to next message
                        else:
                            logger.debug(f"[DLiveWorker] No streamMessageReceived in payload")
                    
                    elif msg_type == "error":
                        error_data = data.get('payload', data)
                        logger.error(f"[DLiveWorker] Full error response: {json.dumps(data, indent=2)}")
                        
                        error_msg = error_data[0].get('message', '') if isinstance(error_data, list) else error_data.get('message', '')
                        
                        # DLive sometimes returns empty error messages for successful mutations
                        # If the error message is empty and this is a send_msg response, treat as success
                        if not error_msg and data.get('id') == 'send_msg':
                            logger.info(f"[DLiveWorker] ✓ Message mutation completed (empty error = success)")
                            # But also check if there's actually data in the response
                            if 'data' in data:
                                logger.debug(f"[DLiveWorker] Response also contains data: {json.dumps(data.get('data'), indent=2)}")
                        else:
                            logger.error(f"[DLiveWorker] Error from server: {json.dumps(error_data, indent=2)}")
                            if error_msg:
                                self.error_signal.emit(f"Server error: {error_msg}")
                            
                            # If this is a subscription error, it might be the wrong username format
                            if data.get('id') == '1':
                                logger.warning(f"[DLiveWorker] Subscription error - check username format")
                    
                    elif msg_type == "complete":
                        logger.info("[DLiveWorker] Subscription completed")
                        break
                    
                    elif msg_type == "ka":
                        # Keep-alive - connection is healthy
                        logger.debug("[DLiveWorker] ✓ Keep-alive received")
                        pass
                
                except asyncio.TimeoutError:
                    # No message received in timeout period
                    logger.debug(f"[DLiveWorker] ⏱ No messages for 30s (total received: {message_count})")
                    # Check if we're still connected
                    try:
                        pong = await websocket.ping()
                        await asyncio.wait_for(pong, timeout=5)
                        logger.debug("[DLiveWorker] ✓ Ping successful, connection alive")
                    except Exception as e:
                        logger.warning(f"[DLiveWorker] ❌ Ping failed: {e}")
                        raise
                    continue
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"[DLiveWorker] ⚠ Invalid JSON received (continuing): {e}")
                    # Continue listening despite bad message
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("[DLiveWorker] WebSocket connection closed")
            self.status_signal.emit(False)
        except Exception as e:
            import traceback
            logger.exception(f"[DLiveWorker] Error listening: {type(e).__name__}: {e}")
            logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
            self.error_signal.emit(f"Listening error: {e}")
        finally:
            # Cancel health monitoring
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass
    
    def process_message(self, msg):
        """Process a chat message with deduplication and error handling"""
        try:
            # Message deduplication
            msg_id = msg.get('id')
            logger.debug(f"[DLiveWorker] process_message called with msg_id: {msg_id}")
            logger.debug(f"[DLiveWorker] Current seen_message_ids size: {len(self.seen_message_ids)}")
            
            if msg_id:
                if msg_id in self.seen_message_ids:
                    logger.debug(f"[DLiveWorker] ✓ Skipping duplicate message: {msg_id}")
                    return
                
                # Add to seen messages
                self.seen_message_ids.add(msg_id)
                logger.debug(f"[DLiveWorker] Added {msg_id} to seen_message_ids")
                
                # Limit size to prevent unbounded memory growth
                if len(self.seen_message_ids) > self.max_seen_ids:
                    # Keep only the most recent half
                    self.seen_message_ids = set(list(self.seen_message_ids)[self.max_seen_ids // 2:])
                    logger.debug(f"[DLiveWorker] Trimmed seen_message_ids to {len(self.seen_message_ids)}")
            
            msg_type = msg.get("type") or msg.get("__typename")
            
            if msg_type in ("ChatText", "Message"):
                # Regular chat message
                sender = msg.get("sender", {})
                username = sender.get("displayname") or sender.get("username", "Unknown")
                content = msg.get("content", "")
                
                # Validate essential data
                if not username or not content:
                    logger.warning(f"[DLiveWorker] ⚠ Incomplete message data, skipping: {msg}")
                    return
                
                # Parse badges
                badges = []
                partner_status = sender.get("partnerStatus")
                if partner_status and partner_status != "NONE":
                    badges.append(partner_status.lower())
                
                metadata = {
                    'badges': badges,
                    'user_id': sender.get('username'),
                    'avatar': sender.get('avatar'),
                    'timestamp': msg.get('createdAt', 0),
                    'message_id': msg.get('id')
                }
                
                logger.info(f"[DLiveWorker] Chat: {username}: {content}")
                from .connector_utils import emit_chat
                emit_chat(self, 'dlive', username, content, metadata)
            
            elif msg_type == "ChatGift":
                # Gift message
                sender = msg.get("sender", {})
                username = sender.get("displayname") or sender.get("username", "Unknown")
                gift = msg.get("gift", "gift")
                amount = msg.get("amount", 1)
                
                if not username:
                    logger.warning(f"[DLiveWorker] ⚠ Gift message missing username, skipping")
                    return
                
                content = f"sent {amount}x {gift}"
                
                metadata = {
                    'badges': ['gift'],
                    'user_id': sender.get('username'),
                    'message_id': msg.get('id')
                }
                
                logger.info(f"[DLiveWorker] Gift: {username} {content}")
                from .connector_utils import emit_chat
                emit_chat(self, 'dlive', username, content, metadata)
            
            elif msg_type == "ChatFollow":
                # Follow message
                sender = msg.get("sender", {})
                username = sender.get("displayname") or sender.get("username", "Unknown")
                
                if not username:
                    logger.warning(f"[DLiveWorker] ⚠ Follow message missing username, skipping")
                    return
                
                event_data = {
                    'user_id': sender.get('username'),
                    'message_id': msg.get('id')
                }
                
                logger.info(f"[DLiveWorker] Follow: {username}")
                # Emit as stream event instead of regular message
                from .connector_utils import emit_chat
                emit_chat(self, 'dlive', username, "🎯 followed the stream", {'event_type': 'follow', **event_data})
            
            elif msg_type == "ChatSubscription":
                # Subscription message
                sender = msg.get("sender", {})
                username = sender.get("displayname") or sender.get("username", "Unknown")
                month = msg.get("month", 1)
                
                if not username:
                    logger.warning(f"[DLiveWorker] ⚠ Subscription message missing username, skipping")
                    return
                
                event_data = {
                    'user_id': sender.get('username'),
                    'message_id': msg.get('id'),
                    'months': month
                }
                
                logger.info(f"[DLiveWorker] Subscription: {username} for {month} month(s)")
                # Emit as stream event instead of regular message
                from .connector_utils import emit_chat
                emit_chat(self, 'dlive', username, f"⭐ subscribed for {month} month{'s' if month > 1 else ''}", {'event_type': 'subscription', **event_data})
            
            elif msg_type in ("ChatHost", "Host"):
                # Host/raid message
                sender = msg.get("sender", {})
                username = sender.get("displayname") or sender.get("username", "Unknown")
                viewer_count = msg.get("viewer") or msg.get("viewers") or msg.get("viewerCount", 0)
                
                if not username:
                    logger.warning(f"[DLiveWorker] ⚠ Host message missing username, skipping")
                    return
                
                event_data = {
                    'user_id': sender.get('username'),
                    'message_id': msg.get('id'),
                    'viewers': viewer_count
                }
                
                logger.info(f"[DLiveWorker] Host/Raid: {username} with {viewer_count} viewer(s)")
                # Emit as stream event
                from .connector_utils import emit_chat
                emit_chat(self, 'dlive', username, f"📢 hosted with {viewer_count} viewer{'s' if viewer_count != 1 else ''}", {'event_type': 'raid', **event_data})
            
            elif msg_type in ("ChatDelete", "Delete"):
                # Message deletion event
                deleted_msg_id = msg.get('id') or msg.get('deletedMessageId')
                if deleted_msg_id:
                    logger.info(f"[DLiveWorker] Message deleted by moderator: {deleted_msg_id}")
                    self.deletion_signal.emit(deleted_msg_id)
                else:
                    logger.warning(f"[DLiveWorker] ⚠ Delete event without message ID")
            else:
                # Unknown message type
                logger.debug(f"[DLiveWorker] Unknown message type: {msg_type}")
        
        except KeyError as e:
            logger.warning(f"[DLiveWorker] ⚠ Missing required field in message: {e}")
        except Exception as e:
            import traceback
            logger.exception(f"[DLiveWorker] ⚠ Error processing message: {type(e).__name__}: {e}")
            logger.debug(f"[DLiveWorker] Message data: {msg}")
            logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
    
    def stop(self):
        """Stop the worker"""
        logger.info("[DLiveWorker] Stopping...")
        self.running = False
        
        # Close WebSocket if open
        if self.ws and self.loop:
            try:
                # Send stop message
                stop_message = {
                    "id": self.subscription_id,
                    "type": "stop"
                }
                asyncio.run_coroutine_threadsafe(
                    self.ws.send(json.dumps(stop_message)),
                    self.loop
                )
                
                # Close connection
                asyncio.run_coroutine_threadsafe(
                    self.ws.close(),
                    self.loop
                )
            except Exception as e:
                logger.exception(f"[DLiveWorker] Error closing WebSocket: {e}")
    
    def send_message(self, message: str):
        """Send a message to DLive chat using HTTP POST (not WebSocket)"""
        if not self.access_token:
            logger.warning("[DLiveWorker] Cannot send message: No access token")
            return False
        
        # Debug: Show which account is sending
        logger.debug(f"[DLiveWorker] send_message: Sending as streamer: {self.username}")
        
        # Parse token if it's stored as JSON
        token = self.access_token
        if token.startswith('{'):
            try:
                token_data = json.loads(token)
                token = token_data.get('token', token)
                logger.debug(f"[DLiveWorker] Extracted token from JSON (length: {len(token)})")
            except:
                logger.debug(f"[DLiveWorker] Token is JSON-like but couldn't parse, using as-is")
        
        # Use HTTP POST for sending messages (more reliable than WebSocket mutation)
        mutation = """
        mutation SendStreamChatMessage($input: SendStreamchatMessageInput!) {
            sendStreamchatMessage(input: $input) {
                err {
                    message
                }
                message {
                    ... on ChatText {
                        id
                        content
                    }
                }
            }
        }
        """
        
        payload = {
            "query": mutation,
            "variables": {
                "input": {
                    "streamer": self.username,
                    "message": message,
                    "roomRole": "Member",
                    "subscribing": False
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": token  # Use extracted token
        }
        
        logger.info(f"[DLiveWorker] Sending via HTTP POST to {self.GRAPHQL_URL}")
        logger.debug(f"[DLiveWorker] Payload: {json.dumps(payload, indent=2)}")
        
        try:
            session = _make_retry_session()
            response = session.post(
                self.GRAPHQL_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            logger.debug(f"[DLiveWorker] Response status: {response.status_code}")
            logger.debug(f"[DLiveWorker] Response body: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for errors first
                if data.get('errors'):
                    error_msg = data['errors'][0].get('message', 'Unknown error')
                    logger.error(f"[DLiveWorker] ❌ GraphQL error: {error_msg}")
                    logger.debug(f"[DLiveWorker] Full errors: {json.dumps(data['errors'], indent=2)}")
                    return False
                
                result = data.get('data', {})
                if result:
                    send_result = result.get('sendStreamchatMessage', {})
                    err = send_result.get('err', {})
                    
                    if err and err.get('message'):
                        logger.error(f"[DLiveWorker] ❌ Message send failed: {err.get('message')}")
                        return False
                    else:
                        logger.info(f"[DLiveWorker] ✓ Message sent successfully via HTTP")
                        return True
                else:
                    logger.error(f"[DLiveWorker] ❌ No data in response")
                    return False
            else:
                logger.error(f"[DLiveWorker] ❌ HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"[DLiveWorker] ❌ Error sending message: {e}")
            import traceback
            logger.debug(f"[DLiveWorker] Traceback:\n{traceback.format_exc()}")
            return False
        except Exception as e:
            logger.exception(f"[DLiveWorker] Error sending message: {e}")
            return False
