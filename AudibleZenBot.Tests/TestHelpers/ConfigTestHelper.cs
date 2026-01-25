using System;
using System.IO;

namespace AudibleZenBot.Tests {
    public static class ConfigTestHelper {
        // Creates a unique repo-local config file and initializes the ConfigModule with it.
        // Returns the generated config file name (relative to .audiblezenbot).
        public static string InitUniqueRepoConfig() {
            var cfgName = $"config_{Guid.NewGuid()}.json";
            try { Directory.CreateDirectory(".audiblezenbot"); } catch { }
            File.WriteAllText(Path.Combine(".audiblezenbot", cfgName), "{}");
            core.config.ConfigModule.Init(cfgName);
            // record for potential cleanup
            lock (_lock) {
                _createdFiles.Add(Path.Combine(".audiblezenbot", cfgName));
            }
            // ensure we attempt cleanup on process exit
            EnsureProcessExitHookRegistered();
            return cfgName;
        }

        private static readonly object _lock = new object();
        private static readonly System.Collections.Generic.List<string> _createdFiles = new System.Collections.Generic.List<string>();
        private static bool _exitHookRegistered = false;

        private static void EnsureProcessExitHookRegistered() {
            if (_exitHookRegistered) return;
            lock (_lock) {
                if (_exitHookRegistered) return;
                AppDomain.CurrentDomain.ProcessExit += (s, e) => CleanupGeneratedConfigs();
                _exitHookRegistered = true;
            }
        }

        // Delete all generated repo-local config files recorded by InitUniqueRepoConfig.
        // Safe to call multiple times.
        public static void CleanupGeneratedConfigs() {
            lock (_lock) {
                foreach (var p in _createdFiles) {
                    try { if (File.Exists(p)) File.Delete(p); } catch { }
                }
                _createdFiles.Clear();
            }
        }
    }
}
