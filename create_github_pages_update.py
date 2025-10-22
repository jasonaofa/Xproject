#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建GitHub Pages热更新配置
生成用于GitHub Pages的更新配置文件
"""

import json
import hashlib
import os
from datetime import datetime

def get_file_hash(file_path):
    """计算文件SHA256哈希"""
    if not os.path.exists(file_path):
        return ""
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_update_config():
    """创建更新配置文件"""
    exe_file = "美术资源上传工具.exe"
    
    config = {
        "latest_version": "1.0.2",
        "release_date": datetime.now().isoformat(),
        "release_notes": """🎉 版本 1.0.2 更新内容:

✨ 新增功能:
• 🆕 添加菜单栏测试选项"1"
• 🔄 完善热更新功能
• 🛡️ 增强版本比较逻辑

🐛 修复问题:
• 修复版本号格式兼容性问题
• 优化更新检查流程
• 改进用户体验

📈 性能优化:
• 提升启动速度
• 优化内存使用
• 增强稳定性

建议立即更新以获得最佳体验！""",
        "download_url": "https://github.com/jasonaofa/Xproject/releases/download/v1.0.2/美术资源上传工具.exe",
        "file_hash": get_file_hash(exe_file) if os.path.exists(exe_file) else "",
        "file_size": os.path.getsize(exe_file) if os.path.exists(exe_file) else 0,
        "mandatory": False,
        "min_supported_version": "0.0.1"
    }
    
    # 保存配置文件
    with open('update_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("✅ 已生成 update_config.json")
    print(f"📁 文件信息:")
    print(f"  版本: {config['latest_version']}")
    print(f"  哈希: {config['file_hash'][:16]}...")
    print(f"  大小: {config['file_size']:,} 字节")
    
    # 生成GitHub Pages的index.html
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>美术资源工具 - 热更新服务</title>
</head>
<body>
    <h1>美术资源上传工具 - 热更新服务</h1>
    <p>当前最新版本: {config['latest_version']}</p>
    <p>发布时间: {config['release_date']}</p>
    <p><a href="{config['download_url']}">下载最新版本</a></p>
    
    <h2>API接口</h2>
    <ul>
        <li><a href="./update_config.json">获取更新配置</a></li>
    </ul>
    
    <h2>更新说明</h2>
    <pre>{config['release_notes']}</pre>
</body>
</html>"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ 已生成 index.html")
    print()
    print("📋 下一步操作:")
    print("1. 将 update_config.json 和 index.html 上传到GitHub仓库")
    print("2. 在GitHub仓库设置中启用GitHub Pages")
    print("3. 页面地址将是: https://jasonaofa.github.io/Xproject/")
    print("4. 更新配置地址: https://jasonaofa.github.io/Xproject/update_config.json")

if __name__ == '__main__':
    create_update_config()





