import os
import sys
import subprocess

def main():
    print("开始打包...")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print("PyInstaller已安装")
    except ImportError:
        print("安装PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 执行打包
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed", 
        "--name=美术资源上传工具",
        "--icon=app_icon_bai.ico",  # 使用白色图标作为exe文件图标
        "--add-data=config.json;.",
        "--add-data=app_icon.ico;.",     # 红色图标
        "--add-data=app_icon_lv.ico;.",  # 绿色图标  
        "--add-data=app_icon_bai.ico;.", # 白色图标
        "art_resource_manager.py"
    ]
    
    print("执行命令:", " ".join(cmd))
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("打包成功!")
    else:
        print("打包失败!")

if __name__ == "__main__":
    main()
    input("按Enter退出...") 