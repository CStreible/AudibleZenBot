using System;
using System.Text;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Net.Http;
using System.Text.Json;
using System.Net;
using System.Diagnostics;
using System.Collections.Generic;

namespace core.oauth_handler {
    public static class Oauth_handlerModule {
        // Original: def log_message(self, format, *args)
        public static void LogMessage(object? format) {
            // TODO: implement
        }

        // Original: def __init__(self)
        public static void Init() {
            // TODO: implement
        }

        // Original: def authenticate(self, platform: str, client_id: str = None, client_secret: str = None)
        public static void Authenticate(string? platform, string? client_id = null, string? client_secret = null) {
            // TODO: implement
        }

        // Original: def run_server()
        public static void RunServer() {
            // TODO: implement
        }

        // Original: def _handler(req)
        public static void Handler(object? req) {
            // TODO: implement
        }

        // Original: def _generate_code_verifier(self)
        public static string GenerateCodeVerifier() {
            // Generate a URL-safe random string similar to Python's secrets.token_urlsafe(64)
            var bytes = new byte[48];
            RandomNumberGenerator.Fill(bytes);
            string base64 = Convert.ToBase64String(bytes);
            // base64 -> base64url without padding
            string urlSafe = base64.Replace('+', '-').Replace('/', '_').TrimEnd('=');
            return urlSafe;
        }

        // Original: def _generate_code_challenge(self, verifier: str)
        public static string GenerateCodeChallenge(string verifier) {
            // SHA256 and base64url-encode without padding
            using var sha = SHA256.Create();
            byte[] hash = sha.ComputeHash(Encoding.ASCII.GetBytes(verifier));
            string b64 = Convert.ToBase64String(hash);
            string urlSafe = b64.Replace('+', '-').Replace('/', '_').TrimEnd('=');
            return urlSafe;
        }

        // Exchange authorization code for access token. Returns access_token or throws on failure.
        public static async Task<string> ExchangeCodeForTokenAsync(string tokenUrl, string clientId, string code, string codeVerifier, string redirectUri, string? clientSecret = null) {
            using var client = core.http_client.HttpClientFactory.GetClient(forceNew: true);

            var values = new List<KeyValuePair<string, string>>() {
                new KeyValuePair<string,string>("client_id", clientId),
                new KeyValuePair<string,string>("code", code),
                new KeyValuePair<string,string>("code_verifier", codeVerifier),
                new KeyValuePair<string,string>("grant_type", "authorization_code"),
                new KeyValuePair<string,string>("redirect_uri", redirectUri)
            };
            if (!string.IsNullOrEmpty(clientSecret)) {
                values.Add(new KeyValuePair<string,string>("client_secret", clientSecret));
            }

            using var content = new FormUrlEncodedContent(values);
            HttpResponseMessage resp = await core.http_retry.HttpRetry.PostWithRetriesAsync(client, tokenUrl, content).ConfigureAwait(false);
            var respText = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
            // Do not call EnsureSuccessStatusCode here; caller may want to inspect body on failure.
            return respText;
        }

