#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的热更新服务器示例
用于演示如何搭建热更新服务
"""

import os
import json
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from packaging import version

app = Flask(__name__)

# 配置
UPDATE_FILES_DIR = "update_files"
CURRENT_VERSION = "1.0.0"
LATEST_VERSION = "1.1.0"

# 确保更新文件目录存在
os.makedirs(UPDATE_FILES_DIR, exist_ok=True)

def calculate_file_hash(file_path):
    """计算文件SHA256哈希"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return ""

def get_file_size(file_path):
    """获取文件大小"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

@app.route('/api/check_update', methods=['GET'])
def check_update():
    """检查更新API"""
    try:
        current_version_str = request.args.get('current_version', '1.0.0')
        
        print(f"📋 检查更新请求: 当前版本 {current_version_str}")
        
        # 比较版本
        has_update = version.parse(LATEST_VERSION) > version.parse(current_version_str)
        
        if not has_update:
            return jsonify({
                'has_update': False,
                'message': '当前已是最新版本'
            })
        
        # 构建更新文件列表
        update_files = []
        version_dir = os.path.join(UPDATE_FILES_DIR, f"v{LATEST_VERSION}")
        
        if os.path.exists(version_dir):
            for filename in os.listdir(version_dir):
                if filename.endswith('.py'):
                    file_path = os.path.join(version_dir, filename)
                    file_hash = calculate_file_hash(file_path)
                    file_size = get_file_size(file_path)
                    
                    update_files.append({
                        'path': filename,
                        'url': f'{request.host_url}api/download/{LATEST_VERSION}/{filename}',
                        'hash': file_hash,
                        'size': file_size
                    })
        
        response_data = {
            'has_update': True,
            'latest_version': LATEST_VERSION,
            'current_version': current_version_str,
            'description': f"""🎉 新版本 {LATEST_VERSION} 可用！

📋 更新内容:
• 🚨 修复了替换模式的重命名问题
• 🔄 优化了热更新下载性能  
• 💾 新增了自动备份功能
• 🛡️ 增强了文件校验机制
• 🎨 改进了用户界面体验

📊 更新统计:
• 更新文件: {len(update_files)} 个
• 发布时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
• 兼容性: 向后兼容

建议立即更新以获得最佳体验！""",
            'files': update_files,
            'mandatory': False,
            'release_date': datetime.now().isoformat(),
            'min_supported_version': '0.9.0'
        }
        
        print(f"✅ 返回更新信息: {len(update_files)} 个文件")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ 检查更新错误: {e}")
        return jsonify({
            'error': '检查更新失败',
            'message': str(e)
        }), 500

@app.route('/api/download/<version>/<filename>', methods=['GET'])
def download_file(version, filename):
    """下载更新文件"""
    try:
        file_path = os.path.join(UPDATE_FILES_DIR, f"v{version}", filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        print(f"📥 下载文件: {filename} (版本: {version})")
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"❌ 下载文件错误: {e}")
        return jsonify({'error': '下载失败', 'message': str(e)}), 500

@app.route('/api/version_info', methods=['GET'])
def version_info():
    """获取版本信息"""
    return jsonify({
        'current_version': CURRENT_VERSION,
        'latest_version': LATEST_VERSION,
        'server_time': datetime.now().isoformat(),
        'available_versions': get_available_versions()
    })

def get_available_versions():
    """获取可用版本列表"""
    versions = []
    if os.path.exists(UPDATE_FILES_DIR):
        for item in os.listdir(UPDATE_FILES_DIR):
            if item.startswith('v') and os.path.isdir(os.path.join(UPDATE_FILES_DIR, item)):
                versions.append(item[1:])  # 去掉v前缀
    return sorted(versions, key=lambda x: version.parse(x), reverse=True)

@app.route('/admin/upload_version', methods=['POST'])
def upload_version():
    """管理员上传新版本（简单示例）"""
    try:
        # 这里可以添加认证机制
        new_version = request.form.get('version')
        if not new_version:
            return jsonify({'error': '版本号不能为空'}), 400
        
        # 创建版本目录
        version_dir = os.path.join(UPDATE_FILES_DIR, f"v{new_version}")
        os.makedirs(version_dir, exist_ok=True)
        
        # 处理上传的文件
        uploaded_files = []
        for key in request.files:
            file = request.files[key]
            if file.filename:
                file_path = os.path.join(version_dir, file.filename)
                file.save(file_path)
                uploaded_files.append(file.filename)
        
        return jsonify({
            'success': True,
            'version': new_version,
            'uploaded_files': uploaded_files,
            'message': f'版本 {new_version} 上传成功'
        })
        
    except Exception as e:
        return jsonify({'error': '上传失败', 'message': str(e)}), 500

if __name__ == '__main__':
    print("🚀 启动热更新服务器...")
    print(f"📋 当前版本: {CURRENT_VERSION}")
    print(f"🆕 最新版本: {LATEST_VERSION}")
    print(f"📁 更新文件目录: {UPDATE_FILES_DIR}")
    print()
    print("📡 API接口:")
    print("  GET  /api/check_update?current_version=1.0.0")
    print("  GET  /api/download/<version>/<filename>")
    print("  GET  /api/version_info")
    print("  POST /admin/upload_version")
    print()
    print("💡 使用说明:")
    print("1. 将更新文件放在 update_files/v1.1.0/ 目录下")
    print("2. 客户端工具会自动检查和下载更新")
    print("3. 访问 http://localhost:5000/api/version_info 查看状态")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)





