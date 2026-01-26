using System;
using System.Threading.Tasks;

namespace core.chat_manager {
    public static class Chat_managerModule {
        private static Delegate? _messageReceivedCallbackDel;
        private static Delegate? _messageReceivedWithMetadataCallbackDel;
        private static readonly object _cacheLock = new object();
        private static readonly System.Collections.Generic.List<System.Collections.Generic.Dictionary<string,object>> _recent_incoming = new System.Collections.Generic.List<System.Collections.Generic.Dictionary<string,object>>();
        private static readonly System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string,object>> _recent_message_ids = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string,object>>();
        // Original: def __init__(self, config=None)
        public static void Init(object? config = null) {
            // TODO: implement
        }

        // Original: def _onConnectorMessageWithMetadata(self, platform, username, message, metadata)
        public static void OnConnectorMessageWithMetadata(object? platform, object? username, object? message, object? metadata) {
            try {
                Console.WriteLine($"Chat_manager.OnConnectorMessageWithMetadata: platform={platform} username={username} message={message}");
                // Attempt to extract platform message id and cache recent messages for UI
                try {
                    var entry = new System.Collections.Generic.Dictionary<string, object>();
                    entry["platform"] = platform?.ToString() ?? string.Empty;
                    entry["username"] = username?.ToString() ?? string.Empty;
                    entry["message"] = message?.ToString() ?? string.Empty;
                    entry["timestamp"] = DateTime.UtcNow.ToString("o");
                    string? platformMsgId = null;
                    if (metadata is System.Collections.Generic.Dictionary<string, object> md) {
                        entry["metadata"] = md;
                        foreach (var key in new string[] { "message_id", "message-id", "id", "msg-id" }) {
                            if (md.ContainsKey(key) && md[key] != null) {
                                platformMsgId = md[key].ToString();
                                break;
                            }
                        }
                    } else if (metadata != null) {
                        entry["metadata"] = metadata;
                    }

                    lock (_cacheLock) {
                        _recent_incoming.Add(entry);
                        if (_recent_incoming.Count > 200) _recent_incoming.RemoveAt(0);
                        if (!string.IsNullOrEmpty(platformMsgId)) {
                            var mapKey = ($"{platform?.ToString() ?? string.Empty}:{platformMsgId}").ToLowerInvariant();
                            _recent_message_ids[mapKey] = entry;
                        }
                    }

                } catch (Exception) { }

                if (_messageReceivedWithMetadataCallbackDel != null) {
                    try { _messageReceivedWithMetadataCallbackDel.DynamicInvoke(platform, username, message, metadata); } catch { }
                }
            } catch (Exception ex) {
                Console.WriteLine($"Chat_manager.OnConnectorMessageWithMetadata error: {ex.Message}");
            }
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
            try {
                if (string.IsNullOrEmpty(platform_id) || string.IsNullOrEmpty(message)) return;
                // Route to platform-specific send implementations. Prefer specialized send helpers where available.
                if (string.Equals(platform_id, core.platforms.PlatformIds.Twitch, StringComparison.OrdinalIgnoreCase)) {
                    try { platform_connectors.twitch_connector.Twitch_connectorModule.SendChatMessageAsync(platform_id, message).GetAwaiter().GetResult(); } catch (Exception ex) { Console.WriteLine($"Chat_manager.SendMessageAsBot(Twitch) error: {ex.Message}"); }
                } else if (string.Equals(platform_id, core.platforms.PlatformIds.DLive, StringComparison.OrdinalIgnoreCase)) {
                    platform_connectors.dlive_connector.Dlive_connectorModule.SendMessage(message);
                } else if (string.Equals(platform_id, core.platforms.PlatformIds.YouTube, StringComparison.OrdinalIgnoreCase)) {
                    platform_connectors.youtube_connector.Youtube_connectorModule.SendMessage(message);
                } else if (string.Equals(platform_id, core.platforms.PlatformIds.Trovo, StringComparison.OrdinalIgnoreCase)) {
                    platform_connectors.trovo_connector.Trovo_connectorModule.SendMessage(message);
                } else if (string.Equals(platform_id, core.platforms.PlatformIds.Kick, StringComparison.OrdinalIgnoreCase)) {
                    platform_connectors.kick_connector.Kick_connectorModule.SendMessage(message);
                } else if (string.Equals(platform_id, core.platforms.PlatformIds.Twitter, StringComparison.OrdinalIgnoreCase)) {
                    platform_connectors.twitter_connector.Twitter_connectorModule.SendMessage(message);
                } else {
                    // Fallback to base connector
                    platform_connectors.base_connector.Base_connectorModule.SendMessage(message);
                }
            } catch (Exception ex) {
                Console.WriteLine($"Chat_manager.SendMessageAsBot error: {ex.Message}");
            }
        }