        // Perform a full OAuth authorization code + PKCE flow using a local HttpListener for the callback.
        // Returns the access token string on success.
        public static async Task<string> PerformOAuthFlow(string authUrl, string tokenUrl, string clientId, string[] scopes, int port = 8889, string? clientSecret = null) {
            var codeVerifier = GenerateCodeVerifier();
            var codeChallenge = GenerateCodeChallenge(codeVerifier);
            var state = Convert.ToBase64String(RandomNumberGenerator.GetBytes(16)).Replace("=", "");

            var redirectUri = $"http://localhost:{port}/callback";

            var query = new List<string>() {
                $"client_id={Uri.EscapeDataString(clientId)}",
                $"redirect_uri={Uri.EscapeDataString(redirectUri)}",
                $"response_type=code",
                $"scope={Uri.EscapeDataString(string.Join(' ', scopes))}",
                $"state={Uri.EscapeDataString(state)}",
                $"code_challenge={Uri.EscapeDataString(codeChallenge)}",
                $"code_challenge_method=S256",
                $"force_verify=true"
            };

            var fullAuthUrl = authUrl + "?" + string.Join("&", query);

            using var listener = new HttpListener();
            var prefix = $"http://localhost:{port}/";
            listener.Prefixes.Add(prefix);
            try {
                listener.Start();
            } catch (HttpListenerException ex) {
                throw new InvalidOperationException($"Failed to start local callback listener on {prefix}: {ex.Message}");
            }

            try {
                // Open browser (log and try multiple fallbacks so we can debug on Windows)
                Console.WriteLine($"Opening browser to: {fullAuthUrl}");
                try {
                    Process.Start(new ProcessStartInfo(fullAuthUrl) { UseShellExecute = true });
                } catch (Exception ex) {
                    Console.WriteLine($"Process.Start(url) failed: {ex.Message}");
                    try {
                        // Try Explorer fallback
                        Process.Start(new ProcessStartInfo("explorer", fullAuthUrl) { UseShellExecute = true });
                    } catch (Exception ex2) {
                        Console.WriteLine($"Explorer fallback failed: {ex2.Message}");
                        try {
                            // Try cmd start (works on many Windows environments)
                            Process.Start(new ProcessStartInfo("cmd", $"/c start \"\" \"{fullAuthUrl}\"") { CreateNoWindow = true, UseShellExecute = false });
                        } catch (Exception ex3) {
                            Console.WriteLine($"cmd start fallback failed: {ex3.Message}");
                            // rethrow so caller can surface error
                            throw;
                        }
                    }
                }

                // Wait for incoming request (timeout 120s)
                var getContextTask = listener.GetContextAsync();
                var completed = await Task.WhenAny(getContextTask, Task.Delay(TimeSpan.FromSeconds(120))).ConfigureAwait(false);
                if (completed != getContextTask) {
                    var msg = "Timeout waiting for OAuth callback";
                    try { System.IO.File.AppendAllText(".audiblezenbot\\logs\\oauth_errors.log", DateTime.UtcNow + " " + msg + "\n"); } catch { }
                    throw new TimeoutException(msg);
                }

                var context = getContextTask.Result;
                var req = context.Request;
                var qs = req.QueryString;
                var code = qs["code"];
                var returnedState = qs["state"];

                // Respond to browser
                var respString = "Authentication complete. You may close this window.";
                var buffer = System.Text.Encoding.UTF8.GetBytes(respString);
                context.Response.ContentLength64 = buffer.Length;
                context.Response.ContentType = "text/plain";
                await context.Response.OutputStream.WriteAsync(buffer, 0, buffer.Length).ConfigureAwait(false);
                context.Response.Close();

                if (string.IsNullOrEmpty(code) || returnedState != state) {
                    throw new InvalidOperationException("Invalid OAuth callback: missing code or state mismatch");
                }

                // Exchange code for token (returns full response JSON)
                string tokenRespText;
                try {
                    tokenRespText = await ExchangeCodeForTokenAsync(tokenUrl, clientId, code, codeVerifier, redirectUri, clientSecret).ConfigureAwait(false);
                } catch (Exception ex) {
                    try { System.IO.File.AppendAllText(".audiblezenbot\\logs\\oauth_errors.log", DateTime.UtcNow + " ExchangeCodeForToken exception: " + ex.ToString() + "\n"); } catch { }
                    throw;
                }
                try { System.IO.File.AppendAllText(".audiblezenbot\\logs\\oauth_events.log", DateTime.UtcNow + " Received token response: " + tokenRespText + "\n"); } catch { }
                return tokenRespText;
            } finally {
                try { listener.Stop(); } catch { }
            }
        }

        // Original: def __init__(self, platform: str, parent=None)
        public static void Init(string? platform, object? parent = null) {
            // TODO: implement
        }

        // Original: def accept(self)
        public static void Accept() {
            // TODO: implement
        }

        // Original: def get_token(self)
        public static void GetToken() {
            // TODO: implement
        }

    }

    public class OAuthCallbackHandler {

        public OAuthCallbackHandler() {
        }

        // Original: def log_message(self, format, *args)
        public void LogMessage(object? format) {
            // TODO: implement
        }

    }

    public class OAuthHandler {
        public object? server { get; set; }
        public object? server_thread { get; set; }
        public object? CONFIGS { get; set; }
        public object? auth_completed { get; set; }
        public object? auth_failed { get; set; }
        public object? _generate_code_verifie { get; set; }
        public object? _generate_code_challeng { get; set; }
        public object? _start_callback_serve { get; set; }
        public object? _exchange_code_for_toke { get; set; }


