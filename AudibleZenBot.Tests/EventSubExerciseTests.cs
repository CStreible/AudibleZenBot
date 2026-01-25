using System;
using System.Reflection;
using System.Threading.Tasks;
using Xunit;

namespace AudibleZenBot.Tests {
    public class EventSubExerciseTests {

        [Fact]
        public async Task HandleMessage_SessionWelcome_SetsSessionId() {
            // craft a session_welcome message
            var msg = @"{""metadata"": { ""message_type"": "session_welcome" }, ""payload"": { ""session"": { ""id"": "test-session-123" } } }";
            await platform_connectors.twitch_connector.Twitch_connectorModule.HandleMessage(msg).ConfigureAwait(false);

            var t = typeof(platform_connectors.twitch_connector.Twitch_connectorModule);
            var f = t.GetField("_eventSubSessionId", BindingFlags.NonPublic | BindingFlags.Static);
            Assert.NotNull(f);
            var val = f!.GetValue(null) as string;
            Assert.Equal("test-session-123", val);
        }

        [Fact]
        public async Task HandleMessage_Notification_Redemption_Completes() {
            var notification = @"{
  ""metadata"": { ""message_type"": "notification" },
  ""payload"": {
    ""subscription"": { ""type"": "channel.channel_points_custom_reward_redemption.add" },
    ""event"": {
      ""user_login"": "someuser",
      ""reward"": { ""title"": "Test Reward", ""cost"": 100 },
      ""user_input"": "hello"
    }
  }
}";
            // Should not throw
            await platform_connectors.twitch_connector.Twitch_connectorModule.HandleMessage(notification).ConfigureAwait(false);
            Assert.True(true);
        }
    }
}
