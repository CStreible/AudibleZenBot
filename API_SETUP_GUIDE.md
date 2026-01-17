# Platform API Setup Guide

This guide explains how to get API credentials for each streaming platform to enable real chat connectivity.

## Quick Start

For **demo mode**, you don't need any credentials. Just enter a username and click Connect.

For **real connections**, follow the platform-specific instructions below.

---

## 🎮 Twitch

### Getting OAuth Token

**Option 1: Using Twitch CLI (Recommended)**
1. Install Twitch CLI: https://github.com/twitchdev/twitch-cli
2. Run: `twitch token -u -s 'chat:read chat:edit'`
3. Copy the OAuth token

**Option 2: Manual Generation**
1. Go to: https://twitchtokengenerator.com/
2. Select scopes: `chat:read`, `chat:edit`
3. Click "Generate Token"
4. Copy the access token

**Option 3: Create Your Own App**
1. Go to https://dev.twitch.tv/console/apps
2. Click "Register Your Application"
3. Fill in:
   - Name: AudibleZenBot
   - OAuth Redirect URLs: http://localhost:3000
   - Category: Chat Bot
4. Get your Client ID and generate a token

### Required Scopes
- `chat:read` - Read chat messages
- `chat:edit` - Send chat messages (optional)

### Using in App
1. Go to Connections → Twitch tab
2. Enter your Twitch channel name
3. Paste your OAuth token (without 'oauth:' prefix)
4. Click Connect

---

## ▶️ YouTube

### Getting API Credentials

**Step 1: Create a Google Cloud Project**
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Name it "AudibleZenBot"

**Step 2: Enable YouTube Data API v3**
1. Go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click "Enable"

**Step 3: Get API Key (Read-only)**
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "API Key"
3. Copy the API key
4. (Optional) Restrict the key to YouTube Data API v3

**Step 4: OAuth for Full Access (Optional)**
1. Go to "Create Credentials" → "OAuth client ID"
2. Choose "Desktop app"
3. Download the JSON file
4. Use the Client ID and Client Secret

### Required Scopes
- `https://www.googleapis.com/auth/youtube.readonly`
- `https://www.googleapis.com/auth/youtube.force-ssl` (for sending messages)

### Using in App
1. Go to Connections → YouTube tab
2. Enter your YouTube Channel ID
   - Find it at: https://www.youtube.com/account_advanced
3. Paste your API key or OAuth token
4. Click Connect

**Note:** You must have an active live stream for chat to work!

---

## 🎮 Trovo

### Getting Access Token

1. Go to https://developer.trovo.live/
2. Create a developer account
3. Register your application:
   - Name: AudibleZenBot
   - Redirect URI: http://localhost:3000
4. Get your Client ID
5. Generate an access token with chat permissions

### Required Permissions
- `chat_send_self` - Send messages
- `chat_connect` - Connect to chat

### Using in App
1. Go to Connections → Trovo tab
2. Enter your Trovo username
3. Paste your access token
4. Click Connect

---

## ⚽ Kick

### Getting Credentials

**Note:** Kick has limited public API documentation. Options:

**Option 1: Direct Connection (No Auth Required)**
- Simply enter channel name
- Connect as anonymous viewer
- Read-only access

**Option 2: Browser Cookies Method**
1. Log into Kick.com in your browser
2. Open Developer Tools (F12)
3. Go to Application → Cookies
4. Copy relevant authentication cookies
5. Use in app

### Using in App
1. Go to Connections → Kick tab
2. Enter the Kick channel name
3. Leave token empty or enter auth cookie
4. Click Connect

---

## 🎥 DLive

### Getting Access Token

1. Go to https://dlive.tv/
2. Sign in to your account
3. Open Developer Tools (F12)
4. Go to Network tab
5. Look for GraphQL requests
6. Copy the Authorization header token

**Alternative: DLive API Key**
1. Contact DLive support for API access
2. Request an API key for chat bot

### Using in App
1. Go to Connections → DLive tab
2. Enter the DLive username
3. Paste your access token
4. Click Connect

---

## 🐦 X (Twitter)

### Getting OAuth Credentials

**Step 1: Create Twitter App**
1. Go to https://developer.twitter.com/
2. Apply for a developer account (if needed)
3. Create a new app in the dashboard
4. Fill in:
   - App name: AudibleZenBot
   - Description: Multi-platform chat bot
   - Website: http://localhost:3000

**Step 2: Get API Keys**
1. Go to your app's "Keys and tokens" tab
2. Copy:
   - API Key (Consumer Key)
   - API Secret Key (Consumer Secret)
   - Bearer Token

**Step 3: Enable OAuth 2.0**
1. Go to "User authentication settings"
2. Set OAuth 2.0 settings
3. Add redirect URI: http://localhost:3000
4. Set permissions: Read

### Required Scopes
- `tweet.read`
- `users.read`
- `offline.access`

### Using in App
1. Go to Connections → X (Twitter) tab
2. Enter your Twitter username
3. Paste your Bearer Token or OAuth token
4. Click Connect

---

## 💡 Tips

### Security Best Practices
1. **Never share your tokens publicly**
2. **Store tokens securely** - AudibleZenBot encrypts tokens locally
3. **Rotate tokens regularly**
4. **Use minimum required permissions**
5. **Revoke unused tokens**

### Troubleshooting

**"Authentication failed" error:**
- Verify token is correct and not expired
- Check token has required scopes/permissions
- Ensure platform account is in good standing

**"No active stream found" (YouTube):**
- Make sure you have a live stream running
- Verify Channel ID is correct
- Check stream privacy settings

**Connection drops randomly:**
- Check internet connection
- Verify token hasn't expired
- Platform may have rate limits - wait and retry

**Messages not appearing:**
- Check platform isn't muted in app
- Verify chat is actually active on platform
- Check connection status in platform tab

### Rate Limits

Each platform has rate limits:
- **Twitch:** ~20 messages/30 seconds
- **YouTube:** 10,000 requests/day (read), lower for write
- **Trovo:** Varies by account type
- **Kick:** Unknown, be conservative
- **DLive:** Varies
- **Twitter:** Varies by API tier

### Demo Mode

If you don't have credentials:
1. Leave the token field empty
2. Enter any username
3. Click Connect
4. The app will show demo messages

This lets you test the UI without real connections.

---

## 🔐 Token Storage

AudibleZenBot stores tokens in:
```
%USERPROFILE%\.audiblezenbot\config.json
```

**Important:**
- Tokens are stored locally only
- No tokens are transmitted to third parties
- Config file should be kept private
- Add to .gitignore if version controlling

### Manual Token Management

You can manually edit the config file:

```json
{
  "platforms": {
    "twitch": {
      "username": "your_channel",
      "oauth_token": "REPLACE_WITH_YOUR_TOKEN"
    }
  }
}
```

---

## 📚 Additional Resources

### Official Documentation
- **Twitch:** https://dev.twitch.tv/docs/
- **YouTube:** https://developers.google.com/youtube/v3
- **Trovo:** https://developer.trovo.live/docs
- **Kick:** Limited documentation available
- **DLive:** Community resources
- **Twitter:** https://developer.twitter.com/

### Community Support
- Platform-specific subreddits
- Developer Discord servers
- Stack Overflow

---

## ⚠️ Legal & Compliance

- Respect each platform's Terms of Service
- Follow API usage guidelines
- Don't spam or abuse chat features
- Protect user privacy
- Comply with rate limits

---

**Last Updated:** December 30, 2025
