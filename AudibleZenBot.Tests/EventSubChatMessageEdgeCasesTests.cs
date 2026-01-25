using System;
using System.IO;
using System.Threading.Tasks;
using Xunit;

namespace AudibleZenBot.Tests {
    public class EventSubChatMessageEdgeCasesTests {

        [Fact]
        public async Task MissingMessageField_DoesNotInvoke_OnMessageReceived() {
            ConfigTestHelper.InitUniqueRepoConfig();

            var payload = @"{
  \"metadata\": { \"message_type\": \"notification\" },
  \"payload\": {
    \"subscription\": { \"type\": \"channel.chat.message\", \"version\": \"1\" },
    \"event\": {
      \"user_name\": \"someuser\",
      \"user_login\": \"someuser\"
    }
  }
}";

            var sw = new StringWriter();
            var orig = Console.Out;
            Console.SetOut(sw);
            try {
                await platform_connectors.twitch_connector.Twitch_connectorModule.HandleMessage(payload).ConfigureAwait(false);
            } finally {
                Console.SetOut(orig);
            }

            var output = sw.ToString();
            Assert.Contains("OnEvent: type=channel.chat.message user=someuser", output);
            Assert.DoesNotContain("OnMessageReceived:", output);
        }

        [Fact]
        public async Task EmotesAndBadges_InMessage_InvokeHandlers() {
            ConfigTestHelper.InitUniqueRepoConfig();

            var payload = @"{
  \"metadata\": { \"message_type\": \"notification\" },
  \"payload\": {
    \"subscription\": { \"type\": \"channel.chat.message\", \"version\": \"1\" },
    \"event\": {
      \"user_name\": \"moduser\",
      \"user_login\": \"moduser\",
      \"message\": \"Hello Kappa\",
      \"emotes\": [{ \"start\": 6, \"end\": 10, \"id\": \"25\" }],
      \"badges\": [{ \"id\": \"moderator\", \"version\": \"1\" }]
    }
  }
}";

            var sw = new StringWriter();
            var orig = Console.Out;
            Console.SetOut(sw);
            try {
                await platform_connectors.twitch_connector.Twitch_connectorModule.HandleMessage(payload).ConfigureAwait(false);
            } finally {
                Console.SetOut(orig);
            }

            var output = sw.ToString();
            Assert.Contains("OnMessageReceived: [moduser] Hello Kappa", output);
            Assert.Contains("OnMessageReceivedWithMetadata: [moduser] Hello Kappa", output);
        }

        [Fact]
        public async Task AnonymousUser_HandledGracefully() {
            ConfigTestHelper.InitUniqueRepoConfig();

            var payload = @"{
  \"metadata\": { \"message_type\": \"notification\" },
  \"payload\": {
    \"subscription\": { \"type\": \"channel.chat.message\", \"version\": \"1\" },
    \"event\": {
      \"is_anonymous\": true,
      \"message\": \"Anonymous hello\"
    }
  }
}";

            var sw = new StringWriter();
            var orig = Console.Out;
            Console.SetOut(sw);
            try {
                await platform_connectors.twitch_connector.Twitch_connectorModule.HandleMessage(payload).ConfigureAwait(false);
            } finally {
                Console.SetOut(orig);
            }

            var output = sw.ToString();
            // username may be empty when anonymous; ensure handlers still invoked
            Assert.Contains("OnMessageReceived:", output);
            Assert.Contains("Anonymous hello", output);
        }

        [Fact]
        public async Task NullMessageField_DoesNotThrow_And_NoInvocation() {
            ConfigTestHelper.InitUniqueRepoConfig();

            var payload = @"{
  \"metadata\": { \"message_type\": \"notification\" },
  \"payload\": {
    \"subscription\": { \"type\": \"channel.chat.message\", \"version\": \"1\" },
    \"event\": {
      \"user_name\": \"nulluser\",
      \"message\": null
    }
  }
}";

            var sw = new StringWriter();
            var orig = Console.Out;
            Console.SetOut(sw);
            try {
                await platform_connectors.twitch_connector.Twitch_connectorModule.HandleMessage(payload).ConfigureAwait(false);
            } finally {
                Console.SetOut(orig);
            }

            var output = sw.ToString();
            Assert.Contains("OnEvent: type=channel.chat.message user=nulluser", output);
            Assert.DoesNotContain("OnMessageReceived: [nulluser]", output);
        }
    }
}
