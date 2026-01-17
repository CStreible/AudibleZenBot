@echo off
REM AudibleZenBot Startup Script

echo ========================================
echo   AudibleZenBot - Multi-Platform Chat
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from python.org
    pause
    exit /b 1
)

REM Prefer .venv if present, otherwise fall back to venv (create .venv if none exist)
set "VENV_DIR="
if exist ".venv" goto :use_dotvenv
if exist "venv" goto :use_venv

echo Creating virtual environment (.venv)...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
set "VENV_DIR=.venv"
goto :after_venv_choice

:use_dotvenv
set "VENV_DIR=.venv"
goto :after_venv_choice

:use_venv
set "VENV_DIR=venv"

:after_venv_choice

REM Activate chosen virtual environment
echo Activating virtual environment (%VENV_DIR%)...
call "%VENV_DIR%\Scripts\activate.bat"

REM Install/update dependencies
if not exist "%VENV_DIR%\Scripts\pip.exe" (
    echo ERROR: pip not found in virtual environment (%VENV_DIR%)
    pause
    exit /b 1
)

echo.
echo Checking dependencies...
pip show PyQt6 >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed.
)

echo.
echo Starting AudibleZenBot...
echo.
python main.py

REM Deactivate virtual environment
deactivate

if errorlevel 1 (
    echo.
    echo Application exited with error.
    pause
)
