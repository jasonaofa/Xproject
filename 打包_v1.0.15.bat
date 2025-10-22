@echo off
chcp 65001 > nul
echo.
echo ========================================
echo 🚀 美术资源上传工具 v1.0.15 打包脚本
echo ========================================
echo.

echo 📅 开始时间: %date% %time%
echo.

echo 🔧 检查Python环境...
python --version
if errorlevel 1 (
    echo ❌ 错误: 未找到Python环境
    echo 请确保已安装Python并添加到系统PATH
    pause
    exit /b 1
)

echo.
echo 🔧 检查PyInstaller...
pyinstaller --version
if errorlevel 1 (
    echo ❌ 错误: 未找到PyInstaller
    echo 正在安装PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo.
echo 🧹 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "美术资源上传工具_v1.0.15.exe" del "美术资源上传工具_v1.0.15.exe"

echo.
echo 🔨 开始打包 v1.0.15...
echo 使用配置文件: 美术资源上传工具_v1.0.15.spec
echo.

pyinstaller --clean 美术资源上传工具_v1.0.15.spec

if errorlevel 1 (
    echo.
    echo ❌ 打包失败！
    echo 请检查错误信息并解决问题
    pause
    exit /b 1
)

echo.
echo 📦 移动执行文件到根目录...
if exist "dist\美术资源上传工具_v1.0.15.exe" (
    move "dist\美术资源上传工具_v1.0.15.exe" "美术资源上传工具_v1.0.15.exe"
    echo ✅ 执行文件已移动到: 美术资源上传工具_v1.0.15.exe
) else (
    echo ❌ 错误: 未找到生成的执行文件
    pause
    exit /b 1
)

echo.
echo 🧹 清理构建目录...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo 📊 检查生成的文件...
if exist "美术资源上传工具_v1.0.15.exe" (
    for %%I in ("美术资源上传工具_v1.0.15.exe") do (
        echo ✅ 文件生成成功: %%~nxI
        echo 📏 文件大小: %%~zI 字节
        echo 📅 修改时间: %%~tI
    )
) else (
    echo ❌ 错误: 执行文件生成失败
    pause
    exit /b 1
)

echo.
echo 🔄 复制到updates目录...
if not exist "updates" mkdir "updates"
copy "美术资源上传工具_v1.0.15.exe" "updates\"
if errorlevel 1 (
    echo ⚠️ 警告: 复制到updates目录失败
) else (
    echo ✅ 已复制到updates目录
)

echo.
echo 📝 更新version.json...
echo 当前版本信息:
type version.json
echo.

echo.
echo ========================================
echo ✅ 打包完成！
echo ========================================
echo.
echo 📦 生成文件: 美术资源上传工具_v1.0.15.exe
echo 📅 完成时间: %date% %time%
echo.
echo 🎯 下一步操作:
echo 1. 测试生成的exe文件
echo 2. 更新CHANGELOG.md
echo 3. 提交代码到Git仓库
echo 4. 发布新版本
echo.

pause

