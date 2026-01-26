using System;
using System.Threading.Tasks;

namespace core.connector_utils {
    public static class ConnectorUtils {
        // Ensure we have an access token for the platform. If missing, initiate interactive auth and wait briefly.
        public static async Task<string?> EnsureAccessTokenAsync(string platform, int waitSeconds = 2) {
            try {
                var handler = new core.oauth_handler.OAuthHandler();
                var token = await handler.GetAccessTokenAsync(platform).ConfigureAwait(false);
                if (string.IsNullOrEmpty(token)) {
                    Console.WriteLine($"EnsureAccessTokenAsync: no token, initiating interactive authenticate for {platform}");
                    handler.Authenticate(platform);
                    await Task.Delay(TimeSpan.FromSeconds(waitSeconds)).ConfigureAwait(false);
                    token = await handler.GetAccessTokenAsync(platform).ConfigureAwait(false);
                }
                return token;
            } catch (Exception ex) {
                Console.WriteLine($"EnsureAccessTokenAsync exception for {platform}: {ex.Message}");
                return null;
            }
        }
    }
}