        // Original: def __init__(self)
        public OAuthHandler() {
            // TODO: implement constructor
            this.server = null;
            this.server_thread = null;
            // initialize default configs similar to Python defaults
            this.CONFIGS = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, object>>() {
                { core.platforms.PlatformIds.Twitch, new System.Collections.Generic.Dictionary<string, object>() {
                    { "auth_url", "https://id.twitch.tv/oauth2/authorize" },
                    { "token_url", "https://id.twitch.tv/oauth2/token" },
                    { "client_id", "YOUR_TWITCH_CLIENT_ID" },
                    { "redirect_uri", "http://localhost:3000" },
                    { "scopes", new string[] { "user:read:email", "chat:read", "chat:edit", "channel:read:subscriptions", "channel:manage:broadcast", "channel:read:redemptions", "bits:read", "moderator:read:followers" } }
                } },
                { core.platforms.PlatformIds.YouTube, new System.Collections.Generic.Dictionary<string, object>() {
                    { "auth_url", "https://accounts.google.com/o/oauth2/v2/auth" },
                    { "token_url", "https://oauth2.googleapis.com/token" },
                    { "client_id", "YOUR_YOUTUBE_CLIENT_ID" },
                    { "redirect_uri", "http://localhost:3000" },
                    { "scopes", new string[] { "https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.force-ssl" } }
                } },
                { core.platforms.PlatformIds.Twitter, new System.Collections.Generic.Dictionary<string, object>() {
                    { "auth_url", "https://twitter.com/i/oauth2/authorize" },
                    { "token_url", "https://api.twitter.com/2/oauth2/token" },
                    { "client_id", "YnpWQ2s2Q1VuX1RVWG4wTlNvZTg6MTpjaQ" },
                    { "client_secret", "52_s2M2njaNEGOymH0Bym9h7Ry6xPjOY9J4YuHPztrZrPROMZ8" },
                    { "redirect_uri", "http://localhost:3000" },
                    { "scopes", new string[] { "tweet.read", "users.read", "offline.access" } }
                } }
            };
            this.auth_failed = null;
            this._generate_code_verifie = null;
            this._generate_code_challeng = null;
            this._start_callback_serve = null;
            this._exchange_code_for_toke = null;
        }

