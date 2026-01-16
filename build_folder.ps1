# Build script for AudibleZenBot - Folder distribution (faster startup)
# Requires PyInstaller: pip install pyinstaller

Write-Host "Building AudibleZenBot folder distribution..." -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & .\.venv\Scripts\Activate.ps1
}

# Install PyInstaller if not already installed
Write-Host "Checking PyInstaller installation..." -ForegroundColor Cyan
pip install pyinstaller

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }
if (Test-Path ".\AudibleZenBot.spec") { Remove-Item ".\AudibleZenBot.spec" -Force }

# Build the executable (folder mode - faster startup)
Write-Host "Building folder distribution with PyInstaller..." -ForegroundColor Cyan
pyinstaller --name="AudibleZenBot" `
    --onedir `
    --noconsole `
    --windowed `
    --icon="resources\icons\app_icon.ico" `
    --add-data="resources;resources" `
    --hidden-import="PyQt6" `
    --hidden-import="PyQt6.QtCore" `
    --hidden-import="PyQt6.QtGui" `
    --hidden-import="PyQt6.QtWidgets" `
    --hidden-import="PyQt6.QtNetwork" `
    --hidden-import="websocket" `
    --hidden-import="requests" `
    --hidden-import="cloudscraper" `
    --hidden-import="pyngrok" `
    --collect-all="PyQt6" `
    main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Build completed successfully!" -ForegroundColor Green
    Write-Host "Executable location: .\dist\AudibleZenBot\AudibleZenBot.exe" -ForegroundColor Yellow
    Write-Host "`nDistribute the entire 'dist\AudibleZenBot' folder" -ForegroundColor Cyan
    Write-Host "Folder size: $((Get-ChildItem .\dist\AudibleZenBot -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB) MB" -ForegroundColor Cyan
} else {
    Write-Host "`n✗ Build failed!" -ForegroundColor Red
    exit 1
}
