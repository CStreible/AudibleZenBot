"""
Chat Manager - Manages connections and messages from all platforms
"""

import asyncio
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from core.config import ConfigManager
from platform_connectors.twitch_connector import TwitchConnector
from platform_connectors.youtube_connector import YouTubeConnector
from platform_connectors.trovo_connector import TrovoConnector
from platform_connectors.kick_connector import KickConnector
from platform_connectors.dlive_connector import DLiveConnector
from platform_connectors.twitter_connector import TwitterConnector


class ChatManager(QObject):
    """Manages all platform connections and chat messages"""
    
    message_received = pyqtSignal(str, str, str, dict)  # platform, username, message, metadata
    message_deleted = pyqtSignal(str, str)  # platform, message_id - emitted when message deleted externally
    connection_status_changed = pyqtSignal(str, bool)  # platform, connected
    bot_connection_changed = pyqtSignal(str, bool, str)  # platform_id, connected, username
    streamer_connection_changed = pyqtSignal(str, bool, str)  # platform_id, connected, username
    
    def __init__(self, config=None):
        super().__init__()
        
        self.config = config
        self.ngrok_manager = None  # Will be set by main.py
        
        # Load disabled platforms from config first
        self.disabled_platforms = set()
        if self.config:
            platforms_config = self.config.get('platforms', {})
            for platform_id, platform_data in platforms_config.items():
                if platform_data.get('disabled', False):
                    self.disabled_platforms.add(platform_id)

        # Platform connectors (for reading chat - streamer account)
        self.connectors: Dict[str, object] = {}
        for pid, ctor in [
            ('twitch', TwitchConnector),
            ('youtube', YouTubeConnector),
            ('trovo', TrovoConnector),
            ('kick', KickConnector),
            ('dlive', DLiveConnector),
            ('twitter', TwitterConnector)
        ]:
            if pid not in self.disabled_platforms:
                self.connectors[pid] = ctor(self.config)
            else:
                print(f"[ChatManager] Not instantiating connector for disabled platform: {pid}")
        
        # Bot connectors (for sending messages - bot account)
        self.bot_connectors: Dict[str, object] = {}
        

        
        # Setup connectors
        for platform_id, connector in self.connectors.items():
            # Check if connector supports metadata (new connectors)
            if hasattr(connector, 'message_received_with_metadata'):
                # Wrap connection with a small tracer to guarantee TRACE output
                def _wrap_metadata(pid, u, m, md, _self=self, _pid=platform_id, _connector=connector):
                    try:
                        preview = m[:120] if m else ''
                    except Exception:
                        preview = ''
                    try:
                        print(f"[ChatManager][TRACE] signal->onMessageReceivedWithMetadata: platform={_pid} username={u} preview={preview} connector_id={id(_connector)} chat_manager_id={id(_self)}")
                    except Exception:
                        print(f"[ChatManager][TRACE] signal->onMessageReceivedWithMetadata: platform={_pid} username={u} preview={preview}")
                    _self.onMessageReceivedWithMetadata(_pid, u, m, md)

                connector.message_received_with_metadata.connect(_wrap_metadata)
                try:
                    print(f"[ChatManager] Connected message_received_with_metadata for {platform_id} (wrapped) connector_id={id(connector)} chat_manager_id={id(self)}")
                except Exception:
                    print(f"[ChatManager] Connected message_received_with_metadata for {platform_id} (wrapped)")
            else:
                # Fallback for old connectors without metadata
                def _wrap_legacy(u, m, pid=platform_id, _self=self, _connector=connector):
                    try:
                        preview = m[:120] if m else ''
                    except Exception:
                        preview = ''
                    try:
                        print(f"[ChatManager][TRACE] signal->onMessageReceived: platform={pid} username={u} preview={preview} connector_id={id(_connector)} chat_manager_id={id(_self)}")
                    except Exception:
                        print(f"[ChatManager][TRACE] signal->onMessageReceived: platform={pid} username={u} preview={preview}")
                    _self.onMessageReceived(pid, u, m)

                connector.message_received.connect(_wrap_legacy)
                try:
                    print(f"[ChatManager] Connected legacy message_received for {platform_id} connector_id={id(connector)} chat_manager_id={id(self)}")
                except Exception:
                    print(f"[ChatManager] Connected legacy message_received for {platform_id}")
            # Connect deletion signal if supported
            if hasattr(connector, 'message_deleted'):
                connector.message_deleted.connect(self.onMessageDeleted)
                print(f"[ChatManager] Connected message_deleted for {platform_id}")

        # Immediately disconnect any platform that is disabled but was previously running
        for disabled_pid in self.disabled_platforms:
            if disabled_pid in self.connectors:
                try:
                    self.connectors[disabled_pid].disconnect()
                    print(f"[ChatManager] Disconnected disabled platform: {disabled_pid}")
                except Exception as e:
                    print(f"[ChatManager] Error disconnecting disabled platform {disabled_pid}: {e}")
    
    def connectPlatform(self, platform_id: str, username: str, token: str = "") -> bool:
        """
        Connect to a platform
        
        Args:
            platform_id: The platform identifier (e.g., 'twitch')
            username: The username/channel to connect to
            token: OAuth token or API key (optional)
            
        Returns:
            True if connection initiated successfully
        """
        print(f"[ChatManager] connectPlatform: platform_id={platform_id}, username={username}, has_token={bool(token)}")
        
        connector = self.connectors.get(platform_id)
        if not connector:
            print(f"[ChatManager] ⚠ No connector found for {platform_id}")
            return False
        
        try:
            # Pass ngrok_manager to connector if available
            if self.ngrok_manager and hasattr(connector, 'ngrok_manager'):
                connector.ngrok_manager = self.ngrok_manager
            
            # Load cookies for Kick (stored during OAuth)
            if platform_id == 'kick' and hasattr(connector, 'set_cookies'):
                from core.config import ConfigManager
                config = ConfigManager()
                platform_config = config.get_platform_config(platform_id)
                cookies_json = platform_config.get('streamer_cookies', '')
                if cookies_json:
                    import json
                    try:
                        cookies = json.loads(cookies_json)
                        connector.set_cookies(cookies)
                        print(f"[ChatManager] Loaded {len(cookies)} cookies for Kick")
                    except Exception as e:
                        print(f"[ChatManager] Failed to load Kick cookies: {e}")
            
            # Set token if provided and connector supports it
            if token and hasattr(connector, 'set_token'):
                print(f"[ChatManager] Setting token for {platform_id} (length: {len(token)})")
                connector.set_token(token)
            elif token and hasattr(connector, 'set_api_key'):
                connector.set_api_key(token)
            
            # Start connection in background
            print(f"[ChatManager] Calling connect() for {platform_id}")
            connector.connect(username)
            self.connection_status_changed.emit(platform_id, True)
            self.streamer_connection_changed.emit(platform_id, True, username)
            return True
        except Exception as e:
            print(f"[ChatManager] ✗ Error connecting to {platform_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def disconnectPlatform(self, platform_id: str):
        """Disconnect from a platform"""
        connector = self.connectors.get(platform_id)
        if connector:
            connector.disconnect()
            self.connection_status_changed.emit(platform_id, False)
            self.streamer_connection_changed.emit(platform_id, False, "")
        
        # Also disconnect bot if connected
        bot_connector = self.bot_connectors.get(platform_id)
        if bot_connector:
            bot_connector.disconnect()
            del self.bot_connectors[platform_id]
            
            # Save bot disconnection state to config
            if self.config:
                # Use ConfigManager to save atomically
                self.config.set_platform_config(platform_id, 'bot_connected', False)
            
            # Emit signal to update UI
            self.bot_connection_changed.emit(platform_id, False, '')
    
    def connectBotAccount(self, platform_id: str, username: str, token: str, refresh_token: str = None):
        """Connect bot account for sending messages (doesn't listen for incoming messages)"""
        try:
            print(f"[ChatManager] Connecting bot account for {platform_id}: {username}")
            
            # Update config with bot credentials to ensure they're in memory
            if self.config:
                self.config.set_platform_config(platform_id, 'bot_username', username)
                self.config.set_platform_config(platform_id, 'bot_token', token)
                if refresh_token:
                    self.config.set_platform_config(platform_id, 'bot_refresh_token', refresh_token)
                print(f"[ChatManager] Bot credentials loaded into config memory")
            
            # For Twitch, Kick, DLive, and YouTube, we need to get the streamer's channel name
            # Bots should send to streamer's chat, not their own channel
            channel_to_join = username
            if platform_id in ['twitch', 'kick', 'dlive', 'youtube']:
                # Get the streamer's username from config
                platform_config = self.config.get_platform_config(platform_id) if self.config else {}
                streamer_username = platform_config.get('streamer_username', '') or platform_config.get('username', '')
                if streamer_username:
                    channel_to_join = streamer_username
                    print(f"[ChatManager] Bot will join streamer's channel: {channel_to_join}")
                else:
                    print(f"[ChatManager] ⚠ No streamer username found, bot will join its own channel")
            
            # Create new connector instance for bot
            if platform_id == 'twitch':
                bot_connector = TwitchConnector(self.config, is_bot_account=True)
            elif platform_id == 'youtube':
                bot_connector = YouTubeConnector(self.config)
            elif platform_id == 'trovo':
                bot_connector = TrovoConnector(self.config)
            elif platform_id == 'kick':
                bot_connector = KickConnector(self.config)
            elif platform_id == 'dlive':
                bot_connector = DLiveConnector(self.config)
            elif platform_id == 'twitter':
                bot_connector = TwitterConnector(self.config)
            else:
                print(f"[ChatManager] Unknown platform: {platform_id}")
                return False
            
            print(f"[ChatManager] Bot connector created for {platform_id}")
            
            # Debug: show token prefix to verify it's different from streamer
            token_prefix = token[:20] if token else "None"
            print(f"[ChatManager] Bot token (first 20 chars): {token_prefix}...")
            
            # For Twitch bot, use provided refresh token or get from config
            if platform_id == 'twitch':
                if not refresh_token:
                    platform_config = self.config.get_platform_config('twitch') if self.config else {}
                    refresh_token = platform_config.get('bot_refresh_token', '')
                
                if refresh_token:
                    print(f"[ChatManager] Bot has refresh token: {refresh_token[:20]}...")
                else:
                    print(f"[ChatManager] ⚠ No bot refresh token found")
            
            # Set bot credentials
            if platform_id in ['twitch', 'youtube', 'trovo', 'dlive']:
                # For Trovo, pass refresh token as well
                if platform_id == 'trovo':
                    bot_connector.set_token(token, refresh_token=refresh_token, is_bot=True)
                    print(f"[ChatManager] Token and refresh token set for Trovo bot")
                else:
                    bot_connector.set_token(token)
                    print(f"[ChatManager] Token set for {platform_id} bot")
                
                # For Twitch, also set refresh token if available
                if platform_id == 'twitch' and refresh_token:
                    bot_connector.refresh_token = refresh_token
                    print(f"[ChatManager] Refresh token set for Twitch bot")
            elif platform_id == 'kick':
                # Kick bot uses OAuth token with is_bot=True flag
                if hasattr(bot_connector, 'set_token'):
                    bot_connector.set_token(token, is_bot=True)
                    print(f"[ChatManager] Bot token set for Kick")
                else:
                    bot_connector.set_api_key(token)
                    print(f"[ChatManager] API key set for Kick bot (legacy)")
            elif platform_id == 'twitter':
                bot_connector.set_token(token)
                print(f"[ChatManager] Token set for {platform_id} bot")
            
            # For Twitch, set the bot username BEFORE connecting
            if platform_id == 'twitch' and hasattr(bot_connector, 'set_bot_username'):
                bot_connector.set_bot_username(username)
                print(f"[ChatManager] Bot username set to: {username}")

            # If we have a streamer connector instance for this platform,
            # attach it to the bot connector so the bot worker can forward
            # incoming messages to the streamer handler when necessary.
            try:
                streamer_conn = self.connectors.get(platform_id)
                if streamer_conn:
                    bot_connector.streamer_connector = streamer_conn
                    print(f"[ChatManager] Attached streamer connector {id(streamer_conn)} to bot connector {id(bot_connector)}")
            except Exception:
                pass
            
            # DO NOT connect message_received signals - we only want to send, not read
            # The streamer connector already handles reading messages
            
            # Connect bot account (maintains connection for sending)
            # For Twitch, pass the streamer's channel; for others, pass bot username
            print(f"[ChatManager] Calling connect() for {platform_id} bot to channel: {channel_to_join}...")
            connect_result = bot_connector.connect(channel_to_join)
            
            # Check if connection failed (e.g., invalid token)
            if connect_result is False:
                print(f"[ChatManager] ⚠️ Bot connection failed for {platform_id}. Clearing saved credentials.")
                # Clear bot credentials from config
                # Clear saved bot credentials using ConfigManager
                self.config.set_platform_config(platform_id, 'bot_token', '')
                self.config.set_platform_config(platform_id, 'bot_refresh_token', '')
                self.config.set_platform_config(platform_id, 'bot_username', '')
                self.config.set_platform_config(platform_id, 'bot_connected', False)
                self.config.set_platform_config(platform_id, 'bot_logged_in', False)
                self.config.set_platform_config(platform_id, 'bot_display_name', '')
                # Emit signal to update UI - pass username so dialog appears
                self.bot_connection_changed.emit(platform_id, False, username)
                
                print(f"[ChatManager] ⚠️ Bot credentials cleared. Please log out and log back in.")
                return
            
            # Store bot connector
            self.bot_connectors[platform_id] = bot_connector
            print(f"[ChatManager] ✓ Bot account connected for {platform_id}: {username}")
            
            # Save bot connection state to config for persistence
            # CRITICAL: Reload config before saving to avoid overwriting other platforms' data
            if self.config:
                self.config.set_platform_config(platform_id, 'bot_connected', True)
                # Verify the credentials were preserved
                bot_username_check = self.config.get_platform_config(platform_id).get('bot_username', '')
                print(f"[ChatManager] After save, bot_username in config: '{bot_username_check}'")
            
            # Emit signal to update UI
            self.bot_connection_changed.emit(platform_id, True, username)
            
            # Give it a moment to establish connection
            import time
            time.sleep(0.5)
            
            print(f"[ChatManager] Bot connector status: connected={getattr(bot_connector, 'connected', 'N/A')}")
            return True
        except Exception as e:
            print(f"[ChatManager] ✗ Error connecting bot account to {platform_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def sendMessageAsBot(self, platform_id: str, message: str, allow_fallback: bool = True):
        """
        Send message using bot account if connected, optionally using streamer account as fallback
        
        Args:
            platform_id: Platform to send on
            message: Message to send
            allow_fallback: If True, try streamer if bot fails. If False, only use bot.
            
        Returns:
            bool: True if message was sent successfully
        """
        # Try bot connector first
        bot_connector = self.bot_connectors.get(platform_id)
        if bot_connector:
            # For debugging: check both connected property and worker status
            has_worker = hasattr(bot_connector, 'worker') and bot_connector.worker is not None
            worker_connected = False
            if has_worker and hasattr(bot_connector.worker, 'websocket') and bot_connector.worker.websocket:
                worker_connected = True
            
            print(f"[ChatManager] Bot connector found for {platform_id}, connected={getattr(bot_connector, 'connected', False)}, has_worker={has_worker}, worker_connected={worker_connected}")
            
            try:
                # Check if bot can send messages
                # For platforms with persistent connections (Twitch, Kick), check connection status
                # For REST API platforms (Trovo, YouTube, DLive), just check if send_message exists
                if platform_id in ['trovo', 'youtube', 'dlive']:
                    # REST API platforms - no persistent connection needed
                    can_send = hasattr(bot_connector, 'send_message')
                else:
                    # WebSocket/IRC platforms - check connection status
                    can_send = getattr(bot_connector, 'connected', False) or worker_connected
                
                if hasattr(bot_connector, 'send_message') and can_send:
                    result = bot_connector.send_message(message)
                    
                    # Check if send was successful
                    if result:
                        print(f"[ChatManager] ✓ Sent message as bot on {platform_id}")
                        
                        # Echo the message to chat log (except for Twitch - IRC echoes automatically)
                        if platform_id != 'twitch':
                            from datetime import datetime
                            bot_config = self.config.get_platform_config(platform_id) if self.config else {}
                            bot_username = bot_config.get('bot_username', 'Bot')
                            metadata = {
                                'timestamp': datetime.now(),
                                'color': '#22B2B2',
                                'badges': [],
                                'emotes': ''
                            }
                            self.message_received.emit(platform_id, bot_username, message, metadata)
                        return True
                    else:
                        print(f"[ChatManager] ✗ Bot send failed for {platform_id}")
                        if not allow_fallback:
                            print(f"[ChatManager] ✗ Fallback disabled, not trying streamer")
                            return False
                        print(f"[ChatManager] Trying fallback to streamer...")
                        # Fall through to try streamer connector
                elif not can_send:
                    print(f"[ChatManager] ⚠ Bot connector not ready for {platform_id}")
                    if not allow_fallback:
                        print(f"[ChatManager] ✗ Fallback disabled, not trying streamer")
                        return False
                    print(f"[ChatManager] Falling back to streamer...")
                else:
                    print(f"[ChatManager] ⚠ Bot connector missing send_message for {platform_id}")
                    if not allow_fallback:
                        print(f"[ChatManager] ✗ Fallback disabled, not trying streamer")
                        return False
            except Exception as e:
                print(f"[ChatManager] ✗ Error sending as bot on {platform_id}: {e}")
                import traceback
                traceback.print_exc()
                if not allow_fallback:
                    print(f"[ChatManager] ✗ Fallback disabled after exception")
                    return False
        else:
            print(f"[ChatManager] No bot connector for {platform_id}")
            if not allow_fallback:
                print(f"[ChatManager] ✗ Fallback disabled, not trying streamer")
                return False
            print(f"[ChatManager] Using streamer as fallback...")
        
        # Fallback to streamer connector (only if allowed)
        if not allow_fallback:
            print(f"[ChatManager] ✗ Bot send failed and fallback disabled for {platform_id}")
            return False
        
        connector = self.connectors.get(platform_id)
        if connector and hasattr(connector, 'send_message'):
            print(f"[ChatManager] Streamer connector found for {platform_id}, connected={getattr(connector, 'connected', False)}")
            try:
                if getattr(connector, 'connected', False):
                    result = connector.send_message(message)
                    
                    # Check if send was successful
                    if result:
                        print(f"[ChatManager] ✓ Sent message as streamer on {platform_id}")
                        
                        # Echo the message to chat log (except for Twitch - IRC echoes automatically)
                        if platform_id != 'twitch':
                            from datetime import datetime
                            streamer_config = self.config.get_platform_config(platform_id) if self.config else {}
                            streamer_username = streamer_config.get('streamer_username') or streamer_config.get('username', 'Streamer')
                            metadata = {
                                'timestamp': datetime.now(),
                                'color': '#22B2B2',
                                'badges': [],
                                'emotes': ''
                            }
                            self.message_received.emit(platform_id, streamer_username, message, metadata)
                        return True
                    else:
                        print(f"[ChatManager] ✗ Streamer send also failed for {platform_id}")
                        return False
                else:
                    print(f"[ChatManager] ⚠ Streamer connector not connected for {platform_id}")
            except Exception as e:
                print(f"[ChatManager] ✗ Error sending as streamer on {platform_id}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[ChatManager] ✗ Failed to send message on {platform_id} - no available connectors")
        return False
    
    def disablePlatform(self, platform_id: str, disabled: bool):
        """Disable or enable a platform. When disabled, disconnects the platform (stops all background workers). When enabled, reconnects if credentials exist."""
        if disabled:
            self.disabled_platforms.add(platform_id)
            self.disconnectPlatform(platform_id)
        else:
            self.disabled_platforms.discard(platform_id)
            # Reconnect if credentials exist
            if self.config:
                platform_config = self.config.get_platform_config(platform_id)
                username = platform_config.get('streamer_username', '') or platform_config.get('username', '')
                token = platform_config.get('streamer_token', '') or platform_config.get('token', '')
                if username and token:
                    print(f"[ChatManager] Enabled {platform_id}, reconnecting...")
                    self.connectPlatform(platform_id, username, token)
        # Save disabled state to config
        if self.config:
            self.config.set_platform_config(platform_id, 'disabled', disabled)
    
    def onMessageReceived(self, platform_id: str, username: str, message: str):
        """Handle incoming message from a platform (legacy without metadata)"""
        # TRACE: log incoming legacy message receipt
        try:
            preview = message[:120] if message else ''
        except Exception:
            preview = ''
        print(f"[ChatManager][TRACE] onMessageReceived: platform={platform_id} username={username} preview={preview}")
        # Don't emit if platform is disabled
        if platform_id not in self.disabled_platforms:
            self.message_received.emit(platform_id, username, message, {})
        else:
            print(f"[ChatManager] Platform {platform_id} is disabled, message not emitted")
    
    def onMessageReceivedWithMetadata(self, platform_id: str, username: str, message: str, metadata: dict):
        """Handle incoming message from a platform with metadata (color, badges, timestamp)"""
        msg_preview = message[:50] + '...' if len(message) > 50 else message
        print(f"[ChatManager] onMessageReceivedWithMetadata: {platform_id}, {username}, {msg_preview}")
        # TRACE: show metadata keys and preview
        try:
            keys = list(metadata.keys()) if isinstance(metadata, dict) else []
        except Exception:
            keys = []
        print(f"[ChatManager][TRACE] onMessageReceivedWithMetadata: platform={platform_id} username={username} preview={msg_preview} metadata_keys={keys}")
        # Don't emit if platform is disabled
        if platform_id not in self.disabled_platforms:
            try:
                self.message_received.emit(platform_id, username, message, metadata)
                print(f"[ChatManager][TRACE] Emitted message_received for {platform_id} {username}")
            except Exception as e:
                print(f"[ChatManager] ✗ Error emitting message signal: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[ChatManager] Platform {platform_id} is disabled, message not emitted")
    
    def onMessageDeleted(self, platform_id: str, message_id: str):
        """Handle message deletion event from platform (moderator or auto-moderation)"""
        print(f"[ChatManager] onMessageDeleted: {platform_id}, message_id={message_id}")
        # Propagate deletion event to UI
        self.message_deleted.emit(platform_id, message_id)
    
    def deleteMessage(self, platform_id: str, message_id: str):
        """
        Delete a message from a platform
        
        Args:
            platform_id: The platform identifier (e.g., 'twitch')
            message_id: Platform-specific message ID
            
        Returns:
            bool: True if deletion was successful or attempted, False if not supported
        """
        connector = self.connectors.get(platform_id)
        if connector and hasattr(connector, 'delete_message'):
            try:
                result = connector.delete_message(message_id)
                print(f"[ChatManager] Deleted message {message_id} from {platform_id}")
                return True
            except Exception as e:
                print(f"[ChatManager] Error deleting message from {platform_id}: {e}")
                return False
        else:
            print(f"[ChatManager] Message deletion not supported for {platform_id}")
            return False
    
    def banUser(self, platform_id: str, username: str, user_id: str = None):
        """
        Ban a user from a platform
        
        Args:
            platform_id: The platform identifier (e.g., 'twitch')
            username: Username to ban
            user_id: Platform-specific user ID (if available)
        """
        connector = self.connectors.get(platform_id)
        if connector and hasattr(connector, 'ban_user'):
            try:
                connector.ban_user(username, user_id)
                print(f"[ChatManager] Banned user {username} from {platform_id}")
            except Exception as e:
                print(f"[ChatManager] Error banning user on {platform_id}: {e}")
        else:
            print(f"[ChatManager] User banning not supported for {platform_id}")
