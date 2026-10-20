@echo off
python -X utf8 "%~dp0patch.py" restore
set "MOD_EXIT=%ERRORLEVEL%"
pause
exit /b %MOD_EXIT%
