using System;
using System.Net.Http;
using System.Threading.Tasks;

namespace core.http_retry {
    public static class HttpRetry {
        public static async Task<HttpResponseMessage> GetWithRetriesAsync(HttpClient http, string url, int maxAttempts = 3) {
            var attempt = 0;
            while (true) {
                attempt++;
                try {
                    var resp = await http.GetAsync(url).ConfigureAwait(false);
                    if (resp.IsSuccessStatusCode) return resp;

                    if ((int)resp.StatusCode == 429 || ((int)resp.StatusCode >= 500 && attempt < maxAttempts)) {
                        if (resp.Headers.TryGetValues("Retry-After", out var vals)) {
                            var ra = vals is null ? null : System.Linq.Enumerable.FirstOrDefault(vals);
                            if (!string.IsNullOrEmpty(ra) && int.TryParse(ra, out var secs)) {
                                await Task.Delay(TimeSpan.FromSeconds(secs)).ConfigureAwait(false);
                            } else {
                                var jitter = Random.Shared.NextDouble() * 0.5;
                                var delay = Math.Pow(2, attempt) + jitter;
                                await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                            }
                        } else {
                            var jitter = Random.Shared.NextDouble() * 0.5;
                            var delay = Math.Pow(2, attempt) + jitter;
                            await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                        }
                        continue;
                    }
                    return resp;
                } catch (Exception) {
                    if (attempt >= maxAttempts) throw;
                    var jitter = Random.Shared.NextDouble() * 0.5;
                    var delay = Math.Pow(2, attempt) + jitter;
                    await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                }
            }
        }

        public static async Task<HttpResponseMessage> PostWithRetriesAsync(HttpClient http, string url, HttpContent content, int maxAttempts = 3) {
            var attempt = 0;
            while (true) {
                attempt++;
                try {
                    var resp = await http.PostAsync(url, content).ConfigureAwait(false);
                    if (resp.IsSuccessStatusCode) return resp;

                    if ((int)resp.StatusCode == 429 || ((int)resp.StatusCode >= 500 && attempt < maxAttempts)) {
                        if (resp.Headers.TryGetValues("Retry-After", out var vals)) {
                            var ra = vals is null ? null : System.Linq.Enumerable.FirstOrDefault(vals);
                            if (!string.IsNullOrEmpty(ra) && int.TryParse(ra, out var secs)) {
                                await Task.Delay(TimeSpan.FromSeconds(secs)).ConfigureAwait(false);
                            } else {
                                var jitter = Random.Shared.NextDouble() * 0.5;
                                var delay = Math.Pow(2, attempt) + jitter;
                                await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                            }
                        } else {
                            var jitter = Random.Shared.NextDouble() * 0.5;
                            var delay = Math.Pow(2, attempt) + jitter;
                            await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                        }
                        continue;
                    }
                    return resp;
                } catch (Exception) {
                    if (attempt >= maxAttempts) throw;
                    var jitter = Random.Shared.NextDouble() * 0.5;
                    var delay = Math.Pow(2, attempt) + jitter;
                    await Task.Delay(TimeSpan.FromSeconds(delay)).ConfigureAwait(false);
                }
            }
        }
    }
}
