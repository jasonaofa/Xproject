@echo off
title 美术资源热更新服务器（后台启动）
echo 🚀 正在后台启动美术资源热更新服务器...
cd /d "%~dp0"
echo 📍 工作目录: %~dp0
echo 🔄 启动服务器中...
start /min "" python simple_file_update_server.py
echo ✅ 热更新服务器已在后台启动
echo 📡 服务器将在后台运行，可通过任务管理器查看python进程
echo 🌐 局域网地址将自动检测并显示
timeout /t 3 >nul
exit

