@echo off
echo 启动美术资源管理工具...
echo.

REM 检查Python是否安装
py --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖是否安装
py -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    py -m pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误：依赖安装失败
        pause
        exit /b 1
    )
)

echo 启动程序...
py art_resource_manager.py

if errorlevel 1 (
    echo 程序运行出错
    pause
) 