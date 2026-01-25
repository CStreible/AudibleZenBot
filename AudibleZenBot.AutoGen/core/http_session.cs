using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Generic;

namespace core.http_session {
    public static class Http_sessionModule {
        // Optional test hook: if set, this factory will be used to create HttpClient instances.
        public static Func<HttpClient>? ClientFactory { get; set; }
        // Original: def make_retry_session(total: int = 3, backoff_factor: float = 1.0, status_forcelist=(429, 500, 502, 503, 504)
        public static HttpClient MakeRetrySession(int total = 3, double backoff_factor = 1.0, int[]? status_forcelist = null) {
            if (ClientFactory != null) return ClientFactory();
            // Build a new HttpClient with a RetryHandler to avoid recursion into HttpClientFactory.
            var statuses = status_forcelist ?? new int[] { 429, 500, 502, 503, 504 };
            var inner = new HttpClientHandler();
            var retryHandler = new RetryHandler(inner, total, backoff_factor, statuses);
            var client = new HttpClient(retryHandler, disposeHandler: true);
            // Set reasonable defaults similar to requests.Session
            client.Timeout = TimeSpan.FromSeconds(100);
            return client;
        }

        private class RetryHandler : DelegatingHandler {
            private readonly int _maxRetries;
            private readonly double _backoffFactor;
            private readonly HashSet<int> _statusForcelist;

            public RetryHandler(HttpMessageHandler innerHandler, int maxRetries, double backoffFactor, int[] statusForcelist) : base(innerHandler) {
                _maxRetries = Math.Max(0, maxRetries);
                _backoffFactor = Math.Max(0.0, backoffFactor);
                _statusForcelist = new HashSet<int>(statusForcelist ?? Array.Empty<int>());
            }

            protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) {
                HttpResponseMessage? response = null;
                for (int attempt = 0; attempt <= _maxRetries; attempt++) {
                    try {
                        response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);

                        if (response != null && !_statusForcelist.Contains((int)response.StatusCode)) {
                            return response;
                        }
                    } catch (HttpRequestException) {
                        // treat as transient and retry
                    }

                    if (attempt == _maxRetries) {
                        break;
                    }

                    // dispose intermediate response before retrying
                    response?.Dispose();

                    // exponential backoff: backoff_factor * (2 ^ attempt) seconds
                    var delayMs = (int)(1000.0 * _backoffFactor * Math.Pow(2, attempt));
                    if (delayMs > 0) await Task.Delay(delayMs, cancellationToken).ConfigureAwait(false);
                }

                // If we have a response (last attempt), return it or throw if null
                if (response != null) return response;
                throw new HttpRequestException("Request failed after retries.");
            }
        }

    }

}

