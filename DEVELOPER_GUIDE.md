# AudibleZenBot - Developer Documentation

## Project Structure

```
AudibleZenBot/
│
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── start.bat                        # Windows startup script
├── README.md                        # Project overview
├── USER_GUIDE.md                   # User documentation
├── DEVELOPER_GUIDE.md              # This file
├── .gitignore                      # Git ignore rules
│
├── ui/                             # User interface components
│   ├── __init__.py
│   ├── chat_page.py                # Chat display page
│   └── connections_page.py         # Platform connections page
│
├── core/                           # Core application logic
│   ├── __init__.py
│   ├── chat_manager.py             # Manages all platform connections
│   └── config.py                   # Configuration management
│
└── platform_connectors/            # Platform-specific connectors
    ├── __init__.py
    ├── base_connector.py           # Base connector class
    ├── twitch_connector.py         # Twitch integration
    ├── youtube_connector.py        # YouTube integration
    ├── trovo_connector.py          # Trovo integration
    ├── kick_connector.py           # Kick integration
    ├── dlive_connector.py          # DLive integration
    └── twitter_connector.py        # Twitter/X integration
```

## Architecture Overview

### Design Pattern: MVC-like Architecture

- **Model**: Platform connectors and ChatManager
- **View**: UI pages (ChatPage, ConnectionsPage)
- **Controller**: Main window and signal/slot connections

### Key Components

#### 1. Main Application (`main.py`)

**MainWindow Class:**
- Creates the main application window
- Manages the expandable sidebar navigation
- Hosts the page stack (Chat and Connections pages)
- Initializes the ChatManager

**SidebarButton Class:**
- Custom button for navigation
- Supports expanded/collapsed states
- Visual feedback for active page

#### 2. Chat Page (`ui/chat_page.py`)

**ChatPage Class:**
- Displays chat messages from all platforms
- Provides options for message display
- Connects to ChatManager signals

**ChatMessage Class:**
- Individual message widget
- Shows platform icon, username, and message
- Platform-specific colors and styling

**Features:**
- Auto-scrolling to latest messages
- Platform icon toggle
- Clear chat functionality
- Demo messages for testing

#### 3. Connections Page (`ui/connections_page.py`)

**ConnectionsPage Class:**
- Tabbed interface for each platform
- Manages platform connection widgets

**PlatformConnectionWidget Class:**
- Connection UI for a single platform
- Username input
- Connect/Disconnect buttons
- Mute toggle
- Connection status and logs

**Features:**
- OAuth authentication flow (placeholder)
- Connection state management
- Real-time status updates

#### 4. Chat Manager (`core/chat_manager.py`)

**ChatManager Class:**
- Central hub for all platform connections
- Manages connector lifecycle
- Routes messages from connectors to UI
- Handles platform muting

**Signals:**
- `message_received(platform, username, message)` - New message
- `connection_status_changed(platform, connected)` - Connection state

**Methods:**
- `connectPlatform(platform_id, username)` - Start connection
- `disconnectPlatform(platform_id)` - Stop connection
- `mutePlatform(platform_id, muted)` - Mute/unmute platform

#### 5. Platform Connectors (`platform_connectors/`)

**BasePlatformConnector Class:**
- Abstract base class for all connectors
- Defines common interface
- Qt signals for communication

**Platform-Specific Connectors:**
Each connector implements:
- `connect(username)` - Establish connection
- `disconnect()` - Close connection
- `send_message(message)` - Send chat message
- Worker thread for async operations

**Current Implementation:**
- Connectors use demo/simulation mode
- Ready for real API integration
- Worker threads prevent UI blocking

#### 6. Configuration (`core/config.py`)

**ConfigManager Class:**
- JSON-based configuration storage
- Nested configuration support (dot notation)
- Platform-specific settings
- Automatic save on changes

**Stored Settings:**
- UI preferences
- Platform credentials (OAuth tokens)
- Connection states
- User preferences

