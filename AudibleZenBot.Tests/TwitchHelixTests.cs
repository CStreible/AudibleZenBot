using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using Xunit;

namespace AudibleZenBot.Tests {
    public class TwitchHelixTests {
        // Note: Config now prefers a canonical account id key when available.
        // Use "{accountType}_user_id" (e.g. "streamer_user_id" or "bot_user_id")
        // as the authoritative identifier; tests set both legacy and canonical keys
        // to ensure connectors that still read legacy keys continue to work.

        [Fact]
        public async Task SendChatMessage_Succeeds_On200() {
            ConfigTestHelper.InitUniqueRepoConfig();
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "oauth_token", "dummy-token");
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "broadcaster_id", "12345");
            // Also set canonical streamer_user_id so callers preferring canonical ids can find it
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "streamer_user_id", "12345");

            var handler = new MockHttpHandler(req => {
                if (req.Method == HttpMethod.Post && req.RequestUri != null && req.RequestUri.AbsoluteUri.Contains("helix/chat/messages")) {
                    return new HttpResponseMessage(HttpStatusCode.NoContent) { Content = new StringContent("") };
                }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });
            var client = new HttpClient(handler);

            var ok = await platform_connectors.twitch_connector.Twitch_connectorModule.SendChatMessageAsync(core.platforms.PlatformIds.Twitch, "hello world", client);
            Assert.True(ok);
        }

        [Fact]
        public async Task SendChatMessage_Fails_On401() {
            ConfigTestHelper.InitUniqueRepoConfig();
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "oauth_token", "dummy-token");
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "broadcaster_id", "12345");

            var handler = new MockHttpHandler(req => new HttpResponseMessage(HttpStatusCode.Unauthorized) { Content = new StringContent("unauthorized") });
            var client = new HttpClient(handler);

            var ok = await platform_connectors.twitch_connector.Twitch_connectorModule.SendChatMessageAsync(core.platforms.PlatformIds.Twitch, "hello world", client);
            Assert.False(ok);
        }

        [Fact]
        public async Task ResolveUserIdAsync_ReturnsId_OnValidJson() {
            ConfigTestHelper.InitUniqueRepoConfig();

            var json = JsonSerializer.Serialize(new { data = new[] { new { id = "99999", login = "botlogin" } } });
            var handler = new MockHttpHandler(req => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(json) });
            var client = new HttpClient(handler);

            var id = await platform_connectors.twitch_connector.Twitch_connectorModule.ResolveUserIdAsync("dummy-client", "dummy-token", "botlogin", client);
            Assert.Equal("99999", id);
        }

        [Fact]
        public async Task ResolveUserIdAsync_ReturnsNull_OnNonJson() {
            ConfigTestHelper.InitUniqueRepoConfig();

            var handler = new MockHttpHandler(req => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("not-a-json") });
            var client = new HttpClient(handler);

            var id = await platform_connectors.twitch_connector.Twitch_connectorModule.ResolveUserIdAsync("dummy-client", "dummy-token", "botlogin", client);
            Assert.Null(id);
        }

        [Fact]
        public async Task ResolveUserId_RetriesOn429ThenSucceeds() {
            var cfgName = $"config_{Guid.NewGuid()}.json";
            try { System.IO.Directory.CreateDirectory(".audiblezenbot"); } catch { }
            System.IO.File.WriteAllText(System.IO.Path.Combine(".audiblezenbot", cfgName), "{}");
            core.config.ConfigModule.Init(cfgName);

            int calls = 0;
            var json = JsonSerializer.Serialize(new { data = new[] { new { id = "555", login = "botlogin" } } });
            var handler = new MockHttpHandler(req => {
                calls++;
                if (req.Method == HttpMethod.Get) {
                    if (calls == 1) {
                        var r = new HttpResponseMessage((HttpStatusCode)429) { Content = new StringContent("rate limited") };
                        r.Headers.TryAddWithoutValidation("Retry-After", "0");
                        return r;
                    }
                    return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(json) };
                }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });
            var client = new HttpClient(handler);

            var id = await platform_connectors.twitch_connector.Twitch_connectorModule.ResolveUserIdAsync("dummy-client", "dummy-token", "botlogin", client);
            Assert.Equal("555", id);
            Assert.Equal(2, calls);
        }

        [Fact]
        public async Task SendChatMessage_RetriesOn5xxThenSucceeds() {
            try { System.IO.Directory.CreateDirectory(".audiblezenbot"); } catch { }
            System.IO.File.WriteAllText(System.IO.Path.Combine(".audiblezenbot", "config.json"), "{}");
            core.config.ConfigModule.Init();
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "oauth_token", "dummy-token");
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(core.platforms.PlatformIds.Twitch, "broadcaster_id", "99999");

            int calls = 0;
            var handler = new MockHttpHandler(req => {
                calls++;
                if (req.Method == HttpMethod.Post) {
                    if (calls == 1) {
                        var r = new HttpResponseMessage(HttpStatusCode.InternalServerError) { Content = new StringContent("err1") };
                        r.Headers.TryAddWithoutValidation("Retry-After", "0");
                        return r;
                    } else if (calls == 2) {
                        var r = new HttpResponseMessage((HttpStatusCode)502) { Content = new StringContent("err2") };
                        r.Headers.TryAddWithoutValidation("Retry-After", "0");
                        return r;
                    }
                    return new HttpResponseMessage(HttpStatusCode.NoContent) { Content = new StringContent("") };
                }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });
            var client = new HttpClient(handler);

            var ok = await platform_connectors.twitch_connector.Twitch_connectorModule.SendChatMessageAsync(core.platforms.PlatformIds.Twitch, "hello retry", client);
            Assert.True(ok);
            Assert.Equal(3, calls);
        }

        [Fact]
        public async Task RefreshToken_RetriesOn5xxThenSucceeds() {
            try { System.IO.Directory.CreateDirectory(".audiblezenbot"); } catch { }
            System.IO.File.WriteAllText(System.IO.Path.Combine(".audiblezenbot", "config.json"), "{}");
            core.config.ConfigModule.Init();

            // configure platform with refresh token and token_url
            var platform = core.platforms.PlatformIds.Twitch;
            core.config.ConfigModule.SetPlatformConfig(platform, "token_url", "https://id.twitch.tv/oauth2/token");
            core.config.ConfigModule.SetPlatformConfig(platform, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(platform, "client_secret", "dummy-secret");
            core.config.ConfigModule.SetPlatformConfig(platform, "refresh_token", "old-refresh");

            int calls = 0;
            var successJson = JsonSerializer.Serialize(new { access_token = "new-access", refresh_token = "new-refresh", expires_in = 3600 });
            var handler = new MockHttpHandler(req => {
                calls++;
                if (req.Method == HttpMethod.Post) {
                    if (calls < 3) {
                        var r = new HttpResponseMessage(HttpStatusCode.InternalServerError) { Content = new StringContent("err") };
                        r.Headers.TryAddWithoutValidation("Retry-After", "0");
                        return r;
                    }
                    return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(successJson) };
                }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });

            // Inject HttpClient factory
            core.http_session.Http_sessionModule.ClientFactory = () => new HttpClient(handler);
            try {
                var oauth = new core.oauth_handler.OAuthHandler();
                var ok = await oauth.RefreshTokenAsync(platform).ConfigureAwait(false);
                Assert.True(ok);
                var cfg = core.config.ConfigModule.GetPlatformConfig(platform);
                Assert.NotNull(cfg);
                cfg!.TryGetValue("oauth_token", out var oauthVal);
                cfg!.TryGetValue("refresh_token", out var refreshVal);
                Assert.Equal("new-access", oauthVal?.ToString());
                Assert.Equal("new-refresh", refreshVal?.ToString());
                Assert.True(calls >= 3);
            } finally {
                core.http_session.Http_sessionModule.ClientFactory = null;
            }
        }
    }
}
