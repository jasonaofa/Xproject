@echo off
chcp 65001 >nul
title Building v1.0.25
echo ========================================
echo Building Art Resource Manager v1.0.25
echo ========================================
echo.

python -m PyInstaller --onefile --windowed --icon=app_icon_bai.ico --name="美术资源上传工具_v1.0.25" --add-data="update_server_config.json;." --add-data="version.json;." art_resource_manager.py

if exist "dist\美术资源上传工具_v1.0.25.exe" (
    echo.
    echo [SUCCESS] Build completed!
    echo [INFO] Location: dist\美术资源上传工具_v1.0.25.exe
    echo.
    echo [INFO] Copying to updates folder...
    if not exist "updates" mkdir updates
    copy "dist\美术资源上传工具_v1.0.25.exe" "updates\美术资源上传工具_v1.0.25.exe" >nul
    if exist "updates\美术资源上传工具_v1.0.25.exe" (
        echo [SUCCESS] Copied to updates folder!
    ) else (
        echo [ERROR] Failed to copy to updates folder
    )
    echo.
    echo v1.0.23 is ready for hot update!
) else (
    echo [ERROR] Build failed! Please check error messages above.
)

echo.
echo Press any key to exit...
pause >nul

