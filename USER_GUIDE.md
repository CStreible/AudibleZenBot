# AudibleZenBot - User Guide

## Overview

AudibleZenBot is a multi-platform streaming chat bot application that allows you to monitor and manage chat messages from multiple streaming platforms in one unified interface.

## Supported Platforms

- **Twitch** - Live streaming on Twitch.tv
- **YouTube** - YouTube Live streaming
- **Trovo** - Trovo.live streaming platform
- **Kick** - Kick.com streaming
- **DLive** - DLive streaming platform
- **X (Twitter)** - Twitter/X live streaming and Spaces

## Installation

### Prerequisites

- Windows 10 or higher
- Python 3.9 or higher
- Internet connection

### Setup Steps

1. **Extract the Application**
   - Extract the AudibleZenBot folder to your desired location

2. **Run the Startup Script**
   - Double-click `start.bat` in the application folder
   - The script will automatically:
     - Check for Python installation
     - Create a virtual environment
     - Install required dependencies
     - Launch the application

3. **First Launch**
   - The application will create a configuration file in `%USERPROFILE%\.audiblezenbot\`
   - All your settings and connection information will be saved there

## Using the Application

### Interface Overview

The application has two main pages accessible from the left sidebar:

1. **Chat Page** - View all chat messages
2. **Connections Page** - Manage platform connections

#### Sidebar Navigation

- Click the **☰** (hamburger) icon to expand/collapse the sidebar
- When expanded, you can see full page names
- When collapsed, only icons are shown

### Chat Page

The Chat page displays messages from all connected platforms in real-time.

**Features:**

- **Platform Icons** - Each message shows which platform it came from
  - 📺 Twitch
  - ▶️ YouTube
  - 🎮 Trovo
  - ⚽ Kick
  - 🎥 DLive
  - 🐦 X (Twitter)

- **Username Colors** - Each platform has a distinct color for usernames
  - Twitch: Purple
  - YouTube: Red
  - Trovo: Green
  - Kick: Lime
  - DLive: Gold
  - Twitter: Blue

**Options:**

- **Show platform icons** - Toggle this checkbox to hide/show platform icons next to messages
- **Clear Chat** - Remove all messages from the display

**Tips:**

- Messages auto-scroll to show the latest content
- The chat history is cleared when you close the application

### Connections Page

Manage your connections to each streaming platform through tabbed interfaces.

**For Each Platform:**

1. **Account Information**
   - Enter your username or channel ID for the platform
   - This is the channel you want to monitor

2. **Connect & Authorize**
   - Click this button to initiate the connection
   - A browser window will open for OAuth authentication (for platforms that require it)
   - Log in with your account and authorize the bot
   - The bot will connect to the chat

3. **Connection Status**
   - Shows whether you're currently connected
   - Green "Connected ✓" means active connection
   - Red "Not Connected" means no connection

4. **Chat Controls**
   - **Mute chat from this platform** - Check this to stop messages from appearing in the Chat page
   - Useful if one platform is too active or you want to focus on others

5. **Connection Information**
   - Shows logs and status messages
   - Displays connection errors if any occur

6. **Disconnect**
   - Click to disconnect from the platform
   - You can reconnect at any time

### Platform-Specific Notes

#### Twitch
- Requires OAuth token for full functionality
- Can read public chat without authentication
- Moderator features require proper authorization

#### YouTube
- Requires YouTube Data API v3 access
- OAuth 2.0 authentication needed
- Must have an active live stream to connect to chat

#### Trovo
- Uses WebSocket connection
- Requires Trovo account
- OAuth authentication recommended

#### Kick
- Relatively new platform with limited API documentation
- Connection may require updates as API evolves

#### DLive
- Uses GraphQL over WebSocket
- Blockchain-based platform
- Requires DLive account

#### X (Twitter)
- Supports Twitter Spaces and live streams
- Requires Twitter API access
- OAuth 2.0 authentication needed

## Configuration

The application stores configuration in:
```
%USERPROFILE%\.audiblezenbot\config.json
```

**Saved Settings:**
- UI preferences (icon visibility, sidebar state)
- Platform usernames
- Connection tokens (encrypted)
- Mute states

**Manual Editing:**
You can edit the config file manually if needed, but be careful with the JSON syntax.

## Troubleshooting

### Application Won't Start

1. **Check Python Installation**
   ```
   python --version
   ```
   Should show Python 3.9 or higher

2. **Reinstall Dependencies**
   ```
   pip install -r requirements.txt --force-reinstall
   ```

3. **Check for Errors**
   - Look for error messages in the console window
   - Check if any files are missing

### Can't Connect to Platform

1. **Verify Username/Channel ID**
   - Make sure you entered the correct username
   - Check for typos or extra spaces

2. **Check Internet Connection**
   - Ensure you have a stable internet connection
   - Check if the streaming platform is accessible

3. **OAuth Authorization**
   - Make sure you completed the OAuth flow
   - Try disconnecting and reconnecting
   - Check if your browser blocked the popup

4. **Platform Status**
   - Check if the streaming platform is experiencing issues
   - Try accessing the platform's website directly

### Messages Not Appearing

1. **Check Mute Status**
   - Make sure the platform isn't muted in Connections page

2. **Verify Connection**
   - Check connection status in Connections page
   - Try disconnecting and reconnecting

3. **Check Chat Activity**
   - Ensure the stream has active chat
   - Test with a known active stream

### Performance Issues

1. **Too Many Messages**
   - Use the mute feature for less important platforms
   - Clear chat regularly using the "Clear Chat" button

2. **High CPU/Memory Usage**
   - Disconnect from platforms you're not actively monitoring
   - Restart the application periodically

## Advanced Features (Coming Soon)

Future updates may include:

- **Chat Filters** - Filter messages by keywords or users
- **Moderation Tools** - Ban, timeout, delete messages
- **Chat Analytics** - View statistics and trends
- **Custom Alerts** - Get notified of specific events
- **Message Search** - Search through chat history
- **Export Chat** - Save chat logs to file
- **Custom Themes** - Light mode and custom color schemes
- **Multi-Language Support** - Interface in multiple languages

## Support and Feedback

For issues, suggestions, or questions:

1. Check the troubleshooting section above
2. Review the connection information logs in each platform tab
3. Make sure you're using the latest version

## Privacy and Security

- OAuth tokens are stored locally in your config file
- No data is transmitted to third parties
- Each platform connection is direct to their official APIs
- You can delete the config file to remove all stored data

## License

This software is provided as-is for personal use.

---

**Version:** 1.0.0  
**Last Updated:** December 30, 2025
