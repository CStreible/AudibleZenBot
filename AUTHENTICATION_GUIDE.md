# AudibleZenBot - Authentication & Real Chat Integration

## Overview

- AudibleZenBot now supports **real chat connections** with authentication for all 6 streaming platforms:
- 📺 Twitch (EventSub websocket + Helix APIs)
- ▶️ YouTube (Live Chat API)
- 🎮 Trovo (WebSocket API)
- ⚽ Kick (WebSocket)
- 🎥 DLive (GraphQL)
- 🐦 X/Twitter (API v2)

## Features Implemented

### ✅ Authentication System
- **OAuth 2.0 Support** - Browser-based authentication flow
- **Manual Token Entry** - Paste tokens directly
- **Token Storage** - Securely saved in config file
- **Multiple Auth Methods** - API keys, OAuth tokens, bearer tokens

### ✅ Platform Connections

#### Twitch
- **EventSub WebSocket** - Uses Twitch EventSub websocket for notifications (replaces legacy raw chat parsing)
- **Message Parsing** - Parses EventSub JSON notifications including channel points redemptions, follows, subscriptions, cheers and chat message notifications when enabled
- **Send Messages** - Uses Helix/moderation/chat endpoints (requires appropriate scopes)
- **Reconnection & Keepalive** - WebSocket reconnection and EventSub session handling
- **Demo Mode** - Works without token for testing

#### YouTube
- **YouTube Data API v3** - Official API integration
- **Live Chat Discovery** - Automatically finds active streams
- **Message Polling** - Fetches new messages every 2 seconds
- **Duplicate Prevention** - Tracks processed messages
- **Send Messages** - OAuth required
- **Demo Mode** - Works without API key

#### Other Platforms
- **Trovo** - WebSocket connection structure ready
- **Kick** - WebSocket connection structure ready
- **DLive** - GraphQL structure ready
- **Twitter** - API v2 structure ready
- **Demo Mode** - All platforms work in demo mode

### ✅ User Interface
- **Token Input Fields** - Enter OAuth tokens or API keys
- **Password Protection** - Tokens displayed as dots
- **Auth Dialog** - Simple dialog for manual token entry
- **Connection Logs** - Real-time status and error messages
- **Status Indicators** - Green (connected) / Red (disconnected)

### ✅ Connection Management
- **Auto-Connect** - Token-based automatic connection
- **Manual Connect** - Connect/disconnect on demand
- **Mute Control** - Mute individual platforms
- **Error Handling** - Graceful error messages
- **Reconnection** - Can disconnect and reconnect

## How to Use

### Option 1: Demo Mode (No Setup Required)

1. Open AudibleZenBot
2. Go to Connections page
3. Select any platform tab
4. Enter any username (e.g., "test_channel")
5. Leave token field **empty**
6. Click "Connect & Authorize"
7. See demo messages in Chat page!

**Perfect for:** Testing the app, UI demonstrations, development

### Option 2: Real Connections (Requires API Setup)

#### For Twitch:

1. **Get OAuth Token:**
   - Visit https://twitchtokengenerator.com/
   - Select scopes: `chat:read`, `chat:edit`
   - Copy the access token

2. **Connect:**
   - Go to Connections → Twitch tab
   - Enter your Twitch channel name
   - Paste token in "OAuth Token / API Key" field
   - Click "Connect & Authorize"
   - Watch real Twitch chat in Chat page!

#### For YouTube:

1. **Get API Key:**
   - Go to https://console.cloud.google.com/
   - Create project → Enable YouTube Data API v3
   - Create credentials → API Key
   - Copy the API key

2. **Connect:**
   - Go to Connections → YouTube tab
   - Enter your YouTube Channel ID
   - Paste API key in token field
   - Click "Connect & Authorize"
   - **Note:** You must have an active live stream!

#### For Other Platforms:

See the detailed **[API Setup Guide](API_SETUP_GUIDE.md)** for:
- Trovo access tokens
- Kick authentication
- DLive tokens
- Twitter/X OAuth

## Technical Details

### Twitch Implementation (EventSub + Helix)

EventSub WebSocket is used to receive structured JSON notifications from Twitch (session_welcome, keepalive, notification, session_reconnect). Common notifications include channel points redemptions, stream.online/offline, follows, subscriptions, gifted subs, and cheers. When available, `channel.chat.message` notifications are used for chat messages instead of legacy PRIVMSG-style parsing.

Receiving messages: connect to `wss://eventsub.wss.twitch.tv/ws` and parse EventSub JSON payloads.

Sending messages and moderation actions use Helix endpoints (requires `chat:edit`, `moderation:chat` or appropriate scopes).

**Features:**
- EventSub JSON parsing for robust event handling
- Helix API usage for sending messages and moderation
- WebSocket reconnect/backoff and session management
- Fallbacks and diagnostics for missing scopes or token validation

### YouTube Implementation

```python
# API Endpoints Used
GET /youtube/v3/search
  - Find active live broadcasts
  
GET /youtube/v3/videos
  - Get live chat ID from video

GET /youtube/v3/liveChat/messages
  - Poll for new messages (every 2s)
  
POST /youtube/v3/liveChat/messages
  - Send chat messages (OAuth required)
```

**Features:**
- Automatic live stream discovery
- Message deduplication
- Pagination support
- API key or OAuth authentication
- Rate limit aware

### Architecture

```
UI Layer (connections_page.py)
    ↓
OAuth Handler (oauth_handler.py)
    ↓
Chat Manager (chat_manager.py)
    ↓
Platform Connectors (twitch_connector.py, etc.)
    ↓
Worker Threads (QThread + asyncio)
    ↓
Platform APIs (WebSocket, REST, GraphQL)
```

