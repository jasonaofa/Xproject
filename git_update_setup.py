#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Git的热更新设置工具
自动生成基于Git仓库的热更新配置
"""

import os
import json
from datetime import datetime

def create_git_based_update_config():
    """创建基于Git的热更新配置"""
    
    print("🚀 基于Git的热更新配置生成器")
    print("=" * 50)
    
    # 获取用户输入
    git_base_url = input("请输入您的Git服务器地址 (例: http://client_gitlab.miniworldplus.com:83): ").strip()
    if not git_base_url:
        git_base_url = "http://client_gitlab.miniworldplus.com:83"
    
    project_group = input("请输入项目组名 (例: miniwan): ").strip()
    if not project_group:
        project_group = "miniwan"
    
    project_name = input("请输入项目名 (例: art-tool-updates): ").strip()
    if not project_name:
        project_name = "art-tool-updates"
    
    # 生成配置
    config = {
        "update_server_config": {
            "git_base_url": git_base_url,
            "project_group": project_group,
            "project_name": project_name,
            "branch": "main",
            "raw_file_base": f"{git_base_url}/{project_group}/{project_name}/raw/main"
        },
        "api_endpoints": {
            "check_update": f"{git_base_url}/{project_group}/{project_name}/raw/main/api/check_update.json",
            "version_info": f"{git_base_url}/{project_group}/{project_name}/raw/main/api/version_info.json",
            "download_base": f"{git_base_url}/{project_group}/{project_name}/raw/main/files"
        },
        "setup_instructions": [
            f"1. 在 {git_base_url} 创建新项目: {project_group}/{project_name}",
            "2. 克隆项目到本地",
            "3. 创建以下目录结构:",
            "   api/",
            "   ├── check_update.json",
            "   └── version_info.json",
            "   files/",
            "   └── v1.1.0/",
            "       └── art_resource_manager.py",
            "4. 推送到Git仓库",
            "5. 更新工具配置使用新的服务器地址"
        ]
    }
    
    # 保存配置
    with open("git_update_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("\n✅ 配置文件已生成: git_update_config.json")
    
    # 生成API文件
    create_api_files(config)
    
    # 生成工具配置更新代码
    generate_tool_config_update(config)
    
    print("\n🎉 Git基于热更新配置完成!")
    print(f"📡 更新服务器地址: {config['api_endpoints']['check_update']}")

def create_api_files(config):
    """创建API响应文件"""
    
    # 创建目录
    os.makedirs("git_update_files/api", exist_ok=True)
    os.makedirs("git_update_files/files/v1.1.0", exist_ok=True)
    
    # 创建版本检查API响应
    check_update_response = {
        "has_update": True,
        "latest_version": "1.1.0",
        "current_version": "1.0.0",
        "description": """🎉 发现新版本 1.1.0！

📋 更新内容:
• 🔥 新增热更新功能
• 🚨 修复远程资源引用检查
• 🌐 支持Avatar/MiniUniverse子目录
• 🎨 新增材质模板验证
• 🔄 优化替换模式文件重命名

✨ 新特性:
• 一键检查更新
• 自动下载和应用更新
• 智能备份和回滚
• 用户友好的进度显示

建议立即更新以获得最佳体验！""",
        "files": [
            {
                "path": "art_resource_manager.py",
                "url": f"{config['api_endpoints']['download_base']}/v1.1.0/art_resource_manager.py",
                "hash": "",
                "size": 0
            }
        ],
        "mandatory": False,
        "release_date": datetime.now().isoformat(),
        "min_supported_version": "1.0.0"
    }
    
    with open("git_update_files/api/check_update.json", "w", encoding="utf-8") as f:
        json.dump(check_update_response, f, indent=2, ensure_ascii=False)
    
    # 创建版本信息API响应
    version_info = {
        "current_version": "1.0.0",
        "latest_version": "1.1.0",
        "server_time": datetime.now().isoformat(),
        "available_versions": ["1.0.0", "1.1.0"],
        "server_status": "active"
    }
    
    with open("git_update_files/api/version_info.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)
    
    # 复制当前的工具文件作为更新文件
    if os.path.exists("art_resource_manager.py"):
        import shutil
        shutil.copy2("art_resource_manager.py", "git_update_files/files/v1.1.0/art_resource_manager.py")
    
    print("✅ API文件已生成到: git_update_files/")

def generate_tool_config_update(config):
    """生成工具配置更新代码"""
    
    update_code = f'''
# 将以下代码添加到 art_resource_manager.py 中的热更新配置部分

# 🌐 基于Git的热更新配置
GIT_UPDATE_CONFIG = {{
    "check_update_url": "{config['api_endpoints']['check_update']}",
    "version_info_url": "{config['api_endpoints']['version_info']}",
    "download_base_url": "{config['api_endpoints']['download_base']}"
}}

# 修改热更新管理器初始化
self.hot_updater = HotUpdateManager(
    current_version="1.0.0",
    update_server_url="{config['api_endpoints']['check_update'].replace('/check_update.json', '')}"
)
'''
    
    with open("git_update_tool_config.py", "w", encoding="utf-8") as f:
        f.write(update_code)
    
    print("✅ 工具配置代码已生成: git_update_tool_config.py")

if __name__ == "__main__":
    create_git_based_update_config()





