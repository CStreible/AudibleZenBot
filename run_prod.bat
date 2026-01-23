@echo off
REM Launch AudibleZenBot in production mode (clears CI/test flags)
set AUDIBLEZENBOT_CI=
set AUDIBLEZENBOT_ENV=production
echo Starting AudibleZenBot (production)...
call start.bat