        // Original: def authenticate(self, platform: str, client_id: str = None, client_secret: str = None)
        public void Authenticate(string? platform, string? client_id = null, string? client_secret = null) {
            // Run the flow asynchronously
            _ = Task.Run(async () => {
                try {
                    if (string.IsNullOrEmpty(platform)) {
                        throw new ArgumentException("platform is required");
                    }

                    // Prefer runtime config from core.config.ConfigModule, fall back to embedded defaults
                    var platformKey = platform.ToLowerInvariant();
                    var platformCfg = core.config.ConfigModule.GetPlatformConfig(platformKey);
                    System.Collections.Generic.Dictionary<string, object>? cfg = null;
                    if (platformCfg != null && platformCfg.Count > 0) {
                        cfg = platformCfg;
                    } else {
                        var configs = this.CONFIGS as System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, object>>;
                        if (configs == null || !configs.ContainsKey(platformKey)) {
                            if (this.auth_failed is Delegate df) df.DynamicInvoke(platform, $"Platform {platform} not supported");
                            return;
                        }
                        cfg = configs[platformKey];
                    }

                    // helpers to extract values that may be strings, arrays, or JsonElement
                    System.Collections.Generic.Dictionary<string, object>? primary = platformCfg;
                    System.Collections.Generic.Dictionary<string, object>? fallback = null;
                    if (primary == null || primary.Count == 0) {
                        var configs = this.CONFIGS as System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, object>>;
                        if (configs != null && configs.ContainsKey(platformKey)) {
                            fallback = configs[platformKey];
                        }
                    } else {
                        var configs = this.CONFIGS as System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, object>>;
                        if (configs != null && configs.ContainsKey(platformKey)) fallback = configs[platformKey];
                    }

                    object? GetVal(string k) {
                        if (primary != null && primary.ContainsKey(k)) return primary[k];
                        if (fallback != null && fallback.ContainsKey(k)) return fallback[k];
                        return null;
                    }

                    string? ToStr(object? o) {
                        if (o == null) return null;
                        if (o is System.Text.Json.JsonElement je) {
                            if (je.ValueKind == System.Text.Json.JsonValueKind.String) return je.GetString();
                            return je.ToString();
                        }
                        return o.ToString() ?? string.Empty;
                    }

                    string[] ToStringArray(object? o) {
                        if (o == null) return Array.Empty<string>();
                        if (o is string[] sa) return sa;
                        if (o is System.Text.Json.JsonElement je && je.ValueKind == System.Text.Json.JsonValueKind.Array) {
                            var list = new System.Collections.Generic.List<string>();
                            foreach (var e in je.EnumerateArray()) {
                                if (e.ValueKind == System.Text.Json.JsonValueKind.String) list.Add(e.GetString()!);
                                else list.Add(e.ToString());
                            }
                            return list.ToArray();
                        }
                        if (o is System.Collections.IEnumerable ie) {
                            var list = new System.Collections.Generic.List<string>();
                            foreach (var x in ie) list.Add(x?.ToString() ?? string.Empty);
                            return list.ToArray();
                        }
                        return new string[] { o?.ToString() ?? string.Empty };
                    }

                    var authUrl = ToStr(GetVal("auth_url")) ?? string.Empty;
                    var tokenUrl = ToStr(GetVal("token_url")) ?? string.Empty;
                    var cfgClientId = ToStr(GetVal("client_id"));
                    var cfgClientSecret = ToStr(GetVal("client_secret"));
                    var useClientId = !string.IsNullOrEmpty(client_id) ? client_id : cfgClientId;
                    var useClientSecret = !string.IsNullOrEmpty(client_secret) ? client_secret : cfgClientSecret;

                    // Diagnostic logging to terminal for troubleshooting missing client_id/secret
                    try {
                        string mask(string s) {
                            if (string.IsNullOrEmpty(s)) return "<missing>";
                            if (s.Length <= 8) return s;
                            return s.Substring(0,4) + "..." + s.Substring(s.Length-4);
                        }
                        var cfgClientSecretMasked = mask(cfgClientSecret);
                        var useClientSecretMasked = mask(useClientSecret);
                        var msg = $"[OAuthHandlerDiag] platformKey={platformKey} cfgClientId_present={(string.IsNullOrEmpty(cfgClientId)?"false":"true")} cfgClientId_masked={mask(cfgClientId)} useClientId_present={(string.IsNullOrEmpty(useClientId)?"false":"true")} useClientId_masked={mask(useClientId)} cfgClientSecret_present={(string.IsNullOrEmpty(cfgClientSecret)?"false":"true")} cfgClientSecret_masked={cfgClientSecretMasked} useClientSecret_present={(string.IsNullOrEmpty(useClientSecret)?"false":"true")} useClientSecret_masked={useClientSecretMasked}";
                        Console.WriteLine(msg);
                        try {
                            var logDir = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs");
                            try { System.IO.Directory.CreateDirectory(logDir); } catch { }
                            var logPath = System.IO.Path.Combine(logDir, "oauth_diag.log");
                            System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " " + msg + "\n");
                        } catch { }
                    } catch { }

                    if (string.IsNullOrEmpty(useClientId) || useClientId.StartsWith("YOUR_")) {
                        if (this.auth_failed is Delegate df2) df2.DynamicInvoke(platform, "Client ID not configured. Please set up OAuth credentials.");
                        return;
                    }

                    var scopes = ToStringArray(GetVal("scopes"));

                    // Determine callback port from configured redirect_uri if present to avoid redirect_mismatch
                    int port = 8889;
                    var cfgRedirect = ToStr(GetVal("redirect_uri"));
                    if (!string.IsNullOrEmpty(cfgRedirect)) {
                        try {
                            var u = new Uri(cfgRedirect);
                            if (u.IsLoopback && u.Port > 0) {
                                port = u.Port;
                            }
                        } catch (Exception ex) {
                            Console.WriteLine($"Invalid configured redirect_uri '{cfgRedirect}': {ex.Message}");
                        }
                    }

                    Console.WriteLine($"Using callback port {port} for platform {platform}");

                    var tokenResponseText = await Oauth_handlerModule.PerformOAuthFlow(authUrl, tokenUrl, useClientId, scopes, port, useClientSecret).ConfigureAwait(false);
                    // Try to parse token response (it may be an error body)
                    try {
                        using var doc = JsonDocument.Parse(tokenResponseText);
                        var root = doc.RootElement;
                        string? accessToken = null;
                        string? refreshToken = null;
                        long? expiresIn = null;
                        if (root.TryGetProperty("access_token", out var at)) accessToken = at.GetString();
                        if (root.TryGetProperty("refresh_token", out var rt)) refreshToken = rt.GetString();
                        if (root.TryGetProperty("expires_in", out var ei) && ei.ValueKind == JsonValueKind.Number) expiresIn = ei.GetInt64();

                        if (!string.IsNullOrEmpty(accessToken)) {
                            // persist tokens to runtime config
                            try {
                                core.config.ConfigModule.SetPlatformConfig(platformKey, "oauth_token", accessToken);
                                if (!string.IsNullOrEmpty(refreshToken)) core.config.ConfigModule.SetPlatformConfig(platformKey, "refresh_token", refreshToken);
                                var epoch = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                                core.config.ConfigModule.SetPlatformConfig(platformKey, "bot_token_timestamp", epoch);
                                core.config.ConfigModule.SetPlatformConfig(platformKey, "streamer_token_timestamp", epoch);
                                core.config.ConfigModule.SetPlatformConfig(platformKey, "bot_logged_in", true);
                                core.config.ConfigModule.SetPlatformConfig(platformKey, "streamer_logged_in", true);
                            } catch { }
                        }

                        if (this.auth_completed is Delegate ac) {
                            ac.DynamicInvoke(platform, accessToken ?? tokenResponseText);
                        }
                    } catch (JsonException) {
                        // not JSON — just pass back raw text
                        if (this.auth_completed is Delegate ac) ac.DynamicInvoke(platform, tokenResponseText);
                    }
                } catch (Exception ex) {
                    if (this.auth_failed is Delegate df3) df3.DynamicInvoke(platform, ex.Message);
                }
            });
        }

