@echo off
title 设置热更新服务器开机启动

echo 正在设置热更新服务器开机启动...
echo 当前目录: %~dp0
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
echo 启动文件夹: %STARTUP_FOLDER%

if not exist "%STARTUP_FOLDER%" mkdir "%STARTUP_FOLDER%"

set BATCH_FILE=%STARTUP_FOLDER%\热更新服务器.bat

echo 创建启动文件: %BATCH_FILE%

echo @echo off > "%BATCH_FILE%"
echo title 美术资源热更新服务器 >> "%BATCH_FILE%"
echo cd /d "%~dp0" >> "%BATCH_FILE%"
echo python simple_file_update_server.py >> "%BATCH_FILE%"

if exist "%BATCH_FILE%" (
    echo.
    echo 设置成功！
    echo 启动文件已创建: %BATCH_FILE%
    echo 服务器将在下次开机时自动启动
    echo.
    echo 测试选项:
    echo [1] 立即测试
    echo [2] 打开启动文件夹
    echo [3] 完成
    echo.
    set /p choice=请选择:
    
    if "%choice%"=="1" call "%BATCH_FILE%"
    if "%choice%"=="2" explorer "%STARTUP_FOLDER%"
) else (
    echo 设置失败！
)

echo.
pause