        // Original: def disablePlatform(self, platform_id: str, disabled: bool)
        public static void DisablePlatform(string? platform_id, bool? disabled) {
            // TODO: implement
        }

        // Original: def onMessageReceived(self, platform_id: str, username: str, message: str)
        public static void OnMessageReceived(string? platform_id, string? username, string? message) {
            try {
                Console.WriteLine($"Chat_manager.OnMessageReceived: platform={platform_id} username={username} message={message}");
                if (_messageReceivedCallbackDel != null) {
                    try { _messageReceivedCallbackDel.DynamicInvoke(platform_id, username, message); } catch { }
                }
            } catch (Exception ex) {
                Console.WriteLine($"Chat_manager.OnMessageReceived error: {ex.Message}");
            }
        }

        // Original: def onMessageReceivedWithMetadata(self, platform_id: str, username: str, message: str, metadata: dict)
        public static void OnMessageReceivedWithMetadata(string? platform_id, string? username, string? message, System.Collections.Generic.Dictionary<string,object>? metadata) {
            try {
                Console.WriteLine($"Chat_manager.OnMessageReceivedWithMetadata: platform={platform_id} username={username} message={message}");
                try {
                    var entry = new System.Collections.Generic.Dictionary<string, object>();
                    entry["platform"] = platform_id ?? string.Empty;
                    entry["username"] = username ?? string.Empty;
                    entry["message"] = message ?? string.Empty;
                    entry["timestamp"] = DateTime.UtcNow.ToString("o");
                    string? platformMsgId = null;
                    if (metadata != null) {
                        entry["metadata"] = metadata;
                        foreach (var key in new string[] { "message_id", "message-id", "id", "msg-id" }) {
                            if (metadata.ContainsKey(key) && metadata[key] != null) {
                                platformMsgId = metadata[key].ToString();
                                break;
                            }
                        }
                    }
                    lock (_cacheLock) {
                        _recent_incoming.Add(entry);
                        if (_recent_incoming.Count > 200) _recent_incoming.RemoveAt(0);
                        if (!string.IsNullOrEmpty(platformMsgId)) {
                            var mapKey = ($"{platform_id}:{platformMsgId}").ToLowerInvariant();
                            _recent_message_ids[mapKey] = entry;
                        }
                    }
                } catch (Exception) { }

                if (_messageReceivedWithMetadataCallbackDel != null) {
                    try { _messageReceivedWithMetadataCallbackDel.DynamicInvoke(platform_id, username, message, metadata); } catch { }
                }
            } catch (Exception ex) {
                Console.WriteLine($"Chat_manager.OnMessageReceivedWithMetadata error: {ex.Message}");
            }
        }

        // Read accessor: returns up to `maxItems` most recent messages (thread-safe shallow copies).
        public static System.Collections.Generic.List<System.Collections.Generic.Dictionary<string, object>> GetRecentIncoming(int maxItems = 50)
        {
            lock (_cacheLock)
            {
                var take = Math.Min(maxItems, _recent_incoming.Count);
                var result = new System.Collections.Generic.List<System.Collections.Generic.Dictionary<string, object>>(take);
                for (int i = _recent_incoming.Count - take; i < _recent_incoming.Count; i++)
                {
                    if (i < 0) continue;
                    result.Add(new System.Collections.Generic.Dictionary<string, object>(_recent_incoming[i]));
                }
                return result;
            }
        }

        // Read accessor: lookup a cached message by platform and platformMessageId
        public static System.Collections.Generic.Dictionary<string, object>? GetRecentMessageByPlatformId(string platform, string platformMessageId)
        {
            if (string.IsNullOrEmpty(platform) || string.IsNullOrEmpty(platformMessageId)) return null;
            var key = ($"{platform}:{platformMessageId}").ToLowerInvariant();
            lock (_cacheLock)
            {
                if (_recent_message_ids.TryGetValue(key, out var entry))
                {
                    return new System.Collections.Generic.Dictionary<string, object>(entry);
                }
                return null;
            }
        }

        // Register UI callbacks
        public static void SetMessageReceivedCallback(object? callback) {
            if (callback is Delegate d) _messageReceivedCallbackDel = d; else _messageReceivedCallbackDel = null;
        }

        public static void SetMessageReceivedWithMetadataCallback(object? callback) {
            if (callback is Delegate d) _messageReceivedWithMetadataCallbackDel = d; else _messageReceivedWithMetadataCallbackDel = null;
        }

        // Original: def onMessageDeleted(self, platform_id: str, message_id: str)
        public static void OnMessageDeleted(string? platform_id, string? message_id) {
            // TODO: implement
        }

