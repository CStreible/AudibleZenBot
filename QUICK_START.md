# AudibleZenBot - Quick Start Guide

## Getting Started in 3 Steps

### Step 1: Install and Run

**Option A: Using the Startup Script (Recommended)**
1. Double-click `start.bat`
2. Wait for dependencies to install (first time only)
3. Application will launch automatically

**Option B: Manual Start**
```bash
# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Run application
python main.py
```

### Step 2: Navigate the Interface

**Sidebar Menu:**
- Click **☰** to expand/collapse the menu
- **💬 Chat** - View messages from all platforms
- **🔌 Connections** - Set up platform connections

### Step 3: Connect to Platforms

1. Go to **Connections** page
2. Select a platform tab (Twitch, YouTube, etc.)
3. Enter your username/channel ID
4. Click **Connect & Authorize**
5. Complete OAuth in the browser (if prompted)
6. Return to **Chat** page to see messages!

## Key Features

### Chat Page
- ✅ View messages from all platforms in one place
- ✅ Color-coded usernames by platform
- ✅ Platform icons for each message
- ✅ Toggle icon visibility
- ✅ Clear chat button
- ✅ Auto-scroll to latest messages

### Connections Page
- ✅ Separate tabs for each platform
- ✅ Easy connection management
- ✅ Mute individual platforms
- ✅ Real-time connection status
- ✅ OAuth authentication support
- ✅ Connection logs and info

## Supported Platforms

| Platform | Icon | Status |
|----------|------|--------|
| Twitch | 📺 | Ready |
| YouTube | ▶️ | Ready |
| Trovo | 🎮 | Ready |
| Kick | ⚽ | Ready |
| DLive | 🎥 | Ready |
| X (Twitter) | 🐦 | Ready |

## Tips & Tricks

### Managing Multiple Platforms
- Connect to all platforms at once
- Mute platforms you're not actively monitoring
- Use color-coding to quickly identify message sources

### Chat Organization
- Platform icons help identify sources at a glance
- Turn off icons for a cleaner look
- Clear chat periodically to improve performance

### Connection Issues?
- Check your username is correct
- Ensure you're connected to the internet
- Try disconnecting and reconnecting
- Review connection logs in the platform tab

## Configuration

Settings are automatically saved to:
```
%USERPROFILE%\.audiblezenbot\config.json
```

Your settings persist between sessions, including:
- Connected platforms
- Usernames
- Mute states
- UI preferences

## Need Help?

📖 **Full documentation:** See `USER_GUIDE.md`  
👨‍💻 **Developer info:** See `DEVELOPER_GUIDE.md`  
🔧 **Troubleshooting:** Check the "Troubleshooting" section in `USER_GUIDE.md`

## What's Next?

Future updates will include:
- Real-time chat moderation tools
- Message filtering and search
- Chat analytics and statistics
- Custom alerts and notifications
- Emote support
- And much more!

---

**Enjoy using AudibleZenBot!**  
Version 1.0.0 | December 30, 2025
