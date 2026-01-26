using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using platform_connectors.twitch_connector;

namespace AudibleZenBot.Tests
{
    public class TwitchResolveUserIdTests
    {
        private class FakeHandler : HttpMessageHandler
        {
            private readonly HttpResponseMessage _response;
            public FakeHandler(string content, HttpStatusCode code = HttpStatusCode.OK)
            {
                _response = new HttpResponseMessage(code)
                {
                    Content = new StringContent(content)
                };
            }
            protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
            {
                return Task.FromResult(_response);
            }
        }

        [Fact]
        public async Task ResolveUserIdAsync_ReturnsId_WhenResponseContainsData()
        {
            var json = "{\"data\":[{\"id\":\"999\",\"login\":\"botlogin\"}]}";
            var handler = new FakeHandler(json);
            using var http = new HttpClient(handler);

            var id = await Twitch_connectorModule.ResolveUserIdAsync("dummy-client", "dummy-token", "botlogin", http).ConfigureAwait(false);

            Assert.Equal("999", id);
        }
    }
}
