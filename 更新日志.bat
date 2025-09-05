@echo off
chcp 65001 >nul
echo.
echo 🚀 美术资源管理工具 - 版本日志更新器
echo ========================================
echo.
echo 请选择操作方式：
echo   [1] 交互式更新版本日志
echo   [2] 查看当前更新日志
echo   [3] 显示使用帮助
echo   [4] 退出
echo.
set /p choice=请选择 (1-4): 

if "%choice%"=="1" goto interactive
if "%choice%"=="2" goto view
if "%choice%"=="3" goto help
if "%choice%"=="4" goto exit

:interactive
echo.
echo 启动交互式更新...
python update_changelog.py
goto end

:view
echo.
echo 当前更新日志内容：
echo ==================
type CHANGELOG.md
goto end

:help
echo.
echo 使用说明：
echo ========
echo 1. 交互式更新：根据提示输入新版本的更新内容
echo 2. 查看日志：显示当前的完整更新日志
echo 3. 工具会自动管理版本号（递增patch版本）
echo 4. 支持添加新功能、优化改进、问题修复等分类
echo.
echo 版本号格式：v主版本.次版本.修订版本
echo 日期格式：YYYY年MM月DD日
echo.
goto end

:exit
echo 再见！
goto end

:end
pause 