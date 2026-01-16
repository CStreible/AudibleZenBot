# Building AudibleZenBot Standalone Executable

This guide explains how to build AudibleZenBot as a standalone Windows executable that includes automatic ngrok tunnel management.

## Prerequisites

1. **Python 3.8+** installed
2. **Virtual environment** (recommended)
3. **All dependencies** installed from `requirements.txt`

## Quick Build

### Using the Build Script (Recommended)

The easiest way to build the executable:

```powershell
# Clean build (removes old builds first)
.\build_exe.ps1 -Clean

# Regular build
.\build_exe.ps1

# Build with debug console visible
.\build_exe.ps1 -Debug

# Build as a folder instead of single file
.\build_exe.ps1 -OneFolder
```

### Manual Build

If you prefer to build manually:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install/update dependencies
pip install -r requirements.txt

# Build using the spec file
pyinstaller AudibleZenBot.spec
```

## Build Output

After a successful build:

- **One-File Mode** (default): `dist\AudibleZenBot.exe` (~150-200 MB)
- **One-Folder Mode**: `dist\AudibleZenBot\` (folder with executable and dependencies)

## Build Options

### One-File vs One-Folder

**One-File (Default)**
- Single executable file
- Slower startup (extracts to temp on launch)
- Easier distribution
- Larger file size

**One-Folder**
- Faster startup
- Multiple files in a folder
- Slightly smaller total size
- Harder to distribute

### Debug Mode

Use `-Debug` flag to build with console output visible:

```powershell
.\build_exe.ps1 -Debug
```

This helps troubleshoot issues during development.

## Configuration Files

The executable uses the following configuration:

### AudibleZenBot.spec

PyInstaller specification file that defines:
- Dependencies to bundle
- Resource files to include
- Hidden imports
- Executable options

Key sections:
```python
datas=[
    ('resources', 'resources'),  # Include badges, icons
    ('core/badges', 'core/badges'),
]

hiddenimports=[
    'pyngrok',  # Ngrok management
    'PyQt6.QtWebEngineCore',  # Web engine
    # ... other imports
]
```

## Troubleshooting

### Build Fails with "Module not found"

Add the missing module to `hiddenimports` in `AudibleZenBot.spec`:

```python
hiddenimports=[
    # ... existing imports
    'your_missing_module',
]
```

### Executable is too large

1. Remove unused platforms in `platform_connectors/`
2. Add packages to `excludes` in the spec file:

```python
excludes=[
    'matplotlib',
    'numpy',
    'pandas',
]
```

### Resources not found at runtime

Ensure resources are added to `datas` in the spec file:

```python
datas=[
    ('path/to/resource', 'destination/in/bundle'),
]
```

### Console shows errors

Build with `-Debug` flag to see detailed output:

```powershell
.\build_exe.ps1 -Debug
```

## Distribution

### Single File Distribution

1. Build in one-file mode (default)
2. Distribute `dist\AudibleZenBot.exe`
3. Users need:
   - Windows 10/11
   - No Python installation required
   - Ngrok auth token (get from https://dashboard.ngrok.com)

### Installation Package (Optional)

For a professional installer, use tools like:
- **Inno Setup**: Creates Windows installers
- **NSIS**: Nullsoft Scriptable Install System
- **WiX Toolset**: Windows Installer XML

## First-Run for End Users

When users run the executable for the first time:

1. **Launch** `AudibleZenBot.exe`
2. **Navigate** to Settings page (⚙️ icon)
3. **Get ngrok auth token** from https://dashboard.ngrok.com/get-started/your-authtoken
4. **Paste token** in Settings and click "Save Token"
5. **Connect** to platforms from Connections page

The app will automatically:
- Start ngrok tunnels when needed
- Configure webhook URLs
- Monitor tunnel health
- Stop tunnels on disconnect

## Advanced Configuration

### Custom Icon

Replace or add `resources/icons/app_icon.ico` before building.

### Version Information

Edit `AudibleZenBot.spec` to add version info:

```python
version='1.0.0',
description='Multi-Platform Streaming Chat Bot',
company_name='Your Company',
```

### Antivirus False Positives

Some antivirus software may flag PyInstaller executables. To minimize this:

1. **Code sign** the executable (requires certificate)
2. **Upload** to VirusTotal and report false positives
3. **Distribute** with checksum for verification

## Testing the Executable

Before distributing:

1. **Test on clean VM** without Python installed
2. **Verify all platforms** connect correctly
3. **Test ngrok tunnels** start/stop properly
4. **Check Settings page** saves configuration
5. **Test disconnection** and reconnection
6. **Verify cleanup** on app close

## Build Performance

Typical build times:
- **First build**: 2-5 minutes
- **Subsequent builds**: 1-3 minutes
- **With -Clean flag**: 3-6 minutes

Build sizes:
- **One-file executable**: ~150-200 MB
- **One-folder bundle**: ~200-250 MB (total)

## Continuous Integration

For automated builds:

```powershell
# CI/CD script example
.\build_exe.ps1 -Clean
if ($LASTEXITCODE -eq 0) {
    # Upload dist\AudibleZenBot.exe to release
}
```

## Support

For build issues:
1. Check PyInstaller documentation: https://pyinstaller.org/
2. Review the spec file for configuration
3. Test with `-Debug` flag
4. Check `build\` folder for logs

## Updates

To update the executable:
1. Update source code
2. Update version in documentation
3. Rebuild with `build_exe.ps1 -Clean`
4. Test thoroughly
5. Distribute new version
