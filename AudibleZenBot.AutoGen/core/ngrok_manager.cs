using System;
using System.Threading.Tasks;

namespace core.ngrok_manager {
    public static class Ngrok_managerModule {
        // Original: def __init__(self, *args, **kwargs)
        public static void Init() {
            // TODO: implement
        }

        // Original: def __init__(self, config=None)
        public static void Init(object? config = null) {
            // TODO: implement
        }

        // Original: def set_auth_token(self, token: str)
        public static void SetAuthToken(string? token) {
            // TODO: implement
        }

        // Original: def is_available(self)
        public static void IsAvailable() {
            // TODO: implement
        }

        // Original: def start_tunnel(self, port: int, protocol: str = 'http', name: str = None)
        public static void StartTunnel(int? port, string? protocol = null, string? name = null) {
            // TODO: implement
        }

        // Original: def start_tunnel_thread()
        public static void StartTunnelThread() {
            // TODO: implement
        }

        // Original: def hidden_popen(*args, **kwargs)
        public static void HiddenPopen() {
            // TODO: implement
        }

        // Original: def stop_tunnel(self, port: int)
        public static void StopTunnel(int? port) {
            // TODO: implement
        }

        // Original: def stop_all_tunnels(self)
        public static void StopAllTunnels() {
            // TODO: implement
        }

        // Original: def kill_existing_processes(self)
        public static void KillExistingProcesses() {
            // TODO: implement
        }

        // Original: def get_tunnel_url(self, port: int)
        public static void GetTunnelUrl(int? port) {
            // TODO: implement
        }

        // Original: def get_all_tunnels(self)
        public static void GetAllTunnels() {
            // TODO: implement
        }

        // Original: def is_tunnel_active(self, port: int)
        public static void IsTunnelActive(int? port) {
            // TODO: implement
        }

        // Original: def start_monitoring(self)
        public static void StartMonitoring() {
            // TODO: implement
        }

        // Original: def stop_monitoring(self)
        public static void StopMonitoring() {
            // TODO: implement
        }

        // Original: def _monitor_tunnels(self)
        public static void MonitorTunnels() {
            // TODO: implement
        }

        // Original: def get_status_summary(self)
        public static void GetStatusSummary() {
            // TODO: implement
        }

        // Original: def cleanup(self)
        public static void Cleanup() {
            // TODO: implement
        }

        // Original: def get_platform_tunnel_requirement(platform: str)
        public static void GetPlatformTunnelRequirement(string? platform) {
            // TODO: implement
        }

    }

    public class _HiddenPopen {


        // Original: def __init__(self, *args, **kwargs)
        public _HiddenPopen() {
            // TODO: implement constructor
        }

    }

    public class NgrokManager {
        public bool? config { get; set; }
        public object? kill_existing_processe { get; set; }
        public object? tunnels { get; set; }
        public object? ngrok_process { get; set; }
        public object? @lock { get; set; }
        public bool? monitoring { get; set; }
        public bool? monitor_thread { get; set; }
        public bool? pyngrok_available { get; set; }
        public bool? auth_token { get; set; }
        public object? set_auth_toke { get; set; }
        public object? status_changed { get; set; }
        public object? is_availabl { get; set; }
        public object? tunnel_error { get; set; }
        public object? tunnel_started { get; set; }
        public object? start_monitorin { get; set; }
        public object? tunnel_stopped { get; set; }
        public object? stop_monitorin { get; set; }
        public object? stop_tunne { get; set; }
        public object? stop_all_tunnel { get; set; }


        // Original: def __init__(self, config=None)
        public NgrokManager(object? config = null) {
            // TODO: implement constructor
            this.config = null;
            this.kill_existing_processe = null;
            this.tunnels = null;
            this.ngrok_process = null;
            this.@lock = null;
            this.monitoring = null;
            this.monitor_thread = null;
            this.pyngrok_available = null;
            this.auth_token = null;
            this.set_auth_toke = null;
            this.status_changed = null;
            this.is_availabl = null;
            this.tunnel_error = null;
            this.tunnel_started = null;
            this.start_monitorin = null;
            this.tunnel_stopped = null;
            this.stop_monitorin = null;
            this.stop_tunne = null;
            this.stop_all_tunnel = null;
        }

        // Original: def set_auth_token(self, token: str)
        public void SetAuthToken(string? token) {
            // TODO: implement
        }

        // Original: def is_available(self)
        public void IsAvailable() {
            // TODO: implement
        }

        // Original: def start_tunnel(self, port: int, protocol: str = 'http', name: str = None)
        public void StartTunnel(int? port, string? protocol = null, string? name = null) {
            // TODO: implement
        }

        // Original: def start_tunnel_thread()
        public void StartTunnelThread() {
            // TODO: implement
        }

        // Original: def hidden_popen(*args, **kwargs)
        public void HiddenPopen() {
            // TODO: implement
        }

        // Original: def stop_tunnel(self, port: int)
        public void StopTunnel(int? port) {
            // TODO: implement
        }

        // Original: def stop_all_tunnels(self)
        public void StopAllTunnels() {
            // TODO: implement
        }

        // Original: def kill_existing_processes(self)
        public void KillExistingProcesses() {
            // TODO: implement
        }

        // Original: def get_tunnel_url(self, port: int)
        public void GetTunnelUrl(int? port) {
            // TODO: implement
        }

        // Original: def get_all_tunnels(self)
        public void GetAllTunnels() {
            // TODO: implement
        }

        // Original: def is_tunnel_active(self, port: int)
        public void IsTunnelActive(int? port) {
            // TODO: implement
        }

        // Original: def start_monitoring(self)
        public void StartMonitoring() {
            // TODO: implement
        }

        // Original: def stop_monitoring(self)
        public void StopMonitoring() {
            // TODO: implement
        }

        // Original: def _monitor_tunnels(self)
        public void MonitorTunnels() {
            // TODO: implement
        }

        // Original: def get_status_summary(self)
        public void GetStatusSummary() {
            // TODO: implement
        }

        // Original: def cleanup(self)
        public void Cleanup() {
            // TODO: implement
        }

        // Original: def get_platform_tunnel_requirement(platform: str)
        public void GetPlatformTunnelRequirement(string? platform) {
            // TODO: implement
        }

    }

}

