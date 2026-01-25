using System;
using System.Threading.Tasks;

namespace core.badge_manager {
    public static class Badge_managerModule {
        // Original: def __init__(self, cache_dir: str = None)
        static BadgeManager? _manager = null;
        public static void Init(string? cache_dir = null) {
            if (_manager == null) _manager = new BadgeManager(cache_dir);
        }

        // Original: def load_cache(self)
        public static void LoadCache() {
            _manager?.LoadCache();
        }

        // Original: def save_cache(self)
        public static void SaveCache() {
            _manager?.SaveCache();
        }

        // Original: def fetch_twitch_badges(self, client_id: str, access_token: str, channel_id: str = None)
        public static void FetchTwitchBadges(string? client_id, string? access_token, string? channel_id = null) {
            _manager?.FetchTwitchBadges(client_id, access_token, channel_id);
        }

        // Original: def download_badge(self, badge_key: str, size: str = '1x')
        public static void DownloadBadge(string? badge_key, string? size = null) {
            _manager?.DownloadBadge(badge_key, size);
        }

        // Original: def get_badge_url(self, badge_key: str, size: str = '1x')
        public static string? GetBadgeUrl(string? badge_key, string? size = null) {
            return _manager?.GetBadgeUrl(badge_key, size);
        }

        // Original: def get_badge_title(self, badge_key: str)
        public static string? GetBadgeTitle(string? badge_key) {
            return _manager == null ? null : _manager.GetBadgeTitle(badge_key);
        }

        // Original: def get_badge_path(self, badge_key: str, size: str = '1x')
        public static string? GetBadgePath(string? badge_key, string? size = null) {
            return _manager?.GetBadgePath(badge_key, size);
        }

        // Original: def get_badge_manager()
        public static BadgeManager? GetBadgeManager() {
            return _manager;
        }

    }

    public class BadgeManager {
        public string? cache_dir { get; set; }
        public System.Collections.Generic.Dictionary<string,string>? badge_urls { get; set; }
        public string? cache_file { get; set; }


