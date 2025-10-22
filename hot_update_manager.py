#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新管理器 - 为美术资源上传工具提供热更新功能
"""

import os
import sys
import json
import hashlib
import requests
import tempfile
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class HotUpdateManager:
    """热更新管理器"""
    
    def __init__(self, current_version: str = "1.0.0", update_server_url: str = None):
        """
        初始化热更新管理器
        
        Args:
            current_version: 当前版本号
            update_server_url: 更新服务器地址
        """
        self.current_version = current_version
        self.update_server_url = update_server_url or "http://your-update-server.com/api"
        self.app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.temp_dir = os.path.join(tempfile.gettempdir(), "art_tool_update")
        self.backup_dir = os.path.join(self.app_path, "backup")
        self.update_info_file = os.path.join(self.app_path, "update_info.json")
        
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def check_for_updates(self) -> Tuple[bool, Dict]:
        """
        检查是否有可用更新
        
        Returns:
            Tuple[bool, Dict]: (是否有更新, 更新信息)
        """
        try:
            print("🔍 检查更新...")
            
            # 请求更新信息
            response = requests.get(
                f"{self.update_server_url}/check_update",
                params={"current_version": self.current_version},
                timeout=10
            )
            
            if response.status_code == 200:
                update_info = response.json()
                
                if self._compare_versions(update_info.get("latest_version", ""), self.current_version):
                    print(f"✅ 发现新版本: {update_info.get('latest_version')}")
                    return True, update_info
                else:
                    print("✅ 当前已是最新版本")
                    return False, {}
            else:
                print(f"❌ 检查更新失败: HTTP {response.status_code}")
                return False, {}
                
        except requests.RequestException as e:
            print(f"❌ 网络错误: {e}")
            return False, {}
        except Exception as e:
            print(f"❌ 检查更新异常: {e}")
            return False, {}
    
    def download_update(self, update_info: Dict) -> bool:
        """
        下载更新文件
        
        Args:
            update_info: 更新信息
            
        Returns:
            bool: 是否下载成功
        """
        try:
            print("⬇️ 开始下载更新...")
            
            # 获取更新文件列表
            update_files = update_info.get("files", [])
            total_files = len(update_files)
            
            if total_files == 0:
                print("❌ 没有需要更新的文件")
                return False
            
            downloaded_files = []
            
            for i, file_info in enumerate(update_files, 1):
                file_path = file_info["path"]
                file_url = file_info["url"]
                file_hash = file_info.get("hash", "")
                
                print(f"📥 下载文件 ({i}/{total_files}): {file_path}")
                
                # 下载文件
                local_file_path = os.path.join(self.temp_dir, file_path)
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                
                response = requests.get(file_url, stream=True, timeout=30)
                if response.status_code == 200:
                    with open(local_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # 验证文件hash
                    if file_hash and not self._verify_file_hash(local_file_path, file_hash):
                        print(f"❌ 文件校验失败: {file_path}")
                        return False
                    
                    downloaded_files.append({
                        "local_path": local_file_path,
                        "target_path": os.path.join(self.app_path, file_path)
                    })
                    
                    print(f"✅ 下载完成: {file_path}")
                else:
                    print(f"❌ 下载失败: {file_path} (HTTP {response.status_code})")
                    return False
            
            # 保存下载信息
            self._save_download_info(update_info, downloaded_files)
            print("✅ 所有文件下载完成")
            return True
            
        except Exception as e:
            print(f"❌ 下载更新异常: {e}")
            return False
    
    def apply_update(self) -> bool:
        """
        应用更新
        
        Returns:
            bool: 是否应用成功
        """
        try:
            print("🔄 开始应用更新...")
            
            # 读取下载信息
            download_info = self._load_download_info()
            if not download_info:
                print("❌ 没有找到下载信息")
                return False
            
            downloaded_files = download_info.get("files", [])
            new_version = download_info.get("version", self.current_version)
            
            # 备份现有文件
            print("💾 备份现有文件...")
            backup_success = self._backup_files(downloaded_files)
            if not backup_success:
                print("❌ 备份失败，取消更新")
                return False
            
            # 应用更新文件
            print("📝 应用更新文件...")
            for file_info in downloaded_files:
                local_path = file_info["local_path"]
                target_path = file_info["target_path"]
                
                try:
                    # 如果是exe文件，生成新的文件名避免冲突
                    if target_path.endswith('.exe'):
                        # 生成新版本的exe文件名
                        dir_path = os.path.dirname(target_path)
                        base_name = os.path.basename(target_path)
                        
                        # 提取版本号并生成新文件名
                        if '_v' in base_name:
                            # 如果文件名包含版本号，保持原样
                            new_exe_path = target_path
                        else:
                            # 如果没有版本号，添加版本号
                            name_without_ext = os.path.splitext(base_name)[0]
                            new_exe_path = os.path.join(dir_path, f"{name_without_ext}_v{new_version}.exe")
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(new_exe_path), exist_ok=True)
                        
                        # 复制文件到当前目录
                        shutil.copy2(local_path, new_exe_path)
                        print(f"✅ 新版本exe保存到: {new_exe_path}")
                        
                        # 更新文件信息，用于重启
                        file_info["new_exe_path"] = new_exe_path
                        
                    else:
                        # 非exe文件正常处理
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        shutil.copy2(local_path, target_path)
                        print(f"✅ 更新文件: {os.path.basename(target_path)}")
                    
                except Exception as e:
                    print(f"❌ 更新文件失败: {target_path} - {e}")
                    # 如果更新失败，尝试回滚
                    self._rollback_update()
                    return False
            
            # 更新版本信息
            new_version = download_info.get("version", self.current_version)
            self._update_version_info(new_version)
            
            # 保存更新后的exe信息供重启使用
            # 清理临时文件
            self._cleanup_temp_files()
            
            print(f"🎉 更新完成! 版本: {self.current_version} -> {new_version}")
            return True
            
        except Exception as e:
            print(f"❌ 应用更新异常: {e}")
            self._rollback_update()
            return False
    
    def rollback_update(self) -> bool:
        """
        回滚更新
        
        Returns:
            bool: 是否回滚成功
        """
        return self._rollback_update()
    
    def _compare_versions(self, version1: str, version2: str) -> bool:
        """
        比较版本号
        
        Args:
            version1: 版本1
            version2: 版本2
            
        Returns:
            bool: version1 > version2
        """
        def version_tuple(v):
            # 移除版本号前缀（如 'v'）
            clean_v = v.lstrip('v').lstrip('V')
            return tuple(map(int, clean_v.split(".")))
        
        try:
            return version_tuple(version1) > version_tuple(version2)
        except:
            return False
    
    def _verify_file_hash(self, file_path: str, expected_hash: str) -> bool:
        """验证文件hash"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash == expected_hash
        except:
            return False
    
    def _save_download_info(self, update_info: Dict, downloaded_files: List[Dict]):
        """保存下载信息"""
        download_data = {
            "version": update_info.get("latest_version"),
            "download_time": datetime.now().isoformat(),
            "files": downloaded_files
        }
        
        with open(self.update_info_file, 'w', encoding='utf-8') as f:
            json.dump(download_data, f, indent=2, ensure_ascii=False)
    
    def _load_download_info(self) -> Optional[Dict]:
        """加载下载信息"""
        try:
            if os.path.exists(self.update_info_file):
                with open(self.update_info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def _backup_files(self, files_to_update: List[Dict]) -> bool:
        """备份文件"""
        try:
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup_dir = os.path.join(self.backup_dir, f"backup_{backup_timestamp}")
            os.makedirs(current_backup_dir, exist_ok=True)
            
            for file_info in files_to_update:
                target_path = file_info["target_path"]
                
                if os.path.exists(target_path):
                    # 计算备份路径
                    rel_path = os.path.relpath(target_path, self.app_path)
                    backup_path = os.path.join(current_backup_dir, rel_path)
                    
                    # 确保备份目录存在
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    
                    # 备份文件
                    shutil.copy2(target_path, backup_path)
            
            # 保存备份信息
            backup_info = {
                "backup_time": datetime.now().isoformat(),
                "version": self.current_version,
                "files": [f["target_path"] for f in files_to_update]
            }
            
            with open(os.path.join(current_backup_dir, "backup_info.json"), 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return False
    
    def _rollback_update(self) -> bool:
        """回滚更新"""
        try:
            print("🔄 开始回滚更新...")
            
            # 找到最新的备份
            if not os.path.exists(self.backup_dir):
                print("❌ 没有找到备份目录")
                return False
            
            backup_folders = [f for f in os.listdir(self.backup_dir) if f.startswith("backup_")]
            if not backup_folders:
                print("❌ 没有找到备份文件")
                return False
            
            # 选择最新的备份
            latest_backup = max(backup_folders)
            backup_path = os.path.join(self.backup_dir, latest_backup)
            
            # 读取备份信息
            backup_info_file = os.path.join(backup_path, "backup_info.json")
            if os.path.exists(backup_info_file):
                with open(backup_info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                
                # 恢复文件
                for file_path in backup_info.get("files", []):
                    rel_path = os.path.relpath(file_path, self.app_path)
                    backup_file = os.path.join(backup_path, rel_path)
                    
                    if os.path.exists(backup_file):
                        shutil.copy2(backup_file, file_path)
                        print(f"✅ 恢复文件: {os.path.basename(file_path)}")
                
                print("✅ 回滚完成")
                return True
            
        except Exception as e:
            print(f"❌ 回滚失败: {e}")
            return False
    
    def _update_version_info(self, new_version: str):
        """更新版本信息"""
        version_file = os.path.join(self.app_path, "version.json")
        version_info = {
            "version": new_version,
            "update_time": datetime.now().isoformat()
        }
        
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, indent=2, ensure_ascii=False)
        
        self.current_version = new_version
    
    def _save_restart_info(self, downloaded_files: List[Dict], new_version: str):
        """保存重启信息"""
        try:
            # 找到新的exe文件路径
            exe_file = None
            # 获取当前运行的exe路径
            if getattr(sys, 'frozen', False):
                # 打包后的exe环境
                current_exe = sys.executable
            else:
                # 开发环境，使用主exe文件
                current_exe = os.path.join(self.app_path, "美术资源上传工具.exe")
                if not os.path.exists(current_exe):
                    # 如果不存在，查找任何exe文件
                    for f in os.listdir(self.app_path):
                        if f.endswith('.exe') and not f.startswith('美术资源上传工具_v'):
                            current_exe = os.path.join(self.app_path, f)
                            break
            
            for file_info in downloaded_files:
                if file_info.get("new_exe_path"):
                    exe_file = file_info["new_exe_path"]
                    break
                elif file_info["local_path"].endswith(".exe"):
                    exe_file = file_info["local_path"]
                    break
            
            if exe_file:
                restart_info = {
                    "version": new_version,
                    "new_exe_path": exe_file,
                    "old_exe_path": current_exe,
                    "update_time": datetime.now().isoformat()
                }
                
                restart_info_file = os.path.join(self.app_path, "restart_info.json")
                with open(restart_info_file, 'w', encoding='utf-8') as f:
                    json.dump(restart_info, f, indent=2, ensure_ascii=False)
                print(f"💾 保存重启信息: {exe_file}")
                print(f"🗑️ 重启后将删除旧版本: {current_exe}")
        except Exception as e:
            print(f"⚠️ 保存重启信息失败: {e}")

    def _cleanup_temp_files(self, keep_exe=False):
        """清理临时文件"""
        try:
            if keep_exe:
                # 只清理非exe文件，保留exe文件
                if os.path.exists(self.temp_dir):
                    for item in os.listdir(self.temp_dir):
                        item_path = os.path.join(self.temp_dir, item)
                        if not item.endswith('.exe') and os.path.isfile(item_path):
                            os.remove(item_path)
                            print(f"🗑️ 清理文件: {item}")
                print("💾 保留exe文件用于重启")
            else:
                # 清理所有临时文件
                if os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
                    print("🗑️ 清理所有临时文件")
            
            if os.path.exists(self.update_info_file):
                os.remove(self.update_info_file)
                
        except Exception as e:
            print(f"⚠️ 清理临时文件失败: {e}")
    
    def get_current_version(self) -> str:
        """获取当前版本"""
        # 优先从version.json文件读取版本号
        try:
            version_file = os.path.join(self.app_path, "version.json")
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
                    file_version = version_data.get("version", "")
                    if file_version:
                        # 更新内存中的版本号
                        self.current_version = file_version
                        return file_version
        except Exception as e:
            print(f"⚠️ 读取版本文件失败: {e}")
        
        # 如果读取失败，返回内存中的版本号
        return self.current_version
    
    def set_update_server_url(self, url: str):
        """设置更新服务器地址"""
        self.update_server_url = url


# 使用示例
if __name__ == "__main__":
    # 创建热更新管理器
    updater = HotUpdateManager(
        current_version="1.0.0",
        update_server_url="http://your-server.com/api"
    )
    
    # 检查更新
    has_update, update_info = updater.check_for_updates()
    
    if has_update:
        print(f"发现新版本: {update_info.get('latest_version')}")
        print(f"更新说明: {update_info.get('description', '无')}")
        
        # 询问用户是否更新
        user_input = input("是否立即更新? (y/n): ")
        
        if user_input.lower() == 'y':
            # 下载更新
            if updater.download_update(update_info):
                # 应用更新
                if updater.apply_update():
                    print("🎉 更新完成，请重启应用!")
                else:
                    print("❌ 更新失败")
            else:
                print("❌ 下载失败")
    else:
        print("✅ 当前已是最新版本")