## Development Guide

### Adding a New Platform

1. **Create Connector Class:**
```python
# platform_connectors/newplatform_connector.py
from platform_connectors.base_connector import BasePlatformConnector

class NewPlatformConnector(BasePlatformConnector):
    def connect(self, username: str):
        # Implement connection logic
        pass
    
    def disconnect(self):
        # Implement disconnection
        pass
    
    def send_message(self, message: str):
        # Implement message sending
        pass
```

2. **Register in ChatManager:**
```python
# core/chat_manager.py
self.connectors = {
    # ... existing connectors
    'newplatform': NewPlatformConnector()
}
```

3. **Add to Connections Page:**
```python
# ui/connections_page.py
platforms = [
    # ... existing platforms
    ("New Platform", "newplatform")
]
```

4. **Update Config:**
```python
# core/config.py - in get_default_config()
"newplatform": {
    "username": "",
    "connected": False,
    "muted": False
}
```

### Implementing Real API Connections

Current connectors are in demo mode. To implement real connections:

#### For Twitch:

Use the Twitch EventSub websocket or implement an EventSub client. Connect to `wss://eventsub.wss.twitch.tv/ws` and handle EventSub JSON notifications (e.g. `session_welcome`, `keepalive`, `notification`, `session_reconnect`). See `AudibleZenBot.AutoGen/platform_connectors/twitch_connector.cs` for a C# example.

#### For YouTube:

```python
# Use YouTube Data API v3
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey=API_KEY)

# Get live chat ID
response = youtube.liveBroadcasts().list(
    part='snippet',
    broadcastStatus='active'
).execute()

# Poll for messages
messages = youtube.liveChatMessages().list(
    liveChatId=live_chat_id,
    part='snippet,authorDetails'
).execute()
```

### OAuth Implementation

For platforms requiring OAuth:

1. **Register Application:**
   - Get client ID and secret from platform
   - Set redirect URI (use localhost for desktop app)

2. **Implement OAuth Flow:**
```python
from PyQt6.QtWebEngineWidgets import QWebEngineView

class OAuthDialog(QDialog):
    def __init__(self, auth_url):
        super().__init__()
        self.browser = QWebEngineView()
        self.browser.load(QUrl(auth_url))
        self.browser.urlChanged.connect(self.onUrlChanged)
    
    def onUrlChanged(self, url):
        # Check for redirect with auth code
        if 'code=' in url.toString():
            # Extract code and exchange for token
            pass
```

3. **Store Tokens Securely:**
```python
# Consider using keyring library for secure storage
import keyring

keyring.set_password("audiblezenbot", "twitch_token", token)
token = keyring.get_password("audiblezenbot", "twitch_token")
```

### Signal/Slot Pattern

The application uses Qt's signal/slot mechanism for communication:

```python
# Emitting a signal
self.message_received.emit(platform, username, message)

# Connecting a slot
connector.message_received.connect(self.onMessageReceived)

# Using lambda for additional parameters
connector.message_received.connect(
    lambda u, m, p=platform_id: self.handleMessage(p, u, m)
)
```

### Threading Best Practices

- Use QThread for long-running operations
- Move worker objects to threads with moveToThread()
- Communicate via signals/slots
- Never update UI from worker threads directly

```python
worker = PlatformWorker()
thread = QThread()

worker.moveToThread(thread)
worker.message_signal.connect(self.onMessage)
thread.started.connect(worker.run)
thread.start()
```

## Testing

### Manual Testing

1. **Run Application:**
```bash
python main.py
```

2. **Test UI Navigation:**
   - Toggle sidebar
   - Switch between pages
   - Check responsive layout

3. **Test Chat Display:**
   - Verify demo messages appear
   - Toggle icon visibility
   - Clear chat

4. **Test Connections:**
   - Enter username in each platform tab
   - Click Connect (should show simulated connection)
   - Check mute functionality

