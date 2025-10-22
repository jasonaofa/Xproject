@echo off
title 美术资源热更新服务器
echo 🚀 正在启动美术资源热更新服务器...
echo 📍 工作目录: %~dp0
cd /d "%~dp0"
echo 🔄 启动服务器中...
python simple_file_update_server.py
pause

