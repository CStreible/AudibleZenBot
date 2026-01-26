using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using core.config;
using core.chat_manager;
using core.oauth_handler;

namespace AudibleZenBot.WPF.Views
{
    public partial class ConnectionsPage : UserControl
    {
        private int _tagCounter = 1;
        

        public ConnectionsPage()
        {
            InitializeComponent();

            // Twitch handlers
            Panel_Twitch.BtnStreamerLoginControl.Click += (s, e) => OnLoginClicked("Twitch", "streamer");
            Panel_Twitch.BtnBotLoginControl.Click += (s, e) => OnLoginClicked("Twitch", "bot");
            Panel_Twitch.DisableCheckbox.Checked += (s, e) => OnDisableChanged("Twitch", true);
            Panel_Twitch.DisableCheckbox.Unchecked += (s, e) => OnDisableChanged("Twitch", false);
            Panel_Twitch.AddTagButton.Click += (s, e) => Panel_Twitch.AddTag();
            Panel_Twitch.RefreshButton.Click += (s, e) => MessageBox.Show("Refresh Twitch (stub)", "Twitch");
            Panel_Twitch.SaveButton.Click += (s, e) => SavePlatformSettings("Twitch");

            // Enable Twitch category suggestions inside the panel
            Panel_Twitch.EnableTwitchCategorySuggestions();

            // YouTube handlers
            Panel_YouTube.BtnStreamerLoginControl.Click += (s, e) => OnLoginClicked("YouTube", "streamer");
            Panel_YouTube.BtnBotLoginControl.Click += (s, e) => OnLoginClicked("YouTube", "bot");
            Panel_YouTube.DisableCheckbox.Checked += (s, e) => OnDisableChanged("YouTube", true);
            Panel_YouTube.DisableCheckbox.Unchecked += (s, e) => OnDisableChanged("YouTube", false);
            Panel_YouTube.AddTagButton.Click += (s, e) => Panel_YouTube.AddTag();
            Panel_YouTube.RefreshButton.Click += (s, e) => MessageBox.Show("Refresh YouTube (stub)", "YouTube");
            Panel_YouTube.SaveButton.Click += (s, e) => SavePlatformSettings("YouTube");

            // Kick handlers
            Panel_Kick.BtnStreamerLoginControl.Click += (s, e) => OnLoginClicked("Kick", "streamer");
            Panel_Kick.BtnBotLoginControl.Click += (s, e) => OnLoginClicked("Kick", "bot");
            Panel_Kick.DisableCheckbox.Checked += (s, e) => OnDisableChanged("Kick", true);
            Panel_Kick.DisableCheckbox.Unchecked += (s, e) => OnDisableChanged("Kick", false);
            Panel_Kick.AddTagButton.Click += (s, e) => Panel_Kick.AddTag();
            Panel_Kick.RefreshButton.Click += (s, e) => MessageBox.Show("Refresh Kick (stub)", "Kick");
            Panel_Kick.SaveButton.Click += (s, e) => SavePlatformSettings("Kick");

            // Trovo handlers
            Panel_Trovo.BtnStreamerLoginControl.Click += (s, e) => OnLoginClicked("Trovo", "streamer");
            Panel_Trovo.BtnBotLoginControl.Click += (s, e) => OnLoginClicked("Trovo", "bot");
            Panel_Trovo.DisableCheckbox.Checked += (s, e) => OnDisableChanged("Trovo", true);
            Panel_Trovo.DisableCheckbox.Unchecked += (s, e) => OnDisableChanged("Trovo", false);
            Panel_Trovo.AddTagButton.Click += (s, e) => Panel_Trovo.AddTag();
            Panel_Trovo.RefreshButton.Click += (s, e) => MessageBox.Show("Refresh Trovo (stub)", "Trovo");
            Panel_Trovo.SaveButton.Click += (s, e) => SavePlatformSettings("Trovo");

            // DLive handlers
            Panel_DLive.BtnStreamerLoginControl.Click += (s, e) => OnLoginClicked("DLive", "streamer");
            Panel_DLive.BtnBotLoginControl.Click += (s, e) => OnLoginClicked("DLive", "bot");
            Panel_DLive.DisableCheckbox.Checked += (s, e) => OnDisableChanged("DLive", true);
            Panel_DLive.DisableCheckbox.Unchecked += (s, e) => OnDisableChanged("DLive", false);
            Panel_DLive.AddTagButton.Click += (s, e) => Panel_DLive.AddTag();
            Panel_DLive.RefreshButton.Click += (s, e) => MessageBox.Show("Refresh DLive (stub)", "DLive");
            Panel_DLive.SaveButton.Click += (s, e) => SavePlatformSettings("DLive");

            // Load saved account states into UI (persisted across runs)
            LoadSavedAccountStates();
        }

