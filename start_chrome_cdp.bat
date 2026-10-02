@echo off
title Start Chrome for PAN Portal Automation (Port 9222)
echo =========================================================
echo Launching Chrome with Remote Debugging (Port 9222)...
echo =========================================================
echo.

set CHROME_PATH=""

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if %CHROME_PATH%=="" (
    echo [ERROR] Google Chrome could not be found in standard paths.
    echo Please start Chrome manually with:
    echo chrome.exe --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome_automation_profile"
    pause
    exit /b 1
)

start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome_automation_profile"
echo Chrome launched with remote debugging port 9222!
echo You can now navigate to your PAN portal, log in, and use the commands in chat.
echo.
timeout /t 3 >nul
