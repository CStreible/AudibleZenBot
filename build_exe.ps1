# Build AudibleZenBot Executable
# This script builds a standalone Windows executable using PyInstaller

param(
    [switch]$Clean,
    [switch]$OneFolder,
    [switch]$Debug
)

Write-Host "`n=== AudibleZenBot Build Script ===" -ForegroundColor Cyan
Write-Host "Building standalone executable...`n" -ForegroundColor Cyan

# Activate virtual environment if it exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "[1/5] Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "[!] Warning: Virtual environment not found. Using system Python." -ForegroundColor Yellow
}

# Install/update dependencies
Write-Host "`n[2/5] Checking dependencies..." -ForegroundColor Yellow
$requirementsExists = Test-Path ".\requirements.txt"
if ($requirementsExists) {
    Write-Host "Installing requirements..." -ForegroundColor Gray
    pip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
}

# Clean previous builds if requested
if ($Clean) {
    Write-Host "`n[3/5] Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path ".\build") {
        Remove-Item -Recurse -Force ".\build"
        Write-Host "Removed build directory" -ForegroundColor Gray
    }
    if (Test-Path ".\dist") {
        Remove-Item -Recurse -Force ".\dist"
        Write-Host "Removed dist directory" -ForegroundColor Gray
    }
    Write-Host "Clean complete" -ForegroundColor Green
} else {
    Write-Host "`n[3/5] Skipping clean (use -Clean to remove old builds)" -ForegroundColor Yellow
}

# Build executable
Write-Host "`n[4/5] Building executable with PyInstaller..." -ForegroundColor Yellow

$buildArgs = @()

if ($Debug) {
    $buildArgs += "--debug=all"
    $buildArgs += "--console"
    Write-Host "Debug mode enabled - console will be visible" -ForegroundColor Gray
}

if ($OneFolder) {
    # Modify spec file temporarily for one-folder mode
    Write-Host "Building in one-folder mode..." -ForegroundColor Gray
    $buildArgs += "main.py"
    $buildArgs += "--name=AudibleZenBot"
    $buildArgs += "--windowed"
    $buildArgs += "--onedir"
} else {
    # Use the spec file for one-file mode (default)
    Write-Host "Building in one-file mode..." -ForegroundColor Gray
    $buildArgs += "AudibleZenBot.spec"
}

# Add common arguments
$buildArgs += "--noconfirm"

# Run PyInstaller
pyinstaller @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Build completed successfully!" -ForegroundColor Green

# Show output location
Write-Host "`n[5/5] Build Output:" -ForegroundColor Yellow
if (Test-Path ".\dist\AudibleZenBot.exe") {
    $exePath = Resolve-Path ".\dist\AudibleZenBot.exe"
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Host "Executable: $exePath" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($exeSize, 2)) MB" -ForegroundColor Green
} elseif (Test-Path ".\dist\AudibleZenBot") {
    $folderPath = Resolve-Path ".\dist\AudibleZenBot"
    Write-Host "Build folder: $folderPath" -ForegroundColor Green
} else {
    Write-Host "[!] Output not found in expected location" -ForegroundColor Red
}

Write-Host "`n=== Build Complete ===" -ForegroundColor Cyan
Write-Host "To test the executable:" -ForegroundColor Gray
Write-Host "  .\dist\AudibleZenBot.exe`n" -ForegroundColor White

# Optional: Run the executable
$response = Read-Host "Do you want to run the executable now? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "`nLaunching AudibleZenBot..." -ForegroundColor Cyan
    if (Test-Path ".\dist\AudibleZenBot.exe") {
        Start-Process ".\dist\AudibleZenBot.exe"
    } elseif (Test-Path ".\dist\AudibleZenBot\AudibleZenBot.exe") {
        Start-Process ".\dist\AudibleZenBot\AudibleZenBot.exe"
    }
}
