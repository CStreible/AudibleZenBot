"""
Chat Manager - Manages connections and messages from all platforms
"""

import asyncio
import time
import os
from typing import Dict, Optional
from platform_connectors.qt_compat import QObject, pyqtSignal, QThread, QTimer, pyqtSlot
from core.logger import get_logger

# Structured logger for this module
logger = get_logger('ChatManager')

from core.config import ConfigManager


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
        # Import connector classes lazily to avoid importing heavy runtime
        # dependencies (like `requests`) at module import time which breaks
        # unit-test collection in CI environments where those deps are not
        # installed. Importing here delays that until ChatManager is actually
        # instantiated.
        self.connectors: Dict[str, object] = {}
        try:
            from platform_connectors.twitch_connector import TwitchConnector
        except Exception:
            TwitchConnector = None
        try:
            from platform_connectors.youtube_connector import YouTubeConnector
        except Exception:
            YouTubeConnector = None
        try:
            from platform_connectors.trovo_connector import TrovoConnector
        except Exception:
            TrovoConnector = None
        try:
            from platform_connectors.kick_connector import KickConnector
        except Exception:
            KickConnector = None
        try:
            from platform_connectors.dlive_connector import DLiveConnector
        except Exception:
            DLiveConnector = None
        try:
            from platform_connectors.twitter_connector import TwitterConnector
        except Exception:
            TwitterConnector = None

        # Expose connector constructors on the instance so other methods
        # (like `connectBotAccount`) can construct bot connectors without
        # relying on names that were only local to __init__'s scope.
        self.TwitchConnector = TwitchConnector
        self.YouTubeConnector = YouTubeConnector
        self.TrovoConnector = TrovoConnector
        self.KickConnector = KickConnector
        self.DLiveConnector = DLiveConnector
        self.TwitterConnector = TwitterConnector

        for pid, ctor in [
            ('twitch', TwitchConnector),
            ('youtube', YouTubeConnector),
            ('trovo', TrovoConnector),
            ('kick', KickConnector),
            ('dlive', DLiveConnector),
            ('twitter', TwitterConnector)
        ]:
            # In CI/test environments we may want to avoid instantiating
            # heavy connector classes which spawn threads or perform network
            # requests. Honor `AUDIBLEZENBOT_CI=1` to skip creating real
            # connectors; tests can opt-in to create lightweight stubs.
            if os.environ.get('AUDIBLEZENBOT_CI', '0') == '1':
                logger.info(f"CI mode active; skipping instantiation of connector for {pid}")
                continue

            if ctor is None:
                logger.info(f"Connector class for {pid} unavailable; skipping instantiation")
                continue
            if pid not in self.disabled_platforms:
                try:
                    self.connectors[pid] = ctor(self.config)
                except Exception as e:
                    logger.warning(f"Failed to instantiate connector for {pid}: {e}")
            else:
                logger.info(f"Not instantiating connector for disabled platform: {pid}")
        
        # Bot connectors (for sending messages - bot account)
        self.bot_connectors: Dict[str, object] = {}
        # Recent incoming message cache to suppress duplicates (platform, user, msg_lower, ts)
        self._recent_incoming = []
        # Recent message_id cache to suppress duplicate delivery when platforms provide IDs
        self._recent_message_ids = {}
        # Recent canonical message cache (normalized platform:username:message)
        # Used to match local echoes to incoming messages that differ only by
        # username formatting (underscores/spaces) or minor whitespace.
        self._recent_canonical = {}

        # Ensure diagnostic emitted log exists so we can verify emissions immediately
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            diag_file = os.path.join(log_dir, 'chatmanager_emitted.log')
            # Touch the file so external checks can find it even if no messages emitted yet
            with open(diag_file, 'a', encoding='utf-8', errors='replace'):
                pass
        except Exception:
            pass
        

        
        # Setup connectors
        for platform_id, connector in self.connectors.items():
            # Connect connector signals to ChatManager slots so Qt can queue across threads
            if hasattr(connector, 'message_received_with_metadata'):
                connector.message_received_with_metadata.connect(self._onConnectorMessageWithMetadata)
                try:
                    logger.info(f"Connected message_received_with_metadata for {platform_id} -> ChatManager._onConnectorMessageWithMetadata")
                except Exception:
                    logger.info(f"Connected message_received_with_metadata for {platform_id} -> ChatManager._onConnectorMessageWithMetadata")
            # Always connect legacy message_received as well if present
            if hasattr(connector, 'message_received'):
                connector.message_received.connect(self._onConnectorMessageLegacy)
                try:
                    logger.info(f"Connected legacy message_received for {platform_id} -> ChatManager._onConnectorMessageLegacy")
                except Exception:
                    logger.info(f"Connected legacy message_received for {platform_id} -> ChatManager._onConnectorMessageLegacy")
            # Connect deletion signal if supported
            if hasattr(connector, 'message_deleted'):
                connector.message_deleted.connect(self.onMessageDeleted)
                logger.info(f"Connected message_deleted for {platform_id}")
            # Assert connector conforms to minimal contract
            try:
                self._assert_connector_contract(platform_id, connector)
            except Exception:
                logger.warning(f"Connector contract assertion failed for {platform_id}")

    def _assert_connector_contract(self, platform_id: str, connector: object):
        """Runtime check to ensure connectors implement at least one of the
        expected incoming message signals. This helps catch legacy connectors
        during startup and surfaces a clear warning.
        """
        has_with_meta = hasattr(connector, 'message_received_with_metadata')
        has_legacy = hasattr(connector, 'message_received')
        if not has_with_meta and not has_legacy:
            logger.warning(f"Connector for '{platform_id}' exposes neither 'message_received_with_metadata' nor 'message_received'.")
        # Additional checks could validate signal types if needed

    @pyqtSlot(str, str, str, dict)
    def _onConnectorMessageWithMetadata(self, platform, username, message, metadata):
        """Slot invoked when a connector emits message_received_with_metadata.

        Using a Qt slot ensures the call is executed in the ChatManager's thread
        (queued connection) rather than directly on the connector's worker thread.
        """
        try:
            preview = message[:120] if message else ''
        except Exception:
            preview = ''
        try:
            logger.debug(f"[TRACE] _onConnectorMessageWithMetadata: platform={platform} username={username} preview={preview}")
        except Exception:
            logger.debug(f"[TRACE] _onConnectorMessageWithMetadata: platform={platform} username={username}")
        # Validate metadata shape before handing off
        try:
            metadata = self._normalize_and_validate_metadata(metadata)
        except Exception as e:
            logger.warning(f"Invalid metadata from {platform} by {username}: {e}")
            metadata = {} if metadata is None else metadata
        self.onMessageReceivedWithMetadata(platform, username, message, metadata)

    @pyqtSlot(str, str, str, dict)
    def _onConnectorMessageLegacy(self, platform, username, message, metadata):
        """Slot for legacy connectors that emit `message_received(platform, username, message, metadata)`.

        Some older connectors may only emit `message_received`; this slot bridges
        those emissions to the ChatManager legacy handler.
        """
        try:
            preview = message[:120] if message else ''
        except Exception:
            preview = ''
        try:
            logger.debug(f"[TRACE] _onConnectorMessageLegacy: platform={platform} username={username} preview={preview}")
        except Exception:
            logger.debug(f"[TRACE] _onConnectorMessageLegacy: platform={platform} username={username}")
        # If this looks like a Twitch IRC tag blob mistakenly sent as `username`,
        # delay handling briefly to allow the metadata-emitting path to run first.
        try:
            if platform == 'twitch' and isinstance(username, str):
                # Heuristic: tag-heavy usernames contain '/' or 'emotesv2_' or patterns like '0-12'
                if 'emotesv2_' in username or '/' in username or any(pat in username for pat in ('emotes=', 'emotes')):
                    try:
                        # Attempt to parse the tag blob and convert it into metadata immediately.
                        raw_user = username or ''
                        if ' :' in raw_user:
                            tag_part, real_user = raw_user.split(' :', 1)
                            # Parse semicolon-separated IRC tags into metadata dict
                            meta = {}
                            for kv in tag_part.split(';'):
                                if '=' in kv:
                                    k, v = kv.split('=', 1)
                                    meta[k] = v
                            # Promote known keys
                            md = {}
                            if 'emotes' in meta and meta.get('emotes'):
                                md['emotes'] = meta.get('emotes')
                            if 'id' in meta and meta.get('id'):
                                md['message_id'] = meta.get('id')
                            # Include timestamp and badges if present
                            for k in ('tmi-sent-ts', 'timestamp', 'badges', 'color'):
                                if k in meta and meta.get(k):
                                    md[k] = meta.get(k)
                            # Use recovered username as the display name
                            recovered_username = real_user.strip()
                            # Emit via the metadata path to ensure uniform handling
                            try:
                                self.onMessageReceivedWithMetadata(platform, recovered_username, message, md)
                                return
                            except Exception:
                                # Fallback to legacy emit if metadata path fails
                                try:
                                    self.onMessageReceived(platform, username, message)
                                    return
                                except Exception:
                                    pass
                    except Exception:
                        pass
        except Exception:
            pass

        # Legacy path: ensure metadata is a dict-like object if provided
        try:
            metadata = self._normalize_and_validate_metadata(metadata)
        except Exception:
            metadata = {}
        # Call the legacy handler which will emit message_received after checks
        self.onMessageReceived(platform, username, message)

        # Immediately disconnect any platform that is disabled but was previously running
        for disabled_pid in self.disabled_platforms:
            if disabled_pid in self.connectors:
                try:
                    self.connectors[disabled_pid].disconnect()
                    logger.info(f"Disconnected disabled platform: {disabled_pid}")
                except Exception as e:
                    logger.error(f"Error disconnecting disabled platform {disabled_pid}: {e}")
    
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
        logger.info(f"connectPlatform: platform_id={platform_id}, username={username}, has_token={bool(token)}")
        
        connector = self.connectors.get(platform_id)
        if not connector:
            logger.warning(f"No connector found for {platform_id}")
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
                        logger.info(f"Loaded {len(cookies)} cookies for Kick")
                    except Exception as e:
                        logger.error(f"Failed to load Kick cookies: {e}")

            # Set token if provided and connector supports it
            if token and hasattr(connector, 'set_token'):
                logger.debug(f"Setting token for {platform_id} (length: {len(token)})")
                connector.set_token(token)
            elif token and hasattr(connector, 'set_api_key'):
                connector.set_api_key(token)

            # Start connection in background
            logger.info(f"Calling connect() for {platform_id}")
            connector.connect(username)

            # Wait briefly for the connector to report its actual connected state.
            # Worker threads may take a short time to emit status; poll up to 3s.
            import time
            waited = 0.0
            timeout = 3.0
            interval = 0.1
            try:
                while waited < timeout:
                    if getattr(connector, 'connected', False):
                        break
                    time.sleep(interval)
                    waited += interval
            except KeyboardInterrupt:
                logger.info(f"connectPlatform interrupted while waiting for {platform_id}")
                return False

            connected_state = bool(getattr(connector, 'connected', False))
            self.connection_status_changed.emit(platform_id, connected_state)
            self.streamer_connection_changed.emit(platform_id, connected_state, username)
            return True
        except Exception as e:
            logger.error(f"Error connecting to {platform_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _normalize_and_validate_metadata(self, metadata):
        """Ensure metadata is a dict and normalize common fields.

        Rules:
        - `metadata` must be a dict or None
        - If `message_id` present, coerce to string
        - If `timestamp` or `tmi-sent-ts` present, leave as-is but ensure it's a str/int
        """
        if metadata is None:
            return {}
        if not isinstance(metadata, dict):
            raise TypeError('metadata must be a dict')
        md = dict(metadata)
        if 'message_id' in md and md['message_id'] is not None:
            md['message_id'] = str(md['message_id'])
        # normalize timestamp keys
        for tkey in ('tmi-sent-ts', 'timestamp'):
            if tkey in md and md[tkey] is not None:
                # accept numeric or string timestamps
                if not isinstance(md[tkey], (int, str)):
                    md[tkey] = str(md[tkey])
        return md
        
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
                        logger.info(f"Loaded {len(cookies)} cookies for Kick")
                    except Exception as e:
                        logger.error(f"Failed to load Kick cookies: {e}")
            
            # Set token if provided and connector supports it
            if token and hasattr(connector, 'set_token'):
                logger.debug(f"Setting token for {platform_id} (length: {len(token)})")
                connector.set_token(token)
            elif token and hasattr(connector, 'set_api_key'):
                connector.set_api_key(token)
            
            # Start connection in background
            logger.info(f"Calling connect() for {platform_id}")
            connector.connect(username)

            # Wait briefly for the connector to report its actual connected state.
            # Worker threads may take a short time to emit status; poll up to 3s.
            import time
            waited = 0.0
            timeout = 3.0
            interval = 0.1
            try:
                while waited < timeout:
                    if getattr(connector, 'connected', False):
                        break
                    time.sleep(interval)
                    waited += interval
            except KeyboardInterrupt:
                logger.info(f"connectPlatform interrupted while waiting for {platform_id}")
                return False

            connected_state = bool(getattr(connector, 'connected', False))
            self.connection_status_changed.emit(platform_id, connected_state)
            self.streamer_connection_changed.emit(platform_id, connected_state, username)
            return True
        except Exception as e:
            logger.error(f"Error connecting to {platform_id}: {e}")
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
            # In CI mode we avoid creating real bot connectors which spawn threads
            # or perform network requests. Honor the AUDIBLEZENBOT_CI flag and
            # short-circuit the connection process while preserving in-memory
            # config state so callers that expect a truthy return value still
            # proceed during tests.
            if os.environ.get('AUDIBLEZENBOT_CI', '0') == '1':
                logger.info(f"CI mode active; skipping bot connector creation for {platform_id}")
                if self.config:
                    # Load credentials into config memory but do not attempt network
                    self.config.set_platform_config(platform_id, 'bot_username', username)
                    self.config.set_platform_config(platform_id, 'bot_token', token)
                    if refresh_token:
                        self.config.set_platform_config(platform_id, 'bot_refresh_token', refresh_token)
                # Emit UI update signal to indicate a bot is 'available' without connecting
                try:
                    self.bot_connection_changed.emit(platform_id, False, username)
                except Exception:
                    pass
                return True

            logger.info(f"Connecting bot account for {platform_id}: {username}")
            
            # Update config with bot credentials to ensure they're in memory
            if self.config:
                self.config.set_platform_config(platform_id, 'bot_username', username)
                self.config.set_platform_config(platform_id, 'bot_token', token)
                if refresh_token:
                    self.config.set_platform_config(platform_id, 'bot_refresh_token', refresh_token)
                logger.debug(f"Bot credentials loaded into config memory")
            
            # For Twitch, Kick, DLive, and YouTube, we need to get the streamer's channel name
            # Bots should send to streamer's chat, not their own channel
            channel_to_join = username
            if platform_id in ['twitch', 'kick', 'dlive', 'youtube']:
                # Get the streamer's username from config
                platform_config = self.config.get_platform_config(platform_id) if self.config else {}
                streamer_username = platform_config.get('streamer_username', '') or platform_config.get('username', '')
                if streamer_username:
                    channel_to_join = streamer_username
                    logger.debug(f"Bot will join streamer's channel: {channel_to_join}")
                else:
                    logger.warning(f"No streamer username found, bot will join its own channel")
            
            # Create new connector instance for bot
            if platform_id == 'twitch':
                ctor = getattr(self, 'TwitchConnector', None)
                if ctor is None:
                    raise RuntimeError('TwitchConnector not available')
                bot_connector = ctor(self.config, is_bot_account=True)
            elif platform_id == 'youtube':
                ctor = getattr(self, 'YouTubeConnector', None)
                if ctor is None:
                    raise RuntimeError('YouTubeConnector not available')
                bot_connector = ctor(self.config)
            elif platform_id == 'trovo':
                ctor = getattr(self, 'TrovoConnector', None)
                if ctor is None:
                    raise RuntimeError('TrovoConnector not available')
                bot_connector = ctor(self.config)
            elif platform_id == 'kick':
                ctor = getattr(self, 'KickConnector', None)
                if ctor is None:
                    raise RuntimeError('KickConnector not available')
                bot_connector = ctor(self.config)
            elif platform_id == 'dlive':
                ctor = getattr(self, 'DLiveConnector', None)
                if ctor is None:
                    raise RuntimeError('DLiveConnector not available')
                bot_connector = ctor(self.config)
            elif platform_id == 'twitter':
                ctor = getattr(self, 'TwitterConnector', None)
                if ctor is None:
                    raise RuntimeError('TwitterConnector not available')
                bot_connector = ctor(self.config)
            else:
                logger.error(f"Unknown platform: {platform_id}")
                return False
            
            logger.info(f"Bot connector created for {platform_id}")

            # Connect bot connector signals to ChatManager so webhook-driven bot instances
            # also route incoming messages into the central message pipeline.
            try:
                if hasattr(bot_connector, 'message_received_with_metadata'):
                    bot_connector.message_received_with_metadata.connect(self._onConnectorMessageWithMetadata)
                    logger.info(f"Connected bot message_received_with_metadata for {platform_id} -> ChatManager._onConnectorMessageWithMetadata")
                if hasattr(bot_connector, 'message_received'):
                    bot_connector.message_received.connect(self._onConnectorMessageLegacy)
                    logger.info(f"Connected bot legacy message_received for {platform_id} -> ChatManager._onConnectorMessageLegacy")
                if hasattr(bot_connector, 'message_deleted'):
                    bot_connector.message_deleted.connect(self.onMessageDeleted)
                    logger.info(f"Connected bot message_deleted for {platform_id} -> ChatManager.onMessageDeleted")
            except Exception as e:
                logger.warning(f"Warning: failed to connect bot signals for {platform_id}: {e}")
            
            # Debug: show token prefix to verify it's different from streamer
            token_prefix = token[:20] if token else "None"
            logger.debug(f"Bot token (first 20 chars): {token_prefix}...")
            
            # For Twitch bot, use provided refresh token or get from config
            if platform_id == 'twitch':
                if not refresh_token:
                    platform_config = self.config.get_platform_config('twitch') if self.config else {}
                    refresh_token = platform_config.get('bot_refresh_token', '')
                
                if refresh_token:
                    logger.debug(f"Bot has refresh token: {refresh_token[:20]}...")
                else:
                    logger.warning(f"No bot refresh token found")
            
            # Set bot credentials
            if platform_id in ['twitch', 'youtube', 'trovo', 'dlive']:
                # For Trovo, pass refresh token as well
                if platform_id == 'trovo':
                    bot_connector.set_token(token, refresh_token=refresh_token, is_bot=True)
                    logger.debug(f"Token and refresh token set for Trovo bot")
                else:
                    bot_connector.set_token(token)
                    logger.debug(f"Token set for {platform_id} bot")
                
                # For Twitch, also set refresh token if available
                if platform_id == 'twitch' and refresh_token:
                    bot_connector.refresh_token = refresh_token
                    logger.debug(f"Refresh token set for Twitch bot")
            elif platform_id == 'kick':
                # Kick bot uses OAuth token with is_bot=True flag
                if hasattr(bot_connector, 'set_token'):
                    bot_connector.set_token(token, is_bot=True)
                    logger.debug(f"Bot token set for Kick")
                else:
                    bot_connector.set_api_key(token)
                    logger.debug(f"API key set for Kick bot (legacy)")
            elif platform_id == 'twitter':
                bot_connector.set_token(token)
                logger.debug(f"Token set for {platform_id} bot")
            
            # For Twitch, set the bot username BEFORE connecting
            if platform_id == 'twitch' and hasattr(bot_connector, 'set_bot_username'):
                bot_connector.set_bot_username(username)
                logger.debug(f"Bot username set to: {username}")

            # If we have a streamer connector instance for this platform,
            # attach it to the bot connector so the bot worker can forward
            # incoming messages to the streamer handler when necessary.
            try:
                streamer_conn = self.connectors.get(platform_id)
                if streamer_conn:
                    bot_connector.streamer_connector = streamer_conn
                    logger.debug(f"Attached streamer connector {id(streamer_conn)} to bot connector {id(bot_connector)}")
            except Exception:
                pass
            
            # DO NOT connect message_received signals - we only want to send, not read
            # The streamer connector already handles reading messages
            
            # Connect bot account (maintains connection for sending)
            # For Twitch, pass the streamer's channel; for others, pass bot username
            logger.info(f"Calling connect() for {platform_id} bot to channel: {channel_to_join}...")
            connect_result = bot_connector.connect(channel_to_join)
            
            # Check if connection failed (e.g., invalid token)
            if connect_result is False:
                logger.warning(f"Bot connection failed for {platform_id}. Clearing saved credentials.")
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
                
                logger.warning(f"Bot credentials cleared. Please log out and log back in.")
                return
            
            # Store bot connector
            self.bot_connectors[platform_id] = bot_connector
            logger.info(f"Bot account connected for {platform_id}: {username}")
            
            # Save bot connection state to config for persistence
            # CRITICAL: Reload config before saving to avoid overwriting other platforms' data
            if self.config:
                self.config.set_platform_config(platform_id, 'bot_connected', True)
                # Verify the credentials were preserved
                bot_username_check = self.config.get_platform_config(platform_id).get('bot_username', '')
                logger.debug(f"After save, bot_username in config: '{bot_username_check}'")
            
            # Emit signal to update UI
            self.bot_connection_changed.emit(platform_id, True, username)
            
            # Wait briefly for the bot connector to report its actual connected state.
            # Worker runs in another thread and may take a short moment to emit status.
            import time
            waited = 0.0
            timeout = 3.0
            interval = 0.1
            while waited < timeout:
                if getattr(bot_connector, 'connected', False):
                    break
                time.sleep(interval)
                waited += interval

            logger.info(f"Bot connector status: connected={getattr(bot_connector, 'connected', 'N/A')}")
            return True
        except Exception as e:
            logger.error(f"Error connecting bot account to {platform_id}: {e}")
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
        # Diagnostic: dump current connector maps
        try:
            bot_states = {k: getattr(v, 'connected', False) for k, v in self.bot_connectors.items()}
            streamer_states = {k: getattr(v, 'connected', False) for k, v in self.connectors.items()}
            logger.debug(f"[SEND-TRACE] bot_connectors={bot_states} connectors={streamer_states}")
        except Exception:
            pass

        # Try bot connector first
        bot_connector = self.bot_connectors.get(platform_id)
        if bot_connector:
            # For debugging: check both connected property and worker status
            has_worker = hasattr(bot_connector, 'worker') and bot_connector.worker is not None
            worker_connected = False
            if has_worker and hasattr(bot_connector.worker, 'websocket') and bot_connector.worker.websocket:
                worker_connected = True

            logger.info(f"Bot connector found for {platform_id}, connected={getattr(bot_connector, 'connected', False)}, has_worker={has_worker}, worker_connected={worker_connected}")
            # Extra diagnostics: if worker exists, log live_chat_id and last poll time
            try:
                worker = getattr(bot_connector, 'worker', None)
                if worker is not None:
                    lc = getattr(worker, 'live_chat_id', None)
                    lpoll = getattr(worker, 'last_successful_poll', None)
                    logger.debug(f"Bot worker diagnostics for {platform_id}: live_chat_id={lc} last_successful_poll={lpoll}")
            except Exception:
                pass

            try:
                # Determine if bot can send messages
                if platform_id in ['trovo', 'youtube', 'dlive']:
                    # REST API platforms - no persistent connection needed
                    can_send = hasattr(bot_connector, 'send_message')
                else:
                    # WebSocket/IRC platforms - check connection status
                    can_send = getattr(bot_connector, 'connected', False) or worker_connected

                if hasattr(bot_connector, 'send_message') and can_send:
                    result = bot_connector.send_message(message)
                    # Persistent send log for debugging
                    try:
                        log_dir = os.path.join(os.getcwd(), 'logs')
                        os.makedirs(log_dir, exist_ok=True)
                        with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                            sf.write(f"{time.time():.3f} platform={platform_id} used=bot connected={getattr(bot_connector, 'connected', False)} preview={repr(message)[:200]}\n")
                    except Exception:
                        pass

                    if result:
                        logger.info(f"[OK] Sent message as bot on {platform_id}")
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
                            # Use onMessageReceivedWithMetadata so de-duplication runs and prevents
                            # duplicate display when the connector later emits the same incoming message.
                            try:
                                self.onMessageReceivedWithMetadata(platform_id, bot_username, message, metadata)
                            except Exception:
                                # Fallback to direct emit if something unexpected fails
                                self.message_received.emit(platform_id, bot_username, message, metadata)
                        return True
                    else:
                        logger.error(f"Bot send failed for {platform_id}")
                        if not allow_fallback:
                            logger.error("Fallback disabled, not trying streamer")
                            return False
                        logger.info("Trying fallback to streamer...")
                elif not can_send:
                    logger.warning(f"Bot connector not ready for {platform_id}")
                    if not allow_fallback:
                        logger.error("Fallback disabled, not trying streamer")
                        return False
                    logger.info("Falling back to streamer...")
                else:
                    logger.warning(f"Bot connector missing send_message for {platform_id}")
                    if not allow_fallback:
                        logger.error("Fallback disabled, not trying streamer")
                        return False
            except Exception as e:
                logger.exception(f"Error sending as bot on {platform_id}: {e}")
                import traceback
                traceback.print_exc()
                if not allow_fallback:
                    logger.error("Fallback disabled after exception")
                    return False
        else:
            logger.info(f"No bot connector for {platform_id}")
            if not allow_fallback:
                logger.error("Fallback disabled, not trying streamer")
                return False
            logger.info("Using streamer as fallback...")

        # Fallback to streamer connector (only if allowed)
        if not allow_fallback:
            logger.error(f"Bot send failed and fallback disabled for {platform_id}")
            return False

        connector = self.connectors.get(platform_id)
        if connector and hasattr(connector, 'send_message'):
            logger.info(f"Streamer connector found for {platform_id}, connected={getattr(connector, 'connected', False)}")
            try:
                # Persistent send log for fallback/streamer path
                try:
                    log_dir = os.path.join(os.getcwd(), 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, 'chatmanager_sends.log'), 'a', encoding='utf-8', errors='replace') as sf:
                        sf.write(f"{time.time():.3f} platform={platform_id} used=streamer connected={getattr(connector, 'connected', False)} preview={repr(message)[:200]}\n")
                except Exception:
                    pass

                if getattr(connector, 'connected', False):
                    result = connector.send_message(message)
                    if result:
                        logger.info(f"[OK] Sent message as streamer on {platform_id}")
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
                            # Call onMessageReceivedWithMetadata to run de-duplication before emitting
                            try:
                                self.onMessageReceivedWithMetadata(platform_id, streamer_username, message, metadata)
                            except Exception:
                                self.message_received.emit(platform_id, streamer_username, message, metadata)
                        return True
                    else:
                        logger.error(f"Streamer send also failed for {platform_id}")
                        return False
                else:
                    logger.warning(f"Streamer connector not connected for {platform_id}")
            except Exception as e:
                logger.exception(f"Error sending as streamer on {platform_id}: {e}")
                import traceback
                traceback.print_exc()

        logger.error(f"Failed to send message on {platform_id} - no available connectors")
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
                    logger.info(f"Enabled {platform_id}, reconnecting...")
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
        logger.debug(f"[TRACE] onMessageReceived: platform={platform_id} username={username} preview={preview}")
        # Route legacy messages through the metadata handler so de-duplication
        # and canonical checks run uniformly for all incoming messages.
        try:
            if platform_id not in self.disabled_platforms:
                self.onMessageReceivedWithMetadata(platform_id, username, message, {})
            else:
                logger.info(f"Platform {platform_id} is disabled, message not emitted")
        except Exception as e:
            logger.exception(f"Error handling legacy message for {platform_id}: {e}")
    
    def onMessageReceivedWithMetadata(self, platform_id: str, username: str, message: str, metadata: dict):
        """Handle incoming message from a platform with metadata (color, badges, timestamp)"""
        msg_preview = message[:50] + '...' if len(message) > 50 else message
        logger.info(f"onMessageReceivedWithMetadata: {platform_id}, {username}, {msg_preview}")
        # TRACE: show metadata keys and preview
        try:
            keys = list(metadata.keys()) if isinstance(metadata, dict) else []
        except Exception:
            keys = []
        logger.debug(f"[TRACE] onMessageReceivedWithMetadata: platform={platform_id} username={username} preview={msg_preview} metadata_keys={keys}")
        # Don't emit if platform is disabled
        if platform_id in self.disabled_platforms:
            logger.info(f"Platform {platform_id} is disabled, message not emitted")
            return

        # Heuristic: some connectors may accidentally place IRC tag payload into the
        # `username` field (e.g., "...;id=xxx;... :realuser"). If metadata is empty
        # or minimal, attempt to recover emotes/message_id and the real username so
        # downstream canonicalization/deduplication works correctly.
        try:
            if platform_id == 'twitch' and (not isinstance(metadata, dict) or not metadata.keys()):
                raw_user = username or ''
                # Look for the common pattern where tags and the real username are joined with ' :'
                if ' :' in raw_user:
                    tag_part, real_user = raw_user.split(' :', 1)
                    first_token = tag_part.split(';', 1)[0]
                    if first_token and ('emotes' in first_token or 'emotesv2_' in first_token or ('-' in first_token and '/' in first_token)):
                        # Recover emotes tag into metadata and set username to real_user
                        try:
                            if not isinstance(metadata, dict):
                                metadata = {}
                        except Exception:
                            metadata = {}
                        try:
                            metadata['emotes'] = first_token
                        except Exception:
                            pass
                        try:
                            # try to find id=... in the tag_part
                            for kv in tag_part.split(';'):
                                if '=' in kv:
                                    k, v = kv.split('=', 1)
                                    if k == 'id' and v:
                                        metadata['message_id'] = v
                                        break
                        except Exception:
                            pass
                        # Replace username with cleaned real username
                        username = real_user.strip()
                        # Durable debug log
                        try:
                            log_dir = os.path.join(os.getcwd(), 'logs')
                            os.makedirs(log_dir, exist_ok=True)
                            with open(os.path.join(log_dir, 'chatmanager_username_fix.log'), 'a', encoding='utf-8', errors='replace') as f:
                                f.write(f"{time.time():.3f} FIXED platform={platform_id} raw_username={repr(raw_user)} recovered_username={repr(username)} emotes={repr(metadata.get('emotes'))} message_id={repr(metadata.get('message_id'))}\n")
                        except Exception:
                            pass
        except Exception:
            pass

        # De-duplication: suppress duplicate incoming messages from multiple connections
        try:
            now = time.time()
            msg_key = (platform_id, username, (message or '').strip().lower())
            # If platform provided a message_id, use it to suppress duplicates first
            msg_id = None
            try:
                msg_id = metadata.get('message_id') if isinstance(metadata, dict) else None
            except Exception:
                msg_id = None
            if msg_id:
                prev = self._recent_message_ids.get(msg_id)
                if prev and (now - prev) < 2.0:
                    logger.debug(f"[TRACE] Suppressing duplicate by message_id: {msg_id}")
                    return
                # record this id
                try:
                    self._recent_message_ids[msg_id] = now
                    # prune oldest entries if map grows too large
                    if len(self._recent_message_ids) > 2000:
                        # remove oldest 25%
                        items = sorted(self._recent_message_ids.items(), key=lambda kv: kv[1])
                        for k, _ in items[: max(1, len(items)//4)]:
                            try:
                                del self._recent_message_ids[k]
                            except Exception:
                                pass
                except Exception:
                    pass

            # Canonical normalization: collapse username formatting and whitespace
            try:
                uname_norm = ''.join([c for c in (username or '').lower() if c.isalnum()])
            except Exception:
                uname_norm = (username or '').lower()
            try:
                msg_norm = (message or '').strip().lower()
            except Exception:
                msg_norm = (message or '').lower() if message else ''
            canonical = f"{platform_id}:{uname_norm}:{msg_norm}"
            # If we've recently seen the canonical signature, suppress duplicate
            prev_can = self._recent_canonical.get(canonical)
            if prev_can and (now - prev_can) < 2.0:
                logger.debug(f"[TRACE] Suppressing duplicate by canonical key: {canonical} age={(now-prev_can):.3f}s")
                return
            # Record canonical occurrence for short window
            try:
                self._recent_canonical[canonical] = now
                # prune oldest canonicals if map grows too large
                if len(self._recent_canonical) > 2000:
                    items = sorted(self._recent_canonical.items(), key=lambda kv: kv[1])
                    for k, _ in items[: max(1, len(items)//4)]:
                        try:
                            del self._recent_canonical[k]
                        except Exception:
                            pass
            except Exception:
                pass
            # prune old entries
            self._recent_incoming = [t for t in self._recent_incoming if now - t[3] < 0.8]
            # check for duplicate
            for (p, u, m, ts) in self._recent_incoming:
                if p == msg_key[0] and u == msg_key[1] and m == msg_key[2]:
                    logger.debug(f"[TRACE] Suppressing duplicate message from {username} on {platform_id}: {message[:120]}")
                    return
            # record this message
            self._recent_incoming.append((msg_key[0], msg_key[1], msg_key[2], now))
        except Exception:
            pass

        try:
            self.message_received.emit(platform_id, username, message, metadata)
            logger.debug(f"[TRACE] Emitted message_received for {platform_id} {username}")
            # Persistent diagnostic log to track emitted messages
            try:
                log_dir = os.path.join(os.getcwd(), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                diag_file = os.path.join(log_dir, 'chatmanager_emitted.log')
                with open(diag_file, 'a', encoding='utf-8', errors='replace') as df:
                    df.write(f"{time.time():.3f} platform={platform_id} username={username} preview={repr(message)[:200]} metadata_keys={list(metadata.keys())}\n")
            except Exception:
                pass
            # Additional debug: write full metadata and message id for tracing
            try:
                debug_file = os.path.join(log_dir, 'chatmanager_emit_debug.log')
                with open(debug_file, 'a', encoding='utf-8', errors='replace') as df:
                    mid = None
                    try:
                        if isinstance(metadata, dict):
                            mid = metadata.get('message_id') or metadata.get('id')
                    except Exception:
                        mid = None
                    df.write(f"{time.time():.3f} EMIT platform={platform_id} username={username} message_id={repr(mid)} metadata={repr(metadata)} preview={repr(message)[:200]}\n")
            except Exception:
                pass
        except Exception as e:
            logger.exception(f"Error emitting message signal: {e}")
            import traceback
            traceback.print_exc()
    
    def onMessageDeleted(self, platform_id: str, message_id: str):
        """Handle message deletion event from platform (moderator or auto-moderation)"""
        logger.info(f"onMessageDeleted: {platform_id}, message_id={message_id}")
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
                logger.info(f"Deleted message {message_id} from {platform_id}")
                return True
            except Exception as e:
                logger.exception(f"Error deleting message from {platform_id}: {e}")
                return False
        else:
            logger.info(f"Message deletion not supported for {platform_id}")
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
                logger.info(f"Banned user {username} from {platform_id}")
            except Exception as e:
                logger.exception(f"Error banning user on {platform_id}: {e}")
        else:
            logger.info(f"User banning not supported for {platform_id}")

    def dump_connector_states(self) -> dict:
        """Return a diagnostic snapshot of connector and bot states.

        Useful for CLI/diagnostic scripts to inspect which connectors are
        connected and relevant runtime details (webhook URLs, last message time).
        """
        snapshot = {
            'connectors': {},
            'bot_connectors': {},
            'ngrok_tunnels': {}
        }

        try:
            for pid, conn in self.connectors.items():
                try:
                    info = {
                        'connected': bool(getattr(conn, 'connected', False)),
                        'has_worker': hasattr(conn, 'worker') and conn.worker is not None,
                        'username': getattr(conn, 'username', None),
                    }
                    # Kick-specific fields
                    if pid == 'kick':
                        info['webhook_url'] = getattr(conn, 'webhook_url', None)
                        info['webhook_port'] = getattr(conn, 'webhook_port', None)
                        info['last_message_time'] = getattr(conn, 'last_message_time', None)
                        info['subscription_active'] = getattr(conn, 'subscription_active', False)
                    snapshot['connectors'][pid] = info
                except Exception:
                    snapshot['connectors'][pid] = {'error': 'failed to inspect connector'}

            for pid, bot in self.bot_connectors.items():
                try:
                    snapshot['bot_connectors'][pid] = {
                        'connected': bool(getattr(bot, 'connected', False)),
                        'username': getattr(bot, 'username', None)
                    }
                except Exception:
                    snapshot['bot_connectors'][pid] = {'error': 'failed to inspect bot connector'}

            if self.ngrok_manager:
                try:
                    snapshot['ngrok_tunnels'] = self.ngrok_manager.get_all_tunnels()
                except Exception:
                    snapshot['ngrok_tunnels'] = {'error': 'failed to get ngrok tunnels'}
        except Exception as e:
            snapshot['error'] = str(e)

        return snapshot
