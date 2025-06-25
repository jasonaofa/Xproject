import json
import os
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = {
            "svn_path": "E:/newprefab04",
            "git_path": "E:/git8a/assetruntimenew/CommonResource", 
            "editor_path": "E:/RPGame5.6.9a",
            "window_geometry": {
                "x": 100,
                "y": 100,
                "width": 1200,
                "height": 800
            },
            "last_selected_branch": "",
            "resource_types": {
                "prefab": True,
                "material": True,
                "texture": True,
                "animation": True,
                "script": True
            },
            "recent_files": [],
            "max_recent_files": 10
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有必需的键都存在
                    merged_config = self.default_config.copy()
                    merged_config.update(config)
                    return merged_config
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def get_svn_path(self) -> str:
        return self.get("svn_path", "")
    
    def set_svn_path(self, path: str):
        self.set("svn_path", path)
    
    def get_git_path(self) -> str:
        return self.get("git_path", "")
    
    def set_git_path(self, path: str):
        self.set("git_path", path)
    
    def get_editor_path(self) -> str:
        return self.get("editor_path", "")
    
    def set_editor_path(self, path: str):
        self.set("editor_path", path)
    
    def get_window_geometry(self) -> Dict[str, int]:
        return self.get("window_geometry", {"x": 100, "y": 100, "width": 1200, "height": 800})
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int):
        self.set("window_geometry", {"x": x, "y": y, "width": width, "height": height})
    
    def get_last_selected_branch(self) -> str:
        return self.get("last_selected_branch", "")
    
    def set_last_selected_branch(self, branch: str):
        self.set("last_selected_branch", branch)
    
    def add_recent_file(self, file_path: str):
        """添加最近使用的文件"""
        recent_files = self.get("recent_files", [])
        
        # 如果文件已存在，先移除
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # 添加到列表开头
        recent_files.insert(0, file_path)
        
        # 限制最大数量
        max_files = self.get("max_recent_files", 10)
        if len(recent_files) > max_files:
            recent_files = recent_files[:max_files]
        
        self.set("recent_files", recent_files)
    
    def get_recent_files(self) -> list:
        return self.get("recent_files", [])
    
    def is_resource_type_enabled(self, resource_type: str) -> bool:
        return self.get(f"resource_types.{resource_type}", True)
    
    def set_resource_type_enabled(self, resource_type: str, enabled: bool):
        self.set(f"resource_types.{resource_type}", enabled) 