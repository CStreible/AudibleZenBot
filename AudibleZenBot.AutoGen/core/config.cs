using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace core.config {
    public static class ConfigModule {
        private static ConfigManager? _manager;

        public static void Init(string? config_file = null) {
            _manager = new ConfigManager(config_file);
        }

        public static Dictionary<string, object>? Load() {
            EnsureManager();
            return _manager!.Load();
        }

        public static void Save() {
            EnsureManager();
            _manager!.Save();
        }

        public static void GetDefaultConfig() {
            EnsureManager();
            _manager!.GetDefaultConfig();
        }

        public static object? Get(string? key, object? @default = null) {
            EnsureManager();
            return _manager!.Get(key, @default);
        }

        public static void Set(string? key, object? value) {
            EnsureManager();
            _manager!.Set(key, value);
        }

        public static Dictionary<string, object>? GetPlatformConfig(string? platform) {
            EnsureManager();
            return _manager!.GetPlatformConfig(platform);
        }

        // Returns the canonical user id for a given platform/accountType (e.g. "streamer" or "bot").
        // Checks in order: "{accountType}_user_id", "streamer_user_id", "broadcaster_user_id", "user_id".
        public static string GetPlatformUserId(string? platform, string? accountType, string? @default = "") {
            EnsureManager();
            return _manager!.GetPlatformUserId(platform, accountType, @default);
        }

        public static void SetPlatformConfig(string? platform, string? key, object? value) {
            EnsureManager();
            _manager!.SetPlatformConfig(platform, key, value);
        }

        public static void Reset() {
            EnsureManager();
            _manager!.Reset();
        }

        public static void MergePlatformStreamInfo(string? platform, Dictionary<string, object>? updates) {
            EnsureManager();
            _manager!.MergePlatformStreamInfo(platform, updates);
        }

        private static void EnsureManager() {
            if (_manager == null) _manager = new ConfigManager();
        }
    }

    public class ConfigManager {
        private readonly object _fileLock = new object();
        public string ConfigDir { get; set; }
        public string ConfigFile { get; set; }
        public bool verbose { get; set; }
        public Dictionary<string, object>? config { get; set; }

        private static readonly string[] SENSITIVE_KEYS = new string[] {
            "bot_token", "streamer_token", "access_token", "refresh_token", "client_secret", "access_token_secret", "api_key", "streamer_cookies", "oauth_token"
        };

        public ConfigManager(string? config_file = null) {
            this.verbose = false;

            // Prefer a repo-local config directory (.audiblezenbot at repository root) for easier local testing.
            try {
                var repoRoot = Directory.GetCurrentDirectory();
                var repoConfigDir = Path.Combine(repoRoot, ".audiblezenbot");
                var candidate = Path.Combine(repoConfigDir, config_file ?? "config.json");
                if (File.Exists(candidate)) {
                    this.ConfigDir = repoConfigDir;
                    this.ConfigFile = candidate;
                    this.config = Load();
                    // Startup diagnostic: log chosen config file and twitch client presence
                    try {
                        var twitchCfg = GetPlatformConfig("twitch");
                        var clientPresent = false;
                        var masked = "<missing>";
                        if (twitchCfg != null && twitchCfg.ContainsKey("client_id") && twitchCfg["client_id"] != null) {
                            var cv = twitchCfg["client_id"].ToString() ?? "";
                            clientPresent = !string.IsNullOrEmpty(cv);
                            if (clientPresent) masked = cv.Length > 8 ? cv.Substring(0,4) + "..." + cv.Substring(cv.Length-4) : cv;
                        }
                        var log = DateTime.UtcNow.ToString("o") + " [ConfigLoadDiag] chosenConfigFile=" + this.ConfigFile + " client_id_present=" + clientPresent + " client_id_masked=" + masked + "\n";
                        Console.WriteLine(log);
                        try { Directory.CreateDirectory(Path.Combine(this.ConfigDir, "logs")); File.AppendAllText(Path.Combine(this.ConfigDir, "logs", "oauth_diag.log"), log); } catch { }
                        // Also log which keys exist under platforms.twitch (do not log values)
                        try {
                            var raw = File.ReadAllText(this.ConfigFile);
                            var rootNode = JsonNode.Parse(raw) as JsonObject;
                            if (rootNode != null && rootNode.TryGetPropertyValue("platforms", out JsonNode? pnode) && pnode is JsonObject prow && prow.TryGetPropertyValue("twitch", out JsonNode? tnode) && tnode is JsonObject tObj) {
                                var keys = string.Join(',', tObj.Select(kv => kv.Key));
                                var klog = DateTime.UtcNow.ToString("o") + " [ConfigLoadDiag] twitch_keys=" + keys + "\n";
                                Console.WriteLine(klog);
                                try { File.AppendAllText(Path.Combine(this.ConfigDir, "logs", "oauth_diag.log"), klog); } catch { }
                            }
                        } catch { }
                    } catch { }
                    return;
                }
            } catch {
                // ignore and fall back to user profile
            }

            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            this.ConfigDir = Path.Combine(home, ".audiblezenbot");
            try { if (!Directory.Exists(this.ConfigDir)) Directory.CreateDirectory(this.ConfigDir); } catch { }
            this.ConfigFile = Path.Combine(this.ConfigDir, config_file ?? "config.json");
            this.config = Load();
            // Startup diagnostic for non-repo config path
            try {
                var twitchCfg = GetPlatformConfig("twitch");
                var clientPresent = false;
                var masked = "<missing>";
                if (twitchCfg != null && twitchCfg.ContainsKey("client_id") && twitchCfg["client_id"] != null) {
                    var cv = twitchCfg["client_id"].ToString() ?? "";
                    clientPresent = !string.IsNullOrEmpty(cv);
                    if (clientPresent) masked = cv.Length > 8 ? cv.Substring(0,4) + "..." + cv.Substring(cv.Length-4) : cv;
                }
                var log = DateTime.UtcNow.ToString("o") + " [ConfigLoadDiag] chosenConfigFile=" + this.ConfigFile + " client_id_present=" + clientPresent + " client_id_masked=" + masked + "\n";
                Console.WriteLine(log);
                try { Directory.CreateDirectory(Path.Combine(this.ConfigDir, "logs")); File.AppendAllText(Path.Combine(this.ConfigDir, "logs", "oauth_diag.log"), log); } catch { }
                // Also log which keys exist under platforms.twitch (do not log values)
                try {
                    var raw = File.ReadAllText(this.ConfigFile);
                    var rootNode = JsonNode.Parse(raw) as JsonObject;
                    if (rootNode != null && rootNode.TryGetPropertyValue("platforms", out JsonNode? pnode) && pnode is JsonObject prow && prow.TryGetPropertyValue("twitch", out JsonNode? tnode) && tnode is JsonObject tObj) {
                        var keys = string.Join(',', tObj.Select(kv => kv.Key));
                        var klog = DateTime.UtcNow.ToString("o") + " [ConfigLoadDiag] twitch_keys=" + keys + "\n";
                        Console.WriteLine(klog);
                        try { File.AppendAllText(Path.Combine(this.ConfigDir, "logs", "oauth_diag.log"), klog); } catch { }
                    }
                } catch { }
            } catch { }
        }
        public Dictionary<string, object>? Load() {
            lock (_fileLock) {
                try {
                    if (!File.Exists(this.ConfigFile)) return new Dictionary<string, object>();
                    var text = File.ReadAllText(this.ConfigFile);
                    // Debug: log raw config text (truncated) and whether it contains client_id
                    try {
                        var snippet = text.Length > 512 ? text.Substring(0, 512) : text;
                        var hasClientKey = text.Contains("\"client_id\"") || snippet.Contains("\"client_id\"");
                        var dbg = DateTime.UtcNow.ToString("o") + " [ConfigLoadRaw] file=" + this.ConfigFile + " len=" + text.Length + " has_client_id=" + hasClientKey + "\n";
                        Console.WriteLine(dbg);
                        try { Directory.CreateDirectory(Path.Combine(this.ConfigDir, "logs")); File.AppendAllText(Path.Combine(this.ConfigDir, "logs", "oauth_diag.log"), dbg); } catch { }
                    } catch { }
                    var root = System.Text.Json.Nodes.JsonNode.Parse(text, null, new System.Text.Json.JsonDocumentOptions { AllowTrailingCommas = true }) as JsonObject;
                    if (root != null) {
                        // Decrypt sensitive fields under platforms
                        if (root.TryGetPropertyValue("platforms", out JsonNode? platformsNode) && platformsNode is JsonObject platformsObj) {
                            foreach (var kv in platformsObj) {
                                if (kv.Value is JsonObject p) {
                                    foreach (var sk in SENSITIVE_KEYS) {
                                        if (p.TryGetPropertyValue(sk, out JsonNode? valNode) && valNode is JsonValue val && val.TryGetValue<string>(out var s) && !string.IsNullOrEmpty(s) && s.StartsWith("ENC:")) {
                                            try {
                                                var dec = core.secret_store.Secret_storeModule.UnprotectString(s);
                                                p[sk] = dec;
                                            } catch {
                                                p[sk] = string.Empty;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        var dict = JsonSerializer.Deserialize<Dictionary<string, object>>(root.ToJsonString());
                        return dict ?? new Dictionary<string, object>();
                    }
                } catch {
                }
                return new Dictionary<string, object>();
            }
        }

        public void Save() {
            lock (_fileLock) {
                try {
                    var opts = new JsonSerializerOptions { WriteIndented = true };
                    // Work on a JsonNode so we can encrypt sensitive fields before writing
                    JsonNode? root = JsonNode.Parse(JsonSerializer.Serialize(this.config ?? new Dictionary<string, object>()));
                    if (root == null) root = new JsonObject();
                    var rootObj = root as JsonObject;
                    if (!rootObj.ContainsKey("platforms")) rootObj["platforms"] = new JsonObject();
                    if (rootObj["platforms"] is JsonObject platformsObj) {
                        foreach (var kv in platformsObj) {
                            if (kv.Value is JsonObject p) {
                                foreach (var sk in SENSITIVE_KEYS) {
                                    if (p.TryGetPropertyValue(sk, out JsonNode? v) && v is JsonValue jv && jv.TryGetValue<string>(out var sval) && !string.IsNullOrEmpty(sval)) {
                                        // If not already encrypted, encrypt and store as ENC:...
                                        if (!sval.StartsWith("ENC:")) {
                                            try {
                                                var enc = core.secret_store.Secret_storeModule.ProtectString(sval);
                                                p[sk] = enc;
                                            } catch {
                                                // fallback: leave original
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    var text = root.ToJsonString(new JsonSerializerOptions { WriteIndented = true });
                    File.WriteAllText(this.ConfigFile, text);
                    // refresh in-memory
                    this.config = JsonSerializer.Deserialize<Dictionary<string, object>>(root.ToJsonString());
                } catch {
                }
            }
        }

        public void GetDefaultConfig() {
            lock (_fileLock) {
                this.config = new Dictionary<string, object>();
            }
        }

        public object? Get(string? key, object? @default = null) {
            if (string.IsNullOrEmpty(key)) return @default;
            lock (_fileLock) {
                try {
                    // Reload to ensure freshest view
                    this.config = Load();
                    var parts = key.Split('.');
                    object? cur = this.config;
                    foreach (var p in parts) {
                        if (cur is JsonElement je) {
                            if (je.TryGetProperty(p, out var v)) cur = v;
                            else return @default;
                        } else if (cur is IDictionary<string, object> dict) {
                            if (dict.ContainsKey(p)) cur = dict[p]; else return @default;
                        } else if (cur is Dictionary<string, object> sd) {
                            if (sd.ContainsKey(p)) cur = sd[p]; else return @default;
                        } else return @default;
                    }
                    return cur ?? @default;
                } catch {
                    return @default;
                }
            }
        }

        public void Set(string? key, object? value) {
            if (string.IsNullOrEmpty(key)) return;
            lock (_fileLock) {
                // reload latest
                this.config = Load();
                var keys = key.Split('.');
                var cfg = this.config ?? new Dictionary<string, object>();
                object cur = cfg;
                for (int i = 0; i < keys.Length - 1; i++) {
                    var k = keys[i];
                    if (cur is Dictionary<string, object> d) {
                        if (!d.ContainsKey(k) || !(d[k] is Dictionary<string, object>)) d[k] = new Dictionary<string, object>();
                        cur = d[k];
                    } else {
                        // can't navigate, create new
                        var nd = new Dictionary<string, object>();
                        if (cur is Dictionary<string, object> dd) {
                            dd[k] = nd;
                            cur = nd;
                        }
                    }
                }
                // set final key
                if (cur is Dictionary<string, object> finalDict) {
                    finalDict[keys[keys.Length - 1]] = value ?? "";
                }
                this.config = cfg;
                Save();
            }
        }

        public Dictionary<string, object>? GetPlatformConfig(string? platform) {
            if (string.IsNullOrEmpty(platform)) return new Dictionary<string, object>();
            lock (_fileLock) {
                try {
                    var cfg = Load();
                    if (cfg != null && cfg.ContainsKey("platforms")) {
                        // platforms may be a Dictionary<string, object> or a JsonElement from deserialization
                        var platformsObj = cfg["platforms"];
                        Dictionary<string, object>? platforms = null;
                        if (platformsObj is Dictionary<string, object> pdict) {
                            platforms = pdict;
                        } else if (platformsObj is System.Text.Json.JsonElement pe && pe.ValueKind == System.Text.Json.JsonValueKind.Object) {
                            try {
                                platforms = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(pe.GetRawText());
                            } catch {
                                platforms = null;
                            }
                        }
                        if (platforms != null && platforms.ContainsKey(platform)) {
                            // platform entry may also be JsonElement or Dictionary
                            var pentry = platforms[platform];
                            if (pentry is Dictionary<string, object> pd) {
                                return new Dictionary<string, object>(pd);
                            } else if (pentry is System.Text.Json.JsonElement pje && pje.ValueKind == System.Text.Json.JsonValueKind.Object) {
                                try {
                                    var pd2 = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(pje.GetRawText());
                                    if (pd2 != null) return new Dictionary<string, object>(pd2);
                                } catch {
                                    // fall through
                                }
                            }
                        }
                    }
                } catch {
                    return new Dictionary<string, object>();
                }
                return new Dictionary<string, object>();
            }
        }

        public void SetPlatformConfig(string? platform, string? key, object? value) {
            if (string.IsNullOrEmpty(platform) || string.IsNullOrEmpty(key)) return;
            lock (_fileLock) {
                try {
                    JsonNode? root = null;
                    if (File.Exists(this.ConfigFile)) {
                        var txt = File.ReadAllText(this.ConfigFile);
                        root = JsonNode.Parse(txt);
                    }
                    if (root == null) root = new JsonObject();
                    var platforms = root["platforms"] as JsonObject ?? new JsonObject();
                    root["platforms"] = platforms;
                    var p = platforms[platform] as JsonObject ?? new JsonObject();
                    platforms[platform] = p;
                    // If key is in sensitive list and value is string, encrypt before storing
                    if (SENSITIVE_KEYS != null && Array.Exists(SENSITIVE_KEYS, s => s == key) && value is string sv && !string.IsNullOrEmpty(sv)) {
                        try {
                            var enc = core.secret_store.Secret_storeModule.ProtectString(sv);
                            p[key] = enc;
                        } catch {
                            p[key] = sv;
                        }
                    } else {
                        // set value (attempt to preserve type)
                        if (value == null) p[key] = null; else if (value is long l) p[key] = l; else if (value is int i) p[key] = i; else if (value is double d) p[key] = d; else p[key] = value.ToString();
                    }
                    var opts = new JsonSerializerOptions { WriteIndented = true };
                    File.WriteAllText(this.ConfigFile, root.ToJsonString(opts));
                    // refresh in-memory config
                    this.config = Load();
                } catch {
                    // ignore write errors for now
                }
            }
        }

        public void Reset() {
            lock (_fileLock) {
                this.config = new Dictionary<string, object>();
                Save();
            }
        }

        public void MergePlatformStreamInfo(string? platform, Dictionary<string, object>? updates) {
            if (string.IsNullOrEmpty(platform) || updates == null) return;
            lock (_fileLock) {
                try {
                    // reload
                    JsonNode? root = null;
                    if (File.Exists(this.ConfigFile)) {
                        var txt = File.ReadAllText(this.ConfigFile);
                        root = JsonNode.Parse(txt);
                    }
                    if (root == null) root = new JsonObject();
                    var platforms = root["platforms"] as JsonObject ?? new JsonObject();
                    root["platforms"] = platforms;
                    var p = platforms[platform] as JsonObject ?? new JsonObject();
                    platforms[platform] = p;
                    var si = p["stream_info"] as JsonObject ?? new JsonObject();
                    p["stream_info"] = si;
                    foreach (var kv in updates) {
                        // simple shallow merge
                        si[kv.Key] = kv.Value == null ? null : JsonValue.Create(kv.Value.ToString());
                    }
                    var opts = new JsonSerializerOptions { WriteIndented = true };
                    File.WriteAllText(this.ConfigFile, root.ToJsonString(opts));
                    this.config = Load();
                } catch {
                }
            }
        }

        public string GetPlatformUserId(string? platform, string? accountType, string? @default = "") {
            try {
                var cfg = GetPlatformConfig(platform);
                if (cfg == null) return @default ?? "";
                // prefer accountType_user_id (e.g. streamer_user_id or bot_user_id)
                if (!string.IsNullOrEmpty(accountType)) {
                    var key = accountType + "_user_id";
                    if (cfg.ContainsKey(key) && cfg[key] != null) return cfg[key].ToString() ?? (@default ?? "");
                }
                // common fallbacks
                var fallbacks = new string[] { "streamer_user_id", "broadcaster_user_id", "user_id" };
                foreach (var k in fallbacks) {
                    if (cfg.ContainsKey(k) && cfg[k] != null) return cfg[k].ToString() ?? (@default ?? "");
                }
            } catch {
                // ignore
            }
            return @default ?? "";
        }
    }

}

