# Dual Account System Guide

## Overview
The Connections page now supports separate **Streamer Account** and **Bot Account** credentials for each platform with **automatic OAuth authentication**.

## Why Two Accounts?

### Streamer Account
- Used for managing stream information and broadcaster-level operations
- Access to stream titles, categories, stream status
- Broadcaster permissions for advanced features

### Bot Account  
- Used for chat interaction and moderation
- Sends automated messages (timer messages, commands, etc.)
- Keeps your main streamer account separate from bot activity

## Features

### Per-Platform Account Management
Each platform tab now has:
- **👤 Streamer Account** section (blue border)
  - Login/Logout button
  - Status indicator
  - Username display
  
- **🤖 Bot Account** section (green border)
  - Login/Logout button
  - Status indicator
  - Username display

### Automatic OAuth Authentication
- **No manual token entry needed** for most platforms
- Browser-based OAuth flow (opens automatically)
- Secure authorization code exchange
- Automatic token storage

### Persistent Login
- Credentials are saved when you log in
- Automatically restored when you restart the application
- Logout clears the active session but preserves credentials for next login

### Independent Operation
- Log in to just streamer account
- Log in to just bot account
- Log in to both accounts simultaneously
- Each account maintains its own connection state

## How to Use

### Logging In (Automatic OAuth)

#### For Trovo & YouTube:

1. **Navigate to the Connections page**
2. **Select the platform tab** (Trovo or YouTube)
3. **Click "Login"** on either Streamer or Bot account section
4. **Enter your username** when prompted
5. **Browser opens automatically** to the OAuth authorization page
6. **Authorize the application** in your browser
7. **Copy the authorization code** from the browser URL or callback page
8. **Paste the code** into the dialog that appears
9. **Token is automatically obtained** and saved
10. **Status updates** to "Logged In"

#### For Twitch:

1. **Click "Login"** on Streamer or Bot account
2. **Enter your username**
3. **Enter your Twitch Client ID** when prompted
   - Get it from: https://dev.twitch.tv/console/apps
4. **Browser opens** for authorization
5. **Authorize and copy the code** from URL
6. **Paste the code** when prompted
7. **Automatic token exchange** completes login

#### For Kick & DLive (Manual):

1. **Click "Login"** on the account section
2. **Enter your username**
3. **Follow platform-specific instructions** shown in the dialog:
   - **Kick**: Copy Authorization cookie from browser DevTools
   - **DLive**: Get API key from DLive settings
4. **Paste the token** when prompted
5. **Status updates** to "Logged In"

### Logging Out

1. **Click "Logout"** on the account you want to disconnect
2. **Status updates** to "Not Logged In"
3. **Credentials are cleared** for security
4. **Button changes** back to "Login"

## Platform-Specific Details

### Trovo
- **OAuth Flow**: Automatic with ngrok callback
- **Required**: Authorization code from browser
- **Scopes**: chat_connect, chat_send_self, manage_messages, channel_details_self, channel_update_self, user_details_self
- **Redirect URI**: Uses ngrok tunnel (must be running)

### YouTube
- **OAuth Flow**: Automatic with localhost callback
- **Required**: Authorization code from browser  
- **Scopes**: youtube.readonly, youtube.force-ssl
- **Redirect URI**: http://localhost:8080
- **Note**: May require Google account verification

### Twitch
- **OAuth Flow**: Automatic (requires Client ID)
- **Required**: Your Twitch Client ID + authorization code
- **Scopes**: chat:read, chat:edit, user:edit:broadcast, channel:manage:broadcast
- **Redirect URI**: http://localhost:3000
- **Setup**: Create app at https://dev.twitch.tv/console/apps

### Kick
- **OAuth Flow**: Manual token entry
- **Required**: Authorization cookie from browser
- **Steps**:
  1. Log in to Kick.com in browser
  2. Open DevTools (F12)
  3. Go to Application → Cookies
  4. Copy 'Authorization' cookie value
  5. Paste when prompted

### DLive
- **OAuth Flow**: Manual API key entry
- **Required**: DLive API key
- **Steps**:
  1. Go to DLive settings
  2. Generate/copy API key
  3. Paste when prompted

## Configuration Storage

Account data is stored separately in the config file:

```json
{
  "trovo": {
    "streamer_username": "your_streamer_name",
    "streamer_token": "oauth_token_here",
    "streamer_logged_in": true,
    
    "bot_username": "your_bot_name",
    "bot_token": "oauth_token_here",
    "bot_logged_in": true
  }
}
```

## OAuth Flow Diagram

```
User clicks Login
       ↓
Enter Username
       ↓
Browser opens OAuth URL
       ↓
User authorizes on platform
       ↓
Authorization code in URL/callback
       ↓
User copies & pastes code
       ↓
App exchanges code for token (automatic)
       ↓
Token saved to config
       ↓
Status shows "Logged In"
```

## Current Implementation Status

### ✅ Completed
- Dual UI sections for each account type
- Login/Logout buttons with state management
- **Automatic OAuth flows for Trovo, YouTube, Twitch**
- **Authorization code exchange for tokens**
- **Browser-based authentication**
- Credential storage and persistence
- Status indicators with visual feedback
- Username display
- Config integration
- Auto-load on startup
- Platform-specific OAuth configurations
- Manual token entry for Kick & DLive

### 🔄 In Progress
- Automatic callback server (currently uses manual code entry)
- Token refresh for expired OAuth tokens
- Connection status synchronization with chat manager

### 📋 Planned
- Full automatic callback handling (no code copy/paste)
- Account-specific permission validation
- Automatic token refresh
- Connection health monitoring per account
- Account switcher for testing

## Security Notes

- Tokens are stored in the config file (encrypt in production)
- Never share your config file with others
- Use different passwords for streamer and bot accounts
- Regularly rotate your API keys/tokens
- OAuth flows use HTTPS for security
- Authorization codes expire quickly (use immediately)

## Troubleshooting

### "Login button doesn't respond"
- Check if username was entered correctly
- Ensure browser opens for OAuth
- Check console for error messages

### "No authorization code received"
- Check browser URL after authorization
- Code may be in URL parameters (?code=...)
- Copy entire code including special characters

### "Token exchange failed"
- Verify authorization code is correct
- Code may have expired (try again)
- Check internet connection
- For Trovo: Ensure ngrok is running

### "Browser doesn't open"
- Check firewall/antivirus settings
- Try manual URL copy if needed
- Verify platform OAuth is enabled

### "Can't see my username after login"
- Refresh by switching tabs
- Check the log area for confirmation
- Username appears on next startup

## Advanced Usage

### For Developers

#### Adding New Platform OAuth:

1. Add method `startPlatformOAuth(account_type, username)` in `connections_page.py`
2. Configure OAuth parameters (client_id, auth_url, scopes)
3. Implement `exchangeCodeForToken` for the platform
4. Test with both streamer and bot accounts

#### Token Exchange Format:

```python
def exchangeCodeForToken(self, account_type, username, code):
    # Make POST request to token endpoint
    # Include: client_id, client_secret, code, redirect_uri
    # Extract access_token from response
    # Call onOAuthSuccess(account_type, username, token)
```

## Future Enhancements

- Visual connection indicators (green dot when active)
- "Test Connection" button for each account
- Account permission level display
- Quick account switcher
- Multi-bot support (more than one bot account per platform)
- Automatic callback server (eliminate manual code entry)
- OAuth token refresh automation
- Platform API health check

---

**Last Updated:** January 6, 2026
**Version:** 2.0 - Automatic OAuth
