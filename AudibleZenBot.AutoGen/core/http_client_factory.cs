using System;
using System.Net.Http;

namespace core.http_client {
    public static class HttpClientFactory {
        private static HttpClient? _sharedClient;
        private static readonly object _lock = new object();

        // Return a shared HttpClient configured via Http_sessionModule.MakeRetrySession.
        // If forceNew is true, returns a new instance instead of the shared one.
        public static HttpClient GetClient(int total = 3, double backoffFactor = 1.0, int[]? status_forcelist = null, bool forceNew = false) {
            if (forceNew) return core.http_session.Http_sessionModule.MakeRetrySession(total, backoffFactor, status_forcelist);
            if (_sharedClient != null) return _sharedClient;
            lock (_lock) {
                if (_sharedClient == null) {
                    _sharedClient = core.http_session.Http_sessionModule.MakeRetrySession(total, backoffFactor, status_forcelist);
                }
                return _sharedClient;
            }
        }

        // Dispose and reset the shared client (useful for tests)
        public static void ResetSharedClient() {
            lock (_lock) {
                try { _sharedClient?.Dispose(); } catch { }
                _sharedClient = null;
            }
        }
    }
}
