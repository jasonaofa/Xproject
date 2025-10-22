#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于GitHub Releases的热更新服务器
使用GitHub API获取最新版本信息
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from datetime import datetime
import hashlib
import os

class GitHubUpdateHandler(BaseHTTPRequestHandler):
    
    # 配置您的GitHub仓库信息
    GITHUB_OWNER = "jasonaofa"
    GITHUB_REPO = "Xproject"
    GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
    
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
        """处理检查更新请求"""
        try:
            current_version = query_params.get('current_version', ['0.0.0'])[0]
            print(f"🔍 检查更新请求 - 当前版本: {current_version}")
            
            # 从GitHub API获取最新Release
            latest_release = self.get_latest_release()
            
            if not latest_release:
                # 没有发布版本，返回无更新
                response_data = {
                    'has_update': False,
                    'message': '暂无可用更新'
                }
                self.send_json_response(200, response_data)
                return
            
            latest_version = latest_release['tag_name'].lstrip('v')
            has_update = self.compare_versions(latest_version, current_version)
            
            if has_update:
                # 查找exe文件
                exe_asset = None
                for asset in latest_release.get('assets', []):
                    if asset['name'].endswith('.exe'):
                        exe_asset = asset
                        break
                
                if exe_asset:
                    response_data = {
                        'has_update': True,
                        'latest_version': latest_version,
                        'release_notes': latest_release.get('body', ''),
                        'download_url': exe_asset['browser_download_url'],
                        'file_size': exe_asset['size'],
                        'release_date': latest_release.get('published_at', ''),
                        'mandatory': False
                    }
                    print(f"✅ 发现更新: {latest_version}")
                else:
                    response_data = {
                        'has_update': False,
                        'message': '最新版本暂无可执行文件'
                    }
            else:
                response_data = {
                    'has_update': False,
                    'message': '已是最新版本'
                }
                print(f"ℹ️ 已是最新版本: {current_version}")
            
            self.send_json_response(200, response_data)
            
        except Exception as e:
            print(f"❌ 检查更新失败: {e}")
            error_response = {
                'has_update': False,
                'error': f'检查更新失败: {str(e)}'
            }
            self.send_json_response(500, error_response)
    
    def handle_download(self, path):
        """处理下载请求 - 重定向到GitHub"""
        try:
            # 提取版本和文件名
            parts = path.split('/')
            if len(parts) >= 4:
                version = parts[3]
                filename = parts[4] if len(parts) > 4 else '美术资源上传工具.exe'
                
                # 获取对应版本的Release
                release = self.get_release_by_tag(f"v{version}")
                if release:
                    for asset in release.get('assets', []):
                        if asset['name'] == filename or asset['name'].endswith('.exe'):
                            # 重定向到GitHub下载链接
                            self.send_response(302)
                            self.send_header('Location', asset['browser_download_url'])
                            self.end_headers()
                            print(f"📥 重定向下载: {asset['browser_download_url']}")
                            return
            
            self.send_error(404, "文件未找到")
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            self.send_error(500, f"下载失败: {str(e)}")
    
    def handle_version_info(self):
        """处理版本信息请求"""
        try:
            latest_release = self.get_latest_release()
            if latest_release:
                response_data = {
                    'latest_version': latest_release['tag_name'].lstrip('v'),
                    'release_date': latest_release.get('published_at', ''),
                    'release_notes': latest_release.get('body', ''),
                    'download_count': sum(asset.get('download_count', 0) 
                                        for asset in latest_release.get('assets', []))
                }
            else:
                response_data = {
                    'latest_version': '0.0.0',
                    'message': '暂无发布版本'
                }
            
            self.send_json_response(200, response_data)
            
        except Exception as e:
            print(f"❌ 获取版本信息失败: {e}")
            self.send_json_response(500, {'error': str(e)})
    
    def get_latest_release(self):
        """从GitHub API获取最新Release"""
        try:
            url = f"{self.GITHUB_API_BASE}/releases/latest"
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("ℹ️ 暂无GitHub Release")
                return None
            raise
    
    def get_release_by_tag(self, tag):
        """根据标签获取Release"""
        try:
            url = f"{self.GITHUB_API_BASE}/releases/tags/{tag}"
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
    
    def compare_versions(self, version1, version2):
        """比较版本号"""
        def version_tuple(v):
            return tuple(map(int, v.replace('v', '').split('.')))
        
        try:
            return version_tuple(version1) > version_tuple(version2)
        except:
            return False
    
    def send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(json_data.encode('utf-8'))

def main():
    print("🚀 启动GitHub热更新服务器...")
    print(f"📡 GitHub仓库: https://github.com/jasonaofa/Xproject")
    print(f"📡 服务器地址: http://localhost:8001")
    print("📋 可用接口:")
    print("  GET  http://localhost:8001/api/check_update?current_version=0.0.2")
    print("  GET  http://localhost:8001/api/download/1.0.2/美术资源上传工具.exe")
    print("  GET  http://localhost:8001/api/version_info")
    print()
    print("💡 使用说明:")
    print("1. 在GitHub上创建Release并上传exe文件")
    print("2. 修改工具中的服务器地址为: http://localhost:8001/api")
    print("3. 工具会自动从GitHub获取最新版本")
    print("4. 按 Ctrl+C 停止服务器")
    print()
    print("✅ 服务器已启动，等待请求...")
    
    server = HTTPServer(('localhost', 8001), GitHubUpdateHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        server.server_close()

if __name__ == '__main__':
    main()





