# Ngrok Auto-Management Guide

AudibleZenBot now includes **automatic ngrok tunnel management**, eliminating the need for manual tunnel setup!

## What is Ngrok?

Ngrok creates secure tunnels from a public URL to your local machine, allowing platforms like Kick (that require webhooks) to send events to your application.

## Features

✅ **Automatic tunnel creation** when connecting to platforms  
✅ **No manual ngrok commands** needed  
✅ **Tunnel health monitoring** and auto-recovery  
✅ **Multi-tunnel support** for multiple platforms  
✅ **Clean shutdown** - tunnels stop automatically  
✅ **Status dashboard** in Settings page  

## Quick Setup

### 1. Get Your Ngrok Auth Token

1. Visit https://dashboard.ngrok.com/signup
2. Sign up for a **free account**
3. Copy your **authtoken** from https://dashboard.ngrok.com/get-started/your-authtoken

### 2. Configure in AudibleZenBot

1. **Launch** AudibleZenBot
2. **Click** the Settings icon (⚙️) in the sidebar
3. **Paste** your ngrok authtoken
4. **Click** "Save Token"
5. **Test** with "Test Connection" button

### 3. Done!

That's it! The app will now automatically:
- Start tunnels when you connect to Kick or other webhook-based platforms
- Use the tunnel URL for webhook configuration
- Monitor tunnel health
- Stop tunnels when you disconnect

## Supported Platforms

### Platforms Requiring Ngrok

| Platform | Port | Purpose | Auto-Managed |
|----------|------|---------|--------------|
| **Kick** | 8889 | Webhooks for real-time chat | ✅ Yes |

### Platforms NOT Requiring Ngrok

| Platform | Connection Method | Ngrok Needed |
|----------|-------------------|--------------|
| **Twitch** | WebSocket (IRC) | ❌ No |
| **YouTube** | API Polling | ❌ No |
| **Trovo** | WebSocket | ❌ No |
| **DLive** | GraphQL WebSocket | ❌ No |
| **Twitter/X** | API | ❌ No |

## Settings Page

The Settings page provides:

### Ngrok Configuration
- **Auth Token**: Your ngrok authentication token
- **Show/Hide**: Toggle token visibility
- **Test Connection**: Verify ngrok is working
- **Auto-start**: Enable automatic tunnel creation (recommended)

### Tunnel Status
- **Active Tunnels**: List of running tunnels with URLs
- **Refresh**: Update tunnel status
- **Stop All**: Manually stop all tunnels (useful for troubleshooting)

## Usage Examples

### Connecting to Kick

**Before (Manual Setup)**:
```powershell
# Terminal 1
ngrok http 8889

# Copy URL from ngrok
# Update Kick webhook URL manually
# Run app in Terminal 2
python main.py
```

**Now (Automatic)**:
1. Configure ngrok token once in Settings
2. Connect to Kick from Connections page
3. Tunnel starts automatically! ✨

### Monitoring Tunnels

View active tunnels in Settings → Tunnel Status:

```
Active Tunnels:

  • kick (http):
    https://abc123.ngrok.io -> localhost:8889
```

## Troubleshooting

### "Ngrok not available" error

**Problem**: Ngrok library not installed  
**Solution**: Install dependencies

```powershell
pip install -r requirements.txt
```

### "Please configure auth token" error

**Problem**: No ngrok authtoken configured  
**Solution**: Add token in Settings page

### "Failed to start tunnel" error

**Possible causes**:
1. **Invalid authtoken**: Double-check token from ngrok dashboard
2. **Port already in use**: Close other apps using port 8889
3. **Network firewall**: Allow ngrok through firewall
4. **Ngrok service down**: Check https://status.ngrok.com

**Solutions**:
```powershell
# Check if port is in use
netstat -ano | findstr :8889

# Kill process on port 8889
Stop-Process -Id <PID>
```

### Tunnel disconnects randomly

**Problem**: Free ngrok tunnels have 2-hour session limit  
**Solution**: 
- Upgrade to ngrok paid plan for unlimited sessions
- Reconnect when needed (app will auto-reconnect)

### Multiple tunnels conflict

**Problem**: Only one tunnel per port allowed  
**Solution**: Use Settings → "Stop All Tunnels" to reset

## Advanced Configuration

### Custom Ngrok Region

Edit `config.json` (in `~/.audiblezenbot/`):

