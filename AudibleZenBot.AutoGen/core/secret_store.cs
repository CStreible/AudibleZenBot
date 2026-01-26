using System;
using System.Threading.Tasks;
using System.Security.Cryptography;
using System.Text;

namespace core.secret_store {
    public static class Secret_storeModule {
        // Original: def _to_blob(data: bytes)
        public static byte[] ToBlob(byte[]? data) {
            if (data == null || data.Length == 0) return Array.Empty<byte>();
            return data;
        }

        // Original: def protect_bytes(data: bytes)
        public static byte[] ProtectBytes(byte[]? data) {
            if (data == null || data.Length == 0) return Array.Empty<byte>();
            return ProtectedData.Protect(data, null, DataProtectionScope.CurrentUser);
        }

        // Original: def unprotect_bytes(data: bytes)
        public static byte[] UnprotectBytes(byte[]? data) {
            if (data == null || data.Length == 0) return Array.Empty<byte>();
            return ProtectedData.Unprotect(data, null, DataProtectionScope.CurrentUser);
        }

        // Original: def protect_string(plain: str)
        public static string ProtectString(string? plain) {
            if (string.IsNullOrEmpty(plain)) return string.Empty;
            var bytes = Encoding.UTF8.GetBytes(plain);
            var prot = ProtectBytes(bytes);
            return "ENC:" + Convert.ToBase64String(prot);
        }

        // Original: def unprotect_string(enc: str)
        public static string UnprotectString(string? enc) {
            if (string.IsNullOrEmpty(enc)) return string.Empty;
            if (!enc.StartsWith("ENC:")) return enc ?? string.Empty;
            try {
                var b = Convert.FromBase64String(enc.Substring(4));
                var plain = UnprotectBytes(b);
                return Encoding.UTF8.GetString(plain);
            } catch {
                return string.Empty;
            }
        }

    }

    public class DATA_BLOB {

        public DATA_BLOB() {
        }

        // Original: def _to_blob(data: bytes)
        public byte[] ToBlob(byte[]? data) {
            return Secret_storeModule.ToBlob(data);
        }

        // Original: def protect_bytes(data: bytes)
        public byte[] ProtectBytes(byte[]? data) {
            return Secret_storeModule.ProtectBytes(data);
        }

        // Original: def unprotect_bytes(data: bytes)
        public byte[] UnprotectBytes(byte[]? data) {
            return Secret_storeModule.UnprotectBytes(data);
        }

        // Original: def protect_string(plain: str)
        public string ProtectString(string? plain) {
            return Secret_storeModule.ProtectString(plain);
        }

        // Original: def unprotect_string(enc: str)
        public string UnprotectString(string? enc) {
            return Secret_storeModule.UnprotectString(enc);
        }

    }

}

