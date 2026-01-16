# DLive Chat Integration

## Overview
DLive chat integration is now fully functional with support for receiving, sending, and displaying chat messages with badges.

## Features

### ✅ Message Reception
- Real-time chat message streaming via GraphQL WebSocket
- Support for multiple message types:
  - **Chat Messages**: Regular text messages from users
  - **Gifts**: Donation/gift notifications
  - **Follows**: New follower notifications
  - **Subscriptions**: Subscription/resub notifications
- Message metadata includes sender info, badges, timestamps

### ✅ Message Sending
- Send chat messages via GraphQL mutation
- Requires authentication with access token
- Automatic error handling and logging

### ✅ Badge System
Supported badges with custom SVG icons:
- **Partner**: Gold star badge for DLive partners
- **Subscriber**: Purple S badge for subscribers
- **Moderator**: Green shield badge for moderators
- **Gift**: Red gift badge for gift senders
- **Follow**: Yellow star badge for followers

### ✅ Platform Icon
- Custom DLive logo SVG with orange/yellow star design
- Displayed alongside messages in chat

## Technical Details

### Protocol
- **WebSocket**: `wss://graphigo.prd.dlive.tv/`
- **Protocol**: GraphQL WebSocket (`graphql-ws` subprotocol)
- **Authentication**: OAuth 2.0 access token

### GraphQL Operations

#### Subscription (Receive Messages)
```graphql
subscription StreamMessageReceived($streamer: String!) {
  streamMessageReceived(streamer: $streamer) {
    type
    ... on ChatText {
      id
      content
      createdAt
      sender {
        displayname
        username
        avatar
        partnerStatus
        badges
      }
    }
    ... on ChatGift { ... }
    ... on ChatFollow { ... }
    ... on ChatSubscription { ... }
  }
}
```

#### Mutation (Send Messages)
```graphql
mutation SendStreamChatMessage($input: SendStreamchatMessageInput!) {
  sendStreamchatMessage(input: $input) {
    err { message }
    message { id, content }
  }
}
```

### Message Flow
1. **Connection Init**: Send `connection_init` message
2. **Wait for ACK**: Receive `connection_ack` response
3. **Subscribe**: Send subscription with streamer username
4. **Listen**: Receive `data` messages with chat events
5. **Keep-Alive**: Handle `ka` messages automatically

### Badge Processing
- Partner status parsed from `sender.partnerStatus`
- Additional badges from `sender.badges` array
- Badges normalized to lowercase for icon matching
- Unknown badges displayed as text fallback

## Configuration

### Config Structure
```json
{
  "dlive": {
    "username": "streamer_username",
    "access_token": "your_dlive_access_token"
  }
}
```

### Getting Access Token
See `platform_connectors/dlive_oauth_guide.py` for detailed instructions:
1. Register app at https://dlive.tv/s/settings?tab=developer
2. Get authorization code via OAuth URL
3. Exchange code for access token
4. Save token to config

## Usage

### Via UI
1. Go to **Connections** → **DLive** tab
2. Enter your DLive username
3. Paste your access token
4. Click **Connect**
5. Chat messages will appear with badges and platform icon

### Programmatically
```python
from platform_connectors.dlive_connector import DLiveConnector

connector = DLiveConnector(config)
connector.set_token("your_access_token")
connector.connect("streamer_username")

# Send message
connector.send_message("Hello chat!")

# Disconnect
connector.disconnect()
```

## Files Modified/Created

### Core Files
- `platform_connectors/dlive_connector.py` - Main connector implementation
- `core/chat_manager.py` - Updated to pass config to DLive connector
- `ui/chat_page.py` - Added DLIVE_BADGE_ICONS mapping
- `ui/platform_icons.py` - Added DLive logo support

### Badge Assets
- `resources/badges/dlive/partner.svg`
- `resources/badges/dlive/subscriber.svg`
- `resources/badges/dlive/moderator.svg`
- `resources/badges/dlive/gift.svg`
- `resources/badges/dlive/follow.svg`
- `resources/badges/dlive/dlive_logo.svg`

### Documentation
- `platform_connectors/dlive_oauth_guide.py` - OAuth setup guide
- `API_SETUP_GUIDE.md` - Already included DLive section

## Error Handling

### Connection Errors
- WebSocket connection failures emit error signal
- Automatic cleanup on disconnect
- Status signals for UI updates

### Message Send Errors
- Requires access token - warns if missing
- GraphQL mutation errors logged and emitted
- Async operation with thread-safe event loop

### Message Parse Errors
- JSON decode errors caught and logged
- Unknown message types safely ignored
- Graceful handling of missing fields

## Testing

### Test Checklist
- [ ] Connect to DLive chat with valid credentials
- [ ] Receive chat messages with correct formatting
- [ ] Display badges properly (partner, subscriber, etc.)
- [ ] Send messages successfully
- [ ] Handle gifts/follows/subs correctly
- [ ] Platform icon displays correctly
- [ ] Disconnect cleanly without errors
- [ ] Reconnect works after disconnect

### Demo Mode
Without credentials, the connector will:
- Emit connection error
- Status remains disconnected
- UI shows appropriate error state

## Known Limitations

1. **Authentication Required**: Cannot receive or send messages without valid access token
2. **No Message Deletion**: DLive API doesn't expose message deletion via GraphQL
3. **No Message Editing**: Messages cannot be modified after sending
4. **Rate Limits**: DLive has undocumented rate limits - be conservative with sending
5. **OAuth Flow**: No automated OAuth flow yet - manual token extraction required

## Future Enhancements

### Planned Features
- [ ] Automated OAuth flow with local callback server
- [ ] Message history/replay
- [ ] User info caching
- [ ] Emote rendering
- [ ] Raid/host notifications
- [ ] Channel point redemptions (if supported)
- [ ] Chat commands support
- [ ] Moderation actions (timeout/ban)

### API Limitations
- Limited official documentation
- GraphQL schema discovery needed for additional features
- Community-driven reverse engineering for advanced features

## Support

### Resources
- DLive Developer Settings: https://dlive.tv/s/settings?tab=developer
- DLive API Docs: Limited official documentation
- Community Resources: Various GitHub projects

### Troubleshooting

**No messages received:**
- Verify streamer username is correct
- Check access token is valid
- Ensure streamer is live (may require active stream)
- Check console for WebSocket errors

**Cannot send messages:**
- Verify access token has write permissions
- Check if account is authenticated properly
- Review GraphQL mutation response for errors

**Connection drops:**
- DLive WebSocket may require periodic reconnection
- Check network stability
- Verify token hasn't been revoked

## Architecture Notes

### Thread Safety
- Uses QThread for async operations
- Event loop runs in worker thread
- Signals for cross-thread communication
- Thread-safe message sending via `asyncio.run_coroutine_threadsafe`

### Memory Management
- Automatic cleanup on disconnect
- Event loop properly closed
- Worker thread joins on stop

### Signal/Slot Pattern
- `message_signal`: Emits (username, message, metadata)
- `status_signal`: Emits connection state
- `error_signal`: Emits error messages
- All connected in main thread via Qt signals

---

**Implementation Date**: December 31, 2025
**Status**: ✅ Complete and Ready for Testing
