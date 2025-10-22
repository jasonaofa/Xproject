#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络统计功能 - 支持局域网统计数据收集
管理员可以收集局域网内所有美术同事的上传统计
"""

import os
import json
import time
import socket
from datetime import datetime
from typing import Dict, List, Any, Optional
from upload_statistics import UploadStatistics, get_statistics_instance

class NetworkStatisticsManager:
    """网络统计管理器 - 支持局域网统计收集"""
    
    def __init__(self, shared_stats_path: str = None):
        """
        初始化网络统计管理器
        
        Args:
            shared_stats_path: 共享统计文件路径（如网络共享文件夹）
        """
        self.local_stats = get_statistics_instance()
        self.shared_stats_path = shared_stats_path or self._get_default_shared_path()
        self.shared_stats = None
        
        if self.shared_stats_path:
            self._init_shared_statistics()
    
    def _get_default_shared_path(self) -> Optional[str]:
        """获取默认的共享统计路径"""
        try:
            # 尝试使用局域网共享路径
            possible_paths = [
                "\\\\10.0.6.231\\shared\\upload_statistics.json",  # 使用您的服务器IP
                "Z:\\upload_statistics.json",  # 映射网络驱动器
                "shared_upload_statistics.json"  # 本地共享文件
            ]
            
            for path in possible_paths:
                try:
                    # 测试路径是否可写
                    test_file = path + ".test"
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    return path
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"⚠️ 获取共享路径失败: {e}")
            return None
    
    def _init_shared_statistics(self):
        """初始化共享统计"""
        try:
            if self.shared_stats_path and os.path.exists(os.path.dirname(self.shared_stats_path)):
                self.shared_stats = UploadStatistics(self.shared_stats_path)
                print(f"✅ 网络统计已启用: {self.shared_stats_path}")
            else:
                print(f"⚠️ 共享路径不可用: {self.shared_stats_path}")
                self.shared_stats = None
        except Exception as e:
            print(f"⚠️ 初始化网络统计失败: {e}")
            self.shared_stats = None
    
    def record_upload(self, file_count: int, file_paths: List[str], 
                     git_path: str = "", additional_info: Dict[str, Any] = None,
                     success: bool = True, error_message: str = "") -> bool:
        """记录上传统计（同时记录到本地和共享位置）"""
        results = []
        
        # 记录到本地
        try:
            local_result = self.local_stats.record_upload(
                file_count, file_paths, git_path, additional_info, success, error_message
            )
            results.append(local_result)
            print(f"📊 本地统计记录: {'成功' if local_result else '失败'}")
        except Exception as e:
            print(f"⚠️ 本地统计记录失败: {e}")
            results.append(False)
        
        # 记录到共享位置
        if self.shared_stats:
            try:
                shared_result = self.shared_stats.record_upload(
                    file_count, file_paths, git_path, additional_info, success, error_message
                )
                results.append(shared_result)
                print(f"🌐 网络统计记录: {'成功' if shared_result else '失败'}")
            except Exception as e:
                print(f"⚠️ 网络统计记录失败: {e}")
                results.append(False)
        
        return any(results)  # 只要有一个成功就返回True
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """获取全局统计数据（优先使用共享统计）"""
        if self.shared_stats:
            try:
                return self.shared_stats.get_summary_stats()
            except Exception as e:
                print(f"⚠️ 获取网络统计失败: {e}")
        
        # 回退到本地统计
        return self.local_stats.get_summary_stats()
    
    def get_global_user_ranking(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取全局用户排行榜"""
        if self.shared_stats:
            try:
                return self.shared_stats.get_user_ranking(limit)
            except Exception as e:
                print(f"⚠️ 获取网络排行榜失败: {e}")
        
        # 回退到本地统计
        return self.local_stats.get_user_ranking(limit)
    
    def export_global_report(self, output_file: str = None) -> str:
        """导出全局统计报告"""
        if self.shared_stats:
            try:
                return self.shared_stats.export_report(output_file)
            except Exception as e:
                print(f"⚠️ 导出网络报告失败: {e}")
        
        # 回退到本地统计
        return self.local_stats.export_report(output_file)
    
    def sync_local_to_shared(self) -> bool:
        """将本地统计数据同步到共享位置"""
        if not self.shared_stats:
            print("⚠️ 网络统计不可用，无法同步")
            return False
        
        try:
            # 获取本地数据
            local_data = self.local_stats.stats_data
            
            # 合并到共享数据中
            for user_id, user_data in local_data.get("users", {}).items():
                if user_id not in self.shared_stats.stats_data["users"]:
                    self.shared_stats.stats_data["users"][user_id] = user_data
                else:
                    # 更新用户数据
                    shared_user = self.shared_stats.stats_data["users"][user_id]
                    shared_user["total_uploads"] = max(shared_user.get("total_uploads", 0), user_data.get("total_uploads", 0))
                    shared_user["total_files"] = max(shared_user.get("total_files", 0), user_data.get("total_files", 0))
                    shared_user["last_upload"] = max(shared_user.get("last_upload", ""), user_data.get("last_upload", ""))
            
            # 保存共享数据
            result = self.shared_stats._save_statistics()
            if result:
                print("✅ 本地数据已同步到网络统计")
            return result
            
        except Exception as e:
            print(f"❌ 同步统计数据失败: {e}")
            return False
    
    def get_network_status(self) -> Dict[str, Any]:
        """获取网络统计状态"""
        return {
            "local_available": self.local_stats is not None,
            "shared_available": self.shared_stats is not None,
            "shared_path": self.shared_stats_path,
            "can_collect_global_stats": self.shared_stats is not None
        }


