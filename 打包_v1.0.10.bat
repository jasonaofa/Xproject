@echo off
chcp 65001 > nul
echo 正在打包美术资源上传工具 v1.0.10...
echo.

echo 1. 检查PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 安装PyInstaller...
    pip install PyInstaller
)

echo.
echo 2. 开始打包...
pyinstaller --clean 美术资源上传工具_v1.0.10.spec

echo.
echo 3. 检查打包结果...
if exist "dist\美术资源上传工具_v1.0.10.exe" (
    echo ✅ 打包成功！
    echo 文件位置: dist\美术资源上传工具_v1.0.10.exe
    
    echo.
    echo 4. 复制到根目录...
    copy "dist\美术资源上传工具_v1.0.10.exe" "美术资源上传工具_v1.0.10.exe"
    echo ✅ 已复制到根目录
    
    echo.
    echo 🎉 打包完成！
    echo 可执行文件: 美术资源上传工具_v1.0.10.exe
    echo.
    echo 📋 版本v1.0.10新功能:
    echo - 🎯 预制体文件名规范检查
    echo - 🔧 Git认证和同步问题一键修复
    echo - 🛠️ 智能推送失败分析和解决方案
    echo.
) else (
    echo ❌ 打包失败，请检查错误信息
)

pause