        // Refresh access token using stored refresh_token for the given platform.
        public async Task<bool> RefreshTokenAsync(string? platform) {
            if (string.IsNullOrEmpty(platform)) return false;
            try {
                var platformCfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? cfg, string k) {
                    if (cfg == null) return string.Empty;
                    if (cfg.ContainsKey(k)) return cfg[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }

                var tokenUrl = GetStr(platformCfg, "token_url");
                var clientId = GetStr(platformCfg, "client_id");
                var clientSecret = GetStr(platformCfg, "client_secret");
                var refreshToken = GetStr(platformCfg, "refresh_token");

                if (string.IsNullOrEmpty(tokenUrl) || string.IsNullOrEmpty(refreshToken)) {
                    Console.WriteLine($"RefreshTokenAsync: missing token_url or refresh_token for platform {platform}");
                    return false;
                }

                using var client = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                var values = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, string>>() {
                    new System.Collections.Generic.KeyValuePair<string,string>("grant_type", "refresh_token"),
                    new System.Collections.Generic.KeyValuePair<string,string>("refresh_token", refreshToken),
                };
                if (!string.IsNullOrEmpty(clientId)) values.Add(new System.Collections.Generic.KeyValuePair<string,string>("client_id", clientId));
                if (!string.IsNullOrEmpty(clientSecret)) values.Add(new System.Collections.Generic.KeyValuePair<string,string>("client_secret", clientSecret));

                using var content = new FormUrlEncodedContent(values);
                HttpResponseMessage resp = await core.http_retry.HttpRetry.PostWithRetriesAsync(client, tokenUrl, content).ConfigureAwait(false);
                var respText = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode) {
                    Console.WriteLine($"RefreshTokenAsync failed for {platform}: {resp.StatusCode} {respText}");
                    return false;
                }

                try {
                    using var doc = JsonDocument.Parse(respText);
                    var root = doc.RootElement;
                    string? accessToken = null;
                    string? newRefresh = null;
                    long? expiresIn = null;
                    if (root.TryGetProperty("access_token", out var at)) accessToken = at.GetString();
                    if (root.TryGetProperty("refresh_token", out var rt)) newRefresh = rt.GetString();
                    if (root.TryGetProperty("expires_in", out var ei) && ei.ValueKind == JsonValueKind.Number) expiresIn = ei.GetInt64();

                    if (!string.IsNullOrEmpty(accessToken)) {
                        try {
                            core.config.ConfigModule.SetPlatformConfig(platform, "oauth_token", accessToken);
                            if (!string.IsNullOrEmpty(newRefresh)) core.config.ConfigModule.SetPlatformConfig(platform, "refresh_token", newRefresh);
                            var epoch = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                            core.config.ConfigModule.SetPlatformConfig(platform, "bot_token_timestamp", epoch);
                            core.config.ConfigModule.SetPlatformConfig(platform, "streamer_token_timestamp", epoch);
                            return true;
                        } catch {
                            // ignore persistence errors
                        }
                    }
                } catch (JsonException) {
                    Console.WriteLine($"RefreshTokenAsync: token endpoint returned non-JSON for {platform}: {respText}");
                    return false;
                }

                return false;
            } catch (Exception ex) {
                Console.WriteLine($"RefreshTokenAsync exception for {platform}: {ex.Message}");
                return false;
            }
        }

        // Get a valid access token for `platform`. If the stored token is expired or `forceRefresh` is true,
        // attempts to refresh using the refresh token and persists the new token.
        public async Task<string?> GetAccessTokenAsync(string? platform, bool forceRefresh = false) {
            if (string.IsNullOrEmpty(platform)) return null;
            try {
                var platformCfg = core.config.ConfigModule.GetPlatformConfig(platform);
                string GetStr(System.Collections.Generic.Dictionary<string, object>? cfg, string k) {
                    if (cfg == null) return string.Empty;
                    if (cfg.ContainsKey(k)) return cfg[k]?.ToString() ?? string.Empty;
                    return string.Empty;
                }
                long GetLong(System.Collections.Generic.Dictionary<string, object>? cfg, string k) {
                    if (cfg == null) return 0;
                    if (!cfg.ContainsKey(k)) return 0;
                    var v = cfg[k];
                    if (v == null) return 0;
                    if (v is long l) return l;
                    if (v is int i) return i;
                    if (long.TryParse(v.ToString(), out var parsed)) return parsed;
                    return 0;
                }

                var token = GetStr(platformCfg, "oauth_token");
                var refresh = GetStr(platformCfg, "refresh_token");
                var ts = GetLong(platformCfg, "bot_token_timestamp");
                if (ts == 0) ts = GetLong(platformCfg, "streamer_token_timestamp");
                var expiresIn = GetLong(platformCfg, "expires_in");

                var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                if (!forceRefresh && !string.IsNullOrEmpty(token)) {
                    if (expiresIn > 0 && ts > 0) {
                        var expiry = ts + expiresIn;
                        if (now < expiry - 60) {
                            return token; // still valid
                        }
                    } else {
                        return token; // no expiry info — assume valid
                    }
                }

                // Try refresh if we have a refresh token
                if (!string.IsNullOrEmpty(refresh)) {
                    var ok = await RefreshTokenAsync(platform).ConfigureAwait(false);
                    if (ok) {
                        var newCfg = core.config.ConfigModule.GetPlatformConfig(platform);
                        var newToken = GetStr(newCfg, "oauth_token");
                        if (!string.IsNullOrEmpty(newToken)) return newToken;
                    }
                }

                // fallback: return stored token (even if expired) or null
                return string.IsNullOrEmpty(token) ? null : token;
            } catch {
                return null;
            }
        }

        // Original: def run_server()
        public void RunServer() {
            // TODO: implement
        }

        // Original: def _handler(req)
        public void Handler(object? req) {
            // TODO: implement
        }

        // Original: def _generate_code_verifier(self)
        public void GenerateCodeVerifier() {
            // TODO: implement
        }

        // Original: def _generate_code_challenge(self, verifier: str)
        public void GenerateCodeChallenge(string? verifier) {
            // TODO: implement
        }

    }

    public class SimpleAuthDialog {
        public object? platform { get; set; }
        public object? token { get; set; }
        public object? setWindowTitl { get; set; }
        public object? setModa { get; set; }
        public object? resiz { get; set; }
        public object? token_input { get; set; }


        // Original: def __init__(self, platform: str, parent=None)
        public SimpleAuthDialog(string? platform, object? parent = null) {
            // TODO: implement constructor
            this.platform = null;
            this.token = null;
            this.setWindowTitl = null;
            this.setModa = null;
            this.resiz = null;
            this.token_input = null;
        }

        // Original: def accept(self)
        public void Accept() {
            // TODO: implement
        }

        // Original: def get_token(self)
        public void GetToken() {
            // TODO: implement
        }

    }

}

