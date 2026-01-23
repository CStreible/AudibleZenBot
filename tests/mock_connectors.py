from platform_connectors.base_connector import BasePlatformConnector
from PyQt6.QtCore import pyqtSignal


class MockConnector(BasePlatformConnector):
    """Lightweight mock connector used by tests/harness.

    Use `emit_message(username, message, metadata)` to simulate incoming chat.
    """

    def __init__(self, platform_id='mock'):
        super().__init__()
        self.platform_id = platform_id

    def connect(self, username: str):
        self.username = username
        self.connected = True

    def disconnect(self):
        self.connected = False

    def send_message(self, message: str):
        # For tests, sending is a no-op
        return True

    def emit_message(self, username: str, message: str, metadata: dict = None):
        metadata = metadata or {}
        # Emit using the standardized signal with platform id
        try:
            self.message_received_with_metadata.emit(self.platform_id, username, message, metadata)
        except Exception:
            # Fallback legacy
            try:
                self.message_received.emit(self.platform_id, username, message, metadata)
            except Exception:
                pass
