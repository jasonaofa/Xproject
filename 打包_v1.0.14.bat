@echo off
chcp 65001 > nul
echo.
echo ========================================
echo   美术资源上传工具 v1.0.14 打包脚本
echo ========================================
echo.

echo 🔍 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python未安装或未添加到PATH
    pause
    exit /b 1
)

echo.
echo 🔍 检查PyInstaller...
python -m PyInstaller --version
if %errorlevel% neq 0 (
    echo ❌ PyInstaller未安装
    echo 正在安装PyInstaller...
    pip install pyinstaller
)

echo.
echo 🧹 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "美术资源上传工具_v1.0.14.exe" del "美术资源上传工具_v1.0.14.exe"

echo.
echo 🔨 开始打包 v1.0.14...
python -m PyInstaller --clean art_resource_manager_v1.0.14.spec

echo.
if exist "dist\美术资源上传工具_v1.0.14.exe" (
    echo ✅ 打包成功！
    echo.
    echo 📁 输出文件信息：
    dir "dist\美术资源上传工具_v1.0.14.exe" | find "美术资源上传工具"
    
    echo.
    echo 📋 复制文件到根目录...
    copy "dist\美术资源上传工具_v1.0.14.exe" "美术资源上传工具_v1.0.14.exe"
    
    echo.
    echo 📋 更新updates目录...
    copy "美术资源上传工具_v1.0.14.exe" "updates\美术资源上传工具_v1.0.14.exe"
    
    echo.
    echo 🎉 v1.0.14 打包完成！
    echo.
    echo 📦 文件位置：
    echo    - 根目录: 美术资源上传工具_v1.0.14.exe
    echo    - updates目录: updates\美术资源上传工具_v1.0.14.exe
    echo    - dist目录: dist\美术资源上传工具_v1.0.14.exe
    echo.
    echo 🆕 新功能包含：
    echo    ✅ 预制体文件名规范检查
    echo    ✅ 文件扩展名大小写检查  
    echo    ✅ overrideController缓存检查
    echo    ✅ Git认证和同步问题修复
    echo    ✅ CRLF换行符问题自动处理
    echo    ✅ 独立引擎环境适配
    echo.
) else (
    echo ❌ 打包失败！
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo 按任意键继续...
pause > nul

