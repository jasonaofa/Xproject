#!/usr/bin/env python3
"""
美术资源管理工具打包脚本
使用PyInstaller将应用程序打包成独立的EXE文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """检查必要的依赖"""
    try:
        import PyQt5
        print("✓ PyQt5 已安装")
    except ImportError:
        print("✗ PyQt5 未安装，请运行: pip install PyQt5")
        return False
    
    try:
        import yaml
        print("✓ PyYAML 已安装")
    except ImportError:
        print("✗ PyYAML 未安装，请运行: pip install PyYAML")
        return False
    
    try:
        import PIL
        print("✓ Pillow 已安装")
    except ImportError:
        print("⚠ Pillow 未安装，图片尺寸检查将使用内置方法")
    
    return True

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
        return True
    except ImportError:
        print("正在安装 PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller 安装成功")
            return True
        except subprocess.CalledProcessError:
            print("✗ PyInstaller 安装失败")
            return False

def build_executable():
    """构建可执行文件"""
    print("开始构建可执行文件...")
    
    # 清理之前的构建
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("清理 build 目录")
    
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("清理 dist 目录")
    
    # PyInstaller 命令
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包成单个文件
        "--windowed",                   # Windows下不显示控制台
        "--name=美术资源管理工具",        # 可执行文件名称
        "--icon=icon.ico",              # 图标文件（如果存在）
        "--add-data=config.json;.",     # 包含配置文件
        "--hidden-import=PyQt5.sip",    # 隐式导入
        "--hidden-import=PIL._tkinter_finder",  # PIL相关
        "art_resource_manager.py"       # 主文件
    ]
    
    # 检查图标文件是否存在
    if not os.path.exists("icon.ico"):
        cmd.remove("--icon=icon.ico")
        print("⚠ 未找到 icon.ico 文件，跳过图标设置")
    
    # 检查配置文件是否存在
    if not os.path.exists("config.json"):
        cmd.remove("--add-data=config.json;.")
        print("⚠ 未找到 config.json 文件，跳过配置文件包含")
    
    try:
        print("执行命令:", " ".join(cmd))
        subprocess.check_call(cmd)
        print("✓ 构建成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 构建失败: {e}")
        return False

def create_distribution_package():
    """创建分发包"""
    if not os.path.exists("dist/美术资源管理工具.exe"):
        print("✗ 可执行文件不存在")
        return False
    
    # 创建分发目录
    dist_dir = Path("distribution")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # 复制可执行文件
    shutil.copy2("dist/美术资源管理工具.exe", dist_dir / "美术资源管理工具.exe")
    
    # 创建说明文件
    readme_content = """
美术资源管理工具 v1.0
====================

使用说明：
1. 双击 "美术资源管理工具.exe" 启动程序
2. 首次使用请设置SVN和Git仓库路径
3. 支持拖拽文件到程序中进行检查
4. 检查结果会显示在"检查结果"标签页中

系统要求：
- Windows 7 及以上版本
- 无需安装Python或其他依赖

功能特性：
- Meta文件缺失检查
- 中文字符检查
- 图片尺寸检查（支持PNG、JPEG格式）
- GUID一致性检查
- GUID引用检查
- Git分支管理
- 详细的错误报告和解决建议

技术支持：
如遇到问题请联系开发团队

版本历史：
v1.0 - 初始版本
- 基础资源检查功能
- 图片尺寸检查（内置方法，无需PIL依赖）
- 详细错误报告
"""
    
    with open(dist_dir / "使用说明.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # 创建批处理文件（可选）
    batch_content = """@echo off
chcp 65001 > nul
echo 启动美术资源管理工具...
start "" "美术资源管理工具.exe"
"""
    
    with open(dist_dir / "启动工具.bat", "w", encoding="gbk") as f:
        f.write(batch_content)
    
    print(f"✓ 分发包已创建在: {dist_dir.absolute()}")
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("美术资源管理工具 - 打包脚本")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("请先安装必要的依赖包")
        return False
    
    # 安装PyInstaller
    if not install_pyinstaller():
        print("无法安装PyInstaller")
        return False
    
    # 构建可执行文件
    if not build_executable():
        print("构建失败")
        return False
    
    # 创建分发包
    if not create_distribution_package():
        print("创建分发包失败")
        return False
    
    print("\n" + "=" * 50)
    print("构建完成！")
    print("可执行文件位置: dist/美术资源管理工具.exe")
    print("分发包位置: distribution/")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        input("按任意键退出...")
        sys.exit(1)
    else:
        input("构建成功！按任意键退出...") 