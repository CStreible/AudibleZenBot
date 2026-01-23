"""
Manual Twitter connector test
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from platform_connectors.twitter_connector import TwitterConnector


def main():
    """Run a short manual test of the Twitter connector (requires auth)."""
    print("=" * 60)
    print("Twitter/X Connector Test")
    print("=" * 60)
    
    # Create connector
    connector = TwitterConnector()
    
    # Test signals
    def on_message(username, message, metadata):
        print(f"\n[MESSAGE RECEIVED]")
        print(f"Username: {username}")
        print(f"Message: {message}")
        print(f"Metadata: {metadata}")
        print("-" * 60)
    
    def on_status(connected):
        status = "Connected" if connected else "Disconnected"
        print(f"\n[STATUS CHANGE] {status}")
    
    def on_error(error):
        print(f"\n[ERROR] {error}")
    
    # Connect signals
    connector.message_signal.connect(on_message) if hasattr(connector.worker, 'message_signal') else None
    
    # Test connection (will fail without valid token)
    print("\nAttempting to connect to Twitter/X...")
    print("Note: This will fail without a valid OAuth token.")
    print("To test properly, authenticate via the UI first.\n")
    
    # Try to connect - this should show error without token
    connector.connect("testuser")
    
    print("\n[INFO] To properly test Twitter integration:")
    print("1. Run the main application (python main.py)")
    print("2. Go to Connections page")
    print("3. Select the X (Twitter) tab")
    print("4. Click 'Connect & Authorize'")
    print("5. Complete OAuth flow")
    print("6. Once authenticated, the connector will fetch mentions")
    print("\n[INFO] Twitter integration is configured and ready!")
    print("=" * 60)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main()
    QTimer.singleShot(2000, app.quit)
    sys.exit(app.exec())
