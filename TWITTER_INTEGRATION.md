# Twitter/X Integration Guide

## Overview
AudibleZenBot now supports Twitter/X integration, allowing you to monitor mentions and interact with your Twitter audience in real-time through the unified chat interface.

## Features
- **Real-time Mentions**: Monitor tweets mentioning your account
- **OAuth 2.0 Authentication**: Secure authentication using Twitter's OAuth 2.0 flow
- **Automatic Token Refresh**: Keeps your session active with automatic token renewal
- **Rate Limit Handling**: Respects Twitter API rate limits
- **Unified Interface**: All Twitter mentions appear in the same chat window as other platforms

## API Credentials

### Current Configuration
- **Client ID**: `YnpWQ2s2Q1VuX1RVWG4wTlNvZTg6MTpjaQ`
- **Client Secret**: `52_s2M2njaNEGOymH0Bym9h7Ry6xPjOY9J4YuHPztrZrPROMZ8`

These credentials are stored in [`core/oauth_handler.py`](core/oauth_handler.py).

## How to Connect

### Step 1: Open Connections Page
1. Launch AudibleZenBot (`python main.py`)
2. Navigate to the **Connections** page
3. Select the **X (Twitter)** tab

### Step 2: Authenticate
1. Enter your Twitter username in the "Username" field
2. Click "Connect & Authorize"
3. You'll be prompted to authenticate via OAuth 2.0
4. Complete the authentication flow in your browser
5. Once authenticated, the bot will automatically start monitoring mentions

### Step 3: View Messages
- All Twitter mentions will appear in the **Chat** page
- Messages show the author's name, tweet content, and timestamp
- Platform icon indicates the source (Twitter/X)

## What Gets Monitored

The Twitter connector monitors:
- **Mentions**: Tweets that mention your @username
- **Replies**: Replies to your tweets
- **Direct mentions**: Any tweet containing @yourusername

## API Details

### Endpoints Used
- **User Lookup**: `GET /2/users/by/username/{username}`
- **Mentions**: `GET /2/users/{id}/mentions`
- **Tweet Posting**: `POST /2/tweets` (for sending messages)

### Polling Interval
- Mentions are checked every **10 seconds**
- Rate limit: 180 requests per 15 minutes (per Twitter's API limits)

### Token Management
- Access tokens are stored in `~/.audiblezenbot/config.json`
- Refresh tokens are automatically used to renew expired access tokens
- Tokens are refreshed every ~50 minutes

## Message Metadata

Each Twitter message includes:
```python
{
    'tweet_id': 'unique_tweet_id',
    'author_id': 'author_user_id',
    'created_at': 'ISO_timestamp',
    'profile_image_url': 'https://...',
    'verified': True/False,
    'badges': []  # Reserved for future badge support
}
```

## Configuration Files

### OAuth Handler
**File**: [`core/oauth_handler.py`](core/oauth_handler.py)
- Contains Twitter API credentials
- Manages OAuth 2.0 authentication flow
- Handles token exchange and refresh

### Twitter Connector
**File**: [`platform_connectors/twitter_connector.py`](platform_connectors/twitter_connector.py)
- Main Twitter integration logic
- Handles API requests and responses
- Manages polling and rate limiting
- Processes incoming mentions

### Chat Manager
**File**: [`core/chat_manager.py`](core/chat_manager.py)
- Integrates Twitter connector with other platforms
- Routes messages to the UI
- Manages mute states

## Troubleshooting

### "No OAuth token provided"
**Problem**: Attempting to connect without authentication
**Solution**: Click "Connect & Authorize" and complete the OAuth flow

### "Could not find user"
**Problem**: Invalid username or API error
**Solution**: 
- Verify the username is correct (no @ symbol needed)
- Check your internet connection
- Verify API credentials are correct

### "Rate limit hit"
**Problem**: Too many API requests
**Solution**: The connector automatically waits when rate limits are hit. Wait 15 minutes for limits to reset.

### No mentions appearing
**Problem**: Connected but not seeing mentions
**Solution**:
- Verify you have recent mentions on Twitter
- Check that the Twitter tab is not muted
- Check console output for errors

## Testing

### Test Script
A test script is provided at [`test_twitter.py`](test_twitter.py):
```bash
python test_twitter.py
```

This script verifies the connector is properly configured and can be initialized.

### Manual Testing
1. Have someone mention your Twitter account
2. Wait up to 10 seconds for the poll
3. The mention should appear in the Chat page
4. Author name, tweet text, and timestamp should all be visible

## Code Structure

### TwitterConnector Class
Main connector that manages the connection lifecycle:
- `connect(username)`: Start monitoring mentions
- `disconnect()`: Stop monitoring
- `send_message(message)`: Post a tweet
- `set_token(token)`: Update OAuth token
- `refresh_access_token()`: Renew access token

### TwitterWorker Class
Background worker thread that:
- Polls Twitter API for new mentions
- Processes incoming tweets
- Manages rate limiting
- Handles token refresh
- Emits signals for new messages

## API Rate Limits

Twitter API v2 Free Tier:
- **Mentions endpoint**: 180 requests per 15 minutes
- **User lookup**: 300 requests per 15 minutes
- **Tweet creation**: 200 requests per 15 minutes

The connector is configured to poll every 10 seconds, using approximately:
- **6 requests per minute**
- **90 requests per 15 minutes**
- Well within rate limits

## Future Enhancements

Potential improvements:
- [ ] Support for Twitter Spaces (audio rooms)
- [ ] Direct message monitoring
- [ ] Tweet threading support
- [ ] Media attachment support
- [ ] Advanced filtering (keywords, hashtags)
- [ ] Multiple account support
- [ ] Webhook-based real-time updates (requires elevated API access)

## Security Notes

- OAuth tokens are stored in user's home directory (`~/.audiblezenbot/config.json`)
- Tokens are not displayed in the UI
- Client secret is embedded in code (typical for installed apps)
- For production deployment, consider using environment variables

## Support

For issues or questions:
1. Check console output for error messages
2. Verify API credentials in [`core/oauth_handler.py`](core/oauth_handler.py)
3. Review Twitter API documentation: https://developer.twitter.com/en/docs/twitter-api
4. Check rate limit status in console output

## Summary

Twitter/X integration is now fully functional and ready to use. Simply authenticate via the Connections page and start monitoring your Twitter mentions in real-time alongside chat from all your other connected platforms!
