"""
Kick Platform Connector - Official API Implementation
Connects to Kick using OAuth2 and Webhooks API
Documentation: https://docs.kick.com/

NOTE: Kick's real-time chat requires webhooks which need a publicly accessible URL.
For local development, you must use ngrok or similar tunnel service:
1. Install ngrok: https://ngrok.com/download
2. Run: ngrok http 8889
3. Update webhook URL in Kick Developer settings with ngrok URL
4. Enable webhooks and subscribe to chat.message.sent events

Alternative: Wait for Kick to release a WebSocket API for developers.
"""

import json
import requests
import cloudscraper
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from platform_connectors.base_connector import BasePlatformConnector
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class KickConnector(BasePlatformConnector):
    """Connector for Kick chat using official OAuth2 + Webhooks API"""
    
    # Kick OAuth credentials from https://kick.com/settings/developer
    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = ""
    
    # Kick API endpoints
    OAUTH_BASE = "https://id.kick.com"
    API_BASE = "https://api.kick.com/public/v1"
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.ngrok_manager = None  # Will be set by chat_manager
        self.client_id = self.DEFAULT_CLIENT_ID
        self.client_secret = self.DEFAULT_CLIENT_SECRET
        self.access_token = None  # User OAuth token for sending messages
        self.app_access_token = None  # App token for API calls
        self.is_bot_account = False  # Track if this is a bot account or streamer
        self.session_cookies = {}  # Store session cookies for v2 API
        self.webhook_server = None
        self.webhook_thread = None
        self.webhook_port = 8889
        self.webhook_url = None  # Store the ngrok URL
        self.broadcaster_user_id = None
        self.chatroom_id = None  # Store chatroom ID for sending messages
        self.subscription_id = None
        
        # Message reliability features
        self.seen_message_ids = set()  # Track processed messages
        self.max_seen_ids = 10000  # Prevent unbounded growth
        self.last_message_time = None  # For health monitoring
        self.health_check_thread = None
        self.health_check_interval = 300  # 5 minutes
        self.subscription_active = False
        self.channel_name = None
        
        # Load token from config if available
        if self.config:
            kick_config = self.config.get_platform_config('kick')
            # Try both old and new token field names for backwards compatibility
            token = kick_config.get('streamer_token', '') or kick_config.get('access_token', '')
            if token:
                self.access_token = token
                print(f"[Kick] Loaded OAuth token from config (length: {len(token)})")
            else:
                self.access_token = None
                print(f"[Kick] No OAuth token found in config")
            # Load client credentials from config if present
            try:
                cid = kick_config.get('client_id', '')
                csec = kick_config.get('client_secret', '')
                if cid:
                    self.client_id = cid
                if csec:
                    self.client_secret = csec
                if cid or csec:
                    print(f"[Kick] Loaded client credentials from config: client_id={'set' if cid else 'not set'}")
            except Exception:
                pass
    
    def set_cookies(self, cookies: dict):
        """Set session cookies for v2 API authentication"""
        if cookies:
            self.session_cookies = cookies
            print(f"[Kick] Session cookies set: {list(cookies.keys())}")
    
    def set_token(self, token: str, is_bot: bool = False):
        """Set access token for authentication
        
        Args:
            token: OAuth access token
            is_bot: True if this is a bot account, False for streamer account
        """
        if token:
            self.access_token = token
            self.is_bot_account = is_bot
            account_type = "bot" if is_bot else "streamer"
            print(f"[Kick] Token set for {account_type} account (length: {len(token)})")
            
            if self.config:
                # Save to appropriate config field
                token_field = 'bot_token' if is_bot else 'streamer_token'
                self.config.set_platform_config('kick', token_field, token)
        else:
            kick_config = self.config.get_platform_config('kick') if self.config else {}
            config_token = kick_config.get('streamer_token', '') or kick_config.get('access_token', '')
            if not config_token:
                self.access_token = None
    
    def get_app_access_token(self):
        """Get App Access Token using client credentials flow
        
        Note: App tokens are for server-to-server API calls (webhooks, etc).
        They cannot send chat messages. Use the user's OAuth token for that.
        """
        try:
            response = requests.post(
                f"{self.OAUTH_BASE}/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                # Store in separate variable - don't overwrite user OAuth token!
                self.app_access_token = data.get("access_token")
                print(f"✓ Kick: Got App Access Token (expires in {data.get('expires_in')}s)")
                print(f"   Note: App token is for webhooks. User OAuth token kept for chat messages.")
                return True
            else:
                print(f"✗ Kick: Failed to get token: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ Kick: Error getting token: {e}")
            return False
    
    def get_channel_info(self, channel_slug: str):
        """Get channel information including user ID and chatroom ID"""
        try:
            # Use cloudscraper to bypass Cloudflare protection
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
            response = scraper.get(f"https://kick.com/api/v2/channels/{channel_slug}")
            
            if response.status_code == 200:
                data = response.json()
                self.broadcaster_user_id = data.get("user_id")
                
                # Get chatroom ID for sending messages
                chatroom = data.get("chatroom", {})
                self.chatroom_id = chatroom.get("id")
                
                print(f"✓ Kick: Channel '{channel_slug}' user_id = {self.broadcaster_user_id}, chatroom_id = {self.chatroom_id}")
                return self.broadcaster_user_id
            else:
                print(f"✗ Kick: Failed to get channel info: {response.status_code}")
                return None
        except Exception as e:
            print(f"✗ Kick: Error getting channel info: {e}")
            return None
    
    def delete_message(self, message_id: str):
        """Delete a message from Kick chat
        
        Note: Kick does not provide a public API for message deletion.
        The endpoint exists but returns 405 Method Not Allowed.
        Message deletion may only be possible through the web moderator panel.
        """
        if not message_id or not self.access_token:
            print(f"[Kick] Cannot delete message - missing message_id or access_token")
            return
        
        print(f"[Kick] Message deletion not supported - Kick has no public API for this")
        print(f"[Kick] Message ID: {message_id}")
        print(f"[Kick] Deletion must be done manually through Kick moderator panel")
        return False
        
        # Keeping code for reference if Kick adds API support in future:
        # try:
        #     scraper = cloudscraper.create_scraper(
        #         browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        #     )
        #     
        #     response = scraper.delete(
        #         f"https://kick.com/api/v2/messages/{message_id}",
        #         headers={
        #             'Authorization': f'Bearer {self.access_token}',
        #             'Content-Type': 'application/json'
        #         }
        #     )
        #     
        #     if response.status_code in [200, 204]:
        #         print(f"[Kick] Message deleted: {message_id}")
        #     else:
        #         print(f"[Kick] Failed to delete message: {response.status_code}")
        #         print(f"[Kick] Response: {response.text}")
        # except Exception as e:
        #     print(f"[Kick] Error deleting message: {e}")
    
    def ban_user(self, username: str, user_id: str = None):
        """Ban a user from Kick chat"""
        if not username or not self.access_token:
            return
        
        try:
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
            
            # Ban user via Kick API
            response = scraper.post(
                f"https://kick.com/api/v2/channels/{self.username}/bans",
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'banned_username': username,
                    'permanent': True
                }
            )
            
            if response.status_code == 200:
                print(f"[Kick] User banned: {username}")
            else:
                print(f"[Kick] Failed to ban user: {response.status_code}")
        except Exception as e:
            print(f"[Kick] Error banning user: {e}")
    
    def subscribe_to_chat_events(self, retry_count=0, max_retries=5):
        """Subscribe to chat.message.sent events via webhooks with retry logic"""
        # Use app access token for webhook subscriptions (server-to-server)
        auth_token = getattr(self, 'app_access_token', None) or self.access_token
        
        if not auth_token or not self.broadcaster_user_id:
            print("✗ Kick: Cannot subscribe - need access token and broadcaster ID")
            return False
        
        # Check if we have a webhook URL
        if not self.webhook_url:
            print("✗ Kick: No webhook URL available")
            return False
        
        try:
            print(f"\n[Subscribe] Using webhook URL: {self.webhook_url}")
            print(f"[Subscribe] Using app access token: {auth_token[:20] if auth_token else 'None'}...")
            
            response = requests.post(
                f"{self.API_BASE}/events/subscriptions",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "broadcaster_user_id": self.broadcaster_user_id,
                    "events": [
                        {
                            "name": "chat.message.sent",
                            "version": 1
                        },
                        {
                            "name": "chat.message.deleted",
                            "version": 1
                        }
                    ],
                    "method": "webhook",
                    "webhook_url": self.webhook_url  # Use ngrok URL
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                subscriptions = data.get("data", [])
                if subscriptions:
                    self.subscription_id = subscriptions[0].get("subscription_id")
                    self.subscription_active = True
                    print(f"✓ Kick: Subscribed to chat.message.sent (subscription: {self.subscription_id})")
                    return True
                else:
                    print(f"✗ Kick: Subscription failed: {data.get('message')}")
                    # Retry with exponential backoff
                    if retry_count < max_retries:
                        import time
                        wait_time = 2 ** retry_count  # 1, 2, 4, 8, 16 seconds
                        print(f"⚠ Kick: Retrying subscription in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                        time.sleep(wait_time)
                        return self.subscribe_to_chat_events(retry_count + 1, max_retries)
                    return False
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("data", "")
                if "webhook not enabled" in error_msg:
                    print(f"✗ Kick: Webhooks not enabled in app settings")
                    print(f"   Go to https://kick.com/settings/developer")
                    print(f"   Edit your app, toggle 'Enable Webhooks' ON")
                    print(f"   Set Webhook URL (must be publicly accessible)")
                    print(f"   If testing locally, use ngrok: https://ngrok.com/")
                else:
                    print(f"✗ Kick: Subscription failed: {error_msg}")
                return False
            else:
                print(f"✗ Kick: Subscription request failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                # Retry with exponential backoff for transient errors
                if retry_count < max_retries and response.status_code >= 500:
                    import time
                    wait_time = 2 ** retry_count
                    print(f"⚠ Kick: Retrying subscription in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(wait_time)
                    return self.subscribe_to_chat_events(retry_count + 1, max_retries)
                return False
        except Exception as e:
            print(f"✗ Kick: Error subscribing to events: {e}")
            # Retry on exception
            if retry_count < max_retries:
                import time
                wait_time = 2 ** retry_count
                print(f"⚠ Kick: Retrying subscription in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self.subscribe_to_chat_events(retry_count + 1, max_retries)
            return False
    
    def start_webhook_server(self):
        """Register Kick webhook handler with shared callback server and start it."""
        try:
            from core import callback_server

            def _handler(req):
                try:
                    # Read headers and JSON body
                    event_type = req.headers.get('Kick-Event-Type')
                    # Flask request.get_json will return parsed JSON
                    data = req.get_json(silent=True) or {}
                    if event_type == 'chat.message.sent':
                        print(f"[Webhook] Chat message from {data.get('sender', {}).get('username', 'Unknown')}")
                        self.handle_chat_message(data)
                    elif event_type in ('chat.message.deleted', 'chat.message.removed'):
                        print(f"[Webhook] Message deletion event")
                        self.handle_message_deletion(data)
                    else:
                        print(f"[Webhook] Unhandled event type: {event_type}")
                    return ('', 200)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return ("", 500)

            route_path = '/kick/webhook'
            callback_server.register_route(route_path, _handler, methods=['POST', 'GET'])
            callback_server.start_server(self.webhook_port)
            self.webhook_server = True
            print(f"✓ Kick: Registered webhook route {route_path} on shared callback server (port {self.webhook_port})")
            print(f"⚠ IMPORTANT: Configure webhook URL in Kick Developer settings:")
            print(f"   If using ngrok: Run 'ngrok http {self.webhook_port}' and use the HTTPS URL + {route_path}")
        except Exception as e:
            print(f"✗ Kick: Failed to start shared webhook server: {e}")
    
    def handle_chat_message(self, data):
        """Handle incoming chat message from webhook with deduplication"""
        try:
            # Update health monitoring timestamp
            import time
            self.last_message_time = time.time()
            
            # Message deduplication
            msg_id = data.get("id") or data.get("message_id")
            if msg_id:
                if msg_id in self.seen_message_ids:
                    print(f"[Kick] Skipping duplicate message: {msg_id}")
                    return
                
                # Add to seen messages
                self.seen_message_ids.add(msg_id)
                
                # Limit size to prevent unbounded memory growth
                if len(self.seen_message_ids) > self.max_seen_ids:
                    # Keep only the most recent half
                    self.seen_message_ids = set(list(self.seen_message_ids)[self.max_seen_ids // 2:])
                    print(f"[Kick] Trimmed seen_message_ids to {len(self.seen_message_ids)}")
            
            sender = data.get("sender", {})
            username = sender.get("username", "Unknown")
            content = data.get("content", "")
            
            # Validate essential data
            if not username or not content:
                print(f"[Kick] ⚠ Incomplete message data, skipping: {data}")
                return
            
            print(f"[Kick] Handling chat message: username={username}, content={content[:50]}")

            # Extract metadata
            identity = sender.get("identity", {})
            # --- Badge normalization for Kick ---
            raw_badges = identity.get("badges", [])
            badges = []
            if isinstance(raw_badges, list):
                for badge in raw_badges:
                    # Kick badges may be dicts (e.g. {"type": "moderator", "text": "Mod"}) or strings
                    if isinstance(badge, dict):
                        # Prefer 'type/version' if available, else fallback to 'type' or 'text'
                        badge_type = badge.get("type")
                        badge_version = badge.get("version")
                        if badge_type and badge_version:
                            badges.append(f"{badge_type}/{badge_version}")
                        elif badge_type:
                            badges.append(badge_type)
                        elif badge.get("text"):
                            badges.append(badge["text"])
                        else:
                            badges.append(str(badge))
                    else:
                        badges.append(str(badge))
            elif isinstance(raw_badges, dict):
                # Single badge as dict
                badge_type = raw_badges.get("type")
                badge_version = raw_badges.get("version")
                if badge_type and badge_version:
                    badges.append(f"{badge_type}/{badge_version}")
                elif badge_type:
                    badges.append(badge_type)
                elif raw_badges.get("text"):
                    badges.append(raw_badges["text"])
                else:
                    badges.append(str(raw_badges))
            elif isinstance(raw_badges, str):
                badges = [raw_badges]
            else:
                badges = []

            metadata = {
                "platform": "kick",
                "color": identity.get("username_color", "#FFFFFF"),
                "badges": badges,
                "timestamp": data.get("created_at", ""),
                "emotes": data.get("emotes", []),
                "message_id": msg_id
            }
            
            # Detect Kick events from webhook data
            event_type = data.get("type") or data.get("event_type")
            
            # Subscription event
            if event_type == "subscription" or event_type == "subscribed":
                months = data.get("months", 1)
                metadata['event_type'] = 'subscription'
                metadata['months'] = months
                content = f"⭐ subscribed for {months} month{'s' if months > 1 else ''}"
                print(f"[Kick] Subscription: {username} - {months} months")
            
            # Follow event
            elif event_type == "follow" or event_type == "followed":
                metadata['event_type'] = 'follow'
                content = "🎯 followed the stream"
                print(f"[Kick] Follow: {username}")
            
            # Gift subscription
            elif event_type == "gift_subscription" or event_type == "gifted_sub":
                recipient = data.get("recipient", {}).get("username", "someone")
                metadata['event_type'] = 'subscription'
                content = f"💝 gifted a sub to {recipient}"
                print(f"[Kick] Gift sub: {username} -> {recipient}")
            
            # Raid event
            elif event_type == "raid" or event_type == "hosted":
                viewers = data.get("viewer_count", 0)
                metadata['event_type'] = 'raid'
                metadata['viewers'] = viewers
                content = f"📢 raided with {viewers} viewer{'s' if viewers != 1 else ''}"
                print(f"[Kick] Raid: {username} - {viewers} viewers")

            print(f"[Kick] Emitting message_received_with_metadata signal")
            # Emit signals with correct signature (platform, username, message, metadata)
            self.message_received.emit('kick', username, content, {})
            self.message_received_with_metadata.emit('kick', username, content, metadata)
            print(f"[Kick] Signal emitted successfully")
        except KeyError as e:
            print(f"[Kick] ⚠ Missing required field in message: {e}")
            print(f"[Kick] Message data: {data}")
        except Exception as e:
            print(f"[Kick] ⚠ Error handling chat message: {type(e).__name__}: {e}")
            print(f"[Kick] Message data: {data}")
            import traceback
            traceback.print_exc()
    
    def handle_message_deletion(self, data):
        """Handle message deletion event from webhook"""
        try:
            msg_id = data.get("id") or data.get("message_id")
            if msg_id:
                print(f"[Kick] Message deleted by moderator: {msg_id}")
                self.message_deleted.emit('kick', msg_id)
            else:
                print(f"[Kick] ⚠ Deletion event without message ID")
        except Exception as e:
            print(f"[Kick] ⚠ Error handling message deletion: {e}")
    
    def connect(self, channel: str):
        """Connect to Kick chat"""
        print(f"\n=== Kick Connection Process ===")
        
        # Step 1: Start ngrok tunnel if ngrok_manager is available
        if self.ngrok_manager and self.ngrok_manager.is_available():
            # Check if tunnel already exists for this port in local tracking
            existing_tunnels = self.ngrok_manager.get_all_tunnels()
            
            if self.webhook_port in existing_tunnels:
                self.webhook_url = existing_tunnels[self.webhook_port].get('public_url')
                print(f"✓ Reusing locally tracked ngrok tunnel: {self.webhook_url}")
            else:
                # Try to get existing tunnels from ngrok
                print("[Ngrok] Checking for existing ngrok tunnels...")
                existing_url = None
                try:
                    from pyngrok import ngrok
                    tunnels = ngrok.get_tunnels()
                    print(f"[Ngrok] Found {len(tunnels)} active tunnel(s)")
                    
                    # Look for a tunnel on our port
                    for tunnel in tunnels:
                        print(f"[Ngrok] Inspecting tunnel: {tunnel.public_url}")
                        # Check if this tunnel is for our port
                        if hasattr(tunnel, 'config'):
                            addr = tunnel.config.get('addr', '')
                            print(f"[Ngrok]   Address: {addr}")
                            if f':{self.webhook_port}' in addr or f'localhost:{self.webhook_port}' in addr:
                                existing_url = tunnel.public_url
                                print(f"[Ngrok] ✓ Found existing tunnel for port {self.webhook_port}")
                                break
                    
                    if not existing_url and tunnels:
                        # Just use the first tunnel if it exists
                        existing_url = tunnels[0].public_url
                        print(f"[Ngrok] Using first available tunnel: {existing_url}")
                        
                except Exception as e:
                    print(f"[Ngrok] Error checking existing tunnels: {e}")
                    import traceback
                    traceback.print_exc()
                
                if existing_url:
                    # Use the existing tunnel
                    self.webhook_url = existing_url
                    print(f"✓ Using existing ngrok tunnel: {self.webhook_url}")
                    
                    # Add it to local tracking
                    try:
                        with self.ngrok_manager.lock:
                            self.ngrok_manager.tunnels[self.webhook_port] = {
                                'public_url': existing_url,
                                'port': self.webhook_port,
                                'protocol': 'http'
                            }
                    except:
                        pass
                else:
                    # No existing tunnel, start a new one
                    print("\n[Ngrok] No existing tunnels found, starting fresh tunnel...")
                    self.webhook_url = self.ngrok_manager.start_tunnel(self.webhook_port, name="kick")
                    
                    if not self.webhook_url:
                        self.error_occurred.emit("Failed to start ngrok tunnel. Configure token in Settings.")
                        print("\n⚠ Ngrok tunnel failed. Please configure auth token in Settings page.")
                        return
                    
                    print(f"✓ Ngrok tunnel active: {self.webhook_url}")
        else:
            print("\n⚠ Ngrok not available. Using manual webhook URL.")
            print("   You must manually configure a public URL for webhooks.")
            print("   For setup, see: https://ngrok.com/")
            # Use a placeholder - webhook will need manual configuration
            self.webhook_url = f"http://your-ngrok-url-here.ngrok.io"  
        
        # Step 2: Get App Access Token
        if not self.get_app_access_token():
            self.error_occurred.emit("Failed to get Kick access token")
            return
        
        # Step 3: Get channel info
        if not self.get_channel_info(channel):
            self.error_occurred.emit(f"Failed to get Kick channel info for '{channel}'")
            return
        
        # Step 4: Start webhook server (shared callback server)
        self.webhook_thread = Thread(target=self.start_webhook_server, daemon=True)
        self.webhook_thread.start()

        # Give the webhook server a moment to start
        import time
        time.sleep(0.5)

        # Ensure webhook_url includes the connector path so providers POST to the correct route
        try:
            if self.webhook_url and not self.webhook_url.endswith('/kick/webhook'):
                # Avoid appending placeholder host
                if not self.webhook_url.startswith('http://your-ngrok'):
                    self.webhook_url = self.webhook_url.rstrip('/') + '/kick/webhook'
                    print(f"[Kick] Using webhook endpoint: {self.webhook_url}")
        except Exception:
            pass
        
        # Step 5: Subscribe to events
        self.channel_name = channel
        if self.subscribe_to_chat_events():
            # Start health monitoring
            self.start_health_monitoring()
            
            # Mark as connected
            self.connected = True
            self.connection_status.emit(True)
            print(f"✓ Kick: Connected to channel '{channel}'")
            if self.webhook_url and not self.webhook_url.startswith("http://your-ngrok"):
                print(f"✓ Webhook URL: {self.webhook_url}")
        else:
            self.error_occurred.emit("Failed to subscribe to Kick chat events")
            print("\n⚠ NOTE: Webhooks require a publicly accessible URL.")
            if not self.ngrok_manager or not self.ngrok_manager.is_available():
                print("   Configure ngrok in Settings for automatic tunnel management.")
            print("   2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)")
            print("   3. Go to https://kick.com/settings/developer")
            print("   4. Edit your app and set Webhook URL to: https://abc123.ngrok.io")
            print("   5. Enable webhooks and restart this application\n")
    
    def disconnect(self):
        """Disconnect from Kick"""
        # Stop health monitoring
        self.subscription_active = False
        self.connected = False
        
        # Clean up subscription
        if self.subscription_id and self.access_token:
            try:
                response = requests.delete(
                    f"{self.API_BASE}/events/subscriptions",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params={"id": self.subscription_id}
                )
                if response.status_code == 204:
                    print("✓ Kick: Unsubscribed from events")
            except Exception as e:
                print(f"Error unsubscribing: {e}")
        
        # Stop webhook server (shared callback server)
        if self.webhook_server:
            try:
                from core import callback_server
                callback_server.unregister_route('/kick/webhook')
            except Exception:
                pass
            self.webhook_server = None
        
        self.connection_status.emit(False)
        print("✓ Kick: Disconnected")
    
    def send_message(self, message: str):
        """Send a chat message using Kick's /chat API endpoint
        
        According to Kick API docs (https://docs.kick.com/apis/chat):
        - type: "user" - Send as yourself using your own OAuth token
        - type: "bot" - Has 500 error bug on Kick's side
        
        For bot accounts: Use the bot's own OAuth token with type "user"
        For streamer accounts: Use the streamer's OAuth token with type "user"
        
        Note: Bot must be authorized (e.g., as moderator) to send messages in the channel
        """
        # Use the token that was set for this connector (bot or streamer)
        token_to_use = self.access_token
        
        if not token_to_use:
            print(f"✗ Kick: Cannot send message - no OAuth access token")
            return False
        
        # Get broadcaster_user_id - use our own if set, otherwise get from config
        broadcaster_id = self.broadcaster_user_id
        if not broadcaster_id and self.config:
            kick_config = self.config.get_platform_config('kick')
            broadcaster_id = kick_config.get('streamer_user_id') or kick_config.get('broadcaster_user_id')
            if broadcaster_id:
                print(f"[Kick] Using broadcaster_user_id from config: {broadcaster_id}")
        
        if not broadcaster_id:
            print(f"✗ Kick: Cannot send - missing broadcaster_user_id")
            if self.config:
                kick_config = self.config.get_platform_config('kick')
                print(f"[Kick] Config keys available: {list(kick_config.keys())}")
            return False
        
        try:
            url = f"{self.API_BASE}/chat"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token_to_use}",
                "User-Agent": "AudibleZenBot/1.0"
            }
            
            # Always use type "user" - it sends as the user who owns the OAuth token
            # (type "bot" returns HTTP 500 error on Kick's side)
            payload = {
                "broadcaster_user_id": int(broadcaster_id),
                "content": message,
                "type": "user"
            }
            
            account_type = "bot" if self.is_bot_account else "streamer"
            token_preview = token_to_use[:20] if len(token_to_use) > 20 else token_to_use
            print(f"[Kick] Sending as {account_type} account (token: {token_preview}...) to broadcaster: {broadcaster_id}")
            print(f"[Kick] Payload: {payload}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Kick: Message sent successfully!")
                return True
            elif response.status_code == 401:
                print(f"✗ Kick: Failed (HTTP 401): {response.text[:200]}")
                if self.is_bot_account:
                    print(f"[Kick] Note: Bot messages require valid STREAMER token.")
                    print(f"[Kick] Make sure the streamer is logged in and connected to Kick.")
                return False
            else:
                print(f"✗ Kick: Failed (HTTP {response.status_code}): {response.text[:200]}")
                return False
            
        except Exception as e:
            print(f"✗ Kick: Error sending message: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def connect_chat_websocket(self):
        """Connect to Kick's chat WebSocket for sending messages"""
        try:
            import websocket
            import threading
            import json
            
            print(f"[Kick] Connecting to chat WebSocket...")
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    print(f"[Kick WS] Received: {data.get('event', 'unknown')}")
                    
                    # Check for authentication success
                    if data.get('event') == 'authenticated':
                        self.ws_authenticated = True
                        print(f"[Kick WS] ✓ Authenticated")
                        
                        # Send any queued messages
                        while self.message_queue:
                            queued_msg = self.message_queue.pop(0)
                            self.send_message(queued_msg)
                            
                except Exception as e:
                    print(f"[Kick WS] Error processing message: {e}")
            
            def on_error(ws, error):
                print(f"[Kick WS] Error: {error}")
                self.ws_authenticated = False
            
            def on_close(ws, close_status_code, close_msg):
                print(f"[Kick WS] Connection closed")
                self.ws_authenticated = False
            
            def on_open(ws):
                print(f"[Kick WS] Connection opened")
                
                # Send authentication with Bearer token
                auth_payload = json.dumps({
                    "event": "authenticate",
                    "data": {
                        "token": self.access_token if self.access_token.startswith('Bearer ') else f'Bearer {self.access_token}',
                        "chatroom_id": self.chatroom_id
                    }
                })
                ws.send(auth_payload)
                print(f"[Kick WS] Sent authentication")
            
            # Create WebSocket connection
            # Kick's chat WebSocket uses pusher protocol
            ws_url = f"wss://ws-us2.pusher.com/app/eb1d5f283081a78b932c?protocol=7&client=js&version=7.6.0&flash=false"
            
            print(f"[Kick WS] Connecting to: {ws_url}")
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Run WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
            print(f"[Kick WS] Started connection thread")
            
        except Exception as e:
            print(f"✗ Kick: Error connecting to chat WebSocket: {e}")
            import traceback
            traceback.print_exc()
    
    def start_health_monitoring(self):
        """Start background thread to monitor webhook health"""
        def health_check_worker():
            import time
            print(f"[Kick] Health monitoring started (checking every {self.health_check_interval}s)")
            
            while self.subscription_active:
                time.sleep(self.health_check_interval)
                
                if not self.subscription_active:
                    break
                
                # Check if we've received messages recently
                if self.last_message_time:
                    time_since_last = time.time() - self.last_message_time
                    
                    if time_since_last > self.health_check_interval:
                        print(f"⚠ Kick: No messages received for {int(time_since_last)}s")
                        print(f"   Verifying subscription status...")
                        
                        # Verify subscription is still active
                        if not self.verify_subscription():
                            print(f"⚠ Kick: Subscription not active, attempting to resubscribe...")
                            if self.subscribe_to_chat_events():
                                print(f"✓ Kick: Successfully resubscribed")
                            else:
                                print(f"✗ Kick: Failed to resubscribe")
                                self.error_occurred.emit("Kick webhook subscription failed")
            
            print(f"[Kick] Health monitoring stopped")
        
        self.health_check_thread = Thread(target=health_check_worker, daemon=True)
        self.health_check_thread.start()
    
    def verify_subscription(self):
        """Verify that webhook subscription is still active"""
        if not self.subscription_id or not self.access_token:
            return False
        
        try:
            response = requests.get(
                f"{self.API_BASE}/events/subscriptions",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"id": self.subscription_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                subscriptions = data.get("data", [])
                
                # Check if our subscription is in the list
                for sub in subscriptions:
                    if sub.get("subscription_id") == self.subscription_id:
                        status = sub.get("status", "unknown")
                        print(f"[Kick] Subscription status: {status}")
                        return status == "enabled" or status == "active"
                
                print(f"[Kick] Subscription {self.subscription_id} not found in active subscriptions")
                return False
            else:
                print(f"[Kick] Failed to verify subscription: {response.status_code}")
                return False
        except Exception as e:
            print(f"[Kick] Error verifying subscription: {e}")
            return False
