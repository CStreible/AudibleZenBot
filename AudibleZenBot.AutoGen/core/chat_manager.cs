using System;
using System.Threading.Tasks;

namespace core.chat_manager {
    public static class Chat_managerModule {
        // Original: def __init__(self, config=None)
        public static void Init(object? config = null) {
            // TODO: implement
        }

        // Original: def _onConnectorMessageWithMetadata(self, platform, username, message, metadata)
        public static void OnConnectorMessageWithMetadata(object? platform, object? username, object? message, object? metadata) {
            // TODO: implement
        }

        // Original: def _onConnectorMessageLegacy(self, platform, username, message, metadata)
        public static void OnConnectorMessageLegacy(object? platform, object? username, object? message, object? metadata) {
            // TODO: implement
        }

        // Original: def connectPlatform(self, platform_id: str, username: str, token: str = "")
        public static void ConnectPlatform(string? platform_id, string? username, string? token = null) {
            // TODO: implement
        }

        // Original: def disconnectPlatform(self, platform_id: str)
        public static void DisconnectPlatform(string? platform_id) {
            // TODO: implement
        }

        // Original: def connectBotAccount(self, platform_id: str, username: str, token: str, refresh_token: str = None)
        public static void ConnectBotAccount(string? platform_id, string? username, string? token, string? refresh_token = null) {
            // TODO: implement
        }

        // Original: def sendMessageAsBot(self, platform_id: str, message: str, allow_fallback: bool = True)
        public static void SendMessageAsBot(string? platform_id, string? message, bool? allow_fallback = null) {
            // TODO: implement
        }

        // Original: def disablePlatform(self, platform_id: str, disabled: bool)
        public static void DisablePlatform(string? platform_id, bool? disabled) {
            // TODO: implement
        }

        // Original: def onMessageReceived(self, platform_id: str, username: str, message: str)
        public static void OnMessageReceived(string? platform_id, string? username, string? message) {
            // TODO: implement
        }

        // Original: def onMessageReceivedWithMetadata(self, platform_id: str, username: str, message: str, metadata: dict)
        public static void OnMessageReceivedWithMetadata(string? platform_id, string? username, string? message, System.Collections.Generic.Dictionary<string,object>? metadata) {
            // TODO: implement
        }

        // Original: def onMessageDeleted(self, platform_id: str, message_id: str)
        public static void OnMessageDeleted(string? platform_id, string? message_id) {
            // TODO: implement
        }

        // Original: def deleteMessage(self, platform_id: str, message_id: str)
        public static void DeleteMessage(string? platform_id, string? message_id) {
            // TODO: implement
        }

        // Original: def banUser(self, platform_id: str, username: str, user_id: str = None)
        public static void BanUser(string? platform_id, string? username, string? user_id = null) {
            // TODO: implement
        }

        // Original: def dump_connector_states(self)
        public static void DumpConnectorStates() {
            // TODO: implement
        }

    }

    public class ChatManager {
        public bool? config { get; set; }
        public bool? ngrok_manager { get; set; }
        public object? disabled_platforms { get; set; }
        public object? connectors { get; set; }
        public object? bot_connectors { get; set; }
        public System.Collections.Generic.List<object>? _recent_incoming { get; set; }
        public System.Collections.Generic.Dictionary<string,object>? _recent_message_ids { get; set; }
        public System.Collections.Generic.Dictionary<string,object>? _recent_canonical { get; set; }
        public object? onMessageReceivedWithMetadat { get; set; }
        public object? onMessageReceive { get; set; }
        public object? connection_status_changed { get; set; }
        public object? streamer_connection_changed { get; set; }
        public object? bot_connection_changed { get; set; }
        public object? message_received { get; set; }
        public object? disconnectPlatfor { get; set; }
        public object? connectPlatfor { get; set; }
        public object? message_deleted { get; set; }


        // Original: def __init__(self, config=None)
        public ChatManager(object? config = null) {
            // TODO: implement constructor
            this.config = null;
            this.ngrok_manager = null;
            this.disabled_platforms = null;
            this.connectors = null;
            this.bot_connectors = null;
            this._recent_incoming = null;
            this._recent_message_ids = null;
            this._recent_canonical = null;
            this.onMessageReceivedWithMetadat = null;
            this.onMessageReceive = null;
            this.connection_status_changed = null;
            this.streamer_connection_changed = null;
            this.bot_connection_changed = null;
            this.message_received = null;
            this.disconnectPlatfor = null;
            this.connectPlatfor = null;
            this.message_deleted = null;
        }

        // Original: def _onConnectorMessageWithMetadata(self, platform, username, message, metadata)
        public void OnConnectorMessageWithMetadata(object? platform, object? username, object? message, object? metadata) {
            // TODO: implement
        }

        // Original: def _onConnectorMessageLegacy(self, platform, username, message, metadata)
        public void OnConnectorMessageLegacy(object? platform, object? username, object? message, object? metadata) {
            // TODO: implement
        }

        // Original: def connectPlatform(self, platform_id: str, username: str, token: str = "")
        public void ConnectPlatform(string? platform_id, string? username, string? token = null) {
            // TODO: implement
        }

        // Original: def disconnectPlatform(self, platform_id: str)
        public void DisconnectPlatform(string? platform_id) {
            // TODO: implement
        }

        // Original: def connectBotAccount(self, platform_id: str, username: str, token: str, refresh_token: str = None)
        public void ConnectBotAccount(string? platform_id, string? username, string? token, string? refresh_token = null) {
            // TODO: implement
        }

        // Original: def sendMessageAsBot(self, platform_id: str, message: str, allow_fallback: bool = True)
        public void SendMessageAsBot(string? platform_id, string? message, bool? allow_fallback = null) {
            // TODO: implement
        }

        // Original: def disablePlatform(self, platform_id: str, disabled: bool)
        public void DisablePlatform(string? platform_id, bool? disabled) {
            // TODO: implement
        }

        // Original: def onMessageReceived(self, platform_id: str, username: str, message: str)
        public void OnMessageReceived(string? platform_id, string? username, string? message) {
            // TODO: implement
        }

        // Original: def onMessageReceivedWithMetadata(self, platform_id: str, username: str, message: str, metadata: dict)
        public void OnMessageReceivedWithMetadata(string? platform_id, string? username, string? message, System.Collections.Generic.Dictionary<string,object>? metadata) {
            // TODO: implement
        }

        // Original: def onMessageDeleted(self, platform_id: str, message_id: str)
        public void OnMessageDeleted(string? platform_id, string? message_id) {
            // TODO: implement
        }

        // Original: def deleteMessage(self, platform_id: str, message_id: str)
        public void DeleteMessage(string? platform_id, string? message_id) {
            // TODO: implement
        }

        // Original: def banUser(self, platform_id: str, username: str, user_id: str = None)
        public void BanUser(string? platform_id, string? username, string? user_id = null) {
            // TODO: implement
        }

        // Original: def dump_connector_states(self)
        public void DumpConnectorStates() {
            // TODO: implement
        }

    }

}

