@echo off
chcp 65001 > nul
title 资源管理器打包工具

echo.
echo ============================================================
echo                  资源管理器自动打包工具
echo ============================================================
echo.
echo 正在启动打包程序...
echo.

:: 检查Python是否可用
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请确保已安装Python并添加到PATH
    pause
    exit /b 1
)

:: 检查主文件是否存在
if not exist "art_resource_manager.py" (
    echo ❌ 错误：未找到 art_resource_manager.py 文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

:: 运行打包脚本并捕获错误
python simple_build.py
set PYTHON_EXIT_CODE=%errorlevel%

echo.
if %PYTHON_EXIT_CODE% equ 0 (
    echo ✅ 打包成功完成！
) else (
    echo ❌ 打包过程中出现错误 (错误代码: %PYTHON_EXIT_CODE%)
)

echo.
echo 按任意键退出...
pause > nul 