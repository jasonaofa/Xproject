@echo off
copy "dist\美术资源上传工具_v1.0.16.exe" "美术资源上传工具_v1.0.16.exe"
copy "美术资源上传工具_v1.0.16.exe" "updates\"
rmdir /s /q build
rmdir /s /q dist
echo 文件移动完成！
pause

