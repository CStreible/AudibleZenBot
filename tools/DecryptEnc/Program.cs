// See https://aka.ms/new-console-template for more information
using System;
using System.IO;
using System.Text;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Text.Json;

namespace DecryptEnc {
	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
	internal struct DATA_BLOB {
		public int cbData;
		public IntPtr pbData;
	}

	internal static class NativeMethods {
		[DllImport("crypt32.dll", SetLastError = true, CharSet = CharSet.Auto)]
		internal static extern bool CryptUnprotectData(ref DATA_BLOB pDataIn, StringBuilder? ppszDataDescr, IntPtr pOptionalEntropy, IntPtr pvReserved, IntPtr pPromptStruct, int dwFlags, ref DATA_BLOB pDataOut);

		[DllImport("kernel32.dll", SetLastError = true)]
		internal static extern IntPtr LocalFree(IntPtr hMem);
	}

	class Program {
		static byte[] UnprotectBytes(byte[] encrypted) {
			if (encrypted == null || encrypted.Length == 0) return Array.Empty<byte>();
			var inBlob = new DATA_BLOB();
			inBlob.cbData = encrypted.Length;
			inBlob.pbData = Marshal.AllocHGlobal(encrypted.Length);
			Marshal.Copy(encrypted, 0, inBlob.pbData, encrypted.Length);
			var outBlob = new DATA_BLOB();
			try {
				bool ok = NativeMethods.CryptUnprotectData(ref inBlob, null, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 0, ref outBlob);
				if (!ok) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
				var result = new byte[outBlob.cbData];
				Marshal.Copy(outBlob.pbData, result, 0, outBlob.cbData);
				return result;
			} finally {
				if (inBlob.pbData != IntPtr.Zero) Marshal.FreeHGlobal(inBlob.pbData);
				if (outBlob.pbData != IntPtr.Zero) NativeMethods.LocalFree(outBlob.pbData);
			}
		}

		static string UnprotectString(string enc) {
			if (string.IsNullOrEmpty(enc)) return string.Empty;
			if (!enc.StartsWith("ENC:")) return enc;
			byte[] b;
			try {
				b = Convert.FromBase64String(enc.Substring(4));
			} catch (FormatException fex) {
				return $"<invalid-base64: {fex.Message}>";
			}
			try {
				var p = UnprotectBytes(b);
				return Encoding.UTF8.GetString(p);
			} catch (Exception ex) {
				return $"<error: {ex.Message}>";
			}
		}

		static int Main(string[] args) {
			var root = Directory.GetCurrentDirectory();
			Console.WriteLine($"CWD: {root}");
			var cfgPath = Path.Combine(root, ".audiblezenbot", "config.json");
			if (!File.Exists(cfgPath)) {
				Console.WriteLine($"Config file not found: {cfgPath}");
				return 1;
			}
			var text = File.ReadAllText(cfgPath);
			using var doc = JsonDocument.Parse(text);
			var sensitive = new List<(string path, string val)>();
			void Scan(JsonElement el, string path) {
				switch (el.ValueKind) {
					case JsonValueKind.Object:
						foreach (var prop in el.EnumerateObject()) Scan(prop.Value, path == "" ? prop.Name : path + "." + prop.Name);
						break;
					case JsonValueKind.Array:
						int i = 0;
						foreach (var item in el.EnumerateArray()) { Scan(item, path + $"[{i}]"); i++; }
						break;
					case JsonValueKind.String:
						var s = el.GetString();
						if (!string.IsNullOrEmpty(s) && s.StartsWith("ENC:")) sensitive.Add((path, s));
						break;
				}
			}
			Scan(doc.RootElement, "");
			Console.WriteLine($"Found {sensitive.Count} ENC entries");
			foreach (var (p, v) in sensitive) {
				var dec = UnprotectString(v);
				Console.WriteLine($"{p} => {dec}");
			}
			return 0;
		}
	}
}
