@echo off
chcp 65001 >nul
echo ========================================
echo   TodayHIT QQ Bot 启动脚本
echo ========================================
echo.

echo [1/2] 启动 NapCat...
start "NapCat" cmd /c "cd /d %~dp0NapCat.Shell && launcher.bat"

echo [2/2] 等待 NapCat 启动 (5秒)...
timeout /t 5 /nobreak >nul

echo [2/2] 启动 Bot...
cd /d %~dp0
C:\Users\wfy\.conda\envs\todayhit\python.exe bot.py

pause