        private void OnLoginClicked(string platform, string accountType)
        {
            // If button currently indicates Logout, treat as a logout request
            var panel = GetPanelForPlatform(platform);
            try {
                if (panel != null) {
                    if (accountType == "streamer") {
                        var content = panel.BtnStreamerLoginControl.Content?.ToString() ?? "";
                        if (content.Equals("Logout", StringComparison.InvariantCultureIgnoreCase)) {
                            // Clear persisted streamer creds
                            var key = platform.ToLowerInvariant();
                            ConfigModule.SetPlatformConfig(key, "streamer_logged_in", false);
                            ConfigModule.SetPlatformConfig(key, "streamer_token", "");
                            ConfigModule.SetPlatformConfig(key, "streamer_refresh_token", "");
                            ConfigModule.SetPlatformConfig(key, "streamer_user_id", "");
                            ConfigModule.SetPlatformConfig(key, "streamer_display_name", "");
                            ConfigModule.Save();
                            Dispatcher.Invoke(() => {
                                panel.StreamerName.Text = "";
                                panel.BtnStreamerLoginControl.Content = "Login";
                            });
                            return;
                        }
                    } else {
                        var content = panel.BtnBotLoginControl.Content?.ToString() ?? "";
                        if (content.Equals("Logout", StringComparison.InvariantCultureIgnoreCase)) {
                            var key = platform.ToLowerInvariant();
                            ConfigModule.SetPlatformConfig(key, "bot_logged_in", false);
                            ConfigModule.SetPlatformConfig(key, "bot_token", "");
                            ConfigModule.SetPlatformConfig(key, "bot_refresh_token", "");
                            ConfigModule.SetPlatformConfig(key, "bot_user_id", "");
                            ConfigModule.SetPlatformConfig(key, "bot_display_name", "");
                            ConfigModule.Save();
                            Dispatcher.Invoke(() => {
                                panel.BotName.Text = "";
                                panel.BtnBotLoginControl.Content = "Login";
                            });
                            return;
                        }
                    }
                }
            } catch { }

            StartOAuth(platform, accountType);
        }

