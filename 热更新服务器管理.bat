@echo off
chcp 65001 >nul
title 美术资源热更新服务器管理工具

:menu
cls
echo ═══════════════════════════════════════
echo     美术资源热更新服务器管理工具
echo ═══════════════════════════════════════
echo.
echo 当前时间: %date% %time%
echo 工作目录: %~dp0
echo.
echo 请选择操作:
echo [1] 启动热更新服务器
echo [2] 停止热更新服务器  
echo [3] 重启热更新服务器
echo [4] 查看服务器状态
echo [5] 查看服务器日志
echo [0] 退出
echo.
set /p choice=请输入选择 (0-5): 

if "%choice%"=="1" goto start_server
if "%choice%"=="2" goto stop_server
if "%choice%"=="3" goto restart_server
if "%choice%"=="4" goto status_server
if "%choice%"=="5" goto log_server
if "%choice%"=="0" goto exit
goto menu

:start_server
cls
echo 🚀 正在启动热更新服务器...
cd /d "%~dp0"
tasklist /fi "imagename eq python.exe" /fi "windowtitle eq *simple_file_update_server*" 2>nul | find /i "python.exe" >nul
if not errorlevel 1 (
    echo ⚠️ 服务器似乎已经在运行中
    pause
    goto menu
)
echo 📡 启动服务器中...
start "" python simple_file_update_server.py
timeout /t 2 >nul
echo ✅ 服务器启动完成
pause
goto menu

:stop_server
cls
echo 🛑 正在停止热更新服务器...
taskkill /f /im python.exe /fi "windowtitle eq *simple_file_update_server*" 2>nul
if errorlevel 1 (
    echo ⚠️ 未找到正在运行的服务器进程
) else (
    echo ✅ 服务器已停止
)
pause
goto menu

:restart_server
cls
echo 🔄 正在重启热更新服务器...
call :stop_server
timeout /t 1 >nul
call :start_server
goto menu

:status_server
cls
echo 📊 检查服务器状态...
tasklist /fi "imagename eq python.exe" | find /i "python.exe" >nul
if errorlevel 1 (
    echo ❌ 服务器未运行
) else (
    echo ✅ 发现Python进程正在运行
    tasklist /fi "imagename eq python.exe"
)
echo.
netstat -an | find ":8002" >nul
if errorlevel 1 (
    echo ❌ 端口8002未被占用
) else (
    echo ✅ 端口8002正在使用中
    netstat -an | find ":8002"
)
pause
goto menu

:log_server
cls
echo 📋 查看最近的服务器活动...
echo 注意: 这里显示的是实时日志，按Ctrl+C返回菜单
pause
python simple_file_update_server.py
goto menu

:exit
echo 👋 再见！
exit

