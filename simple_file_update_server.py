#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超简单的文件热更新服务器
只需要把新版本exe放到指定文件夹即可
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import os
import hashlib
from datetime import datetime
import socket

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个不存在的地址，只是为了获取本机IP
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 如果失败，返回localhost
        return '127.0.0.1'

class SimpleUpdateHandler(BaseHTTPRequestHandler):
    
    # 配置：新版本文件存放目录
    UPDATE_DIR = "updates"  # 在当前目录创建updates文件夹
    
    # 服务器IP地址（动态获取）
    SERVER_IP = None
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if path == '/api/check_update':
            self.handle_check_update(query_params)
        elif path.startswith('/api/download/'):
            self.handle_download(path)
        elif path == '/api/version_info':
            self.handle_version_info()
        else:
            self.send_error(404, "Not Found")
    
    def handle_check_update(self, query_params):
        """检查更新请求"""
        try:
            current_version = query_params.get('current_version', ['0.0.0'])[0]
            print(f"🔍 检查更新请求 - 当前版本: {current_version}")
            
            # 检查updates文件夹中的exe文件
            latest_exe = self.find_latest_exe()
            
            if not latest_exe:
                response_data = {
                    'has_update': False,
                    'message': 'updates文件夹中没有找到新版本exe文件'
                }
                print("ℹ️ 未找到更新文件")
                self.send_json_response(200, response_data)
                return
            
            # 从文件名中提取版本号（假设文件名包含版本号）
            latest_version = self.extract_version_from_filename(latest_exe)
            
            if self.compare_versions(latest_version, current_version):
                file_path = os.path.join(self.UPDATE_DIR, latest_exe)
                file_size = os.path.getsize(file_path)
                file_hash = self.get_file_hash(file_path)
                
                response_data = {
                    'has_update': True,
                    'latest_version': latest_version,
                    'current_version': current_version,
                    'release_notes': f"""🎉 发现新版本 {latest_version}!

🔄 **远程资源引用检查功能升级**:
• 完善本地prefab引用远程skeleton/mesh文件的检测
• 增强远程资源引用检查的错误分类和阻塞机制
• 新增详细的调试日志，帮助快速定位问题
• 完善GUID提取和路径判断逻辑

🔍 **增强调试功能**:
• 详细的文件扫描和GUID提取日志
• 完整的远程引用检查过程显示
• 明确的违规引用错误提示
• 精确的违规引用检测机制

✨ **用户体验提升**:
• 更准确的远程资源引用检测
• 更详细的问题定位信息
• 更完善的检查过程可视化

建议立即更新，享受更安全的美术资源管理体验！""",
                    'download_url': f'http://{self.SERVER_IP}:8002/api/download/{latest_version}/{latest_exe}',
                    'file_size': file_size,
                    'file_hash': file_hash,
                    'release_date': datetime.now().isoformat(),
                    'mandatory': False,
                    # 🔧 添加files字段以兼容HotUpdateManager
                    'files': [
                        {
                            'path': latest_exe,  # 使用实际文件名
                            'url': f'http://{self.SERVER_IP}:8002/api/download/{latest_version}/{latest_exe}',
                            'hash': file_hash,
                            'size': file_size
                        }
                    ]
                }
                print(f"✅ 发现更新: {latest_version}")
            else:
                response_data = {
                    'has_update': False,
                    'message': '已是最新版本'
                }
                print(f"ℹ️ 已是最新版本")
            
            self.send_json_response(200, response_data)
            
        except Exception as e:
            print(f"❌ 检查更新失败: {e}")
            error_response = {
                'has_update': False,
                'error': f'检查更新失败: {str(e)}'
            }
            self.send_json_response(500, error_response)
    
    def handle_download(self, path):
        """处理文件下载"""
        try:
            # 提取文件名并解码URL编码
            import urllib.parse
            parts = path.split('/')
            if len(parts) >= 4:
                filename = urllib.parse.unquote(parts[-1])  # 解码URL编码的文件名
                file_path = os.path.join(self.UPDATE_DIR, filename)
                
                if os.path.exists(file_path):
                    # 发送文件
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    # 处理中文文件名
                    safe_filename = filename.encode('utf-8').decode('latin-1', errors='ignore')
                    self.send_header('Content-Disposition', f'attachment; filename*=UTF-8\'\'{urllib.parse.quote(filename)}')
                    self.send_header('Content-Length', str(os.path.getsize(file_path)))
                    self.end_headers()
                    
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                    
                    print(f"📥 文件下载成功: {filename}")
                    return
            
            self.send_error(404, "File not found")
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            self.send_error(500, f"Download failed: {str(e)}")
    
    def handle_version_info(self):
        """获取版本信息"""
        try:
            latest_exe = self.find_latest_exe()
            if latest_exe:
                latest_version = self.extract_version_from_filename(latest_exe)
                file_path = os.path.join(self.UPDATE_DIR, latest_exe)
                response_data = {
                    'latest_version': latest_version,
                    'filename': latest_exe,
                    'file_size': os.path.getsize(file_path),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }
            else:
                response_data = {
                    'latest_version': '0.0.0',
                    'message': '暂无更新文件'
                }
            
            self.send_json_response(200, response_data)
            
        except Exception as e:
            print(f"❌ 获取版本信息失败: {e}")
            self.send_json_response(500, {'error': str(e)})
    
    def find_latest_exe(self):
        """查找最新的exe文件"""
        if not os.path.exists(self.UPDATE_DIR):
            os.makedirs(self.UPDATE_DIR)
            return None
        
        exe_files = [f for f in os.listdir(self.UPDATE_DIR) if f.endswith('.exe')]
        if not exe_files:
            return None
        
        # 按修改时间排序，最新的在前
        exe_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.UPDATE_DIR, x)), reverse=True)
        return exe_files[0]
    
    def extract_version_from_filename(self, filename):
        """从文件名提取版本号"""
        # 尝试从文件名中提取版本号
        # 支持格式: 美术资源上传工具_v1.0.3.exe, 工具_1.0.3.exe 等
        import re
        
        # 匹配版本号模式
        patterns = [
            r'v?(\d+\.\d+\.\d+)',  # v1.0.3 或 1.0.3
            r'(\d+)\.(\d+)\.(\d+)', # 1.0.3
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                if len(match.groups()) == 1:
                    return match.group(1)
                else:
                    return '.'.join(match.groups())
        
        # 如果没找到版本号，使用文件修改时间作为版本
        file_path = os.path.join(self.UPDATE_DIR, filename)
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime("1.0.%Y%m%d")
    
    def compare_versions(self, version1, version2):
        """比较版本号"""
        def version_tuple(v):
            return tuple(map(int, v.replace('v', '').split('.')))
        
        try:
            return version_tuple(version1) > version_tuple(version2)
        except:
            return True  # 如果比较失败，假设有更新
    
    def get_file_hash(self, file_path):
        """计算文件哈希"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(json_data.encode('utf-8'))

def main():
    # 获取本机IP地址
    local_ip = get_local_ip()
    SimpleUpdateHandler.SERVER_IP = local_ip
    
    # 确保updates文件夹存在
    if not os.path.exists("updates"):
        os.makedirs("updates")
        print("📁 已创建 updates 文件夹")
    
    print("🚀 启动局域网热更新服务器...")
    print(f"📡 服务器地址: http://{local_ip}:8002")
    print(f"📁 更新文件夹: {os.path.abspath('updates')}")
    print()
    print("📋 可用接口:")
    print(f"  GET  http://{local_ip}:8002/api/check_update?current_version=0.0.2")
    print(f"  GET  http://{local_ip}:8002/api/version_info")
    print(f"  GET  http://{local_ip}:8002/api/download/版本号/文件名.exe")
    print()
    print("💡 使用方法（超级简单）:")
    print("1. 📁 将新版本exe文件复制到 'updates' 文件夹")
    print("2. 🔄 工具会自动检测新版本")
    print("3. 🎯 局域网内的同事点击更新即可自动下载")
    print("4. 🔧 文件名建议包含版本号，如: 美术资源上传工具_v1.0.3.exe")
    print()
    print("🌐 局域网访问说明:")
    print(f"   同事需要将客户端配置中的服务器地址改为: http://{local_ip}:8002")
    print("   或者直接在浏览器访问上述地址测试连通性")
    print()
    print("📂 当前updates文件夹内容:")
    if os.path.exists("updates"):
        files = os.listdir("updates")
        if files:
            for f in files:
                size = os.path.getsize(os.path.join("updates", f))
                print(f"  📄 {f} ({size:,} 字节)")
        else:
            print("  📭 文件夹为空，请放入新版本exe文件")
    print()
    print("✅ 服务器已启动，等待请求...")
    print("   按 Ctrl+C 停止服务器")
    
    server = HTTPServer(('0.0.0.0', 8002), SimpleUpdateHandler)  # 监听所有网络接口
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        server.server_close()

if __name__ == '__main__':
    main()