        // Original: def deleteMessage(self, platform_id: str, message_id: str)
        public static void DeleteMessage(string? platform_id, string? message_id) {
            try {
                if (string.IsNullOrEmpty(platform_id) || string.IsNullOrEmpty(message_id)) return;
                var p = platform_id?.ToLowerInvariant();
                if (p == "twitch") {
                    platform_connectors.twitch_connector.Twitch_connectorModule.DeleteMessage(message_id);
                } else if (p == "trovo") {
                    platform_connectors.trovo_connector.Trovo_connectorModule.DeleteMessage(message_id);
                } else if (p == "dlive") {
                    platform_connectors.dlive_connector.Dlive_connectorModule.DeleteMessage(message_id);
                } else {
                    Console.WriteLine($"DeleteMessage: platform {platform_id} not handled");
                }
            } catch (Exception ex) {
                Console.WriteLine($"Chat_manager.DeleteMessage error: {ex.Message}");
            }
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
            try {
                var entry = new System.Collections.Generic.Dictionary<string, object>();
                entry["platform"] = platform?.ToString() ?? string.Empty;
                entry["username"] = username?.ToString() ?? string.Empty;
                entry["message"] = message?.ToString() ?? string.Empty;
                entry["timestamp"] = DateTime.UtcNow.ToString("o");
                if (metadata != null) entry["metadata"] = metadata!;
                // Push into instance recent list if present
                try {
                    if (this._recent_incoming == null) this._recent_incoming = new System.Collections.Generic.List<object>();
                    this._recent_incoming.Add(entry as object);
                    if (this._recent_incoming.Count > 200) this._recent_incoming.RemoveAt(0);
                } catch { }
                // Invoke instance callback if wired
                try { if (this.onMessageReceivedWithMetadat is Delegate d) d.DynamicInvoke(platform, username, message, metadata); } catch { }
            } catch (Exception ex) {
                Console.WriteLine($"ChatManager.OnConnectorMessageWithMetadata error: {ex.Message}");
            }
        }

        // Instance-level read accessor: returns up to `maxItems` most recent messages for this ChatManager
        public System.Collections.Generic.List<System.Collections.Generic.Dictionary<string, object>> GetRecentIncoming(int maxItems = 50)
        {
            var result = new System.Collections.Generic.List<System.Collections.Generic.Dictionary<string, object>>();
            try {
                if (this._recent_incoming == null) return result;
                var total = this._recent_incoming.Count;
                var take = Math.Min(maxItems, total);
                for (int i = total - take; i < total; i++) {
                    if (i < 0) continue;
                    var obj = this._recent_incoming[i];
                    if (obj is System.Collections.Generic.Dictionary<string, object> dict) {
                        result.Add(new System.Collections.Generic.Dictionary<string, object>(dict));
                    } else if (obj is System.Collections.Generic.Dictionary<string,object> boxedDict) {
                        result.Add(new System.Collections.Generic.Dictionary<string, object>(boxedDict));
                    }
                }
            } catch { }
            return result;
        }

        // Instance-level lookup by platform+message id
        public System.Collections.Generic.Dictionary<string, object>? GetRecentMessageByPlatformId(string platform, string platformMessageId)
        {
            if (string.IsNullOrEmpty(platform) || string.IsNullOrEmpty(platformMessageId)) return null;
            try {
                if (this._recent_message_ids == null) return null;
                var key = ($"{platform}:{platformMessageId}").ToLowerInvariant();
                if (this._recent_message_ids.TryGetValue(key, out var boxed)) {
                    if (boxed is System.Collections.Generic.Dictionary<string, object> entry) {
                        return new System.Collections.Generic.Dictionary<string, object>(entry);
                    }
                }
            } catch { }
            return null;
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
            try {
                var entry = new System.Collections.Generic.Dictionary<string, object>();
                entry["platform"] = platform_id ?? string.Empty;
                entry["username"] = username ?? string.Empty;
                entry["message"] = message ?? string.Empty;
                entry["timestamp"] = DateTime.UtcNow.ToString("o");
                if (metadata != null) entry["metadata"] = metadata;
                try {
                    if (this._recent_incoming == null) this._recent_incoming = new System.Collections.Generic.List<object>();
                    this._recent_incoming.Add(entry as object);
                    if (this._recent_incoming.Count > 200) this._recent_incoming.RemoveAt(0);
                } catch { }
                try { if (this.onMessageReceivedWithMetadat is Delegate d) d.DynamicInvoke(platform_id, username, message, metadata); } catch { }
            } catch (Exception ex) {
                Console.WriteLine($"ChatManager.OnMessageReceivedWithMetadata error: {ex.Message}");
            }
        }

        // Original: def onMessageDeleted(self, platform_id: str, message_id: str)
        public void OnMessageDeleted(string? platform_id, string? message_id) {
            // TODO: implement
        }

        // Original: def deleteMessage(self, platform_id: str, message_id: str)
        public void DeleteMessage(string? platform_id, string? message_id) {
            try {
                Chat_managerModule.DeleteMessage(platform_id, message_id);
            } catch (Exception ex) {
                Console.WriteLine($"ChatManager.DeleteMessage error: {ex.Message}");
            }
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

