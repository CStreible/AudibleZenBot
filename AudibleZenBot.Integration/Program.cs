// See https://aka.ms/new-console-template for more information
using System;
using System.Threading.Tasks;
using core.oauth_handler;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;

class Program {
	static async Task<int> Main(string[] args) {
		Console.WriteLine("Starting OAuth integration runner...");

		var handler = new OAuthHandler();

		handler.auth_failed = new Action<string, string>((platform, msg) => {
			Console.WriteLine($"AUTH FAILED [{platform}]: {msg}");
		});

		handler.auth_completed = new Action<string, string>((platform, token) => {
			Console.WriteLine($"AUTH COMPLETED [{platform}]: token length={token?.Length}");
			try {
				var cfgDir = Path.Combine(Directory.GetCurrentDirectory(), ".audiblezenbot");
				var cfgPath = Path.Combine(cfgDir, "config.json");
				if (!Directory.Exists(cfgDir)) Directory.CreateDirectory(cfgDir);
				JsonNode? root = null;
				if (File.Exists(cfgPath)) {
					root = JsonNode.Parse(File.ReadAllText(cfgPath));
				} else {
					root = new JsonObject();
				}
				if (root == null) root = new JsonObject();
				var platforms = root["platforms"] as JsonObject ?? new JsonObject();
				root["platforms"] = platforms;
				var p = platforms[platform] as JsonObject ?? new JsonObject();
				platforms[platform] = p;
				p["oauth_token"] = token;
				var epoch = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
				p["bot_token_timestamp"] = epoch;
				p["streamer_token_timestamp"] = epoch;
				File.WriteAllText(cfgPath, root.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
				Console.WriteLine($"Persisted token to: {cfgPath}");
			} catch (Exception ex) {
				Console.WriteLine($"Failed to persist token: {ex.Message}");
			}
		});

		Console.WriteLine("Launching Authenticate(\"twitch\") — a browser will open for OAuth. Complete the flow to return the token.");
		var platform = core.platforms.PlatformIds.Twitch;
		handler.Authenticate(platform);

		// Keep process alive to wait for callback (max 5 minutes)
		await Task.Delay(TimeSpan.FromMinutes(5));
		Console.WriteLine("Integration runner exiting (timeout or completed).");
		return 0;
	}
}