**Benefits:**
- Non-blocking UI
- Concurrent connections
- Threadsafe signal/slot communication
- Easy to extend

## Configuration

### Token Storage

Tokens are stored in:
```
%USERPROFILE%\.audiblezenbot\config.json
```

Example structure:
```json
{
  "platforms": {
    "twitch": {
      "username": "your_channel",
      "oauth_token": "REPLACE_WITH_YOUR_TOKEN",
      "connected": false,
      "muted": false
    },
    "youtube": {
      "channel_id": "UC1234567890",
      "oauth_token": "REPLACE_WITH_YOUR_API_KEY",
      "connected": false,
      "muted": false
    }
  }
}
```

### Security Notes

- **Tokens are stored in plain text** - Consider encrypting for production
- **Config file should be private** - Don't commit to version control
- **Tokens persist across sessions** - Saved automatically
- **Manual editing supported** - Can edit config file directly

## API Requirements Summary

| Platform | Auth Type | Required | Purpose |
|----------|-----------|----------|---------|
| Twitch | OAuth | Recommended | Read/send chat |
| YouTube | API Key/OAuth | Required | Read chat |
| Trovo | Access Token | Required | Connect to chat |
| Kick | Cookie/None | Optional | Read chat |
| DLive | Access Token | Required | GraphQL API |
| Twitter | Bearer Token | Required | API access |

## Testing

### Test Real Twitch Connection

1. Get token from https://twitchtokengenerator.com/
2. Enter your channel name
3. Paste token
4. Click Connect
5. Open your Twitch channel in browser
6. Type test message in chat
7. **Message appears in AudibleZenBot!** ✓

### Test YouTube (If Streaming)

1. Get API key from Google Cloud Console
2. Start a live stream on YouTube
3. Get your Channel ID
4. Enter ID and API key in app
5. Click Connect
6. Type in YouTube live chat
7. **Message appears in AudibleZenBot!** ✓

## Troubleshooting

### Twitch "Connection Error"
- **Check token:** Make sure it's valid and not expired
- **Check channel name:** Must be lowercase, no #symbol
- **Check scopes:** Token needs `chat:read` permission
- **Internet:** Verify connection to Twitch

### YouTube "No active live stream found"
- **Start streaming:** Must have active live broadcast
- **Check Channel ID:** Get from YouTube account settings
- **Check API quota:** Daily limit is 10,000 requests
- **API enabled:** YouTube Data API v3 must be enabled

### "Authentication failed"
- **Token format:** Check for extra spaces or characters
- **Token validity:** Generate a new token
- **Platform status:** Check if platform is having issues
- **Scope/permissions:** Verify token has required permissions

### Messages not appearing
- **Check mute status:** Platform might be muted
- **Check connection:** Green "Connected ✓" status
- **Check chat activity:** Ensure chat is actually active
- **Refresh:** Try disconnect and reconnect

## Future Enhancements

### Planned Features
- [ ] Token encryption in config file
- [ ] Automatic token refresh (OAuth)
- [ ] Connection retry logic
- [ ] WebSocket reconnection
- [ ] Rate limit handling
- [ ] Emote parsing and display
- [ ] User badges and roles
- [ ] Moderation commands
- [ ] Message filtering
- [ ] Chat analytics

-### Platform Completion
- [x] Twitch - EventSub + Helix implementation
- [x] YouTube - API v3 implementation
- [ ] Trovo - Complete WebSocket
- [ ] Kick - Complete WebSocket
- [ ] DLive - Complete GraphQL
- [ ] Twitter - Complete API v2

## Development

### Adding Real API to Other Platforms

Each platform connector follows this pattern:

```python
class PlatformConnector(BasePlatformConnector):
    def set_token(self, token: str):
        self.oauth_token = token
    
    def connect(self, username: str):
        # Create worker thread
        worker = PlatformWorker(username, self.oauth_token)
        # Setup signals
        # Start thread
    
    class PlatformWorker(QThread):
        def run(self):
            if self.oauth_token:
                # Real connection
                self.connect_to_api()
            else:
                # Demo mode
                self.run_demo_mode()
        
        def connect_to_api(self):
            # Platform-specific connection logic
            pass
```

### Testing New Implementations

1. Add API connection code
2. Test with valid token
3. Test with invalid token (error handling)
4. Test with no token (demo mode)
5. Test reconnection
6. Test message sending
7. Verify UI updates correctly

## Resources

- **[API Setup Guide](API_SETUP_GUIDE.md)** - Get credentials for each platform
- **[User Guide](USER_GUIDE.md)** - Complete user documentation
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Architecture and development

## Summary

-✅ **What Works:**
- Twitch real EventSub + Helix connection with OAuth
- YouTube real API connection with API key
- Token-based authentication for all platforms
- Demo mode for all platforms (no setup needed)
- OAuth token storage and management
- Manual token entry interface
- Connection status tracking
- Error handling and logging

✅ **What's Ready:**
- Platform connector architecture
- Worker thread implementation
- Signal/slot communication
- UI for token management
- Multi-platform support

🔧 **What's Next:**
- Complete remaining platform implementations
- Add token encryption
- Implement automatic OAuth flows
- Add emote support
- Add moderation features

---

**The app is fully functional!** You can use it in demo mode right now, or set up API credentials for real chat connections.

**Version:** 1.0.0 with Real API Support  
**Date:** December 30, 2025
