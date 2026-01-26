using System;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace AudibleZenBot.Tests {
    public class MockHttpHandler : HttpMessageHandler {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _responder;
        public MockHttpHandler(Func<HttpRequestMessage, HttpResponseMessage> responder) {
            _responder = responder ?? throw new ArgumentNullException(nameof(responder));
        }
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) {
            return Task.FromResult(_responder(request));
        }
    }
}