        // Original: def __init__(self, cache_dir: str = None)
        public BadgeManager(string? cache_dir = null) {
            this.cache_dir = string.IsNullOrEmpty(cache_dir) ? System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), ".audiblezenbot", "badges") : cache_dir;
            this.cache_file = System.IO.Path.Combine(this.cache_dir, "badges.json");
            this.badge_urls = new System.Collections.Generic.Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
            // ensure directory
            try { System.IO.Directory.CreateDirectory(this.cache_dir); } catch {}
            LoadCache();
        }

        // Original: def load_cache(self)
        public void LoadCache() {
            try {
                if (string.IsNullOrEmpty(this.cache_file)) return;
                if (!System.IO.File.Exists(this.cache_file)) return;
                var txt = System.IO.File.ReadAllText(this.cache_file);
                var dict = System.Text.Json.JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(txt);
                if (dict != null) this.badge_urls = new System.Collections.Generic.Dictionary<string,string>(dict, StringComparer.OrdinalIgnoreCase);
            } catch (Exception ex) {
                Console.WriteLine($"BadgeManager.LoadCache error: {ex.Message}");
            }
        }

        // Original: def save_cache(self)
        public void SaveCache() {
            try {
                if (string.IsNullOrEmpty(this.cache_file) || this.badge_urls == null) return;
                var txt = System.Text.Json.JsonSerializer.Serialize(this.badge_urls, new System.Text.Json.JsonSerializerOptions { WriteIndented = true });
                System.IO.File.WriteAllText(this.cache_file, txt);
            } catch (Exception ex) {
                Console.WriteLine($"BadgeManager.SaveCache error: {ex.Message}");
            }
        }

        // Original: def fetch_twitch_badges(self, client_id: str, access_token: str, channel_id: str = None)
        public void FetchTwitchBadges(string? client_id, string? access_token, string? channel_id = null) {
            // Minimal implementation: attempt to call Twitch badges API and cache badge URLs.
            try {
                if (string.IsNullOrEmpty(client_id) || string.IsNullOrEmpty(access_token)) return;
                var http = new System.Net.Http.HttpClient();
                http.DefaultRequestHeaders.Add("Client-Id", client_id);
                http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", access_token);
                // Prefer canonical streamer id if no channel_id provided
                if (string.IsNullOrEmpty(channel_id)) {
                    try {
                        channel_id = core.config.ConfigModule.GetPlatformUserId(core.platforms.PlatformIds.Twitch, "streamer", "");
                    } catch { }
                }
                string url = "https://api.twitch.tv/helix/chat/badges?broadcaster_id=" + Uri.EscapeDataString(channel_id ?? "");
                var resp = core.http_retry.HttpRetry.GetWithRetriesAsync(http, url).GetAwaiter().GetResult();
                if (!resp.IsSuccessStatusCode) return;
                var body = resp.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                try {
                    using var doc = System.Text.Json.JsonDocument.Parse(body);
                    if (doc.RootElement.TryGetProperty("data", out var data) && data.ValueKind == System.Text.Json.JsonValueKind.Array) {
                        foreach (var item in data.EnumerateArray()) {
                            if (item.TryGetProperty("set_id", out var sid) && item.TryGetProperty("versions", out var versions) && versions.ValueKind == System.Text.Json.JsonValueKind.Array) {
                                var setId = sid.GetString() ?? string.Empty;
                                foreach (var ver in versions.EnumerateArray()) {
                                    if (ver.TryGetProperty("id", out var vid)) {
                                        var versionId = vid.GetString() ?? string.Empty;
                                        var baseKey = setId + ":" + versionId;
                                        // check common sizes
                                        if (ver.TryGetProperty("image_url_1x", out var img1)) {
                                            var url1 = img1.GetString() ?? string.Empty;
                                            if (!string.IsNullOrEmpty(url1)) {
                                                var local = SaveUrlToCache(url1, baseKey + "_1x");
                                                if (!string.IsNullOrEmpty(local)) this.badge_urls![baseKey + ":1x"] = local;
                                            }
                                        }
                                        if (ver.TryGetProperty("image_url_2x", out var img2)) {
                                            var url2 = img2.GetString() ?? string.Empty;
                                            if (!string.IsNullOrEmpty(url2)) {
                                                var local = SaveUrlToCache(url2, baseKey + "_2x");
                                                if (!string.IsNullOrEmpty(local)) this.badge_urls![baseKey + ":2x"] = local;
                                            }
                                        }
                                        if (ver.TryGetProperty("image_url_4x", out var img4)) {
                                            var url4 = img4.GetString() ?? string.Empty;
                                            if (!string.IsNullOrEmpty(url4)) {
                                                var local = SaveUrlToCache(url4, baseKey + "_4x");
                                                if (!string.IsNullOrEmpty(local)) this.badge_urls![baseKey + ":4x"] = local;
                                            }
                                        }
                                        // fallback: any image_url_* property
                                        if (this.badge_urls!.ContainsKey(baseKey + ":1x") == false && ver.TryGetProperty("image_url", out var imgAny)) {
                                            var urlAny = imgAny.GetString() ?? string.Empty;
                                            if (!string.IsNullOrEmpty(urlAny)) {
                                                var local = SaveUrlToCache(urlAny, baseKey + "_1x");
                                                if (!string.IsNullOrEmpty(local)) this.badge_urls![baseKey + ":1x"] = local;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                } catch { }
                SaveCache();
            } catch (Exception ex) {
                Console.WriteLine($"FetchTwitchBadges error: {ex.Message}");
            }
        }

        // Original: def download_badge(self, badge_key: str, size: str = '1x')
        public void DownloadBadge(string? badge_key, string? size = null) {
            // No-op for minimal implementation: could download image and cache locally later.
        }

        string SaveUrlToCache(string url, string filenameHint) {
            try {
                if (string.IsNullOrEmpty(url)) return string.Empty;
                var ext = System.IO.Path.GetExtension(new Uri(url).AbsolutePath);
                if (string.IsNullOrEmpty(ext)) ext = ".png";
                var safe = string.Join("_", System.IO.Path.GetInvalidFileNameChars()
                    .Aggregate(filenameHint, (s, c) => s.Replace(c.ToString(), ""))
                );
                var fileName = safe + ext;
                var localPath = System.IO.Path.Combine(this.cache_dir ?? string.Empty, fileName);
                if (System.IO.File.Exists(localPath)) return localPath;
                using var http = new System.Net.Http.HttpClient();
                var resp = core.http_retry.HttpRetry.GetWithRetriesAsync(http, url).GetAwaiter().GetResult();
                if (!resp.IsSuccessStatusCode) throw new Exception($"download failed: {resp.StatusCode}");
                var data = resp.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult();
                System.IO.File.WriteAllBytes(localPath, data);
                return localPath;
            } catch (Exception ex) {
                Console.WriteLine($"SaveUrlToCache error for {url}: {ex.Message}");
                return string.Empty;
            }
        }

        // Original: def get_badge_url(self, badge_key: str, size: str = '1x')
        public string? GetBadgeUrl(string? badge_key, string? size = null) {
            if (string.IsNullOrEmpty(badge_key) || badge_urls == null) return null;
            return badge_urls.TryGetValue(badge_key, out var v) ? v : null;
        }

        // Original: def get_badge_title(self, badge_key: str)
        public string? GetBadgeTitle(string? badge_key) {
            // Minimal: return badge_key as title
            return badge_key;
        }

        // Original: def get_badge_path(self, badge_key: str, size: str = '1x')
        public string? GetBadgePath(string? badge_key, string? size = null) {
            // If we had local downloads, return path. For now return null.
            return null;
        }

        // Original: def get_badge_manager()
        public BadgeManager GetBadgeManager() {
            return this;
        }

    }

}

