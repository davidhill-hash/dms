@echo off
REM Makes Bolt the robot start automatically every time you log in.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0autostart.ps1" enable
pause
