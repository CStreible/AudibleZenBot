# AudibleZenBot

<div align="center">

**A Powerful Multi-Platform Chat Bot for Live Streaming**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.7.0-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monitor and manage chat messages from **Twitch**, **YouTube**, **Trovo**, **Kick**, **DLive**, and **X (Twitter)** all in one unified interface!

**🆕 Now available as standalone executable with automatic ngrok management!**

</div>

---

## 🌟 Features

### 🎯 Multi-Platform Support
Connect to multiple streaming platforms simultaneously and see all chats in one place:
- **📺 Twitch** - IRC chat integration
- **▶️ YouTube** - Live chat via YouTube Data API
- **🎮 Trovo** - WebSocket chat connection
- **⚽ Kick** - Real-time chat monitoring (auto-ngrok webhooks!)
- **🎥 DLive** - GraphQL-based chat
- **🐦 X (Twitter)** - Spaces and live streams

### 🚀 Automatic Ngrok Management
- **No manual tunnel setup** required for webhook-based platforms
- **Automatic tunnel creation** when connecting to Kick
- **Health monitoring** with auto-reconnect
- **Settings UI** for easy configuration
- **Clean shutdown** - tunnels stop automatically

### 💬 Unified Chat Interface
- View messages from all platforms in a single scrollable feed
- Color-coded usernames by platform
- Platform icons for quick identification
- Auto-scroll to latest messages
- Clear chat functionality

### 🔌 Connection Management
- Tabbed interface for each platform
- Easy OAuth authentication
- Real-time connection status
- Mute/unmute individual platforms
- Connection logs and diagnostics

### 🎨 Modern GUI
- Clean, dark-themed interface
- Expandable sidebar navigation (Chat, Connections, Settings)
- Responsive layout
- Professional styling

### ⚙️ Configuration
- Automatic settings persistence
- Per-platform preferences
- Custom mute states
- UI customization options
- Ngrok token management

---

## 🚀 Quick Start

### Option 1: Standalone Executable (Easiest!)

1. **Download** the latest `AudibleZenBot.exe` from releases
2. **Run** the executable
3. **Configure ngrok** in Settings (for Kick support)
4. **Connect** to your platforms!

No Python installation required! See [EXECUTABLE_BUILD.md](EXECUTABLE_BUILD.md) for details.

### Option 2: Run from Source

#### Prerequisites
- Windows 10 or higher
- Python 3.9 or higher
- Internet connection

#### Installation & Launch

**Simple Method (Recommended):**
```bash
# Just double-click:
start.bat
```
The script will automatically set up everything and launch the app!

**Manual Method:**
```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python main.py
```

---

## 📖 Documentation

- **[Quick Start Guide](QUICK_START.md)** - Get up and running in 3 steps
- **[User Guide](USER_GUIDE.md)** - Complete user documentation
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Architecture and development info

---

## 🖼️ Interface Overview

### Chat Page
View and manage all incoming chat messages:
- Real-time message display
- Platform identification
- Message options and controls
- Demo mode for testing

### Connections Page
Manage your platform connections:
- Per-platform configuration tabs
- Username/Channel ID input
- Connect & Authorize buttons
- Mute toggles
- Connection status and logs

---

## 🛠️ Technical Details

### Built With
- **PyQt6** - Modern Qt framework for Python
- **Python 3.9+** - Core language
- **asyncio** - Async I/O for concurrent connections
- **websockets** - WebSocket client for real-time chat
- **aiohttp** - Async HTTP client
- **requests** - HTTP library for API calls

### Architecture
- **MVC Pattern** - Separation of concerns
- **Signal/Slot** - Qt's event-driven communication
- **Multi-threading** - Non-blocking platform connections
- **Modular Design** - Easy to extend with new platforms

### Project Structure
```
AudibleZenBot/
├── main.py                      # Application entry point
├── start.bat                    # Windows launcher
├── requirements.txt             # Python dependencies
│
├── ui/                          # User interface
│   ├── chat_page.py            # Chat display
│   └── connections_page.py     # Connection management
│
├── core/                        # Core logic
│   ├── chat_manager.py         # Message routing
│   └── config.py               # Configuration management
│
└── platform_connectors/         # Platform integrations
    ├── base_connector.py       # Base connector class
    ├── twitch_connector.py     # Twitch integration
    ├── youtube_connector.py    # YouTube integration
    ├── trovo_connector.py      # Trovo integration
    ├── kick_connector.py       # Kick integration
    ├── dlive_connector.py      # DLive integration
    └── twitter_connector.py    # Twitter/X integration
```

---

## 🔧 Configuration

Settings are stored in:
```
%USERPROFILE%\.audiblezenbot\config.json
```

Configuration includes:
- Platform credentials (OAuth tokens)
- Connection preferences
- UI settings
- Mute states

---

## 🎯 Usage Examples

### Connecting to Twitch
1. Navigate to **Connections** page
2. Select **Twitch** tab
3. Enter your Twitch channel name
4. Click **Connect & Authorize**
5. Complete OAuth in browser
6. Return to **Chat** page to see messages!

### Managing Multiple Platforms
1. Connect to multiple platforms from the Connections page
2. Use mute toggles to filter which platforms show in chat
3. Toggle platform icons on/off for cleaner display
4. Clear chat when needed using the Clear Chat button

---

## 🚧 Development Status

### Current State
✅ Core application framework  
✅ UI components and navigation  
✅ Platform connector architecture  
✅ Configuration management  
✅ Demo/simulation mode  

### In Progress
🔄 Real API integrations  
🔄 OAuth authentication flows  
🔄 Production platform connectors  

### Planned Features
📋 Chat moderation tools  
📋 Message filtering and search  
📋 Emote support and display  
📋 Chat analytics and statistics  
📋 Custom alerts and notifications  
📋 Message export functionality  
📋 Multi-language support  

---

## 🤝 Contributing

Contributions are welcome! To add a new platform:

1. Create a new connector in `platform_connectors/`
2. Inherit from `BasePlatformConnector`
3. Implement required methods
4. Register in `ChatManager`
5. Add UI tab in `ConnectionsPage`

See [Developer Guide](DEVELOPER_GUIDE.md) for detailed instructions.

---

## 📝 License

This project is open source. See LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with PyQt6 and Python
- Platform APIs and documentation
- Open source community

---

## 📞 Support

For issues, questions, or suggestions:
- Check the [User Guide](USER_GUIDE.md)
- Review [Troubleshooting](USER_GUIDE.md#troubleshooting)
- Check platform connection logs

---

<div align="center">

**Made with ❤️ for the streaming community**

Version 1.0.0 | December 30, 2025

[⬆ Back to Top](#audiblezenbot)

</div>
