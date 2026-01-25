using System;
using System.Threading.Tasks;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Net.WebSockets;
using System.Threading;
using System.Collections.Generic;

namespace platform_connectors.twitch_connector {
    public static class Twitch_connectorModule {
        private static string? _eventSubSessionId;
        private static async Task<HttpResponseMessage> GetWithRetriesAsync(HttpClient http, string url, int maxAttempts = 3) {
            return await core.http_retry.HttpRetry.GetWithRetriesAsync(http, url, maxAttempts).ConfigureAwait(false);
        }

        private static async Task<HttpResponseMessage> PostWithRetriesAsync(HttpClient http, string url, HttpContent content, int maxAttempts = 3) {
            return await core.http_retry.HttpRetry.PostWithRetriesAsync(http, url, content, maxAttempts).ConfigureAwait(false);
        }
        // Original: def _make_retry_session(total: int = 3, backoff_factor: float = 1.0)
        public static void MakeRetrySession(int? total = null, double? backoff_factor = null) {
            // TODO: implement
        }

        // Original: def __new__(cls, config=None, is_bot_account=False)
        public static void New(object? config = null, bool? is_bot_account = null) {
            // TODO: implement
        }

        // Original: def __init__(self, config=None, is_bot_account=False)
        public static void Init(object? config = null, bool? is_bot_account = null) {
            // TODO: implement
        }

        // Original: def set_token(self, token: str)
        public static void SetToken(string? token) {
            try {
                var platform = core.platforms.PlatformIds.Twitch;
                core.config.ConfigModule.SetPlatformConfig(platform, "oauth_token", token ?? string.Empty);
                var epoch = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                core.config.ConfigModule.SetPlatformConfig(platform, "bot_token_timestamp", epoch);
                Console.WriteLine($"Twitch_connectorModule.SetToken: token length={(token?.Length ?? 0)}");
            } catch (Exception ex) {
                Console.WriteLine($"SetToken error: {ex.Message}");
            }
        }

        // Original: def set_username(self, username: str)
        public static void SetUsername(string? username) {
            try {
                var platform = core.platforms.PlatformIds.Twitch;
                core.config.ConfigModule.SetPlatformConfig(platform, "bot_username", username ?? string.Empty);
                Console.WriteLine($"Twitch_connectorModule.SetUsername: {username}");
            } catch (Exception ex) {
                Console.WriteLine($"SetUsername error: {ex.Message}");
            }
        }

        // Original: def set_bot_username(self, bot_username: str)
        public static void SetBotUsername(string? bot_username) {
            // TODO: implement
        }

        // Original: def connect(self, username: str)
        public static void Connect(string? username) {
            try {
                var platform = core.platforms.PlatformIds.Twitch;
                ConnectToPlatform(platform).GetAwaiter().GetResult();
                Console.WriteLine($"Twitch_connectorModule.Connect invoked for username={username}");
            } catch (Exception ex) {
                Console.WriteLine($"Connect error: {ex.Message}");
            }
        }

        // Original: def refresh_access_token(self)
        public static void RefreshAccessToken() {
            // TODO: implement
        }

        // Original: def _on_eventsub_reauth_requested(self, oauth_url: str)
        public static void OnEventsubReauthRequested(string? oauth_url) {
            // TODO: implement
        }

        // Original: def disconnect(self)
        public static void Disconnect() {
            // TODO: implement
        }

        // Original: def send_message(self, message: str)
        public static void SendMessage(string? message) {
            try {
                var platform = core.platforms.PlatformIds.Twitch;
                if (string.IsNullOrEmpty(message)) return;
                _ = SendChatMessageAsync(platform, message).GetAwaiter().GetResult();
            } catch (Exception ex) {
                Console.WriteLine($"Twitch_connectorModule.SendMessage error: {ex.Message}");
            }
        }

