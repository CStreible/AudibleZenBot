"""
Trovo Platform Connector
"""

from platform_connectors.base_connector import BasePlatformConnector

import asyncio
import json
import websockets
import requests
import random
import string
import time
from PyQt6.QtCore import QThread, pyqtSignal


class TrovoConnector(BasePlatformConnector):
    """Connector for Trovo chat"""
    def connect(self, channel_name):
        print(f"[TrovoConnector] connect() called for channel: {channel_name}")
        if not self.access_token:
            print("[TrovoConnector] No access token set. Cannot connect.")
            return
        
        # Skip refresh if we just set a fresh token via OAuth
        if self._skip_next_refresh:
            print(f"[TrovoConnector] Skipping refresh, using fresh OAuth token")
            self._skip_next_refresh = False
        elif self.refresh_token and self.config:
            # Try to refresh token if we have a refresh token, but skip if token was just saved recently
            import time
            trovo_config = self.config.get_platform_config('trovo')
            token_timestamp = trovo_config.get('streamer_token_timestamp', 0)
            age_seconds = time.time() - token_timestamp if token_timestamp else 999999
            
            if age_seconds > 10:  # Only refresh if token is older than 10 seconds
                print(f"[TrovoConnector] Token is {age_seconds:.0f}s old, attempting refresh...")
                self.refresh_access_token()
            else:
                print(f"[TrovoConnector] Token is fresh ({age_seconds:.0f}s old), skipping refresh")
        
        print(f"[TrovoConnector] Starting TrovoWorker for channel: {channel_name}")
        self.worker = TrovoWorker(self.access_token, channel_name)
        self.worker.message_signal.connect(self.onMessageReceived)
        self.worker.status_signal.connect(self.onStatusChanged)
        self.worker.deletion_signal.connect(self.onMessageDeleted)
        self.worker.start()

    # Hard-coded fallback Trovo access token
    DEFAULT_ACCESS_TOKEN = "892ea7e2c9ad3e719a6e977ab5d69275"
    CLIENT_ID = "b239c1cc698e04e93a164df321d142b3"
    CLIENT_SECRET = "a6a9471aed462e984c85feb04e39882e"

    def __init__(self, config=None):
        super().__init__()
        self.worker_thread = None
        self.worker = None
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

    def set_token(self, token: str, refresh_token: str = None, is_bot: bool = False):
        """Set OAuth access token for Trovo chat"""
        if token:
            self.access_token = token
            self.is_bot_account = is_bot
            self._skip_next_refresh = True  # Skip refresh since we just got a fresh token
            # Store bot's refresh token if provided
            if refresh_token:
                self.refresh_token = refresh_token
                print(f"[Trovo] {'Bot' if is_bot else 'Streamer'} token and refresh token set")
            # Don't save to config - bot token is already saved as 'bot_token' in config
            # and we don't want to overwrite the streamer's 'access_token'
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            print("[Trovo] No refresh token available")
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
            
            response = requests.post(
                'https://open-api.trovo.live/openplatform/refreshtoken',
                headers=headers,
                json=data
            )
            
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
                    print(f"[Trovo] Saved refreshed tokens via ConfigManager")
                
                print("[Trovo] Access token refreshed successfully")
                return True
            else:
                print(f"[Trovo] Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[Trovo] Error refreshing token: {e}")
            return False
    
    def delete_message(self, message_id: str):
        """Delete a message from Trovo chat
        
        Trovo API requires: DELETE /openplatform/channels/{channelID}/messages/{messageID}/users/{uID}
        The message_id format from chat is: timestamp_channelID_channelID_messageID_sequence
        We need to extract channelID, messageID, and need to get uID from somewhere
        """
        if not message_id or not self.access_token:
            print(f"[Trovo] Cannot delete message - missing message_id or access_token")
            return
        
        try:
            # Parse Trovo message ID format: timestamp_channelID_channelID_messageID_sequence
            parts = message_id.split('_')
            if len(parts) < 5:
                print(f"[Trovo] Invalid message_id format: {message_id}")
                return
            
            # Extract channel_id and message_id from the composite ID
            # Format: timestamp_channelID_channelID_actualMessageID_sequence
            channel_id = parts[1]  # Second part is channel ID
            actual_message_id = parts[3]  # Fourth part is the actual message ID
            
            # Get user_id from cache
            user_id = self.message_cache.get(message_id)
            if not user_id:
                print(f"[Trovo] Cannot delete message: user_id not found in cache")
                print(f"[Trovo] Message ID: {message_id}, Channel ID: {channel_id}, Msg ID: {actual_message_id}")
                return
            
            headers = {
                'Accept': 'application/json',
                'Client-ID': self.CLIENT_ID,
                'Authorization': f'OAuth {self.access_token}'
            }
            
            # DELETE /openplatform/channels/{channelID}/messages/{messageID}/users/{uID}
            response = requests.delete(
                f'https://open-api.trovo.live/openplatform/channels/{channel_id}/messages/{actual_message_id}/users/{user_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"[Trovo] Message deleted: {message_id}")
                # Remove from cache after successful deletion
                if message_id in self.message_cache:
                    del self.message_cache[message_id]
                return True
            else:
                print(f"[Trovo] Failed to delete message: {response.status_code}")
                print(f"[Trovo] Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"[Trovo] Error deleting message: {e}")
            return False
    
    def onMessageDeleted(self, message_id: str):
        """Handle message deleted by platform/moderator"""
        print(f"[TrovoConnector] Message deleted by platform: {message_id}")
        self.message_deleted.emit('trovo', message_id)

    def ban_user(self, username: str, user_id: str = None):
        """Ban a user from Trovo chat"""
        if not user_id or not self.access_token:
            print(f"[Trovo] Cannot ban user: missing user_id or access_token")
            return
        
        try:
            headers = {
                'Client-ID': 'b239c1cc698e04e93a164df321d142b3',
                'Authorization': f'OAuth {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Ban user via Trovo API
            response = requests.post(
                'https://open-api.trovo.live/openplatform/chat/ban',
                headers=headers,
                json={
                    'user_id': user_id,
                    'duration': 0  # 0 = permanent ban
                }
            )
            
            if response.status_code == 200:
                print(f"[Trovo] User banned: {username}")
            else:
                print(f"[Trovo] Failed to ban user: {response.status_code}")
        except Exception as e:
            print(f"[Trovo] Error banning user: {e}")
    
    def onMessageReceived(self, username: str, message: str, metadata: dict):
        print(f"[TrovoConnector] onMessageReceived: {username}, {message}, metadata: {metadata}")
        
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
        
        self.message_received_with_metadata.emit('trovo', username, message, metadata)
    
    def onStatusChanged(self, connected: bool):
        self.connected = connected
        self.last_status = connected
        self.connection_status.emit(connected)
    
    def send_message(self, message: str):
        """Send a message to Trovo chat via REST API"""
        if not self.access_token:
            print("[Trovo] Cannot send message: No access token")
            return False
        
        if not self.config:
            print("[Trovo] Cannot send message: No config available")
            return False
        
        try:
            # Debug: Show which token is being used
            token_prefix = self.access_token[:12] if self.access_token else "None"
            print(f"[Trovo] send_message: Using token (first 12 chars): {token_prefix}...")
            
            # Get config (don't reload to preserve in-memory token)
            trovo_config = self.config.get_platform_config('trovo')
            print(f"[Trovo] send_message: Config keys: {list(trovo_config.keys())}")
            
            # Try multiple possible field names for channel_id
            channel_id = (
                trovo_config.get('streamer_channel_id') or 
                trovo_config.get('channel_id') or
                trovo_config.get('streamer_user_id') or
                trovo_config.get('user_id')
            )
            print(f"[Trovo] send_message: channel_id from config = {channel_id}")
            
            if not channel_id:
                print(f"[Trovo] Cannot send message: No channel_id found in config. Available keys: {list(trovo_config.keys())}")
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
            
            response = requests.post(
                'https://open-api.trovo.live/openplatform/chat/send',
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[Trovo] Message sent successfully: {message[:50]}...")
                return True
            elif response.status_code == 401:
                # Token expired - try to refresh and retry
                print(f"[Trovo] Token expired (401), attempting refresh...")
                if self.refresh_access_token():
                    print(f"[Trovo] Token refreshed, retrying send...")
                    # Update headers with new token
                    headers['Authorization'] = f'OAuth {self.access_token}'
                    response = requests.post(
                        'https://open-api.trovo.live/openplatform/chat/send',
                        headers=headers,
                        json=data,
                        timeout=10
                    )
                    if response.status_code == 200:
                        print(f"[Trovo] Message sent successfully after token refresh: {message[:50]}...")
                        return True
                    else:
                        print(f"[Trovo] Failed after token refresh: {response.status_code} - {response.text}")
                        return False
                else:
                    print(f"[Trovo] Failed to refresh token")
                    return False
            else:
                print(f"[Trovo] Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[Trovo] Error sending message: {e}")
            import traceback
            traceback.print_exc()
            return False



class TrovoWorker(QThread):
    """Worker thread for Trovo chat via WebSocket"""
    message_signal = pyqtSignal(str, str, dict)  # username, message, metadata
    status_signal = pyqtSignal(bool)
    deletion_signal = pyqtSignal(str)  # message_id


    TROVO_CHAT_WS_URL = "wss://open-chat.trovo.live/chat"
    TROVO_CHAT_TOKEN_URL = "https://open-api.trovo.live/openplatform/chat/token"

    def __init__(self, access_token: str, channel: str = None):
        super().__init__()
        self.access_token = access_token
        self.channel = channel
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
        print("[TrovoWorker] Starting run()")
        self.running = True
        self.status_signal.emit(True)
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                # Step 1: Get chat token
                self.chat_token = self.get_chat_token()
                if not self.chat_token:
                    print("[TrovoWorker] Failed to get chat token. Aborting connection.")
                    return
                self.loop.run_until_complete(self.connect_to_trovo())
            except Exception as e:
                print(f"[TrovoWorker] Error: {e}")
            finally:
                if self.loop and not self.loop.is_closed():
                    self.loop.close()
        except Exception as e:
            print(f"[TrovoWorker] Exception in run(): {e}")
            return

    def get_chat_token(self):
        access_token = (self.access_token or "").strip()
        print("[TrovoWorker] Entered get_chat_token()")
        try:
            print(f"[TrovoWorker] Access token length: {len(access_token)}; starts with: {access_token[:8]}")
            headers = {
                "Accept": "application/json",
                "Client-ID": "b239c1cc698e04e93a164df321d142b3",
                "Client-Id": "b239c1cc698e04e93a164df321d142b3",
                "Authorization": f"OAuth {access_token}"
            }
            print(f"[TrovoWorker] Requesting chat token with headers: {headers}")
            try:
                resp = requests.get(self.TROVO_CHAT_TOKEN_URL, headers=headers)
                print(f"[TrovoWorker] Response status: {resp.status_code}")
                print(f"[TrovoWorker] Response headers: {resp.headers}")
                print(f"[TrovoWorker] Response body: {resp.text}")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("token")
                else:
                    print(f"[TrovoWorker] Failed to get chat token: {resp.status_code} {resp.text}")
                    return None
            except Exception as e:
                print(f"[TrovoWorker] Exception getting chat token: {e}")
                return None
        except Exception as e:
            print(f"[TrovoWorker] Exception in get_chat_token(): {e}")
            return None

    async def connect_to_trovo(self):
        try:
            # Disable built-in ping/pong since Trovo uses custom protocol
            async with websockets.connect(self.TROVO_CHAT_WS_URL, ping_interval=None) as ws:
                self.ws = ws
                print("[TrovoWorker] Connected to Trovo chat WebSocket.")
                # Step 2: Send AUTH message
                nonce = self._random_nonce()
                auth_msg = {
                    "type": "AUTH",
                    "nonce": nonce,
                    "data": {"token": self.chat_token}
                }
                await ws.send(json.dumps(auth_msg))
                print(f"[TrovoWorker] Sent AUTH message with nonce {nonce}")
                # Wait for RESPONSE
                response = await ws.recv()
                print(f"[TrovoWorker] AUTH response: {response}")
                # Set connection time to filter old messages
                self.connection_time = time.time()
                self.last_message_time = time.time()
                print(f"[TrovoWorker] Connection established at {self.connection_time}")
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
            print(f"[TrovoWorker] WebSocket connection error: {e}")

    async def ping_loop(self, ws):
        while self.running:
            await asyncio.sleep(self.ping_gap)
            nonce = self._random_nonce()
            ping_msg = {"type": "PING", "nonce": nonce}
            try:
                await ws.send(json.dumps(ping_msg))
                print(f"[TrovoWorker] Sent PING with nonce {nonce}")
            except Exception as e:
                print(f"[TrovoWorker] Error sending PING: {e}")
                break

    async def listen(self, ws):
        while self.running:
            try:
                message = await ws.recv()
                self.last_message_time = time.time()  # Update health timestamp
                self.handle_message(message)
            except websockets.ConnectionClosed:
                print(f"[TrovoWorker] Connection closed")
                break
            except Exception as e:
                print(f"[TrovoWorker] Error receiving message: {e}")
                break

    def handle_message(self, raw_message):
        try:
            # Debug: Log all received messages
            print(f"[TrovoWorker] Received message: {raw_message[:200]}")
            data = json.loads(raw_message)
            msg_type = data.get("type")
            if msg_type == "PONG":
                # Adjust ping gap if provided
                gap = data.get("data", {}).get("gap")
                if gap:
                    self.ping_gap = gap
                print(f"[TrovoWorker] Received PONG, set ping gap to {self.ping_gap}s")
            elif msg_type == "CHAT":
                print(f"[TrovoWorker] Processing CHAT message: {data}")
                chats = data.get("data", {}).get("chats", [])
                print(f"[TrovoWorker] Found {len(chats)} chat messages")
                for chat in chats:
                    # Message deduplication
                    msg_id = chat.get("message_id") or chat.get("msg_id")
                    if msg_id:
                        if msg_id in self.seen_message_ids:
                            print(f"[TrovoWorker] Skipping duplicate message: {msg_id}")
                            continue
                        
                        # Add to seen messages
                        self.seen_message_ids.add(msg_id)
                        
                        # Limit size to prevent unbounded memory growth
                        if len(self.seen_message_ids) > self.max_seen_ids:
                            self.seen_message_ids = set(list(self.seen_message_ids)[self.max_seen_ids // 2:])
                            print(f"[TrovoWorker] Trimmed seen_message_ids to {len(self.seen_message_ids)}")
                    
                    # Filter old messages - only emit messages after connection time
                    send_time = chat.get("send_time", 0)
                    if self.connection_time and send_time < self.connection_time:
                        print(f"[TrovoWorker] Skipping old message (send_time: {send_time} < connection_time: {self.connection_time})")
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
                                print(f"[TrovoWorker] Auto-saved streamer_user_id: {user_id}")
                    
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
                        print(f"[TrovoWorker] Subscription: {username} - {months} months")
                    
                    # Type 5002 = Follow
                    elif chat_type == 5002 or 'followed' in message.lower():
                        metadata['event_type'] = 'follow'
                        message = "🎯 followed the stream"
                        print(f"[TrovoWorker] Follow: {username}")
                    
                    # Type 5003 = Gift (subscription gift)
                    elif chat_type == 5003 or chat.get('gift_type'):
                        gift_num = chat.get('num', 1)
                        metadata['event_type'] = 'subscription'
                        message = f"💝 gifted {gift_num} subscription{'s' if gift_num > 1 else ''}"
                        print(f"[TrovoWorker] Gift subs: {username} - {gift_num}")
                    
                    # Type 5004 = Spell (Trovo's version of bits/donations)
                    elif chat_type == 5004 or chat.get('value_type') == 'spell':
                        spell_value = chat.get('value', 0)
                        spell_name = chat.get('gift', 'spell')
                        metadata['event_type'] = 'spell'
                        metadata['amount'] = spell_value
                        metadata['spell_name'] = spell_name
                        message = f"✨ cast {spell_name} ({spell_value} mana)"
                        print(f"[TrovoWorker] Spell: {username} - {spell_name} ({spell_value})")
                    
                    # Type 5005 = Magic Chat (highlighted message)
                    elif chat_type == 5005 or chat.get('magic_chat_id'):
                        metadata['event_type'] = 'magic_chat'
                        message = f"🌟 {message}"
                        print(f"[TrovoWorker] Magic Chat: {username}")
                    
                    # Type 5006 = Raid
                    elif chat_type == 5006 or 'raid' in message.lower():
                        viewers = chat.get('viewer_count', 0)
                        metadata['event_type'] = 'raid'
                        metadata['viewers'] = viewers
                        message = f"📢 raided with {viewers} viewer{'s' if viewers != 1 else ''}"
                        print(f"[TrovoWorker] Raid: {username} - {viewers} viewers")
                    
                    print(f"[TrovoWorker] Emitting message from {username}: {message} with badges: {badges}")
                    self.message_signal.emit(username, message, metadata)
            elif msg_type == "MESSAGE_DELETE" or msg_type == "DELETE":
                # Handle message deletion events
                print(f"[TrovoWorker] Processing deletion message: {data}")
                delete_data = data.get("data", {})
                
                # Try to get message_id from various possible fields
                deleted_msg_id = (
                    delete_data.get("message_id") or 
                    delete_data.get("msg_id") or
                    delete_data.get("id")
                )
                
                if deleted_msg_id:
                    print(f"[TrovoWorker] Message deleted by moderator: {deleted_msg_id}")
                    self.deletion_signal.emit(str(deleted_msg_id))
                else:
                    print(f"[TrovoWorker] ⚠ Deletion event missing message_id")
            else:
                print(f"[TrovoWorker] Unknown message type: {msg_type}")
        except json.JSONDecodeError as e:
            print(f"[TrovoWorker] ⚠ Invalid JSON received: {e}")
        except KeyError as e:
            print(f"[TrovoWorker] ⚠ Missing required field: {e}")
        except Exception as e:
            import traceback
            print(f"[TrovoWorker] ⚠ Error handling message: {type(e).__name__}: {e}")
            print(f"[TrovoWorker] Traceback:\n{traceback.format_exc()}")

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
                        print(f"[TrovoWorker] Connection appears dead ({int(time_since_last)}s since last message)")
                        print(f"[TrovoWorker] Forcing reconnection...")
                        await websocket.close()
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[TrovoWorker] Health check error: {e}")

    def stop(self):
        self.running = False
        if self.loop and self.ws:
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)


# Note: Trovo uses WebSocket connections
# Documentation: https://developer.trovo.live/
