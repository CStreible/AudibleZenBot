using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using Xunit;

namespace AudibleZenBot.Tests {
    public class TwitchEventSubSubscriptionTests {

        [Fact]
        public async Task CreateEventSub_Skips_When_ExistingWithSameSession() {
            ConfigTestHelper.InitUniqueRepoConfig();
            var platform = core.platforms.PlatformIds.Twitch;
            core.config.ConfigModule.SetPlatformConfig(platform, "oauth_token", "dummy-token");
            core.config.ConfigModule.SetPlatformConfig(platform, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(platform, "broadcaster_id", "12345");

            int postCalls = 0, deleteCalls = 0, getCalls = 0;

            var handler = new MockHttpHandler(req => {
                getCalls++;
                if (req.Method == HttpMethod.Get && req.RequestUri != null && req.RequestUri.AbsoluteUri.Contains("eventsub/subscriptions")) {
                    var listJson = JsonSerializer.Serialize(new {
                        data = new[] {
                            new {
                                id = "existing1",
                                type = "channel.follow",
                                condition = new { broadcaster_user_id = "12345" },
                                transport = new { session_id = "session-abc" }
                            }
                        }
                    });
                    return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(listJson) };
                }
                if (req.Method == HttpMethod.Delete) { deleteCalls++; return new HttpResponseMessage(HttpStatusCode.NoContent); }
                if (req.Method == HttpMethod.Post) { postCalls++; return new HttpResponseMessage(HttpStatusCode.Created) { Content = new StringContent("created") }; }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });

            core.http_session.Http_sessionModule.ClientFactory = () => new HttpClient(handler);
            try {
                // set session id directly to avoid triggering background subscribe tasks
                var tset = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
                var f = tset.GetField("_eventSubSessionId", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
                f!.SetValue(null, "session-abc");

                // call private CreateEventSubSubscriptionIfNotExistsAsync for a single type via reflection
                var t = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
                var m = t.GetMethod("CreateEventSubSubscriptionIfNotExistsAsync", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
                Assert.NotNull(m);
                var task = (System.Threading.Tasks.Task)m!.Invoke(null, new object[] { "channel.follow", "12345", "dummy-token", "dummy-client" });
                await task.ConfigureAwait(false);

                Assert.Equal(0, postCalls);
                Assert.Equal(0, deleteCalls);
                Assert.True(getCalls >= 1);
            } finally {
                core.http_session.Http_sessionModule.ClientFactory = null;
            }
        }

        [Fact]
        public async Task CreateEventSub_Creates_When_NoneExists() {
            ConfigTestHelper.InitUniqueRepoConfig();
            var platform = core.platforms.PlatformIds.Twitch;
            core.config.ConfigModule.SetPlatformConfig(platform, "oauth_token", "dummy-token");
            core.config.ConfigModule.SetPlatformConfig(platform, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(platform, "broadcaster_id", "12345");

            int postCalls = 0, deleteCalls = 0, getCalls = 0;

            var handler = new MockHttpHandler(req => {
                getCalls++;
                if (req.Method == HttpMethod.Get && req.RequestUri != null && req.RequestUri.AbsoluteUri.Contains("eventsub/subscriptions")) {
                    var listJson = JsonSerializer.Serialize(new { data = new object[] { } });
                    return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(listJson) };
                }
                if (req.Method == HttpMethod.Delete) { deleteCalls++; return new HttpResponseMessage(HttpStatusCode.NoContent); }
                if (req.Method == HttpMethod.Post) { postCalls++; return new HttpResponseMessage(HttpStatusCode.Created) { Content = new StringContent("created") }; }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });

            core.http_session.Http_sessionModule.ClientFactory = () => new HttpClient(handler);
            try {
                var tset = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
                var f = tset.GetField("_eventSubSessionId", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
                f!.SetValue(null, "session-xyz");

                var t = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
                var m = t.GetMethod("CreateEventSubSubscriptionIfNotExistsAsync", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
                Assert.NotNull(m);
                var task = (System.Threading.Tasks.Task)m!.Invoke(null, new object[] { "channel.follow", "12345", "dummy-token", "dummy-client" });
                await task.ConfigureAwait(false);

                Assert.True(postCalls >= 1, "expected post to create subscription");
                Assert.Equal(0, deleteCalls);
                Assert.True(getCalls >= 1);
            } finally {
                core.http_session.Http_sessionModule.ClientFactory = null;
            }
        }

        [Fact]
        public async Task CreateEventSub_DeletesAndRecreates_When_SessionDiffers() {
            ConfigTestHelper.InitUniqueRepoConfig();
            var platform = core.platforms.PlatformIds.Twitch;
            core.config.ConfigModule.SetPlatformConfig(platform, "oauth_token", "dummy-token");
            core.config.ConfigModule.SetPlatformConfig(platform, "client_id", "dummy-client");
            core.config.ConfigModule.SetPlatformConfig(platform, "broadcaster_id", "12345");

            int postCalls = 0, deleteCalls = 0, getCalls = 0;

            var handler = new MockHttpHandler(req => {
                if (req.Method == HttpMethod.Get && req.RequestUri != null && req.RequestUri.AbsoluteUri.Contains("eventsub/subscriptions")) {
                    getCalls++;
                    var listJson = JsonSerializer.Serialize(new {
                        data = new[] {
                            new {
                                id = "sub123",
                                type = "channel.follow",
                                condition = new { broadcaster_user_id = "12345" },
                                transport = new { session_id = "old-session" }
                            }
                        }
                    });
                    return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(listJson) };
                }
                if (req.Method == HttpMethod.Delete) { deleteCalls++; return new HttpResponseMessage(HttpStatusCode.NoContent); }
                if (req.Method == HttpMethod.Post) { postCalls++; return new HttpResponseMessage(HttpStatusCode.Created) { Content = new StringContent("created") }; }
                return new HttpResponseMessage(HttpStatusCode.NotFound) { Content = new StringContent("not found") };
            });

            core.http_session.Http_sessionModule.ClientFactory = () => new HttpClient(handler);
            try {
                var tset = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
                var f = tset.GetField("_eventSubSessionId", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
                f!.SetValue(null, "session-abc");

                var t = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
                var m = t.GetMethod("CreateEventSubSubscriptionIfNotExistsAsync", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
                Assert.NotNull(m);
                var task = (System.Threading.Tasks.Task)m!.Invoke(null, new object[] { "channel.follow", "12345", "dummy-token", "dummy-client" });
                await task.ConfigureAwait(false);

                Assert.True(deleteCalls >= 1, "expected delete to be attempted");
                Assert.True(postCalls >= 1, "expected post to be attempted");
                Assert.True(getCalls >= 1);
            } finally {
                core.http_session.Http_sessionModule.ClientFactory = null;
            }
        }
    }
}
