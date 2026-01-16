"""
Base Platform Connector
"""

from abc import abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal


class BasePlatformConnector(QObject):
    """Base class for all platform connectors"""
    
    message_received = pyqtSignal(str, str, str, dict)  # platform, username, message, metadata
    message_received_with_metadata = pyqtSignal(str, str, str, dict)  # platform, username, message, metadata
    message_deleted = pyqtSignal(str, str)  # platform, message_id - emitted when message deleted by platform/other mods
    stream_event = pyqtSignal(str, str, str, dict)  # platform, event_type, username, event_data
    connection_status = pyqtSignal(bool)  # connected
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.connected = False
        self.username = None
    
    @abstractmethod
    def connect(self, username: str):
        """Connect to the platform"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the platform"""
        pass
    
    @abstractmethod
    def send_message(self, message: str):
        """Send a message to the chat"""
        pass
    
    def isConnected(self) -> bool:
        """Check if connected"""
        return self.connected
