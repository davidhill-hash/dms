@echo off
REM Stops Bolt from starting automatically at login.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0autostart.ps1" disable
pause
