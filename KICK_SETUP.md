# Kick Integration Setup Guide

## Overview

Kick integration now uses the **official Kick Developer API** with OAuth2 and Webhooks.

**Status**: ✅ Fully functional with webhook setup

## Current Implementation

- ✅ OAuth2 App Access Token (client credentials flow)
- ✅ Channel info retrieval (with Cloudflare bypass)
- ✅ Webhook server for real-time chat messages
- ✅ Chat message sending
- ✅ Full metadata (badges, colors, emotes, timestamps)

## Prerequisites

### 1. Kick Developer App

Your app credentials are already configured:
- **Client ID**: `01KDPP3YN4SB6ZMSV6R6HM12C7`
- **Client Secret**: `da4f8c91298805bb2b851432634a10f5275f6e381b05aef189899bf265df1297`

### 2. Enable Webhooks

Kick's real-time chat API requires **webhooks**, which need a publicly accessible URL.

#### Option A: Using ngrok (Recommended for testing)

1. **Download ngrok**: https://ngrok.com/download
2. **Create free account** (optional but recommended for persistent URLs)
3. **Run ngrok**:
   ```bash
   ngrok http 8889
   ```
4. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok-free.app`)
5. **Configure in Kick**:
   - Go to https://kick.com/settings/developer
   - Click "Edit" on your app
   - Set **Webhook URL**: `https://abc123.ngrok-free.app`
   - **Enable the webhook toggle**
   - Save
6. **Restart AudibleZenBot**

#### Option B: Using Cloudflare Tunnel (Better for production)

1. **Install cloudflared**: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
2. **Run tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8889
   ```
3. **Use the provided URL** in Kick Developer settings (same as ngrok steps 5-6)

#### Option C: Public Server

If you have a VPS/cloud server:
1. Deploy AudibleZenBot to your server
2. Configure firewall to allow port 8889
3. Use your server's public URL in Kick Developer settings

## How It Works

```
┌─────────────┐
│ AudibleZen  │ 1. Get OAuth Token
│    Bot      ├──────────────────────►┌──────────────┐
│             │                        │              │
│             │ 2. Subscribe to events │   Kick API   │
│             │◄───────────────────────┤              │
│             │                        │  id.kick.com │
└─────┬───────┘                        │ api.kick.com │
      │                                └──────────────┘
      │ 3. Start webhook server                │
      │    (port 8889)                         │
      │                                        │
      │        4. Chat events via webhook      │
      │◄───────────────────────────────────────┘
      │
      │ 5. Display in UI
      ▼
   ┌─────┐
   │ GUI │
   └─────┘
```

## Testing

1. **Start ngrok**: `ngrok http 8889`
2. **Copy the HTTPS URL** from ngrok output
3. **Configure webhook** in Kick Developer settings
4. **Launch AudibleZenBot**
5. **Check console output**:
   ```
   ✓ Kick: Got App Access Token (expires in 5184000s)
   ✓ Kick: Channel 'YourChannel' user_id = 123456
   ✓ Kick: Webhook server started on port 8889
   ✓ Kick: Subscribed to chat.message.sent
   ✓ Kick: Connected to channel 'YourChannel'
   ```
6. **Send a test message** in Kick chat
7. **Message should appear** in AudibleZenBot

## Troubleshooting

### "webhook not enabled for app"
- Go to https://kick.com/settings/developer
- Edit your app
- Toggle "Enable Webhooks" to ON
- Set the webhook URL
- Save and restart bot

### "Failed to get channel info: 403"
- This is Cloudflare protection (expected)
- Fixed automatically using cloudscraper
- If still failing, try a different channel name

### Webhook not receiving messages
1. **Check ngrok is running**: Terminal should show "Forwarding https://..."
2. **Verify webhook URL**: Should match ngrok URL exactly (including https://)
3. **Check Kick Developer settings**: Webhook toggle should be ON
4. **Test ngrok URL**: Visit it in browser - should see "404 Not Found" (normal)
5. **Check bot console**: Should show "Webhook server started on port 8889"

### Messages not appearing in UI
- Check console for "Error handling chat message"
- Verify signal connections in connections_page.py
- Restart the application

## API Documentation

- **Official Docs**: https://docs.kick.com/
- **OAuth Flow**: https://docs.kick.com/getting-started/generating-tokens-oauth2-flow
- **Events API**: https://docs.kick.com/events/introduction
- **Webhooks**: https://docs.kick.com/events/subscribe-to-events

## Scopes Used

- `events:subscribe`: Subscribe to chat message events
- `chat:write`: Send chat messages (future feature)

## Future Improvements

- [ ] User OAuth flow for sending messages as user (not bot)
- [ ] Handle webhook signature verification
- [ ] Auto-reconnect on token expiration
- [ ] Support for other events (follows, subs, etc.)
- [ ] ngrok integration (auto-start with bot)

## Notes

- **App Access Token** expires after 60 days (5184000 seconds)
- Webhook URL must be **HTTPS** (not HTTP)
- ngrok free tier has **2-hour session limit** (reconnect required)
- Kick may rate-limit excessive API calls
- Maximum 1,000 chat.message.sent subscriptions for unverified apps

## Comparison: Old vs New Implementation

### Old (Pusher WebSocket)
- ❌ Undocumented Pusher cluster
- ❌ "Not in this cluster" errors
- ❌ Cloudflare blocks API requests
- ❌ No official documentation

### New (Official API + Webhooks)
- ✅ Official Kick Developer API
- ✅ Full documentation
- ✅ OAuth2 authentication
- ✅ Reliable webhook delivery
- ✅ Future-proof
