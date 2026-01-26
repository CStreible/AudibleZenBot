using System;
using System.Threading.Tasks;

namespace core.overlay_server {
    public static class Overlay_serverModule {
        // Original: def overlay()
        public static void Overlay() {
            // TODO: implement
        }

        // Original: def get_messages()
        public static void GetMessages() {
            // TODO: implement
        }

        // Original: def get_settings()
        public static void GetSettings() {
            // TODO: implement
        }

        // Original: def serve_media()
        public static void ServeMedia() {
            // TODO: implement
        }

        // Original: def receive_devices()
        public static void ReceiveDevices() {
            // TODO: implement
        }

        // Original: def update_overlay_settings(new_settings)
        public static void UpdateOverlaySettings(object? new_settings) {
            // TODO: implement
        }

        // Original: def add_overlay_message(platform, username, message, message_id, badges=None, color=None)
        public static void AddOverlayMessage(object? platform, object? username, object? message, object? message_id, object? badges = null, object? color = null) {
            // TODO: implement
        }

        // Original: def remove_overlay_message(message_id)
        public static void RemoveOverlayMessage(object? message_id) {
            // TODO: implement
        }

        // Original: def __init__(self, port=5000)
        public static void Init(int? port = null) {
            // TODO: implement
        }

        // Original: def start(self)
        public static void Start() {
            // TODO: implement
        }

        // Original: def run_server()
        public static void RunServer() {
            // TODO: implement
        }

        // Original: def add_message(self, platform, username, message, message_id, badges=None, color=None)
        public static void AddMessage(object? platform, object? username, object? message, object? message_id, object? badges = null, object? color = null) {
            // TODO: implement
        }

        // Original: def remove_message(self, message_id)
        public static void RemoveMessage(object? message_id) {
            // TODO: implement
        }

        // Original: def update_settings(self, settings)
        public static void UpdateSettings(object? settings) {
            // TODO: implement
        }

    }

    public class OverlayServer {
        public object? port { get; set; }
        public object? server_thread { get; set; }
        public object? server_started { get; set; }


        // Original: def __init__(self, port=5000)
        public OverlayServer(int? port = null) {
            // TODO: implement constructor
            this.port = null;
            this.server_thread = null;
            this.server_started = null;
        }

        // Original: def start(self)
        public void Start() {
            // TODO: implement
        }

        // Original: def run_server()
        public void RunServer() {
            // TODO: implement
        }

        // Original: def add_message(self, platform, username, message, message_id, badges=None, color=None)
        public void AddMessage(object? platform, object? username, object? message, object? message_id, object? badges = null, object? color = null) {
            // TODO: implement
        }

        // Original: def remove_message(self, message_id)
        public void RemoveMessage(object? message_id) {
            // TODO: implement
        }

        // Original: def update_settings(self, settings)
        public void UpdateSettings(object? settings) {
            // TODO: implement
        }

    }

}