```json
{
  "ngrok": {
    "auth_token": "your_token",
    "region": "us"  // Options: us, eu, ap, au, sa, jp, in
  }
}
```

### Manual Tunnel Control

For testing, you can manually control tunnels in Settings:

1. **Start tunnel**: Connect to platform
2. **View URL**: Check Tunnel Status section
3. **Stop tunnel**: Disconnect platform or use "Stop All Tunnels"

### Ngrok Configuration File

Ngrok uses `~/.ngrok2/ngrok.yml` for advanced configuration. Example:

```yaml
authtoken: REPLACE_WITH_NGROK_AUTHTOKEN
region: us
tunnels:
  kick:
    proto: http
    addr: 8889
```

## Free vs Paid Ngrok

### Free Tier (Sufficient for most users)
✅ Unlimited tunnel startups  
✅ 40 connections/minute  
✅ HTTP/TCP tunnels  
⚠️ 2-hour session timeout  
⚠️ Random subdomain  

### Paid Tier ($8/month)
✅ No session timeout  
✅ Custom subdomain  
✅ More connections  
✅ IP whitelisting  

For casual streaming, **free tier works great**!

## Security Considerations

### Protect Your Authtoken
- ⚠️ **Never share** your ngrok authtoken
- ⚠️ **Don't commit** `config.json` with token to Git
- ✅ **Regenerate** token if exposed (ngrok dashboard)

### Webhook Security
- ✅ Ngrok URLs use HTTPS encryption
- ✅ Only your platforms can send to webhook URL
- ✅ Tunnels stop when app closes

### Firewall Rules
- Ngrok connects **outbound** to ngrok.com
- No **inbound** firewall rules needed
- Safe for home networks

## Technical Details

### How It Works

1. **App starts** → NgrokManager initializes
2. **Connect to Kick** → App requests tunnel for port 8889
3. **NgrokManager** → Starts ngrok subprocess
4. **Tunnel created** → Public URL obtained (e.g., https://abc123.ngrok.io)
5. **Kick connector** → Uses tunnel URL for webhook subscription
6. **Kick sends events** → ngrok → localhost:8889 → Your app
7. **Disconnect** → Tunnel stops automatically

### Monitoring

NgrokManager checks tunnel health every 30 seconds by querying:
```
http://localhost:4040/api/tunnels
```

If a tunnel fails, the app attempts to reconnect automatically.

### Ports Used

| Port | Purpose |
|------|---------|
| 8889 | Kick webhook server |
| 4040 | Ngrok local API (monitoring) |
| Various | Ngrok control connection (outbound) |

## For Developers

### Accessing NgrokManager

```python
# In a connector
if self.ngrok_manager and self.ngrok_manager.is_available():
    url = self.ngrok_manager.start_tunnel(port=8889, name="kick")
    if url:
        print(f"Tunnel: {url}")
```

### Adding New Platform with Webhooks

1. Add to `PLATFORM_TUNNEL_REQUIREMENTS` in `core/ngrok_manager.py`
2. Initialize `self.ngrok_manager = None` in connector
3. Start tunnel in `connect()` method
4. Stop tunnel in `disconnect()` method

Example:
```python
def connect(self, username):
    if self.ngrok_manager:
        self.webhook_url = self.ngrok_manager.start_tunnel(5000)
    # ... rest of connection logic
```

## Support & Links

- **Ngrok Dashboard**: https://dashboard.ngrok.com
- **Ngrok Documentation**: https://ngrok.com/docs
- **Ngrok Status**: https://status.ngrok.com
- **Get Authtoken**: https://dashboard.ngrok.com/get-started/your-authtoken

## FAQ

**Q: Do I need ngrok for all platforms?**  
A: No, only Kick requires it. Twitch, YouTube, etc. use different connection methods.

**Q: Can I use my existing ngrok installation?**  
A: Yes! The app uses the `pyngrok` library which handles ngrok automatically.

**Q: What if I already have ngrok running?**  
A: The app manages its own tunnels. Your existing tunnels won't conflict.

**Q: Is my authtoken stored securely?**  
A: Yes, it's stored in `~/.audiblezenbot/config.json` with proper file permissions.

**Q: Can I run multiple instances of the app?**  
A: Each instance needs different ports. Only one Kick connection per machine.

**Q: Will this work on Mac/Linux?**  
A: Yes! NgrokManager is cross-platform compatible.

---

**Need Help?** Check the Settings page for tunnel status and use "Test Connection" to verify your setup!
