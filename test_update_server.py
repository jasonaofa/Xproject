#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试热更新服务器
用于测试热更新功能的简单HTTP服务器
"""

import os
import json
import hashlib
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class UpdateServerHandler(BaseHTTPRequestHandler):
    """更新服务器请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            print(f"📡 收到请求: {path}")
            
            if path == '/api/check_update':
                self._handle_check_update(query_params)
            elif path.startswith('/api/download/'):
                self._handle_download(path)
            elif path == '/api/version_info':
                self._handle_version_info()
            else:
                self._send_404()
                
        except Exception as e:
            print(f"❌ 处理请求错误: {e}")
            self._send_error(500, str(e))
    
    def _handle_check_update(self, query_params):
        """处理检查更新请求"""
        current_version = query_params.get('current_version', ['1.0.0'])[0]
        print(f"🔍 检查更新请求 - 当前版本: {current_version}")
        
        # 模拟更新检查逻辑
        latest_version = "1.1.0"  # 模拟有新版本
        has_update = current_version != latest_version
        
        if has_update:
            # 模拟有更新的情况
            response_data = {
                'has_update': True,
                'latest_version': latest_version,
                'current_version': current_version,
                'description': f"""🎉 发现新版本 {latest_version}！

📋 更新内容:
• 🔥 修复了热更新功能连接问题
• 🚀 优化了程序启动速度
• 🎨 改进了用户界面体验
• 🛡️ 增强了文件校验机制
• 📊 新增了详细的更新日志

✨ 新特性:
• 支持一键检查更新
• 自动备份和回滚机制
• 智能增量更新
• 用户友好的进度显示

📈 性能优化:
• 减少了50%的内存占用
• 提升了30%的处理速度
• 优化了网络连接稳定性

建议立即更新以获得最佳体验！""",
                'files': [
                    {
                        'path': 'art_resource_manager.py',
                        'url': f'http://localhost:8000/api/download/v{latest_version}/art_resource_manager.py',
                        'hash': self._get_file_hash('art_resource_manager.py') if os.path.exists('art_resource_manager.py') else '',
                        'size': os.path.getsize('art_resource_manager.py') if os.path.exists('art_resource_manager.py') else 1024000
                    }
                ],
                'mandatory': False,
                'release_date': datetime.now().isoformat(),
                'min_supported_version': '1.0.0'
            }
            print(f"✅ 返回更新信息: 版本 {latest_version}")
        else:
            # 没有更新
            response_data = {
                'has_update': False,
                'message': '当前已是最新版本',
                'latest_version': current_version,
                'current_version': current_version
            }
            print(f"✅ 无需更新: 当前版本 {current_version}")
        
        self._send_json_response(response_data)
    
    def _handle_download(self, path):
        """处理文件下载请求"""
        print(f"📥 文件下载请求: {path}")
        
        # 模拟文件下载 - 返回当前的源文件
        if 'art_resource_manager.py' in path:
            try:
                if os.path.exists('art_resource_manager.py'):
                    with open('art_resource_manager.py', 'rb') as f:
                        file_data = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', 'attachment; filename="art_resource_manager.py"')
                    self.send_header('Content-Length', str(len(file_data)))
                    self.end_headers()
                    self.wfile.write(file_data)
                    
                    print(f"✅ 文件下载成功: art_resource_manager.py ({len(file_data)} bytes)")
                else:
                    self._send_404()
            except Exception as e:
                print(f"❌ 文件下载失败: {e}")
                self._send_error(500, str(e))
        else:
            self._send_404()
    
    def _handle_version_info(self):
        """处理版本信息请求"""
        version_info = {
            'current_version': '1.0.0',
            'latest_version': '1.1.0',
            'server_time': datetime.now().isoformat(),
            'server_status': 'running',
            'available_versions': ['1.0.0', '1.1.0']
        }
        
        print("📊 返回版本信息")
        self._send_json_response(version_info)
    
    def _send_json_response(self, data):
        """发送JSON响应"""
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        json_bytes = json_data.encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(json_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')  # 允许跨域
        self.end_headers()
        self.wfile.write(json_bytes)
    
    def _send_404(self):
        """发送404响应"""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'404 Not Found')
    
    def _send_error(self, code, message):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(f'{code} {message}'.encode('utf-8'))
    
    def _get_file_hash(self, file_path):
        """计算文件SHA256哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"🌐 {datetime.now().strftime('%H:%M:%S')} - {format % args}")

def start_test_server(port=8000):
    """启动测试服务器"""
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, UpdateServerHandler)
    
    print("🚀 启动测试热更新服务器...")
    print(f"📡 服务器地址: http://localhost:{port}")
    print("📋 可用接口:")
    print(f"  GET  http://localhost:{port}/api/check_update?current_version=1.0.0")
    print(f"  GET  http://localhost:{port}/api/download/v1.1.0/art_resource_manager.py")
    print(f"  GET  http://localhost:{port}/api/version_info")
    print()
    print("💡 使用说明:")
    print("1. 启动美术资源上传工具")
    print("2. 点击菜单栏 '帮助' → '检查更新'")
    print("3. 工具会自动连接此服务器检查更新")
    print("4. 按 Ctrl+C 停止服务器")
    print()
    print("✅ 服务器已启动，等待请求...")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        httpd.shutdown()

if __name__ == '__main__':
    start_test_server()
