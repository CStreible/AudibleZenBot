using System;
using System.Threading.Tasks;
using System.Net;
using System.Text;

namespace get_twitch_token {
    public static class Get_twitch_tokenModule {
        // Original: def do_GET(self)
        public static void DoGET(HttpListenerContext context) {
            try {
                var req = context.Request;
                var qs = req.Url?.Query ?? string.Empty;
                var parsed = ParseQuery(qs);
                Console.WriteLine("OAuth callback received:");
                foreach (var kv in parsed) Console.WriteLine($"{kv.Key} = {kv.Value}");

                var respString = "<html><body><h2>Authentication complete. You may close this window.</h2></body></html>";
                var buffer = Encoding.UTF8.GetBytes(respString);
                context.Response.ContentLength64 = buffer.Length;
                context.Response.ContentType = "text/html";
                context.Response.OutputStream.Write(buffer, 0, buffer.Length);
                context.Response.OutputStream.Close();
            } catch (Exception ex) {
                Console.WriteLine($"DoGET handler error: {ex.Message}");
            }
        }

        // Original: def log_message(self, format, *args)
        public static void LogMessage(object? format) {
            Console.WriteLine(format?.ToString());
        }

        // Original: def main()
        public static void Main() {
            var prefix = "http://localhost:8888/";
            using var listener = new HttpListener();
            listener.Prefixes.Add(prefix);
            try {
                listener.Start();
            } catch (HttpListenerException ex) {
                Console.WriteLine($"Failed to start listener on {prefix}: {ex.Message}");
                return;
            }
            Console.WriteLine($"Listening for OAuth callback on {prefix} ...");
            try {
                var ctx = listener.GetContext();
                DoGET(ctx);
            } catch (Exception ex) {
                Console.WriteLine($"Listener error: {ex.Message}");
            } finally {
                try { listener.Stop(); } catch { }
            }
        }

        static System.Collections.Generic.Dictionary<string,string> ParseQuery(string query) {
            var result = new System.Collections.Generic.Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
            if (string.IsNullOrEmpty(query)) return result;
            var q = query.TrimStart('?');
            var parts = q.Split(new[] { '&' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var p in parts) {
                var kv = p.Split(new[] { '=' }, 2);
                var k = Uri.UnescapeDataString(kv[0]);
                var v = kv.Length > 1 ? Uri.UnescapeDataString(kv[1]) : string.Empty;
                result[k] = v;
            }
            return result;
        }

    }

    public class OAuthHandler {
        public object? path { get; set; }
        public object? send_respons { get; set; }
        public object? send_heade { get; set; }
        public object? end_header { get; set; }
        public object? wfile { get; set; }

        public OAuthHandler() {
            this.path = null;
            this.send_respons = null;
            this.send_heade = null;
            this.end_header = null;
            this.wfile = null;
        }

        // Original: def do_GET(self)
        public void DoGET() {
            // instance-level no-op for now
        }

        // Original: def log_message(self, format, *args)
        public void LogMessage(object? format) {
            Console.WriteLine(format?.ToString());
        }

        // Original: def main()
        public void Main() {
            Get_twitch_tokenModule.Main();
        }

    }

}

