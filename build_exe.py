#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动打包脚本 - 将资源管理器打包成exe文件
运行此脚本将自动生成可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """检查是否安装了PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("❌ PyInstaller 未安装")
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    print("🔧 正在安装 PyInstaller...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 安装成功")
        return True
    except subprocess.CalledProcessError:
        print("❌ PyInstaller 安装失败")
        return False

def create_spec_file():
    """创建PyInstaller的spec文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['art_resource_manager.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('app_icon.ico', '.'),      # 错误状态图标文件
        ('app_icon_lv.ico', '.'),   # 正常运行状态图标文件  
        ('app_icon_bai.ico', '.'),  # 默认状态图标文件
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtWidgets', 
        'PyQt5.QtGui',
        'yaml',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='美术资源上传工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon_bai.ico',  # 指定图标文件
)
'''
    
    with open('ArtResourceManager.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✅ 创建了 ArtResourceManager.spec 文件")

def build_exe():
    """执行打包"""
    print("🚀 开始打包...")
    
    try:
        # 使用spec文件打包
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "ArtResourceManager.spec"]
        
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ 打包成功！")
            return True
        else:
            print("❌ 打包失败！")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 打包过程中出现异常: {str(e)}")
        return False

def clean_build_files():
    """清理构建文件"""
    print("🧹 清理构建文件...")
    
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = ['ArtResourceManager.spec']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  删除目录: {dir_name}")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"  删除文件: {file_name}")

def copy_exe_to_root():
    """将生成的exe文件复制到项目根目录"""
    exe_path = Path("dist/美术资源上传工具.exe")
    if exe_path.exists():
        shutil.copy2(exe_path, "美术资源上传工具.exe")
        print("✅ exe文件已复制到项目根目录")
        
        # 删除dist目录
        if os.path.exists("dist"):
            shutil.rmtree("dist")
            print("  删除了dist目录")
        
        return True
    else:
        print("❌ 未找到生成的exe文件")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 资源管理器自动打包工具")
    print("=" * 60)
    print("Python版本:", sys.version)
    print("当前目录:", os.getcwd())
    
    # 检查当前目录
    if not os.path.exists("art_resource_manager.py"):
        print("❌ 错误：未找到 art_resource_manager.py 文件")
        print("请确保在项目根目录运行此脚本")
        return False
    
    # 检查图标文件
    if not os.path.exists("app_icon.ico"):
        print("⚠️  警告：未找到 app_icon.ico 图标文件")
        print("💡 提示：")
        print("  1. 将您的图标文件重命名为 app_icon.ico 并放在项目根目录")
        print("  2. 或使用 convert_to_ico.py 脚本转换其他格式的图片")
        print("  3. 打包将继续进行，但exe文件将使用默认图标")
        print()
    
    # 检查并安装PyInstaller
    if not check_pyinstaller():
        if not install_pyinstaller():
            return False
    
    # 创建spec文件
    create_spec_file()
    
    # 执行打包
    if not build_exe():
        return False
    
    # 复制exe文件到根目录
    if not copy_exe_to_root():
        return False
    
    # 清理构建文件
    clean_build_files()
    
    print("\n" + "=" * 60)
    print("🎉 打包完成！")
    print("=" * 60)
    print("📁 生成的文件:")
    print("  美术资源上传工具.exe - 可执行文件")
    print("\n💡 使用说明:")
    print("  1. 双击 美术资源上传工具.exe 即可运行")
    print("  2. 无需安装Python环境")
    print("  3. 可以分发给其他用户使用")
    print("\n⚠️  注意事项:")
    print("  1. 首次运行可能被杀毒软件拦截，请添加信任")
    print("  2. exe文件较大是正常现象（包含了所有依赖）")
    print("  3. 如需修改代码，请重新运行此打包脚本")
    
    return True

if __name__ == "__main__":
    # 设置控制台编码为UTF-8
    import sys
    import io
    
    # 修复Windows控制台的UTF-8编码问题
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    class TeeOutput:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                try:
                    f.write(obj)
                    f.flush()
                except UnicodeEncodeError:
                    # 如果遇到编码错误，尝试用ASCII替换
                    f.write(obj.encode('ascii', 'replace').decode('ascii'))
                    f.flush()
        def flush(self):
            for f in self.files:
                f.flush()
    
    # 打开日志文件
    with open('build_log.txt', 'w', encoding='utf-8') as log_file:
        # 重定向输出到文件和控制台
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TeeOutput(sys.stdout, log_file)
        sys.stderr = TeeOutput(sys.stderr, log_file)
        
        try:
            print("开始执行打包脚本...")
            success = main()
            if success:
                print("\n✅ 打包成功完成！")
                print("日志文件已保存到: build_log.txt")
                # 尝试等待用户输入，如果在后台运行则跳过
                try:
                    input("\n按Enter键退出...")
                except (EOFError, OSError):
                    pass  # 后台运行时跳过
            else:
                print("\n❌ 打包失败！")
                print("详细信息请查看: build_log.txt")
                try:
                    input("\n按Enter键退出...")
                except (EOFError, OSError):
                    pass
        except KeyboardInterrupt:
            print("\n\n用户取消操作")
        except Exception as e:
            print(f"\n❌ 发生未预期的错误: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                input("按Enter键退出...")
            except (EOFError, OSError):
                pass
        finally:
            # 恢复原始输出
            sys.stdout = original_stdout
            sys.stderr = original_stderr 