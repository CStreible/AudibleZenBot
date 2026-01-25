using System;
using System.Security.Cryptography;
using System.Text;

class Program {
    static int Main(string[] args) {
        if (args.Length >= 1 && args[0] == "--test-config") {
            try {
                var cwd = System.IO.Directory.GetCurrentDirectory();
                var path = System.IO.Path.Combine(cwd, ".audiblezenbot", "config.json");
                Console.WriteLine("Testing config at: " + path);
                var text = System.IO.File.ReadAllText(path);
                var root = System.Text.Json.Nodes.JsonNode.Parse(text) as System.Text.Json.Nodes.JsonObject;
                if (root == null) { Console.WriteLine("Parse failed: root null"); return 3; }
                var sNodes = new string[] { "client_secret", "oauth_token" };
                if (root.TryGetPropertyValue("platforms", out var platformsNode) && platformsNode is System.Text.Json.Nodes.JsonObject platformsObj) {
                    foreach (var kv in platformsObj) {
                        try {
                            if (kv.Value is System.Text.Json.Nodes.JsonObject p) {
                                foreach (var sk in sNodes) {
                                    try {
                                        if (p.TryGetPropertyValue(sk, out var valNode) && valNode is System.Text.Json.Nodes.JsonValue val && val.TryGetValue<string>(out var s) && !string.IsNullOrEmpty(s) && s.StartsWith("ENC:")) {
                                            Console.WriteLine($"Found ENC in {kv.Key}.{sk}");
                                        }
                                    } catch (Exception ex) {
                                        Console.WriteLine($"Error inspecting {kv.Key}.{sk}: {ex.Message}");
                                    }
                                }
                            }
                        } catch (Exception ex) {
                            Console.WriteLine($"Error processing platform {kv.Key}: {ex.Message}");
                        }
                    }
                }
                var dict = System.Text.Json.JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string, object>>(root.ToJsonString());
                if (dict != null && dict.ContainsKey("platforms")) {
                    Console.WriteLine("Deserialized platforms present.");
                    var platforms = dict["platforms"] as System.Collections.Generic.Dictionary<string, object>;
                    if (platforms != null && platforms.ContainsKey("twitch")) Console.WriteLine("twitch present in deserialized platforms.");
                } else {
                    Console.WriteLine("Deserialized dict missing platforms");
                }
                // Detect duplicate keys within each platform object by scanning property names
                if (root.TryGetPropertyValue("platforms", out var pnode) && pnode is System.Text.Json.Nodes.JsonObject pobj) {
                        var rx = new System.Text.RegularExpressions.Regex("\\\"([^\\\"]+)\\\"\\s*:", System.Text.RegularExpressions.RegexOptions.Compiled);
                    foreach (var kv in pobj) {
                        if (kv.Value is System.Text.Json.Nodes.JsonObject sub) {
                            var json = sub.ToJsonString();
                            var matches = rx.Matches(json);
                            var counts = new System.Collections.Generic.Dictionary<string,int>(StringComparer.Ordinal);
                            foreach (System.Text.RegularExpressions.Match m in matches) {
                                var name = m.Groups[1].Value;
                                counts[name] = counts.ContainsKey(name) ? counts[name]+1 : 1;
                            }
                            foreach (var c in counts) {
                                if (c.Value > 1) Console.WriteLine($"Platform {kv.Key} has duplicate property '{c.Key}' count={c.Value}");
                            }
                        }
                    }
                }
                return 0;
            } catch (Exception ex) {
                Console.Error.WriteLine("Error testing config: " + ex.ToString());
                return 4;
            }
        }
        if (args.Length < 2) {
            Console.Error.WriteLine("Usage: azb_dpapi_encrypt <plain1> <plain2>");
            return 2;
        }
        foreach (var s in new string[] { args[0], args[1] }) {
            try {
                var b = Encoding.UTF8.GetBytes(s);
                var p = ProtectedData.Protect(b, null, DataProtectionScope.CurrentUser);
                Console.WriteLine("ENC:" + Convert.ToBase64String(p));
            } catch (Exception ex) {
                Console.Error.WriteLine("Error: " + ex.Message);
                return 1;
            }
        }
        return 0;
    }
}