class NetworkStatisticsServer:
    """网络统计服务器 - 为局域网提供统计API"""
    
    def __init__(self, port: int = 8003):
        self.port = port
        self.stats_manager = NetworkStatisticsManager()
    
    def start_server(self):
        """启动统计服务器"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import urllib.parse
            
            class StatisticsHandler(BaseHTTPRequestHandler):
                def __init__(self, *args, stats_manager=None, **kwargs):
                    self.stats_manager = stats_manager
                    super().__init__(*args, **kwargs)
                
                def do_GET(self):
                    """处理GET请求"""
                    if self.path == '/api/global_stats':
                        self._handle_global_stats()
                    elif self.path == '/api/user_ranking':
                        self._handle_user_ranking()
                    elif self.path == '/api/network_status':
                        self._handle_network_status()
                    else:
                        self._handle_404()
                
                def _handle_global_stats(self):
                    """处理全局统计请求"""
                    try:
                        stats = self.stats_manager.get_global_statistics()
                        self._send_json_response(stats)
                    except Exception as e:
                        self._send_error_response(str(e))
                
                def _handle_user_ranking(self):
                    """处理用户排行榜请求"""
                    try:
                        ranking = self.stats_manager.get_global_user_ranking()
                        self._send_json_response(ranking)
                    except Exception as e:
                        self._send_error_response(str(e))
                
                def _handle_network_status(self):
                    """处理网络状态请求"""
                    try:
                        status = self.stats_manager.get_network_status()
                        self._send_json_response(status)
                    except Exception as e:
                        self._send_error_response(str(e))
                
                def _send_json_response(self, data):
                    """发送JSON响应"""
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = json.dumps(data, ensure_ascii=False, indent=2)
                    self.wfile.write(response.encode('utf-8'))
                
                def _send_error_response(self, error_message):
                    """发送错误响应"""
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error_data = {"error": error_message}
                    response = json.dumps(error_data, ensure_ascii=False)
                    self.wfile.write(response.encode('utf-8'))
                
                def _handle_404(self):
                    """处理404错误"""
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Not Found')
            
            # 创建处理器工厂
            def handler_factory(*args, **kwargs):
                return StatisticsHandler(*args, stats_manager=self.stats_manager, **kwargs)
            
            server = HTTPServer(('0.0.0.0', self.port), handler_factory)
            local_ip = self._get_local_ip()
            
            print(f"🌐 统计服务器已启动")
            print(f"📡 服务器地址: http://{local_ip}:{self.port}")
            print(f"📋 可用接口:")
            print(f"  GET  http://{local_ip}:{self.port}/api/global_stats")
            print(f"  GET  http://{local_ip}:{self.port}/api/user_ranking")
            print(f"  GET  http://{local_ip}:{self.port}/api/network_status")
            print(f"✅ 服务器运行中，按 Ctrl+C 停止...")
            
            server.serve_forever()
            
        except Exception as e:
            print(f"❌ 启动统计服务器失败: {e}")
    
    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


# 全局网络统计管理器
_global_network_stats = None

def get_network_statistics_manager() -> NetworkStatisticsManager:
    """获取全局网络统计管理器"""
    global _global_network_stats
    if _global_network_stats is None:
        _global_network_stats = NetworkStatisticsManager()
    return _global_network_stats

def record_network_upload(file_count: int, file_paths: List[str], 
                         git_path: str = "", additional_info: Dict[str, Any] = None,
                         success: bool = True, error_message: str = "") -> bool:
    """便捷函数：记录网络上传统计"""
    manager = get_network_statistics_manager()
    return manager.record_upload(file_count, file_paths, git_path, additional_info, success, error_message)

def get_global_summary_stats() -> Dict[str, Any]:
    """便捷函数：获取全局统计摘要"""
    manager = get_network_statistics_manager()
    return manager.get_global_statistics()

def get_global_user_ranking(limit: int = 10) -> List[Dict[str, Any]]:
    """便捷函数：获取全局用户排行榜"""
    manager = get_network_statistics_manager()
    return manager.get_global_user_ranking(limit)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # 启动统计服务器
        server = NetworkStatisticsServer()
        server.start_server()
    else:
        # 测试网络统计功能
        print("🧪 测试网络统计功能")
        
        manager = NetworkStatisticsManager()
        status = manager.get_network_status()
        print("网络状态:", json.dumps(status, ensure_ascii=False, indent=2))
        
        # 测试记录
        test_files = ["test1.prefab", "test2.mat"]
        result = record_network_upload(2, test_files, "TestRepo", success=True)
        print(f"记录结果: {result}")
        
        # 获取统计
        stats = get_global_summary_stats()
        print("全局统计:", json.dumps(stats, ensure_ascii=False, indent=2))

