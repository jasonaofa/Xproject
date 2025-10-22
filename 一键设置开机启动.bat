@echo off
chcp 65001 >nul
title 一键设置热更新服务器开机启动

echo =======================================
echo     一键设置热更新服务器开机启动
echo =======================================
echo.
echo 🔧 正在设置开机启动...
echo 📍 当前目录: %~dp0
echo.

:: 创建启动批处理文件
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set BATCH_FILE=%STARTUP_FOLDER%\美术资源热更新服务器.bat

echo 📁 启动文件夹: %STARTUP_FOLDER%
echo 📄 启动文件: %BATCH_FILE%
echo.

:: 创建启动文件夹（如果不存在）
if not exist "%STARTUP_FOLDER%" (
    echo 📁 创建启动文件夹...
    mkdir "%STARTUP_FOLDER%"
)

:: 创建启动批处理内容
echo 📝 创建启动批处理文件...
(
echo @echo off
echo title 美术资源热更新服务器
echo cd /d "%~dp0"
echo echo 启动美术资源热更新服务器...
echo echo 工作目录: %~dp0
echo echo 启动服务器中...
echo start /min "" python simple_file_update_server.py
echo echo 热更新服务器已在后台启动
echo timeout /t 2 ^>nul
) > "%BATCH_FILE%"

if exist "%BATCH_FILE%" (
    echo ✅ 设置成功！
    echo.
    echo 📋 设置详情:
    echo    - 启动文件已创建: %BATCH_FILE%
    echo    - 服务器将在下次开机时自动启动
    echo    - 服务器将在后台运行，不会显示窗口
    echo.
    echo 🧪 测试选项:
    echo    [1] 立即测试启动
    echo    [2] 打开启动文件夹查看
    echo    [3] 完成设置
    echo.
    set /p test_choice=请选择 (1-3): 
    
    if "!test_choice!"=="1" (
        echo 🔄 测试启动...
        call "%BATCH_FILE%"
    ) else if "!test_choice!"=="2" (
        echo 📂 打开启动文件夹...
        explorer "%STARTUP_FOLDER%"
    )
    
    echo.
    echo ✅ 设置完成！热更新服务器将在下次开机时自动启动。
) else (
    echo ❌ 设置失败！请检查权限或手动设置。
)

echo.
pause
