# Standalone Executable - Quick Reference

## For End Users

### First Time Setup

1. **Download** `AudibleZenBot.exe`
2. **Run** the executable (no installation needed!)
3. **First launch**: App creates config folder at `C:\Users\YourName\.audiblezenbot`

### Ngrok Setup (Required for Kick)

1. **Get authtoken**: Visit https://dashboard.ngrok.com/get-started/your-authtoken
2. **Open Settings**: Click ⚙️ icon in sidebar
3. **Paste token**: Enter your ngrok authtoken
4. **Save**: Click "Save Token"
5. **Test**: Click "Test Connection" to verify

### Connecting to Platforms

1. **Click** 🔌 Connections in sidebar
2. **Select** platform tab (Twitch, Kick, YouTube, etc.)
3. **Enter** channel/username
4. **Connect**!

For Kick: Tunnel starts automatically - no manual ngrok needed!

### Viewing Chat

1. **Click** 💬 Chat in sidebar
2. **Messages** appear from all connected platforms
3. **Mute** platforms from Connections page if needed

## For Developers

### Building the Executable

```powershell
# Quick build
.\build_exe.ps1

# Clean build (recommended)
.\build_exe.ps1 -Clean

# Debug mode (with console)
.\build_exe.ps1 -Debug
```

Output: `dist\AudibleZenBot.exe`

### Project Structure

```
AudibleZenBot/
├── main.py                    # Entry point
├── core/
│   ├── ngrok_manager.py      # 🆕 Automatic tunnel management
│   ├── chat_manager.py       # Platform coordination
│   └── config.py             # Settings persistence
├── ui/
│   ├── chat_page.py          # Chat display
│   ├── connections_page.py   # Platform connections
│   └── settings_page.py      # 🆕 Ngrok configuration
├── platform_connectors/
│   ├── kick_connector.py     # 🔄 Updated for auto-ngrok
│   └── ... other connectors
├── AudibleZenBot.spec        # 🆕 PyInstaller config
├── build_exe.ps1             # 🆕 Build script
└── requirements.txt          # 🔄 Updated with pyngrok, PyInstaller
```

### Key Changes from Original

#### Added Files
- `core/ngrok_manager.py` - Manages ngrok tunnels
- `ui/settings_page.py` - Settings UI with ngrok config
- `AudibleZenBot.spec` - PyInstaller specification
- `build_exe.ps1` - Automated build script
- `EXECUTABLE_BUILD.md` - Build documentation
- `NGROK_AUTO_SETUP.md` - Ngrok guide

#### Modified Files
- `main.py` - Initialize NgrokManager, add Settings page
- `core/config.py` - Add ngrok configuration section
- `core/chat_manager.py` - Pass ngrok_manager to connectors
- `platform_connectors/kick_connector.py` - Use NgrokManager
- `requirements.txt` - Add pyngrok, PyInstaller
- `README.md` - Document executable version

#### Original Code Preserved
All original functionality remains intact! The app can still run from source with:
```powershell
python main.py
```

### Testing

```powershell
# Test from source
python main.py

# Test executable
.\dist\AudibleZenBot.exe
```

### Distribution Checklist

- [ ] Build with `.\build_exe.ps1 -Clean`
- [ ] Test on clean VM without Python
- [ ] Verify all platforms connect
- [ ] Test ngrok auto-start for Kick
- [ ] Check Settings page functionality
- [ ] Test disconnect/reconnect
- [ ] Verify cleanup on exit
- [ ] Create release notes
- [ ] Zip or create installer
- [ ] Upload to release page

## Troubleshooting

### Executable doesn't start
- **Windows Defender**: May need to allow app
- **Antivirus**: Add exception for AudibleZenBot.exe
- **Missing VCRUNTIME140.dll**: Install Visual C++ Redistributable

### Ngrok fails
- **Check Settings**: Verify authtoken is configured
- **Test Connection**: Use button in Settings
- **Port conflict**: Close apps using port 8889

### Build fails
- **Dependencies**: Run `pip install -r requirements.txt`
- **Spec file**: Check `AudibleZenBot.spec` for errors
- **Resources**: Ensure `resources/` folder exists

## Version History

**v1.0.0-standalone**
- ✅ Automatic ngrok tunnel management
- ✅ Settings page for configuration
- ✅ Standalone executable build
- ✅ All original features preserved

## Support

- **Build Issues**: See [EXECUTABLE_BUILD.md](EXECUTABLE_BUILD.md)
- **Ngrok Setup**: See [NGROK_AUTO_SETUP.md](NGROK_AUTO_SETUP.md)
- **Platform Setup**: See individual platform guides

## Development Mode vs Executable

| Feature | Development | Executable |
|---------|-------------|------------|
| Python required | ✅ Yes | ❌ No |
| Install dependencies | ✅ Yes | ❌ No |
| Ngrok setup | Manual or Auto | Auto only |
| Startup time | Fast | Slower (extracts) |
| File size | Small | ~150-200MB |
| Updates | Git pull | Download new .exe |
| Debugging | Easy (console) | Use -Debug build |

## Next Steps

**For Users**: 
1. Download executable
2. Configure ngrok
3. Start chatting!

**For Developers**:
1. Review code changes
2. Test locally
3. Build executable
4. Distribute!
