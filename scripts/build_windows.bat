@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
  echo Windows installer build failed. Read the message above.
  pause
  exit /b 1
)
echo Windows installer created in dist\Container-Workbench-Setup.exe
pause