### Unit Testing (To Implement)

```python
# tests/test_chat_manager.py
import unittest
from core.chat_manager import ChatManager

class TestChatManager(unittest.TestCase):
    def setUp(self):
        self.manager = ChatManager()
    
    def test_connect_platform(self):
        result = self.manager.connectPlatform('twitch', 'testuser')
        self.assertTrue(result)
    
    def test_mute_platform(self):
        self.manager.mutePlatform('twitch', True)
        self.assertIn('twitch', self.manager.muted_platforms)
```

## Debugging

### Enable Debug Logging

Add to main.py:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

1. **Import Errors:**
   - Check virtual environment is activated
   - Verify all dependencies installed

2. **Qt Errors:**
   - Ensure PyQt6 version compatibility
   - Check for circular imports

3. **Threading Issues:**
   - Use Qt-safe threading patterns
   - Don't access UI from worker threads

### Debug Tools

```python
# Print object hierarchy
def print_widget_tree(widget, indent=0):
    print("  " * indent + widget.__class__.__name__)
    for child in widget.children():
        print_widget_tree(child, indent + 1)

# Monitor signals
def debug_signal(sender, signal_name, *args):
    print(f"{sender.__class__.__name__}.{signal_name}: {args}")
```

## Performance Optimization

### Message Handling

- Limit max messages displayed (configurable)
- Use virtual scrolling for large message lists
- Batch message updates

### Connection Management

- Reuse WebSocket connections
- Implement connection pooling
- Handle reconnection gracefully

### UI Rendering

- Use stylesheets efficiently
- Minimize widget rebuilds
- Implement lazy loading for messages

## Security Considerations

1. **Token Storage:**
   - Never commit tokens to version control
   - Use secure storage (keyring library)
   - Implement token encryption

2. **Input Validation:**
   - Sanitize usernames
   - Validate URLs
   - Escape HTML in messages

3. **Network Security:**
   - Use HTTPS/WSS only
   - Verify SSL certificates
   - Implement rate limiting

## Future Enhancements

### Priority Features

1. **Real API Integration:**
    - Complete Twitch EventSub implementation
   - YouTube Live Chat API
   - Other platforms

2. **OAuth Flow:**
   - Embedded browser for authentication
   - Token refresh logic
   - Multi-account support

3. **Chat Features:**
   - Message filtering
   - User mentions
   - Emote display
   - Badges and roles

4. **Moderation:**
   - Ban/timeout users
   - Delete messages
   - Slow mode
   - Subscriber-only mode

5. **Analytics:**
   - Message statistics
   - Active users
   - Chat trends
   - Export data

### Code Quality

- Add type hints throughout
- Implement comprehensive tests
- Add docstrings to all functions
- Create API documentation

### Distribution

- Create executable with PyInstaller
- Build installer with NSIS
- Auto-update functionality
- Multi-platform support (macOS, Linux)

## Resources

### Platform APIs

- **Twitch:** https://dev.twitch.tv/docs/
- **YouTube:** https://developers.google.com/youtube/v3
- **Trovo:** https://developer.trovo.live/
- **Kick:** Limited documentation, reverse engineering required
- **DLive:** https://dlive.tv/s/api
- **Twitter:** https://developer.twitter.com/

### Qt Documentation

- **PyQt6:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **Qt Widgets:** https://doc.qt.io/qt-6/qtwidgets-index.html

### Python Libraries

- **websockets:** https://websockets.readthedocs.io/
- **aiohttp:** https://docs.aiohttp.org/
- **requests:** https://requests.readthedocs.io/

## Contributing

When contributing:

1. Follow PEP 8 style guide
2. Add docstrings to new functions
3. Update this documentation
4. Test thoroughly before committing
5. Create feature branches

## License

[Specify your license here]

---

**Version:** 1.0.0  
**Last Updated:** December 30, 2025
