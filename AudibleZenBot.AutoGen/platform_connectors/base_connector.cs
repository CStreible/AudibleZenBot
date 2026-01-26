using System;
using System.Threading.Tasks;

namespace platform_connectors.base_connector {
    public static class Base_connectorModule {
        // Original: def __init__(self)
        public static void Init() {
            // TODO: implement
        }

        // Original: def connect(self, username: str)
        public static void Connect(string? username) {
            // minimal connect: mark as connected in config
            core.config.ConfigModule.SetPlatformConfig("", "bot_logged_in", false);
            Console.WriteLine($"Base connect called for: {username}");
        }

        // Original: def disconnect(self)
        public static void Disconnect() {
            core.config.ConfigModule.SetPlatformConfig("", "bot_logged_in", false);
            Console.WriteLine("Base disconnect called");
        }

        // Original: def send_message(self, message: str)
        public static void SendMessage(string? message) {
            Console.WriteLine($"Base send_message: {message}");
        }

        // Original: def isConnected(self)
        public static void IsConnected() {
            Console.WriteLine("Base isConnected check");
        }

    }

    public class BasePlatformConnector {
        public bool? connected { get; set; }
        public object? username { get; set; }


        // Original: def __init__(self)
        public BasePlatformConnector() {
            // TODO: implement constructor
            this.connected = null;
            this.username = null;
        }

        // Original: def connect(self, username: str)
        public void Connect(string? username) {
            this.connected = true;
            this.username = username;
            Console.WriteLine($"Connector instance connected: {username}");
        }

        // Original: def disconnect(self)
        public void Disconnect() {
            this.connected = false;
            Console.WriteLine("Connector instance disconnected");
        }

        // Original: def send_message(self, message: str)
        public void SendMessage(string? message) {
            Console.WriteLine($"Connector instance send_message: {message}");
        }

        // Original: def isConnected(self)
        public void IsConnected() {
            Console.WriteLine($"Connector instance isConnected: {this.connected}");
        }

    }

}