        // Send a chat message using Twitch Helix Chat Messages API (best-effort)
        public static async Task<bool> SendChatMessageAsync(string platform, string message, HttpClient? httpClient = null) {
            try {
                var platformCfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? cfg, string k) {
                    if (cfg == null) return string.Empty;
                    if (cfg.ContainsKey(k)) return cfg[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }

                var oauth = GetStr(platformCfg, "oauth_token");
                var clientId = GetStr(platformCfg, "client_id");
                // Try to find broadcaster id or username. Prefer canonical user id lookup.
                var broadcasterId = core.config.ConfigModule.GetPlatformUserId(platform, "streamer", "");
                if (string.IsNullOrEmpty(broadcasterId)) broadcasterId = GetStr(platformCfg, "broadcaster_id");
                var broadcasterLogin = GetStr(platformCfg, "bot_username");

                if (string.IsNullOrEmpty(oauth) || string.IsNullOrEmpty(clientId)) {
                    Console.WriteLine("SendChatMessageAsync: missing oauth_token or client_id");
                    return false;
                }

                if (string.IsNullOrEmpty(broadcasterId) && !string.IsNullOrEmpty(broadcasterLogin)) {
                    // Resolve login -> id
                    broadcasterId = await ResolveUserIdAsync(clientId, oauth, broadcasterLogin).ConfigureAwait(false);
                    if (!string.IsNullOrEmpty(broadcasterId)) {
                        try {
                            core.config.ConfigModule.SetPlatformConfig(platform, "broadcaster_id", broadcasterId);
                            // Also persist canonical streamer_user_id for future lookups
                            try { core.config.ConfigModule.SetPlatformConfig(platform, "streamer_user_id", broadcasterId); } catch { }
                        } catch (Exception ex) {
                            Console.WriteLine($"Failed to persist broadcaster_id: {ex.Message}");
                        }
                    }
                }

                if (string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine("SendChatMessageAsync: broadcaster id unknown");
                    return false;
                }

                var disposeClient = false;
                var http = httpClient ?? core.http_client.HttpClientFactory.GetClient(forceNew: true);
                if (httpClient == null) disposeClient = true;
                http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauth);
                http.DefaultRequestHeaders.Add("Client-Id", clientId);

                var url = $"https://api.twitch.tv/helix/chat/messages?broadcaster_id={Uri.EscapeDataString(broadcasterId)}";
                var payload = new { message = message };
                var body = JsonSerializer.Serialize(payload);
                using var content = new StringContent(body, Encoding.UTF8, "application/json");
                var resp = await PostWithRetriesAsync(http, url, content).ConfigureAwait(false);
                var respText = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode) {
                    Console.WriteLine($"SendChatMessageAsync failed: {resp.StatusCode} {respText}");
                    if (disposeClient) http.Dispose();
                    return false;
                }
                if (disposeClient) http.Dispose();
                return true;
            } catch (Exception ex) {
                Console.WriteLine($"SendChatMessageAsync exception: {ex.Message}");
                return false;
            }
        }

        public static async Task<string?> ResolveUserIdAsync(string clientId, string oauth, string login, HttpClient? httpClient = null) {
            try {
                var disposeClient = false;
                var http = httpClient ?? core.http_client.HttpClientFactory.GetClient(forceNew: true);
                if (httpClient == null) disposeClient = true;
                http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauth);
                http.DefaultRequestHeaders.Add("Client-Id", clientId);
                var url = $"https://api.twitch.tv/helix/users?login={Uri.EscapeDataString(login)}";
                var resp = await GetWithRetriesAsync(http, url).ConfigureAwait(false);
                var txt = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode) {
                    Console.WriteLine($"ResolveUserIdAsync failed: {resp.StatusCode} {txt}");
                    if (disposeClient) http.Dispose();
                    return null;
                }
                using var doc = JsonDocument.Parse(txt);
                var root = doc.RootElement;
                if (root.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Array && data.GetArrayLength() > 0) {
                    var first = data[0];
                    if (first.TryGetProperty("id", out var id)) return id.GetString();
                }
                if (disposeClient) http.Dispose();
                return null;
            } catch (Exception ex) {
                Console.WriteLine($"ResolveUserIdAsync exception: {ex.Message}");
                return null;
            }
        }

        // Original: def delete_message(self, message_id: str)
        public static void DeleteMessage(string? message_id) {
            // TODO: implement
        }

        // Original: def get_custom_reward(self, reward_id: str)
        public static void GetCustomReward(string? reward_id) {
            // TODO: implement
        }

        // Original: def ban_user(self, username: str, user_id: Optional[str] = None)
        public static void BanUser(string? username, object? user_id = null) {
            // TODO: implement
        }

        // Original: def onMessageReceived(self, username: str, message: str)
        public static void OnMessageReceived(string? username, string? message) {
            // TODO: implement
        }

        // Original: def onMessageReceivedWithMetadata(self, username: str, message: str, metadata: dict)
        public static void OnMessageReceivedWithMetadata(string? username, string? message, System.Collections.Generic.Dictionary<string,object>? metadata) {
            // TODO: implement
        }

        // Original: def onMessageDeleted(self, message_id: str)
        public static void OnMessageDeleted(string? message_id) {
            // TODO: implement
        }

        // Original: def onRedemption(self, username: str, reward_title: str, reward_cost: int, user_input: str)
        public static void OnRedemption(string? username, string? reward_title, int? reward_cost, string? user_input) {
            // TODO: implement
        }

        // Original: def onEvent(self, event_type: str, username: str, event_data: dict)
        public static void OnEvent(string? event_type, string? username, System.Collections.Generic.Dictionary<string,object>? event_data) {
            // TODO: implement
        }

        // Original: def onEventSubStatus(self, connected: bool)
        public static void OnEventSubStatus(bool? connected) {
            // TODO: implement
        }

        // Original: def onStatusChanged(self, connected: bool)
        public static void OnStatusChanged(bool? connected) {
            // TODO: implement
        }

        // Original: def onError(self, error: str)
        public static void OnError(string? error) {
            // TODO: implement
        }

        // Original: def set_metadata_callback(self, callback)
        public static void SetMetadataCallback(object? callback) {
            // TODO: implement
        }

        // Original: def set_deletion_callback(self, callback)
        public static void SetDeletionCallback(object? callback) {
            // TODO: implement
        }

        // Original: def run(self)
        public static void Run() {
            // TODO: implement
        }

        // Original: def connect_to_twitch(self)
        public static async Task ConnectToTwitch() {
            // legacy wrapper for compatibility
            var platform = core.platforms.PlatformIds.Twitch;
            await ConnectToPlatform(platform).ConfigureAwait(false);
        }

        // Generic connector that accepts platform id (e.g., "twitch")
        public static async Task ConnectToPlatform(string platform) {
            // Attempt to ensure we have a valid OAuth token before connecting.
            try {
                var token = await core.connector_utils.ConnectorUtils.EnsureAccessTokenAsync(platform).ConfigureAwait(false);
                if (string.IsNullOrEmpty(token)) {
                    Console.WriteLine($"ConnectToPlatform({platform}): no token available after interactive authenticate");
                } else {
                    Console.WriteLine($"ConnectToPlatform({platform}): obtained token length={token.Length}");
                }
            } catch (Exception ex) {
                Console.WriteLine($"ConnectToPlatform({platform}) exception: {ex.Message}");
            }
            await Task.Yield();
            return;
        }

        // Original: def refresh_token_if_needed(self)
        public static async Task RefreshTokenIfNeeded() {
            var platform = core.platforms.PlatformIds.Twitch;
            await RefreshTokenIfNeededForPlatform(platform).ConfigureAwait(false);
        }

        public static async Task RefreshTokenIfNeededForPlatform(string platform) {
            try {
                var handler = new core.oauth_handler.OAuthHandler();
                var token = await handler.GetAccessTokenAsync(platform).ConfigureAwait(false);
                if (!string.IsNullOrEmpty(token)) {
                    Console.WriteLine($"RefreshTokenIfNeededForPlatform({platform}): token is available/updated");
                } else {
                    Console.WriteLine($"RefreshTokenIfNeededForPlatform({platform}): no token available after refresh attempt");
                }
            } catch (Exception ex) {
                Console.WriteLine($"RefreshTokenIfNeededForPlatform({platform}) exception: {ex.Message}");
            }
            await Task.Yield();
            return;
        }

        // Original: def health_check_loop(self, websocket)
        public static async Task HealthCheckLoop(object? websocket) {
            // noop: keep-alive handled by websocket server; provide delay loop
            try {
                while (true) {
                    await Task.Delay(TimeSpan.FromSeconds(30)).ConfigureAwait(false);
                }
            } catch (TaskCanceledException) {
            }
            return;
        }

        // Original: def authenticate(self)
        public static async Task Authenticate() {
            var platform = core.platforms.PlatformIds.Twitch;
            await AuthenticatePlatform(platform).ConfigureAwait(false);
        }

        public static async Task AuthenticatePlatform(string platform) {
            try {
                var handler = new core.oauth_handler.OAuthHandler();
                handler.Authenticate(platform);
            } catch (Exception ex) {
                Console.WriteLine($"AuthenticatePlatform({platform}) exception: {ex.Message}");
            }
            await Task.Yield();
            return;
        }

        // Original: def handle_message(self, raw_message: str)
        public static async Task HandleMessage(string? raw_message) {
            if (string.IsNullOrEmpty(raw_message)) return;
            try {
                using var doc = JsonDocument.Parse(raw_message);
                var root = doc.RootElement;
                if (root.TryGetProperty("metadata", out var metadata)) {
                    var msgType = metadata.GetProperty("message_type").GetString();
                    if (string.Equals(msgType, "session_welcome", StringComparison.OrdinalIgnoreCase)) {
                        // session welcome
                        if (root.TryGetProperty("payload", out var payload) && payload.TryGetProperty("session", out var session)) {
                            if (session.TryGetProperty("id", out var sid)) {
                                var sidstr = sid.GetString();
                                Console.WriteLine($"EventSub session welcome: {sidstr}");
                                _eventSubSessionId = sidstr;
                                // notify status
                                OnEventSubStatus(true);
                                // attempt to subscribe to default topics (redemptions + common events)
                                _ = SubscribeToRedemptions().ConfigureAwait(false);
                                _ = SubscribeToCommonEvents().ConfigureAwait(false);
                            }
                        }
                    } else if (string.Equals(msgType, "notification", StringComparison.OrdinalIgnoreCase)) {
                        if (root.TryGetProperty("payload", out var payload) && payload.TryGetProperty("subscription", out var sub)) {
                            var eventType = sub.GetProperty("type").GetString() ?? string.Empty;
                            // extract event object
                            if (payload.TryGetProperty("event", out var ev)) {
                                // try to extract username for common fields
                                string? username = null;
                                if (ev.TryGetProperty("user_login", out var ul) && ul.ValueKind == JsonValueKind.String) username = ul.GetString();
                                else if (ev.TryGetProperty("broadcaster_user_login", out var bl) && bl.ValueKind == JsonValueKind.String) username = bl.GetString();
                                else if (ev.TryGetProperty("user_name", out var un) && un.ValueKind == JsonValueKind.String) username = un.GetString();

                                var eventData = new Dictionary<string, object>();
                                foreach (var p in ev.EnumerateObject()) {
                                    try { eventData[p.Name] = p.Value.GetRawText(); } catch { eventData[p.Name] = p.Value.ToString(); }
                                }

                                // dispatch common events
                                OnEvent(eventType, username, eventData);

                                // channel points redemption event type contains "redemption"
                                if (eventType != null && eventType.Contains("redemption")) {
                                    // try to pull reward title and cost
                                    string? rewardTitle = null;
                                    int rewardCost = 0;
                                    if (ev.TryGetProperty("reward", out var reward) && reward.ValueKind == JsonValueKind.Object) {
                                        if (reward.TryGetProperty("title", out var rt)) rewardTitle = rt.GetString();
                                        if (reward.TryGetProperty("cost", out var rc) && rc.TryGetInt32(out var rcv)) rewardCost = rcv;
                                    }
                                    var userInput = ev.TryGetProperty("user_input", out var ui) ? ui.GetString() : null;
                                    OnRedemption(username, rewardTitle, rewardCost, userInput);
                                }
                            }
                        }
                    } else if (string.Equals(msgType, "session_keepalive", StringComparison.OrdinalIgnoreCase)) {
                        // keepalive, ignore
                    } else {
                        Console.WriteLine($"Unhandled EventSub message_type={msgType}");
                    }
                }
            } catch (Exception ex) {
                Console.WriteLine($"HandleMessage parse error: {ex.Message}");
            }
            await Task.Yield();
            return;
        }

        // Start an EventSub websocket connection and process incoming messages
        public static async Task StartEventSubWebsocketAsync(string platform) {
            try {
                var cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? c, string k) {
                    if (c == null) return string.Empty;
                    if (c.ContainsKey(k)) return c[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }
                var oauth = GetStr(cfg, "oauth_token");
                var clientId = GetStr(cfg, "client_id");

                using var ws = new ClientWebSocket();
                var uri = new Uri("wss://eventsub.wss.twitch.tv/ws");
                try {
                    await ws.ConnectAsync(uri, CancellationToken.None).ConfigureAwait(false);
                } catch (Exception ex) {
                    Console.WriteLine($"EventSub websocket connect failed: {ex.Message}");
                    OnEventSubStatus(false);
                    return;
                }

                OnEventSubStatus(true);

                var buffer = new ArraySegment<byte>(new byte[16 * 1024]);
                var sb = new StringBuilder();
                while (ws.State == WebSocketState.Open) {
                    sb.Clear();
                    WebSocketReceiveResult? result = null;
                    do {
                        result = await ws.ReceiveAsync(buffer, CancellationToken.None).ConfigureAwait(false);
                        if (result.MessageType == WebSocketMessageType.Close) {
                            await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "closing", CancellationToken.None).ConfigureAwait(false);
                            OnEventSubStatus(false);
                            return;
                        }
                        var chunk = Encoding.UTF8.GetString(buffer.Array ?? Array.Empty<byte>(), 0, result.Count);
                        sb.Append(chunk);
                    } while (!result.EndOfMessage);

                    var msg = sb.ToString();
                    try {
                        await HandleMessage(msg).ConfigureAwait(false);
                    } catch (Exception ex) {
                        Console.WriteLine($"Error handling EventSub message: {ex.Message}");
                    }
                }
            } catch (Exception ex) {
                Console.WriteLine($"StartEventSubWebsocketAsync exception: {ex.Message}");
                OnEventSubStatus(false);
            }
        }

        // Original: def parse_clearmsg(self, raw_message: str)
        public static void ParseClearmsg(string? raw_message) {
            // TODO: implement
        }

        // Original: def parse_usernotice(self, raw_message: str)
        public static void ParseUsernotice(string? raw_message) {
            // TODO: implement
        }

        // Original: def parse_privmsg(self, raw_message: str)
        public static void ParsePrivmsg(string? raw_message) {
            // TODO: implement
        }

        // Original: def stop(self)
        public static void Stop() {
            // TODO: implement
        }

        // Original: def send_message_async(self, message: str)
        public static async Task SendMessageAsync(string? message) {
            // TODO: implement
            await Task.Yield();
            return;
        }

        // Original: def __init__(self, oauth_token: str, client_id: str, broadcaster_login: str)
        public static void Init(string? oauth_token, string? client_id, string? broadcaster_login) {
            // TODO: implement
        }

        // Original: def validate_token(self)
        public static async Task ValidateToken() {
            var platform = core.platforms.PlatformIds.Twitch;
            try {
                var cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? c, string k) {
                    if (c == null) return string.Empty;
                    if (c.ContainsKey(k)) return c[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }
                var oauth = GetStr(cfg, "oauth_token");
                if (string.IsNullOrEmpty(oauth)) {
                    Console.WriteLine("ValidateToken: no oauth_token configured");
                    return;
                }

                using var http = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauth);
                var url = "https://id.twitch.tv/oauth2/validate";
                var resp = await http.GetAsync(url).ConfigureAwait(false);
                var txt = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode) {
                    Console.WriteLine($"ValidateToken failed: {resp.StatusCode} {txt}");
                    return;
                }
                try {
                    using var doc = JsonDocument.Parse(txt);
                    var root = doc.RootElement;
                    if (root.TryGetProperty("client_id", out var cid)) {
                        core.config.ConfigModule.SetPlatformConfig(platform, "client_id", cid.GetString() ?? string.Empty);
                    }
                    if (root.TryGetProperty("login", out var login)) {
                        core.config.ConfigModule.SetPlatformConfig(platform, "bot_username", login.GetString() ?? string.Empty);
                    }
                    if (root.TryGetProperty("user_id", out var uid)) {
                        core.config.ConfigModule.SetPlatformConfig(platform, "broadcaster_id", uid.GetString() ?? string.Empty);
                    }
                    if (root.TryGetProperty("expires_in", out var exp)) {
                        Console.WriteLine($"ValidateToken: expires_in={exp.GetInt32()}");
                    }
                } catch (Exception ex) {
                    Console.WriteLine($"ValidateToken parse exception: {ex.Message}");
                }
            } catch (Exception ex) {
                Console.WriteLine($"ValidateToken exception: {ex.Message}");
            }
            return;
        }

        // Original: def connect_and_listen(self)
        public static async Task ConnectAndListen() {
            // Start EventSub websocket listener for Twitch
            var platform = core.platforms.PlatformIds.Twitch;
            _ = StartEventSubWebsocketAsync(platform);
            await Task.Yield();
            return;
        }

        // Original: def get_broadcaster_id(self)
        public static async Task GetBroadcasterId() {
            var platform = core.platforms.PlatformIds.Twitch;
            try {
                var cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? c, string k) {
                    if (c == null) return string.Empty;
                    if (c.ContainsKey(k)) return c[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }
                // Prefer canonical id lookup first
                var broadcasterId = core.config.ConfigModule.GetPlatformUserId(platform, "streamer", "");
                if (!string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine($"GetBroadcasterId: canonical id already known {broadcasterId}");
                    return;
                }
                broadcasterId = GetStr(cfg, "broadcaster_id");
                if (!string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine($"GetBroadcasterId: already known {broadcasterId}");
                    return;
                }

                // Try validate token which may populate login/user_id
                await ValidateToken().ConfigureAwait(false);

                cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                // check canonical id again after validate
                broadcasterId = core.config.ConfigModule.GetPlatformUserId(platform, "streamer", "");
                if (!string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine($"GetBroadcasterId: found canonical after validate {broadcasterId}");
                    return;
                }
                broadcasterId = GetStr(cfg, "broadcaster_id");
                if (!string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine($"GetBroadcasterId: found after validate {broadcasterId}");
                    return;
                }

                var botLogin = GetStr(cfg, "bot_username");
                var clientId = GetStr(cfg, "client_id");
                var oauth = GetStr(cfg, "oauth_token");
                if (!string.IsNullOrEmpty(botLogin) && !string.IsNullOrEmpty(clientId) && !string.IsNullOrEmpty(oauth)) {
                    var id = await ResolveUserIdAsync(clientId, oauth, botLogin).ConfigureAwait(false);
                    if (!string.IsNullOrEmpty(id)) {
                        core.config.ConfigModule.SetPlatformConfig(platform, "broadcaster_id", id);
                        Console.WriteLine($"GetBroadcasterId: resolved and saved {id}");
                        return;
                    }
                }

                Console.WriteLine("GetBroadcasterId: unable to determine broadcaster id");
            } catch (Exception ex) {
                Console.WriteLine($"GetBroadcasterId exception: {ex.Message}");
            }
            return;
        }

        // Original: def subscribe_to_redemptions(self)
        public static async Task SubscribeToRedemptions() {
            var platform = core.platforms.PlatformIds.Twitch;
            try {
                // ensure we have a session id
                if (string.IsNullOrEmpty(_eventSubSessionId)) {
                    Console.WriteLine("SubscribeToRedemptions: no EventSub session id available");
                    return;
                }

                // ensure broadcaster id
                await GetBroadcasterId().ConfigureAwait(false);
                var cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? c, string k) {
                    if (c == null) return string.Empty;
                    if (c.ContainsKey(k)) return c[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }
                var oauth = GetStr(cfg, "oauth_token");
                var clientId = GetStr(cfg, "client_id");
                // Prefer canonical broadcaster id when available
                var broadcasterId = core.config.ConfigModule.GetPlatformUserId(platform, "streamer", "");
                if (string.IsNullOrEmpty(broadcasterId)) broadcasterId = GetStr(cfg, "broadcaster_id");

                if (string.IsNullOrEmpty(oauth) || string.IsNullOrEmpty(clientId) || string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine("SubscribeToRedemptions: missing oauth/clientId/broadcasterId");
                    return;
                }

                // create subscription if not already present
                await CreateEventSubSubscriptionIfNotExistsAsync("channel.channel_points_custom_reward_redemption.add", broadcasterId, oauth, clientId).ConfigureAwait(false);
            } catch (Exception ex) {
                Console.WriteLine($"SubscribeToRedemptions exception: {ex.Message}");
            }
            return;
        }

        // Subscribe to common event types (follow, subscribe, raid)
        public static async Task SubscribeToCommonEvents() {
            var platform = core.platforms.PlatformIds.Twitch;
            try {
                if (string.IsNullOrEmpty(_eventSubSessionId)) {
                    Console.WriteLine("SubscribeToCommonEvents: no EventSub session id available");
                    return;
                }

                await GetBroadcasterId().ConfigureAwait(false);
                var cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? c, string k) {
                    if (c == null) return string.Empty;
                    if (c.ContainsKey(k)) return c[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }
                var oauth = GetStr(cfg, "oauth_token");
                var clientId = GetStr(cfg, "client_id");
                // Prefer canonical broadcaster id when available
                var broadcasterId = core.config.ConfigModule.GetPlatformUserId(platform, "streamer", "");
                if (string.IsNullOrEmpty(broadcasterId)) broadcasterId = GetStr(cfg, "broadcaster_id");

                if (string.IsNullOrEmpty(oauth) || string.IsNullOrEmpty(clientId) || string.IsNullOrEmpty(broadcasterId)) {
                    Console.WriteLine("SubscribeToCommonEvents: missing oauth/clientId/broadcasterId");
                    return;
                }

                var types = new string[] { "channel.follow", "channel.subscribe", "channel.raid" };
                var http = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauth);
                http.DefaultRequestHeaders.Remove("Client-Id");
                http.DefaultRequestHeaders.Add("Client-Id", clientId);

                foreach (var t in types) {
                    await CreateEventSubSubscriptionIfNotExistsAsync(t, broadcasterId, oauth, clientId).ConfigureAwait(false);
                }

                http.Dispose();
            } catch (Exception ex) {
                Console.WriteLine($"SubscribeToCommonEvents exception: {ex.Message}");
            }
            return;
        }

        // Create a subscription only if a matching subscription (type + condition) does not already exist
        private static async Task CreateEventSubSubscriptionIfNotExistsAsync(string type, string broadcasterId, string oauth, string clientId) {
            try {
                // Fetch existing subscriptions
                var listUrl = "https://api.twitch.tv/helix/eventsub/subscriptions";
                var httpList = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                httpList.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauth);
                httpList.DefaultRequestHeaders.Remove("Client-Id");
                httpList.DefaultRequestHeaders.Add("Client-Id", clientId);

                var resp = await GetWithRetriesAsync(httpList, listUrl).ConfigureAwait(false);
                var txt = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode) {
                    Console.WriteLine($"CreateEventSubSubscriptionIfNotExists: failed to list subscriptions: {resp.StatusCode} {txt}");
                    httpList.Dispose();
                    return;
                }

                bool needCreate = true;
                try {
                    using var doc = JsonDocument.Parse(txt);
                    var root = doc.RootElement;
                    if (root.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Array) {
                        foreach (var item in data.EnumerateArray()) {
                            var itype = item.GetProperty("type").GetString();
                            if (!string.Equals(itype, type, StringComparison.OrdinalIgnoreCase)) continue;
                            if (item.TryGetProperty("condition", out var cond) && cond.ValueKind == JsonValueKind.Object) {
                                if (cond.TryGetProperty("broadcaster_user_id", out var bid) && bid.GetString() == broadcasterId) {
                                    // matching subscription exists; check transport.session_id
                                    string? existingSessionId = null;
                                    if (item.TryGetProperty("transport", out var transport) && transport.ValueKind == JsonValueKind.Object) {
                                        if (transport.TryGetProperty("session_id", out var sid) && sid.ValueKind == JsonValueKind.String) existingSessionId = sid.GetString();
                                    }
                                    var subId = item.GetProperty("id").GetString();
                                    if (existingSessionId == _eventSubSessionId) {
                                        Console.WriteLine($"Subscription exists for type={type} broadcaster={broadcasterId} with same session, skipping creation");
                                        httpList.Dispose();
                                        return;
                                    } else {
                                        // session differs: attempt to delete existing subscription then create new
                                        if (!string.IsNullOrEmpty(subId)) {
                                            try {
                                                var deleteUrl = $"https://api.twitch.tv/helix/eventsub/subscriptions?id={Uri.EscapeDataString(subId)}";
                                                int attempt = 0;
                                                while (true) {
                                                    attempt++;
                                                    try {
                                                        var delResp = await httpList.SendAsync(new HttpRequestMessage(HttpMethod.Delete, deleteUrl)).ConfigureAwait(false);
                                                        var delTxt = await delResp.Content.ReadAsStringAsync().ConfigureAwait(false);
                                                        if (delResp.IsSuccessStatusCode || (int)delResp.StatusCode == 404) {
                                                            Console.WriteLine($"Deleted stale subscription {subId} (type={type})");
                                                            break;
                                                        }
                                                        if (((int)delResp.StatusCode == 429 || (int)delResp.StatusCode >= 500) && attempt < 3) {
                                                            if (delResp.Headers.TryGetValues("Retry-After", out var vals)) {
                                                                var ra = System.Linq.Enumerable.FirstOrDefault(vals);
                                                                if (!string.IsNullOrEmpty(ra) && int.TryParse(ra, out var secs)) {
                                                                    await Task.Delay(TimeSpan.FromSeconds(secs)).ConfigureAwait(false);
                                                                    continue;
                                                                }
                                                            }
                                                            var jitter = Random.Shared.NextDouble() * 0.5;
                                                            var delay = Math.Pow(2, attempt) + jitter;
                                                            await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                                                            continue;
                                                        }
                                                        Console.WriteLine($"Failed to delete stale subscription {subId}: {delResp.StatusCode} {delTxt}");
                                                        break;
                                                    } catch (Exception ex) {
                                                        if (attempt >= 3) { Console.WriteLine($"Error deleting subscription {subId}: {ex.Message}"); break; }
                                                        var jitter = Random.Shared.NextDouble() * 0.5;
                                                        var delay = Math.Pow(2, attempt) + jitter;
                                                        await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                                                    }
                                                }
                                            } catch (Exception ex) {
                                                Console.WriteLine($"Exception deleting subscription {subId}: {ex.Message}");
                                            }
                                        }
                                        // after deletion attempt, continue to create
                                        needCreate = true;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                } catch (Exception ex) {
                    Console.WriteLine($"CreateEventSubSubscriptionIfNotExists parse list error: {ex.Message}");
                }

                httpList.Dispose();
                if (!needCreate) return;

                // Not found -> create
                var url = "https://api.twitch.tv/helix/eventsub/subscriptions";
                var body = new {
                    type = type,
                    version = "1",
                    condition = new { broadcaster_user_id = broadcasterId },
                    transport = new { method = "websocket", session_id = _eventSubSessionId }
                };
                var json = JsonSerializer.Serialize(body);
                using var content = new StringContent(json, Encoding.UTF8, "application/json");

                var http = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauth);
                http.DefaultRequestHeaders.Remove("Client-Id");
                http.DefaultRequestHeaders.Add("Client-Id", clientId);

                var postResp = await PostWithRetriesAsync(http, url, content, 3).ConfigureAwait(false);
                var postTxt = await postResp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!postResp.IsSuccessStatusCode) {
                    Console.WriteLine($"CreateEventSubSubscriptionIfNotExists POST failed for {type}: {postResp.StatusCode} {postTxt}");
                } else {
                    Console.WriteLine($"Created EventSub subscription for {type}: {postTxt}");
                }
                http.Dispose();
            } catch (Exception ex) {
                Console.WriteLine($"CreateEventSubSubscriptionIfNotExists exception: {ex.Message}");
            }
        }

        // Original: def _mask_token(tkn: str)
        public static void MaskToken(string? tkn) {
            // TODO: implement
        }

    }

    public class TwitchConnector {
        public bool? worker_thread { get; set; }
        public bool? worker { get; set; }
        public bool? eventsub_worker_thread { get; set; }
        public bool? eventsub_worker { get; set; }
        public int? _last_worker_created { get; set; }
        public bool? config { get; set; }
        public bool? is_bot_account { get; set; }
        public string? oauth_token { get; set; }
        public object? DEFAULT_ACCESS_TOKEN { get; set; }
        public bool? refresh_token { get; set; }
        public object? DEFAULT_REFRESH_TOKEN { get; set; }
        public object? client_id { get; set; }
        public object? DEFAULT_CLIENT_ID { get; set; }
        public object? client_secret { get; set; }
        public object? DEFAULT_CLIENT_SECRET { get; set; }
        public object? username { get; set; }
        public object? broadcaster_id { get; set; }
        public System.Collections.Generic.List<object>? _recent_local_echoes { get; set; }
        public System.Collections.Generic.Dictionary<string,object>? _recent_message_ids { get; set; }
        public double? _recent_message_window { get; set; }
        public int? _max_recent_message_ids { get; set; }
        public bool? _initialized { get; set; }
        public object? connection_status { get; set; }
        public object? bot_username { get; set; }
        public object? disconnec { get; set; }
        public object? refresh_access_toke { get; set; }
        public bool? connected { get; set; }
        public object? message_received { get; set; }
        public object? message_received_with_metadata { get; set; }
        public object? message_deleted { get; set; }
        public object? error_occurred { get; set; }


        // Original: def __new__(cls, config=None, is_bot_account=False)
        public void New(object? config = null, bool? is_bot_account = null) {
            // TODO: implement
        }

        // Original: def __init__(self, config=None, is_bot_account=False)
        public TwitchConnector(object? config = null, bool? is_bot_account = null) {
            // TODO: implement constructor
            this.worker_thread = null;
            this.worker = null;
            this.eventsub_worker_thread = null;
            this.eventsub_worker = null;
            this._last_worker_created = null;
            this.config = null;
            this.is_bot_account = null;
            this.oauth_token = null;
            this.DEFAULT_ACCESS_TOKEN = null;
            this.refresh_token = null;
            this.DEFAULT_REFRESH_TOKEN = null;
            this.client_id = null;
            this.DEFAULT_CLIENT_ID = null;
            this.client_secret = null;
            this.DEFAULT_CLIENT_SECRET = null;
            this.username = null;
            this.broadcaster_id = null;
            this._recent_local_echoes = null;
            this._recent_message_ids = null;
            this._recent_message_window = null;
            this._max_recent_message_ids = null;
            this._initialized = null;
            this.connection_status = null;
            this.bot_username = null;
            this.disconnec = null;
            this.refresh_access_toke = null;
            this.connected = null;
            this.message_received = null;
            this.message_received_with_metadata = null;
            this.message_deleted = null;
            this.error_occurred = null;
        }

        // Original: def set_token(self, token: str)
        public void SetToken(string? token) {
            try {
                this.oauth_token = token;
                core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "oauth_token", token ?? string.Empty);
                Console.WriteLine($"TwitchConnector.SetToken: token length={(token?.Length ?? 0)}");
            } catch (Exception ex) {
                Console.WriteLine($"TwitchConnector.SetToken error: {ex.Message}");
            }
        }

        // Original: def set_username(self, username: str)
        public void SetUsername(string? username) {
            try {
                this.username = username;
                core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "bot_username", username ?? string.Empty);
                Console.WriteLine($"TwitchConnector.SetUsername: {username}");
            } catch (Exception ex) {
                Console.WriteLine($"TwitchConnector.SetUsername error: {ex.Message}");
            }
        }

        // Original: def set_bot_username(self, bot_username: str)
        public void SetBotUsername(string? bot_username) {
            // TODO: implement
        }

        // Original: def connect(self, username: str)
        public void Connect(string? username) {
            try {
                if (!string.IsNullOrEmpty(username)) this.username = username;
                Twitch_connectorModule.Connect(this.username?.ToString());
                this.connected = true;
                Console.WriteLine($"TwitchConnector.Connect: connected (username={this.username})");
            } catch (Exception ex) {
                Console.WriteLine($"TwitchConnector.Connect error: {ex.Message}");
                this.connected = false;
            }
        }

        // Original: def refresh_access_token(self)
        public void RefreshAccessToken() {
            // legacy wrapper
            RefreshAccessTokenForPlatform(core.platforms.PlatformIds.Twitch);
        }

        public void RefreshAccessTokenForPlatform(string platform) {
            try {
                var h = new core.oauth_handler.OAuthHandler();
                // fire-and-forget refresh
                _ = h.RefreshTokenAsync(platform);
            } catch (Exception ex) {
                Console.WriteLine($"RefreshAccessTokenForPlatform({platform}) exception: {ex.Message}");
            }
        }

        // Original: def _on_eventsub_reauth_requested(self, oauth_url: str)
        public void OnEventsubReauthRequested(string? oauth_url) {
            // TODO: implement
        }

        // Original: def disconnect(self)
        public void Disconnect() {
            try {
                this.connected = false;
                Console.WriteLine("TwitchConnector.Disconnect: disconnected");
            } catch (Exception ex) {
                Console.WriteLine($"TwitchConnector.Disconnect error: {ex.Message}");
            }
        }

        // Original: def send_message(self, message: str)
        public void SendMessage(string? message) {
            try {
                if (string.IsNullOrEmpty(message)) return;
                // If we have a broadcaster_id set on the instance, persist it to platform config for the helper
                try {
                    if (this.broadcaster_id != null) core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "broadcaster_id", this.broadcaster_id?.ToString() ?? string.Empty);
                } catch { }
                var ok = Twitch_connectorModule.SendChatMessageAsync(core.platforms.PlatformIds.Twitch, message).GetAwaiter().GetResult();
                Console.WriteLine($"TwitchConnector.SendMessage: sent={ok} [{this.username}] {message}");
            } catch (Exception ex) {
                Console.WriteLine($"TwitchConnector.SendMessage error: {ex.Message}");
            }
        }

        // Original: def delete_message(self, message_id: str)
        public void DeleteMessage(string? message_id) {
            // TODO: implement
        }

        // Original: def get_custom_reward(self, reward_id: str)
        public void GetCustomReward(string? reward_id) {
            // TODO: implement
        }

        // Original: def ban_user(self, username: str, user_id: Optional[str] = None)
        public void BanUser(string? username, object? user_id = null) {
            // TODO: implement
        }

        // Original: def onMessageReceived(self, username: str, message: str)
        public void OnMessageReceived(string? username, string? message) {
            // TODO: implement
        }

        // Original: def onMessageReceivedWithMetadata(self, username: str, message: str, metadata: dict)
        public void OnMessageReceivedWithMetadata(string? username, string? message, System.Collections.Generic.Dictionary<string,object>? metadata) {
            // TODO: implement
        }

        // Original: def onMessageDeleted(self, message_id: str)
        public void OnMessageDeleted(string? message_id) {
            // TODO: implement
        }

        // Original: def onRedemption(self, username: str, reward_title: str, reward_cost: int, user_input: str)
        public void OnRedemption(string? username, string? reward_title, int? reward_cost, string? user_input) {
            // TODO: implement
        }

        // Original: def onEvent(self, event_type: str, username: str, event_data: dict)
        public void OnEvent(string? event_type, string? username, System.Collections.Generic.Dictionary<string,object>? event_data) {
            // TODO: implement
        }

        // Original: def onEventSubStatus(self, connected: bool)
        public void OnEventSubStatus(bool? connected) {
            // TODO: implement
        }

        // Original: def onStatusChanged(self, connected: bool)
        public void OnStatusChanged(bool? connected) {
            // TODO: implement
        }

        // Original: def onError(self, error: str)
        public void OnError(string? error) {
            // TODO: implement
        }

    }

    public class TwitchWorker {
        public object? _metadata_callback { get; set; }
        public object? _deletion_callback { get; set; }
        public bool? running { get; set; }
        public bool? loop { get; set; }
        public object? connect_to_twitc { get; set; }
        public object? error_signal { get; set; }
        public object? status_signal { get; set; }
        public object? IRC_SERVER { get; set; }
        public bool? ws { get; set; }
        public object? authenticat { get; set; }
        public object? channel { get; set; }
        public object? health_check_loo { get; set; }
        public object? refresh_token_if_neede { get; set; }
        public object? last_message_time { get; set; }
        public object? handle_messag { get; set; }
        public object? refresh_token { get; set; }
        public object? client_id { get; set; }
        public object? client_secret { get; set; }
        public object? oauth_token { get; set; }
        public int? connection_timeout { get; set; }
        public object? _last_parsed_time { get; set; }
        public object? bot_nick { get; set; }
        public bool? _auth_printed { get; set; }
        public bool? connector { get; set; }
        public object? parse_clearms { get; set; }
        public object? _deletion_callbac { get; set; }
        public object? parse_usernotic { get; set; }
        public object? message_signal { get; set; }
        public object? _metadata_callbac { get; set; }
        public object? parse_privms { get; set; }
        public object? send_message_asyn { get; set; }

        public TwitchWorker() {
            this._metadata_callback = null;
            this._deletion_callback = null;
            this.running = null;
            this.loop = null;
            this.connect_to_twitc = null;
            this.error_signal = null;
            this.status_signal = null;
            this.IRC_SERVER = null;
            this.ws = null;
            this.authenticat = null;
            this.channel = null;
            this.health_check_loo = null;
            this.refresh_token_if_neede = null;
            this.last_message_time = null;
            this.handle_messag = null;
            this.refresh_token = null;
            this.client_id = null;
            this.client_secret = null;
            this.oauth_token = null;
            this.connection_timeout = null;
            this._last_parsed_time = null;
            this.bot_nick = null;
            this._auth_printed = null;
            this.connector = null;
            this.parse_clearms = null;
            this._deletion_callbac = null;
            this.parse_usernotic = null;
            this.message_signal = null;
            this._metadata_callbac = null;
            this.parse_privms = null;
            this.send_message_asyn = null;
        }

        // Original: def set_metadata_callback(self, callback)
        public void SetMetadataCallback(object? callback) {
            // TODO: implement
        }

        // Original: def set_deletion_callback(self, callback)
        public void SetDeletionCallback(object? callback) {
            // TODO: implement
        }

        // Original: def run(self)
        public void Run() {
            // TODO: implement
        }

        // Original: def connect_to_twitch(self)
        public async Task ConnectToTwitch() {
            // TODO: implement
            // // original awaited: self.authenticate()\n                    \n
            await Task.Yield();
            return;
        }

        // Original: def refresh_token_if_needed(self)
        public async Task RefreshTokenIfNeeded() {
            // TODO: implement
            await Task.Yield();
            return;
        }

        // Original: def health_check_loop(self, websocket)
        public async Task HealthCheckLoop(object? websocket) {
            // TODO: implement
            // original awaited: asyncio.sleep(30)
            await Task.Delay(TimeSpan.FromSeconds(30));
            return;
        }

        // Original: def authenticate(self)
        public async Task Authenticate() {
            // TODO: implement
            // // original awaited: self.ws.send(f'PASS oauth:{token}')\n        await self.ws.send(f'NICK {self.bot_nick}')\n        \n
            await Task.Yield();
            return;
        }

        // Original: def handle_message(self, raw_message: str)
        public async Task HandleMessage(string? raw_message) {
            // TODO: implement
            // // original awaited: self.ws.send('PONG :tmi.twitch.tv')\n            return\n        \n
            await Task.Yield();
            return;
        }

        // Original: def parse_clearmsg(self, raw_message: str)
        public void ParseClearmsg(string? raw_message) {
            // TODO: implement
        }

        // Original: def parse_usernotice(self, raw_message: str)
        public void ParseUsernotice(string? raw_message) {
            // TODO: implement
        }

        // Original: def parse_privmsg(self, raw_message: str)
        public void ParsePrivmsg(string? raw_message) {
            // TODO: implement
        }

        // Original: def stop(self)
        public void Stop() {
            // TODO: implement
        }

        // Original: def send_message_async(self, message: str)
        public async Task SendMessageAsync(string? message) {
            // TODO: implement
            // // original awaited: self.ws.send(f'PRIVMSG
            await Task.Yield();
            return;
        }

        // Original: def send_message(self, message: str)
        public void SendMessage(string? message) {
            try {
                if (string.IsNullOrEmpty(message)) return;
                var ok = Twitch_connectorModule.SendChatMessageAsync(core.platforms.PlatformIds.Twitch, message).GetAwaiter().GetResult();
                Console.WriteLine($"TwitchWorker.SendMessage: sent={ok} {message}");
            } catch (Exception ex) {
                Console.WriteLine($"TwitchWorker.SendMessage error: {ex.Message}");
            }
        }

    }

    public class TwitchEventSubWorker {
        public object? oauth_token { get; set; }
        public object? client_id { get; set; }
        public object? broadcaster_login { get; set; }
        public bool? broadcaster_id { get; set; }
        public bool? running { get; set; }
        public bool? ws { get; set; }
        public object? loop { get; set; }
        public object? session_id { get; set; }
        public object? subscription_id { get; set; }
        public bool? validated_scopes { get; set; }
        public object? connect_and_liste { get; set; }
        public object? error_signal { get; set; }
        public object? reauth_signal { get; set; }
        public object? EVENTSUB_URL { get; set; }
        public object? status_signal { get; set; }
        public object? validate_toke { get; set; }
        public object? get_broadcaster_i { get; set; }
        public object? subscribe_to_redemption { get; set; }
        public object? handle_messag { get; set; }
        public object? redemption_signal { get; set; }
        public object? event_signal { get; set; }


        // Original: def __init__(self, oauth_token: str, client_id: str, broadcaster_login: str)
        public TwitchEventSubWorker(string? oauth_token, string? client_id, string? broadcaster_login) {
            // TODO: implement constructor
            this.oauth_token = null;
            this.client_id = null;
            this.broadcaster_login = null;
            this.broadcaster_id = null;
            this.running = null;
            this.ws = null;
            this.loop = null;
            this.session_id = null;
            this.subscription_id = null;
            this.validated_scopes = null;
            this.connect_and_liste = null;
            this.error_signal = null;
            this.reauth_signal = null;
            this.EVENTSUB_URL = null;
            this.status_signal = null;
            this.validate_toke = null;
            this.get_broadcaster_i = null;
            this.subscribe_to_redemption = null;
            this.handle_messag = null;
            this.redemption_signal = null;
            this.event_signal = null;
        }

        // Original: def run(self)
        public void Run() {
            // TODO: implement
        }

        // Original: def validate_token(self)
        public async Task ValidateToken() {
            // TODO: implement
            await Task.Yield();
            return;
        }

        // Original: def connect_and_listen(self)
        public async Task ConnectAndListen() {
            // TODO: implement
            // // original awaited: ws.recv()\n                    welcome_data = json.loads(welcome_msg)\n                    \n                    if welcome_data.get('metadata', {}).get('message_type') == 'session_welcome':\n                        self.session_id = welcome_data['payload']['session']['id']\n                        logger.info(f"[EventSub] Session ID: {self.session_id}")\n                        \n
            await Task.Yield();
            return;
        }

        // Original: def get_broadcaster_id(self)
        public async Task GetBroadcasterId() {
            // TODO: implement
            await Task.Yield();
            return;
        }

        // Original: def subscribe_to_redemptions(self)
        public async Task SubscribeToRedemptions() {
            // TODO: implement
            await Task.Yield();
            return;
        }

        // Original: def _mask_token(tkn: str)
        public void MaskToken(string? tkn) {
            // TODO: implement
        }

        // Original: def handle_message(self, message: str)
        public async Task HandleMessage(string? message) {
            // TODO: implement
            await Task.Yield();
            return;
        }

        // Original: def stop(self)
        public void Stop() {
            // TODO: implement
        }

    }

}