        private void StartOAuth(string platform, string accountType)
        {
            try
            {
                var handler = new OAuthHandler();

                handler.auth_completed = new Action<string, object>((plt, tokenOrText) => {
                    // Run API lookup and UI update asynchronously
                    Task.Run(async () => {
                        var p = GetPanelForPlatform(plt);
                        var info = GetInfoTextBoxForPlatform(plt);
                        try {
                            if (info != null) Dispatcher.Invoke(() => info.Text = "Authenticated.");
                        } catch { }

                        var token = tokenOrText?.ToString() ?? string.Empty;
                        var platformKey = plt.ToLowerInvariant();

                        try {
                            if (platformKey == "twitch") {
                                using var client = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                                var req = new HttpRequestMessage(HttpMethod.Get, "https://api.twitch.tv/helix/users");
                                if (!string.IsNullOrEmpty(token)) req.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token);
                                // Add Client-ID from config if present
                                var cfg = ConfigModule.GetPlatformConfig("twitch");
                                if (cfg != null && cfg.ContainsKey("client_id")) req.Headers.Add("Client-ID", cfg["client_id"]?.ToString() ?? "");
                                System.Net.Http.HttpResponseMessage? resp = null;
                                string txt = string.Empty;
                                try {
                                    resp = await client.SendAsync(req).ConfigureAwait(false);
                                    txt = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                                } catch (System.Exception ex) {
                                    try {
                                        var logPath2 = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs", "oauth_diag.log");
                                        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(logPath2) ?? ".");
                                        System.IO.File.AppendAllText(logPath2, DateTime.UtcNow.ToString("o") + " [OAuthHTTPError] twitch request exception=" + ex.Message + " stack=" + ex.StackTrace + "\n");
                                    } catch { }
                                }
                                try {
                                    var logPath = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs", "oauth_diag.log");
                                    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(logPath) ?? ".");
                                    var snippet = txt.Length > 1024 ? txt.Substring(0, 1024) + "..." : txt;
                                    var statusCode = resp == null ? 0 : (int)resp.StatusCode;
                                    var reason = resp == null ? "(no response)" : resp.ReasonPhrase;
                                    System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthHTTP] twitch users status=" + statusCode.ToString() + " reason=" + reason + " body_snippet=" + snippet + "\n");
                                } catch { }
                                if (resp.IsSuccessStatusCode) {
                                    using var doc = JsonDocument.Parse(txt);
                                    if (doc.RootElement.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Array && data.GetArrayLength() > 0) {
                                        var first = data[0];
                                        string display = string.Empty;
                                        string userId = string.Empty;
                                        if (first.TryGetProperty("id", out var idEl) && idEl.ValueKind == JsonValueKind.String) userId = idEl.GetString() ?? string.Empty;
                                        if (first.TryGetProperty("display_name", out var dn) && dn.ValueKind == JsonValueKind.String) display = dn.GetString() ?? string.Empty;
                                        if (string.IsNullOrEmpty(display) && first.TryGetProperty("login", out var ln) && ln.ValueKind == JsonValueKind.String) display = ln.GetString() ?? string.Empty;
                                        if (!string.IsNullOrEmpty(display) || !string.IsNullOrEmpty(userId)) {
                                            if (!string.IsNullOrEmpty(display)) ConfigModule.SetPlatformConfig(platformKey, accountType + "_display_name", display);
                                            if (!string.IsNullOrEmpty(userId)) ConfigModule.SetPlatformConfig(platformKey, accountType + "_user_id", userId);
                                            ConfigModule.Save();
                                            try {
                                                var logPath = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs", "oauth_diag.log");
                                                System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(logPath) ?? ".");
                                                var entry = DateTime.UtcNow.ToString("o") + " [OAuthComplete] platform=" + platformKey + " accountType=" + accountType + " saved_display=" + display + " saved_userid=" + userId + "\n";
                                                System.IO.File.AppendAllText(logPath, entry);
                                            } catch { }
                                            if (p != null) Dispatcher.Invoke(() => {
                                                if (accountType == "streamer") {
                                                    p.StreamerName.Text = (string.IsNullOrEmpty(display) ? userId : display);
                                                    p.BtnStreamerLoginControl.Content = "Logout";
                                                } else {
                                                    p.BotName.Text = (string.IsNullOrEmpty(display) ? userId : display);
                                                    p.BtnBotLoginControl.Content = "Logout";
                                                }
                                            });
                                            return;
                                        }
                                    }
                                }
                            } else if (platformKey == "youtube") {
                                using var client = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                                var req = new HttpRequestMessage(HttpMethod.Get, "https://www.googleapis.com/oauth2/v2/userinfo");
                                if (!string.IsNullOrEmpty(token)) req.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token);
                                System.Net.Http.HttpResponseMessage? resp = null;
                                string txt = string.Empty;
                                try {
                                    resp = await client.SendAsync(req).ConfigureAwait(false);
                                    txt = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                                } catch (System.Exception ex) {
                                    try {
                                        var logPath2 = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs", "oauth_diag.log");
                                        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(logPath2) ?? ".");
                                        System.IO.File.AppendAllText(logPath2, DateTime.UtcNow.ToString("o") + " [OAuthHTTPError] youtube request exception=" + ex.Message + " stack=" + ex.StackTrace + "\n");
                                    } catch { }
                                }
                                try {
                                    var logPath = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs", "oauth_diag.log");
                                    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(logPath) ?? ".");
                                    var snippet = txt.Length > 1024 ? txt.Substring(0, 1024) + "..." : txt;
                                    var statusCode = resp == null ? 0 : (int)resp.StatusCode;
                                    var reason = resp == null ? "(no response)" : resp.ReasonPhrase;
                                    System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthHTTP] youtube userinfo status=" + statusCode.ToString() + " reason=" + reason + " body_snippet=" + snippet + "\n");
                                } catch { }
                                if (resp.IsSuccessStatusCode) {
                                    using var doc = JsonDocument.Parse(txt);
                                    string display = string.Empty;
                                    string userId = string.Empty;
                                    if (doc.RootElement.TryGetProperty("id", out var idEl) && idEl.ValueKind == JsonValueKind.String) userId = idEl.GetString() ?? string.Empty;
                                    if (doc.RootElement.TryGetProperty("name", out var nameEl) && nameEl.ValueKind == JsonValueKind.String) display = nameEl.GetString() ?? string.Empty;
                                    if (!string.IsNullOrEmpty(display) || !string.IsNullOrEmpty(userId)) {
                                        if (!string.IsNullOrEmpty(display)) ConfigModule.SetPlatformConfig(platformKey, accountType + "_display_name", display);
                                        if (!string.IsNullOrEmpty(userId)) ConfigModule.SetPlatformConfig(platformKey, accountType + "_user_id", userId);
                                        ConfigModule.Save();
                                            if (p != null) Dispatcher.Invoke(() => {
                                                if (accountType == "streamer") {
                                                    p.StreamerName.Text = (string.IsNullOrEmpty(display) ? userId : display);
                                                    p.BtnStreamerLoginControl.Content = "Logout";
                                                } else {
                                                    p.BotName.Text = (string.IsNullOrEmpty(display) ? userId : display);
                                                    p.BtnBotLoginControl.Content = "Logout";
                                                }
                                            });
                                        return;
                                    }
                                }
                            }
                        } catch {
                            // ignore API errors, fall through to generic update
                        }

                        // fallback: mark as logged in
                        try {
                            var logPath = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs", "oauth_diag.log");
                            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(logPath) ?? ".");
                            System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthFallback] platform=" + platformKey + " accountType=" + accountType + " fallback_shown=1\n");
                        } catch { }
                        if (p != null) Dispatcher.Invoke(() => {
                            if (accountType == "streamer") {
                                p.StreamerName.Text = "(streamer logged in)";
                                p.BtnStreamerLoginControl.Content = "Logout";
                            } else {
                                p.BotName.Text = "(bot logged in)";
                                p.BtnBotLoginControl.Content = "Logout";
                            }
                        });
                    });
                });

                handler.auth_failed = new Action<string, object>((plt, err) => {
                    Dispatcher.Invoke(() => {
                        var info = GetInfoTextBoxForPlatform(plt);
                        if (info != null) info.Text = $"OAuth failed: {err}";
                    });
                });

                // Diagnostic: show resolved client_id from runtime config (also log to console)
                var diagCfg = ConfigModule.GetPlatformConfig(platform.ToLowerInvariant());
                var infoBox = GetInfoTextBoxForPlatform(platform);
                string clientId = "";
                try {
                    if (diagCfg != null && diagCfg.ContainsKey("client_id")) clientId = diagCfg["client_id"]?.ToString() ?? "";
                } catch { clientId = ""; }
                var maskedClientId = string.IsNullOrEmpty(clientId) ? "<missing>" : (clientId.Length > 8 ? clientId.Substring(0,4) + "..." + clientId.Substring(clientId.Length-4) : clientId);
                Console.WriteLine($"[OAuthDiag] platform={platform} client_id_present={(string.IsNullOrEmpty(clientId) ? "false" : "true")} client_id_masked={maskedClientId}");
                try {
                    var cfgJson = System.Text.Json.JsonSerializer.Serialize(diagCfg);
                    Console.WriteLine($"[OAuthDiag] platform config: {cfgJson}");
                } catch { }
                // Also write diagnostics to file in case console is not attached
                try {
                    var logDir = System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "logs");
                    try { System.IO.Directory.CreateDirectory(logDir); } catch { }
                    var logPath = System.IO.Path.Combine(logDir, "oauth_diag.log");
                    var line = DateTime.UtcNow.ToString("o") + " " + $"[OAuthDiag] platform={platform} client_id_present={(string.IsNullOrEmpty(clientId) ? "false" : "true")} client_id_masked={maskedClientId}";
                    System.IO.File.AppendAllText(logPath, line + "\n");
                    try { var cfgJson2 = System.Text.Json.JsonSerializer.Serialize(diagCfg); System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthDiag] platform config: " + cfgJson2 + "\n"); } catch { }

                    // Additional diagnostics: current working dir and candidate config paths
                    try {
                        var cwd = System.IO.Directory.GetCurrentDirectory();
                        var repoCandidate = System.IO.Path.Combine(cwd, ".audiblezenbot", "config.json");
                        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                        var homeCandidate = System.IO.Path.Combine(home, ".audiblezenbot", "config.json");
                        System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthDiag] CWD: " + cwd + "\n");
                        System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthDiag] repoCandidateExists: " + System.IO.File.Exists(repoCandidate).ToString() + " path=" + repoCandidate + "\n");
                        System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthDiag] homeCandidateExists: " + System.IO.File.Exists(homeCandidate).ToString() + " path=" + homeCandidate + "\n");
                        try { if (System.IO.File.Exists(repoCandidate)) System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthDiag] repoCandidateLen: " + new System.IO.FileInfo(repoCandidate).Length + "\n"); } catch { }
                        try { if (System.IO.File.Exists(homeCandidate)) System.IO.File.AppendAllText(logPath, DateTime.UtcNow.ToString("o") + " [OAuthDiag] homeCandidateLen: " + new System.IO.FileInfo(homeCandidate).Length + "\n"); } catch { }
                    } catch { }
                } catch { }
                if (string.IsNullOrEmpty(clientId)) {
                    if (infoBox != null) infoBox.Text = "Opening browser for OAuth login... (client_id missing)";
                } else {
                    if (infoBox != null) infoBox.Text = "Opening browser for OAuth login... (client_id present)";
                }
                handler.Authenticate(platform);
            }
            catch (System.Exception ex)
            {
                MessageBox.Show($"Failed to start OAuth: {ex.Message}", "OAuth Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private PlatformConnectionPanel GetPanelForPlatform(string platform)
        {
            return platform switch
            {
                "Twitch" => Panel_Twitch,
                "YouTube" => Panel_YouTube,
                "Kick" => Panel_Kick,
                "Trovo" => Panel_Trovo,
                "DLive" => Panel_DLive,
                _ => null,
            };
        }

        private void OnDisableChanged(string platform, bool disabled)
        {
            var key = platform.ToLowerInvariant();
            // persist to config
            ConfigModule.SetPlatformConfig(key, "disabled", disabled);
            ConfigModule.Save();
            // notify chat manager
            Chat_managerModule.DisablePlatform(key, disabled);

            var infoBox = GetInfoTextBoxForPlatform(platform);
            if (infoBox != null)
            {
                infoBox.Text = $"Platform {platform} is now {(disabled ? "disabled" : "enabled")}.";
            }
        }

        private TextBox GetInfoTextBoxForPlatform(string platform)
        {
            return platform switch
            {
                "Twitch" => Panel_Twitch.InfoBox,
                "YouTube" => Panel_YouTube.InfoBox,
                "Kick" => Panel_Kick.InfoBox,
                "Trovo" => Panel_Trovo.InfoBox,
                "DLive" => Panel_DLive.InfoBox,
                _ => null,
            };
        }

        private void LoadSavedAccountStates()
        {
            try {
                foreach (var platform in new string[] { "twitch", "youtube", "kick", "trovo", "dlive" }) {
                    var cfg = ConfigModule.GetPlatformConfig(platform);
                    if (cfg == null) continue;
                    bool streamerLoggedIn = false;
                    bool botLoggedIn = false;
                    try { if (cfg.ContainsKey("streamer_logged_in") && bool.TryParse(cfg["streamer_logged_in"]?.ToString() ?? "false", out var v1)) streamerLoggedIn = v1; } catch {}
                    try { if (cfg.ContainsKey("bot_logged_in") && bool.TryParse(cfg["bot_logged_in"]?.ToString() ?? "false", out var v2)) botLoggedIn = v2; } catch {}

                    var panel = platform switch {
                        "twitch" => Panel_Twitch,
                        "youtube" => Panel_YouTube,
                        "kick" => Panel_Kick,
                        "trovo" => Panel_Trovo,
                        "dlive" => Panel_DLive,
                        _ => null
                    };
                    if (panel == null) continue;

                    if (streamerLoggedIn) {
                        string display = "";
                        if (cfg.ContainsKey("streamer_display_name")) display = cfg["streamer_display_name"]?.ToString() ?? "";
                        if (string.IsNullOrEmpty(display) && cfg.ContainsKey("streamer_username")) display = cfg["streamer_username"]?.ToString() ?? "";
                        if (!string.IsNullOrEmpty(display)) Dispatcher.Invoke(() => panel.StreamerName.Text = display);
                        Dispatcher.Invoke(() => panel.BtnStreamerLoginControl.Content = "Logout");
                    }
                    if (botLoggedIn) {
                        string display = "";
                        if (cfg.ContainsKey("bot_display_name")) display = cfg["bot_display_name"]?.ToString() ?? "";
                        if (string.IsNullOrEmpty(display) && cfg.ContainsKey("bot_username")) display = cfg["bot_username"]?.ToString() ?? "";
                        if (!string.IsNullOrEmpty(display)) Dispatcher.Invoke(() => panel.BotName.Text = display);
                        Dispatcher.Invoke(() => panel.BtnBotLoginControl.Content = "Logout");
                    }
                }
            } catch (System.Exception) {
                // swallow - UI should still function
            }
        }

        

        private async void FetchTwitchCategorySuggestionsAsync(string query)
        {
            try
            {
                var q = (query ?? string.Empty).Trim();
                if (string.IsNullOrEmpty(q)) return;
                // read client_id and oauth_token from config
                var cfg = ConfigModule.GetPlatformConfig("twitch");
                string clientId = "";
                string oauthToken = "";
                if (cfg != null)
                {
                    if (cfg.ContainsKey("client_id")) clientId = cfg["client_id"]?.ToString() ?? "";
                    if (cfg.ContainsKey("oauth_token")) oauthToken = cfg["oauth_token"]?.ToString() ?? "";
                }
                if (string.IsNullOrEmpty(clientId) || string.IsNullOrEmpty(oauthToken))
                {
                    // nothing to do
                    await Dispatcher.InvokeAsync(() => { Panel_Twitch.CategoryPopupControl.IsOpen = false; });
                    return;
                }

                using var http = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                var req = new System.Net.Http.HttpRequestMessage(System.Net.Http.HttpMethod.Get, "https://api.twitch.tv/helix/search/categories?query=" + System.Uri.EscapeDataString(q));
                req.Headers.Add("Client-ID", clientId);
                req.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauthToken);
                var resp = await http.SendAsync(req).ConfigureAwait(false);
                var text = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode)
                {
                    await Dispatcher.InvokeAsync(() => Panel_Twitch.CategoryPopupControl.IsOpen = false);
                    return;
                }
                using var doc = System.Text.Json.JsonDocument.Parse(text);
                var root = doc.RootElement;
                var list = new System.Collections.Generic.List<string>();
                if (root.TryGetProperty("data", out var data) && data.ValueKind == System.Text.Json.JsonValueKind.Array)
                {
                    foreach (var item in data.EnumerateArray())
                    {
                        if (item.TryGetProperty("name", out var name) && name.ValueKind == System.Text.Json.JsonValueKind.String)
                        {
                            list.Add(name.GetString() ?? string.Empty);
                        }
                        if (list.Count >= 12) break;
                    }
                }
                // category cache handled inside PlatformConnectionPanel
                var toShow = list.Count > 10 ? list.GetRange(0, 10) : list;
                await Dispatcher.InvokeAsync(() => {
                    Panel_Twitch.CategorySuggestionsList.ItemsSource = toShow;
                    Panel_Twitch.CategoryPopupControl.IsOpen = Panel_Twitch.CategorySuggestionsList.Items.Count > 0;
                });
            }
            catch
            {
                await Dispatcher.InvokeAsync(() => Panel_Twitch.CategoryPopupControl.IsOpen = false);
            }
        }

        

        private void SavePlatformSettings(string platform)
        {
            var key = platform.ToLowerInvariant();
            switch (key)
            {
                case "twitch":
                    ConfigModule.SetPlatformConfig(key, "stream_title", Panel_Twitch.TitleBox.Text ?? "");
                    ConfigModule.SetPlatformConfig(key, "stream_category", Panel_Twitch.CategoryBox.Text ?? "");
                    ConfigModule.SetPlatformConfig(key, "stream_notification", Panel_Twitch.NotificationBox.Text ?? "");
                    break;
                case "youtube":
                    ConfigModule.SetPlatformConfig(key, "stream_title", Panel_YouTube.TitleBox.Text ?? "");
                    ConfigModule.SetPlatformConfig(key, "stream_category", Panel_YouTube.CategoryBox.Text ?? "");
                    break;
                case "kick":
                    ConfigModule.SetPlatformConfig(key, "stream_title", Panel_Kick.TitleBox.Text ?? "");
                    ConfigModule.SetPlatformConfig(key, "stream_category", Panel_Kick.CategoryBox.Text ?? "");
                    break;
                case "trovo":
                    ConfigModule.SetPlatformConfig(key, "stream_title", Panel_Trovo.TitleBox.Text ?? "");
                    ConfigModule.SetPlatformConfig(key, "stream_category", Panel_Trovo.CategoryBox.Text ?? "");
                    break;
                case "dlive":
                    ConfigModule.SetPlatformConfig(key, "stream_title", Panel_DLive.TitleBox.Text ?? "");
                    ConfigModule.SetPlatformConfig(key, "stream_category", Panel_DLive.CategoryBox.Text ?? "");
                    break;
            }
            // Persist tags for each platform as a comma-separated string
            string tags = string.Empty;
            switch (key)
            {
                case "twitch":
                    tags = Panel_Twitch.GetTagsAsString();
                    break;
                case "youtube":
                    tags = Panel_YouTube.GetTagsAsString();
                    break;
                case "kick":
                    tags = Panel_Kick.GetTagsAsString();
                    break;
                case "trovo":
                    tags = Panel_Trovo.GetTagsAsString();
                    break;
                case "dlive":
                    tags = Panel_DLive.GetTagsAsString();
                    break;
            }
            if (!string.IsNullOrEmpty(tags)) ConfigModule.SetPlatformConfig(key, "tags", tags);
            ConfigModule.Save();
            var info = GetInfoTextBoxForPlatform(platform);
            if (info != null) info.Text = $"Saved settings to config. Tags: {(string.IsNullOrEmpty(tags) ? "(none)" : tags)}";
        }
    }
}
