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
        "--name=ArtResourceManager",
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