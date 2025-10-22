@echo off
title 快速打包美术资源上传工具 v1.0.21
echo 🚀 开始打包美术资源上传工具 v1.0.21...
echo.
echo 📦 正在打包，请稍候...

python -m PyInstaller --onefile --windowed --icon=app_icon.ico --name="美术资源上传工具_v1.0.21" --add-data="update_server_config.json;." --add-data="version.json;." art_resource_manager.py

if exist "dist\美术资源上传工具_v1.0.21.exe" (
    echo.
    echo ✅ 打包完成！
    echo 📁 文件位置: dist\美术资源上传工具_v1.0.21.exe
    echo.
    echo 🔄 正在复制到updates文件夹...
    copy "dist\美术资源上传工具_v1.0.21.exe" "updates\美术资源上传工具_v1.0.21.exe"
    if exist "updates\美术资源上传工具_v1.0.21.exe" (
        echo ✅ 已复制到updates文件夹，热更新服务器可以使用新版本！
    ) else (
        echo ❌ 复制到updates文件夹失败
    )
    echo.
    echo 🎯 现在用户可以通过热更新获取v1.0.21版本（包含PBR模板修复）
) else (
    echo ❌ 打包失败！请检查错误信息
)

echo.
echo 按任意键退出...
pause >nul



