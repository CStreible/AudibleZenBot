@echo off
REM Launch AudibleZenBot in test/CI mode (sets CI flags so connectors avoid network)
set AUDIBLEZENBOT_CI=1
set AUDIBLEZENBOT_ENV=test
echo Starting AudibleZenBot (test/CI mode)...
call start.bat
