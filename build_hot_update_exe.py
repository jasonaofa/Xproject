#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新版本的exe打包脚本
包含热更新功能的完整exe打包
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime

def build_hot_update_exe():
    """构建包含热更新功能的exe"""
    
    print("🚀 开始构建热更新版本的exe...")
    print("=" * 60)
    
    # 1. 清理之前的构建
    print("🧹 清理构建目录...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # 2. 准备打包配置
    print("📋 准备打包配置...")
    
    # PyInstaller 配置
    pyinstaller_args = [
        'pyinstaller',
        '--onefile',                    # 单文件模式
        '--windowed',                   # 无控制台窗口
        '--name=美术资源上传工具',        # exe名称
        '--icon=app_icon_bai.ico',      # 图标
        '--add-data=app_icon_bai.ico;.',  # 包含图标文件
        '--add-data=app_icon_lv.ico;.',   # 包含备用图标
        '--add-data=hot_update_manager.py;.',  # 包含热更新管理器
        '--hidden-import=requests',     # 热更新需要的依赖
        '--hidden-import=packaging',    # 版本比较需要
        'art_resource_manager.py'       # 主文件
    ]
    
    # 3. 执行打包
    print("📦 执行PyInstaller打包...")
    try:
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        print("✅ 打包成功!")
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    
    # 4. 准备分发包
    print("📁 准备分发包...")
    
    # 创建分发目录
    version = "1.0.0"  # 可以从配置文件读取
    dist_name = f"美术资源上传工具_热更新版_v{version}"
    dist_dir = f"dist/{dist_name}"
    
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # 复制exe文件
    exe_src = "dist/美术资源上传工具.exe"
    exe_dst = os.path.join(dist_dir, "美术资源上传工具.exe")
    if os.path.exists(exe_src):
        shutil.copy2(exe_src, exe_dst)
        print(f"✅ 复制exe: {exe_dst}")
    else:
        print(f"❌ 找不到exe文件: {exe_src}")
        return False
    
    # 复制必要的文件
    files_to_copy = [
        ("hot_update_manager.py", "热更新管理器源码（备用）"),
        ("update_server_config.json", "更新服务器配置"),
        ("app_icon_bai.ico", "白色图标"),
        ("app_icon_lv.ico", "绿色图标"),
        ("热更新功能说明.md", "使用说明"),
        ("热更新部署方案.md", "部署方案"),
        ("config.json", "默认配置文件")
    ]
    
    for filename, description in files_to_copy:
        if os.path.exists(filename):
            dst_path = os.path.join(dist_dir, filename)
            shutil.copy2(filename, dst_path)
            print(f"✅ 复制文件: {filename} - {description}")
        else:
            print(f"⚠️ 文件不存在: {filename}")
    
    # 5. 创建安装说明
    print("📝 创建安装说明...")
    readme_content = f"""# 美术资源上传工具 - 热更新版

## 📋 版本信息
- **版本号**: {version}
- **构建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **特性**: 包含热更新功能

## 🚀 安装说明

### 1. 解压文件
将此文件夹解压到您希望安装的目录。

### 2. 运行程序
双击 `美术资源上传工具.exe` 启动程序。

### 3. 首次配置
- 设置SVN路径和Git路径
- 配置更新服务器地址（如需要）

## 🔄 热更新功能

### 自动检查更新
程序启动时会自动检查是否有可用更新。

### 手动检查更新
点击菜单栏 **"帮助" → "检查更新"** 手动检查。

### 更新过程
1. 发现新版本时会弹出更新对话框
2. 点击"立即更新"开始下载
3. 系统自动备份和应用更新
4. 重启程序完成更新

## 📁 文件说明

- `美术资源上传工具.exe` - 主程序（包含热更新功能）
- `hot_update_manager.py` - 热更新管理器源码（备用）
- `update_server_config.json` - 更新服务器配置
- `热更新功能说明.md` - 详细使用说明
- `app_icon_*.ico` - 程序图标文件

## ⚠️ 注意事项

1. **首次安装**: 这是包含热更新功能的完整版本
2. **后续更新**: 无需重新下载exe，通过热更新自动完成
3. **网络要求**: 热更新需要网络连接
4. **权限要求**: 可能需要管理员权限进行文件更新

## 🆘 故障排除

如遇到问题，请参考 `热更新功能说明.md` 中的故障处理章节。

---
**构建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**版本**: 热更新版 v{version}
"""
    
    readme_path = os.path.join(dist_dir, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✅ 创建安装说明: README.md")
    
    # 6. 创建压缩包
    print("📦 创建分发压缩包...")
    try:
        import zipfile
        zip_path = f"dist/{dist_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, "dist")
                    zipf.write(file_path, arc_path)
        
        # 获取压缩包大小
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
        print(f"✅ 创建压缩包: {zip_path} ({zip_size:.1f} MB)")
        
    except Exception as e:
        print(f"⚠️ 创建压缩包失败: {e}")
    
    # 7. 输出构建结果
    print("\n" + "=" * 60)
    print("🎉 构建完成!")
    print(f"📁 分发目录: {dist_dir}")
    if 'zip_path' in locals():
        print(f"📦 压缩包: {zip_path}")
    
    print("\n📋 分发说明:")
    print("1. 这是包含热更新功能的完整版本")
    print("2. 用户只需下载此版本一次")
    print("3. 后续更新通过热更新功能自动完成")
    print("4. 无需再重新打包和分发exe文件")
    
    print("\n🔄 后续更新流程:")
    print("1. 修改 art_resource_manager.py 源码")
    print("2. 将更新文件上传到更新服务器")
    print("3. 用户工具自动检测并更新")
    
    return True

def check_dependencies():
    """检查构建依赖"""
    print("🔍 检查构建依赖...")
    
    required_files = [
        "art_resource_manager.py",
        "hot_update_manager.py",
        "app_icon_bai.ico"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {missing_files}")
        return False
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("❌ 未安装PyInstaller，请运行: pip install pyinstaller")
        return False
    
    # 检查其他依赖
    try:
        import requests
        import packaging
        print("✅ 热更新依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install requests packaging")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 美术资源上传工具 - 热更新版本构建器")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装必要的依赖")
        input("按Enter键退出...")
        sys.exit(1)
    
    # 开始构建
    success = build_hot_update_exe()
    
    if success:
        print("\n🎉 构建成功完成!")
        print("\n💡 提示:")
        print("- 这是最后一次需要打包exe的版本")
        print("- 后续所有更新都通过热更新功能完成")
        print("- 大大简化了版本管理和用户体验")
    else:
        print("\n❌ 构建失败!")
    
    input("\n按Enter键退出...")
