@echo off
chcp 65001 >nul
title 热更新服务器
echo ========================================
echo 正在启动热更新服务器...
echo ========================================
echo.

python simple_file_update_server.py

echo.
echo 服务器已停止
pause
