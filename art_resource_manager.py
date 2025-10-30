#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import yaml
import re
import subprocess
import shutil
import time
import platform
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple, Any

# 添加Windows特定的subprocess标志
if platform.system() == 'Windows':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0

# 导入热更新管理器
try:
    from hot_update_manager import HotUpdateManager
    HOT_UPDATE_AVAILABLE = True
except ImportError:
    HOT_UPDATE_AVAILABLE = False
    print("⚠️ 热更新功能不可用：缺少hot_update_manager模块")

# 导入统计管理器
try:
    from statistics_ui_manager import create_statistics_ui_manager, record_successful_upload, record_failed_upload
    STATISTICS_AVAILABLE = True
except ImportError:
    STATISTICS_AVAILABLE = False
    print("⚠️ 统计功能不可用：缺少statistics_ui_manager模块")

# 添加错误处理和调试信息
def debug_print(msg):
    print(f"DEBUG: {msg}")

try:
    debug_print("开始导入PyQt5...")
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                                 QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                                 QFileDialog, QComboBox, QCheckBox, QMessageBox, 
                                 QProgressBar, QSplitter, QGroupBox, QGridLayout,
                                 QListWidget, QListWidgetItem, QTabWidget, QDialog, QCompleter,
                                 QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout,
                                 QInputDialog, QSpinBox, QAbstractItemView, QRadioButton,
                                 QAction, QProgressDialog)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QStringListModel
    from PyQt5.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent, QDragMoveEvent
    debug_print("PyQt5导入成功")
    
    debug_print("导入配置管理器...")
    from config import ConfigManager
    debug_print("配置管理器导入成功")
    
    debug_print("导入CRLF自动修复模块...")
    try:
        from crlf_auto_fix import CRLFAutoFixer
        debug_print("CRLF自动修复模块导入成功")
    except ImportError:
        debug_print("CRLF自动修复模块导入失败，将使用备用方案")
        CRLFAutoFixer = None
    
except Exception as e:
    print(f"导入错误: {e}")
    import traceback
    traceback.print_exc()
    input("按Enter键退出...")
    sys.exit(1)


class ResourceDependencyAnalyzer:
    """资源依赖分析器"""
    
    def __init__(self):
        # 编辑器资源文件扩展名到依赖字段的映射
        self.editor_extensions = {
            '.prefab', '.mat', '.controller', '.anim', '.asset', 
            '.unity', '.fbx', '.png', '.jpg', '.jpeg', '.tga', '.psd'
        }
        
        # 着色器GUID映射
        self.common_shader_guids = {
            "00000000000000001000000000000000": "Standard",
            "00000000000000002000000000000000": "UI/Default",
            "00000000000000003000000000000000": "Sprites/Default"
        }
        
        # 内置资源GUID（Unity内置资源）
        self.builtin_guids = {
            "0000000000000000e000000000000000",  # Unity内置材质
            "0000000000000000f000000000000000",  # Unity内置纹理
            "0000000000000000d000000000000000",  # Unity内置着色器
        }
    
    def parse_meta_file(self, meta_path: str) -> str:
        """解析meta文件获取GUID"""
        try:
            with open(meta_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
                
                if not content:
                    print(f"⚠️ meta文件为空: {meta_path}")
                    return None
                
                # 支持YAML格式 - guid: xxxxx
                yaml_match = re.search(r'guid:\s*([a-f0-9]{32})', content, re.IGNORECASE)
                if yaml_match:
                    guid = yaml_match.group(1).lower()
                    print(f"✅ 找到YAML格式GUID: {guid} in {meta_path}")
                    return guid
                
                # 支持JSON格式 - "m_GUID": "xxxxx" (字符串形式)
                json_match = re.search(r'"m_GUID":\s*"([a-f0-9]{32})"', content, re.IGNORECASE)
                if json_match:
                    guid = json_match.group(1).lower()
                    print(f"✅ 找到JSON字符串格式GUID: {guid} in {meta_path}")
                    return guid
                
                # 支持新的Unity JSON对象格式 - "m_GUID": { "data[0]": xxx, "data[1]": xxx, ... }
                try:
                    import json
                    data = json.loads(content)
                    if ('m_MetaHeader' in data and 'm_GUID' in data['m_MetaHeader'] and 
                        isinstance(data['m_MetaHeader']['m_GUID'], dict)):
                        guid_obj = data['m_MetaHeader']['m_GUID']
                        if all(f'data[{i}]' in guid_obj for i in range(4)):
                            # 将4个32位整数转换为32位十六进制字符串
                            data0 = int(guid_obj['data[0]']) & 0xFFFFFFFF
                            data1 = int(guid_obj['data[1]']) & 0xFFFFFFFF  
                            data2 = int(guid_obj['data[2]']) & 0xFFFFFFFF
                            data3 = int(guid_obj['data[3]']) & 0xFFFFFFFF
                            
                            guid = f"{data0:08x}{data1:08x}{data2:08x}{data3:08x}"
                            print(f"✅ 找到JSON对象格式GUID: {guid} in {meta_path}")
                            return guid.lower()
                    elif ('m_MetaHeader' in data and 'm_GUID' in data['m_MetaHeader'] and 
                          isinstance(data['m_MetaHeader']['m_GUID'], str)):
                        # 也支持JSON中的字符串GUID
                        guid = data['m_MetaHeader']['m_GUID'].lower()
                        if len(guid) == 32 and re.match(r'^[a-f0-9]{32}$', guid):
                            print(f"✅ 找到JSON MetaHeader字符串GUID: {guid} in {meta_path}")
                            return guid
                except Exception as json_e:
                    print(f"⚠️ JSON解析失败: {meta_path}, 错误: {json_e}")
                
                # 如果都没找到，打印文件内容的前200个字符用于调试
                preview = content[:200].replace('\n', '\\n').replace('\r', '\\r')
                print(f"❌ 未找到GUID格式匹配: {meta_path}")
                print(f"   文件内容预览: {preview}...")
                
        except Exception as e:
            print(f"❌ 解析meta文件失败: {meta_path}, 错误: {e}")
        return None
    
    def parse_meta_file_debug(self, meta_path: str, show_content: bool = False) -> str:
        """调试版本的meta文件解析，可以显示文件内容"""
        try:
            with open(meta_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                if show_content:
                    print(f"📄 [DEBUG] Meta文件内容 ({meta_path}):")
                    print("-" * 50)
                    print(content[:500])  # 显示前500个字符
                    print("-" * 50)
                
                # 支持YAML格式 - guid: xxxxx
                yaml_match = re.search(r'guid:\s*([a-f0-9]{32})', content, re.IGNORECASE)
                if yaml_match:
                    guid = yaml_match.group(1).lower()
                    print(f"✅ [DEBUG] YAML格式匹配到GUID: {guid}")
                    return guid
                
                # 支持JSON格式 - "m_GUID": "xxxxx" (字符串形式)
                json_match = re.search(r'"m_GUID":\s*"([a-f0-9]{32})"', content, re.IGNORECASE)
                if json_match:
                    guid = json_match.group(1).lower()
                    print(f"✅ [DEBUG] JSON字符串格式匹配到GUID: {guid}")
                    return guid
                
                # 支持新的Unity JSON对象格式 - "m_GUID": { "data[0]": xxx, "data[1]": xxx, ... }
                try:
                    import json
                    data = json.loads(content)
                    if ('m_MetaHeader' in data and 'm_GUID' in data['m_MetaHeader'] and 
                        isinstance(data['m_MetaHeader']['m_GUID'], dict)):
                        guid_obj = data['m_MetaHeader']['m_GUID']
                        if all(f'data[{i}]' in guid_obj for i in range(4)):
                            # 将4个32位整数转换为32位十六进制字符串
                            data0 = int(guid_obj['data[0]']) & 0xFFFFFFFF
                            data1 = int(guid_obj['data[1]']) & 0xFFFFFFFF  
                            data2 = int(guid_obj['data[2]']) & 0xFFFFFFFF
                            data3 = int(guid_obj['data[3]']) & 0xFFFFFFFF
                            
                            guid = f"{data0:08x}{data1:08x}{data2:08x}{data3:08x}"
                            print(f"✅ [DEBUG] JSON对象格式匹配到GUID: {guid}")
                            print(f"   原始数据: [{guid_obj['data[0]']}, {guid_obj['data[1]']}, {guid_obj['data[2]']}, {guid_obj['data[3]']}]")
                            return guid.lower()
                except Exception as e:
                    print(f"🔍 [DEBUG] JSON对象格式解析失败: {e}")
                
                # 尝试找到任何包含"guid"的行
                lines_with_guid = [line.strip() for line in content.split('\n') if 'guid' in line.lower()]
                if lines_with_guid:
                    print(f"❓ [DEBUG] 找到包含'guid'的行但未匹配:")
                    for line in lines_with_guid[:3]:  # 显示前3行
                        print(f"   {line}")
                
                print(f"❌ [DEBUG] 未找到有效GUID格式")
                
        except Exception as e:
            print(f"解析meta文件失败: {meta_path}, 错误: {e}")
        return None
    
    def parse_editor_asset(self, file_path: str) -> Set[str]:
        """解析编辑器资源文件，提取依赖的GUID"""
        dependencies = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查文件格式
            if content.strip().startswith('{'):
                # JSON格式
                print(f"🔍 [DEBUG] 检测到JSON格式文件: {os.path.basename(file_path)}")
                dependencies.update(self._parse_json_asset(content, file_path))
            elif content.startswith('%YAML'):
                # YAML格式
                print(f"🔍 [DEBUG] 检测到YAML格式文件: {os.path.basename(file_path)}")
                dependencies.update(self._parse_yaml_asset(content, file_path))
            else:
                # 尝试通用GUID提取
                print(f"🔍 [DEBUG] 使用通用GUID提取: {os.path.basename(file_path)}")
                dependencies.update(self._extract_guids_generic(content))
                
        except Exception as e:
            print(f"解析资源文件失败: {file_path}, 错误: {e}")
        
        return dependencies
    
    def _parse_json_asset(self, content: str, file_path: str) -> Set[str]:
        """解析JSON格式的编辑器资源文件"""
        dependencies = set()
        
        try:
            # 获取文件自身的GUID
            self_guid = None
            meta_path = file_path + '.meta'
            if os.path.exists(meta_path):
                self_guid = self.parse_meta_file(meta_path)
            
            # 使用正则表达式提取所有GUID - 增强版本
            guid_patterns = [
                r'"m_GUID":\s*"([a-f0-9]{32})"',  # 标准m_GUID格式
                r'"guid":\s*"([a-f0-9]{32})"',    # 标准guid格式
                r'"GUID":\s*"([a-f0-9]{32})"',    # 大写GUID格式
                r'"m_SourcePrefabGUID":\s*"([a-f0-9]{32})"',  # prefab中的SourcePrefabGUID引用
                r'"SourcePrefabGUID":\s*"([a-f0-9]{32})"',    # SourcePrefabGUID引用
                r'"texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"',  # 贴图引用
                r'"texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"', # 贴图m_GUID引用
                r'"m_Texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"', # m_Texture引用
                r'"m_Texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"', # m_Texture m_GUID引用
            ]
            
            for pattern in guid_patterns:
                guids = re.findall(pattern, content, re.IGNORECASE)
                for guid in guids:
                    guid = guid.lower()
                    # 过滤掉自身GUID和常见系统GUID
                    if (guid != self_guid and 
                        guid not in self.common_shader_guids and
                        not guid.startswith('00000000000000')):
                        dependencies.add(guid)
                        print(f"🔍 [DEBUG] 在JSON文件 {os.path.basename(file_path)} 中找到GUID: {guid}")
                    
        except Exception as e:
            print(f"解析JSON资源失败: {file_path}, 错误: {e}")
            
        return dependencies
    
    def _parse_yaml_asset(self, content: str, file_path: str) -> Set[str]:
        """解析YAML格式的编辑器资源文件"""
        dependencies = set()
        
        try:
            # 获取文件自身的GUID
            self_guid = None
            meta_path = file_path + '.meta'
            if os.path.exists(meta_path):
                self_guid = self.parse_meta_file(meta_path)
            
            # YAML格式的GUID提取 - 增强版本
            guid_patterns = [
                r'guid:\s*([a-f0-9]{32})',           # 标准GUID格式
                r'm_GUID:\s*([a-f0-9]{32})',         # m_GUID格式
                r'texture:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})',  # 材质中的贴图引用
                r'texture:\s*{fileID:\s*0,\s*guid:\s*([a-f0-9]{32})',    # 材质中的贴图引用（fileID为0）
                r'texture:\s*{guid:\s*([a-f0-9]{32})',                   # 简化的贴图引用
                r'texture:\s*{.*?guid:\s*([a-f0-9]{32})',                # 材质中的贴图引用（任意内容）
                r'm_Texture:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})', # m_Texture引用
                r'm_Texture:\s*{guid:\s*([a-f0-9]{32})',                 # m_Texture只有guid
                r'texture2D:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})', # texture2D引用
                r'texture2D:\s*{guid:\s*([a-f0-9]{32})',                 # texture2D只有guid
                r'([a-f0-9]{32})',                   # 通用32位十六进制（作为后备）
            ]
            
            for pattern in guid_patterns:
                guids = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                for guid in guids:
                    guid = guid.lower()
                    # 过滤掉自身GUID和常见系统GUID
                    if (guid != self_guid and 
                        guid not in self.common_shader_guids and
                        not guid.startswith('00000000000000')):
                        dependencies.add(guid)
                        print(f"🔍 [DEBUG] 在 {os.path.basename(file_path)} 中找到GUID: {guid}")
                
        except Exception as e:
            print(f"解析YAML资源失败: {file_path}, 错误: {e}")
            
        return dependencies
    
    def _extract_guids_generic(self, content: str) -> Set[str]:
        """通用GUID提取方法"""
        dependencies = set()
        
        # 通用GUID模式
        guid_patterns = [
            r'([a-f0-9]{32})',  # 32位十六进制字符串
            r'"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"'  # 标准GUID格式
        ]
        
        for pattern in guid_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # 移除连字符并转为小写
                clean_guid = match.replace('-', '').lower()
                if len(clean_guid) == 32 and clean_guid.isalnum():
                    dependencies.add(clean_guid)
        
        return dependencies
    
    def find_dependency_files(self, file_paths: List[str], search_directories: List[str] = None) -> Dict[str, Any]:
        """
        分析文件依赖并找到所有相关的文件（包括meta文件）
        
        Args:
            file_paths: 要分析的文件路径列表
            search_directories: 搜索依赖文件的目录列表（可选）
            
        Returns:
            Dict[str, Any]: 包含分析结果的字典
        """
        result = {
            'original_files': file_paths,
            'dependency_files': [],  # 找到的依赖文件
            'meta_files': [],        # 相关的meta文件
            'guid_to_file_map': {},  # GUID到文件路径的映射
            'file_to_guid_map': {},  # 文件路径到GUID的映射
            'missing_dependencies': [],  # 缺失的依赖
            'analysis_stats': {
                'total_original': len(file_paths),
                'total_dependencies': 0,
                'total_meta_files': 0,
                'total_missing': 0
            }
        }
        
        try:
            # 1. 建立搜索目录 - 改进：使用整个SVN仓库作为搜索范围
            if not search_directories:
                # 如果没有指定搜索目录，尝试找到SVN仓库根目录
                svn_root = self._find_svn_root_from_files(file_paths)
                if svn_root:
                    search_directories = [svn_root]
                    print(f"🔍 自动找到SVN根目录: {svn_root}")
                else:
                    # 回退到原始文件所在的目录
                    search_directories = list(set([os.path.dirname(f) for f in file_paths]))
                    print(f"⚠️ 未找到SVN根目录，使用文件所在目录: {search_directories}")
            
            # 2. 扫描搜索目录中的所有meta文件，建立GUID映射
            print(f"🔍 开始扫描 {len(search_directories)} 个目录...")
            for search_dir in search_directories:
                if os.path.exists(search_dir):
                    self._scan_directory_for_guids(search_dir, result['guid_to_file_map'])
            
            print(f"✅ 扫描完成，找到 {len(result['guid_to_file_map'])} 个GUID映射")
            
            # 3. 分析每个原始文件的依赖
            print(f"🔍 开始分析 {len(file_paths)} 个文件的依赖...")
            for file_path in file_paths:
                if os.path.exists(file_path):
                    self._analyze_file_dependencies(file_path, result)
            
            # 4. 去重并统计
            result['dependency_files'] = list(set(result['dependency_files']))
            result['meta_files'] = list(set(result['meta_files']))
            
            result['analysis_stats']['total_dependencies'] = len(result['dependency_files'])
            result['analysis_stats']['total_meta_files'] = len(result['meta_files'])
            result['analysis_stats']['total_missing'] = len(result['missing_dependencies'])
            
            print(f"📊 分析完成:")
            print(f"   原始文件: {result['analysis_stats']['total_original']}")
            print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
            print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
            print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
            
        except Exception as e:
            print(f"❌ 依赖分析失败: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _find_svn_root_from_files(self, file_paths: List[str]) -> str:
        """从文件路径中找到SVN仓库根目录"""
        if not file_paths:
            return ""
        
        # 从第一个文件开始向上查找SVN根目录
        first_file = file_paths[0]
        current_path = os.path.dirname(os.path.abspath(first_file))
        
        while current_path:
            # 检查是否有.svn目录
            svn_dir = os.path.join(current_path, '.svn')
            if os.path.exists(svn_dir) and os.path.isdir(svn_dir):
                return current_path
            
            # 向上查找父目录
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:  # 已经到达根目录
                break
            current_path = parent_path
        
        return ""
    
    def _scan_directory_for_guids(self, directory: str, guid_map: Dict[str, str]):
        """扫描目录中的所有meta文件，建立GUID映射"""
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.meta'):
                        meta_path = os.path.join(root, file)
                        guid = self.parse_meta_file(meta_path)
                        if guid:
                            # 计算对应的资源文件路径
                            resource_path = meta_path[:-5]  # 移除.meta后缀
                            
                            # 🚨 关键修复：只有资源文件真实存在时，才认为GUID有效
                            if os.path.exists(resource_path):
                                guid_map[guid] = resource_path
                            else:
                                print(f"⚠️ [GUID] 发现孤儿meta文件: {meta_path}")
                                print(f"   对应资源文件不存在: {resource_path}")
                                print(f"   跳过GUID: {guid}")
                                # 🚨 增强调试：记录被跳过的孤儿GUID
                                if not hasattr(self, '_orphan_guids'):
                                    self._orphan_guids = set()
                                self._orphan_guids.add(guid)
        except Exception as e:
            print(f"❌ 扫描目录失败 {directory}: {e}")
    
    def _analyze_file_dependencies(self, file_path: str, result: Dict[str, Any], analyzed_files: set = None):
        """分析单个文件的依赖"""
        if analyzed_files is None:
            analyzed_files = set()
        
        # 避免重复分析
        if file_path in analyzed_files:
            print(f"🔍 [DEBUG] 跳过重复分析: {os.path.basename(file_path)}")
            return
        
        analyzed_files.add(file_path)
        
        # 标准化原始文件路径列表（用于比较）
        normalized_original_files = set()
        for orig_file in result['original_files']:
            normalized_original_files.add(os.path.normpath(os.path.abspath(orig_file)))
        
        try:
            # 获取文件自身的GUID
            file_guid = None
            
            # 处理原始文件本身的meta文件
            if file_path.endswith('.meta'):
                # 如果是meta文件，获取其GUID并添加对应的资源文件
                file_guid = self.parse_meta_file(file_path)
                resource_path = file_path[:-5]
                if os.path.exists(resource_path):
                    # 检查资源文件是否已经在原始文件列表中
                    normalized_resource_path = os.path.normpath(os.path.abspath(resource_path))
                    if normalized_resource_path not in normalized_original_files:
                        result['dependency_files'].append(resource_path)
                        print(f"🔍 [DEBUG] 添加meta文件对应的资源: {os.path.basename(resource_path)}")
                    else:
                        print(f"🔍 [DEBUG] 跳过重复的原始文件: {os.path.basename(resource_path)}")
            else:
                # 如果是资源文件，添加对应的meta文件
                meta_path = file_path + '.meta'
                if os.path.exists(meta_path):
                    file_guid = self.parse_meta_file(meta_path)
                    # 确保原始文件的meta文件被添加到结果中
                    result['meta_files'].append(meta_path)
                    print(f"🔍 [DEBUG] 添加资源文件对应的meta: {os.path.basename(meta_path)}")
            
            # 记录文件到GUID的映射
            if file_guid:
                result['file_to_guid_map'][file_path] = file_guid
            
            # 分析文件中的GUID引用（只对非meta文件进行）
            if not file_path.endswith('.meta'):
                referenced_guids = self.parse_editor_asset(file_path)
                print(f"🔍 [DEBUG] {os.path.basename(file_path)} 中找到 {len(referenced_guids)} 个GUID引用")
                
                # 用于递归分析的依赖文件列表
                recursive_deps = []
                
                for ref_guid in referenced_guids:
                    print(f"🔍 [DEBUG] 处理GUID: {ref_guid}")
                    
                    # 跳过内置资源和自身引用
                    if (ref_guid in self.builtin_guids or 
                        ref_guid in self.common_shader_guids or
                        ref_guid == file_guid or
                        ref_guid.startswith('00000000000000')):
                        print(f"🔍 [DEBUG] 跳过GUID {ref_guid} (内置资源或自身引用)")
                        continue
                    
                    # 查找依赖文件
                    if ref_guid in result['guid_to_file_map']:
                        dep_file = result['guid_to_file_map'][ref_guid]
                        print(f"🔍 [DEBUG] 找到依赖文件: {os.path.basename(dep_file)}")
                        
                        if os.path.exists(dep_file):
                            # 检查依赖文件是否已经在原始文件列表中
                            normalized_dep_file = os.path.normpath(os.path.abspath(dep_file))
                            if normalized_dep_file not in normalized_original_files:
                                result['dependency_files'].append(dep_file)
                                print(f"🔍 [DEBUG] 添加依赖文件: {os.path.basename(dep_file)}")
                                
                                # 添加对应的meta文件
                                dep_meta = dep_file + '.meta'
                                if os.path.exists(dep_meta):
                                    result['meta_files'].append(dep_meta)
                                    print(f"🔍 [DEBUG] 添加依赖meta文件: {os.path.basename(dep_meta)}")
                                
                                # 如果是材质文件，添加到递归分析列表
                                if dep_file.lower().endswith('.mat'):
                                    recursive_deps.append(dep_file)
                                    print(f"🔍 [DEBUG] 添加到递归分析: {os.path.basename(dep_file)}")
                            else:
                                print(f"🔍 [DEBUG] 跳过重复的原始文件: {os.path.basename(dep_file)}")
                        else:
                            print(f"🔍 [DEBUG] 依赖文件不存在: {dep_file}")
                            result['missing_dependencies'].append({
                                'guid': ref_guid,
                                'referenced_by': file_path,
                                'expected_path': dep_file
                            })
                    else:
                        print(f"🔍 [DEBUG] 在GUID映射中未找到: {ref_guid}")
                        
                        # 🚨 新增：检查是否为系统默认材质的GUID引用
                        # 这里我们可以添加一些已知的系统材质GUID，或者通过其他方式识别
                        # 暂时先记录为缺失，后续在检查阶段会被系统材质检查逻辑过滤
                        result['missing_dependencies'].append({
                            'guid': ref_guid,
                            'referenced_by': file_path,
                            'expected_path': 'unknown'
                        })
                
                # 递归分析材质文件中的贴图引用
                if recursive_deps:
                    print(f"🔍 [DEBUG] 开始递归分析 {len(recursive_deps)} 个材质文件...")
                    for dep_file in recursive_deps:
                        if dep_file not in result['original_files']:  # 避免重复分析
                            self._analyze_file_dependencies(dep_file, result, analyzed_files)
                        
        except Exception as e:
            print(f"❌ 分析文件依赖失败 {file_path}: {e}")
    
    def analyze_resource_package(self, package_path: str) -> Dict[str, Any]:
        """分析资源包，返回完整的分析报告"""
        report = {
            'package_path': package_path,
            'files': {},
            'dependencies': {},
            'guid_map': {},
            'missing_dependencies': set(),
            'internal_conflicts': set(),
            'file_structure': {},
            'validation_errors': []
        }
        
        try:
            package_dir = Path(package_path)
            if not package_dir.exists():
                report['validation_errors'].append(f"资源包路径不存在: {package_path}")
                return report
            
            # 1. 扫描所有文件
            all_files = []
            for file_path in package_dir.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    all_files.append(str(file_path))
            
            report['files']['total_count'] = len(all_files)
            report['files']['asset_files'] = []
            report['files']['meta_files'] = []
            report['files']['other_files'] = []
            
            # 2. 分类文件
            for file_path in all_files:
                if file_path.endswith('.meta'):
                    report['files']['meta_files'].append(file_path)
                elif any(file_path.lower().endswith(ext) for ext in self.editor_extensions):
                    report['files']['asset_files'].append(file_path)
                else:
                    report['files']['other_files'].append(file_path)
            
            # 3. 建立GUID映射
            for meta_file in report['files']['meta_files']:
                guid = self.parse_meta_file(meta_file)
                if guid:
                    asset_file = meta_file[:-5]  # 移除.meta后缀
                    # 🚨 关键修复：只有资源文件真实存在时，才认为GUID有效
                    if os.path.exists(asset_file):
                        report['guid_map'][guid] = {
                            'asset_file': asset_file,
                            'meta_file': meta_file,
                            'exists': True
                        }
                    else:
                        print(f"⚠️ [GUID] 发现孤儿meta文件: {meta_file}")
                        print(f"   对应资源文件不存在: {asset_file}")
                        print(f"   跳过GUID: {guid}")
            
            # 4. 分析依赖关系
            for asset_file in report['files']['asset_files']:
                if os.path.exists(asset_file):
                    deps = self.parse_editor_asset(asset_file)
                    if deps:
                        report['dependencies'][asset_file] = list(deps)
            
            # 5. 检查缺失依赖
            all_deps = set()
            for deps in report['dependencies'].values():
                all_deps.update(deps)
            
            available_guids = set(report['guid_map'].keys())
            report['missing_dependencies'] = all_deps - available_guids
            
            # 6. 检查内部GUID冲突
            guid_count = {}
            for guid in report['guid_map'].keys():
                guid_count[guid] = guid_count.get(guid, 0) + 1
            
            report['internal_conflicts'] = {guid for guid, count in guid_count.items() if count > 1}
            
            # 7. 分析文件结构
            report['file_structure'] = self._analyze_file_structure(package_dir)
            
        except Exception as e:
            report['validation_errors'].append(f"分析过程中发生错误: {str(e)}")
        
        return report
    
    def _analyze_file_structure(self, package_dir: Path) -> Dict[str, Any]:
        """分析文件结构"""
        structure = {
            'directories': [],
            'has_prefab': False,
            'has_materials': False,
            'has_textures': False,
            'has_models': False,
            'has_animations': False,
            'naming_issues': []
        }
        
        for item in package_dir.rglob('*'):
            if item.is_dir():
                structure['directories'].append(str(item.relative_to(package_dir)))
            elif item.is_file():
                file_ext = item.suffix.lower()
                file_name = item.name
                
                # 检查文件类型
                if file_ext == '.prefab':
                    structure['has_prefab'] = True
                elif file_ext == '.mat':
                    structure['has_materials'] = True
                elif file_ext in ['.png', '.jpg', '.jpeg', '.tga', '.psd']:
                    structure['has_textures'] = True
                elif file_ext in ['.fbx', '.obj', '.3ds']:
                    structure['has_models'] = True
                elif file_ext in ['.anim', '.controller']:
                    structure['has_animations'] = True
                
                # 检查命名问题
                if ' ' in file_name:
                    structure['naming_issues'].append(f"文件名包含空格: {file_name}")
                if any(ord(c) > 127 for c in file_name):
                    structure['naming_issues'].append(f"文件名包含非ASCII字符: {file_name}")
        
        return structure

    def get_all_dependencies(self, file_paths: List[str]) -> Dict[str, Set[str]]:
        """获取所有文件的依赖关系"""
        all_deps = {}
        for file_path in file_paths:
            if any(file_path.lower().endswith(ext) for ext in self.editor_extensions):
                deps = self.parse_editor_asset(file_path)
                if deps:
                    all_deps[file_path] = deps
        return all_deps

    def _check_dependencies_enhanced(self, package_report: dict) -> dict:
        """增强的依赖检查 - 完善版本"""
        result = {
            'success': True,
            'missing_internal': [],
            'missing_external': [],
            'missing_details': {},
            'available_in_git': [],
            'builtin_references': [],
            'warnings': [],
            'info': [],
            'summary': {}
        }
        
        # 编辑器内置GUID（不需要检查的系统资源）
        builtin_guids = {
            "0000000000000000e000000000000000",  # Built-in Shader
            "0000000000000000f000000000000000",  # Built-in Extra
        }
        
        missing_deps = package_report.get('missing_dependencies', set())
        dependencies = package_report.get('dependencies', {})
        package_guids = set(package_report.get('guid_map', {}).keys())
        
        if missing_deps:
            # 获取Git仓库中的GUID
            git_guids = self._get_git_repository_guids()
            
            # 建立反向映射：GUID -> 引用它的文件列表
            guid_to_files = {}
            for asset_file, deps in dependencies.items():
                for dep_guid in deps:
                    if dep_guid not in guid_to_files:
                        guid_to_files[dep_guid] = []
                    guid_to_files[dep_guid].append(asset_file)
            
            # 分类处理缺失的依赖
            for dep_guid in missing_deps:
                referencing_files = guid_to_files.get(dep_guid, [])
                
                if dep_guid in builtin_guids:
                    # 内置资源，正常情况
                    result['builtin_references'].append(dep_guid)
                    result['info'].append(f"引用内置资源: {dep_guid}")
                elif dep_guid in git_guids:
                    # 在Git仓库中找到，这是好的
                    result['available_in_git'].append(dep_guid)
                    result['info'].append(f"外部依赖在Git仓库中找到: {dep_guid}")
                else:
                    # 真正缺失的外部依赖
                    result['missing_external'].append(dep_guid)
                    result['missing_details'][dep_guid] = {
                        'referencing_files': [os.path.basename(f) for f in referencing_files],
                        'full_paths': referencing_files,
                        'severity': 'critical'  # 标记严重程度
                    }
        
        # 检查依赖合理性
        for asset_file, deps in dependencies.items():
            if len(deps) > 15:  # 依赖过多
                result['warnings'].append(f"文件 {os.path.basename(asset_file)} 依赖过多 ({len(deps)} 个)")
            elif len(deps) == 0:
                result['info'].append(f"文件 {os.path.basename(asset_file)} 无外部依赖")
        
        # 生成摘要信息
        total_refs = sum(len(deps) for deps in dependencies.values())
        result['summary'] = {
            'total_files_analyzed': len(dependencies),
            'total_references': total_refs,
            'missing_external_count': len(result['missing_external']),
            'available_in_git_count': len(result['available_in_git']),
            'builtin_references_count': len(result['builtin_references']),
            'files_with_many_deps': len([f for f, deps in dependencies.items() if len(deps) > 10])
        }
        
        # 判断是否成功
        if result['missing_external']:
            result['success'] = False
        
        return result

    def _get_git_repository_guids(self) -> Set[str]:
        """获取Git仓库中的所有GUID"""
        git_guids = set()
        
        if not self.git_manager.git_path or not os.path.exists(self.git_manager.git_path):
            self.status_updated.emit(f"❌ Git仓库路径无效: {self.git_manager.git_path}")
            return git_guids
        
        self.status_updated.emit(f"🔍 开始扫描Git仓库: {self.git_manager.git_path}")
        
        # 统计信息
        scan_stats = {
            'directories_scanned': 0,
            'meta_files_found': 0,
            'meta_files_parsed_success': 0,
            'meta_files_parsed_failed': 0,
            'guids_extracted': 0,
            'failed_files': [],
            'sample_success_files': [],
            'sample_guids': []
        }
        
        try:
            # 扫描Git仓库中的.meta文件
            for root, dirs, files in os.walk(self.git_manager.git_path):
                scan_stats['directories_scanned'] += 1
                
                # 每扫描100个目录输出一次进度
                if scan_stats['directories_scanned'] % 100 == 0:
                    self.status_updated.emit(f"  📁 已扫描 {scan_stats['directories_scanned']} 个目录...")
                
                # 记录深层目录（用于调试）
                relative_path = os.path.relpath(root, self.git_manager.git_path)
                depth = len(relative_path.split(os.sep)) if relative_path != '.' else 0
                
                for file in files:
                    if file.endswith('.meta'):
                        scan_stats['meta_files_found'] += 1
                        meta_path = os.path.join(root, file)
                        
                        # 记录特定文件（用于调试）
                        if 'Character_NPR_Opaque.templatemat.meta' in file:
                            self.status_updated.emit(f"  🎯 找到目标文件: {meta_path}")
                            self.status_updated.emit(f"     相对路径: {relative_path}")
                            self.status_updated.emit(f"     目录深度: {depth}")
                        
                        try:
                            guid = self.parse_meta_file(meta_path)
                            if guid:
                                # 🚨 关键修复：检查对应的资源文件是否存在
                                resource_path = meta_path[:-5]  # 移除.meta后缀
                                if os.path.exists(resource_path):
                                    git_guids.add(guid)
                                    scan_stats['meta_files_parsed_success'] += 1
                                    scan_stats['guids_extracted'] += 1
                                    
                                    # 记录成功解析的样本
                                    if len(scan_stats['sample_success_files']) < 5:
                                        scan_stats['sample_success_files'].append({
                                            'file': os.path.relpath(meta_path, self.git_manager.git_path),
                                            'guid': guid
                                        })
                                    
                                    # 记录特定GUID
                                    if guid == 'a52adbec141594d439747c542824c830':
                                        self.status_updated.emit(f"  ✅ 找到目标GUID: {guid}")
                                        self.status_updated.emit(f"     文件路径: {meta_path}")
                                    
                                    # 记录样本GUID
                                    if len(scan_stats['sample_guids']) < 10:
                                        scan_stats['sample_guids'].append(guid)
                                else:
                                    # 记录孤儿meta文件
                                    scan_stats['meta_files_parsed_failed'] += 1
                                    scan_stats['failed_files'].append({
                                        'file': os.path.relpath(meta_path, self.git_manager.git_path),
                                        'reason': 'orphan_meta_file',
                                        'resource_path': os.path.relpath(resource_path, self.git_manager.git_path)
                                    })
                                    # 调试输出孤儿文件
                                    if len(scan_stats['failed_files']) <= 5:  # 只显示前5个
                                        self.status_updated.emit(f"⚠️ [GUID] 发现孤儿meta文件: {os.path.relpath(meta_path, self.git_manager.git_path)}")
                                        self.status_updated.emit(f"   对应资源文件不存在: {os.path.relpath(resource_path, self.git_manager.git_path)}")
                                        self.status_updated.emit(f"   跳过GUID: {guid}")
                            else:
                                scan_stats['meta_files_parsed_failed'] += 1
                                scan_stats['failed_files'].append({
                                    'file': os.path.relpath(meta_path, self.git_manager.git_path),
                                    'reason': 'GUID解析失败'
                                })
                        except Exception as e:
                            scan_stats['meta_files_parsed_failed'] += 1
                            scan_stats['failed_files'].append({
                                'file': os.path.relpath(meta_path, self.git_manager.git_path),
                                'reason': f'异常: {str(e)}'
                            })
                            self.status_updated.emit(f"  ❌ 解析meta文件异常: {meta_path}")
                            self.status_updated.emit(f"     错误: {e}")
                            
        except Exception as e:
            self.status_updated.emit(f"❌ 扫描Git仓库异常: {e}")
            import traceback
            traceback.print_exc()
        
        # 输出详细统计信息
        print(f"\n📊 Git仓库扫描完成统计:")
        print(f"   📁 扫描目录数: {scan_stats['directories_scanned']}")
        print(f"   📄 找到meta文件数: {scan_stats['meta_files_found']}")
        print(f"   ✅ 解析成功: {scan_stats['meta_files_parsed_success']}")
        print(f"   ❌ 解析失败: {scan_stats['meta_files_parsed_failed']}")
        print(f"   🔑 提取GUID数: {scan_stats['guids_extracted']}")
        
        # 显示成功解析的样本
        if scan_stats['sample_success_files']:
            print(f"\n📝 成功解析的样本文件:")
            for sample in scan_stats['sample_success_files']:
                print(f"   {sample['file']} -> {sample['guid']}")
        
        # 显示解析失败的文件（最多5个）
        if scan_stats['failed_files']:
            print(f"\n⚠️  解析失败的文件样本:")
            for failed in scan_stats['failed_files'][:5]:
                print(f"   {failed['file']}: {failed['reason']}")
            if len(scan_stats['failed_files']) > 5:
                print(f"   ... 还有 {len(scan_stats['failed_files']) - 5} 个失败文件")
        
        # 显示样本GUID
        if scan_stats['sample_guids']:
            print(f"\n🔑 样本GUID:")
            for guid in scan_stats['sample_guids'][:5]:
                print(f"   {guid}")
        
        # 检查特定GUID是否存在
        target_guid = 'a52adbec141594d439747c542824c830'
        if target_guid in git_guids:
            print(f"\n✅ 目标GUID {target_guid} 已找到!")
        else:
            print(f"\n❌ 目标GUID {target_guid} 未找到!")
        
        print(f"\n🎯 最终结果: 从Git仓库中提取了 {len(git_guids)} 个唯一GUID")
        
        return git_guids
    
    def _determine_package_root(self) -> str:
        """确定资源包根目录"""
        if not self.upload_files:
            return None
        
        # 如果只有一个文件，返回其所在目录
        if len(self.upload_files) == 1:
            return os.path.dirname(self.upload_files[0])
        
        # 如果有多个文件，找到它们的共同父目录
        try:
            common_prefix = os.path.commonpath(self.upload_files)
            return common_prefix
        except ValueError:
            # 如果文件在不同的驱动器上，返回第一个文件的目录
            return os.path.dirname(self.upload_files[0])
    
    def _generate_comprehensive_report(self) -> dict:
        """生成综合检查报告"""
        result = {
            'success': True,
            'message': '',
            'summary': {},
            'details': {}
        }
        
        # 汇总所有检查结果
        internal_check = self.detailed_check_report.get('internal_consistency', {})
        external_check = self.detailed_check_report.get('external_compatibility', {})
        reference_check = self.detailed_check_report.get('reference_validity', {})
        dependency_chain_check = self.detailed_check_report.get('dependency_chain', {})
        
        # 检查是否有严重问题
        critical_issues = []
        
        if not internal_check.get('success', True):
            critical_issues.extend(internal_check.get('issues', []))
        
        if not external_check.get('success', True):
            critical_issues.extend(external_check.get('issues', []))
        
        if not reference_check.get('success', True):
            critical_issues.extend(reference_check.get('issues', []))
        
        # 生成摘要信息
        package_report = self.detailed_check_report.get('package_analysis', {})
        total_files = package_report.get('files', {}).get('total_count', 0)
        asset_files = len(package_report.get('files', {}).get('asset_files', []))
        
        result['summary'] = {
            'total_files': total_files,
            'asset_files': asset_files,
            'critical_issues': len(critical_issues),
            'warnings': len(internal_check.get('warnings', []) + 
                          external_check.get('warnings', []) + 
                          reference_check.get('warnings', []) + 
                          dependency_chain_check.get('warnings', [])),
            'max_dependency_depth': dependency_chain_check.get('details', {}).get('max_dependency_depth', 0)
        }
        
        # 生成消息
        if critical_issues:
            result['success'] = False
            result['message'] = f"检查失败：发现 {len(critical_issues)} 个严重问题"
            result['details']['critical_issues'] = critical_issues
        else:
            result['message'] = f"检查通过：共检查 {asset_files} 个资源文件，无严重问题"
        
        return result


class GitGuidCacheManager:
    """Git仓库GUID缓存管理器 - 用于优化GUID扫描性能"""
    
    def __init__(self, git_path: str):
        self.git_path = git_path
        self.cache_available = False
        self.cache_file = None
        self.cache_data = None
        self.analyzer = ResourceDependencyAnalyzer()
        
        # 尝试获取Git缓存路径
        try:
            self.cache_file = self._get_git_cache_path()
            self.cache_available = True
            print(f"✅ [CACHE] GUID缓存可用: {self.cache_file}")
        except Exception as e:
            print(f"⚠️ [CACHE] GUID缓存不可用: {e}")
            print("📝 [CACHE] 将使用实时扫描模式（性能较慢但功能完整）")
    
    def _get_git_cache_path(self) -> str:
        """使用Git命令获取缓存文件路径"""
        try:
            # 使用Git命令获取真实的.git目录
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'], 
                cwd=self.git_path,
                capture_output=True,
                text=True,
                timeout=5
            , creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                git_dir = result.stdout.strip()
                
                # 处理相对路径
                if not os.path.isabs(git_dir):
                    git_dir = os.path.join(self.git_path, git_dir)
                
                # 确保目录存在且可写
                git_dir = os.path.abspath(git_dir)
                if not os.path.exists(git_dir):
                    raise Exception(f"Git目录不存在: {git_dir}")
                
                if not os.access(git_dir, os.W_OK):
                    raise Exception(f"Git目录不可写: {git_dir}")
                
                cache_file = os.path.join(git_dir, 'guid_cache.json')
                return cache_file
            else:
                raise Exception(f"Git命令失败: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Git命令超时")
        except Exception as e:
            raise Exception(f"无法获取Git目录: {e}")
    
    def _get_current_commit_hash(self) -> str:
        """获取当前commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'], 
                cwd=self.git_path, 
                capture_output=True, 
                text=True, 
                check=True
            , creationflags=SUBPROCESS_FLAGS)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
    
    def _load_cache(self) -> Dict[str, Any]:
        """加载缓存数据"""
        if self.cache_data is not None:
            return self.cache_data
            
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                return self.cache_data
        except Exception as e:
            print(f"加载GUID缓存失败: {e}")
        
        # 返回空缓存结构
        self.cache_data = {
            "version": "1.0",
            "last_scan_time": "",
            "last_commit_hash": "",
            "total_guids": 0,
            "guid_mapping": {}
        }
        return self.cache_data
    
    def _save_cache(self, cache_data: Dict[str, Any]) -> bool:
        """保存缓存数据"""
        try:
            # 确保.git目录存在
            git_dir = os.path.dirname(self.cache_file)
            if not os.path.exists(git_dir):
                os.makedirs(git_dir, exist_ok=True)
                
            # 保存缓存
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.cache_data = cache_data
            return True
        except Exception as e:
            print(f"保存GUID缓存失败: {e}")
            return False
    
    def _get_changed_meta_files(self, last_commit_hash: str) -> Tuple[List[str], List[str]]:
        """获取变更的meta文件列表
        
        Returns:
            Tuple[List[str], List[str]]: (added_or_modified_files, deleted_files)
        """
        try:
            if not last_commit_hash:
                # 如果没有上次的hash，需要全量扫描
                return [], []
            
            # 获取变更的文件列表
            result = subprocess.run(
                ['git', 'diff', '--name-status', last_commit_hash, 'HEAD'],
                cwd=self.git_path,
                capture_output=True,
                text=True,
                check=True
            , creationflags=SUBPROCESS_FLAGS)
            
            added_modified = []
            deleted = []
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                    
                status = parts[0]
                file_path = parts[1]
                
                if file_path.endswith('.meta'):
                    if status == 'D':  # Deleted
                        deleted.append(file_path)
                    else:  # Added, Modified, etc.
                        added_modified.append(file_path)
            
            return added_modified, deleted
            
        except subprocess.CalledProcessError as e:
            print(f"获取Git变更文件失败: {e}")
            return [], []
    
    def _scan_all_meta_files(self, progress_callback=None) -> List[str]:
        """使用Git命令获取所有meta文件"""
        try:
            if progress_callback:
                progress_callback(f"🔍 [DEBUG] 开始扫描meta文件，Git路径: {self.git_path}")
            
            result = subprocess.run(
                ['git', 'ls-files', '*.meta'],
                cwd=self.git_path,
                capture_output=True,
                text=True,
                check=True
            , creationflags=SUBPROCESS_FLAGS)
            
            all_git_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            # 过滤掉不存在的文件
            files = []
            skipped_count = 0
            for file_path in all_git_files:
                full_path = os.path.join(self.git_path, file_path)
                if os.path.exists(full_path):
                    files.append(file_path)
                else:
                    skipped_count += 1
            
            if progress_callback:
                progress_callback(f"🔍 [DEBUG] Git索引中找到 {len(all_git_files)} 个meta文件，实际存在 {len(files)} 个")
                if skipped_count > 0:
                    progress_callback(f"🔍 [DEBUG] 跳过 {skipped_count} 个Git索引中但文件系统中不存在的meta文件")
            
            # 显示前5个文件样本
            if files:
                if progress_callback:
                    progress_callback(f"🔍 [DEBUG] 前5个meta文件样本:")
                    for i, file in enumerate(files[:5]):
                        progress_callback(f"   {i+1}. {file}")
            else:
                if progress_callback:
                    progress_callback(f"⚠️ [DEBUG] Git命令没有找到任何meta文件!")
                    progress_callback(f"🔍 [DEBUG] 尝试其他Git命令进行诊断...")
                
                # 检查所有文件
                all_files_result = subprocess.run(
                    ['git', 'ls-files'],
                    cwd=self.git_path,
                    capture_output=True,
                    text=True
                , creationflags=SUBPROCESS_FLAGS)
                if all_files_result.returncode == 0:
                    all_files = [f.strip() for f in all_files_result.stdout.split('\n') if f.strip()]
                    meta_files_count = sum(1 for f in all_files if f.endswith('.meta'))
                    if progress_callback:
                        progress_callback(f"🔍 [DEBUG] Git ls-files总文件数: {len(all_files)}, 其中meta文件: {meta_files_count}")
                    
                    if meta_files_count > 0:
                        if progress_callback:
                            progress_callback(f"🔍 [DEBUG] 找到的meta文件样本:")
                            meta_samples = [f for f in all_files if f.endswith('.meta')][:5]
                            for i, file in enumerate(meta_samples):
                                progress_callback(f"   {i+1}. {file}")
                        # 过滤并返回存在的meta文件
                        meta_files = [f for f in all_files if f.endswith('.meta')]
                        existing_meta_files = []
                        for file_path in meta_files:
                            full_path = os.path.join(self.git_path, file_path)
                            if os.path.exists(full_path):
                                existing_meta_files.append(file_path)
                        
                        if progress_callback and len(existing_meta_files) != len(meta_files):
                            skipped = len(meta_files) - len(existing_meta_files)
                            progress_callback(f"🔍 [DEBUG] 从备用扫描中跳过 {skipped} 个不存在的meta文件")
                        
                        return existing_meta_files
            
            return files
            
        except subprocess.CalledProcessError as e:
            print(f"❌ [DEBUG] Git命令失败: {e}")
            print(f"❌ [DEBUG] 错误输出: {e.stderr}")
            # 如果git命令失败，回退到文件系统扫描
            print("🔄 [DEBUG] Git命令失败，回退到文件系统扫描")
            return self._fallback_scan_meta_files()
        except Exception as e:
            print(f"❌ [DEBUG] 扫描meta文件异常: {e}")
            return self._fallback_scan_meta_files()
    
    def _fallback_scan_meta_files(self) -> List[str]:
        """回退的文件系统扫描方法"""
        print(f"🔍 [DEBUG] 开始文件系统扫描: {self.git_path}")
        
        meta_files = []
        directories_scanned = 0
        
        for root, dirs, files in os.walk(self.git_path):
            # 跳过.git目录
            if '.git' in dirs:
                dirs.remove('.git')
            
            directories_scanned += 1
            if directories_scanned % 1000 == 0:
                print(f"🔍 [DEBUG] 已扫描 {directories_scanned} 个目录...")
                
            for file in files:
                if file.endswith('.meta'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.git_path)
                    meta_files.append(rel_path.replace('\\', '/'))
        
        print(f"🔍 [DEBUG] 文件系统扫描完成: 扫描了 {directories_scanned} 个目录，找到 {len(meta_files)} 个meta文件")
        
        if meta_files:
            print(f"🔍 [DEBUG] 文件系统扫描找到的前5个meta文件:")
            for i, file in enumerate(meta_files[:5]):
                print(f"   {i+1}. {file}")
        
        return meta_files
    
    def _process_meta_files(self, meta_files: List[str], progress_callback=None) -> Dict[str, Dict[str, str]]:
        """处理meta文件列表，提取GUID信息"""
        if progress_callback:
            progress_callback(f"🔍 [DEBUG] 开始处理 {len(meta_files)} 个meta文件")
            # 显示前几个文件样本
            progress_callback(f"🔍 [DEBUG] 前5个待处理文件:")
            for i, file in enumerate(meta_files[:5]):
                progress_callback(f"   {i+1}. {file}")
        
        guid_mapping = {}
        total_files = len(meta_files)
        parse_success = 0
        parse_failed = 0
        file_not_found = 0
        
        # 记录样本
        not_found_samples = []
        parse_failed_samples = []
        
        for i, rel_meta_path in enumerate(meta_files):
            if progress_callback and i % 100 == 0:
                progress = int((i / total_files) * 100)
                progress_callback(f"处理meta文件: {i}/{total_files} ({progress}%)")
            
            meta_path = os.path.join(self.git_path, rel_meta_path)
            
            # 检查文件是否存在
            if not os.path.exists(meta_path):
                file_not_found += 1
                if len(not_found_samples) < 5:  # 记录前5个不存在的文件
                    not_found_samples.append(rel_meta_path)
                if file_not_found <= 3 and progress_callback:  # 只显示前3个不存在的文件
                    progress_callback(f"⚠️ [DEBUG] 文件不存在: {meta_path}")
                continue
                
            try:
                guid = self.analyzer.parse_meta_file(meta_path)
                
                if guid and len(guid) == 32:
                    parse_success += 1
                    
                    # 记录前几个成功解析的GUID
                    if parse_success <= 5 and progress_callback:
                        progress_callback(f"✅ [DEBUG] 成功解析GUID: {guid} <- {rel_meta_path}")
                    
                    # 计算资源文件路径
                    if rel_meta_path.endswith('.meta'):
                        rel_resource_path = rel_meta_path[:-5]
                    else:
                        rel_resource_path = rel_meta_path
                    
                    # 标准化路径
                    rel_resource_path = rel_resource_path.replace('\\', '/')
                    rel_meta_path = rel_meta_path.replace('\\', '/')
                    
                    # 🚨 关键修复：检查对应的资源文件是否存在
                    resource_path = os.path.join(self.git_path, rel_resource_path)
                    if os.path.exists(resource_path):
                        guid_mapping[guid] = {
                            'meta_path': meta_path,
                            'relative_meta_path': rel_meta_path,
                            'relative_resource_path': rel_resource_path,
                            'resource_name': os.path.basename(rel_resource_path)
                        }
                    else:
                        if progress_callback and parse_success <= 10:  # 只显示前10个孤儿文件
                            progress_callback(f"⚠️ [GUID] 发现孤儿meta文件: {rel_meta_path}")
                            progress_callback(f"   对应资源文件不存在: {rel_resource_path}")
                            progress_callback(f"   跳过GUID: {guid}")
                        # 🚨 增强调试：记录被跳过的孤儿GUID
                        if not hasattr(self, '_orphan_guids_cache'):
                            self._orphan_guids_cache = set()
                        self._orphan_guids_cache.add(guid)
                        # 不添加到guid_mapping中
                else:
                    parse_failed += 1
                    if len(parse_failed_samples) < 5:  # 记录前5个解析失败的文件
                        parse_failed_samples.append((rel_meta_path, guid))
                    if parse_failed <= 3 and progress_callback:  # 只显示前3个解析失败的文件
                        progress_callback(f"❌ [DEBUG] GUID解析失败: {rel_meta_path} -> '{guid}'")
                        
                        # 使用调试版本分析前几个失败的文件
                        if parse_failed <= 2:
                            progress_callback(f"🔍 [DEBUG] 详细分析第{parse_failed}个失败文件:")
                            debug_guid = self.analyzer.parse_meta_file_debug(meta_path, show_content=(parse_failed == 1))
                            if progress_callback and parse_failed == 1:
                                progress_callback(f"📄 [DEBUG] 如需查看详细内容，请检查控制台输出")
                    
            except Exception as e:
                parse_failed += 1
                if len(parse_failed_samples) < 5:  # 记录前5个异常文件
                    parse_failed_samples.append((rel_meta_path, f"异常: {e}"))
                if parse_failed <= 3 and progress_callback:  # 只显示前3个异常
                    progress_callback(f"❌ [DEBUG] 解析meta文件异常: {rel_meta_path} - {e}")
                if progress_callback:
                    progress_callback(f"解析meta文件失败: {rel_meta_path} - {e}")
        
        if progress_callback:
            progress_callback(f"🔍 [DEBUG] 处理完成统计:")
            progress_callback(f"   📄 总文件数: {total_files}")
            progress_callback(f"   ✅ 解析成功: {parse_success}")
            progress_callback(f"   ❌ 解析失败: {parse_failed}")
            progress_callback(f"   🚫 文件不存在: {file_not_found}")
            progress_callback(f"   🔑 提取GUID数: {len(guid_mapping)}")
            
            # 显示文件不存在的样本 - 已禁用此检测
            # if not_found_samples:
            #     progress_callback(f"🚫 [DEBUG] 文件不存在样本:")
            #     for i, sample in enumerate(not_found_samples):
            #         full_path = os.path.join(self.git_path, sample)
            #         progress_callback(f"   {i+1}. {sample}")
            #         progress_callback(f"      完整路径: {full_path}")
            #         progress_callback(f"      父目录存在: {os.path.exists(os.path.dirname(full_path))}")
            
            # 显示解析失败的样本
            if parse_failed_samples:
                progress_callback(f"❌ [DEBUG] 解析失败样本:")
                for i, (sample_path, reason) in enumerate(parse_failed_samples):
                    progress_callback(f"   {i+1}. {sample_path} -> {reason}")
                    
                    # 对第一个失败文件进行深度分析
                    if i == 0:
                        progress_callback(f"🔍 [DEBUG] 第一个失败文件深度分析:")
                        full_path = os.path.join(self.git_path, sample_path)
                        if os.path.exists(full_path):
                            try:
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    progress_callback(f"   文件大小: {len(content)} 字符")
                                    progress_callback(f"   前200字符: {repr(content[:200])}")
                                    # 查找包含guid的行
                                    lines = content.split('\n')
                                    guid_lines = [line.strip() for line in lines if 'guid' in line.lower()]
                                    if guid_lines:
                                        progress_callback(f"   包含'guid'的行数: {len(guid_lines)}")
                                        progress_callback(f"   第一行: {repr(guid_lines[0])}")
                                    else:
                                        progress_callback(f"   未找到包含'guid'的行")
                            except Exception as e:
                                progress_callback(f"   读取文件异常: {e}")
        
        return guid_mapping
    
    def get_git_repository_guids(self, progress_callback=None) -> Dict[str, Dict[str, str]]:
        """获取Git仓库GUID映射，支持缓存和增量更新"""
        
        if progress_callback:
            progress_callback("🔍 检查GUID缓存状态...")
            progress_callback(f"🔍 [DEBUG] Git路径: {self.git_path}")
            progress_callback(f"🔍 [DEBUG] Git路径存在: {os.path.exists(self.git_path)}")
            progress_callback(f"🔍 [DEBUG] 是否为目录: {os.path.isdir(self.git_path)}")
        
        # 获取当前commit hash
        current_hash = self._get_current_commit_hash()
        if progress_callback:
            progress_callback(f"🔍 [DEBUG] 当前commit hash: {current_hash}")
        
        if not current_hash:
            if progress_callback:
                progress_callback(f"❌ [DEBUG] 无法获取Git commit hash")
                progress_callback("❌ 无法获取Git commit hash，可能不是Git仓库")
            return {}
        
        # 加载缓存
        cache_data = self._load_cache()
        last_hash = cache_data.get("last_commit_hash", "")
        cached_guids = cache_data.get("guid_mapping", {})
        
        if progress_callback:
            progress_callback(f"🔍 [DEBUG] 缓存状态检查:")
            progress_callback(f"   🏷️ 缓存中的commit hash: {last_hash}")
            progress_callback(f"   🔑 缓存中的GUID数量: {len(cached_guids)}")
            progress_callback(f"   ✅ Hash匹配: {current_hash == last_hash}")
            progress_callback(f"   ✅ 缓存有数据: {bool(cached_guids)}")
        
        # 检查缓存是否有效
        if current_hash == last_hash and cache_data.get("guid_mapping"):
            if progress_callback:
                progress_callback(f"✅ [DEBUG] 缓存命中！使用缓存数据")
                total_guids = cache_data.get("total_guids", 0)
                progress_callback(f"✅ 使用GUID缓存，共 {total_guids} 个GUID")
            return cache_data["guid_mapping"]
        else:
            if progress_callback:
                progress_callback(f"⚠️ [DEBUG] 缓存未命中，需要重新扫描")
        
        # 缓存无效，需要更新
        if progress_callback:
            if last_hash:
                progress_callback(f"🔄 检测到Git变更，开始增量更新...")
            else:
                progress_callback(f"🆕 首次扫描，建立GUID缓存...")
        
        # 获取变更的文件
        if last_hash:
            added_modified, deleted = self._get_changed_meta_files(last_hash)
            if progress_callback:
                progress_callback(f"📊 变更统计: 新增/修改 {len(added_modified)} 个，删除 {len(deleted)} 个meta文件")
        else:
            added_modified, deleted = [], []
        
        # 决定是增量更新还是全量扫描
        if last_hash and cache_data.get("guid_mapping"):
            # 增量更新
            guid_mapping = dict(cache_data["guid_mapping"])
            
            # 处理删除的文件
            for deleted_file in deleted:
                if progress_callback:
                    progress_callback(f"🗑️ 移除已删除文件: {deleted_file}")
                
                # 找到并移除对应的GUID
                to_remove = []
                for guid, info in guid_mapping.items():
                    if info.get('relative_meta_path') == deleted_file:
                        to_remove.append(guid)
                
                for guid in to_remove:
                    del guid_mapping[guid]
            
            # 处理新增/修改的文件
            if added_modified:
                if progress_callback:
                    progress_callback(f"🔄 处理变更的meta文件...")
                
                new_mappings = self._process_meta_files(added_modified, progress_callback)
                
                # 移除旧的GUID映射（如果文件被修改）
                for file_path in added_modified:
                    to_remove = []
                    for guid, info in guid_mapping.items():
                        if info.get('relative_meta_path') == file_path:
                            to_remove.append(guid)
                    
                    for guid in to_remove:
                        del guid_mapping[guid]
                
                # 添加新的映射
                guid_mapping.update(new_mappings)
        else:
            # 全量扫描
            if progress_callback:
                progress_callback("📁 开始全量扫描Git仓库...")
            
            all_meta_files = self._scan_all_meta_files(progress_callback)
            if progress_callback:
                progress_callback(f"📄 找到 {len(all_meta_files)} 个meta文件")
            
            guid_mapping = self._process_meta_files(all_meta_files, progress_callback)
        
        # 更新缓存
        new_cache_data = {
            "version": "1.0",
            "last_scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_commit_hash": current_hash,
            "total_guids": len(guid_mapping),
            "guid_mapping": guid_mapping
        }
        
        if self._save_cache(new_cache_data):
            if progress_callback:
                progress_callback(f"💾 GUID缓存已更新，共 {len(guid_mapping)} 个GUID")
        else:
            if progress_callback:
                progress_callback("⚠️ GUID缓存保存失败")
        
        return guid_mapping
    
    def clear_cache(self) -> bool:
        """清除缓存"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            self.cache_data = None
            print(f"✅ [CACHE] GUID缓存已清除")
            return True
        except Exception as e:
            print(f"❌ [CACHE] 清除GUID缓存失败: {e}")
            return False
    
    def clear_guid_cache_for_git_path(self, git_path: str) -> bool:
        """为指定Git路径清除GUID缓存"""
        try:
            if not git_path:
                return False
            
            # 创建临时缓存管理器来清除缓存
            temp_cache_manager = GitGuidCacheManager(git_path)
            success = temp_cache_manager.clear_cache()
            
            if success:
                print(f"✅ [CACHE] 已清除Git路径的GUID缓存: {git_path}")
            else:
                print(f"⚠️ [CACHE] 清除Git路径的GUID缓存失败: {git_path}")
            
            return success
        except Exception as e:
            print(f"❌ [CACHE] 清除Git路径GUID缓存异常: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        cache_data = self._load_cache()
        return {
            "cache_exists": os.path.exists(self.cache_file),
            "last_scan_time": cache_data.get("last_scan_time", ""),
            "last_commit_hash": cache_data.get("last_commit_hash", "")[:8] + "..." if cache_data.get("last_commit_hash") else "",
            "total_guids": cache_data.get("total_guids", 0),
            "cache_file_size": os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
        }


class GitSvnManager:
    """Git和SVN仓库管理器"""
    
    def __init__(self):
        self.git_path = ""
        self.svn_path = ""
        self.current_branch = ""
        
        # 分支缓存系统
        self.branch_cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        self._branch_cache = []
        self._cache_timestamp = 0
        self._cache_timeout = 300  # 5分钟缓存有效期
        
        # 🎯 路径映射配置系统
        self.path_mapping_enabled = True  # ✅ 启用路径映射，提供清晰的资源组织结构
        self.path_mapping_rules = self._load_default_mapping_rules()
        self._load_path_mapping_config()
        
        # 🔧 CRLF自动修复器
        self.crlf_fixer = None
        self._init_crlf_fixer()
    
    def _load_default_mapping_rules(self) -> dict:
        """
        加载内置路径映射规则 - 专为CommonResource目录设计
        
        路径映射说明:
        1. CommonResource是Unity项目的资源子仓库
        2. 所有美术资源都会上传到CommonResource/Assets/Resources/目录下
        3. 不同类型的资源会按类型分类存放，便于管理和加载
        
        最终路径结构示例:
        - 实体资源: CommonResource/Assets/Resources/minigame/entity/100060/...
        - 远程实体: CommonResource/Assets/Resources/minigame/remotes/entity/140492/...
        - UI资源: CommonResource/Assets/Resources/minigame/ui/...
        - 音频资源: CommonResource/Assets/Resources/minigame/sounds/... 
        - 特效资源: CommonResource/Assets/Resources/minigame/prefab/...
        - 其他资源: CommonResource/Assets/Resources/minigame/...
        """
        return {
            # 🎯 按优先级排序的路径映射规则（数字越小优先级越高）
            
            "remotes_entity_mapping": {
                "name": "🌐 远程实体资源映射",
                "description": "远程实体资源 Assets/remotes/entity/140492/ → Assets/Resources/minigame/remotes/entity/140492/",
                "example": "Assets/remotes/entity/140492/Model/body.prefab → Assets/Resources/minigame/remotes/entity/140492/Model/body.prefab",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]remotes[\\\/]entity($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/remotes/entity/",
                "priority": 1,  # 🔥 最高优先级
                "category": "实体资源"
            },
            
            "entity_to_minigame": {
                "name": "👤 本地实体资源映射",
                "description": "本地实体资源 Assets/entity/100060/ → Assets/Resources/minigame/entity/100060/",
                "example": "Assets/entity/100060/Model/body.prefab → Assets/Resources/minigame/entity/100060/Model/body.prefab",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]entity[\\\/]",
                "target_pattern": "Assets/Resources/minigame/entity/",
                "priority": 2,  # 🔥 第二优先级
                "category": "实体资源"
            },
            
            "ui_mapping": {
                "name": "🖼️ UI界面资源映射",
                "description": "UI界面资源 Assets/ui/ → Assets/Resources/minigame/ui/",
                "example": "Assets/ui/MainMenu/background.png → Assets/Resources/minigame/ui/MainMenu/background.png",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]ui($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/ui/",
                "priority": 3,
                "category": "界面资源"
            },
            
            "audio_mapping": {
                "name": "🎵 音频资源映射",
                "description": "音频资源 Assets/audio/ → Assets/Resources/minigame/sounds/",
                "example": "Assets/audio/bgm/main_theme.ogg → Assets/Resources/minigame/sounds/bgm/main_theme.ogg",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]audio($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/sounds/",
                "priority": 4,
                "category": "音频资源"
            },
            
            "texture_mapping": {
                "name": "🖌️ 贴图资源映射",
                "description": "贴图资源 Assets/texture/ → Assets/Resources/minigame/textures/",
                "example": "Assets/texture/characters/hero.png → Assets/Resources/minigame/textures/characters/hero.png",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]texture($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/textures/",
                "priority": 5,
                "category": "贴图资源"
            },
            
            "effects_mapping": {
                "name": "✨ 特效资源映射",
                "description": "特效资源 Assets/effects/ → Assets/Resources/minigame/prefab/effects/",
                "example": "Assets/effects/explosion.prefab → Assets/Resources/minigame/prefab/effects/explosion.prefab",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]effects($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/prefab/effects/",
                "priority": 6,
                "category": "特效资源"
            },
            
            "prefab_mapping": {
                "name": "🧩 Prefab预制体映射",
                "description": "Prefab预制体 Assets/prefab/ → Assets/Resources/minigame/prefab/",
                "example": "Assets/prefab/weapons/sword.prefab → Assets/Resources/minigame/prefab/weapons/sword.prefab",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]prefab($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/prefab/",
                "priority": 7,
                "category": "游戏预制体"
            },
            
            "assets_to_minigame": {
                "name": "📦 通用资源映射",
                "description": "其他未分类资源 Assets/其他/ → Assets/Resources/minigame/其他/",
                "example": "Assets/materials/wood.mat → Assets/Resources/minigame/materials/wood.mat",
                "enabled": True,
                "source_pattern": r"^Assets[\\/](?!Resources[\\/])(?!remotes[\\/]entity[\\/])(?!entity[\\/])(?!ui[\\/])(?!audio[\\/])(?!texture[\\/])(?!effects[\\/])(?!prefab[\\/])",
                "target_pattern": "Assets/Resources/minigame/",
                "priority": 998,  # 🔥 倒数第二优先级，作为兜底规则
                "category": "通用资源"
            },
            
            "direct_assets_mapping": {
                "name": "📁 直接Assets映射（备用）",
                "description": "直接使用原始Assets路径，不进行映射转换",
                "example": "Assets/special/file.txt → Assets/special/file.txt",
                "enabled": False,  # 🔥 默认禁用，特殊情况下可启用
                "source_pattern": r"^Assets[\\\/]",
                "target_pattern": "Assets/",
                "priority": 999,  # 🔥 最低优先级
                "category": "特殊用途"
            }
        }
    
    def _load_path_mapping_config(self):
        """加载内置路径映射配置"""
        try:
            # 直接使用内置规则，不再依赖外部JSON文件
            self.path_mapping_enabled = True
            self.path_mapping_rules = self._load_default_mapping_rules()
            
            print(f"📋 [CONFIG] 使用内置路径映射配置: {len(self.path_mapping_rules)} 条规则")
            
            # 显示启用的规则
            enabled_rules = [rule for rule in self.path_mapping_rules.values() if rule.get('enabled', True)]
            print(f"📋 [CONFIG] 启用的规则: {len(enabled_rules)} 条")
            for rule in enabled_rules:
                print(f"   - {rule['name']}: {rule['source_pattern']} -> {rule['target_pattern']}")
                
        except Exception as e:
            print(f"❌ [CONFIG] 加载内置路径映射配置失败: {e}")
            print(f"📋 [CONFIG] 使用默认配置")
            self.path_mapping_rules = self._load_default_mapping_rules()
    
    def _save_path_mapping_config(self):
        """保存路径映射配置（已弃用，现在使用内置配置）"""
        print(f"📋 [CONFIG] 路径映射配置已内置，无需外部文件")
        print(f"📋 [CONFIG] 当前启用的规则: {len([r for r in self.path_mapping_rules.values() if r.get('enabled', True)])} 条")
    
    def apply_path_mapping(self, assets_path: str) -> str:
        """
        应用路径映射规则
        
        Args:
            assets_path: 原始Assets路径，如 "Assets\\entity\\100060\\..."
            
        Returns:
            str: 映射后的路径，如 "Assets\\Resources\\minigame\\entity\\100060\\..."
        """
        if not self.path_mapping_enabled:
            print(f"   ⏸️ 路径映射已禁用，使用原始路径")
            return assets_path
            
        print(f"🔄 [MAPPING] ========== 路径映射处理 ==========")
        print(f"   📥 原始路径: {assets_path}")
        
        # 按优先级排序规则（数字越小优先级越高）
        sorted_rules = sorted(
            [(rule_id, rule) for rule_id, rule in self.path_mapping_rules.items() if rule.get('enabled', True)],
            key=lambda x: x[1].get('priority', 999)
        )
        
        print(f"   🎯 规则检查顺序（按优先级）:")
        for i, (rule_id, rule) in enumerate(sorted_rules):
            print(f"      {i+1}. {rule['name']} (优先级: {rule.get('priority', 999)})")
        
        for rule_id, rule in sorted_rules:
            try:
                import re
                source_pattern = rule['source_pattern']
                target_pattern = rule['target_pattern']
                
                print(f"   🔍 测试规则: {rule['name']}")
                print(f"      📋 描述: {rule['description']}")
                print(f"      🎨 模式: {source_pattern}")
                
                # 🚨 关键修复：使用IGNORECASE标志进行匹配
                if re.match(source_pattern, assets_path, re.IGNORECASE):
                    # 应用映射规则 - 使用更精确的替换
                    match = re.match(source_pattern, assets_path, re.IGNORECASE)
                    if match:
                        # 获取匹配的部分
                        matched_part = match.group(0)
                        remaining_path = assets_path[len(matched_part):].lstrip('\\/')
                        
                        # 构建映射后的路径
                        if remaining_path:
                            mapped_path = target_pattern + remaining_path
                        else:
                            mapped_path = target_pattern.rstrip('\\/')
                        
                        print(f"      ✅ 匹配成功!")
                        print(f"      🔍 匹配部分: '{matched_part}'")
                        print(f"      📂 剩余路径: '{remaining_path}'")
                        print(f"      🎯 目标模式: '{target_pattern}'")
                        print(f"   📤 最终映射结果: {mapped_path}")
                        print(f"   ==========================================")
                        
                        return mapped_path
                    else:
                        # 兜底：使用简单替换
                        mapped_path = re.sub(source_pattern, target_pattern, assets_path, flags=re.IGNORECASE)
                        print(f"      ✅ 使用简单替换: {mapped_path}")
                        print(f"   ==========================================")
                        return mapped_path
                else:
                    print(f"      ❌ 不匹配")
                    
            except Exception as e:
                print(f"   ❌ 规则 {rule_id} 处理失败: {e}")
                continue
        
        print(f"   ⚠️ 没有匹配的映射规则，使用原始路径")
        print(f"   ==========================================")
        return assets_path
    
    def get_path_mapping_rules(self) -> dict:
        """获取当前路径映射规则"""
        return self.path_mapping_rules.copy()
    
    def update_path_mapping_rule(self, rule_id: str, rule_data: dict):
        """更新路径映射规则（运行时修改，重启后恢复默认）"""
        self.path_mapping_rules[rule_id] = rule_data
        print(f"📝 [CONFIG] 更新映射规则: {rule_id} (运行时修改)")
    
    def add_path_mapping_rule(self, rule_id: str, rule_data: dict):
        """添加新的路径映射规则（运行时添加，重启后恢复默认）"""
        self.path_mapping_rules[rule_id] = rule_data
        print(f"➕ [CONFIG] 添加映射规则: {rule_id} (运行时添加)")
    
    def remove_path_mapping_rule(self, rule_id: str):
        """删除路径映射规则（运行时删除，重启后恢复默认）"""
        if rule_id in self.path_mapping_rules:
            del self.path_mapping_rules[rule_id]
            print(f"🗑️ [CONFIG] 删除映射规则: {rule_id} (运行时删除)")
    
    def set_path_mapping_enabled(self, enabled: bool):
        """启用/禁用路径映射（运行时修改，重启后恢复默认）"""
        self.path_mapping_enabled = enabled
        print(f"🔧 [CONFIG] 路径映射: {'启用' if enabled else '禁用'} (运行时修改)")
    
    def clear_guid_cache_for_git_path(self, git_path: str) -> bool:
        """为指定Git路径清除GUID缓存"""
        try:
            if not git_path:
                return False
            
            # 创建临时缓存管理器来清除缓存
            temp_cache_manager = GitGuidCacheManager(git_path)
            success = temp_cache_manager.clear_cache()
            
            if success:
                print(f"✅ [CACHE] 已清除Git路径的GUID缓存: {git_path}")
            else:
                print(f"⚠️ [CACHE] 清除Git路径的GUID缓存失败: {git_path}")
            
            return success
        except Exception as e:
            print(f"❌ [CACHE] 清除Git路径GUID缓存异常: {e}")
            return False
    
    def test_path_mapping(self, test_path: str) -> str:
        """测试路径映射效果"""
        print(f"🧪 [TEST] ========== 路径映射测试 ==========")
        print(f"   测试路径: {test_path}")
        
        # 如果是完整路径，提取Assets相对路径
        if 'Assets' in test_path:
            assets_index = test_path.find('Assets')
            if assets_index != -1:
                # 提取从Assets开始的相对路径
                assets_relative_path = test_path[assets_index:].replace('/', '\\')
                print(f"   提取的Assets路径: {assets_relative_path}")
                
                # 对Assets相对路径进行映射测试
                mapped_result = self.apply_path_mapping(assets_relative_path)
                print(f"   映射结果: {mapped_result}")
                
                if mapped_result != assets_relative_path:
                    print(f"   ✅ 映射成功!")
                    print(f"   原始: {assets_relative_path}")
                    print(f"   映射: {mapped_result}")
                else:
                    print(f"   ❌ 映射失败，没有匹配的规则")
                
                print(f"   ==========================================")
                return mapped_result
            else:
                print(f"   ❌ 路径中未找到Assets目录")
        else:
            print(f"   ❌ 路径中未包含Assets目录")
            
        print(f"   ==========================================")
        return test_path
    
    def _init_crlf_fixer(self):
        """初始化CRLF修复器"""
        try:
            if CRLFAutoFixer and self.git_path:
                self.crlf_fixer = CRLFAutoFixer(self.git_path)
                print("🔧 [CRLF] CRLF自动修复器初始化成功")
            else:
                print("⚠️ [CRLF] CRLF自动修复器不可用或Git路径未设置")
        except Exception as e:
            print(f"❌ [CRLF] CRLF修复器初始化失败: {e}")
            self.crlf_fixer = None
    
    def set_paths(self, git_path: str, svn_path: str):
        """设置Git和SVN路径"""
        # 如果路径发生变化，清除缓存
        if self.git_path != git_path:
            self._clear_branch_cache()
            
        self.git_path = git_path
        self.svn_path = svn_path
        
        # 重新初始化CRLF修复器
        self._init_crlf_fixer()
        
        # 不自动配置Git换行符，保护团队协作环境
        print(f"   📝 Git换行符处理：手动解决模式（保护团队协作）")
    
    def _clear_branch_cache(self):
        """清除分支缓存"""
        self._branch_cache = []
        self._cache_timestamp = 0
        print("🗑️ [DEBUG] 分支缓存已清除")
    
    def get_git_branches(self, fetch_remote: bool = True, use_cache: bool = True) -> List[str]:
        """
        获取Git分支列表
        
        Args:
            fetch_remote: 是否获取远程分支信息
            use_cache: 是否使用缓存
            
        Returns:
            List[str]: 分支名称列表
        """
        if not self.git_path or not os.path.exists(self.git_path):
            return []
        
        # 检查缓存是否有效
        import time
        current_time = time.time()
        if use_cache and self._branch_cache and (current_time - self._cache_timestamp) < self._cache_timeout:
            print(f"📦 [DEBUG] 使用缓存的分支列表({len(self._branch_cache)}个分支)")
            return self._branch_cache.copy()
        
        branches = []
        
        try:
            # 检测是否为子仓库，调整超时策略
            is_submodule = self._detect_submodule()
            
            if fetch_remote:
                print(f"🌐 [DEBUG] 获取远程分支信息...")
                if is_submodule:
                    print(f"   📦 子仓库模式：使用较长超时时间")
                    fetch_timeout = 60  # 子仓库使用60秒超时
                else:
                    print(f"   📁 普通仓库模式：使用标准超时时间")
                    fetch_timeout = 30  # 普通仓库使用30秒超时
                
                # 尝试获取远程信息
                try:
                    result = subprocess.run(['git', 'fetch'], 
                                          cwd=self.git_path, 
                                          capture_output=True, 
                                          text=True,
                                          encoding='utf-8',
                                          errors='ignore',
                                          timeout=fetch_timeout, creationflags=SUBPROCESS_FLAGS)
                    
                    if result.returncode == 0:
                        print(f"   ✅ 远程信息获取成功")
                    else:
                        print(f"   ⚠️ 远程信息获取失败，但继续获取本地分支")
                        print(f"       错误信息: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    print(f"   ⏰ 远程信息获取超时({fetch_timeout}秒)，使用本地分支")
                except Exception as e:
                    print(f"   ❌ 网络操作异常: {e}")
            else:
                print(f"   📍 跳过远程信息获取，仅使用本地分支")
            
            # 获取所有分支（本地+远程）
            print(f"   📋 获取分支列表...")
            result = subprocess.run(['git', 'branch', '-a'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=15, creationflags=SUBPROCESS_FLAGS)  # 获取分支列表用较短超时
            
            if result.returncode != 0:
                print(f"   ❌ 获取分支列表失败: {result.stderr}")
                return []
            
            # 解析分支名称
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # 跳过当前分支标记
                if line.startswith('*'):
                    line = line[1:].strip()
                
                # 处理远程分支
                if line.startswith('remotes/origin/'):
                    branch_name = line.replace('remotes/origin/', '')
                    # 跳过HEAD指针
                    if branch_name != 'HEAD':
                        branches.append(branch_name)
                elif not line.startswith('remotes/'):
                    # 本地分支
                    branches.append(line)
            
            # 去重并排序
            branches = sorted(list(set(branches)))
            print(f"   ✅ 找到 {len(branches)} 个分支")
            
            # 更新缓存
            if use_cache:
                self._branch_cache = branches.copy()
                self._cache_timestamp = current_time
                print(f"   💾 分支列表已缓存")
            
            return branches
            
        except subprocess.TimeoutExpired as e:
            print(f"   ⏰ Git操作超时: {e}")
            # 超时时尝试获取本地分支
            try:
                print(f"   🔄 尝试仅获取本地分支...")
                result = subprocess.run(['git', 'branch'], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=10, creationflags=SUBPROCESS_FLAGS)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('*'):
                            branches.append(line)
                        elif line.startswith('*'):
                            branches.append(line[1:].strip())
                    
                    print(f"   ✅ 获取到 {len(branches)} 个本地分支")
                    return sorted(list(set(branches)))
                    
            except Exception as fallback_e:
                print(f"   ❌ 获取本地分支也失败: {fallback_e}")
            
            return []
            
        except Exception as e:
            print(f"   ❌ 获取分支列表异常: {e}")
            return []
    
    def get_current_branch(self) -> str:
        """获取当前Git分支 - 增强版，支持多种获取策略"""
        if not self.git_path or not os.path.exists(self.git_path):
            return ""
        
        try:
            # 策略1: 使用 git branch --show-current (标准方法)
            print("🔍 [DEBUG] 尝试获取当前分支 - 策略1: git branch --show-current")
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                current_branch = result.stdout.strip()
                self.current_branch = current_branch
                print(f"   ✅ 策略1成功: {current_branch}")
                return current_branch
            
            print(f"   ⚠️ 策略1失败: {result.stderr.strip()}")
            
            # 策略2: 使用 git rev-parse --abbrev-ref HEAD (处理分离头指针)
            print("🔍 [DEBUG] 尝试获取当前分支 - 策略2: git rev-parse --abbrev-ref HEAD")
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                current_branch = result.stdout.strip()
                # 如果是HEAD，说明在分离头指针状态
                if current_branch == "HEAD":
                    print("   ⚠️ 检测到分离头指针状态")
                    # 策略3: 尝试获取最近的提交信息
                    commit_result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                                 cwd=self.git_path, 
                                                 capture_output=True, 
                                                 text=True,
                                                 encoding='utf-8',
                                                 errors='ignore',
                                                 timeout=5, creationflags=SUBPROCESS_FLAGS)
                    if commit_result.returncode == 0:
                        commit_hash = commit_result.stdout.strip()
                        print(f"   📍 分离头指针状态，当前提交: {commit_hash}")
                        # 返回一个特殊标识，表示分离头指针状态
                        self.current_branch = f"DETACHED_HEAD_{commit_hash}"
                        return self.current_branch
                else:
                    self.current_branch = current_branch
                    print(f"   ✅ 策略2成功: {current_branch}")
                    return current_branch
            
            print(f"   ⚠️ 策略2失败: {result.stderr.strip()}")
            
            # 策略3: 使用 git status --porcelain -b 获取分支信息
            print("🔍 [DEBUG] 尝试获取当前分支 - 策略3: git status --porcelain -b")
            result = subprocess.run(['git', 'status', '--porcelain', '-b'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if lines:
                    # 第一行包含分支信息
                    first_line = lines[0]
                    if first_line.startswith('## '):
                        branch_info = first_line[3:]  # 去掉 '## '
                        # 提取分支名（去掉跟踪信息）
                        if '...' in branch_info:
                            branch_name = branch_info.split('...')[0]
                        else:
                            branch_name = branch_info
                        
                        if branch_name and branch_name != "HEAD":
                            self.current_branch = branch_name
                            print(f"   ✅ 策略3成功: {branch_name}")
                            return branch_name
            
            print(f"   ⚠️ 策略3失败")
            
            # 策略4: 检查是否有本地分支
            print("🔍 [DEBUG] 尝试获取当前分支 - 策略4: 检查本地分支")
            result = subprocess.run(['git', 'branch'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('*'):
                        # 找到当前分支
                        branch_name = line[1:].strip()
                        if branch_name:
                            self.current_branch = branch_name
                            print(f"   ✅ 策略4成功: {branch_name}")
                            return branch_name
            
            print(f"   ⚠️ 策略4失败")
            
            # 所有策略都失败，返回空字符串
            print("❌ [DEBUG] 所有获取当前分支的策略都失败了")
            return ""
            
        except subprocess.TimeoutExpired as e:
            print(f"⏰ 获取当前分支超时: {e}")
        except Exception as e:
            print(f"获取当前分支失败: {e}")
        return ""
    
    def checkout_branch(self, branch_name: str) -> bool:
        """
        切换到指定分支
        
        Args:
            branch_name: 分支名称
            
        Returns:
            bool: 是否成功切换
        """
        if not self.git_path or not os.path.exists(self.git_path):
            print(f"Git路径无效: {self.git_path}")
            return False
        
        if not branch_name:
            print("分支名称为空")
            return False
        
        try:
            print(f"🔄 [DEBUG] 切换分支: {branch_name}")
            
            # 检测是否为子仓库，调整超时策略
            is_submodule = self._detect_submodule()
            if is_submodule:
                print(f"   📦 子仓库模式：使用较长超时时间")
                checkout_timeout = 90  # 子仓库使用90秒超时
            else:
                print(f"   📁 普通仓库模式：使用标准超时时间")
                checkout_timeout = 45  # 普通仓库使用45秒超时
            
            # 首先检查分支是否存在
            print(f"   🔍 检查分支是否存在...")
            check_result = subprocess.run(['git', 'branch', '-a'], 
                                        cwd=self.git_path, 
                                        capture_output=True, 
                                        text=True,
                                        encoding='utf-8',
                                        errors='ignore',
                                        timeout=15, creationflags=SUBPROCESS_FLAGS)
            
            if check_result.returncode != 0:
                print(f"   ❌ 无法检查分支列表: {check_result.stderr}")
                return False
            
            # 检查目标分支是否存在
            branch_exists = False
            is_remote_branch = False
            
            for line in check_result.stdout.split('\n'):
                line = line.strip()
                if line.endswith(branch_name) or line == f"* {branch_name}":
                    branch_exists = True
                    break
                elif line == f"remotes/origin/{branch_name}":
                    branch_exists = True
                    is_remote_branch = True
                    break
            
            if not branch_exists:
                print(f"   ❌ 分支 '{branch_name}' 不存在")
                return False
            
            print(f"   ✅ 分支存在，准备切换...")
            
            # 如果是远程分支，需要先创建本地跟踪分支
            if is_remote_branch:
                print(f"   🌐 创建本地跟踪分支...")
                result = subprocess.run(['git', 'checkout', '-b', branch_name, f'origin/{branch_name}'], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=checkout_timeout, creationflags=SUBPROCESS_FLAGS)
            else:
                # 本地分支直接切换
                print(f"   📍 切换到本地分支...")
                result = subprocess.run(['git', 'checkout', branch_name], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=checkout_timeout, creationflags=SUBPROCESS_FLAGS)
            
            # 如果切换失败，检查是否是因为分离头指针状态
            if result.returncode != 0 and "HEAD is now at" in result.stderr:
                print(f"   ⚠️ 检测到分离头指针状态，尝试强制切换...")
                # 强制切换到分支
                force_result = subprocess.run(['git', 'checkout', '-f', branch_name], 
                                            cwd=self.git_path, 
                                            capture_output=True, 
                                            text=True,
                                            encoding='utf-8',
                                            errors='ignore',
                                            timeout=checkout_timeout, creationflags=SUBPROCESS_FLAGS)
                if force_result.returncode == 0:
                    print(f"   ✅ 强制切换成功")
                    return True
                else:
                    print(f"   ❌ 强制切换失败: {force_result.stderr}")
                    result = force_result
            
            if result.returncode == 0:
                print(f"   ✅ 成功切换到分支: {branch_name}")
                
                # 清除GUID缓存，因为分支切换后仓库内容可能发生变化
                self.clear_guid_cache_for_git_path(self.git_path)
                
                return True
            else:
                print(f"   ❌ 分支切换失败: {result.stderr}")
                
                # 如果切换失败，尝试强制切换
                if "Your local changes" in result.stderr or "would be overwritten" in result.stderr:
                    print(f"   🔧 检测到本地更改冲突，尝试强制切换...")
                    
                    # 先保存当前更改
                    stash_result = subprocess.run(['git', 'stash'], 
                                                cwd=self.git_path, 
                                                capture_output=True, 
                                                text=True,
                                                encoding='utf-8',
                                                errors='ignore',
                                                timeout=30, creationflags=SUBPROCESS_FLAGS)
                    
                    if stash_result.returncode == 0:
                        print(f"   💾 本地更改已暂存")
                        
                        # 再次尝试切换
                        retry_result = subprocess.run(['git', 'checkout', branch_name], 
                                                    cwd=self.git_path, 
                                                    capture_output=True, 
                                                    text=True,
                                                    encoding='utf-8',
                                                    errors='ignore',
                                                    timeout=checkout_timeout, creationflags=SUBPROCESS_FLAGS)
                        
                        if retry_result.returncode == 0:
                            print(f"   ✅ 强制切换成功")
                            return True
                        else:
                            print(f"   ❌ 强制切换仍然失败: {retry_result.stderr}")
                    else:
                        print(f"   ❌ 无法暂存本地更改: {stash_result.stderr}")
                
                return False
            
        except subprocess.TimeoutExpired as e:
            print(f"   ⏰ 分支切换超时({checkout_timeout}秒): {e}")
            return False
        except Exception as e:
            print(f"   ❌ 分支切换异常: {e}")
            return False
    
    def reset_git_repository(self) -> Tuple[bool, str]:
        """重置更新Git仓库 - 强制同步到远程分支最新状态"""
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        try:
            print("🔄 [RESET] ========== 开始重置更新Git仓库 ==========")
            
            # 1. 获取当前分支名
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支"
            
            # 检查是否为分离头指针状态
            if current_branch.startswith("DETACHED_HEAD_"):
                return False, f"当前处于分离头指针状态，无法重置。请先切换到具体分支。"
            
            print(f"🌿 [RESET] 当前分支: {current_branch}")
            
            # 2. 获取远程最新信息 (git fetch origin)
            print("🌐 [RESET] 步骤1/3: 获取远程最新信息...")
            result = subprocess.run(
                ['git', 'fetch', 'origin'], 
                cwd=self.git_path, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=60  # 网络操作超时设置
            , creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                print(f"❌ [RESET] fetch失败: {error_msg}")
                return False, f"获取远程信息失败: {error_msg}"
            
            print("✅ [RESET] 远程信息获取成功")
            
            # 3. 清理未跟踪的文件和目录 (git clean -f -d)
            print("🧹 [RESET] 步骤2/3: 清理未跟踪文件...")
            result = subprocess.run(
                ['git', 'clean', '-f', '-d'], 
                cwd=self.git_path, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='ignore'
            , creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                print(f"⚠️ [RESET] clean警告: {error_msg}")
                # clean命令即使有警告也继续执行
            else:
                cleaned_files = result.stdout.strip()
                if cleaned_files:
                    print(f"🗑️ [RESET] 已清理文件:\n{cleaned_files}")
                else:
                    print("✅ [RESET] 无需清理文件")
            
            # 4. 硬重置到远程分支 (git reset --hard origin/分支名)
            print("💥 [RESET] 步骤3/3: 硬重置到远程分支...")
            remote_branch = f"origin/{current_branch}"
            result = subprocess.run(
                ['git', 'reset', '--hard', remote_branch], 
                cwd=self.git_path, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='ignore'
            , creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                print(f"❌ [RESET] reset失败: {error_msg}")
                return False, f"重置到远程分支失败: {error_msg}"
            
            reset_info = result.stdout.strip()
            print(f"✅ [RESET] 重置成功: {reset_info}")
            
            # 5. 验证重置结果
            print("🔍 [RESET] 验证重置结果...")
            result = subprocess.run(
                ['git', 'status', '--porcelain'], 
                cwd=self.git_path, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='ignore'
            , creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                status_output = result.stdout.strip()
                if not status_output:
                    print("✅ [RESET] 工作区已清理干净")
                else:
                    print(f"⚠️ [RESET] 工作区仍有变化:\n{status_output}")
            
            print("🎉 [RESET] ========== 重置更新完成 ==========")
            
            # 清除GUID缓存，因为仓库内容已重置
            self.clear_guid_cache_for_git_path(self.git_path)
            
            return True, f"重置更新完成！已同步到远程分支 {current_branch} 最新状态"
            
        except subprocess.TimeoutExpired:
            error_msg = "网络超时：获取远程信息耗时过长"
            print(f"⏰ [RESET] {error_msg}")
            return False, error_msg
        except subprocess.CalledProcessError as e:
            error_msg = f"Git命令执行失败: {e}"
            print(f"❌ [RESET] {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"重置Git仓库时发生异常: {e}"
            print(f"💥 [RESET] {error_msg}")
            return False, error_msg
    
    def auto_fix_git_sync_issues(self) -> Tuple[bool, str]:
        """自动修复Git同步和认证问题"""
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        try:
            # 1. 配置Git凭据存储（如果尚未配置）
            result = subprocess.run(['git', 'config', '--get', 'credential.helper'], 
                                  cwd=self.git_path, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                # 配置凭据存储
                result = subprocess.run(['git', 'config', 'credential.helper', 'store'], 
                                      cwd=self.git_path, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    return False, f"配置Git凭据存储失败: {result.stderr}"
                print("✅ [SYNC] Git凭据存储已配置")
            
            # 2. 检查远程连接
            print("🌐 [SYNC] 测试远程连接...")
            result = subprocess.run(['git', 'ls-remote', '--heads', 'origin'], 
                                  cwd=self.git_path, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "Authentication failed" in error_msg:
                    return False, (
                        "Git认证失败，需要手动输入用户名密码。\n"
                        "请在命令行中执行以下步骤：\n"
                        f"1. cd \"{self.git_path}\"\n"
                        "2. git pull origin <分支名>\n"
                        "3. 输入用户名和密码（只需输入一次）"
                    )
                else:
                    return False, f"无法连接到远程仓库: {error_msg}"
            
            # 3. 尝试同步
            sync_success, sync_message = self.pull_current_branch()
            if not sync_success:
                return False, f"同步失败: {sync_message}"
            
            return True, "Git同步和认证问题已自动修复"
            
        except subprocess.TimeoutExpired:
            return False, "操作超时，请检查网络连接"
        except Exception as e:
            return False, f"修复过程中发生错误: {str(e)}"

    def pull_current_branch(self) -> Tuple[bool, str]:
        """拉取当前分支的最新代码 - 增强版，支持分离头指针状态"""
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        try:
            # 1. 获取当前分支名
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支"
            
            # 检查是否为分离头指针状态
            if current_branch.startswith("DETACHED_HEAD_"):
                return False, f"当前处于分离头指针状态，无法拉取。请先切换到具体分支。"
            
            # 2. 获取远程仓库信息 (git fetch)
            print("🌐 [PULL] 获取远程信息...")
            result = subprocess.run(['git', 'fetch', 'origin'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"获取远程信息失败: {error_msg}"
            
            print("✅ [PULL] 远程信息获取成功")
            
            # 3. 拉取当前分支 (git pull origin 当前分支名)
            print(f"📥 [PULL] 拉取分支: {current_branch}")
            result = subprocess.run(['git', 'pull', 'origin', current_branch], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"拉取分支失败: {error_msg}"
            
            print("✅ [PULL] 拉取成功")
            
            # 清除GUID缓存，因为仓库内容已更新
            self.clear_guid_cache_for_git_path(self.git_path)
            
            return True, f"拉取成功 - 已更新分支 {current_branch} 到最新版本"
            
        except subprocess.TimeoutExpired:
            return False, "拉取操作超时，请检查网络连接"
        except subprocess.CalledProcessError as e:
            return False, f"Git命令执行失败: {e}"
        except Exception as e:
            return False, f"拉取分支时发生异常: {e}"
    
    def get_git_files_in_directory(self, target_dir: str) -> List[str]:
        """获取Git仓库指定目录下的所有文件"""
        if not self.git_path or not os.path.exists(self.git_path):
            return []
        
        target_path = os.path.join(self.git_path, target_dir)
        if not os.path.exists(target_path):
            return []
        
        files = []
        for root, dirs, filenames in os.walk(target_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                files.append(file_path)
        
        return files
    
    def diagnose_git_repository(self) -> Dict[str, Any]:
        """诊断Git仓库状态，返回详细信息"""
        diagnosis = {
            'git_path': self.git_path,
            'path_exists': False,
            'is_git_repo': False,
            'current_branch': '',
            'branch_status': '',
            'remote_status': '',
            'working_tree_status': '',
            'issues': [],
            'recommendations': []
        }
        
        if not self.git_path:
            diagnosis['issues'].append("Git路径未设置")
            diagnosis['recommendations'].append("请先设置Git仓库路径")
            return diagnosis
        
        if not os.path.exists(self.git_path):
            diagnosis['issues'].append("Git路径不存在")
            diagnosis['recommendations'].append("请检查Git仓库路径是否正确")
            return diagnosis
        
        diagnosis['path_exists'] = True
        
        # 检查是否为Git仓库
        try:
            result = subprocess.run(['git', 'rev-parse', '--git-dir'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                diagnosis['is_git_repo'] = True
            else:
                diagnosis['issues'].append("不是有效的Git仓库")
                diagnosis['recommendations'].append("请选择正确的Git仓库目录")
                return diagnosis
        except Exception as e:
            diagnosis['issues'].append(f"检查Git仓库时出错: {e}")
            return diagnosis
        
        # 获取当前分支状态
        current_branch = self.get_current_branch()
        diagnosis['current_branch'] = current_branch
        
        if not current_branch:
            diagnosis['issues'].append("无法获取当前分支")
            diagnosis['recommendations'].append("Git仓库可能处于异常状态")
        elif current_branch.startswith("DETACHED_HEAD_"):
            diagnosis['branch_status'] = "分离头指针状态"
            diagnosis['issues'].append("当前处于分离头指针状态")
            diagnosis['recommendations'].append("请切换到具体分支")
        else:
            diagnosis['branch_status'] = "正常分支状态"
        
        # 检查远程仓库状态
        try:
            result = subprocess.run(['git', 'remote', '-v'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0 and result.stdout.strip():
                diagnosis['remote_status'] = "已配置远程仓库"
            else:
                diagnosis['remote_status'] = "未配置远程仓库"
                diagnosis['issues'].append("未配置远程仓库")
                diagnosis['recommendations'].append("请配置远程仓库")
        except Exception as e:
            diagnosis['remote_status'] = f"检查远程仓库时出错: {e}"
        
        # 检查工作区状态
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                if result.stdout.strip():
                    diagnosis['working_tree_status'] = "有未提交的更改"
                    diagnosis['issues'].append("工作区有未提交的更改")
                    diagnosis['recommendations'].append("请提交或暂存更改")
                else:
                    diagnosis['working_tree_status'] = "工作区干净"
            else:
                diagnosis['working_tree_status'] = "无法检查工作区状态"
        except Exception as e:
            diagnosis['working_tree_status'] = f"检查工作区时出错: {e}"
        
        return diagnosis

    def _is_crlf_error(self, error_message: str) -> bool:
        """检测是否为CRLF相关错误"""
        crlf_indicators = [
            "LF would be replaced by CRLF",
            "CRLF would be replaced by LF",
            "in the working copy",
            "line endings",
            "warning: in the working copy of"
        ]
        return any(indicator in error_message for indicator in crlf_indicators)
    
    def _validate_upload_path(self) -> bool:
        """
        验证上传路径是否安全
        确保只能上传到CommonResource目录，防止误上传到其他仓库路径
        
        Returns:
            bool: True表示路径安全，False表示路径不安全
        """
        try:
            if not self.git_path:
                print("❌ [PATH_VALIDATION] Git路径为空")
                return False
            
            # 标准化路径
            normalized_git_path = os.path.normpath(self.git_path).replace('\\', '/')
            
            print(f"🔍 [PATH_VALIDATION] 开始验证上传路径...")
            print(f"   原始Git路径: {self.git_path}")
            print(f"   标准化路径: {normalized_git_path}")
            
            # 检查是否包含CommonResource
            if 'CommonResource' not in normalized_git_path:
                print(f"❌ [PATH_VALIDATION] 路径不包含CommonResource目录")
                print(f"   当前路径: {normalized_git_path}")
                print(f"   要求: 路径必须包含CommonResource目录")
                return False
            
            # 检查是否以CommonResource结尾（推荐配置）
            if normalized_git_path.endswith('CommonResource'):
                print(f"✅ [PATH_VALIDATION] 路径配置正确，直接指向CommonResource目录")
                return True
            
            # 检查是否在CommonResource目录下（也允许）
            if '/CommonResource/' in normalized_git_path:
                print(f"✅ [PATH_VALIDATION] 路径在CommonResource目录下，允许上传")
                print(f"   CommonResource位置: {normalized_git_path.find('/CommonResource/')}")
                return True
            
            # 禁止的路径模式
            forbidden_patterns = [
                'assetruntimenew/Assets',  # 防止上传到主仓库的Assets目录
                'assetruntimenew/Packages',  # 防止上传到Packages目录
                'assetruntimenew/ProjectSettings',  # 防止上传到ProjectSettings
                '/Assets/',  # 防止直接上传到任何Assets目录（除非在CommonResource下）
                '/Packages/',  # 防止上传到Packages目录
                '/ProjectSettings/'  # 防止上传到ProjectSettings目录
            ]
            
            for pattern in forbidden_patterns:
                if pattern in normalized_git_path and 'CommonResource' not in normalized_git_path:
                    print(f"❌ [PATH_VALIDATION] 检测到禁止的路径模式: {pattern}")
                    print(f"   当前路径: {normalized_git_path}")
                    print(f"   说明: 此路径可能导致资源上传到错误的仓库位置")
                    return False
            
            print(f"✅ [PATH_VALIDATION] 路径验证通过")
            return True
            
        except Exception as e:
            print(f"❌ [PATH_VALIDATION] 路径验证过程中发生错误: {e}")
            return False
    
    def _auto_fix_crlf_issue(self, error_message: str) -> tuple:
        """自动修复CRLF问题
        
        Returns:
            tuple: (是否修复成功, 详细信息)
        """
        try:
            if not self.crlf_fixer:
                return False, "CRLF修复器未初始化"
            
            print("🔧 [CRLF] 尝试自动修复CRLF问题...")
            
            # 使用CRLF修复器进行智能修复
            success, message = self.crlf_fixer.auto_fix_crlf_issue(error_message)
            result = {'success': success, 'message': message}
            
            if result['success']:
                print(f"✅ [CRLF] 自动修复成功: {result['message']}")
                return True, result['message']
            else:
                print(f"❌ [CRLF] 自动修复失败: {result['message']}")
                return False, result['message']
                
        except Exception as e:
            error_info = f"CRLF自动修复异常: {str(e)}"
            print(f"❌ [CRLF] {error_info}")
            return False, error_info
    
    def push_files_to_git(self, source_files: List[str], target_directory: str = "CommonResource", folder_upload_modes: dict = None) -> Tuple[bool, str]:
        """
        将文件推送到Git仓库
        
        Args:
            source_files: 源文件路径列表
            target_directory: 目标目录（相对于Git仓库根目录）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        # 🔍 详细调试输出：函数参数
        print(f"📋 [FUNC_DEBUG] ========== push_files_to_git 函数调用 ==========")
        print(f"   函数: GitSvnManager.push_files_to_git()")
        print(f"   参数 - source_files: {len(source_files)} 个文件")
        for i, file_path in enumerate(source_files):
            print(f"     {i+1}. {file_path}")
        print(f"   参数 - target_directory: '{target_directory}'")
        print(f"   当前Git路径: {self.git_path}")
        print(f"   当前SVN路径: {self.svn_path}")
        print(f"   Git路径是否存在: {os.path.exists(self.git_path) if self.git_path else False}")
        print(f"   ====================================================")
        
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        # 🛡️ 路径安全验证：确保只能上传到CommonResource目录
        if not self._validate_upload_path():
            return False, "❌ 路径验证失败：只能上传到CommonResource目录，请检查Git路径配置"
        
        if not source_files:
            return False, "没有要推送的文件"
        
        try:
            start_time = time.time()
            print(f"🚀 [DEBUG] ========== 开始推送操作 ==========")
            print(f"   开始时间: {time.strftime('%H:%M:%S')}")
            print(f"   文件数量: {len(source_files)}")
            
            # 0. 不自动配置Git换行符，避免影响团队协作
            print(f"🔧 [DEBUG] 使用标准Git操作，遇到CRLF问题时提供解决指导")
            
            # 1. 检测是否为子仓库
            print(f"🔍 [DEBUG] 检测仓库类型...")
            is_submodule = self._detect_submodule()
            if is_submodule:
                print(f"   📦 检测到子仓库/子模块")
            else:
                print(f"   📁 普通Git仓库")
            
            # 2. 确定目标基础路径
            print(f"🔍 [DEBUG] 路径计算调试:")
            print(f"   原始Git路径: {self.git_path}")
            print(f"   目标目录参数: {target_directory}")
            
            # 直接使用git_path作为基础路径
            target_base_path = self.git_path
            print(f"   ✅ 最终target_base_path: {target_base_path}")
            print(f"   📝 说明: 直接使用git_path，避免路径重复")
            
            # 2.5. 🔧 安全的文件夹替换模式处理
            if folder_upload_modes:
                print(f"🔄 [REPLACE] 开始处理文件夹替换模式...")
                replace_folders = [info for info in folder_upload_modes.values() if info.get('mode') == 'replace']
                
                if replace_folders:
                    print(f"   发现 {len(replace_folders)} 个需要替换的文件夹")
                    
                    # 🚨 关键安全改进：只删除与当前提交文件直接相关的目标文件夹
                    safe_deletions = self._calculate_safe_deletion_targets(replace_folders, source_files)
                    
                    if safe_deletions:
                        print(f"   🎯 经过安全验证，确定需要删除的文件夹:")
                        for deletion_info in safe_deletions:
                            print(f"      📁 {deletion_info['folder_name']}")
                            print(f"      🎯 路径: {deletion_info['target_path']}")
                            print(f"      🔍 原因: {deletion_info['reason']}")
                        
                        # 🚨 最终安全确认：显示即将删除的详细信息
                        print(f"   🚨 即将执行替换操作，删除以下文件夹:")
                        for deletion_info in safe_deletions:
                            print(f"      📁 {deletion_info['folder_name']}")
                            print(f"      📍 路径: {deletion_info['target_path']}")
                            print(f"      📊 文件数: {deletion_info.get('file_count', '未知')}")
                            print(f"      📝 原因: {deletion_info['reason']}")
                            print(f"      " + "="*50)
                        
                        # 执行安全删除
                        deletion_results = self._execute_safe_deletions(safe_deletions)
                        
                        # 🚨 增强用户反馈：详细的替换操作说明
                        successful_replacements = []
                        failed_replacements = []
                        
                        for result in deletion_results:
                            if result['success']:
                                successful_replacements.append(result)
                                print(f"      ✅ 替换成功: {result['folder_name']}")
                                print(f"         📁 删除了目标路径: {result.get('deleted_path', 'N/A')}")
                                print(f"         📄 清理了 {result.get('deleted_files_count', 0)} 个旧文件")
                            else:
                                failed_replacements.append(result)
                                print(f"      ❌ 替换失败: {result['folder_name']} - {result['error']}")
                        
                        # 总结替换操作
                        if successful_replacements:
                            print(f"   🎉 替换模式执行完成：成功替换 {len(successful_replacements)} 个文件夹")
                            print(f"   💡 接下来将上传新文件到已清理的目标位置")
                        
                        if failed_replacements:
                            print(f"   ⚠️ 注意：{len(failed_replacements)} 个文件夹替换失败，可能影响上传结果")
                    else:
                        print(f"   ✅ 安全验证：没有需要删除的文件夹（避免误删）")
                else:
                    print(f"   ℹ️ 没有标记为替换模式的文件夹")
            else:
                print(f"🔍 [DEBUG] 未提供文件夹上传模式信息，跳过文件夹删除步骤")
            
            copied_files = []
            failed_files = []
            
            # 3. 批量复制文件
            print(f"📄 [DEBUG] 开始批量复制文件...")
            copy_start_time = time.time()
            
            for i, source_file in enumerate(source_files):
                try:
                    print(f"   处理文件 {i+1}/{len(source_files)}: {os.path.basename(source_file)}")
                    
                    # 计算目标路径
                    target_file_path = self._calculate_target_path(source_file, target_base_path)
                    
                    if not target_file_path:
                        failed_files.append(f"{os.path.basename(source_file)}: 无法计算目标路径")
                        continue
                    
                    # 确保目标目录存在
                    target_dir = os.path.dirname(target_file_path)
                    
                    # 🔍 详细调试输出：目录创建位置
                    print(f"📁 [MKDIR_DEBUG] ========== 目录创建调试信息 ==========")
                    print(f"   调用函数: GitSvnManager.push_files_to_git()")
                    print(f"   源文件: {source_file}")
                    print(f"   目标文件路径: {target_file_path}")
                    print(f"   目标目录: {target_dir}")
                    print(f"   目标目录绝对路径: {os.path.abspath(target_dir)}")
                    print(f"   目录是否存在: {os.path.exists(target_dir)}")
                    
                    # 检查路径中的CommonResource重复
                    if target_dir.count('CommonResource') > 1:
                        print(f"   ❌ 警告：检测到重复的CommonResource目录！")
                        commonresource_positions = []
                        start = 0
                        while True:
                            pos = target_dir.find('CommonResource', start)
                            if pos == -1:
                                break
                            commonresource_positions.append(pos)
                            start = pos + 1
                        print(f"   CommonResource出现位置: {commonresource_positions}")
                    
                    # 显示路径组成部分
                    path_parts = target_dir.split(os.sep)
                    print(f"   路径组成部分: {' -> '.join(path_parts)}")
                    
                    # 检查Git配置路径
                    print(f"   当前Git路径配置: {self.git_path}")
                    print(f"   target_base_path参数: {target_base_path}")
                    
                    if not os.path.exists(target_dir):
                        print(f"   🔨 即将创建目录: {target_dir}")
                        print(f"   🔨 创建目录的绝对路径: {os.path.abspath(target_dir)}")
                    else:
                        print(f"   ✅ 目录已存在，无需创建")
                    
                    print(f"   ================================================")
                    
                    # 创建目录（支持长路径）
                    def get_long_path_name_for_dir(path):
                        """获取支持长路径的目录路径名"""
                        if os.name == 'nt' and not path.startswith('\\\\?\\'):
                            abs_path = os.path.abspath(path)
                            if len(abs_path) > 260:
                                return '\\\\?\\' + abs_path
                        return path
                    
                    long_target_dir = get_long_path_name_for_dir(target_dir)
                    if len(target_dir) > 250:
                        print(f"   ⚠️ 检测到长目录路径 ({len(target_dir)} 字符)")
                        print(f"   应用长路径支持: {long_target_dir}")
                    
                    os.makedirs(long_target_dir, exist_ok=True)
                    
                    # 复制文件（支持长路径）
                    import shutil
                    
                    # Windows长路径支持：使用UNC路径前缀
                    def get_long_path_name(path):
                        """获取支持长路径的路径名"""
                        if os.name == 'nt' and not path.startswith('\\\\?\\'):
                            # 转换为绝对路径并添加UNC前缀
                            abs_path = os.path.abspath(path)
                            if len(abs_path) > 260:  # 只在路径过长时使用UNC前缀
                                return '\\\\?\\' + abs_path
                        return path
                    
                    # 检查路径长度并应用长路径支持
                    long_source_path = get_long_path_name(source_file)
                    long_target_path = get_long_path_name(target_file_path)
                    
                    if len(target_file_path) > 250:  # 预警长度
                        print(f"   ⚠️ 检测到长路径 ({len(target_file_path)} 字符)")
                        print(f"   应用长路径支持: {long_target_path}")
                    
                    shutil.copy2(long_source_path, long_target_path)
                    copied_files.append(target_file_path)
                    print(f"   ✅ 复制成功: {os.path.basename(source_file)}")
                    
                except Exception as e:
                    error_msg = f"{os.path.basename(source_file)}: {str(e)}"
                    failed_files.append(error_msg)
                    print(f"   ❌ 复制失败: {error_msg}")
            
            copy_time = time.time() - copy_start_time
            print(f"   📊 文件复制耗时: {copy_time:.2f}秒")
            
            if not copied_files:
                return False, f"所有文件复制失败: {'; '.join(failed_files)}"
            
            # 4. Git操作优化
            print(f"📝 [DEBUG] 开始Git操作...")
            git_start_time = time.time()
            
            # 4.0. 配置Git长路径支持（预防性措施）
            self._configure_git_long_path_support()
            
            # 4.1. 批量添加文件到Git（使用相对路径）
            print(f"   批量添加 {len(copied_files)} 个文件到Git...")
            relative_paths = []
            for file_path in copied_files:
                relative_path = os.path.relpath(file_path, self.git_path)
                relative_paths.append(relative_path)
            
            # 🚨 关键修复：智能批处理，避免命令行参数过长
            result = self._smart_git_add_files(relative_paths)
            
            if result.returncode != 0:
                print(f"   ❌ 批量添加失败: {result.stderr}")
                
                # 检查是否为CRLF问题，提供智能解决方案
                if self._is_crlf_error(result.stderr):
                    print(f"   🔧 检测到CRLF问题，尝试自动修复...")
                    
                    # 尝试自动修复CRLF问题
                    auto_fix_result = self._auto_fix_crlf_issue(result.stderr)
                    if auto_fix_result[0]:  # 修复成功
                        print(f"   ✅ CRLF问题已自动修复，重新尝试添加文件...")
                        
                        # 🚨 重新尝试添加文件 - 使用智能批处理
                        print(f"   🔄 CRLF修复后重新尝试添加文件...")
                        retry_result = self._smart_git_add_files(relative_paths)
                        
                        if retry_result and retry_result.returncode == 0:
                            print(f"   ✅ 重新添加文件成功")
                            result = retry_result  # 更新结果
                        else:
                            error_msg = f"CRLF问题修复成功，但重新添加文件失败: {retry_result.stderr if retry_result else '未知错误'}"
                            return False, error_msg
                    else:
                        # 自动修复失败，提供手动指导
                        error_msg = (
                            "🚨 Git换行符冲突检测到！\n\n"
                            f"🔧 自动修复尝试失败: {auto_fix_result[1]}\n\n"
                            "💡 这是Windows/Unix换行符差异导致的，需要手动解决以避免影响团队协作。\n\n"
                            "🛠️ 推荐解决方案（请选择一种）：\n\n"
                            "【方案1 - 临时解决】\n"
                            "在目标Git仓库中执行：\n"
                            "git config core.safecrlf false\n"
                            "然后重新推送\n\n"
                            "【方案2 - 使用工具】\n"
                            "运行独立修复工具：\n"
                            f"python crlf_auto_fix.py \"{self.git_path}\"\n\n"
                            "【方案3 - 手动处理】\n"
                            "使用'重置更新仓库'功能重新初始化\n\n"
                            "⚠️ 注意：为保证团队协作，建议与团队讨论后再修改Git配置\n\n"
                            f"详细错误: {result.stderr}"
                        )
                        return False, error_msg
                else:
                    return False, f"添加文件到Git失败: {result.stderr}"
            else:
                print(f"   ✅ 文件添加成功")
            
            # 4.2. 检查Git状态（简化）
            print(f"   检查Git状态...")
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=15, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                changed_files = len(result.stdout.strip().split('\n'))
                print(f"   📊 检测到 {changed_files} 个文件更改")
            else:
                print(f"   ⚠️ 没有检测到更改或状态检查失败")
            
            # 4.3. 提交更改
            commit_message = f"{len(copied_files)} 个文件被提交，来自美术自资产上传工具。"
            print(f"   提交更改: {commit_message}")
            
            result = subprocess.run(['git', 'commit', '-m', commit_message], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)  # 60秒超时
            
            if result.returncode != 0:
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    print(f"   ⚠️ 没有新的更改需要提交")
                    return False, "没有新的更改需要提交（文件可能已存在且内容相同）"
                print(f"   ❌ 提交失败: {result.stderr}")
                return False, f"提交更改失败: {result.stderr}"
            else:
                print(f"   ✅ 提交成功")
            
            git_time = time.time() - git_start_time
            print(f"   📊 Git操作耗时: {git_time:.2f}秒")
            
            # 5. 推送到远程仓库（优化）
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支"
            
            print(f"🚀 [DEBUG] 推送到远程...")
            push_start_time = time.time()
            
            # 针对子仓库的特殊处理
            if is_submodule:
                print(f"   🔧 子仓库推送模式")
                # 子仓库可能需要特殊的推送策略
                result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=120, creationflags=SUBPROCESS_FLAGS)  # 2分钟超时
            else:
                print(f"   🔧 普通仓库推送模式")
                result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=90, creationflags=SUBPROCESS_FLAGS)  # 1.5分钟超时
            
            push_time = time.time() - push_start_time
            print(f"   📊 推送耗时: {push_time:.2f}秒")
            
            if result.returncode != 0:
                print(f"   ❌ 推送失败: {result.stderr}")
                error_msg = result.stderr.strip()
                
                # 🚨 推送失败时的智能回滚判断
                print(f"🔍 [ROLLBACK_CHECK] 推送失败，分析是否需要回滚...")
                should_rollback, rollback_reason = self._should_perform_rollback(copied_files, error_msg)
                
                if should_rollback:
                    print(f"✅ [ROLLBACK_CHECK] 确认需要回滚: {rollback_reason}")
                    rollback_success = self._rollback_failed_push(copied_files)
                else:
                    print(f"🛡️ [ROLLBACK_CHECK] 跳过回滚: {rollback_reason}")
                    rollback_success = False
                
                if should_rollback:
                    if rollback_success:
                        print(f"   ✅ 安全回滚成功：已撤销当前上传的文件，其他文件未受影响")
                        rollback_msg = "\n\n🔄 已安全回滚本次上传的文件，Git仓库中的其他文件和历史记录未受影响。"
                    else:
                        print(f"   ⚠️ 回滚部分失败：可能需要手动清理本次上传的文件")
                        rollback_msg = "\n\n⚠️ 自动回滚部分失败，建议手动检查并清理本次上传的文件。"
                else:
                    rollback_msg = f"\n\n🛡️ 为安全起见，未执行自动回滚。原因：{rollback_reason}\n💡 如需回滚，请手动处理。"
                
                # 🔍 分析推送失败原因并提供解决方案
                if "rejected" in error_msg and "remote contains work" in error_msg:
                    return False, (
                        "❌ 推送被拒绝：远程仓库包含您本地没有的更改。\n\n"
                        "💡 重要说明：文件未成功上传到远程仓库，团队成员无法获取这些文件。\n\n"
                        "解决方案：\n"
                        "1. 点击工具中的'拉取最新代码'按钮同步远程更改\n"
                        "2. 或者手动执行: git pull origin <分支名>\n"
                        "3. 解决可能的冲突后重新推送\n\n"
                        f"详细错误: {error_msg}{rollback_msg}"
                    )
                elif "Authentication failed" in error_msg or "could not read Username" in error_msg:
                    return False, (
                        "❌ Git认证失败：需要输入用户名和密码。\n\n"
                        "💡 重要说明：文件未成功上传到远程仓库，团队成员无法获取这些文件。\n\n"
                        "解决方案：\n"
                        "1. 运行 git_auth_fix.py 脚本配置凭据存储\n"
                        "2. 或手动执行: git config credential.helper store\n"
                        "3. 然后执行一次 git pull 并输入用户名密码\n"
                        "4. 凭据将被保存，以后不需要重复输入\n\n"
                        f"详细错误: {error_msg}{rollback_msg}"
                    )
                elif "Connection" in error_msg or "network" in error_msg or "timeout" in error_msg:
                    return False, (
                        "❌ 网络连接失败：无法连接到Git服务器。\n\n"
                        "💡 重要说明：文件未成功上传到远程仓库，团队成员无法获取这些文件。\n\n"
                        "解决方案：\n"
                        "1. 检查网络连接是否正常\n"
                        "2. 确认Git服务器地址是否正确\n"
                        "3. 如果使用VPN，请确保VPN连接正常\n"
                        "4. 稍后重试推送操作\n\n"
                        f"详细错误: {error_msg}{rollback_msg}"
                    )
                else:
                    return False, (
                        f"❌ 推送到远程仓库失败: {error_msg}\n\n"
                        f"💡 重要说明：文件未成功上传到远程仓库，团队成员无法获取这些文件。{rollback_msg}"
                    )
            else:
                print(f"   ✅ 推送成功")
            
            # 6. 生成成功消息
            total_time = time.time() - start_time
            print(f"📊 [DEBUG] ========== 推送完成 ==========")
            print(f"   总耗时: {total_time:.2f}秒")
            print(f"   文件复制: {copy_time:.2f}秒")
            print(f"   Git操作: {git_time:.2f}秒") 
            print(f"   远程推送: {push_time:.2f}秒")
            print(f"   结束时间: {time.strftime('%H:%M:%S')}")
            
            success_msg = f"成功推送 {len(copied_files)} 个文件到分支 {current_branch} (耗时 {total_time:.1f}秒)"
            if failed_files:
                success_msg += f"，{len(failed_files)} 个文件失败"
            
            # 清除GUID缓存，因为仓库内容已更新
            self.clear_guid_cache_for_git_path(self.git_path)
            
            return True, success_msg
            
        except subprocess.TimeoutExpired as e:
            return False, f"推送操作超时: {str(e)}"
        except Exception as e:
            # 🚨 专门处理Windows长路径问题
            error_msg = str(e)
            if "WinError 206" in error_msg or "文件名或扩展名太长" in error_msg:
                return False, self._handle_long_path_error(error_msg, source_files)
            else:
                return False, f"推送过程中发生异常: {error_msg}"
    
    def reset_and_pull_repository(self) -> tuple:
        """
        重置仓库并拉取最新代码
        
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            print(f"🔄 [REPO_RESET] 开始重置和拉取仓库...")
            
            if not self.git_path or not os.path.exists(self.git_path):
                return False, "Git仓库路径无效"
            
            # 第1步：Git重置 (git reset --hard)
            print(f"   🔄 执行 git reset --hard...")
            result = subprocess.run(['git', 'reset', '--hard'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                error_msg = f"git reset --hard 失败: {result.stderr.strip()}"
                print(f"   ❌ {error_msg}")
                return False, error_msg
            else:
                print(f"   ✅ git reset --hard 成功")
            
            # 第2步：清理未跟踪文件 (git clean -f)
            print(f"   🗑️ 执行 git clean -f...")
            result = subprocess.run(['git', 'clean', '-f'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                error_msg = f"git clean -f 失败: {result.stderr.strip()}"
                print(f"   ❌ {error_msg}")
                return False, error_msg
            else:
                cleaned_output = result.stdout.strip()
                if cleaned_output:
                    print(f"   ✅ git clean -f 成功，清理了文件:")
                    cleaned_lines = cleaned_output.split('\n')
                    for line in cleaned_lines[:5]:  # 只显示前5行
                        print(f"     🗑️ {line}")
                    if len(cleaned_lines) > 5:
                        remaining_count = len(cleaned_lines) - 5
                        print(f"     ... 还有 {remaining_count} 个文件")
                else:
                    print(f"   ✅ git clean -f 成功，没有需要清理的文件")
            
            # 第3步：拉取最新代码 (git pull)
            print(f"   📥 执行 git pull...")
            
            # 获取当前分支
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支信息"
            
            print(f"   📋 当前分支: {current_branch}")
            
            result = subprocess.run(['git', 'pull', 'origin', current_branch], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=180, creationflags=SUBPROCESS_FLAGS)  # 3分钟超时
            
            if result.returncode != 0:
                error_msg = f"git pull 失败: {result.stderr.strip()}"
                print(f"   ❌ {error_msg}")
                
                # 分析拉取失败的原因
                stderr_lower = result.stderr.lower()
                if 'authentication' in stderr_lower or 'credential' in stderr_lower:
                    return False, f"Git认证失败，请检查用户名密码配置:\n{result.stderr.strip()}"
                elif 'connection' in stderr_lower or 'network' in stderr_lower:
                    return False, f"网络连接失败，请检查网络状态:\n{result.stderr.strip()}"
                elif 'permission' in stderr_lower or 'access' in stderr_lower:
                    return False, f"权限不足，请检查仓库访问权限:\n{result.stderr.strip()}"
                else:
                    return False, error_msg
            else:
                pull_output = result.stdout.strip()
                if 'Already up to date' in pull_output or 'Already up-to-date' in pull_output:
                    print(f"   ✅ 仓库已是最新版本")
                else:
                    print(f"   ✅ git pull 成功，更新内容:")
                    # 显示更新摘要
                    for line in pull_output.split('\n')[:3]:  # 只显示前3行
                        if line.strip():
                            print(f"     📥 {line}")
            
            print(f"🎉 [REPO_RESET] 仓库重置和拉取完成")
            return True, "仓库重置和拉取成功"
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"操作超时: {str(e)}"
            print(f"❌ [REPO_RESET] {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"重置和拉取过程中发生异常: {str(e)}"
            print(f"❌ [REPO_RESET] {error_msg}")
            return False, error_msg

    def _should_perform_rollback(self, copied_files: List[str], error_msg: str) -> tuple:
        """
        智能判断是否应该执行回滚操作
        
        Args:
            copied_files: 已复制的文件列表
            error_msg: 推送错误信息
            
        Returns:
            tuple: (是否应该回滚, 判断原因)
        """
        try:
            print(f"🔍 [ROLLBACK_ANALYSIS] 分析推送失败情况...")
            
            # 1. 检查是否有本地文件被成功复制和提交
            if not copied_files:
                return False, "没有文件被复制到本地仓库"
            
            # 2. 验证文件确实存在于本地Git仓库中
            existing_files = []
            for file_path in copied_files:
                if os.path.exists(file_path):
                    existing_files.append(file_path)
            
            if not existing_files:
                return False, f"本地仓库中没有找到已复制的文件（{len(copied_files)} 个文件都不存在）"
            
            print(f"   📊 文件存在性检查: {len(existing_files)}/{len(copied_files)} 个文件存在于本地仓库")
            
            # 3. 检查Git是否有新的提交（确认本地提交成功）
            result = subprocess.run(['git', 'log', '--oneline', '-1'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=15, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                return False, "无法检查Git提交历史"
            
            latest_commit = result.stdout.strip()
            if not latest_commit:
                return False, "没有找到最新的Git提交"
            
            print(f"   📝 最新提交: {latest_commit[:50]}...")
            
            # 4. 检查最新提交是否包含我们的文件
            result = subprocess.run(['git', 'show', '--name-only', '--format='], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=15, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                return False, "无法检查最新提交的文件列表"
            
            committed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            if not committed_files:
                return False, "最新提交中没有文件更改"
            
            print(f"   📋 最新提交包含 {len(committed_files)} 个文件")
            
            # 5. 验证提交中的文件是否与我们上传的文件匹配
            our_relative_files = []
            for file_path in copied_files:
                rel_path = os.path.relpath(file_path, self.git_path).replace('\\', '/')
                our_relative_files.append(rel_path)
            
            matching_files = [f for f in committed_files if f in our_relative_files]
            if not matching_files:
                return False, f"最新提交中没有找到我们上传的文件（提交: {len(committed_files)} 个，上传: {len(our_relative_files)} 个）"
            
            print(f"   ✅ 匹配文件: {len(matching_files)}/{len(our_relative_files)} 个文件在最新提交中")
            
            # 6. 分析推送失败的具体原因，判断是否适合回滚
            error_lower = error_msg.lower()
            
            # 6.1 网络或连接问题 - 适合回滚
            if any(keyword in error_lower for keyword in ['connection', 'network', 'timeout', 'unreachable', 'failed to connect']):
                return True, f"网络连接问题导致推送失败，本地已提交 {len(matching_files)} 个文件"
            
            # 6.2 认证问题 - 适合回滚  
            if any(keyword in error_lower for keyword in ['authentication', 'credential', 'username', 'password', 'token']):
                return True, f"认证问题导致推送失败，本地已提交 {len(matching_files)} 个文件"
            
            # 6.3 远程仓库冲突 - 需要谨慎，通常不回滚
            if any(keyword in error_lower for keyword in ['rejected', 'non-fast-forward', 'remote contains work']):
                # 检查是否是简单的版本冲突
                if 'hint: updates were rejected because the remote contains work' in error_lower:
                    return True, f"远程版本冲突，本地已提交 {len(matching_files)} 个文件（可安全回滚后重新同步）"
                else:
                    return False, "复杂的远程冲突，建议手动处理而非自动回滚"
            
            # 6.4 权限问题 - 适合回滚
            if any(keyword in error_lower for keyword in ['permission', 'access', 'forbidden', '403', '401']):
                return True, f"权限问题导致推送失败，本地已提交 {len(matching_files)} 个文件"
            
            # 6.5 其他未知错误 - 保守处理，不回滚
            print(f"   ⚠️ 未识别的推送错误类型: {error_msg[:100]}...")
            return False, "未知的推送错误，为安全起见不执行自动回滚"
            
        except Exception as e:
            print(f"❌ [ROLLBACK_ANALYSIS] 分析过程异常: {e}")
            return False, f"回滚分析过程出现异常: {e}"

    def _rollback_failed_push(self, copied_files: List[str]) -> bool:
        """
        推送失败时回滚本地更改
        
        Args:
            copied_files: 已复制的文件列表
            
        Returns:
            bool: 回滚是否成功
        """
        try:
            print(f"🔄 [ROLLBACK] 开始回滚操作...")
            print(f"   需要回滚 {len(copied_files)} 个文件")
            
            # 1. 安全的Git回滚 - 只撤销当前提交的文件
            print(f"   🔄 安全回滚Git提交（只影响当前上传的文件）...")
            
            # 1.1 首先获取当前提交中修改的文件列表
            result = subprocess.run(['git', 'show', '--name-only', '--format='], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=30, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                committed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                print(f"   📋 当前提交包含 {len(committed_files)} 个文件")
                
                # 验证这些文件是否都是我们刚才上传的文件
                our_relative_files = []
                for file_path in copied_files:
                    rel_path = os.path.relpath(file_path, self.git_path).replace('\\', '/')
                    our_relative_files.append(rel_path)
                
                # 检查是否有不属于当前上传的文件被提交了
                unexpected_files = [f for f in committed_files if f not in our_relative_files]
                if unexpected_files:
                    print(f"   ⚠️ 警告：发现不属于当前上传的文件在提交中: {unexpected_files[:3]}")
                    print(f"   🛡️ 为安全起见，使用精确回滚模式")
                    
                    # 使用更安全的回滚方式：只撤销我们的文件
                    return self._safe_selective_rollback(copied_files, our_relative_files)
                else:
                    print(f"   ✅ 验证通过：提交中只包含当前上传的文件")
            else:
                print(f"   ⚠️ 无法获取当前提交文件列表，使用安全回滚模式")
                return self._safe_selective_rollback(copied_files, [])
            
            # 1.2 安全的完整回滚（只有确认安全时才执行）
            print(f"   🔄 执行安全的完整回滚...")
            result = subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=30, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                print(f"   ❌ Git reset失败: {result.stderr}")
                print(f"   🔄 改用精确文件回滚模式...")
                our_relative_files = []
                for file_path in copied_files:
                    rel_path = os.path.relpath(file_path, self.git_path).replace('\\', '/')
                    our_relative_files.append(rel_path)
                return self._safe_selective_rollback(copied_files, our_relative_files)
            else:
                print(f"   ✅ 安全回滚成功")
            
            # 2. 删除已复制的文件
            print(f"   🗑️ 清理已复制的文件...")
            deleted_count = 0
            failed_deletions = []
            
            for file_path in copied_files:
                try:
                    if os.path.exists(file_path):
                        # 支持长路径删除
                        def get_long_path_name(path):
                            if os.name == 'nt' and not path.startswith('\\\\?\\'):
                                abs_path = os.path.abspath(path)
                                if len(abs_path) > 260:
                                    return '\\\\?\\' + abs_path
                            return path
                        
                        long_file_path = get_long_path_name(file_path)
                        os.remove(long_file_path)
                        deleted_count += 1
                        print(f"     ✅ 删除: {os.path.basename(file_path)}")
                    else:
                        print(f"     ⚠️ 文件不存在: {os.path.basename(file_path)}")
                        
                except Exception as e:
                    failed_deletions.append(f"{os.path.basename(file_path)}: {str(e)}")
                    print(f"     ❌ 删除失败: {os.path.basename(file_path)} - {e}")
            
            # 3. 清理空目录
            print(f"   📁 清理空目录...")
            self._cleanup_empty_directories(copied_files)
            
            # 4. 总结回滚结果
            print(f"📊 [ROLLBACK] 回滚完成:")
            print(f"   成功删除文件: {deleted_count}/{len(copied_files)}")
            if failed_deletions:
                print(f"   删除失败: {len(failed_deletions)} 个")
                for failure in failed_deletions[:3]:  # 只显示前3个
                    print(f"     • {failure}")
                if len(failed_deletions) > 3:
                    print(f"     • ... 还有 {len(failed_deletions) - 3} 个失败")
            
            # 如果大部分文件成功删除，认为回滚成功
            success_rate = deleted_count / len(copied_files) if copied_files else 1.0
            rollback_success = success_rate >= 0.8  # 80%成功率
            
            print(f"   回滚成功率: {success_rate:.1%}")
            print(f"   回滚结果: {'✅ 成功' if rollback_success else '❌ 部分失败'}")
            
            return rollback_success
            
        except Exception as e:
            print(f"❌ [ROLLBACK] 回滚操作异常: {e}")
            return False
    
    def _safe_selective_rollback(self, copied_files: List[str], our_relative_files: List[str]) -> bool:
        """
        安全的选择性回滚 - 只撤销当前上传的文件，不影响其他文件
        
        Args:
            copied_files: 已复制的文件绝对路径列表
            our_relative_files: 我们上传的文件相对路径列表
            
        Returns:
            bool: 回滚是否成功
        """
        try:
            print(f"🛡️ [SAFE_ROLLBACK] 开始精确选择性回滚...")
            print(f"   只回滚当前上传的 {len(copied_files)} 个文件")
            
            # 1. 使用git checkout恢复我们的文件到上一个版本
            if our_relative_files:
                print(f"   🔄 从Git历史恢复文件到上一版本...")
                for rel_file in our_relative_files[:5]:  # 显示前5个文件
                    print(f"     📄 {rel_file}")
                if len(our_relative_files) > 5:
                    print(f"     ... 还有 {len(our_relative_files) - 5} 个文件")
                
                # 批量恢复文件到HEAD~1版本
                result = subprocess.run(['git', 'checkout', 'HEAD~1', '--'] + our_relative_files, 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=60, creationflags=SUBPROCESS_FLAGS)
                
                if result.returncode != 0:
                    print(f"   ⚠️ Git checkout部分失败: {result.stderr}")
                    # 继续尝试删除文件
                else:
                    print(f"   ✅ Git文件恢复成功")
            
            # 2. 直接删除我们复制的文件（如果Git恢复失败的话）
            print(f"   🗑️ 确保删除当前上传的文件...")
            deleted_count = 0
            failed_deletions = []
            
            for file_path in copied_files:
                try:
                    if os.path.exists(file_path):
                        # 支持长路径删除
                        def get_long_path_name(path):
                            if os.name == 'nt' and not path.startswith('\\\\?\\'):
                                abs_path = os.path.abspath(path)
                                if len(abs_path) > 260:
                                    return '\\\\?\\' + abs_path
                            return path
                        
                        long_file_path = get_long_path_name(file_path)
                        os.remove(long_file_path)
                        deleted_count += 1
                        print(f"     ✅ 删除: {os.path.basename(file_path)}")
                    else:
                        print(f"     ✅ 文件已不存在: {os.path.basename(file_path)}")
                        deleted_count += 1  # 算作成功
                        
                except Exception as e:
                    failed_deletions.append(f"{os.path.basename(file_path)}: {str(e)}")
                    print(f"     ❌ 删除失败: {os.path.basename(file_path)} - {e}")
            
            # 3. 撤销Git暂存区的更改（只针对我们的文件）
            if our_relative_files:
                print(f"   🔄 撤销Git暂存区的更改...")
                result = subprocess.run(['git', 'reset', 'HEAD'] + our_relative_files, 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=30, creationflags=SUBPROCESS_FLAGS)
                
                if result.returncode != 0:
                    print(f"   ⚠️ Git reset暂存区失败: {result.stderr}")
                else:
                    print(f"   ✅ 暂存区重置成功")
            
            # 4. 修正最后一次提交（移除我们的文件）
            print(f"   🔧 修正最后一次提交（移除当前上传的文件）...")
            result = subprocess.run(['git', 'commit', '--amend', '--no-edit'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                # 如果amend失败，尝试创建一个回滚提交
                print(f"   ⚠️ 修正提交失败，尝试创建回滚提交...")
                result = subprocess.run(['git', 'add', '.'], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      timeout=30, creationflags=SUBPROCESS_FLAGS)
                
                if result.returncode == 0:
                    result = subprocess.run(['git', 'commit', '-m', f'回滚推送失败的 {len(copied_files)} 个文件'], 
                                          cwd=self.git_path, 
                                          capture_output=True, 
                                          text=True,
                                          timeout=60, creationflags=SUBPROCESS_FLAGS)
                    
                    if result.returncode == 0:
                        print(f"   ✅ 回滚提交创建成功")
                    else:
                        print(f"   ⚠️ 回滚提交失败: {result.stderr}")
            else:
                print(f"   ✅ 提交修正成功")
            
            # 5. 清理空目录
            print(f"   📁 清理空目录...")
            self._cleanup_empty_directories(copied_files)
            
            # 6. 总结回滚结果
            success_rate = deleted_count / len(copied_files) if copied_files else 1.0
            rollback_success = success_rate >= 0.8  # 80%成功率
            
            print(f"📊 [SAFE_ROLLBACK] 精确回滚完成:")
            print(f"   文件处理: {deleted_count}/{len(copied_files)} 成功")
            print(f"   成功率: {success_rate:.1%}")
            print(f"   回滚结果: {'✅ 成功' if rollback_success else '❌ 部分失败'}")
            print(f"   🛡️ 其他文件和Git历史未受影响")
            
            if failed_deletions:
                print(f"   失败文件: {len(failed_deletions)} 个")
                for failure in failed_deletions[:3]:
                    print(f"     • {failure}")
                if len(failed_deletions) > 3:
                    print(f"     • ... 还有 {len(failed_deletions) - 3} 个失败")
            
            return rollback_success
            
        except Exception as e:
            print(f"❌ [SAFE_ROLLBACK] 精确回滚异常: {e}")
            return False

    def _cleanup_empty_directories(self, copied_files: List[str]):
        """清理空目录"""
        try:
            # 收集所有目录
            directories = set()
            for file_path in copied_files:
                dir_path = os.path.dirname(file_path)
                while dir_path and dir_path != self.git_path:
                    directories.add(dir_path)
                    parent = os.path.dirname(dir_path)
                    if parent == dir_path:  # 避免无限循环
                        break
                    dir_path = parent
            
            # 按深度排序（深的先删除）
            sorted_dirs = sorted(directories, key=lambda x: x.count(os.sep), reverse=True)
            
            cleaned_count = 0
            for dir_path in sorted_dirs:
                try:
                    if os.path.exists(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        cleaned_count += 1
                        print(f"     🗑️ 清理空目录: {os.path.relpath(dir_path, self.git_path)}")
                except Exception as e:
                    # 目录不为空或其他错误，忽略
                    pass
            
            if cleaned_count > 0:
                print(f"   清理了 {cleaned_count} 个空目录")
                
        except Exception as e:
            print(f"   ⚠️ 清理空目录时出错: {e}")

    def _handle_long_path_error(self, error_msg: str, source_files: List[str]) -> str:
        """处理Windows长路径错误"""
        try:
            print(f"🚨 [LONG_PATH] 检测到Windows长路径问题")
            print(f"   错误信息: {error_msg}")
            
            # 分析哪些文件可能导致路径过长
            long_path_files = []
            for file_path in source_files:
                # 计算目标路径长度
                target_path = self._calculate_target_path(file_path, self.git_path)
                if target_path and len(target_path) > 260:  # Windows路径限制
                    long_path_files.append({
                        'source': file_path,
                        'target': target_path,
                        'length': len(target_path)
                    })
            
            if long_path_files:
                print(f"   发现 {len(long_path_files)} 个长路径文件:")
                for file_info in long_path_files[:5]:  # 只显示前5个
                    print(f"     • {os.path.basename(file_info['source'])} -> {file_info['length']} 字符")
            
            # 生成用户友好的错误消息和解决方案
            error_message = (
                "🚨 Windows路径长度限制问题\n\n"
                "❌ 错误原因:\n"
                f"• Windows系统默认路径长度限制为260个字符\n"
                f"• 检测到 {len(long_path_files)} 个文件的目标路径超过此限制\n\n"
                "🛠️ 解决方案 (请选择一种):\n\n"
                "【方案1 - 启用Windows长路径支持】\n"
                "1. 以管理员身份运行PowerShell\n"
                "2. 执行命令: New-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force\n"
                "3. 重启计算机\n"
                "4. 重新尝试推送\n\n"
                "【方案2 - 使用较短的Git仓库路径】\n"
                "• 将Git仓库移动到较短的路径 (如 C:\\git\\repo)\n"
                "• 重新配置Git路径并重试\n\n"
                "【方案3 - 重新组织文件结构】\n"
                "• 简化目标目录层级\n"
                "• 使用较短的文件名\n\n"
                "💡 推荐使用方案1，这是Windows 10/11的官方长路径支持功能"
            )
            
            return error_message
            
        except Exception as handle_e:
            return f"处理长路径错误时发生异常: {handle_e}\n\n原始错误: {error_msg}"
    
    def _configure_git_long_path_support(self):
        """配置Git长路径支持（Windows专用）"""
        try:
            # 只在Windows系统上执行
            if os.name != 'nt':
                return
            
            # 检查是否已经配置过，避免重复设置
            if hasattr(self, '_git_longpath_configured') and self._git_longpath_configured:
                return
            
            print(f"   🔧 配置Git长路径支持...")
            
            # 检查当前的longpaths设置
            result = subprocess.run(['git', 'config', '--get', 'core.longpaths'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            current_setting = result.stdout.strip().lower() if result.returncode == 0 else ""
            
            if current_setting == "true":
                print(f"   ✅ Git长路径支持已启用")
                self._git_longpath_configured = True
                return
            
            # 尝试启用长路径支持
            print(f"   📝 启用Git长路径支持...")
            result = subprocess.run(['git', 'config', 'core.longpaths', 'true'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                print(f"   ✅ Git长路径支持已启用")
                self._git_longpath_configured = True
                
                # 同时检查Windows系统级长路径支持
                self._check_windows_long_path_support()
            else:
                print(f"   ⚠️ 启用Git长路径支持失败: {result.stderr}")
                
        except Exception as e:
            print(f"   ⚠️ 配置Git长路径支持时出错: {e}")
    
    def _check_windows_long_path_support(self):
        """检查Windows系统级长路径支持状态"""
        try:
            import winreg
            
            # 检查注册表中的长路径支持设置
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SYSTEM\CurrentControlSet\Control\FileSystem")
                value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
                winreg.CloseKey(key)
                
                if value == 1:
                    print(f"   ✅ Windows系统长路径支持已启用")
                else:
                    print(f"   ⚠️ Windows系统长路径支持未启用")
                    print(f"   💡 建议以管理员身份运行PowerShell并执行:")
                    powershell_cmd = "New-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"
                    print(f"      {powershell_cmd}")
                    
            except FileNotFoundError:
                print(f"   ⚠️ Windows系统长路径支持未配置")
                print(f"   💡 建议启用Windows长路径支持以避免路径长度限制")
                
        except ImportError:
            print(f"   ⚠️ 无法检查Windows长路径支持状态（winreg模块不可用）")
        except Exception as e:
            print(f"   ⚠️ 检查Windows长路径支持时出错: {e}")
    
    def _smart_git_add_files(self, relative_paths: List[str]):
        """智能Git文件添加，避免命令行参数过长问题"""
        try:
            print(f"   🔧 智能添加 {len(relative_paths)} 个文件...")
            
            # 🚨 增强功能1：智能模式选择
            if len(relative_paths) <= 5:
                # 少量文件，直接添加
                print(f"   📝 使用直接添加模式（{len(relative_paths)}个文件）...")
                return self._direct_git_add(relative_paths)
            elif len(relative_paths) <= 50:
                # 中等数量文件，使用优化批处理
                print(f"   📦 使用批处理模式（{len(relative_paths)}个文件）...")
                return self._batch_git_add(relative_paths)
            else:
                # 大量文件，使用智能分批
                print(f"   🧠 使用智能分批模式（{len(relative_paths)}个文件）...")
                return self._intelligent_batch_git_add(relative_paths)
            
        except Exception as e:
            print(f"   ❌ 智能添加文件时出错: {e}")
            # 回退到逐个添加模式
            return self._fallback_individual_git_add(relative_paths)
    
    def _direct_git_add(self, relative_paths: List[str]):
        """直接添加模式（适用于少量文件）"""
        return subprocess.run(['git', 'add'] + relative_paths, 
                            cwd=self.git_path, 
                            capture_output=True, 
                            text=True,
                            encoding='utf-8',
                            errors='ignore',
                            timeout=60, creationflags=SUBPROCESS_FLAGS)
    
    def _batch_git_add(self, relative_paths: List[str]):
        """批处理模式（原有逻辑的增强版）"""
        # 🚨 恢复原有功能：根据文件数量选择策略
        if len(relative_paths) > 10:
            print(f"   📦 使用批量添加模式...")
            return subprocess.run(['git', 'add'] + relative_paths, 
                                cwd=self.git_path, 
                                capture_output=True, 
                                text=True,
                                encoding='utf-8',
                                errors='ignore',
                                timeout=60, creationflags=SUBPROCESS_FLAGS)
        else:
            print(f"   📝 使用逐个添加模式...")
            # 🚨 恢复原有功能：逐个添加并检查每个文件的结果
            last_result = None
            for relative_path in relative_paths:
                result = subprocess.run(['git', 'add', relative_path], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=30, creationflags=SUBPROCESS_FLAGS)
                if result.returncode != 0:
                    print(f"   ❌ 添加文件失败: {relative_path} - {result.stderr}")
                    return result  # 🚨 重要：立即返回失败结果
                last_result = result
            
            return last_result if last_result else self._create_success_result()
    
    def _intelligent_batch_git_add(self, relative_paths: List[str]):
        """智能分批模式（处理大量文件，避免命令行过长）"""
        # 计算命令行长度限制（Windows约为8191字符）
        max_cmd_length = 7000  # 保守估计，留出安全边界
        
        # 估算命令行长度
        base_cmd = "git add "
        current_length = len(base_cmd)
        current_batch = []
        batch_count = 0
        
        for path in relative_paths:
            # 估算添加这个文件后的命令长度（包括空格和引号）
            path_length = len(f'"{path}" ')
            
            if current_length + path_length > max_cmd_length and current_batch:
                # 当前批次已满，执行添加
                batch_count += 1
                print(f"   📦 执行批次 {batch_count}: {len(current_batch)} 个文件")
                result = subprocess.run(['git', 'add'] + current_batch, 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=60, creationflags=SUBPROCESS_FLAGS)
                
                if result.returncode != 0:
                    print(f"   ❌ 批次 {batch_count} 添加失败: {result.stderr}")
                    return result
                else:
                    print(f"   ✅ 批次 {batch_count} 添加成功")
                
                # 重置批次
                current_batch = [path]
                current_length = len(base_cmd) + path_length
            else:
                # 添加到当前批次
                current_batch.append(path)
                current_length += path_length
        
        # 处理最后一个批次
        if current_batch:
            batch_count += 1
            print(f"   📦 执行最终批次 {batch_count}: {len(current_batch)} 个文件")
            result = subprocess.run(['git', 'add'] + current_batch, 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                print(f"   ✅ 最终批次 {batch_count} 添加成功")
            
            return result
        
        # 如果没有文件，返回成功
        return self._create_success_result()
    
    def _create_success_result(self):
        """创建成功结果对象"""
        class MockResult:
            returncode = 0
            stderr = ""
            stdout = "Files added successfully"
        
        return MockResult()
    
    def _fallback_individual_git_add(self, relative_paths: List[str]):
        """回退方案：逐个添加文件（增强版，包含原有的详细错误处理）"""
        print(f"   🔄 回退到逐个添加模式...")
        
        for i, relative_path in enumerate(relative_paths):
            print(f"   📄 添加文件 {i+1}/{len(relative_paths)}: {os.path.basename(relative_path)}")
            result = subprocess.run(['git', 'add', relative_path], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=30, creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                print(f"   ❌ 添加文件失败: {relative_path} - {result.stderr}")
                return result  # 🚨 重要：保持原有行为，立即返回失败结果
            else:
                print(f"   ✅ 成功添加: {os.path.basename(relative_path)}")
        
        # 所有文件都成功添加
        print(f"   🎉 所有 {len(relative_paths)} 个文件添加成功")
        return self._create_success_result()
    
    def _configure_git_line_endings(self):
        """配置Git换行符处理，解决CRLF问题（保守方式）"""
        try:
            # 检查是否已经配置过，避免重复设置
            if hasattr(self, '_git_crlf_configured') and self._git_crlf_configured:
                print(f"   ✅ Git换行符设置已配置，跳过")
                return
            
            print(f"   检查当前Git换行符配置...")
            
            # 检查当前的autocrlf设置
            result = subprocess.run(['git', 'config', '--get', 'core.autocrlf'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            current_autocrlf = result.stdout.strip() if result.returncode == 0 else ""
            print(f"   当前 core.autocrlf = '{current_autocrlf}'")
            
            # 只在必要时修改设置（更保守的方式）
            if current_autocrlf.lower() in ['true', 'input']:
                print(f"   设置core.autocrlf=false（从 '{current_autocrlf}' 修改）...")
                result = subprocess.run(['git', 'config', 'core.autocrlf', 'false'], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore',
                                      timeout=10, creationflags=SUBPROCESS_FLAGS)
                
                if result.returncode == 0:
                    print(f"   ✅ core.autocrlf 设置成功")
                else:
                    print(f"   ⚠️ core.autocrlf 设置失败: {result.stderr}")
            else:
                print(f"   ✅ core.autocrlf 无需修改")
            
            # 设置 core.safecrlf=false，但只在遇到CRLF问题时
            print(f"   配置core.safecrlf=false...")
            result = subprocess.run(['git', 'config', 'core.safecrlf', 'false'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                print(f"   ✅ core.safecrlf 设置成功")
            else:
                print(f"   ⚠️ core.safecrlf 设置失败: {result.stderr}")
                
            # 检查是否需要创建.gitattributes（更保守）
            gitattributes_path = os.path.join(self.git_path, '.gitattributes')
            if not os.path.exists(gitattributes_path):
                print(f"   创建.gitattributes文件...")
                self._create_gitattributes_file()
            else:
                print(f"   ✅ .gitattributes文件已存在，跳过创建")
            
            # 标记已配置，避免重复
            self._git_crlf_configured = True
            
        except Exception as e:
            print(f"   ❌ 配置Git换行符处理失败: {e}")
    
    def _create_gitattributes_file(self):
        """创建或更新.gitattributes文件来控制换行符处理"""
        try:
            gitattributes_path = os.path.join(self.git_path, '.gitattributes')
            
            # 检查文件是否已存在
            if os.path.exists(gitattributes_path):
                with open(gitattributes_path, 'r', encoding='utf-8', errors='ignore') as f:
                    existing_content = f.read()
                print(f"   📄 .gitattributes 文件已存在")
            else:
                existing_content = ""
                print(f"   📄 创建新的 .gitattributes 文件")
            
            # 定义需要添加的规则
            rules_to_add = [
                "# 设置默认行为，以防人们没有设置core.autocrlf",
                "* text=auto",
                "",
                "# 声明想要始终被规范化并转换为本地行结束的文件",
                "*.c text",
                "*.h text",
                "*.py text",
                "",
                "# 声明想要始终保持LF的文件，即使在Windows上",
                "*.sh text eol=lf",
                "",
                "# 二进制文件应该不被修改",
                "*.png binary",
                "*.jpg binary",
                "*.jpeg binary",
                "*.gif binary",
                "*.ico binary",
                "*.mov binary",
                "*.mp4 binary",
                "*.mp3 binary",
                "*.flv binary",
                "*.fla binary",
                "*.swf binary",
                "*.gz binary",
                "*.zip binary",
                "*.7z binary",
                "*.ttf binary",
                "*.eot binary",
                "*.woff binary",
                "*.pyc binary",
                "*.pdf binary",
                "*.dll binary",
                "*.exe binary",
                "*.so binary",
                "*.dylib binary",
                "",
                "# Unity特定文件",
                "*.prefab text",
                "*.unity text",
                "*.asset text",
                "*.mat text",
                "*.anim text",
                "*.controller text",
                "*.meta text",
                "*.cs text",
                "*.js text",
                "",
                "# 特殊的Unity二进制文件",
                "*.fbx binary",
                "*.mesh binary",
                "*.terraindata binary",
                "*.cubemap binary",
                "*.unitypackage binary"
            ]
            
            # 检查是否需要添加规则
            needs_update = False
            rules_content = "\n".join(rules_to_add)
            
            if "* text=auto" not in existing_content:
                needs_update = True
            
            if needs_update:
                # 如果文件存在但需要更新，在末尾添加规则
                if existing_content and not existing_content.endswith('\n'):
                    existing_content += '\n'
                
                new_content = existing_content + '\n' + rules_content + '\n'
                
                with open(gitattributes_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(new_content)
                print(f"   ✅ .gitattributes 文件已更新")
            else:
                print(f"   ✅ .gitattributes 文件已包含必要规则")
                
        except Exception as e:
            print(f"   ❌ 创建.gitattributes文件失败: {e}")

    def _detect_submodule(self) -> bool:
        """检测当前仓库是否为子模块"""
        try:
            # 检查是否存在.gitmodules文件（在父仓库中）
            parent_dir = os.path.dirname(self.git_path)
            while parent_dir and parent_dir != os.path.dirname(parent_dir):
                gitmodules_path = os.path.join(parent_dir, '.gitmodules')
                if os.path.exists(gitmodules_path):
                    return True
                parent_dir = os.path.dirname(parent_dir)
            
            # 检查Git配置中是否有子模块相关信息
            result = subprocess.run(['git', 'config', '--get', 'remote.origin.url'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                # 如果URL包含子仓库的典型特征
                if 'CommonResource' in url or 'assetruntime' in url.lower():
                    return True
            
            return False
        except Exception:
            return False
    
    def _calculate_target_path(self, source_file: str, target_base_path: str) -> str:
        """
        计算源文件在目标Git仓库中的路径
        
        Args:
            source_file: 源文件路径
            target_base_path: 目标基础路径（已经是完整的Git仓库路径）
            
        Returns:
            str: 目标文件路径，如果无法计算则返回None
        """
        try:
            print(f"📁 [DEBUG] ==========路径计算详细分析==========")
            print(f"   源文件: {source_file}")
            print(f"   目标基础路径: {target_base_path}")
            
            # 检查target_base_path是否已经包含CommonResource
            target_base_normalized = os.path.normpath(target_base_path).replace('/', '\\')
            print(f"   标准化目标基础路径: {target_base_normalized}")
            
            if 'CommonResource' in target_base_normalized:
                print(f"   ✅ 目标路径已包含CommonResource，无需额外添加")
            else:
                print(f"   ⚠️ 目标路径不包含CommonResource")
            
            if not self.svn_path:
                # 如果没有SVN路径，直接使用文件名
                filename = os.path.basename(source_file)
                result = os.path.join(target_base_path, filename)
                print(f"   ⚠️ 没有SVN路径，使用文件名: {result}")
                print(f"   ========================================")
                return result
            
            # 规范化路径分隔符
            source_path = os.path.normpath(source_file).replace('/', '\\')
            svn_path = os.path.normpath(self.svn_path).replace('/', '\\')
            
            print(f"   标准化源文件路径: {source_path}")
            print(f"   标准化SVN路径: {svn_path}")
            
            # 检查文件是否在SVN仓库内
            if not source_path.startswith(svn_path):
                # 文件不在SVN仓库内，直接使用文件名
                filename = os.path.basename(source_file)
                result = os.path.join(target_base_path, filename)
                print(f"   ⚠️ 文件不在SVN仓库内，使用文件名: {result}")
                print(f"   ========================================")
                return result
            
            # 计算相对于SVN仓库根的路径
            relative_to_svn = source_path[len(svn_path):].lstrip('\\')
            print(f"   相对于SVN的路径: {relative_to_svn}")
            
            # 🔧 关键修复：查找Assets目录，但保留Assets之后的完整路径结构
            assets_index = relative_to_svn.find('Assets\\')
            if assets_index == -1:
                # 没有Assets目录，直接使用文件名
                filename = os.path.basename(source_file)
                result = os.path.join(target_base_path, filename)
                print(f"   ⚠️ 没有Assets目录，使用文件名: {result}")
                print(f"   ========================================")
                return result
            
            # 🎯 重要：提取从Assets开始的完整路径（包含所有中间目录）
            # 比如：Assets\Resources\minigame\entity\100028\file.prefab
            assets_full_path = relative_to_svn[assets_index:]
            print(f"   Assets完整路径: {assets_full_path}")
            
            # 🔄 应用路径映射规则
            mapped_assets_path = self.apply_path_mapping(assets_full_path)
            if mapped_assets_path != assets_full_path:
                print(f"   🎯 路径映射生效:")
                print(f"      原始路径: {assets_full_path}")
                print(f"      映射路径: {mapped_assets_path}")
                assets_full_path = mapped_assets_path
            else:
                print(f"   ⚠️ 未应用路径映射，使用原始路径")
            
            # 分析路径结构
            path_parts = assets_full_path.split('\\')
            print(f"   路径组成部分: {path_parts}")
            
            # 验证路径结构是否合理
            if len(path_parts) < 2:
                print(f"   ⚠️ 路径结构异常，部分太少")
            else:
                print(f"   📂 Assets目录: {path_parts[0]}")
                if len(path_parts) > 1:
                    print(f"   📂 第二级目录: {path_parts[1]}")
                if len(path_parts) > 2:
                    print(f"   📂 第三级目录: {path_parts[2]}")
                if len(path_parts) > 3:
                    print(f"   📂 更深层目录: {' -> '.join(path_parts[3:])}")
            
            # 构建最终目标路径：target_base_path + 映射后的Assets路径
            # 这样可以保证正确的路径结构，如：Assets\Resources\minigame\entity\100028
            target_path = os.path.join(target_base_path, assets_full_path)
            
            print(f"   🎯 最终目标路径: {target_path}")
            
            # 验证路径是否合理
            if target_path.count('CommonResource') > 1:
                print(f"   ❌ 警告：检测到重复的CommonResource目录！")
                print(f"       这可能是路径计算错误")
            else:
                print(f"   ✅ 路径验证通过，无重复目录")
            
            # 验证编辑器资源路径结构
            if 'Assets\\Resources\\' in target_path:
                print(f"   ✅ 检测到标准编辑器 Resources路径结构")
            elif 'Assets\\' in target_path and 'Resources' not in target_path:
                print(f"   ⚠️ 注意：路径中包含Assets但没有Resources目录")
                print(f"       这可能是特殊的编辑器资源类型")
            
            print(f"   ========================================")
            
            return target_path
            
        except Exception as e:
            print(f"   ❌ 路径计算异常: {e}")
            print(f"   ========================================")
            return None

    def test_path_mapping(self, test_file_path: str) -> str:
        """
        测试路径映射功能 - 用于调试
        
        Args:
            test_file_path: 测试文件路径
            
        Returns:
            str: 映射后的目标路径
        """
        print(f"🧪 [TEST] ========== 路径映射测试 ==========")
        print(f"   测试文件: {test_file_path}")
        print(f"   当前SVN路径配置: {self.svn_path}")
        print(f"   当前Git路径配置: {self.git_path}")
        
        # 🔥 新增：直接测试路径映射规则
        print(f"\n🔍 [TEST] 直接测试路径映射规则:")
        
        # 测试几个关键路径
        test_paths = [
            "Assets\\entity\\100060\\test.prefab",
            "Assets\\remotes\\entity\\100060\\test.prefab", 
            "Assets\\Resources\\minigame\\entity\\100060\\test.prefab",
            "Assets\\Resources\\minigame\\remotes\\entity\\100060\\test.prefab"
        ]
        
        if test_file_path not in test_paths:
            test_paths.insert(0, test_file_path)
        
        for path in test_paths:
            print(f"\n   📝 测试路径: {path}")
            mapped = self.apply_path_mapping(path)
            print(f"   📤 映射结果: {mapped}")
            print(f"   {'✅ 正确' if self._is_mapping_correct(path, mapped) else '❌ 可能有问题'}")
        
        # 原有的完整路径计算测试
        print(f"\n🎯 [TEST] 完整路径计算测试:")
        target_path = self._calculate_target_path(test_file_path, self.git_path)
        
        print(f"   🎯 最终目标路径: {target_path}")
        print(f"   ==========================================")
        
        return target_path
    
    def _is_mapping_correct(self, original_path: str, mapped_path: str) -> bool:
        """验证路径映射是否正确"""
        # 检查entity路径映射
        if "\\entity\\" in original_path and not "\\remotes\\entity\\" in original_path:
            return "\\Resources\\minigame\\entity\\" in mapped_path and "\\remotes\\entity\\" not in mapped_path
        
        # 检查remotes/entity路径映射  
        if "\\remotes\\entity\\" in original_path:
            return "\\Resources\\minigame\\remotes\\entity\\" in mapped_path
            
        return True  # 其他路径暂不验证
    
    def _calculate_safe_deletion_targets(self, replace_folders: List[dict], source_files: List[str]) -> List[dict]:
        """
        🛡️ 安全计算需要删除的目标文件夹
        
        关键安全原则：
        1. 只删除与当前提交文件直接相关的目标文件夹
        2. 通过路径映射验证删除目标的正确性
        3. 避免删除无关的文件夹
        
        Args:
            replace_folders: 标记为替换模式的文件夹信息
            source_files: 当前要提交的源文件列表
            
        Returns:
            List[dict]: 经过安全验证的删除目标列表
        """
        print(f"🛡️ [SAFE_DELETE] ========== 安全删除目标计算 ==========")
        
        safe_deletions = []
        
        # 1. 计算所有源文件的目标路径，建立映射关系
        source_target_mapping = {}
        target_folders = set()
        
        for source_file in source_files:
            try:
                # 计算此源文件的目标路径
                target_path = self._calculate_target_path(source_file, self.git_path)
                if target_path:
                    source_target_mapping[source_file] = target_path
                    
                    # 提取目标文件夹路径
                    target_dir = os.path.dirname(target_path)
                    target_folders.add(target_dir)
                    
                    print(f"   📝 映射: {os.path.basename(source_file)} -> {target_dir}")
                    
            except Exception as e:
                print(f"   ⚠️ 无法计算目标路径: {source_file} - {e}")
        
        print(f"   📊 当前提交涉及 {len(target_folders)} 个目标文件夹")
        
        # 2. 对每个替换文件夹进行安全验证
        for folder_info in replace_folders:
            folder_name = folder_info.get('folder_name', '未知')
            target_folder_path = folder_info.get('target_path', '')
            
            print(f"\n   🔍 验证替换文件夹: {folder_name}")
            print(f"      声明的目标路径: {target_folder_path}")
            
            if not target_folder_path or not os.path.exists(target_folder_path):
                print(f"      ❌ 跳过：目标路径不存在")
                continue
            
            # 🚨 增强的安全检查：更精确的替换模式验证
            is_safe_to_delete = False
            related_files = []
            deletion_reason = ""
            
            # 检查是否有源文件会映射到这个目标文件夹或其子文件夹
            normalized_target = os.path.normpath(target_folder_path).replace('\\', '/').lower()
            
            # 方法1：检查直接文件夹映射关系
            for source_file, target_path in source_target_mapping.items():
                target_dir = os.path.normpath(os.path.dirname(target_path)).replace('\\', '/').lower()
                
                # 🚨 改进：更精确的路径匹配逻辑
                if self._is_target_folder_match(normalized_target, target_dir):
                    is_safe_to_delete = True
                    related_files.append(os.path.basename(source_file))
                    print(f"      ✅ 关联文件: {os.path.basename(source_file)} -> {target_dir}")
            
            # 方法2：🚨 严格的用户替换确认（增加多重安全验证）
            if not is_safe_to_delete:
                # 🛡️ 安全检查1：必须有明确的文件夹名称匹配
                if not folder_name or folder_name == '未知':
                    print(f"      ❌ 安全阻止：文件夹名称未知，拒绝删除")
                else:
                    # 🛡️ 安全检查2：检查目标路径是否确实存在文件
                    if os.path.exists(target_folder_path) and os.listdir(target_folder_path):
                        existing_files = [f for f in os.listdir(target_folder_path) if os.path.isfile(os.path.join(target_folder_path, f))]
                        if existing_files:
                            # 🛡️ 安全检查3：验证文件夹名称是否出现在目标路径中
                            if folder_name.lower() in target_folder_path.lower():
                                # 🛡️ 安全检查4：检查是否是合理的替换操作
                                if self._is_reasonable_replacement(folder_name, target_folder_path, existing_files):
                                    print(f"      🔍 安全验证通过：目标文件夹存在 {len(existing_files)} 个文件，且路径匹配")
                                    is_safe_to_delete = True
                                    deletion_reason = f"用户明确选择替换模式，目标文件夹有 {len(existing_files)} 个文件（经过安全验证）"
                                    related_files = [f"目标文件夹中的 {len(existing_files)} 个文件"]
                                else:
                                    print(f"      ❌ 安全阻止：替换操作不合理，拒绝删除")
                            else:
                                print(f"      ❌ 安全阻止：文件夹名称与目标路径不匹配，拒绝删除")
                                print(f"         文件夹名称: {folder_name}")
                                print(f"         目标路径: {target_folder_path}")
                    else:
                        print(f"      ℹ️ 目标文件夹为空或不存在，无需删除")
            
            if is_safe_to_delete:
                # 额外的路径合理性检查
                if self._is_deletion_path_reasonable(target_folder_path, folder_name):
                    final_reason = deletion_reason if deletion_reason else f"与当前提交的 {len(related_files)} 个文件相关"
                    safe_deletions.append({
                        'folder_name': folder_name,
                        'target_path': target_folder_path,
                        'related_files': related_files,
                        'reason': final_reason
                    })
                    print(f"      ✅ 安全验证通过：将删除 {folder_name}")
                    print(f"      📝 删除原因: {final_reason}")
                else:
                    print(f"      ❌ 路径合理性检查失败，跳过删除")
            else:
                print(f"      ❌ 安全验证失败：目标文件夹为空或与当前提交无关，跳过删除")
        
        print(f"\n   📊 安全验证结果：{len(safe_deletions)}/{len(replace_folders)} 个文件夹通过验证")
        print(f"   ==========================================")
        
        return safe_deletions
    
    def _is_target_folder_match(self, normalized_target: str, target_dir: str) -> bool:
        """检查目标文件夹是否匹配"""
        # 精确匹配
        if target_dir == normalized_target:
            return True
        
        # 检查是否是子文件夹（目标文件在要删除的文件夹内）
        if target_dir.startswith(normalized_target + '/'):
            return True
        
        # 检查是否是父文件夹（要删除的是目标文件的子文件夹）
        if normalized_target.startswith(target_dir + '/'):
            return True
        
        return False
    
    def _is_reasonable_replacement(self, folder_name: str, target_folder_path: str, existing_files: list) -> bool:
        """
        🛡️ 验证替换操作是否合理
        
        Args:
            folder_name: 源文件夹名称
            target_folder_path: 目标文件夹路径
            existing_files: 目标文件夹中的现有文件列表
            
        Returns:
            bool: True表示替换操作合理，False表示不合理
        """
        try:
            # 🚨 安全检查1：文件夹名称不能为空或过于通用
            if not folder_name or len(folder_name.strip()) < 2:
                print(f"      ❌ 不合理：文件夹名称过短或为空")
                return False
            
            # 🚨 安全检查2：禁止删除过于通用的文件夹名称
            dangerous_names = ['assets', 'resources', 'common', 'shared', 'data', 'files', 'temp', 'tmp']
            if folder_name.lower() in dangerous_names:
                print(f"      ❌ 不合理：文件夹名称过于通用，可能误删重要文件")
                return False
            
            # 🚨 安全检查3：检查文件数量是否合理（避免删除大量文件）
            if len(existing_files) > 100:  # 超过100个文件需要额外确认
                print(f"      ⚠️ 警告：目标文件夹包含 {len(existing_files)} 个文件，数量较多")
                # 可以在这里添加更严格的检查
                return False
            
            # 🚨 安全检查4：检查路径深度是否合理
            path_parts = target_folder_path.replace('\\', '/').split('/')
            if len(path_parts) < 4:  # 路径太短可能是根目录
                print(f"      ❌ 不合理：目标路径层级太浅 ({len(path_parts)} 层)，可能是重要目录")
                return False
            
            # 🚨 安全检查5：检查是否包含重要的项目结构
            important_indicators = ['assets', 'resources', 'entity', 'prefab', 'material', 'texture']
            has_important_indicator = any(indicator in target_folder_path.lower() for indicator in important_indicators)
            
            if not has_important_indicator:
                print(f"      ❌ 不合理：目标路径不包含项目结构标识符，可能不是正确的替换目标")
                return False
            
            print(f"      ✅ 替换操作合理性验证通过")
            return True
            
        except Exception as e:
            print(f"      ❌ 替换合理性检查异常: {e}")
            return False
    
    def _is_deletion_path_reasonable(self, target_path: str, folder_name: str) -> bool:
        """验证删除路径是否合理，避免删除重要系统文件夹"""
        
        # 转换为标准化路径
        normalized_path = os.path.normpath(target_path).replace('/', '\\').lower()
        
        # 🚨 严格的安全检查：禁止删除的路径模式
        forbidden_patterns = [
            # 系统关键路径
            'c:\\windows', 'c:\\program files', 'c:\\users', 'c:\\system32',
            # Git仓库根目录和配置
            '\\.git\\', '\\.git$', '\\.gitignore', '\\.gitattributes',
            # 过于宽泛的根目录（但允许具体的子目录）
            '\\assets$', '\\resources$', '\\commonresource$',
            # 根驱动器
            '^[a-z]:$', '^[a-z]:\\$',
            # 项目根目录
            '\\assets\\$', '\\resources\\$',
            # 重要的开发工具目录
            'node_modules', '.vscode', '.idea', '__pycache__'
        ]
        
        for pattern in forbidden_patterns:
            if pattern.endswith('$'):
                # 精确匹配
                if normalized_path.lower().endswith(pattern[:-1]):
                    print(f"      ⚠️ 禁止删除：路径过于宽泛 ({pattern})")
                    return False
            else:
                # 包含匹配
                if pattern in normalized_path:
                    print(f"      ⚠️ 禁止删除：包含敏感路径 ({pattern})")
                    return False
        
        # ✅ 必须包含合理的子路径结构
        required_patterns = ['assets', 'resources', 'minigame']
        pattern_count = sum(1 for pattern in required_patterns if pattern in normalized_path)
        
        if pattern_count < 2:
            print(f"      ⚠️ 路径结构不合理：缺少必要的子路径结构")
            return False
        
        # ✅ 路径长度检查（避免删除过短的路径）
        path_parts = [part for part in normalized_path.split('\\') if part]
        if len(path_parts) < 4:  # 至少应该有4层目录结构
            print(f"      ⚠️ 路径过短：{len(path_parts)} 层，最少需要4层")
            return False
        
        print(f"      ✅ 路径合理性检查通过")
        return True
    
    def _execute_safe_deletions(self, safe_deletions: List[dict]) -> List[dict]:
        """
        🔧 执行安全删除操作
        
        Args:
            safe_deletions: 经过安全验证的删除目标列表
            
        Returns:
            List[dict]: 删除操作结果
        """
        print(f"🗑️ [SAFE_DELETE] ========== 执行安全删除 ==========")
        
        results = []
        
        for deletion_info in safe_deletions:
            folder_name = deletion_info['folder_name']
            target_path = deletion_info['target_path']
            related_files = deletion_info['related_files']
            
            print(f"   🗑️ 处理替换文件夹: {folder_name}")
            print(f"      目标路径: {target_path}")
            print(f"      替换原因: {deletion_info.get('reason', '未知')}")
            
            result = {
                'folder_name': folder_name,
                'success': False,
                'error': None,
                'deleted_path': target_path,
                'deleted_files_count': 0
            }
            
            try:
                if not os.path.exists(target_path):
                    result['success'] = True
                    result['error'] = '文件夹不存在，无需删除'
                    print(f"      ℹ️ 文件夹不存在，无需删除")
                    results.append(result)
                    continue
                
                # 🔍 统计要删除的文件数量
                files_to_delete = []
                for root, dirs, files in os.walk(target_path):
                    files_to_delete.extend([os.path.join(root, f) for f in files])
                
                result['deleted_files_count'] = len(files_to_delete)
                print(f"      📊 发现 {len(files_to_delete)} 个文件待删除")
                
                # 🔧 先尝试使用Git删除（更安全，会被Git跟踪）
                relative_path = os.path.relpath(target_path, self.git_path).replace('\\', '/')
                print(f"      🔧 使用Git删除: {relative_path}")
                
                delete_result = subprocess.run(
                    ['git', 'rm', '-r', relative_path], 
                    cwd=self.git_path, 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=60,  # 增加超时时间，处理大文件夹
                    creationflags=SUBPROCESS_FLAGS
                )
                
                if delete_result.returncode == 0:
                    result['success'] = True
                    result['error'] = None
                    print(f"      ✅ Git删除成功，清理了 {result['deleted_files_count']} 个文件")
                else:
                    # Git删除失败，尝试直接删除（仅作为后备方案）
                    print(f"      ⚠️ Git删除失败，尝试直接删除: {delete_result.stderr}")
                    
                    import shutil
                    shutil.rmtree(target_path, ignore_errors=True)
                    
                    if not os.path.exists(target_path):
                        result['success'] = True
                        result['error'] = None
                        print(f"      ✅ 直接删除成功，清理了 {result['deleted_files_count']} 个文件")
                        print(f"      ⚠️ 注意：文件已从磁盘删除，但未通过Git跟踪")
                    else:
                        result['success'] = False
                        result['error'] = '删除失败，文件夹仍然存在'
                        print(f"      ❌ 删除失败，文件夹仍然存在")
                        
                results.append(result)
                
            except Exception as e:
                result['success'] = False
                result['error'] = f"删除操作异常: {str(e)}"
                print(f"      ❌ 删除操作异常: {str(e)}")
                results.append(result)
        
        print(f"🗑️ [SAFE_DELETE] ========== 删除操作完成 ==========")
        return results


class BranchSwitchThread(QThread):
    """分支切换线程"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    switch_completed = pyqtSignal(bool, str, str, str)  # success, selected_branch, current_branch, message
    
    def __init__(self, git_manager, selected_branch, current_branch):
        super().__init__()
        self.git_manager = git_manager
        self.selected_branch = selected_branch
        self.current_branch = current_branch
    
    def run(self):
        """执行分支切换"""
        try:
            self.progress_updated.emit(10)
            self.status_updated.emit(f"🔄 准备切换分支: {self.current_branch} -> {self.selected_branch}")
            
            # 模拟准备阶段
            self.msleep(500)  # 0.5秒
            self.progress_updated.emit(30)
            
            # 执行分支切换
            self.status_updated.emit("🌐 正在获取远程分支信息...")
            self.progress_updated.emit(50)
            
            success = self.git_manager.checkout_branch(self.selected_branch)
            
            self.progress_updated.emit(90)
            self.msleep(300)  # 0.3秒
            
            self.progress_updated.emit(100)
            
            if success:
                message = f"成功切换到分支: {self.selected_branch}"
                self.status_updated.emit(f"✅ {message}")
            else:
                message = f"无法切换到分支: {self.selected_branch}"
                self.status_updated.emit(f"❌ {message}")
            
            self.switch_completed.emit(success, self.selected_branch, self.current_branch, message)
            
        except Exception as e:
            error_msg = f"分支切换线程异常: {str(e)}"
            self.status_updated.emit(f"❌ {error_msg}")
            self.switch_completed.emit(False, self.selected_branch, self.current_branch, error_msg)


class ResourceChecker(QThread):
    """资源检查线程 - 基于JSON格式文件的检查逻辑"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    check_completed = pyqtSignal(bool, str)
    detailed_report = pyqtSignal(dict)
    git_sync_required = pyqtSignal(dict)  # 新增：Git同步需求信号
    local_deleted_warning = pyqtSignal(list)  # 本地删除但Git存在的警告
    
    def __init__(self, upload_files, git_manager, target_directory, folder_upload_modes=None):
        super().__init__()
        self.upload_files = upload_files
        self.git_manager = git_manager
        self.target_directory = target_directory
        self.folder_upload_modes = folder_upload_modes or {}
        self.analyzer = ResourceDependencyAnalyzer()
        
        # 需要检查GUID引用的文件类型（按优先级排序）
        self.high_priority_types = {'.mat', '.controller', '.prefab'}  # 复杂GUID引用
        self.medium_priority_types = {'.asset'}  # 可能有引用
        self.low_priority_types = {'.mesh', '.skeleton', '.skAnim', '.animmask'}  # 通常独立
        
        # 图片文件类型
        self.image_types = {'.png', '.jpg', '.jpeg', '.tga', '.bmp'}
        
        # 系统内置GUID（不需要检查的）
        self.builtin_guids = {
            "0000000000000000e000000000000000",  # Built-in Shader
            "0000000000000000f000000000000000",  # Built-in Extra
        }
        
        # 本地删除但Git存在的引用列表
        self.local_deleted_but_git_exists = []

    def run(self):
        """运行检查任务"""
        try:
            self.status_updated.emit("开始检查资源...")
            
            # 🔄 新增步骤：重置和拉取仓库
            self.status_updated.emit("🔄 重置Git仓库并拉取最新代码...")
            self.progress_updated.emit(1)
            
            reset_success, reset_message = self.git_manager.reset_and_pull_repository()
            if not reset_success:
                # 如果重置和拉取失败，停止检查
                error_msg = f"❌ 仓库重置和拉取失败: {reset_message}"
                self.status_updated.emit(error_msg)
                self.check_completed.emit(False, error_msg)
                return
            
            self.status_updated.emit(f"✅ 仓库重置和拉取完成: {reset_message}")
            self.progress_updated.emit(3)
            
            # 🔍 第一步：检查Git同步状态（重置后应该已经同步）
            self.status_updated.emit("🔍 验证Git仓库同步状态...")
            self.progress_updated.emit(4)
            
            git_sync_result = self._check_git_sync_status()
            if not git_sync_result['is_up_to_date']:
                # 理论上重置和拉取后应该已经同步，如果还是不同步，可能有其他问题
                warning_msg = f"⚠️ 重置拉取后仓库状态仍不同步: {git_sync_result.get('message', '未知原因')}"
                self.status_updated.emit(warning_msg)
                # 继续检查，但发出警告信号
                self.git_sync_required.emit(git_sync_result)
                # 不return，继续执行检查
            
            self.status_updated.emit("✅ Git仓库状态正常，继续检查资源...")
            self.progress_updated.emit(5)
            
            # 检查所有问题
            all_issues = []
            
            # 1. Meta文件检查
            self.status_updated.emit("检查Meta文件...")
            self.progress_updated.emit(8)
            meta_issues = self._check_meta_files()
            all_issues.extend(meta_issues)
            
            # 2. 中文字符检查
            self.status_updated.emit("检查中文字符...")
            self.progress_updated.emit(25)
            chinese_issues = self._check_chinese_characters()
            all_issues.extend(chinese_issues)
            
            # 3. 图片尺寸检查
            self.status_updated.emit("检查图片尺寸...")
            self.progress_updated.emit(40)
            image_issues = self._check_image_sizes()
            all_issues.extend(image_issues)
            
            # 4. GUID一致性检查
            self.status_updated.emit("检查GUID一致性...")
            self.progress_updated.emit(55)
            guid_issues = self._check_guid_consistency()
            all_issues.extend(guid_issues)
            
            # 5. GUID唯一性检查（新增）
            self.status_updated.emit("检查GUID唯一性...")
            self.progress_updated.emit(70)
            uniqueness_issues = self._check_guid_uniqueness()
            all_issues.extend(uniqueness_issues)
            
            # 6. GUID引用检查
            self.status_updated.emit("检查GUID引用...")
            self.progress_updated.emit(80)
            reference_issues = self._check_guid_references()
            all_issues.extend(reference_issues)
            
            # 7. 材质模板检查
            self.status_updated.emit("检查材质模板...")
            self.progress_updated.emit(85)
            template_issues = self._check_material_templates()
            all_issues.extend(template_issues)
            
            # 8. Avatar文件夹all.filelist检查
            self.status_updated.emit("检查Avatar文件夹all.filelist...")
            self.progress_updated.emit(90)
            avatar_filelist_issues = self._check_avatar_filelist()
            all_issues.extend(avatar_filelist_issues)
            
            # 9. Weapon文件夹all.filelist检查
            self.status_updated.emit("检查Weapon文件夹all.filelist...")
            self.progress_updated.emit(92)
            weapon_filelist_issues = self._check_weapon_filelist()
            all_issues.extend(weapon_filelist_issues)
            
            # 10. 预制体文件名规范检查
            self.status_updated.emit("检查预制体文件名规范...")
            self.progress_updated.emit(93)
            prefab_naming_issues = self._check_prefab_naming_convention()
            all_issues.extend(prefab_naming_issues)
            
            # 11. 图片文件扩展名大小写检查
            self.status_updated.emit("检查图片文件扩展名大小写...")
            self.progress_updated.emit(94)
            extension_case_issues = self._check_file_extension_case()
            all_issues.extend(extension_case_issues)
            
            # 12. overrideController缓存检查
            self.status_updated.emit("检查overrideController缓存...")
            self.progress_updated.emit(95)
            override_controller_issues = self._check_override_controller_cache()
            all_issues.extend(override_controller_issues)
            
            # 生成详细报告
            report = self._generate_detailed_report(all_issues, len(self.upload_files))
            self.detailed_report.emit(report)
            
            self.progress_updated.emit(100)
            
            # 区分阻塞性错误和警告/信息
            # meta_missing_git 和 guid_file_update 类型的问题是警告/信息，不阻塞推送操作
            non_blocking_types = {'meta_missing_git', 'guid_file_update', 'no_template_found'}
            blocking_issues = [issue for issue in all_issues if issue.get('type') not in non_blocking_types]
            warning_issues = [issue for issue in all_issues if issue.get('type') in non_blocking_types]
            
            if blocking_issues:
                self.check_completed.emit(False, f"发现 {len(blocking_issues)} 个阻塞性问题，请查看详细报告")
            else:
                if warning_issues:
                    # 统计不同类型的非阻塞问题
                    file_updates = len([issue for issue in warning_issues if issue.get('type') == 'guid_file_update'])
                    other_warnings = len(warning_issues) - file_updates
                    
                    if file_updates > 0 and other_warnings > 0:
                        self.check_completed.emit(True, f"检查通过！发现 {file_updates} 个文件更新和 {other_warnings} 个警告")
                    elif file_updates > 0:
                        self.check_completed.emit(True, f"检查通过！发现 {file_updates} 个文件更新（将覆盖Git中的现有版本）")
                    else:
                        self.check_completed.emit(True, f"检查通过！发现 {len(warning_issues)} 个警告（推送时会自动处理）")
                else:
                    self.check_completed.emit(True, f"所有 {len(self.upload_files)} 个文件检查通过")
                
        except Exception as e:
            self.check_completed.emit(False, f"检查过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def _check_meta_files(self) -> List[Dict[str, str]]:
        """检查Meta文件完整性 - 严格的GUID一致性检查"""
        issues = []
        
        # 检查是否有替换模式的文件夹
        has_replace_mode = False
        if hasattr(self, 'folder_upload_modes') and self.folder_upload_modes:
            for folder_info in self.folder_upload_modes.values():
                if folder_info.get('mode') == 'replace':
                    has_replace_mode = True
                    break
        
        for file_path in self.upload_files:
            try:
                if file_path.lower().endswith('.meta'):
                    # 跳过.meta文件本身
                    continue
                
                # 1. 检查SVN中是否有对应的.meta文件
                svn_meta_path = file_path + '.meta'
                svn_has_meta = os.path.exists(svn_meta_path)
                svn_guid = None
                
                if svn_has_meta:
                    # 读取SVN中的GUID
                    try:
                        svn_guid = self.analyzer.parse_meta_file(svn_meta_path)
                        if not svn_guid:
                            issues.append({
                                'file': file_path,
                                'type': 'svn_meta_no_guid',
                                'message': 'SVN中的.meta文件缺少有效GUID'
                            })
                    except Exception as e:
                        issues.append({
                            'file': file_path,
                            'type': 'svn_meta_read_error',
                            'message': f'SVN中的.meta文件读取失败: {str(e)}'
                        })
                
                # 2. 计算Git中对应的文件路径
                git_file_path = None
                git_meta_path = None
                git_has_meta = False
                git_guid = None
                
                try:
                    # 重要：与push_files_to_git保持一致，直接使用git_path作为基础路径
                    # 不再拼接target_directory，因为git_path已经是完整路径
                    git_file_path = self.git_manager._calculate_target_path(file_path, self.git_manager.git_path)
                    
                    if git_file_path:
                        git_meta_path = git_file_path + '.meta'
                        git_has_meta = os.path.exists(git_meta_path)
                        
                        if git_has_meta:
                            # 读取Git中的GUID
                            try:
                                git_guid = self.analyzer.parse_meta_file(git_meta_path)
                            except Exception as e:
                                issues.append({
                                    'file': file_path,
                                    'type': 'git_meta_read_error',
                                    'message': f'Git中的.meta文件读取失败: {str(e)}'
                                })
                
                except Exception as e:
                    issues.append({
                        'file': file_path,
                        'type': 'git_path_calc_error',
                        'message': f'计算Git路径失败: {str(e)}'
                    })
                
                # 3. 根据不同情况进行检查
                if not svn_has_meta and not git_has_meta:
                    # 两边都没有.meta文件
                    issues.append({
                        'file': file_path,
                        'type': 'meta_missing_both',
                        'message': 'SVN和Git中都缺少.meta文件',
                        'svn_path': file_path,
                        'git_path': git_file_path or '路径计算失败'
                    })
                
                elif not svn_has_meta and git_has_meta:
                    # SVN中没有，Git中有
                    if git_guid:
                        issues.append({
                            'file': file_path,
                            'type': 'meta_missing_svn',
                            'message': f'SVN中缺少.meta文件，Git中存在(GUID: {git_guid})',
                            'svn_path': file_path,
                            'git_path': git_file_path,
                            'git_guid': git_guid
                        })
                    else:
                        issues.append({
                            'file': file_path,
                            'type': 'meta_missing_svn_invalid_git',
                            'message': 'SVN中缺少.meta文件，Git中的.meta文件无效',
                            'svn_path': file_path,
                            'git_path': git_file_path
                        })
                
                elif svn_has_meta and not git_has_meta:
                    # SVN中有，Git中没有
                    if svn_guid:
                        issues.append({
                            'file': file_path,
                            'type': 'meta_missing_git',
                            'message': f'Git中缺少.meta文件，SVN中存在(GUID: {svn_guid})',
                            'svn_path': file_path,
                            'git_path': git_file_path or '路径计算失败',
                            'svn_guid': svn_guid
                        })
                    else:
                        issues.append({
                            'file': file_path,
                            'type': 'meta_missing_git_invalid_svn',
                            'message': 'Git中缺少.meta文件，SVN中的.meta文件无效',
                            'svn_path': file_path,
                            'git_path': git_file_path or '路径计算失败'
                        })
                
                elif svn_has_meta and git_has_meta:
                    # 两边都有.meta文件，检查GUID一致性（仅在非替换模式下）
                    if not has_replace_mode:
                        if svn_guid and git_guid:
                            if svn_guid != git_guid:
                                issues.append({
                                    'file': file_path,
                                    'type': 'guid_mismatch',
                                    'message': f'GUID不一致 - SVN: {svn_guid}, Git: {git_guid}',
                                    'svn_path': file_path,
                                    'git_path': git_file_path,
                                    'svn_guid': svn_guid,
                                    'git_guid': git_guid
                                })
                            # 如果GUID一致，则通过检查，不添加问题
                        elif not svn_guid and not git_guid:
                            issues.append({
                                'file': file_path,
                                'type': 'guid_invalid_both',
                                'message': 'SVN和Git中的.meta文件都没有有效GUID',
                                'svn_path': file_path,
                                'git_path': git_file_path
                            })
                        elif not svn_guid:
                            issues.append({
                                'file': file_path,
                                'type': 'guid_invalid_svn',
                                'message': f'SVN中的.meta文件无效GUID，Git中有效(GUID: {git_guid})',
                                'svn_path': file_path,
                                'git_path': git_file_path,
                                'git_guid': git_guid
                            })
                        elif not git_guid:
                            issues.append({
                                'file': file_path,
                                'type': 'guid_invalid_git',
                                'message': f'Git中的.meta文件无效GUID，SVN中有效(GUID: {svn_guid})',
                                'svn_path': file_path,
                                'git_path': git_file_path,
                                'svn_guid': svn_guid
                            })
                    else:
                        # 替换模式下，跳过GUID一致性检查
                        # 只检查SVN中的.meta文件是否有效
                        if not svn_guid:
                            issues.append({
                                'file': file_path,
                                'type': 'guid_invalid_svn',
                                'message': f'SVN中的.meta文件无效GUID（替换模式下忽略Git中的GUID）',
                                'svn_path': file_path,
                                'git_path': git_file_path
                            })
                        
            except Exception as e:
                issues.append({
                    'file': file_path,
                    'type': 'meta_check_error',
                    'message': f'Meta文件检查失败: {str(e)}'
                })
        
        return issues

    def _check_chinese_characters(self) -> List[Dict[str, str]]:
        """检查文件名中的中文字符"""
        issues = []
        
        for file_path in self.upload_files:
            try:
                filename = os.path.basename(file_path)
                # 检查是否包含中文字符
                if any('\u4e00' <= char <= '\u9fff' for char in filename):
                    issues.append({
                        'file': file_path,
                        'type': 'chinese_filename',
                        'message': '文件名包含中文字符'
                    })
            except Exception as e:
                issues.append({
                    'file': file_path,
                    'type': 'chinese_check_error',
                    'message': f'中文字符检查失败: {str(e)}'
                })
        
        return issues

    def _check_image_sizes(self) -> List[Dict[str, str]]:
        """检查图片尺寸 - 支持Environment/Scenes特殊规则和DefaultToonMat.templatemat材质引用的贴图"""
        issues = []
        
        # 🆕 首先找到所有使用DefaultToonMat.templatemat的材质文件引用的贴图
        defaulttoon_referenced_images = self._find_defaulttoon_referenced_images()
        
        for file_path in self.upload_files:
            try:
                _, ext = os.path.splitext(file_path.lower())
                if ext in self.image_types:
                    # 🆕 检查是否在Environment/Scenes路径下（跳过2的幂次检查）
                    is_environment_scenes = self._is_environment_scenes_path(file_path)
                    
                    # 🆕 检查是否被DefaultToonMat.templatemat材质引用
                    is_defaulttoon_referenced = file_path in defaulttoon_referenced_images
                    
                    # 如果满足任一条件，跳过2的次幂检查
                    skip_power_of_2_check = is_environment_scenes or is_defaulttoon_referenced
                    
                    if skip_power_of_2_check:
                        if is_environment_scenes:
                            print(f"🔍 [DEBUG] 检测到Environment/Scenes贴图文件: {os.path.basename(file_path)}")
                            print(f"   完整路径: {file_path}")
                            print(f"   ✅ 跳过2的幂次检查（Environment/Scenes特殊规则）")
                        if is_defaulttoon_referenced:
                            print(f"🔍 [DEBUG] 检测到DefaultToonMat材质引用的贴图: {os.path.basename(file_path)}")
                            print(f"   完整路径: {file_path}")
                            print(f"   ✅ 跳过2的幂次检查（DefaultToonMat.templatemat特殊规则）")
                    
                    try:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            width, height = img.size
                            
                            # 🆕 只有不满足特殊规则的贴图才检查2的幂次
                            if not skip_power_of_2_check:
                                # 检查是否为2的幂次
                                if not (width & (width - 1) == 0 and width != 0):
                                    issues.append({
                                        'file': file_path,
                                        'type': 'image_width_not_power_of_2',
                                        'message': f'图片宽度({width})不是2的幂次'
                                    })
                                
                                if not (height & (height - 1) == 0 and height != 0):
                                    issues.append({
                                        'file': file_path,
                                        'type': 'image_height_not_power_of_2',
                                        'message': f'图片高度({height})不是2的幂次'
                                    })
                            
                            # 检查尺寸是否过大（这个检查对所有图片都适用）
                            if width > 2048 or height > 2048:
                                issues.append({
                                    'file': file_path,
                                    'type': 'image_too_large',
                                    'message': f'图片尺寸过大({width}x{height})'
                                })
                                
                    except ImportError:
                        # PIL不可用，跳过图片检查
                        pass
                    except Exception as e:
                        issues.append({
                            'file': file_path,
                            'type': 'image_check_error',
                            'message': f'图片检查失败: {str(e)}'
                        })
                        
            except Exception as e:
                issues.append({
                    'file': file_path,
                    'type': 'image_size_check_error',
                    'message': f'图片尺寸检查失败: {str(e)}'
                })
        
        return issues

    def _check_guid_consistency(self) -> List[Dict[str, str]]:
        """检查GUID一致性"""
        issues = []
        guid_map = {}
        
        for file_path in self.upload_files:
            try:
                meta_path = file_path + '.meta'
                if os.path.exists(meta_path):
                    guid = self.analyzer.parse_meta_file(meta_path)
                    if guid:
                        if guid in guid_map:
                            issues.append({
                                'file': file_path,
                                'type': 'guid_duplicate',
                                'message': f'GUID重复: {guid} (与{guid_map[guid]}冲突)'
                            })
                        else:
                            guid_map[guid] = file_path
                            
            except Exception as e:
                issues.append({
                    'file': file_path,
                    'type': 'guid_consistency_error',
                    'message': f'GUID一致性检查失败: {str(e)}'
                })
        
        return issues

    def _check_guid_uniqueness(self) -> List[Dict[str, str]]:
        """检查GUID唯一性 - 确保上传的资产之间和与Git仓库内文件之间的GUID都是唯一的"""
        issues = []
        
        try:
            self.status_updated.emit("🔍 开始GUID唯一性检查...")
            
            # 检查是否有替换模式的文件夹
            has_replace_mode = False
            replace_folders = []
            if hasattr(self, 'folder_upload_modes') and self.folder_upload_modes:
                for folder_info in self.folder_upload_modes.values():
                    if folder_info.get('mode') == 'replace':
                        has_replace_mode = True
                        replace_folders.append(folder_info.get('folder_name', '未知文件夹'))
            
            if has_replace_mode:
                self.status_updated.emit(f"🔄 检测到替换模式文件夹: {', '.join(replace_folders)}")
                self.status_updated.emit("🔄 替换模式：仍需检查所有GUID冲突")
                self.status_updated.emit("   即使替换模式，也要遍历检查所有Git文件的GUID冲突")
            
            # 第一步：预处理，建立文件映射关系
            self.status_updated.emit("分析文件结构...")
            meta_files = set()  # 所有需要处理的meta文件
            file_to_meta = {}   # 资源文件 -> meta文件的映射
            
            for file_path in self.upload_files:
                if file_path.lower().endswith('.meta'):
                    # 直接的meta文件
                    meta_files.add(file_path)
                else:
                    # 资源文件，查找对应的meta文件
                    meta_path = file_path + '.meta'
                    if os.path.exists(meta_path):
                        meta_files.add(meta_path)
                        file_to_meta[file_path] = meta_path
            
            self.status_updated.emit(f"发现 {len(meta_files)} 个meta文件需要检查")
            
            # 第二步：收集所有GUID及其对应的meta文件
            self.status_updated.emit("收集GUID信息...")
            guid_to_meta = {}  # {guid: meta_file_path}
            meta_to_guid = {}  # {meta_file_path: guid}
            guid_duplicates = {}  # {guid: [meta_file_path1, meta_file_path2, ...]}
            
            for meta_file in meta_files:
                try:
                    guid = self.analyzer.parse_meta_file(meta_file)
                    if guid:
                        meta_to_guid[meta_file] = guid
                        
                        if guid in guid_to_meta:
                            # 发现重复GUID
                            if guid not in guid_duplicates:
                                guid_duplicates[guid] = [guid_to_meta[guid]]
                            guid_duplicates[guid].append(meta_file)
                        else:
                            guid_to_meta[guid] = meta_file
                        
                        self.status_updated.emit(f"找到GUID: {guid} ({os.path.basename(meta_file)})")
                    else:
                        # GUID解析失败，但这会在meta文件检查中处理
                        pass
                        
                except Exception as e:
                    self.status_updated.emit(f"❌ 解析meta文件失败: {os.path.basename(meta_file)} - {e}")
                    # 找到对应的资源文件用于报告
                    resource_file = meta_file[:-5] if meta_file.endswith('.meta') else meta_file
                    issues.append({
                        'file': resource_file,
                        'type': 'guid_parse_error',
                        'message': f'GUID解析失败: {str(e)}'
                    })
            
            self.status_updated.emit(f"收集到 {len(guid_to_meta)} 个唯一GUID")
            
            # 第三步：检查内部重复
            if guid_duplicates:
                self.status_updated.emit(f"发现 {len(guid_duplicates)} 个重复GUID")
                for guid, meta_files_list in guid_duplicates.items():
                    self.status_updated.emit(f"⚠️ GUID重复: {guid} (涉及{len(meta_files_list)}个文件)")
                    
                    # 为每个重复的GUID创建问题记录
                    # 使用第一个meta文件作为主要问题记录
                    main_meta = meta_files_list[0]
                    main_resource = main_meta[:-5] if main_meta.endswith('.meta') else main_meta
                    
                    # 构建重复文件列表（显示资源文件名而不是meta文件名）
                    duplicate_resources = []
                    for meta_file in meta_files_list:
                        resource_file = meta_file[:-5] if meta_file.endswith('.meta') else meta_file
                        duplicate_resources.append(os.path.basename(resource_file))
                    
                    issues.append({
                        'file': main_resource,
                        'type': 'guid_duplicate_internal',
                        'guid': guid,
                        'files': meta_files_list,
                        'file_count': len(meta_files_list),
                        'message': f'GUID重复 ({guid}): 在{len(meta_files_list)}个上传文件中重复出现: {", ".join(duplicate_resources)}'
                    })
            else:
                self.status_updated.emit("✅ 未发现内部GUID重复")
            
            # 第四步：检查与Git仓库的冲突（智能替换模式处理）
            self.status_updated.emit("扫描Git仓库中的GUID...")
            git_guids = self._get_git_repository_guids()
            self.status_updated.emit(f"Git仓库扫描完成，共找到 {len(git_guids)} 个GUID")
            
            git_conflicts = []
            file_updates = []
            debug_count = 0  # 限制调试输出
            
            if has_replace_mode:
                self.status_updated.emit("🔄 替换模式：仍需检查所有GUID冲突")
                self.status_updated.emit("   即使是替换模式，也要遍历检查所有Git文件的GUID冲突")
            
            # 进行Git冲突检查（替换模式下需要智能处理）
            for guid, meta_file in guid_to_meta.items():
                if guid in git_guids:
                    resource_file = meta_file[:-5] if meta_file.endswith('.meta') else meta_file
                    git_file_info = git_guids[guid]
                    
                    # 计算上传文件的相对路径（相对于SVN根目录）
                    upload_relative_path = self._get_upload_file_relative_path(resource_file)
                    git_relative_path = git_file_info['relative_resource_path']
                    
                    # 调试信息（只输出前3个）
                    if debug_count < 3:
                        self.status_updated.emit(f"🔍 路径比较调试:")
                        self.status_updated.emit(f"   文件: {os.path.basename(resource_file)}")
                        self.status_updated.emit(f"   上传路径: '{upload_relative_path}'")
                        self.status_updated.emit(f"   Git路径: '{git_relative_path}'")
                        
                        # 显示路径映射结果
                        if hasattr(self.git_manager, 'apply_path_mapping'):
                            mapped_path = self.git_manager.apply_path_mapping(upload_relative_path)
                            self.status_updated.emit(f"   映射后路径: '{mapped_path}'")
                        
                        debug_count += 1
                    
                    # 🚨 关键修复：替换模式下仍需检查所有GUID冲突
                    # 用户需求：即使替换模式也要遍历检查所有GUID，警告报错
                    will_be_deleted = False
                    if has_replace_mode:
                        # 检查Git中的文件是否会被替换模式删除（仅用于判断类型）
                        will_be_deleted = self._will_be_deleted_by_replace_mode(
                            git_relative_path, replace_folders
                        )
                        if will_be_deleted:
                            self.status_updated.emit(f"🔄 替换模式：文件 {git_relative_path} 将被删除，但仍检查GUID冲突")
                    
                    # 无论替换模式与否，都进行GUID冲突检查
                    # 路径比较 - 使用映射
                    if self._compare_file_paths(upload_relative_path, git_relative_path):
                        # 同一文件的更新（或替换模式下的同路径文件）
                        update_type = "文件更新"
                        if has_replace_mode and will_be_deleted:
                            update_type = "替换模式更新"
                        
                        file_updates.append({
                            'guid': guid,
                            'meta_file': meta_file,
                            'resource_file': resource_file,
                            'upload_path': upload_relative_path,
                            'git_path': git_relative_path,
                            'update_type': update_type
                        })
                        self.status_updated.emit(f"📝 {update_type}: {guid} ({os.path.basename(resource_file)})")
                    else:
                        # 真正的GUID冲突 - 不同文件使用相同GUID
                        svn_filename = os.path.basename(resource_file)
                        git_filename = git_file_info['resource_name']
                        
                        # 🎯 重点：无论替换模式与否，都要报告GUID冲突
                        conflict_type = "GUID冲突"
                        if has_replace_mode and will_be_deleted:
                            conflict_type = "GUID冲突(目标将被替换)"
                        elif has_replace_mode:
                            conflict_type = "GUID冲突(不同目录)"
                        
                        git_conflicts.append({
                            'guid': guid,
                            'meta_file': meta_file,
                            'resource_file': resource_file,
                            'upload_path': upload_relative_path,
                            'git_path': git_relative_path,
                            'git_file_name': git_file_info['resource_name'],
                            'conflict_type': conflict_type,
                            'will_be_deleted': will_be_deleted
                        })
                        self.status_updated.emit(f"⚠️ {conflict_type}: {guid} SVN:{svn_filename} Git:{git_filename} (路径:{git_relative_path})")
            
            # 记录文件更新（信息级别，不是错误）
            for update in file_updates:
                issues.append({
                    'file': update['resource_file'],
                    'type': 'guid_file_update',
                    'guid': update['guid'],
                    'upload_path': update['upload_path'],
                    'git_path': update['git_path'],
                    'severity': 'info',
                    'message': f'文件更新 ({update["guid"]}): {os.path.basename(update["resource_file"])} 将覆盖Git中的现有版本'
                })
            
            # 记录真正的GUID冲突（警告级别）
            for conflict in git_conflicts:
                svn_name = os.path.basename(conflict['resource_file'])
                git_name = conflict['git_file_name']
                    
                issues.append({
                    'file': conflict['resource_file'],
                    'type': 'guid_duplicate_git',
                    'guid': conflict['guid'],
                    'upload_path': conflict['upload_path'],
                    'git_path': conflict['git_path'],
                    'git_file_name': conflict['git_file_name'],
                    'severity': 'warning',
                    'message': f'GUID冲突 ({conflict["guid"]}): 文件名不同但GUID相同\n  SVN：{svn_name}\n  Git：{git_name}\n  建议：请统一文件名'
                })
            
            # 第五步：生成检查摘要
            total_unique_guids = len(guid_to_meta)
            internal_duplicate_count = len(guid_duplicates)
            
            # 计算GUID冲突数量和文件更新数量
            actual_git_conflict_count = len(git_conflicts)
            file_update_count = len(file_updates)
            
            self.status_updated.emit("📊 GUID唯一性检查完成:")
            self.status_updated.emit(f"   📄 上传文件GUID数量: {total_unique_guids}")
            self.status_updated.emit(f"   🔄 内部重复: {internal_duplicate_count}")
            
            self.status_updated.emit(f"   📝 文件更新: {file_update_count}")
            self.status_updated.emit(f"   ⚡ GUID冲突: {actual_git_conflict_count}")
            self.status_updated.emit(f"   🎯 Git仓库GUID数量: {len(git_guids)}")
            
            if has_replace_mode:
                self.status_updated.emit(f"   🔄 替换模式: 仍检查了所有GUID冲突（包括不同目录）")
            
            if issues:
                self.status_updated.emit(f"❌ GUID唯一性检查发现 {len(issues)} 个问题")
            else:
                self.status_updated.emit("✅ GUID唯一性检查通过，所有GUID都是唯一的")
                
        except Exception as e:
            error_msg = f"GUID唯一性检查异常: {str(e)}"
            self.status_updated.emit(f"❌ {error_msg}")
            
            # 添加详细的异常信息
            import traceback
            tb_str = traceback.format_exc()
            self.status_updated.emit(f"详细异常信息: {tb_str}")
            
            issues.append({
                'type': 'uniqueness_check_error',
                'file': 'system',
                'message': error_msg,
                'traceback': tb_str
            })
            
            # 打印到控制台以便调试
            print(f"GUID唯一性检查异常: {error_msg}")
            print(f"异常详情: {tb_str}")
        
        return issues
    
    def _will_be_deleted_by_replace_mode(self, git_relative_path: str, replace_folders: List[str]) -> bool:
        """
        判断Git中的文件是否会被替换模式删除
        
        Args:
            git_relative_path: Git中文件的相对路径
            replace_folders: 替换模式的文件夹列表
            
        Returns:
            bool: True表示会被删除，False表示不会被删除
        """
        try:
            # 标准化Git路径
            git_path_normalized = git_relative_path.replace('\\', '/').strip('/')
            
            # 获取当前提交的源文件映射信息
            if hasattr(self, 'folder_upload_modes') and self.folder_upload_modes:
                for folder_info in self.folder_upload_modes.values():
                    if folder_info.get('mode') == 'replace':
                        # 获取替换模式的目标路径
                        target_path = folder_info.get('target_path', '').replace('\\', '/').strip('/')
                        
                        # 检查Git文件是否在会被删除的目标路径下
                        if target_path and git_path_normalized.startswith(target_path):
                            self.status_updated.emit(f"🔍 替换模式分析: Git文件 '{git_path_normalized}' 在删除路径 '{target_path}' 下")
                            return True
            
            return False
            
        except Exception as e:
            self.status_updated.emit(f"⚠️ 替换模式检查异常: {e}")
            return False
    
    def _get_upload_file_relative_path(self, file_path: str) -> str:
        """获取上传文件相对于SVN根目录的路径"""
        try:
            if hasattr(self.git_manager, 'svn_path') and self.git_manager.svn_path:
                svn_path = os.path.normpath(self.git_manager.svn_path)
                file_path_normalized = os.path.normpath(file_path)
                
                # 调试信息（静态变量模拟）
                if not hasattr(self, '_debug_path_count'):
                    self._debug_path_count = 0
                if self._debug_path_count < 3:
                    self.status_updated.emit(f"🔍 路径计算调试:")
                    self.status_updated.emit(f"   SVN路径: '{svn_path}'")
                    self.status_updated.emit(f"   文件路径: '{file_path_normalized}'")
                    self._debug_path_count += 1
                
                # 计算相对路径
                if file_path_normalized.startswith(svn_path):
                    relative_path = os.path.relpath(file_path_normalized, svn_path)
                    # 标准化路径分隔符
                    result = relative_path.replace('\\', '/')
                    if hasattr(self, '_debug_path_count') and self._debug_path_count <= 3:
                        self.status_updated.emit(f"   相对路径: '{result}'")
                    return result
                else:
                    # 如果文件不在SVN路径下，返回文件名
                    result = os.path.basename(file_path)
                    self.status_updated.emit(f"   文件不在SVN路径下，返回文件名: '{result}'")
                    return result
            else:
                # 如果没有SVN路径，返回文件名
                result = os.path.basename(file_path)
                self.status_updated.emit(f"   没有SVN路径，返回文件名: '{result}'")
                return result
        except Exception as e:
            # 异常情况下返回文件名
            result = os.path.basename(file_path)
            self.status_updated.emit(f"   异常情况，返回文件名: '{result}' (错误: {e})")
            return result
    
    def _compare_file_paths(self, upload_path: str, git_path: str) -> bool:
        """比较上传文件路径与Git文件路径是否匹配（使用路径映射）
        
        返回True表示是同一个文件的更新，返回False表示是GUID冲突
        
        主要职责：
        1. 标准化路径格式
        2. 应用路径映射规则
        3. 区分"文件更新"和"GUID冲突"
        4. 处理同目录不同文件名的情况（关键修复）
        """
        try:
            # 标准化路径 - 统一使用正斜杠
            upload_normalized = upload_path.replace('\\', '/').strip('/')
            git_normalized = git_path.replace('\\', '/').strip('/')
            
            # 直接比较（原始逻辑）
            if upload_normalized.lower() == git_normalized.lower():
                return True
            
            # 使用路径映射进行比较
            mapped_upload_normalized = upload_normalized
            if hasattr(self.git_manager, 'apply_path_mapping'):
                # 将上传路径应用映射规则
                mapped_upload_path = self.git_manager.apply_path_mapping(upload_normalized)
                mapped_upload_normalized = mapped_upload_path.replace('\\', '/').strip('/')
                
                # 比较映射后的完整路径
                if mapped_upload_normalized.lower() == git_normalized.lower():
                    return True
            
            # 关键修复：检查是否只是文件名不同
            # 分离目录和文件名
            upload_dir = '/'.join(mapped_upload_normalized.split('/')[:-1])
            upload_filename = mapped_upload_normalized.split('/')[-1]
            git_dir = '/'.join(git_normalized.split('/')[:-1])  
            git_filename = git_normalized.split('/')[-1]
            
            if upload_dir.lower() == git_dir.lower() and upload_filename.lower() != git_filename.lower():
                # 同目录不同文件名的情况
                # 检查是否在替换模式下
                has_replace_mode = False
                if hasattr(self, 'folder_upload_modes') and self.folder_upload_modes:
                    for folder_info in self.folder_upload_modes.values():
                        if folder_info.get('mode') == 'replace':
                            has_replace_mode = True
                            break
                
                if has_replace_mode:
                    # 🆕 替换模式下：同GUID不同文件名视为文件重命名，允许替换
                    self.status_updated.emit(f"🔄 替换模式文件重命名检测:")
                    self.status_updated.emit(f"  上传路径: '{upload_normalized}' -> '{mapped_upload_normalized}'")
                    self.status_updated.emit(f"  Git路径: '{git_normalized}'")
                    self.status_updated.emit(f"  结果: 同目录'{upload_dir}'下文件重命名 '{git_filename}' -> '{upload_filename}' (替换模式允许)")
                    return True  # 在替换模式下视为同一文件的更新
                else:
                    # 非替换模式：同目录不同文件名仍然是GUID冲突
                    self.status_updated.emit(f"🔍 GUID冲突检测:")
                    self.status_updated.emit(f"  上传路径: '{upload_normalized}' -> '{mapped_upload_normalized}'")
                    self.status_updated.emit(f"  Git路径: '{git_normalized}'")
                    self.status_updated.emit(f"  结果: 同目录'{upload_dir}'下不同文件名 '{upload_filename}' vs '{git_filename}' -> GUID冲突")
                    return False
            
            return False
        except Exception as e:
            # 异常情况下返回False，表示不匹配（GUID冲突）
            self.status_updated.emit(f"⚠️ 路径比较异常，视为GUID冲突: {e}")
            return False

    def _check_guid_references(self) -> List[Dict[str, str]]:
        """检查GUID引用完整性"""
        issues = []
        
        try:
            self.status_updated.emit("🔍 开始GUID引用检查...")
            
            # 检查是否有替换模式的文件夹
            has_replace_mode = False
            if hasattr(self, 'folder_upload_modes') and self.folder_upload_modes:
                for folder_info in self.folder_upload_modes.values():
                    if folder_info.get('mode') == 'replace':
                        has_replace_mode = True
                        break
            
            if has_replace_mode:
                self.status_updated.emit("🔄 替换模式：仍需检查GUID引用完整性")
                self.status_updated.emit("   即使替换模式，也要检查所有GUID引用问题（包括不同目录冲突）")
            
            # 验证必要的属性和方法
            if not hasattr(self, 'analyzer'):
                raise AttributeError("缺少analyzer属性")
            
            if not hasattr(self.analyzer, '_get_git_repository_guids'):
                raise AttributeError("analyzer缺少_get_git_repository_guids方法")
            
            if not hasattr(self, '_analyze_missing_guid'):
                raise AttributeError("缺少_analyze_missing_guid方法")
            
            if not hasattr(self, '_check_internal_dependencies'):
                raise AttributeError("缺少_check_internal_dependencies方法")
            
            self.status_updated.emit("✅ 方法验证通过")
            
            # 收集SVN中所有资源的GUID
            self.status_updated.emit("扫描SVN仓库收集所有资源GUID...")
            local_guids = {}  # SVN所有文件的GUID
            upload_guids = {}  # 本次上传文件的GUID
            svn_root = None
            
            # 先收集本次上传文件的GUID
            self.status_updated.emit("收集本次上传文件的GUID...")
            for file_path in self.upload_files:
                if file_path.endswith('.meta'):
                    guid = self.analyzer.parse_meta_file(file_path)
                    if guid:
                        upload_guids[guid] = file_path
                else:
                    meta_path = file_path + '.meta'
                    if os.path.exists(meta_path):
                        guid = self.analyzer.parse_meta_file(meta_path)
                        if guid:
                            upload_guids[guid] = meta_path
            
            self.status_updated.emit(f"✅ 收集到 {len(upload_guids)} 个上传文件GUID")
            
            # 获取SVN根目录
            if hasattr(self, 'git_manager') and self.git_manager and self.git_manager.svn_path:
                svn_root = self.git_manager.svn_path
            
            if svn_root and os.path.exists(svn_root):
                self.status_updated.emit(f"SVN根目录: {svn_root}")
                
                # 扫描SVN目录
                meta_count = 0
                for root, dirs, files in os.walk(svn_root):
                    # 跳过隐藏目录
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        if file.endswith('.meta'):
                            meta_file = os.path.join(root, file)
                            resource_file = meta_file[:-5]
                            
                            # 只收集有对应资源文件的meta
                            if os.path.exists(resource_file):
                                try:
                                    guid = self.analyzer.parse_meta_file(meta_file)
                                    if guid:
                                        local_guids[guid] = meta_file
                                        meta_count += 1
                                        if meta_count % 500 == 0:
                                            self.status_updated.emit(f"已扫描 {meta_count} 个meta文件...")
                                except:
                                    pass
                
                self.status_updated.emit(f"✅ SVN扫描完成，共找到 {len(local_guids)} 个本地资源GUID")
            else:
                # 降级方案：使用上传文件的GUID
                self.status_updated.emit("⚠️ 无法获取SVN根目录，使用上传文件GUID")
                local_guids = upload_guids.copy()
            
            # 获取Git仓库中的所有GUID
            self.status_updated.emit("开始扫描Git仓库GUID...")
            git_guids_dict = self._get_git_repository_guids()
            git_guids = set(git_guids_dict.keys())  # 转换为Set以保持兼容性
            self.status_updated.emit(f"Git仓库扫描完成，共找到 {len(git_guids)} 个GUID")
            
            # 检查GUID引用
            self.status_updated.emit("分析文件间的GUID引用关系...")
            
            for file_path in self.upload_files:
                if not file_path.endswith('.meta'):
                    try:
                        # 分析文件中引用的GUID
                        referenced_guids = self.analyzer.parse_editor_asset(file_path)
                        
                        # 分析文件中引用的GUID
                        if referenced_guids:
                            self.status_updated.emit(f"🔍 文件 {os.path.basename(file_path)} 引用了 {len(referenced_guids)} 个GUID")
                            # 🚨 增强调试：显示所有引用的GUID
                            for guid in list(referenced_guids)[:5]:  # 只显示前5个
                                self.status_updated.emit(f"   📎 引用GUID: {guid}")
                                
                            for ref_guid in referenced_guids:
                                # 🚨 增强调试：显示GUID检查详情
                                in_local = ref_guid in local_guids
                                in_git = ref_guid in git_guids
                                self.status_updated.emit(f"   🔍 检查GUID {ref_guid[:8]}...: 本地={in_local}, Git={in_git}")
                                
                                # 检查本地已删除但Git存在的情况
                                if ref_guid not in local_guids and ref_guid in git_guids:
                                    git_file_info = git_guids_dict.get(ref_guid, {})
                                    git_resource_name = git_file_info.get('resource_name', 'unknown')
                                    git_relative_path = git_file_info.get('relative_resource_path', '')
                                    
                                    # 材质模板文件允许只在Git中存在
                                    if git_resource_name.lower().endswith('.templatemat'):
                                        self.status_updated.emit(f"   ✅ 材质模板(Git): {git_resource_name}")
                                        continue
                                    
                                    # 其他资源：本地删除但仍被引用，收集警告
                                    resource_ext = os.path.splitext(git_resource_name.lower())[1]
                                    if resource_ext in self.image_types:
                                        resource_type = '贴图'
                                    elif resource_ext == '.mat':
                                        resource_type = '材质'
                                    elif resource_ext == '.prefab':
                                        resource_type = 'Prefab'
                                    elif resource_ext in ['.mesh', '.skeleton']:
                                        resource_type = '模型'
                                    else:
                                        resource_type = '资源'
                                    
                                    self.local_deleted_but_git_exists.append({
                                        'referencing_file': os.path.basename(file_path),
                                        'referencing_file_path': file_path,
                                        'missing_file': git_resource_name,
                                        'missing_file_path': git_relative_path,
                                        'guid': ref_guid,
                                        'resource_type': resource_type
                                    })
                                    
                                    self.status_updated.emit(f"   ⚠️ 本地已删除但仍被引用: {git_resource_name}")
                                    continue
                                
                                # 检查引用的GUID是否存在
                                if ref_guid not in local_guids and ref_guid not in git_guids:
                                    # 🚨 新增：检查是否为本地缺失文件的GUID
                                    local_missing_info = self._check_local_missing_file(ref_guid, file_path)
                                    
                                    if local_missing_info:
                                        # 这是本地缺失文件
                                        referencing_file_name = os.path.basename(file_path)
                                        expected_file_name = os.path.basename(local_missing_info['expected_path'])
                                        
                                        issues.append({
                                            'type': 'local_file_missing',
                                            'file': file_path,
                                            'description': f'【本地文件缺失】\n' +
                                                         f'问题文件: {referencing_file_name}\n' +
                                                         f'引用GUID: {ref_guid}\n' +
                                                         f'缺失文件: {expected_file_name}\n' +
                                                         f'缺失类型: {local_missing_info["missing_type"]}\n' +
                                                         f'解决方案: {local_missing_info["solution"]}',
                                            'guid': ref_guid,
                                            'expected_file_path': local_missing_info['expected_path'],
                                            'missing_type': local_missing_info['missing_type'],
                                            'solution': local_missing_info['solution'],
                                            'message': f'{referencing_file_name} 引用了缺失的本地文件 {expected_file_name} (GUID: {ref_guid[:8]}...)'
                                        })
                                        self.status_updated.emit(f"🚨 本地文件缺失: {ref_guid}")
                                        self.status_updated.emit(f"   预期文件路径: {local_missing_info['expected_path']}")
                                        self.status_updated.emit(f"   缺失类型: {local_missing_info['missing_type']}")
                                        continue
                                    
                                    # 🚨 检查是否为Git仓库中的孤儿meta文件GUID
                                    orphan_meta_path = self._find_orphan_meta_by_guid(ref_guid)
                                    
                                    if orphan_meta_path:
                                        # 这是Git仓库中的孤儿meta文件引用
                                        resource_path = orphan_meta_path[:-5]  # 移除.meta后缀
                                        referencing_file_name = os.path.basename(file_path)
                                        orphan_meta_name = os.path.basename(orphan_meta_path)
                                        missing_resource_name = os.path.basename(resource_path)
                                        
                                        issues.append({
                                            'type': 'orphan_meta_reference',
                                            'file': file_path,
                                            'description': f'【Git仓库孤儿meta引用】\n' +
                                                         f'问题文件: {referencing_file_name}\n' +
                                                         f'引用GUID: {ref_guid}\n' +
                                                         f'孤儿meta文件: {orphan_meta_name}\n' +
                                                         f'缺失资源文件: {missing_resource_name}\n' +
                                                         f'原因: Git仓库中存在meta文件但对应的资源文件被删除\n' +
                                                         f'解决方案: 恢复Git仓库中被删除的资源文件或移除孤儿meta文件',
                                            'guid': ref_guid,
                                            'orphan_meta_path': orphan_meta_path,
                                            'missing_resource_path': resource_path,
                                            'solution': '需要恢复Git仓库中被删除的资源文件或移除对应的meta文件',
                                            'message': f'{referencing_file_name} 引用了Git仓库中的孤儿meta文件 {orphan_meta_name}'
                                        })
                                        self.status_updated.emit(f"🚨 Git孤儿meta引用: {ref_guid} -> {os.path.basename(orphan_meta_path)}")
                                        self.status_updated.emit(f"   Git中缺失资源文件: {os.path.basename(resource_path)}")
                                    else:
                                        # 分析缺失的GUID
                                        analysis = self._analyze_missing_guid(ref_guid, file_path)
                                        
                                        # 获取引用文件的GUID（如果存在）
                                        referring_file_guid = ''
                                        referring_file_guid_status = '未找到'
                                        meta_path = file_path + '.meta'
                                        
                                        if os.path.exists(meta_path):
                                            try:
                                                referring_file_guid = self.analyzer.parse_meta_file(meta_path) or ''
                                                if referring_file_guid:
                                                    referring_file_guid_status = f'找到GUID: {referring_file_guid}'
                                                    self.status_updated.emit(f"🔍 引用文件GUID: {os.path.basename(file_path)} -> {referring_file_guid}")
                                                else:
                                                    referring_file_guid_status = 'meta文件存在但无法解析GUID'
                                                    self.status_updated.emit(f"⚠️ 无法解析GUID: {os.path.basename(meta_path)}")
                                            except Exception as e:
                                                referring_file_guid_status = f'解析失败: {str(e)}'
                                                self.status_updated.emit(f"❌ 解析meta文件失败: {os.path.basename(meta_path)} - {e}")
                                        else:
                                            referring_file_guid_status = f'meta文件不存在: {os.path.basename(meta_path)}'
                                            self.status_updated.emit(f"❌ meta文件不存在: {os.path.basename(meta_path)}")
                                        
                                        issues.append({
                                            'type': 'guid_reference_missing',
                                            'file': file_path,
                                            'description': f'引用的GUID {ref_guid} 不存在',
                                            'guid': ref_guid,
                                            'referring_file_guid': referring_file_guid,
                                            'referring_file_guid_status': referring_file_guid_status,
                                            'analysis': analysis
                                        })
                                        
                                        self.status_updated.emit(f"⚠️ 缺失GUID引用: {ref_guid} 在文件 {os.path.basename(file_path)}")
                                else:
                                    # 找到引用，记录来源
                                    if ref_guid in local_guids:
                                        source = f"本地文件: {os.path.basename(local_guids[ref_guid])}"
                                    else:
                                        source = "Git仓库"
                                        
                                        # 🚨 新增：检查是否引用了远程资源（Assets\remotes\entity）
                                        remote_reference_check = self._check_remote_resource_reference(ref_guid, file_path, git_guids_dict)
                                        if remote_reference_check:
                                            # 发现引用了远程资源，添加错误
                                            referencing_file_name = os.path.basename(file_path)
                                            remote_file_info = remote_reference_check
                                            
                                            issues.append({
                                                'type': 'remote_resource_reference',
                                                'file': file_path,
                                                'description': f'【禁止引用远程资源】\n' +
                                                             f'问题文件: {referencing_file_name}\n' +
                                                             f'引用GUID: {ref_guid}\n' +
                                                             f'远程资源: {remote_file_info["resource_name"]}\n' +
                                                             f'远程路径: {remote_file_info["remote_path"]}\n' +
                                                             f'规则说明: 本地资源不允许引用Assets\\remotes\\entity目录下的文件\n' +
                                                             f'解决方案: 将远程资源复制到本地目录，或移除对远程资源的引用',
                                                'guid': ref_guid,
                                                'remote_resource_path': remote_file_info['remote_path'],
                                                'remote_resource_name': remote_file_info['resource_name'],
                                                'solution': '将远程资源复制到本地目录，或移除对远程资源的引用',
                                                'message': f'{referencing_file_name} 引用了禁止的远程资源 {remote_file_info["resource_name"]} (GUID: {ref_guid[:8]}...)'
                                            })
                                            self.status_updated.emit(f"🚨 禁止引用远程资源: {ref_guid}")
                                            self.status_updated.emit(f"   问题文件: {referencing_file_name}")
                                            self.status_updated.emit(f"   远程资源: {remote_file_info['remote_path']}")
                                            continue
                                    
                                    self.status_updated.emit(f"✅ GUID引用正常: {ref_guid} -> {source}")
                        else:
                            self.status_updated.emit(f"文件 {os.path.basename(file_path)} 没有GUID引用")
                            
                    except Exception as e:
                        error_msg = f"分析文件失败: {os.path.basename(file_path)} - {str(e)}"
                        self.status_updated.emit(f"❌ {error_msg}")
                        issues.append({
                            'type': 'analysis_error',
                            'file': file_path,
                            'description': error_msg
                        })
            
            # 🚨 新增：检查Debug_Path文件完整性
            self.status_updated.emit("检查Debug_Path文件完整性...")
            debug_path_issues = self._check_debug_path_files()
            issues.extend(debug_path_issues)
            
            # 检查内部依赖完整性（使用上传文件的GUID）
            self.status_updated.emit("检查内部依赖完整性...")
            internal_issues = self._check_internal_dependencies(upload_guids)
            issues.extend(internal_issues)
            
            # 处理本地删除但Git存在的情况
            if self.local_deleted_but_git_exists:
                self.status_updated.emit(f"⚠️ 发现 {len(self.local_deleted_but_git_exists)} 个本地删除但仍被引用的资源")
                self.status_updated.emit("将在上传前请求用户确认...")
                # 发送信号给主窗口，在上传前处理
                self.local_deleted_warning.emit(self.local_deleted_but_git_exists)
            
            if issues:
                self.status_updated.emit(f"GUID引用检查完成，发现 {len(issues)} 个问题")
            else:
                self.status_updated.emit("✅ GUID引用检查通过，所有引用都完整")
            
        except Exception as e:
            error_msg = f"GUID引用检查异常: {str(e)}"
            self.status_updated.emit(f"❌ {error_msg}")
            
            # 添加详细的异常信息
            import traceback
            tb_str = traceback.format_exc()
            self.status_updated.emit(f"详细异常信息: {tb_str}")
            
            issues.append({
                'type': 'check_error',
                'file': 'system',
                'description': error_msg,
                'traceback': tb_str
            })
            
            # 打印到控制台以便调试
            print(f"GUID引用检查异常: {error_msg}")
            print(f"异常详情: {tb_str}")
        
        return issues
    
    def _find_orphan_meta_by_guid(self, target_guid: str) -> str:
        """查找指定GUID对应的孤儿meta文件路径
        
        Args:
            target_guid: 要查找的GUID
            
        Returns:
            str: 孤儿meta文件的路径，如果找不到则返回空字符串
        """
        if not self.git_manager.git_path or not os.path.exists(self.git_manager.git_path):
            return ""
        
        try:
            # 扫描Git仓库中的所有.meta文件
            for root, dirs, files in os.walk(self.git_manager.git_path):
                for file in files:
                    if file.endswith('.meta'):
                        meta_path = os.path.join(root, file)
                        
                        try:
                            # 解析meta文件的GUID
                            guid = self.analyzer.parse_meta_file(meta_path)
                            if guid and guid.lower() == target_guid.lower():
                                # 检查对应的资源文件是否存在
                                resource_path = meta_path[:-5]  # 移除.meta后缀
                                if not os.path.exists(resource_path):
                                    # 找到孤儿meta文件
                                    return meta_path
                        except Exception:
                            # 忽略解析错误，继续查找
                            continue
        except Exception:
            # 忽略扫描错误
            pass
        
        return ""
    
    def _check_local_missing_file(self, target_guid: str, referencing_file: str) -> dict:
        """检查GUID是否对应本地缺失的文件
        
        Args:
            target_guid: 要检查的GUID
            referencing_file: 引用该GUID的文件路径
            
        Returns:
            dict: 如果是本地缺失文件，返回详细信息；否则返回None
        """
        try:
            # 获取引用文件所在的目录
            ref_file_dir = os.path.dirname(referencing_file)
            
            # 在本地上传文件列表中查找可能的文件路径
            # 1. 检查同目录下是否有对应的文件应该存在
            for upload_file in self.upload_files:
                upload_dir = os.path.dirname(upload_file)
                
                # 如果在相同或相关目录中
                if self._is_related_directory(ref_file_dir, upload_dir):
                    # 检查是否有对应的meta文件但缺少资源文件
                    if upload_file.endswith('.meta'):
                        # 这是一个meta文件，检查其GUID
                        try:
                            meta_guid = self.analyzer.parse_meta_file(upload_file)
                            if meta_guid and meta_guid.lower() == target_guid.lower():
                                # 找到了对应的meta文件，但检查资源文件是否存在
                                resource_file = upload_file[:-5]  # 移除.meta后缀
                                if not os.path.exists(resource_file):
                                    return {
                                        'expected_path': resource_file,
                                        'missing_type': '资源文件缺失（meta文件存在）',
                                        'solution': f'需要创建或恢复文件: {os.path.basename(resource_file)}'
                                    }
                        except Exception:
                            continue
                    else:
                        # 这是一个资源文件，检查其meta文件
                        meta_file = upload_file + '.meta'
                        if os.path.exists(meta_file):
                            try:
                                meta_guid = self.analyzer.parse_meta_file(meta_file)
                                if meta_guid and meta_guid.lower() == target_guid.lower():
                                    # 找到了对应的文件对，但GUID没有被正确收集
                                    # 这种情况不应该发生，可能是其他问题
                                    return None
                            except Exception:
                                continue
            
            # 2. 检查是否有预期的文件路径模式
            # 根据prefab中的Debug_Path信息推断文件位置
            if referencing_file.endswith('.prefab'):
                try:
                    with open(referencing_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 查找Debug_Path信息
                    import re
                    debug_path_pattern = rf'"Debug_Path":\s*"[^"]*{re.escape(target_guid)}[^"]*"'
                    debug_match = re.search(debug_path_pattern, content)
                    
                    if not debug_match:
                        # 尝试更宽泛的搜索
                        debug_path_matches = re.findall(r'"Debug_Path":\s*"([^"]+)"', content)
                        for debug_path in debug_path_matches:
                            # 检查这个路径是否可能对应目标GUID
                            if self._could_be_related_file(debug_path, target_guid, referencing_file):
                                expected_local_path = self._convert_debug_path_to_local(debug_path, referencing_file)
                                if expected_local_path:
                                    return {
                                        'expected_path': expected_local_path,
                                        'missing_type': '根据Debug_Path推断的缺失文件',
                                        'solution': f'需要创建文件: {os.path.basename(expected_local_path)} 及其.meta文件'
                                    }
                except Exception:
                    pass
            
            # 3. 基于文件名模式推断
            ref_filename = os.path.basename(referencing_file)
            if ref_filename.endswith('.prefab'):
                # 对于prefab文件，常见的依赖文件在同目录或Material子目录
                possible_paths = [
                    os.path.join(ref_file_dir, 'body_skin.mat'),
                    os.path.join(ref_file_dir, 'Material', 'body_skin.mat'),
                    os.path.join(ref_file_dir, '..', 'Material', 'body_skin.mat'),
                ]
                
                for possible_path in possible_paths:
                    if not os.path.exists(possible_path) and not os.path.exists(possible_path + '.meta'):
                        return {
                            'expected_path': possible_path,
                            'missing_type': '基于常见模式推断的缺失文件',
                            'solution': f'需要创建文件: {os.path.basename(possible_path)} 及其.meta文件'
                        }
        
        except Exception as e:
            self.status_updated.emit(f"⚠️ 检查本地缺失文件时出错: {e}")
        
        return None
    
    def _is_related_directory(self, dir1: str, dir2: str) -> bool:
        """检查两个目录是否相关（相同或父子关系）"""
        try:
            dir1_norm = os.path.normpath(dir1).lower()
            dir2_norm = os.path.normpath(dir2).lower()
            
            # 相同目录
            if dir1_norm == dir2_norm:
                return True
            
            # 父子关系
            if dir1_norm.startswith(dir2_norm) or dir2_norm.startswith(dir1_norm):
                return True
                
            # 兄弟目录（共同父目录）
            parent1 = os.path.dirname(dir1_norm)
            parent2 = os.path.dirname(dir2_norm)
            if parent1 == parent2:
                return True
                
        except Exception:
            pass
        
        return False
    
    def _check_remote_resource_reference(self, target_guid: str, referencing_file: str, git_guids_dict: dict) -> dict:
        """检查GUID是否引用了远程资源（Assets\\remotes\\entity目录下的文件）
        
        Args:
            target_guid: 要检查的GUID
            referencing_file: 引用该GUID的文件路径
            git_guids_dict: Git仓库中的GUID映射字典
            
        Returns:
            dict: 如果引用了远程资源，返回详细信息；否则返回None
        """
        try:
            # 检查GUID是否在Git仓库中
            if target_guid not in git_guids_dict:
                return None
                
            guid_info = git_guids_dict[target_guid]
            
            # 获取资源文件的相对路径
            relative_resource_path = guid_info.get('relative_resource_path', '')
            
            # 标准化路径用于检查
            normalized_path = relative_resource_path.replace('\\', '/').lower()
            
            # 检查是否在 Assets/remotes/entity 目录下
            if '/remotes/entity' in normalized_path:
                # 这是一个远程资源引用
                resource_name = guid_info.get('resource_name', os.path.basename(relative_resource_path))
                
                # 检查引用文件是否也在remotes目录下
                referencing_file_normalized = referencing_file.replace('\\', '/').lower()
                
                # 如果引用文件本身就在remotes目录下，则允许引用
                if '/remotes/entity' in referencing_file_normalized or '/remotes/entity' in referencing_file_normalized:
                    return None
                
                # 本地资源引用远程资源，返回错误信息
                return {
                    'remote_path': relative_resource_path,
                    'resource_name': resource_name,
                    'guid': target_guid
                }
                
        except Exception as e:
            # 如果检查过程中出现异常，记录但不阻止流程
            self.status_updated.emit(f"⚠️ 检查远程资源引用时出错: {e}")
        
        return None
    
    def _could_be_related_file(self, debug_path: str, target_guid: str, referencing_file: str) -> bool:
        """检查Debug_Path是否可能对应目标GUID"""
        # 简单的启发式检查
        debug_filename = os.path.basename(debug_path).lower()
        ref_filename = os.path.basename(referencing_file).lower()
        
        # 如果Debug_Path包含常见的材质文件名
        if 'body_skin' in debug_filename or 'material' in debug_path.lower():
            return True
            
        return False
    
    def _convert_debug_path_to_local(self, debug_path: str, referencing_file: str) -> str:
        """将Debug_Path转换为本地预期路径"""
        try:
            # 提取文件名
            filename = os.path.basename(debug_path)
            ref_dir = os.path.dirname(referencing_file)
            
            # 尝试几种可能的本地路径
            possible_paths = [
                os.path.join(ref_dir, filename),
                os.path.join(ref_dir, 'Material', filename),
                os.path.join(ref_dir, '..', 'Material', filename),
            ]
            
            # 返回第一个合理的路径
            for path in possible_paths:
                return os.path.normpath(path)
                
        except Exception:
            pass
        
        return ""
    
    def _check_debug_path_files(self) -> List[Dict[str, str]]:
        """检查prefab文件中Debug_Path记录的文件是否存在"""
        issues = []
        
        try:
            self.status_updated.emit("🔍 开始检查Debug_Path文件完整性...")
            
            # 遍历所有上传的prefab文件
            for file_path in self.upload_files:
                if not file_path.lower().endswith('.prefab'):
                    continue
                
                try:
                    self.status_updated.emit(f"🔍 检查prefab文件: {os.path.basename(file_path)}")
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取所有Debug_Path记录
                    import re
                    debug_path_matches = re.findall(r'"Debug_Path":\s*"([^"]+)"', content)
                    
                    self.status_updated.emit(f"   找到 {len(debug_path_matches)} 个Debug_Path记录")
                    
                    for debug_path in debug_path_matches:
                        self.status_updated.emit(f"   🔍 检查Debug_Path: {debug_path}")
                        
                        # 🚨 新增：检查是否为系统默认材质
                        if self._is_system_default_material(debug_path):
                            self.status_updated.emit(f"   ✅ 系统默认材质，跳过检查: {os.path.basename(debug_path)}")
                            continue
                        
                        # 提取文件名
                        debug_filename = os.path.basename(debug_path)
                        
                        # 转换为本地预期路径
                        local_expected_paths = self._get_local_expected_paths(debug_path, file_path)
                        
                        # 检查文件是否存在
                        file_found = False
                        found_path = ""
                        
                        for expected_path in local_expected_paths:
                            # 🚨 修复：将正斜杠路径转换为系统路径格式进行文件存在性检查
                            system_path = expected_path.replace('/', os.sep)
                            if os.path.exists(system_path):
                                file_found = True
                                found_path = expected_path  # 保持显示格式一致
                                self.status_updated.emit(f"   ✅ 找到文件: {expected_path}")
                                break
                        
                        if not file_found:
                            # 🚨 新增：如果本地路径都找不到，尝试全局SVN搜索
                            self.status_updated.emit(f"   🔍 本地路径未找到，开始全局SVN搜索: {debug_filename}")
                            global_search_result = self._search_file_in_svn_by_name_and_guid(debug_filename, debug_path, file_path)
                            
                            if global_search_result:
                                file_found = True
                                found_path = global_search_result['path']
                                self.status_updated.emit(f"   ✅ 全局搜索找到文件: {found_path}")
                                self.status_updated.emit(f"      GUID匹配: {global_search_result['guid']}")
                            else:
                                # 检查是否有对应的meta文件但资源文件缺失
                                meta_found = False
                                meta_path = ""
                                
                                for expected_path in local_expected_paths:
                                    meta_file = expected_path + '.meta'
                                    # 🚨 修复：将正斜杠路径转换为系统路径格式进行文件存在性检查
                                    system_meta_file = meta_file.replace('/', os.sep)
                                    if os.path.exists(system_meta_file):
                                        meta_found = True
                                        meta_path = meta_file  # 保持显示格式一致
                                        break
                                
                                if meta_found:
                                    # 有meta文件但资源文件缺失
                                    prefab_name = os.path.basename(file_path)
                                    resource_name = os.path.basename(expected_path)
                                    meta_name = os.path.basename(meta_path)
                                    
                                    issues.append({
                                        'type': 'debug_path_resource_missing',
                                        'file': file_path,
                                        'description': f'【资源文件缺失】\n' +
                                                     f'问题文件: {prefab_name}\n' +
                                                     f'缺失资源: {resource_name}\n' +
                                                     f'存在meta: {meta_name}\n' +
                                                     f'原因: prefab引用了{resource_name}，但资源文件被删除了\n' +
                                                     f'解决方案: 恢复缺失的资源文件 {resource_name}',
                                        'debug_path': debug_path,
                                        'expected_local_path': expected_path,
                                        'meta_file_exists': meta_path,
                                        'solution': f'需要恢复资源文件: {debug_filename}',
                                        'message': f'prefab文件 {prefab_name} 引用了缺失的资源文件 {resource_name}（meta文件存在）'
                                })
                                    self.status_updated.emit(f"   🚨 资源文件缺失: {debug_filename} (meta文件存在: {os.path.basename(meta_path)})")
                                else:
                                    # 完全缺失（资源文件和meta文件都没有）
                                    prefab_name = os.path.basename(file_path)
                                    expected_paths_str = '\n'.join([f'    • {path}' for path in local_expected_paths[:3]])
                                    if len(local_expected_paths) > 3:
                                        expected_paths_str += f'\n    • ... 还有{len(local_expected_paths)-3}个路径'
                                    
                                    issues.append({
                                        'type': 'debug_path_completely_missing',
                                        'file': file_path,
                                        'description': f'【文件完全缺失】\n' +
                                                     f'问题文件: {prefab_name}\n' +
                                                     f'缺失文件: {debug_filename}\n' +
                                                 f'原因: prefab的Debug_Path记录指向了不存在的文件\n' +
                                                 f'预期位置:\n{expected_paths_str}\n' +
                                                 f'解决方案: 创建文件 {debug_filename} 及其对应的.meta文件',
                                    'debug_path': debug_path,
                                    'expected_local_paths': local_expected_paths,
                                    'solution': f'需要创建文件: {debug_filename} 及其.meta文件',
                                    'message': f'prefab文件 {prefab_name} 引用了完全不存在的文件 {debug_filename}'
                                })
                                self.status_updated.emit(f"   🚨 文件完全缺失: {debug_filename}")
                                self.status_updated.emit(f"      预期路径: {local_expected_paths}")
                        
                except Exception as e:
                    self.status_updated.emit(f"❌ 检查prefab文件失败: {os.path.basename(file_path)} - {e}")
                    issues.append({
                        'type': 'debug_path_check_error',
                        'file': file_path,
                        'description': f'检查Debug_Path时发生错误: {str(e)}'
                    })
        
        except Exception as e:
            self.status_updated.emit(f"❌ Debug_Path检查异常: {e}")
            issues.append({
                'type': 'debug_path_system_error',
                'file': 'system',
                'description': f'Debug_Path检查系统错误: {str(e)}'
            })
        
        if issues:
            self.status_updated.emit(f"Debug_Path检查完成，发现 {len(issues)} 个问题")
        else:
            self.status_updated.emit("✅ Debug_Path检查通过，所有文件都存在")
        
        return issues
    
    def _is_system_default_material(self, debug_path: str) -> bool:
        """检查是否为系统默认材质路径
        
        Args:
            debug_path: Debug_Path路径
            
        Returns:
            bool: True表示是系统默认材质，False表示不是
        """
        try:
            # 标准化路径（统一使用正斜杠）
            normalized_path = debug_path.replace('\\', '/').lower()
            
            # 系统默认材质的特征路径
            system_material_patterns = [
                '/assets/systemdefault/',  # 主要的系统默认路径
                '/systemdefault/',         # 简化的系统默认路径
                '/engineresource/',        # 引擎资源路径
                '/assets/engineresource/', # 完整引擎资源路径
            ]
            
            # 检查是否包含系统材质路径特征
            for pattern in system_material_patterns:
                if pattern in normalized_path:
                    return True
            
            # 检查是否为常见的系统材质文件名
            filename = os.path.basename(normalized_path)
            system_material_files = [
                'particlematerial.mat',        # 粒子材质
                'defaultmaterial.mat',         # 默认材质
                'spritematerial.mat',          # 精灵材质
                'ui-default.mat',              # UI默认材质
                'legacy-diffuse.mat',          # 传统漫反射材质
                'legacy-transparent.mat',      # 传统透明材质
            ]
            
            if filename in system_material_files:
                return True
                
            return False
            
        except Exception as e:
            # 如果检查过程中出现异常，默认认为不是系统材质
            return False
    
    def _get_local_expected_paths(self, debug_path: str, prefab_file: str) -> List[str]:
        """根据Debug_Path和prefab文件位置，推断本地预期的文件路径"""
        expected_paths = []
        
        try:
            # 🚨 新增：检查是否为系统默认材质路径
            if self._is_system_default_material(debug_path):
                # 系统材质路径，不需要检查本地存在性，直接返回空列表
                # 这样会跳过后续的缺失文件检查
                return []
            
            # 提取Debug_Path中的文件名
            debug_filename = os.path.basename(debug_path)
            prefab_dir = os.path.dirname(prefab_file)
            
            # 🚨 关键修复：首先尝试Debug_Path的直接路径映射
            # Debug_Path可能使用正斜杠，但在Windows下文件实际使用反斜杠
            # 1. 直接将Debug_Path转换为Windows路径格式进行检查
            direct_path = debug_path.replace('/', os.sep)
            expected_paths.append(direct_path)
            
            # 2. 如果Debug_Path包含盘符路径，尝试映射到当前工作环境
            if ':' in debug_path:
                # 提取Assets之后的相对路径部分
                debug_normalized = debug_path.replace('\\', '/')
                if '/Assets/' in debug_normalized:
                    assets_index = debug_normalized.find('/Assets/')
                    relative_from_assets = debug_normalized[assets_index:]  # 包含/Assets/
                    
                    # 基于prefab文件位置推断项目根目录
                    prefab_normalized = os.path.normpath(prefab_file).replace('\\', '/')
                    if '/Assets/' in prefab_normalized:
                        prefab_assets_index = prefab_normalized.find('/Assets/')
                        project_root = prefab_normalized[:prefab_assets_index]
                        mapped_path = project_root + relative_from_assets
                        expected_paths.append(mapped_path)
                        
                        # 🚨 新增：基于Debug_Path的目录结构进行更精确的映射
                        # 提取Debug_Path中Assets之后的路径结构
                        debug_asset_relative = relative_from_assets[8:]  # 去掉/Assets/
                        debug_parts = debug_asset_relative.split('/')
                        
                        if len(debug_parts) >= 2:  # 至少有目录/文件名
                            # 尝试将Debug_Path的目录结构映射到prefab所在的相对位置
                            # 例如: entity/140494/Timeline/Prefab/zhoushen_ring.prefab
                            # 映射到: remotes/entity/140494/Timeline/Prefab/zhoushen_ring.prefab
                            
                            prefab_asset_relative = prefab_normalized[prefab_assets_index + 8:]  # 去掉/Assets/
                            prefab_parts = prefab_asset_relative.split('/')
                            
                            if len(prefab_parts) >= 2:
                                # 尝试找到共同的目录结构
                                # 如果Debug_Path是 entity/140494/Timeline/Prefab/xxx
                                # 而prefab在 remotes/entity/140494/xxx
                                # 则尝试 remotes/entity/140494/Timeline/Prefab/xxx
                                
                                # 找到实体ID（通常是数字目录）
                                entity_id = None
                                for part in debug_parts:
                                    if part.isdigit() and len(part) == 6:  # 6位数字的实体ID
                                        entity_id = part
                                        break
                                
                                if entity_id:
                                    # 在prefab路径中找到相同的实体ID位置
                                    for i, part in enumerate(prefab_parts):
                                        if part == entity_id:
                                            # 构建映射路径：prefab的前缀 + debug的后缀
                                            prefab_prefix = '/'.join(prefab_parts[:i+1])  # 到实体ID为止
                                            
                                            # 找到Debug_Path中实体ID之后的部分
                                            debug_entity_index = debug_parts.index(entity_id)
                                            debug_suffix = '/'.join(debug_parts[debug_entity_index+1:])  # 实体ID之后的部分
                                            
                                            if debug_suffix:
                                                mapped_structure_path = project_root + '/Assets/' + prefab_prefix + '/' + debug_suffix
                                                expected_paths.append(mapped_structure_path)
                                            break
            
            # 根据Debug_Path的结构推断本地路径
            # 例如: "F:/Minigame_Art_NewPrefab_6.1.10/Assets/remotes/entity/140491/Material/body_skin.mat"
            # 可能的本地路径：
            
            # 3. 同目录下
            expected_paths.append(os.path.join(prefab_dir, debug_filename))
            
            # 4. Material子目录下
            material_dir = os.path.join(prefab_dir, 'Material')
            expected_paths.append(os.path.join(material_dir, debug_filename))
            
            # 5. 上级目录的Material子目录
            parent_dir = os.path.dirname(prefab_dir)
            if parent_dir != prefab_dir:  # 确保不是根目录
                expected_paths.append(os.path.join(parent_dir, 'Material', debug_filename))
            
            # 6. 根据Debug_Path的目录结构推断
            if 'Material' in debug_path:
                # 如果Debug_Path包含Material目录，尝试在本地找到相似结构
                debug_parts = debug_path.replace('\\', '/').split('/')
                if 'Material' in debug_parts:
                    material_index = debug_parts.index('Material')
                    # 从Material开始的相对路径
                    relative_path = '/'.join(debug_parts[material_index:])
                    expected_paths.append(os.path.join(prefab_dir, relative_path))
                    expected_paths.append(os.path.join(parent_dir, relative_path))
            
            # 🚨 新增：检查本地特效资源路径
            # 7. 本地特效资源常见路径
            if debug_filename.endswith('.mat'):
                # 基于prefab文件位置推断项目根目录
                prefab_normalized = os.path.normpath(prefab_file).replace('\\', '/')
                if '/Assets/' in prefab_normalized:
                    prefab_assets_index = prefab_normalized.find('/Assets/')
                    project_root = prefab_normalized[:prefab_assets_index]
                    
                    # 常见的本地特效资源路径
                    local_fx_paths = [
                        # 标准特效资源路径
                        f"{project_root}/Assets/prefab/particles/public/Material/{debug_filename}",
                        f"{project_root}/Assets/prefab/particles/Material/{debug_filename}",
                        f"{project_root}/Assets/prefab/fx/Material/{debug_filename}",
                        f"{project_root}/Assets/particles/public/Material/{debug_filename}",
                        f"{project_root}/Assets/particles/Material/{debug_filename}",
                        f"{project_root}/Assets/fx/Material/{debug_filename}",
                        
                        # 通用Material目录
                        f"{project_root}/Assets/Material/{debug_filename}",
                        f"{project_root}/Assets/Materials/{debug_filename}",
                    ]
                    
                    expected_paths.extend(local_fx_paths)
            
            # 7. 基于文件名模式的推断
            if 'body_skin' in debug_filename.lower():
                # 常见的材质文件位置
                expected_paths.append(os.path.join(prefab_dir, 'Materials', debug_filename))
                expected_paths.append(os.path.join(parent_dir, 'Materials', debug_filename))
            
            # 去重并标准化路径 - 统一使用正斜杠以匹配Debug_Path格式
            unique_paths = []
            for path in expected_paths:
                # 🚨 修复：统一使用正斜杠，与Debug_Path格式保持一致
                normalized = os.path.normpath(path).replace('\\', '/')
                if normalized not in unique_paths:
                    unique_paths.append(normalized)
            
            return unique_paths
            
        except Exception as e:
            # 如果推断失败，至少返回同目录下的路径
            fallback_path = os.path.join(os.path.dirname(prefab_file), os.path.basename(debug_path))
            # 🚨 修复：统一使用正斜杠格式
            return [fallback_path.replace('\\', '/')]
    
    def _search_file_in_svn_by_name_and_guid(self, filename: str, debug_path: str, prefab_file: str) -> dict:
        """在SVN仓库中搜索同名文件并通过GUID验证引用关系"""
        try:
            # 1. 获取SVN根目录
            svn_root = None
            if hasattr(self, 'git_manager') and self.git_manager and self.git_manager.svn_path:
                svn_root = self.git_manager.svn_path
            else:
                # 尝试从prefab文件路径推断SVN根目录
                svn_root = self._find_svn_root_from_file(prefab_file)
            
            if not svn_root or not os.path.exists(svn_root):
                self.status_updated.emit(f"   ⚠️ 无法确定SVN根目录，跳过全局搜索")
                return None
            
            self.status_updated.emit(f"   🔍 在SVN根目录搜索: {svn_root}")
            
            # 2. 搜索所有同名文件
            matching_files = []
            file_count = 0
            max_files_to_scan = 10000  # 限制扫描文件数量，避免过度消耗性能
            
            for root, dirs, files in os.walk(svn_root):
                # 跳过一些不必要的目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['temp', 'tmp', 'cache']]
                
                for file in files:
                    file_count += 1
                    if file_count > max_files_to_scan:
                        self.status_updated.emit(f"   ⚠️ 已扫描{max_files_to_scan}个文件，停止搜索以避免性能问题")
                        break
                    
                    if file.lower() == filename.lower():
                        full_path = os.path.join(root, file)
                        matching_files.append(full_path)
                        self.status_updated.emit(f"   🔍 找到同名文件: {full_path}")
                        
                        # 🚨 特殊处理：如果是在本地特效资源路径中找到的，优先考虑
                        if 'particles' in root.lower() or 'fx' in root.lower():
                            self.status_updated.emit(f"   ✅ 发现本地特效资源: {full_path}")
                
                if file_count > max_files_to_scan:
                    break
            
            if not matching_files:
                self.status_updated.emit(f"   ❌ SVN仓库中未找到同名文件: {filename}")
                return None
            
            # 3. 从Debug_Path中提取期望的GUID（如果可能）
            expected_guid = self._extract_guid_from_debug_path(debug_path, prefab_file)
            
            # 4. 检查每个同名文件的GUID和Assets路径匹配
            best_match = None
            for candidate_file in matching_files:
                meta_file = candidate_file + '.meta'
                if os.path.exists(meta_file):
                    try:
                        candidate_guid = self.analyzer.parse_meta_file(meta_file)
                        if candidate_guid:
                            self.status_updated.emit(f"      检查GUID: {candidate_guid}")
                            
                            # 🚨 新增：使用增强的Debug_Path一致性验证
                            validation_result = self._validate_debug_path_consistency(debug_path, candidate_file, expected_guid)
                            
                            # 输出详细验证信息
                            for detail in validation_result['validation_details']:
                                self.status_updated.emit(f"      {detail}")
                            
                            # 如果验证通过，返回匹配结果
                            if validation_result['is_valid']:
                                match_type = 'exact_match' if validation_result['guid_match'] else 'path_match'
                                return {
                                    'path': candidate_file.replace('\\', '/'),
                                    'guid': candidate_guid,
                                    'match_type': match_type,
                                    'assets_similarity': validation_result['confidence_score'],
                                    'validation_status': 'confirmed',
                                    'validation_details': '; '.join(validation_result['validation_details'])
                                }
                            
                            # 如果有期望的GUID但验证未通过，继续检查其他候选
                            elif expected_guid and candidate_guid.lower() == expected_guid.lower():
                                self.status_updated.emit(f"      ✅ GUID完全匹配！")
                                self.status_updated.emit(f"      📋 依赖关系验证: GUID匹配，但路径可能有差异")
                                return {
                                    'path': candidate_file.replace('\\', '/'),
                                    'guid': candidate_guid,
                                    'match_type': 'exact_guid',
                                    'assets_similarity': validation_result['confidence_score'],
                                    'validation_status': 'partial',
                                    'validation_details': '; '.join(validation_result['validation_details'])
                                }
                            
                            # 记录为候选（如果验证结果有一定置信度）
                            elif validation_result['confidence_score'] > 0.3:
                                if not best_match or validation_result['confidence_score'] > best_match.get('assets_similarity', 0):
                                    best_match = {
                                        'path': candidate_file.replace('\\', '/'),
                                        'guid': candidate_guid,
                                        'match_type': 'candidate',
                                        'assets_similarity': validation_result['confidence_score'],
                                        'validation_details': '; '.join(validation_result['validation_details'])
                                    }
                    except Exception as e:
                        self.status_updated.emit(f"      ⚠️ 读取meta文件失败: {e}")
                        continue
            
            # 如果找到了最佳匹配，返回它
            if best_match:
                self.status_updated.emit(f"      ✅ 返回最佳匹配: {best_match['match_type']}")
                return best_match
            
            # 5. 如果没有找到GUID匹配的文件，但有同名文件，返回第一个
            if matching_files:
                first_match = matching_files[0]
                self.status_updated.emit(f"   ⚠️ 未找到GUID匹配的文件，返回第一个同名文件")
                return {
                    'path': first_match.replace('\\', '/'),
                    'guid': None,
                    'match_type': 'name_fallback'
                }
            
            return None
            
        except Exception as e:
            self.status_updated.emit(f"   ❌ 全局搜索出错: {e}")
            return None
    
    def _find_svn_root_from_file(self, file_path: str) -> str:
        """从文件路径推断SVN根目录"""
        try:
            current_dir = os.path.dirname(os.path.abspath(file_path))
            
            # 向上搜索，寻找包含.svn或Assets目录的根目录
            while current_dir and current_dir != os.path.dirname(current_dir):
                if os.path.exists(os.path.join(current_dir, '.svn')):
                    return current_dir
                
                # 如果找到Assets目录，其父目录通常是项目根目录
                if os.path.basename(current_dir).lower() == 'assets':
                    return os.path.dirname(current_dir)
                
                current_dir = os.path.dirname(current_dir)
            
            return None
        except Exception:
            return None
    
    def _calculate_assets_path_similarity(self, debug_path: str, candidate_file: str) -> float:
        """计算Debug_Path与候选文件的Assets路径相似度"""
        try:
            # 1. 使用统一的路径标准化方法
            debug_normalized = self._normalize_path_for_comparison(debug_path)
            candidate_normalized = self._normalize_path_for_comparison(candidate_file)
            
            # 2. 提取Assets之后的路径部分
            debug_assets_path = self._extract_assets_path_from_debug_path(debug_path)
            candidate_assets_path = self._extract_assets_path_from_debug_path(candidate_file)
            
            # 3. 增强调试信息
            self.status_updated.emit(f"      🔍 路径标准化调试:")
            self.status_updated.emit(f"         原始Debug_Path: {debug_path}")
            self.status_updated.emit(f"         标准化Debug_Path: {debug_normalized}")
            self.status_updated.emit(f"         提取的Debug Assets路径: {debug_assets_path}")
            self.status_updated.emit(f"         原始候选文件路径: {candidate_file}")
            self.status_updated.emit(f"         标准化候选文件路径: {candidate_normalized}")
            self.status_updated.emit(f"         提取的候选Assets路径: {candidate_assets_path}")
            
            # 如果其中一个没有Assets路径，返回较低的相似度
            if not debug_assets_path or not candidate_assets_path:
                return 0.1
            
            # 3. 分割路径为组件
            debug_parts = [part for part in debug_assets_path.split('/') if part]
            candidate_parts = [part for part in candidate_assets_path.split('/') if part]
            
            # 4. 计算路径相似度
            # 方法1: 检查是否有相同的实体ID模式
            entity_id_match = self._check_entity_id_pattern_match(debug_parts, candidate_parts)
            if entity_id_match > 0:
                return entity_id_match
            
            # 方法2: 计算路径组件的重叠度
            if not debug_parts or not candidate_parts:
                return 0.1
            
            # 计算公共前缀长度
            common_prefix_len = 0
            min_len = min(len(debug_parts), len(candidate_parts))
            for i in range(min_len):
                if debug_parts[i] == candidate_parts[i]:
                    common_prefix_len += 1
                else:
                    break
            
            # 计算公共后缀长度（文件名通常在最后）
            common_suffix_len = 0
            for i in range(1, min_len + 1):
                if debug_parts[-i] == candidate_parts[-i]:
                    common_suffix_len += 1
                else:
                    break
            
            # 计算总体匹配度
            max_len = max(len(debug_parts), len(candidate_parts))
            common_parts = common_prefix_len + common_suffix_len
            
            # 避免重复计算（如果前缀和后缀重叠）
            if common_prefix_len + common_suffix_len > min_len:
                common_parts = min_len
            
            similarity = common_parts / max_len if max_len > 0 else 0
            
            # 5. 特殊加分项
            # 如果文件名完全相同，加分
            debug_filename = debug_parts[-1] if debug_parts else ""
            candidate_filename = candidate_parts[-1] if candidate_parts else ""
            if debug_filename == candidate_filename:
                similarity += 0.2
            
            # 如果包含相同的特殊目录（如Timeline, Material等），加分
            special_dirs = {'timeline', 'material', 'prefab', 'texture', 'animation'}
            debug_special = set(part for part in debug_parts if part in special_dirs)
            candidate_special = set(part for part in candidate_parts if part in special_dirs)
            if debug_special & candidate_special:  # 有交集
                similarity += 0.1
            
            return min(similarity, 1.0)  # 确保不超过1.0
            
        except Exception as e:
            self.status_updated.emit(f"   ⚠️ 计算路径相似度失败: {e}")
            return 0.1
    
    def _check_entity_id_pattern_match(self, debug_parts: list, candidate_parts: list) -> float:
        """检查实体ID模式匹配（专门处理跨实体引用）"""
        try:
            # 查找6位数字的实体ID
            debug_entity_ids = [part for part in debug_parts if part.isdigit() and len(part) == 6]
            candidate_entity_ids = [part for part in candidate_parts if part.isdigit() and len(part) == 6]
            
            if not debug_entity_ids or not candidate_entity_ids:
                return 0
            
            # 如果是跨实体引用（不同的实体ID），这是正常的
            debug_entity_id = debug_entity_ids[0]
            candidate_entity_id = candidate_entity_ids[0]
            
            # 找到实体ID在路径中的位置
            debug_entity_index = debug_parts.index(debug_entity_id)
            candidate_entity_index = candidate_parts.index(candidate_entity_id)
            
            # 检查实体ID之前的路径是否相似（如 entity, remotes/entity 等）
            debug_prefix = debug_parts[:debug_entity_index]
            candidate_prefix = candidate_parts[:candidate_entity_index]
            
            # 检查实体ID之后的路径是否相似
            debug_suffix = debug_parts[debug_entity_index + 1:]
            candidate_suffix = candidate_parts[candidate_entity_index + 1:]
            
            # 计算前缀相似度
            prefix_similarity = self._calculate_list_similarity(debug_prefix, candidate_prefix)
            
            # 计算后缀相似度
            suffix_similarity = self._calculate_list_similarity(debug_suffix, candidate_suffix)
            
            # 如果前缀和后缀都比较相似，说明是合理的跨实体引用
            if prefix_similarity >= 0.5 and suffix_similarity >= 0.5:
                # 跨实体引用的相似度计算
                overall_similarity = (prefix_similarity + suffix_similarity) / 2
                self.status_updated.emit(f"      🔗 检测到跨实体引用: {debug_entity_id} → {candidate_entity_id}")
                self.status_updated.emit(f"      前缀相似度: {prefix_similarity:.2%}, 后缀相似度: {suffix_similarity:.2%}")
                return min(overall_similarity + 0.3, 1.0)  # 跨实体引用给予额外加分
            
            return 0
            
        except Exception:
            return 0
    
    def _calculate_list_similarity(self, list1: list, list2: list) -> float:
        """计算两个列表的相似度"""
        if not list1 and not list2:
            return 1.0
        if not list1 or not list2:
            return 0.0
        
        # 计算公共元素数量
        set1 = set(list1)
        set2 = set(list2)
        common = len(set1 & set2)
        total = len(set1 | set2)
        
        return common / total if total > 0 else 0.0
    
    def _validate_debug_path_consistency(self, debug_path: str, candidate_file: str, expected_guid: str = None) -> dict:
        """验证Debug_Path与候选文件的一致性（专门处理140489/140488场景）"""
        result = {
            'is_valid': False,
            'confidence_score': 0.0,
            'validation_details': [],
            'assets_path_match': False,
            'guid_match': False
        }
        
        try:
            # 1. 提取并比较Assets路径
            debug_assets_path = self._extract_assets_path_from_debug_path(debug_path)
            candidate_assets_path = self._extract_assets_path_from_debug_path(candidate_file)
            
            if debug_assets_path and candidate_assets_path:
                # 计算路径相似度
                similarity = self._calculate_assets_path_similarity(debug_path, candidate_file)
                result['confidence_score'] = similarity
                
                if similarity >= 0.8:
                    result['assets_path_match'] = True
                    result['validation_details'].append(f"✅ Assets路径高度匹配 (相似度: {similarity:.2%})")
                elif similarity >= 0.5:
                    result['validation_details'].append(f"⚠️ Assets路径部分匹配 (相似度: {similarity:.2%})")
                else:
                    result['validation_details'].append(f"❌ Assets路径差异较大 (相似度: {similarity:.2%})")
                
                # 详细路径分析
                result['validation_details'].append(f"Debug Assets路径: {debug_assets_path}")
                result['validation_details'].append(f"候选文件Assets路径: {candidate_assets_path}")
            
            # 2. GUID验证（如果提供）
            if expected_guid:
                meta_file = candidate_file + '.meta'
                if os.path.exists(meta_file):
                    candidate_guid = self.analyzer.parse_meta_file(meta_file)
                    if candidate_guid and candidate_guid.lower() == expected_guid.lower():
                        result['guid_match'] = True
                        result['validation_details'].append(f"✅ GUID完全匹配: {expected_guid}")
                    else:
                        result['validation_details'].append(f"❌ GUID不匹配: 期望{expected_guid}, 实际{candidate_guid}")
                else:
                    result['validation_details'].append(f"⚠️ 候选文件缺少meta文件: {meta_file}")
            
            # 3. 综合判断
            if result['guid_match'] and result['assets_path_match']:
                result['is_valid'] = True
                result['validation_details'].append("🎉 依赖关系完全验证通过：GUID和Debug_Path都匹配")
            elif result['assets_path_match']:
                result['is_valid'] = True
                result['validation_details'].append("✅ 依赖关系基本验证通过：Debug_Path匹配度高")
            elif result['guid_match']:
                result['validation_details'].append("⚠️ GUID匹配但路径差异较大，可能存在路径映射问题")
            
            return result
            
        except Exception as e:
            result['validation_details'].append(f"❌ 验证过程出错: {e}")
            return result
    
    def _normalize_path_for_comparison(self, path: str) -> str:
        """统一的路径标准化方法，专门用于路径比较"""
        try:
            if not path:
                return ""
            
            # 1. 标准化路径分隔符：统一使用正斜杠
            normalized = path.replace('\\', '/')
            
            # 2. 转换为小写（Windows路径不区分大小写）
            normalized = normalized.lower()
            
            # 3. 移除开头和结尾的斜杠
            normalized = normalized.strip('/')
            
            # 4. 处理多个连续斜杠
            while '//' in normalized:
                normalized = normalized.replace('//', '/')
            
            return normalized
        except:
            return ""
    
    def _extract_assets_path_from_debug_path(self, path: str) -> str:
        """从Debug_Path或文件路径中提取Assets之后的部分"""
        try:
            normalized_path = self._normalize_path_for_comparison(path)
            if '/assets/' in normalized_path:
                assets_index = normalized_path.find('/assets/')
                return normalized_path[assets_index + 8:]  # 去掉 '/assets/'
            # 🚨 增强：如果没有找到 '/assets/'，尝试查找 'assets/' （没有前导斜杠）
            elif 'assets/' in normalized_path:
                assets_index = normalized_path.find('assets/')
                return normalized_path[assets_index + 7:]  # 去掉 'assets/'
            return ""
        except:
            return ""

    def _extract_debug_path_guid_mapping(self, prefab_file: str) -> dict:
        """从prefab文件中提取Debug_Path和GUID的映射关系"""
        mapping = {}
        try:
            with open(prefab_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析JSON格式
            try:
                import json
                data = json.loads(content)
                self._extract_debug_path_from_json(data, mapping)
            except json.JSONDecodeError:
                # 如果不是JSON，使用正则表达式提取
                self._extract_debug_path_with_regex(content, mapping)
            
            return mapping
        except Exception as e:
            self.status_updated.emit(f"   ⚠️ 提取Debug_Path映射失败: {e}")
            return {}
    
    def _extract_debug_path_from_json(self, data, mapping, path=""):
        """递归从JSON数据中提取Debug_Path和GUID的映射"""
        if isinstance(data, dict):
            debug_path = data.get("Debug_Path")
            guid = data.get("m_GUID") or data.get("guid") or data.get("m_SourcePrefabGUID")
            
            if debug_path and guid:
                # 标准化Debug_Path
                normalized_debug_path = self._normalize_path_for_comparison(debug_path)
                mapping[normalized_debug_path] = {
                    'guid': guid.lower(),
                    'original_debug_path': debug_path,
                    'context': path
                }
                self.status_updated.emit(f"   🔍 提取映射: {debug_path} -> {guid}")
            
            # 递归处理嵌套对象
            for key, value in data.items():
                self._extract_debug_path_from_json(value, mapping, f"{path}.{key}" if path else key)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._extract_debug_path_from_json(item, mapping, f"{path}[{i}]" if path else f"[{i}]")
    
    def _extract_debug_path_with_regex(self, content: str, mapping: dict):
        """使用正则表达式提取Debug_Path和GUID的映射"""
        # 匹配Debug_Path和附近的GUID
        debug_path_pattern = r'"Debug_Path":\s*"([^"]+)"[^}]*?"(?:m_GUID|guid|m_SourcePrefabGUID)":\s*"([a-f0-9]{32})"'
        matches = re.findall(debug_path_pattern, content, re.IGNORECASE | re.DOTALL)
        
        for debug_path, guid in matches:
            normalized_debug_path = self._normalize_path_for_comparison(debug_path)
            mapping[normalized_debug_path] = {
                'guid': guid.lower(),
                'original_debug_path': debug_path,
                'context': 'regex_extract'
            }
            self.status_updated.emit(f"   🔍 正则提取映射: {debug_path} -> {guid}")

    def _extract_guid_from_debug_path(self, debug_path: str, prefab_file: str) -> str:
        """从Debug_Path或相关prefab文件中提取期望的GUID"""
        try:
            # 使用新的映射提取方法
            mapping = self._extract_debug_path_guid_mapping(prefab_file)
            normalized_debug_path = self._normalize_path_for_comparison(debug_path)
            
            if normalized_debug_path in mapping:
                return mapping[normalized_debug_path]['guid']
            
            # 如果没有找到精确匹配，尝试部分匹配
            for mapped_path, info in mapping.items():
                if debug_path.lower() in info['original_debug_path'].lower():
                    self.status_updated.emit(f"   🔍 部分匹配找到GUID: {info['guid']}")
                    return info['guid']
            
            # 方法1: 尝试从prefab文件内容中找到对应的GUID引用
            with open(prefab_file, 'r', encoding='utf-8') as f:
                prefab_content = f.read()
            
            # 在prefab内容中搜索Debug_Path附近的GUID
            # 这里简化处理，实际可能需要更复杂的JSON解析
            import re
            
            # 查找Debug_Path行附近的GUID
            lines = prefab_content.split('\n')
            debug_filename = os.path.basename(debug_path)
            
            for i, line in enumerate(lines):
                if debug_filename in line and 'Debug_Path' in line:
                    # 在前后几行中搜索GUID
                    search_range = range(max(0, i-10), min(len(lines), i+10))
                    for j in search_range:
                        guid_match = re.search(r'"guid":\s*"([a-f0-9]{32})"', lines[j], re.IGNORECASE)
                        if guid_match:
                            return guid_match.group(1)
                        
                        # 也尝试其他GUID格式
                        guid_match2 = re.search(r'guid:\s*([a-f0-9]{32})', lines[j], re.IGNORECASE)
                        if guid_match2:
                            return guid_match2.group(1)
            
            return None
            
        except Exception as e:
            self.status_updated.emit(f"   ⚠️ 提取GUID失败: {e}")
            return None
    
    def _analyze_missing_guid(self, missing_guid: str, referencing_file: str) -> str:
        """分析缺失的GUID可能对应的文件类型和建议"""
        try:
            _, ext = os.path.splitext(referencing_file.lower())
            
            # 根据引用文件类型推测缺失文件类型
            if ext == '.controller':
                return "可能是动画文件(.skAnim)或状态机相关资源"
            elif ext == '.prefab':
                return "可能是材质(.mat)、模型(.mesh)、纹理(.png/.jpg)或其他组件"
            elif ext == '.mat':
                return "可能是纹理文件(.png/.jpg/.tga)或着色器"
            elif ext == '.asset':
                return "可能是配置文件或其他资源文件"
            else:
                return "未知类型的依赖资源"
                
        except:
            return "无法分析的依赖资源"
    
    def _check_internal_dependencies(self, local_guids: dict) -> List[Dict[str, str]]:
        """检查本次推送文件包内部的依赖完整性"""
        issues = []
        
        try:
            # 分析每个文件的依赖关系
            file_dependencies = {}  # {file_path: set(referenced_guids)}
            
            for file_path in self.upload_files:
                if file_path.lower().endswith('.meta'):
                    continue
                
                try:
                    _, ext = os.path.splitext(file_path.lower())
                    if ext in self.high_priority_types or ext in self.medium_priority_types:
                        referenced_guids = self.analyzer.parse_editor_asset(file_path)
                        file_dependencies[file_path] = referenced_guids
                except:
                    continue
            
            # 检查内部引用的完整性
            for file_path, referenced_guids in file_dependencies.items():
                for guid in referenced_guids:
                    # 如果这个GUID在本次推送的文件中
                    if guid in local_guids:
                        referenced_file = local_guids[guid]
                        
                        # 检查被引用的文件是否真的在推送列表中
                        if referenced_file not in self.upload_files:
                            issues.append({
                                'file': file_path,
                                'type': 'internal_dependency_missing',
                                'message': f'内部依赖文件缺失: {os.path.basename(referenced_file)}',
                                'missing_file': referenced_file,
                                'missing_guid': guid,
                                'dependency_info': f'{os.path.basename(file_path)} 依赖 {os.path.basename(referenced_file)}'
                            })
            
            # 检查是否有孤立的文件（被引用但没有引用者）
            referenced_files = set()
            for referenced_guids in file_dependencies.values():
                for guid in referenced_guids:
                    if guid in local_guids:
                        referenced_files.add(local_guids[guid])
            
            # 找出可能的孤立文件（在推送列表中但没有被引用的文件）
            all_files_with_guids = set(local_guids.values())
            potentially_orphaned = all_files_with_guids - referenced_files
            
            # 对于孤立文件，检查它们是否是入口文件（如prefab、controller等）
            for file_path in potentially_orphaned:
                _, ext = os.path.splitext(file_path.lower())
                if ext in {'.png', '.jpg', '.jpeg', '.tga', '.mesh', '.mat'}:  # 通常被引用的文件
                    # 这些文件类型通常应该被其他文件引用
                    issues.append({
                        'file': file_path,
                        'type': 'potentially_orphaned_file',
                        'message': f'文件可能未被引用: {os.path.basename(file_path)}',
                        'orphan_info': f'此{ext}文件在本次推送中未被其他文件引用，请确认是否需要'
                    })
                        
        except Exception as e:
            issues.append({
                'file': 'SYSTEM',
                'type': 'internal_dependency_check_error',
                'message': f'内部依赖检查失败: {str(e)}'
            })
        
        return issues

    def _check_material_templates(self) -> List[Dict[str, str]]:
        """检查材质模板使用情况"""
        issues = []
        
        # 允许的材质模板列表
        allowed_templates = {
            # 角色和场景模板
            'Character_NPR_Opaque.templatemat',
            'Character_NPR_Masked.templatemat',
            'Character_NPR_Tranclucent.templatemat',
            'Character_AVATAR_Masked.templatemat',
            'Character_AVATAR_Opaque.templatemat',
            'Character_AVATAR_Tranclucent.templatemat',
            'Character_PBR_Opaque.templatemat',
            'Character_PBR_Translucent.templatemat',
            'Character_PatternMask.templatemat',
            'Scene_Prop_Opaque.templatemat',
            'Scene_Prop_Tranclucent.templatemat',
            'Scene_Prop_Masked.templatemat',
            'Sight.templatemat',
            
            # 🆕 通用模板 - DefaultToonMat可以在所有路径下使用
            'DefaultToonMat.templatemat',
            'DefaultMaterial.templatemat',
            
            # 🆕 新增的场景PBR模板
            'Scene_PBR_Opaque.templatemat',
            'Scene_PBR_Translucent.templatemat',
            
            # 特效模板
            'fx_basic_ADD.templatemat',
            'fx_basic_fire.templatemat',
            'fx_basic_TRANSLUCENT.templatemat',
            'fx_dissolve_ADD.templatemat',
            'fx_dissolve_fresnel_ADD.templatemat',
            'fx_dissolve_fresnel_TRANSLUCENT.templatemat',
            'fx_dissolve_fresneluvwarp_ADD.templatemat',
            'fx_dissolve_fresneluvwarp_TRANSLUCENT.templatemat',
            'fx_dissolve_TRANSLUCENT.templatemat',
            'fx_dissolve_uvwarp_ADD.templatemat',
            'fx_dissolve_uvwarp_Fire_ADD.templatemat',
            'fx_dissolve_uvwarp_Fire_TRANSLUCENT.templatemat',
            'fx_dissolve_uvwarp_TRANSLUCENT.templatemat',
            'fx_dissolve_vertexesoffsetWithMask_ADD.templatemat',
            'fx_dissolve_vertexesoffsetWithMask_TRANSLUCENT.templatemat',
            'fx_fresnel_ADD.templatemat',
            'fx_fresnel_TRANSLUCENT.templatemat',
            'fx_uvwarp_ADD.templatemat',
            'fx_uvwarp_TRANSLUCENT.templatemat',
            'fx_vertexesoffset_ADD.templatemat',
            'fx_vertexesoffset_TRANSLUCENT.templatemat',
            'fx_vertexesoffsetWithMask_ADD.templatemat',
            'fx_vertexesoffsetWithMask_TRANSLUCENT.templatemat',
            'PolarDistortion.templatemat',
            'standard_particle_additive.templatemat',
            'standard_particle_translucent.templatemat'
        }
        
        # Timeline文件夹下材质的额外允许模板
        timeline_allowed_templates = {
            'DefaultMaterial.templatemat',
            'DefaultToonMat.templatemat'
        }
        
        try:
            self.status_updated.emit("🔍 开始材质模板检查...")
            
            # 筛选出需要检查的材质文件
            material_files = []
            for file_path in self.upload_files:
                if not file_path.lower().endswith('.mat'):
                    continue
                
                # 检查是否在entity目录下
                normalized_path = os.path.normpath(file_path)
                path_parts = normalized_path.split(os.sep)
                
                # 查找entity目录
                entity_index = -1
                for i, part in enumerate(path_parts):
                    if part.lower() == 'entity':
                        entity_index = i
                        break
                
                if entity_index == -1:
                    continue  # 不在entity目录下，跳过
                
                # 检查是否在排除的目录中
                excluded_path = False
                remaining_parts = path_parts[entity_index + 1:]
                
                # 🆕 检查是否在entity/Environment/Scenes目录下（特殊规则）
                is_environment_scenes = False
                if (len(remaining_parts) >= 2 and 
                    remaining_parts[0].lower() == 'environment' and 
                    remaining_parts[1].lower() == 'scenes'):
                    is_environment_scenes = True
                    print(f"🔍 [DEBUG] 检测到Environment/Scenes材质文件: {os.path.basename(file_path)}")
                    print(f"   完整路径: {file_path}")
                    print(f"   标准化路径: {normalized_path}")
                    print(f"   路径部分: {remaining_parts[:3]}")  # 显示前3个部分
                
                # 所有entity下的材质文件都需要检查（包括Environment/Scenes）
                material_files.append((file_path, is_environment_scenes))
            
            self.status_updated.emit(f"找到 {len(material_files)} 个需要检查的材质文件")
            
            # 检查每个材质文件的模板使用情况
            for file_path, is_environment_scenes in material_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查文件是否在Timeline文件夹下
                    is_timeline_material = False
                    normalized_path = os.path.normpath(file_path)
                    path_parts = normalized_path.split(os.sep)
                    
                    # 查找entity目录索引
                    entity_index = -1
                    for i, part in enumerate(path_parts):
                        if part.lower() == 'entity':
                            entity_index = i
                            break
                    
                    if entity_index != -1:
                        # 检查是否在entity/.../Timeline/...路径下
                        remaining_parts = path_parts[entity_index + 1:]
                        for part in remaining_parts:
                            if part.lower() == 'timeline':
                                is_timeline_material = True
                                break
                    
                    # 查找模板引用
                    template_references = self._find_template_references(content)
                    
                    if not template_references:
                        # 没有找到模板引用，这可能是问题
                        issues.append({
                            'file': file_path,
                            'type': 'no_template_found',
                            'message': '未找到材质模板引用'
                        })
                    else:
                        # 检查使用的模板是否在允许列表中
                        found_valid_template = False
                        for template_name in template_references:
                            # 跳过GUID引用，这些不是实际的模板名称
                            if template_name.startswith('TEMPLATE_GUID:'):
                                continue
                            
                            if template_name in allowed_templates:
                                # 记录使用了正确的模板（信息性）
                                self.status_updated.emit(f"✅ {os.path.basename(file_path)} 使用了正确模板: {template_name}")
                                found_valid_template = True
                            elif is_timeline_material and template_name in timeline_allowed_templates:
                                # Timeline特殊规则检查
                                self.status_updated.emit(f"✅ {os.path.basename(file_path)} (Timeline) 使用了允许的特殊模板: {template_name}")
                                found_valid_template = True
                            elif is_environment_scenes and template_name == 'DefaultToonMat.templatemat':
                                # 🆕 Environment/Scenes特殊规则：允许使用DefaultToonMat.templatemat
                                self.status_updated.emit(f"✅ {os.path.basename(file_path)} (Environment/Scenes) 使用了允许的特殊模板: {template_name}")
                                found_valid_template = True
                            else:
                                # 提供更详细的错误信息，包括特殊文件夹下可用的模板
                                if is_timeline_material:
                                    message = f'使用了不允许的材质模板: {template_name} (Timeline文件夹下可额外使用: DefaultMaterial.templatemat, DefaultToonMat.templatemat)'
                                elif is_environment_scenes:
                                    message = f'使用了不允许的材质模板: {template_name} (Environment/Scenes路径下只允许使用DefaultToonMat.templatemat或标准模板)'
                                else:
                                    message = f'使用了不允许的材质模板: {template_name}'
                                
                                issues.append({
                                    'file': file_path,
                                    'type': 'invalid_template',
                                    'message': message,
                                    'template_name': template_name
                                })
                        
                        # 如果只找到了GUID引用而没有找到实际的模板名称，视为没有模板
                        if not found_valid_template and all(ref.startswith('TEMPLATE_GUID:') for ref in template_references):
                            issues.append({
                                'file': file_path,
                                'type': 'no_template_found',
                                'message': '未找到材质模板引用（仅找到GUID引用）'
                            })
                    
                except Exception as e:
                    issues.append({
                        'file': file_path,
                        'type': 'template_check_error',
                        'message': f'材质模板检查失败: {str(e)}'
                    })
            
            if issues:
                blocking_issues = [issue for issue in issues if issue.get('type') != 'no_template_found']
                if blocking_issues:
                    self.status_updated.emit(f"材质模板检查完成，发现 {len(blocking_issues)} 个问题")
                else:
                    self.status_updated.emit(f"材质模板检查完成，发现 {len(issues)} 个警告")
            else:
                self.status_updated.emit("✅ 材质模板检查通过，所有材质都使用了正确的模板")
                
        except Exception as e:
            issues.append({
                'file': 'SYSTEM',
                'type': 'template_check_system_error',
                'message': f'材质模板检查系统错误: {str(e)}'
            })
        
        return issues

    def _find_template_references(self, content: str) -> List[str]:
        """查找材质文件中的模板引用"""
        template_references = []
        
        try:
            # 查找templatemat引用
            import re
            
            # 使用多种模式查找模板引用
            template_patterns = [
                # 直接的templatemat引用
                r'templatemat:\s*([^\s\n]+\.templatemat)',
                # template引用
                r'template:\s*([^\s\n]+\.templatemat)',
                # 任何.templatemat文件引用
                r'([A-Za-z_][A-Za-z0-9_]*\.templatemat)',
                # JSON格式的templatemat引用
                r'"templatemat":\s*"([^"]+\.templatemat)"',
                # 其他可能的格式
                r'templatemat["\']?\s*[:=]\s*["\']?([^"\'\s\n]+\.templatemat)',
            ]
            
            found_templates = set()
            for pattern in template_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    template_name = match.strip().strip('"\'')
                    if template_name and template_name.endswith('.templatemat'):
                        found_templates.add(template_name)
            
            # 转换为列表
            template_references = list(found_templates)
            
            # 如果还没找到，查找可能的GUID引用（作为备选方案）
            if not template_references:
                guid_pattern = r'guid:\s*([a-f0-9]{32})'
                guid_matches = re.findall(guid_pattern, content, re.IGNORECASE)
                
                for guid in guid_matches:
                    # 标记为GUID引用，以便后续处理
                    template_references.append(f'TEMPLATE_GUID:{guid}')
            
        except Exception as e:
            debug_print(f"查找模板引用失败: {str(e)}")
        
        return template_references
    
    def _find_defaulttoon_referenced_images(self) -> Set[str]:
        """找到所有使用DefaultToonMat.templatemat的材质文件引用的贴图文件"""
        referenced_images = set()
        
        try:
            # 找到所有使用DefaultToonMat.templatemat的材质文件
            defaulttoon_materials = []
            for file_path in self.upload_files:
                if file_path.lower().endswith('.mat'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 查找模板引用
                        template_references = self._find_template_references(content)
                        
                        # 检查是否使用DefaultToonMat.templatemat
                        if 'DefaultToonMat.templatemat' in template_references:
                            defaulttoon_materials.append(file_path)
                            print(f"🔍 [DEBUG] 找到使用DefaultToonMat.templatemat的材质: {os.path.basename(file_path)}")
                    except Exception as e:
                        debug_print(f"检查材质文件失败 {file_path}: {str(e)}")
            
            # 对每个DefaultToonMat材质文件，找到它引用的贴图
            for mat_file in defaulttoon_materials:
                try:
                    with open(mat_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 使用ResourceDependencyAnalyzer来解析依赖
                    dependencies = self.analyzer.parse_editor_asset(mat_file)
                    
                    # 找到对应的贴图文件
                    for guid in dependencies:
                        # 在上传文件中查找对应GUID的图片文件
                        for upload_file in self.upload_files:
                            _, ext = os.path.splitext(upload_file.lower())
                            if ext in self.image_types:
                                meta_file = upload_file + '.meta'
                                if os.path.exists(meta_file):
                                    try:
                                        file_guid = self.analyzer.parse_meta_file(meta_file)
                                        if file_guid == guid:
                                            referenced_images.add(upload_file)
                                            print(f"🔍 [DEBUG] DefaultToonMat材质 {os.path.basename(mat_file)} 引用贴图: {os.path.basename(upload_file)}")
                                            break
                                    except Exception as e:
                                        debug_print(f"解析meta文件失败 {meta_file}: {str(e)}")
                        
                except Exception as e:
                    debug_print(f"分析材质依赖失败 {mat_file}: {str(e)}")
                    
        except Exception as e:
            debug_print(f"查找DefaultToonMat引用的贴图失败: {str(e)}")
        
        print(f"🔍 [DEBUG] 总共找到 {len(referenced_images)} 个被DefaultToonMat.templatemat引用的贴图文件")
        return referenced_images
    
    def _is_environment_scenes_path(self, file_path: str) -> bool:
        """检查文件是否在Assets/entity/Environment/Scenes路径下"""
        try:
            # 🚨 路径分隔符统一处理：将所有路径统一为正斜杠格式进行比较
            normalized_path = os.path.normpath(file_path).replace('\\', '/')
            path_parts = normalized_path.split('/')
            
            # 查找entity目录
            entity_index = -1
            for i, part in enumerate(path_parts):
                if part.lower() == 'entity':
                    entity_index = i
                    break
            
            if entity_index == -1:
                return False
            
            # 检查是否在entity/Environment/Scenes路径下
            remaining_parts = path_parts[entity_index + 1:]
            print(f"🔍 [DEBUG] _is_environment_scenes_path 检查:")
            print(f"   文件: {os.path.basename(file_path)}")
            print(f"   标准化路径: {normalized_path}")
            print(f"   entity后的路径部分: {remaining_parts}")
            print(f"   检查条件: len >= 2? {len(remaining_parts) >= 2}")
            if len(remaining_parts) >= 2:
                print(f"   第1部分: '{remaining_parts[0]}' == 'environment'? {remaining_parts[0].lower() == 'environment'}")
                print(f"   第2部分: '{remaining_parts[1]}' == 'scenes'? {remaining_parts[1].lower() == 'scenes'}")
            
            if (len(remaining_parts) >= 2 and 
                remaining_parts[0].lower() == 'environment' and 
                remaining_parts[1].lower() == 'scenes'):
                print(f"   ✅ 匹配Environment/Scenes路径")
                return True
            
            print(f"   ❌ 不匹配Environment/Scenes路径")
            return False
            
        except Exception:
            return False

    def _check_folder_filelist(self, folder_type: str) -> List[Dict[str, str]]:
        """检查指定文件夹中的all.filelist文件完整性
        
        Args:
            folder_type: 文件夹类型，支持 'avatar' 或 'weapon'
        """
        issues = []
        
        try:
            self.status_updated.emit(f"🔍 开始{folder_type.title()}文件夹all.filelist检查...")
            
            # 收集指定文件夹下的上传文件包
            folder_packages = {}  # {package_path: [files_in_package]}
            
            for file_path in self.upload_files:
                try:
                    # 标准化路径
                    normalized_path = os.path.normpath(file_path).replace('\\', '/')
                    
                    # 检查是否在指定文件夹中 - 支持avatar/MiniUniverse子目录
                    folder_pattern = f'/{folder_type}/'
                    miniuniverse_pattern = f'/{folder_type}/miniuniverse/'  # 新增：支持MiniUniverse子目录
                    
                    folder_pos = -1
                    actual_folder_type = folder_type
                    
                    # 首先检查是否在MiniUniverse子目录下
                    if miniuniverse_pattern in normalized_path.lower():
                        folder_pos = normalized_path.lower().find(miniuniverse_pattern)
                        actual_folder_type = f"{folder_type}/MiniUniverse"
                        folder_pattern = miniuniverse_pattern
                    elif folder_pattern in normalized_path.lower():
                        folder_pos = normalized_path.lower().find(folder_pattern)
                    
                    if folder_pos != -1:
                        # 提取文件夹后的路径部分
                        after_folder = normalized_path[folder_pos + len(folder_pattern):]
                        
                        # 查找文件夹下的文件包目录（如 1000_1018, 2000_237）
                        if '/' in after_folder:
                            package_name = after_folder.split('/')[0]  # 获取文件包名
                            
                            # 重构完整的文件包路径
                            package_path = normalized_path[:folder_pos] + folder_pattern[:-1] + '/' + package_name
                            
                            if package_path not in folder_packages:
                                folder_packages[package_path] = []
                            folder_packages[package_path].append(file_path)
                            
                            debug_print(f"发现{actual_folder_type}文件包: {package_name}, 文件: {os.path.basename(file_path)}")
                            
                except Exception as e:
                    debug_print(f"处理文件路径失败 {file_path}: {e}")
                    continue
            
            if not folder_packages:
                self.status_updated.emit(f"✅ 没有发现{folder_type}文件夹(包括MiniUniverse子目录)下的文件，跳过检查")
                return issues
            
            # 统计普通avatar和MiniUniverse的文件包数量
            normal_packages = 0
            miniuniverse_packages = 0
            for package_path in folder_packages.keys():
                if '/miniuniverse/' in package_path.lower():
                    miniuniverse_packages += 1
                else:
                    normal_packages += 1
            
            status_msg = f"发现 {len(folder_packages)} 个{folder_type}文件包需要检查"
            if miniuniverse_packages > 0:
                status_msg += f" (其中{miniuniverse_packages}个在MiniUniverse子目录)"
            self.status_updated.emit(status_msg)
            
            # 检查每个文件包
            for package_path, files_in_package in folder_packages.items():
                package_name = os.path.basename(package_path)
                
                # 确定文件包的位置（普通avatar还是MiniUniverse）
                if '/miniuniverse/' in package_path.lower():
                    location_info = f"{folder_type}/MiniUniverse"
                else:
                    location_info = folder_type
                
                self.status_updated.emit(f"检查{location_info}文件包: {package_name}")
                
                # 查找all.filelist文件
                all_filelist_path = None
                for file_path in files_in_package:
                    if os.path.basename(file_path).lower() == 'all.filelist':
                        all_filelist_path = file_path
                        break
                
                if not all_filelist_path:
                    issues.append({
                        'file': package_path,
                        'type': f'{folder_type}_missing_filelist',
                        'message': f'{location_info}文件包 {package_name} 缺少 all.filelist 文件'
                    })
                    continue
                
                # 读取all.filelist的原始内容和解析后的GUID
                try:
                    with open(all_filelist_path, 'r', encoding='utf-8') as f:
                        filelist_content = f.read()
                    
                    # 解析标准格式的GUID（32位）
                    filelist_guids = self._parse_all_filelist(all_filelist_path)
                    if not filelist_content.strip():
                        issues.append({
                            'file': all_filelist_path,
                            'type': f'{folder_type}_empty_filelist',
                            'message': f'all.filelist 文件为空'
                        })
                        continue
                    
                except Exception as e:
                    issues.append({
                        'file': all_filelist_path,
                        'type': f'{folder_type}_filelist_parse_error',
                        'message': f'all.filelist 文件解析失败: {str(e)}'
                    })
                    continue
                
                # 收集文件包内所有文件的GUID
                package_guids = self._collect_folder_guids(files_in_package)
                
                # 分析GUID问题：区分缺失和格式错误
                guid_issues = self._analyze_guid_issues(package_guids, filelist_guids, filelist_content)
                
                missing_guids = []
                if guid_issues:
                    missing_guids = guid_issues
                
                # 报告缺失的GUID
                if missing_guids:
                    missing_files = ', '.join([os.path.basename(item['file']) for item in missing_guids[:5]])
                    if len(missing_guids) > 5:
                        missing_files += f" 等{len(missing_guids)}个文件"
                    
                    issues.append({
                        'file': all_filelist_path,
                        'type': f'{folder_type}_filelist_incomplete',
                        'message': f'all.filelist 缺少 {len(missing_guids)} 个文件的GUID记录: {missing_files}',
                        'missing_guids': missing_guids,
                        'package_name': package_name
                    })
                else:
                    self.status_updated.emit(f"✅ {location_info}文件包 {package_name} 的all.filelist检查通过")
            
            if issues:
                summary_msg = f"{folder_type.title()}文件包all.filelist检查完成，发现 {len(issues)} 个问题"
                if miniuniverse_packages > 0:
                    summary_msg += f" (包含MiniUniverse子目录检查)"
                self.status_updated.emit(summary_msg)
            else:
                summary_msg = f"✅ 所有{folder_type.title()}文件包的all.filelist检查通过"
                if miniuniverse_packages > 0:
                    summary_msg += f" (包含{miniuniverse_packages}个MiniUniverse文件包)"
                self.status_updated.emit(summary_msg)
                
        except Exception as e:
            issues.append({
                'file': 'SYSTEM',
                'type': f'{folder_type}_filelist_system_error',
                'message': f'{folder_type.title()}文件包all.filelist检查系统错误: {str(e)}'
            })
        
        return issues

    def _check_avatar_filelist(self) -> List[Dict[str, str]]:
        """检查avatar文件夹中的all.filelist文件完整性"""
        return self._check_folder_filelist('avatar')
        
    def _check_weapon_filelist(self) -> List[Dict[str, str]]:
        """检查weapon文件夹中的all.filelist文件完整性"""
        return self._check_folder_filelist('weapon')
    
    def _check_prefab_naming_convention(self) -> List[Dict[str, str]]:
        """检查预制体文件名是否符合命名规范"""
        issues = []
        
        for file_path in self.upload_files:
            if not file_path.lower().endswith('.prefab'):
                continue
                
            try:
                # 标准化路径
                normalized_path = os.path.normpath(file_path).replace('\\', '/')
                
                # 检查是否在avatar目录下（包括MiniUniverse子目录）
                if '/avatar/' in normalized_path:
                    # 提取路径信息
                    path_parts = normalized_path.split('/')
                    avatar_index = -1
                    
                    # 找到avatar目录的位置
                    for i, part in enumerate(path_parts):
                        if part == 'avatar':
                            avatar_index = i
                            break
                    
                    if avatar_index != -1:
                        # 检查是否在MiniUniverse子目录下
                        is_miniuniverse = False
                        target_dir_index = avatar_index + 1
                        
                        if (avatar_index + 1 < len(path_parts) and 
                            path_parts[avatar_index + 1].lower() == 'miniuniverse'):
                            # 在MiniUniverse子目录下，实际的目录名在下一级
                            is_miniuniverse = True
                            target_dir_index = avatar_index + 2
                        
                        if target_dir_index < len(path_parts):
                            # 获取目标目录名 (如: 1000_3512)
                            target_dir = path_parts[target_dir_index]
                            
                            # 获取文件名 (不包含扩展名)
                            file_name = os.path.splitext(os.path.basename(file_path))[0]
                            
                            # 检查命名规范
                            naming_issue = self._validate_prefab_name(target_dir, file_name, normalized_path, is_miniuniverse)
                            if naming_issue:
                                issues.append({
                                    'type': 'prefab_naming_violation',
                                    'file': file_path,
                                    'message': naming_issue,
                                    'severity': 'error'
                                })
                                
                                # 更新状态信息
                                location_info = "avatar/MiniUniverse" if is_miniuniverse else "avatar"
                                self.status_updated.emit(f"❌ {location_info}预制体文件名检查错误: {os.path.basename(file_path)}")
                        
            except Exception as e:
                issues.append({
                    'type': 'prefab_naming_check_error',
                    'file': file_path,
                    'message': f"检查预制体文件名时发生错误: {str(e)}",
                    'severity': 'warning'
                })
        
        return issues
    
    def _is_english_prefab_with_particle_system(self, file_name: str, prefab_path: str) -> bool:
        """
        检查prefab文件是否为英文名且包含ParticleSystem组件
        
        Args:
            file_name: 文件名（不含扩展名）
            prefab_path: prefab文件的完整路径
            
        Returns:
            如果是英文名且包含ParticleSystem组件返回True，否则返回False
        """
        import re
        
        # 1. 检查是否为英文名（只包含英文字母、数字、下划线）
        if not re.match(r'^[a-zA-Z0-9_]+$', file_name):
            return False
        
        # 2. 检查是否包含ParticleSystem组件
        try:
            with open(prefab_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含ParticleSystem组件的标识
            # Unity中ParticleSystem通常在JSON/YAML中有这些特征
            particle_system_indicators = [
                '"ParticleSystem"',
                "'ParticleSystem'",
                'ParticleSystem',
                'm_ParticleSystem',
            ]
            
            for indicator in particle_system_indicators:
                if indicator in content:
                    return True
            
            return False
            
        except Exception as e:
            # 如果读取失败，返回False
            print(f"⚠️ 检查ParticleSystem组件失败: {os.path.basename(prefab_path)}, 错误: {str(e)}")
            return False
    
    def _validate_prefab_name(self, avatar_dir: str, file_name: str, full_path: str, is_miniuniverse: bool = False) -> str:
        """
        验证预制体文件名是否符合avatar目录命名规范（支持普通avatar和MiniUniverse子目录）
        
        Args:
            avatar_dir: avatar目录名 (如: 1000_3512)
            file_name: 预制体文件名 (不含扩展名, 如: 3215_2)
            full_path: 完整路径 (用于错误信息)
            is_miniuniverse: 是否在MiniUniverse子目录下
        
        Returns:
            错误信息字符串，如果符合规范则返回空字符串
        """
        try:
            # 解析avatar目录名，提取ID部分
            if '_' in avatar_dir:
                # 格式: 1000_3512 -> 期望文件名: 3512 或 3512_X
                avatar_parts = avatar_dir.split('_')
                if len(avatar_parts) >= 2:
                    expected_base = avatar_parts[1]  # 3512
                    
                    # 检查文件名是否符合规范
                    if file_name == expected_base:
                        # 完全匹配: 3512.prefab ✅
                        return ""
                    elif file_name.startswith(expected_base + '_'):
                        # 带序号匹配: 3512_2.prefab ✅
                        suffix = file_name[len(expected_base + '_'):]
                        if suffix.isdigit():
                            return ""
                        else:
                            location_prefix = "avatar/MiniUniverse" if is_miniuniverse else "avatar"
                            return (f"预制体文件名不符合规定，发现其文件名 {file_name}.prefab 不符合规定，"
                                  f"预期应为 {expected_base}.prefab 或 {expected_base}_数字.prefab "
                                  f"(位置: {location_prefix}目录下)")
                    elif self._is_english_prefab_with_particle_system(file_name, full_path):
                        # 英文名且包含ParticleSystem组件，检测通过 ✅
                        return ""
                    else:
                        # 不匹配 ❌
                        location_prefix = "avatar/MiniUniverse" if is_miniuniverse else "avatar"
                        return (f"预制体文件名不符合规定，发现其文件名 {file_name}.prefab 不符合规定，"
                              f"预期应为 {expected_base}.prefab 或 {expected_base}_数字.prefab "
                              f"(位置: {location_prefix}目录下)")
                else:
                    return f"无法解析avatar目录名格式: {avatar_dir}"
            else:
                # 没有下划线的目录名，直接使用目录名作为期望文件名
                if file_name == avatar_dir or file_name.startswith(avatar_dir + '_'):
                    return ""
                elif self._is_english_prefab_with_particle_system(file_name, full_path):
                    # 英文名且包含ParticleSystem组件，检测通过 ✅
                    return ""
                else:
                    location_prefix = "avatar/MiniUniverse" if is_miniuniverse else "avatar"
                    return (f"预制体文件名不符合规定，发现其文件名 {file_name}.prefab 不符合规定，"
                          f"预期应为 {avatar_dir}.prefab 或 {avatar_dir}_数字.prefab "
                          f"(位置: {location_prefix}目录下)")
                          
        except Exception as e:
            return f"验证预制体文件名时发生错误: {str(e)}"
    
    def _check_file_extension_case(self) -> List[Dict[str, str]]:
        """检查文件扩展名大小写规范 - 仅检查图片格式"""
        issues = []
        
        # 定义应该使用小写的文件扩展名 - 仅包含图片格式
        lowercase_extensions = {
            # 图片文件
            '.png', '.jpg', '.jpeg', '.tga', '.bmp', '.psd', '.tiff', '.exr', '.hdr'
        }
        
        for file_path in self.upload_files:
            try:
                # 获取文件扩展名
                _, ext = os.path.splitext(file_path)
                
                if ext:  # 如果有扩展名
                    ext_lower = ext.lower()
                    
                    # 检查是否在需要小写的扩展名列表中
                    if ext_lower in lowercase_extensions:
                        # 检查是否有大写字母
                        if ext != ext_lower:
                            # 特别检查avatar目录
                            is_avatar_file = '/avatar/' in file_path.replace('\\', '/')
                            
                            # 确定严重程度
                            severity = 'error' if is_avatar_file else 'warning'
                            
                            # 生成建议的正确文件名
                            file_dir = os.path.dirname(file_path)
                            file_basename = os.path.basename(file_path)
                            correct_basename = os.path.splitext(file_basename)[0] + ext_lower
                            correct_path = os.path.join(file_dir, correct_basename)
                            
                            issues.append({
                                'type': 'file_extension_case_violation',
                                'file': file_path,
                                'message': (
                                    f"文件扩展名大小写不规范：发现扩展名 '{ext}'，"
                                    f"应使用小写 '{ext_lower}'。"
                                    f"建议重命名为：{correct_basename}"
                                ),
                                'severity': severity,
                                'current_extension': ext,
                                'expected_extension': ext_lower,
                                'suggested_filename': correct_basename,
                                'is_avatar_file': is_avatar_file
                            })
                            
                            # 更新状态信息
                            status_icon = "🔴" if is_avatar_file else "⚠️"
                            self.status_updated.emit(
                                f"{status_icon} 扩展名大小写错误: {os.path.basename(file_path)} "
                                f"({ext} → {ext_lower})"
                            )
                        
            except Exception as e:
                issues.append({
                    'type': 'extension_case_check_error',
                    'file': file_path,
                    'message': f"检查文件扩展名大小写时发生错误: {str(e)}",
                    'severity': 'warning'
                })
        
        return issues
    
    def _check_override_controller_cache(self) -> List[Dict[str, str]]:
        """检查overrideController缓存问题 - 检测丢失的动画片段引用"""
        issues = []
        
        # 收集所有上传文件中的GUID映射
        available_guids = set()
        for file_path in self.upload_files:
            try:
                if file_path.endswith('.meta'):
                    guid = self.analyzer.parse_meta_file(file_path)
                    if guid:
                        available_guids.add(guid.lower())
                else:
                    meta_path = file_path + '.meta'
                    if os.path.exists(meta_path):
                        guid = self.analyzer.parse_meta_file(meta_path)
                        if guid:
                            available_guids.add(guid.lower())
            except Exception as e:
                continue
        
        # 检查Git仓库中的GUID
        try:
            git_guids = self.analyzer._get_git_repository_guids(self.git_manager.repo_path)
            available_guids.update(guid.lower() for guid in git_guids.keys())
        except Exception as e:
            self.status_updated.emit(f"⚠️ 获取Git仓库GUID失败: {str(e)}")
        
        # 检查SVN仓库中的GUID
        try:
            svn_root = self.analyzer._find_svn_root_from_files(self.upload_files)
            if svn_root:
                svn_guid_map = {}
                self.analyzer._scan_directory_for_guids(svn_root, svn_guid_map)
                available_guids.update(guid.lower() for guid in svn_guid_map.keys())
        except Exception as e:
            self.status_updated.emit(f"⚠️ 获取SVN仓库GUID失败: {str(e)}")
        
        # 检查所有overrideController文件
        for file_path in self.upload_files:
            if not file_path.lower().endswith('.overridecontroller'):
                continue
                
            try:
                self.status_updated.emit(f"🔍 检查overrideController: {os.path.basename(file_path)}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析JSON内容
                import json
                try:
                    controller_data = json.loads(content)
                except json.JSONDecodeError:
                    issues.append({
                        'type': 'override_controller_parse_error',
                        'file': file_path,
                        'message': f"overrideController文件格式错误，无法解析JSON内容",
                        'severity': 'warning'
                    })
                    continue
                
                # 提取所有GUID引用
                missing_guids = []
                total_refs = 0
                
                def extract_guids_from_object(obj, path=""):
                    nonlocal total_refs, missing_guids
                    
                    if isinstance(obj, dict):
                        # 特殊处理 m_OverrideClip 字段
                        if "m_OverrideClip" in obj and isinstance(obj["m_OverrideClip"], dict):
                            override_clip = obj["m_OverrideClip"]
                            if "m_GUID" in override_clip and isinstance(override_clip["m_GUID"], str):
                                guid = override_clip["m_GUID"]
                                if len(guid) == 32:
                                    total_refs += 1
                                    guid_lower = guid.lower()
                                    
                                    # 00000000000000000000000000000000 是正常的，表示没有赋予动画片段
                                    if guid_lower == "00000000000000000000000000000000":
                                        # 这是正常情况，不报错
                                        pass
                                    elif (not guid_lower.startswith('00000000000000') and
                                          guid_lower not in self.builtin_guids and
                                          guid_lower not in available_guids):
                                        
                                        # 检查是否是动画片段引用
                                        is_animation_clip = self._is_animation_clip_reference(obj, path)
                                        
                                        missing_guids.append({
                                            'guid': guid_lower,
                                            'path': f"{path}.m_OverrideClip.m_GUID",
                                            'context': "动画片段引用" if is_animation_clip else "overrideClip引用",
                                            'is_animation_clip': is_animation_clip,
                                            'original_clip': obj.get("m_OriginalClip", {}).get("m_GUID", "未知")
                                        })
                        
                        # 继续处理其他GUID字段
                        for key, value in obj.items():
                            if key == "m_GUID" and isinstance(value, str) and len(value) == 32:
                                # 如果不是 m_OverrideClip 中的 GUID，按原逻辑处理
                                if not (path.endswith("m_OverrideClip") or "m_OverrideClip" in path):
                                    total_refs += 1
                                    guid_lower = value.lower()
                                    
                                    # 跳过内置GUID、全零GUID和自身GUID
                                    if (guid_lower != "00000000000000000000000000000000" and
                                        not guid_lower.startswith('00000000000000') and
                                        guid_lower not in self.builtin_guids and
                                        guid_lower not in available_guids):
                                        
                                        missing_guids.append({
                                            'guid': guid_lower,
                                            'path': f"{path}.{key}" if path else key,
                                            'context': self._get_override_controller_context(obj, key),
                                            'is_animation_clip': False
                                        })
                            else:
                                extract_guids_from_object(value, f"{path}.{key}" if path else key)
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            extract_guids_from_object(item, f"{path}[{i}]" if path else f"[{i}]")
                
                # 提取所有GUID
                extract_guids_from_object(controller_data)
                
                # 如果发现丢失的GUID，报告问题
                if missing_guids:
                    # 分析丢失GUID的类型
                    animation_clip_guids = []
                    controller_guids = []
                    other_guids = []
                    
                    # 生成详细的丢失动画片段信息
                    missing_clips_details = []
                    
                    for missing in missing_guids:
                        if missing.get('is_animation_clip', False):
                            animation_clip_guids.append(missing)
                            # 添加详细信息，包括原始片段GUID
                            original_clip = missing.get('original_clip', '未知')
                            missing_clips_details.append({
                                'missing_guid': missing['guid'],
                                'original_clip': original_clip,
                                'path': missing['path']
                            })
                        elif 'controller' in missing['context'].lower():
                            controller_guids.append(missing)
                        else:
                            other_guids.append(missing)
                    
                    # 生成详细的错误信息
                    details = []
                    if animation_clip_guids:
                        details.append(f"丢失动画片段: {len(animation_clip_guids)}个")
                    if controller_guids:
                        details.append(f"丢失控制器引用: {len(controller_guids)}个")
                    if other_guids:
                        details.append(f"其他丢失引用: {len(other_guids)}个")
                    
                    # 生成更详细的错误消息
                    error_message = f"overrideController存在缓存问题：发现{len(missing_guids)}个丢失的引用。"
                    if animation_clip_guids:
                        error_message += f"\n特别注意：{len(animation_clip_guids)}个m_OverrideClip动画片段引用丢失，这些片段的meta文件在项目中找不到。"
                    error_message += f"\n详情：{', '.join(details)}。"
                    error_message += f"\n建议：在引擎编辑器中重新打开并保存此overrideController文件以刷新缓存，或者检查引用的动画文件是否存在。"
                    
                    issues.append({
                        'type': 'override_controller_missing_references',
                        'file': file_path,
                        'message': error_message,
                        'severity': 'error',
                        'missing_count': len(missing_guids),
                        'total_references': total_refs,
                        'missing_guids': [m['guid'] for m in missing_guids[:5]],  # 只保存前5个用于显示
                        'animation_clips': len(animation_clip_guids),
                        'controllers': len(controller_guids),
                        'others': len(other_guids),
                        'missing_clips_details': missing_clips_details[:3],  # 保存前3个详细信息
                        'fix_suggestion': "在引擎编辑器中重新打开并保存overrideController文件"
                    })
                    
                    # 更新状态显示
                    self.status_updated.emit(
                        f"🔴 overrideController缓存问题: {os.path.basename(file_path)} "
                        f"({len(missing_guids)}个丢失引用)"
                    )
                else:
                    # 没有问题的情况
                    self.status_updated.emit(
                        f"✅ overrideController正常: {os.path.basename(file_path)} "
                        f"({total_refs}个引用都有效)"
                    )
                        
            except Exception as e:
                issues.append({
                    'type': 'override_controller_check_error',
                    'file': file_path,
                    'message': f"检查overrideController时发生错误: {str(e)}",
                    'severity': 'warning'
                })
                
        return issues
    
    def _is_animation_clip_reference(self, obj: dict, path: str) -> bool:
        """判断是否是动画片段引用"""
        try:
            # 检查对象中是否包含 m_OriginalClip 和 m_OverrideClip，这是动画片段替换的典型结构
            if "m_OriginalClip" in obj and "m_OverrideClip" in obj:
                return True
            
            # 检查路径中是否包含动画相关关键词
            path_lower = path.lower()
            animation_keywords = ['clip', 'animation', 'anim', 'override']
            for keyword in animation_keywords:
                if keyword in path_lower:
                    return True
            
            return False
        except:
            return False
    
    def _get_override_controller_context(self, obj: dict, guid_key: str) -> str:
        """获取overrideController中GUID的上下文信息"""
        try:
            # 检查父级对象的类型信息
            context_clues = []
            
            # 检查同级键名
            for key in obj.keys():
                if 'animation' in key.lower():
                    context_clues.append('动画')
                elif 'clip' in key.lower():
                    context_clues.append('片段')
                elif 'controller' in key.lower():
                    context_clues.append('控制器')
                elif 'state' in key.lower():
                    context_clues.append('状态')
                elif 'transition' in key.lower():
                    context_clues.append('转换')
            
            if context_clues:
                return f"{'/'.join(context_clues)}引用"
            else:
                return "未知类型引用"
                
        except:
            return "引用"
    
    def _parse_all_filelist(self, filelist_path: str) -> Set[str]:
        """解析all.filelist文件，提取GUID列表（忽略**符号等特殊标记）"""
        guids = set()
        
        try:
            with open(filelist_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找所有GUID模式（32位十六进制字符）
            import re
            # 使用更全面的模式，包括处理**符号和其他特殊字符的情况
            # 匹配冒号后、空格/制表符后、或行首的32位十六进制GUID
            guid_pattern = r'[:\s\t*]+([a-f0-9]{32})|^([a-f0-9]{32})'
            raw_matches = re.findall(guid_pattern, content, re.IGNORECASE | re.MULTILINE)
            
            # 合并匹配组的结果
            matches = []
            for match_group in raw_matches:
                for group in match_group:
                    if group:  # 非空组
                        matches.append(group)
            
            # 额外处理：使用更简单的模式作为补充，确保不遗漏任何GUID
            # 查找所有独立的32位十六进制字符串
            simple_pattern = r'\b([a-f0-9]{32})\b'
            simple_matches = re.findall(simple_pattern, content, re.IGNORECASE)
            
            # 合并所有匹配结果
            all_matches = matches + simple_matches
            
            for guid in all_matches:
                if len(guid) == 32:  # 确保是32位GUID
                    guids.add(guid.lower())
            
            debug_print(f"从 {os.path.basename(filelist_path)} 解析出 {len(guids)} 个GUID（支持**符号等特殊格式）")
            
        except Exception as e:
            debug_print(f"解析all.filelist文件失败 {filelist_path}: {e}")
        
        return guids
    
    def _collect_folder_guids(self, file_list: List[str]) -> Dict[str, str]:
        """收集文件夹内所有文件的GUID"""
        folder_guids = {}  # {file_path: guid}
        
        for file_path in file_list:
            try:
                # 跳过all.filelist文件本身
                if os.path.basename(file_path).lower() == 'all.filelist':
                    continue
                
                # 跳过.meta文件（这些文件的GUID由对应的资源文件表示）
                if file_path.lower().endswith('.meta'):
                    continue
                
                # 尝试获取文件的GUID
                file_guid = None
                
                # 1. 优先从对应的.meta文件中获取GUID（最可靠）
                meta_path = file_path + '.meta'
                if os.path.exists(meta_path):
                    file_guid = self.analyzer.parse_meta_file(meta_path)
                    if file_guid:
                        debug_print(f"从meta文件获取GUID: {os.path.basename(file_path)} -> {file_guid}")
                
                # 2. 如果.meta文件不存在或无法解析，尝试直接从文件内容获取
                if not file_guid:
                    try:
                        guids = self.analyzer.parse_editor_asset(file_path)
                        if guids:
                            # 取第一个GUID作为文件的主GUID
                            file_guid = next(iter(guids))
                            debug_print(f"从文件内容获取GUID: {os.path.basename(file_path)} -> {file_guid}")
                    except Exception as e:
                        debug_print(f"从文件内容获取GUID失败 {os.path.basename(file_path)}: {e}")
                
                # 3. 如果仍然没有GUID，尝试使用更详细的解析方法
                if not file_guid:
                    try:
                        import json
                        with open(meta_path if os.path.exists(meta_path) else file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 尝试JSON解析
                        try:
                            data = json.loads(content)
                            if 'm_MetaHeader' in data and 'm_GUID' in data['m_MetaHeader']:
                                file_guid = data['m_MetaHeader']['m_GUID']
                                debug_print(f"JSON解析获取GUID: {os.path.basename(file_path)} -> {file_guid}")
                        except:
                            # 使用正则表达式作为最后手段
                            import re
                            guid_match = re.search(r'"?m_GUID"?\s*:?\s*"?([a-f0-9]{32})"?', content, re.IGNORECASE)
                            if guid_match:
                                file_guid = guid_match.group(1)
                                debug_print(f"正则表达式获取GUID: {os.path.basename(file_path)} -> {file_guid}")
                    except Exception as e:
                        debug_print(f"详细解析GUID失败 {os.path.basename(file_path)}: {e}")
                
                if file_guid and len(file_guid) == 32:
                    folder_guids[file_path] = file_guid.lower()
                    debug_print(f"✅ 收集到文件GUID: {os.path.basename(file_path)} -> {file_guid}")
                else:
                    debug_print(f"❌ 无法获取有效GUID: {os.path.basename(file_path)}")
                
            except Exception as e:
                debug_print(f"收集文件GUID失败 {file_path}: {e}")
                continue
        
        return folder_guids

    def _analyze_guid_issues(self, package_guids: Dict[str, str], filelist_guids: Set[str], filelist_content: str) -> List[Dict[str, str]]:
        """分析GUID问题：检测缺失的GUID和GUID不一致的问题"""
        issues = []
        
        try:
            # 提取all.filelist中所有32位GUID
            import re
            all_guids_in_filelist = re.findall(r'([a-f0-9]{32})', filelist_content, re.IGNORECASE)
            all_guids_in_filelist = [guid.lower() for guid in all_guids_in_filelist]
            
            debug_print(f"all.filelist中找到的32位GUID: {len(all_guids_in_filelist)}")
            debug_print(f"解析的标准GUID: {len(filelist_guids)}")
            debug_print(f"需要检查的文件数: {len(package_guids)}")
            
            for file_path, correct_guid in package_guids.items():
                if not correct_guid:
                    continue
                
                file_name = os.path.basename(file_path)
                correct_guid_lower = correct_guid.lower()
                
                debug_print(f"检查文件: {file_name}, 正确GUID: {correct_guid_lower}")
                
                # 1. 检查是否存在正确的GUID
                if correct_guid_lower in filelist_guids:
                    debug_print(f"✅ {file_name} 的GUID正确存在")
                    continue
                
                # 2. 查找是否有错误的GUID记录
                wrong_guid = None
                for guid_in_file in all_guids_in_filelist:
                    if guid_in_file != correct_guid_lower:
                        # 检查相似度 - 如果差异较小，可能是错误的GUID
                        diff_count = sum(1 for a, b in zip(correct_guid_lower, guid_in_file) if a != b)
                        debug_print(f"  比较GUID: {guid_in_file}, 差异: {diff_count}个字符")
                        
                        # 如果差异在1-10个字符之间，认为是错误的GUID
                        if 1 <= diff_count <= 10:
                            wrong_guid = guid_in_file
                            debug_print(f"❌ {file_name} 发现错误GUID: {wrong_guid} (与正确GUID有{diff_count}处不同)")
                            break
                
                if wrong_guid:
                    # GUID不一致错误
                    issues.append({
                        'file': file_path,
                        'correct_guid': correct_guid,
                        'wrong_guid': wrong_guid,
                        'issue_type': 'format_error'
                    })
                    debug_print(f"❌ 添加GUID不一致记录: {file_name}")
                else:
                    # GUID缺失
                    issues.append({
                        'file': file_path,
                        'correct_guid': correct_guid,
                        'issue_type': 'missing'
                    })
                    debug_print(f"❌ 添加GUID缺失记录: {file_name}")
            
            debug_print(f"发现 {len(issues)} 个GUID问题")
            
        except Exception as e:
            debug_print(f"分析GUID问题失败: {e}")
            import traceback
            debug_print(f"错误详情: {traceback.format_exc()}")
        
        return issues

    def _generate_detailed_report(self, all_issues: List[Dict[str, str]], total_files: int) -> Dict[str, Any]:
        """生成详细报告 - 美术友好版本"""
        blocking_issues = []  # 初始化阻塞性错误列表
        try:
            # 区分阻塞性错误和警告/信息
            non_blocking_types = {'meta_missing_git', 'guid_file_update', 'potentially_orphaned_file', 'no_template_found'}
            blocking_issues = [issue for issue in all_issues if issue.get('type') not in non_blocking_types]
            
            # 按严重程度分类
            critical_issues = []    # 严重错误：阻止上传
            warning_issues = []     # 警告：可以上传但需要注意
            info_issues = []        # 信息：提示性信息
            
            # 定义严重程度
            critical_types = {
                'meta_missing_both', 'meta_missing_svn', 'guid_mismatch', 'guid_invalid_both',
                'guid_duplicate_internal', 'guid_duplicate_git', 'guid_reference_missing',
                'internal_dependency_missing', 'invalid_template',
                'avatar_missing_filelist', 'avatar_empty_filelist', 'avatar_filelist_parse_error',
                'avatar_filelist_incomplete', 'avatar_filelist_system_error',
                'weapon_missing_filelist', 'weapon_empty_filelist', 'weapon_filelist_parse_error',
                'weapon_filelist_incomplete', 'weapon_filelist_system_error',
                'prefab_naming_violation', 'file_extension_case_violation',
                'override_controller_missing_references', 'remote_resource_reference'
            }
            
            warning_types = {
                'chinese_filename', 'image_width_not_power_of_2', 'image_height_not_power_of_2',
                'image_too_large', 'guid_parse_error', 'template_check_error', 
                'prefab_naming_check_error', 'extension_case_check_error',
                'override_controller_parse_error', 'override_controller_check_error'
            }
            
            for issue in blocking_issues:
                issue_type = issue.get('type', 'unknown')
                if issue_type in critical_types:
                    critical_issues.append(issue)
                elif issue_type in warning_types:
                    warning_issues.append(issue)
                else:
                    info_issues.append(issue)
            
            # 按类型分组问题
            issues_by_type = {}
            for issue in blocking_issues:
                issue_type = issue.get('type', 'unknown')
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append(issue)
            
            # 生成美化报告
            report_lines = []
            
            # 报告头部 - 更加美观
            report_lines.append("╔" + "═" * 78 + "╗")
            report_lines.append("║" + "🎨 美术资源检查报告".center(78) + "║")
            report_lines.append("╚" + "═" * 78 + "╝")
            report_lines.append("")
            
            # 基本信息
            report_lines.append("📋 **检查概况**")
            report_lines.append("┌" + "─" * 50 + "┐")
            report_lines.append(f"│ 📅 检查时间: {self._get_current_time()}")
            report_lines.append(f"│ 📁 检查文件数: {total_files} 个")
            report_lines.append(f"│ 🔍 发现问题数: {len(blocking_issues)} 个")
            report_lines.append("└" + "─" * 50 + "┘")
            report_lines.append("")
            
            if blocking_issues:
                # 问题严重程度统计
                report_lines.append("🚨 **问题严重程度统计**")
                report_lines.append("┌" + "─" * 60 + "┐")
                if critical_issues:
                    report_lines.append(f"│ 🔴 **严重错误**: {len(critical_issues)} 个 (必须修复才能上传)")
                if warning_issues:
                    report_lines.append(f"│ 🟡 **警告**: {len(warning_issues)} 个 (建议修复)")
                if info_issues:
                    report_lines.append(f"│ 🔵 **信息**: {len(info_issues)} 个 (提示信息)")
                report_lines.append("└" + "─" * 60 + "┘")
                report_lines.append("")
                
                # 问题分类和友好解释
                report_lines.append("💡 **问题类型解释**")
                report_lines.append("═" * 70)
                
                # 美术友好的问题类型说明
                type_explanations = {
                    # 严重错误 - 用通俗语言解释
                    'meta_missing_both': {
                        'icon': '🔴',
                        'title': '缺少配置文件',
                        'description': '资源文件缺少必需的.meta配置文件',
                        'impact': '无法在游戏引擎中正确识别和使用',
                        'solution': '在编辑器中重新导入文件'
                    },
                    'meta_missing_svn': {
                        'icon': '🔴',
                        'title': '本地缺少配置文件',
                        'description': '本地SVN目录缺少.meta文件，但Git中存在',
                        'impact': '可能导致文件关联错误',
                        'solution': '从Git复制对应的.meta文件'
                    },
                    'meta_missing_svn_invalid_git': {
                        'icon': '🔴',
                        'title': '本地缺少配置文件且Git配置无效',
                        'description': '本地SVN目录缺少.meta文件，且Git中的.meta文件也有问题',
                        'impact': '文件无法正确识别，需要重新生成配置',
                        'solution': '删除Git中的.meta文件，在编辑器中重新导入'
                    },
                    'meta_missing_git_invalid_svn': {
                        'icon': '🔴',
                        'title': 'Git缺少配置文件且本地配置无效',
                        'description': 'Git中缺少.meta文件，且本地SVN的.meta文件也有问题',
                        'impact': '文件无法正确同步，需要重新生成配置',
                        'solution': '删除本地.meta文件，在编辑器中重新导入'
                    },
                    'guid_mismatch': {
                        'icon': '🔴',
                        'title': '文件ID不匹配',
                        'description': '同一文件在不同位置的唯一标识符不一致',
                        'impact': '会导致引用错误，材质、预制体等失效',
                        'solution': '使用正确的标识符，通常以Git为准'
                    },
                    'guid_invalid_both': {
                        'icon': '🔴',
                        'title': '文件ID格式错误',
                        'description': 'SVN和Git中的.meta文件都没有有效的GUID',
                        'impact': '文件无法被游戏引擎正确识别',
                        'solution': '删除损坏的.meta文件，重新导入'
                    },
                    'guid_invalid_svn': {
                        'icon': '🔴',
                        'title': '本地文件ID格式错误',
                        'description': '本地SVN中的.meta文件GUID格式不正确',
                        'impact': '文件无法被游戏引擎正确识别',
                        'solution': '删除本地.meta文件，从Git复制或重新导入'
                    },
                    'guid_invalid_git': {
                        'icon': '🔴',
                        'title': 'Git文件ID格式错误',
                        'description': 'Git中的.meta文件GUID格式不正确',
                        'impact': '文件无法被游戏引擎正确识别',
                        'solution': '删除Git中的.meta文件，重新导入'
                    },
                    'svn_meta_no_guid': {
                        'icon': '🔴',
                        'title': '本地配置文件缺少ID',
                        'description': '本地SVN的.meta文件中没有找到GUID字段',
                        'impact': '文件无法被游戏引擎正确识别',
                        'solution': '删除本地.meta文件，重新导入或从Git复制'
                    },
                    'svn_meta_read_error': {
                        'icon': '🔴',
                        'title': '本地配置文件读取失败',
                        'description': '无法读取本地SVN中的.meta文件',
                        'impact': '文件状态未知，可能影响同步',
                        'solution': '检查文件权限，或删除重新生成'
                    },
                    'git_meta_read_error': {
                        'icon': '🔴',
                        'title': 'Git配置文件读取失败',
                        'description': '无法读取Git中的.meta文件',
                        'impact': '文件状态未知，可能影响同步',
                        'solution': '检查Git仓库状态，或重新导入文件'
                    },
                    'git_path_calc_error': {
                        'icon': '🔴',
                        'title': 'Git路径计算失败',
                        'description': '无法计算文件在Git中的对应路径',
                        'impact': '无法进行路径映射和同步',
                        'solution': '检查路径映射配置，或联系技术支持'
                    },
                    'guid_duplicate_internal': {
                        'icon': '🔴',
                        'title': '内部文件ID重复',
                        'description': '上传文件包内部存在重复的GUID',
                        'impact': '游戏引擎会混淆文件，导致引用错误',
                        'solution': '检查是否有重复文件，保留其中一个'
                    },
                    'guid_duplicate_git': {
                        'icon': '🔴',
                        'title': '文件ID冲突',
                        'description': '不同的文件使用了相同的唯一标识符',
                        'impact': '游戏引擎会混淆文件，导致引用错误',
                        'solution': '重新生成冲突文件的标识符'
                    },
                    'guid_reference_missing': {
                        'icon': '🔴',
                        'title': '缺少关联文件',
                        'description': '文件引用了不存在的其他资源',
                        'impact': '材质会显示为粉色，预制体可能缺失组件',
                        'solution': '添加缺失的资源文件或移除无效引用'
                    },
                    'guid_reference_parse_error': {
                        'icon': '🔴',
                        'title': '引用解析失败',
                        'description': '无法解析文件中的GUID引用',
                        'impact': '无法检查依赖关系完整性',
                        'solution': '检查文件格式是否正确，重新导入'
                    },
                    'guid_reference_check_error': {
                        'icon': '🔴',
                        'title': '引用检查异常',
                        'description': 'GUID引用检查过程中发生异常',
                        'impact': '无法确认依赖关系完整性',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'guid_reference_system_error': {
                        'icon': '🔴',
                        'title': '引用系统错误',
                        'description': 'GUID引用检查系统发生严重错误',
                        'impact': '无法进行依赖关系检查',
                        'solution': '联系技术支持'
                    },
                    'internal_dependency_missing': {
                        'icon': '🔴',
                        'title': '依赖文件不完整',
                        'description': '上传的文件包缺少必要的依赖文件',
                        'impact': '资源无法正常显示或工作',
                        'solution': '添加所有依赖的贴图、模型等文件'
                    },
                    'internal_dependency_check_error': {
                        'icon': '🔴',
                        'title': '内部依赖检查失败',
                        'description': '内部依赖检查过程中发生异常',
                        'impact': '无法确认文件包完整性',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'remote_resource_reference': {
                        'icon': '🔴',
                        'title': '禁止引用远程资源',
                        'description': '本地资源文件引用了Assets\\remotes\\entity目录下的远程资源',
                        'impact': '违反项目资源管理规范，可能导致依赖混乱',
                        'solution': '将远程资源复制到本地目录，或移除对远程资源的引用'
                    },
                    'invalid_template': {
                        'icon': '🔴',
                        'title': '材质模板错误',
                        'description': '使用了项目不允许的材质模板',
                        'impact': '材质效果不符合项目标准',
                        'solution': '使用项目规定的材质模板重新创建'
                    },
                    'template_check_system_error': {
                        'icon': '🔴',
                        'title': '材质模板检查系统错误',
                        'description': '材质模板检查系统发生严重错误',
                        'impact': '无法进行材质模板验证',
                        'solution': '联系技术支持'
                    },
                    
                    # Avatar文件夹all.filelist检查类型
                    'avatar_missing_filelist': {
                        'icon': '🔴',
                        'title': '缺少Avatar文件清单',
                        'description': 'Avatar文件包中缺少all.filelist文件',
                        'impact': '无法验证文件包的完整性',
                        'solution': '在Avatar文件包目录中创建all.filelist文件并记录所有文件的GUID'
                    },
                    'avatar_empty_filelist': {
                        'icon': '🔴',
                        'title': 'Avatar文件清单为空',
                        'description': 'all.filelist文件存在但为空或无法解析',
                        'impact': '无法验证文件包的完整性',
                        'solution': '检查all.filelist文件格式，确保包含所有文件的GUID'
                    },
                    'avatar_filelist_parse_error': {
                        'icon': '🔴',
                        'title': 'Avatar文件清单解析失败',
                        'description': 'all.filelist文件解析失败',
                        'impact': '无法验证文件包的完整性',
                        'solution': '检查all.filelist文件格式是否正确'
                    },
                    'avatar_filelist_incomplete': {
                        'icon': '🔴',
                        'title': 'Avatar文件清单不完整',
                        'description': 'all.filelist文件缺少部分文件的GUID记录',
                        'impact': '文件包不完整，可能导致资源缺失',
                        'solution': '在all.filelist中添加所有缺失文件的GUID'
                    },
                    'avatar_filelist_system_error': {
                        'icon': '🔴',
                        'title': 'Avatar文件清单检查系统错误',
                        'description': 'Avatar文件包清单检查系统发生严重错误',
                        'impact': '无法进行Avatar文件包清单验证',
                        'solution': '联系技术支持'
                    },
                    'weapon_missing_filelist': {
                        'icon': '🔴',
                        'title': 'Weapon文件清单缺失',
                        'description': 'Weapon文件包目录缺少all.filelist文件',
                        'impact': '无法验证文件包的完整性，可能导致资源缺失或版本不一致',
                        'solution': '在Weapon文件包目录中创建all.filelist文件并记录所有文件的GUID'
                    },
                    'weapon_empty_filelist': {
                        'icon': '🔴',
                        'title': 'Weapon文件清单为空',
                        'description': 'all.filelist文件存在但为空或无法解析',
                        'impact': '无法验证文件包的完整性',
                        'solution': '检查all.filelist文件格式，确保包含所有文件的GUID'
                    },
                    'weapon_filelist_parse_error': {
                        'icon': '🔴',
                        'title': 'Weapon文件清单解析失败',
                        'description': 'all.filelist文件解析失败',
                        'impact': '无法验证文件包的完整性',
                        'solution': '检查all.filelist文件格式是否正确'
                    },
                    'weapon_filelist_incomplete': {
                        'icon': '🔴',
                        'title': 'Weapon文件清单不完整',
                        'description': 'all.filelist文件缺少部分文件的GUID记录',
                        'impact': '文件包不完整，可能导致资源缺失',
                        'solution': '在all.filelist中添加所有缺失文件的GUID'
                    },
                    'weapon_filelist_system_error': {
                        'icon': '🔴',
                        'title': 'Weapon文件清单检查系统错误',
                        'description': 'Weapon文件包清单检查系统发生严重错误',
                        'impact': '无法进行Weapon文件包清单验证',
                        'solution': '联系技术支持'
                    },
                    
                    # 基础检查错误
                    'meta_missing': {
                        'icon': '🔴',
                        'title': '缺少Meta文件',
                        'description': '资源文件没有对应的.meta文件',
                        'impact': '无法在游戏引擎中正确识别',
                        'solution': '在编辑器中重新导入文件'
                    },
                    'meta_empty': {
                        'icon': '🔴',
                        'title': 'Meta文件为空',
                        'description': '.meta文件存在但内容为空',
                        'impact': '无法获取文件信息',
                        'solution': '删除空的.meta文件，重新导入'
                    },
                    'meta_no_guid': {
                        'icon': '🔴',
                        'title': 'Meta文件缺少GUID',
                        'description': '.meta文件中没有找到guid字段',
                        'impact': '文件无法被游戏引擎正确识别',
                        'solution': '删除.meta文件，重新导入'
                    },
                    'meta_read_error': {
                        'icon': '🔴',
                        'title': 'Meta文件读取错误',
                        'description': '无法读取.meta文件内容',
                        'impact': '无法获取文件信息',
                        'solution': '检查文件权限，或重新生成'
                    },
                    'meta_check_error': {
                        'icon': '🔴',
                        'title': 'Meta文件检查错误',
                        'description': 'Meta文件检查过程中发生异常',
                        'impact': '无法确认文件状态',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'guid_duplicate': {
                        'icon': '🔴',
                        'title': 'GUID重复',
                        'description': '多个文件使用了相同的GUID',
                        'impact': '游戏引擎会混淆文件',
                        'solution': '重新生成重复文件的GUID'
                    },
                    'guid_consistency_error': {
                        'icon': '🔴',
                        'title': 'GUID一致性检查错误',
                        'description': 'GUID一致性检查过程中发生异常',
                        'impact': '无法确认GUID一致性',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'uniqueness_check_error': {
                        'icon': '🔴',
                        'title': 'GUID唯一性检查错误',
                        'description': 'GUID唯一性检查过程中发生异常',
                        'impact': '无法确认GUID唯一性',
                        'solution': '重新检查，或联系技术支持'
                    },
                    
                    # 警告 - 不阻止上传但建议修复
                    'chinese_filename': {
                        'icon': '🟡',
                        'title': '文件名包含中文',
                        'description': '资源文件名包含中文字符',
                        'impact': '可能在某些系统上出现兼容性问题',
                        'solution': '重命名为英文文件名'
                    },
                    'chinese_check_error': {
                        'icon': '🟡',
                        'title': '中文字符检查错误',
                        'description': '中文字符检查过程中发生异常',
                        'impact': '无法确认文件名规范性',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'image_width_not_power_of_2': {
                        'icon': '🟡',
                        'title': '贴图宽度不是2的幂',
                        'description': '贴图宽度不是2的幂次方(如256, 512, 1024)',
                        'impact': '可能影响渲染性能和内存占用',
                        'solution': '调整为2的幂次方尺寸'
                    },
                    'image_height_not_power_of_2': {
                        'icon': '🟡',
                        'title': '贴图高度不是2的幂',
                        'description': '贴图高度不是2的幂次方(如256, 512, 1024)',
                        'impact': '可能影响渲染性能和内存占用',
                        'solution': '调整为2的幂次方尺寸'
                    },
                    'image_too_large': {
                        'icon': '🟡',
                        'title': '贴图尺寸过大',
                        'description': '贴图尺寸超过建议的最大值(通常是2048)',
                        'impact': '会消耗大量内存，影响游戏性能',
                        'solution': '压缩贴图或降低分辨率'
                    },
                    'image_check_error': {
                        'icon': '🟡',
                        'title': '图片检查错误',
                        'description': '图片检查过程中发生异常',
                        'impact': '无法确认图片规范性',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'image_size_check_error': {
                        'icon': '🟡',
                        'title': '图片尺寸检查错误',
                        'description': '图片尺寸检查过程中发生异常',
                        'impact': '无法确认图片尺寸规范',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'guid_parse_error': {
                        'icon': '🟡',
                        'title': '文件格式异常',
                        'description': '文件格式存在问题，无法正确解析',
                        'impact': '可能导致文件无法正常使用',
                        'solution': '重新导入文件或检查文件是否损坏'
                    },
                    'template_check_error': {
                        'icon': '🟡',
                        'title': '材质检查异常',
                        'description': '材质文件检查过程中出现异常',
                        'impact': '无法确认材质是否符合规范',
                        'solution': '检查材质文件是否完整或重新创建'
                    },
                    'analysis_error': {
                        'icon': '🟡',
                        'title': '文件分析错误',
                        'description': '文件分析过程中发生异常',
                        'impact': '无法完成文件分析',
                        'solution': '重新检查，或联系技术支持'
                    },
                    'check_error': {
                        'icon': '🟡',
                        'title': '检查过程错误',
                        'description': '检查过程中发生系统错误',
                        'impact': '无法完成完整检查',
                        'solution': '重新检查，或联系技术支持'
                    }
                }
                
                # 显示问题类型说明
                for issue_type, issues in issues_by_type.items():
                    if issue_type in type_explanations:
                        explanation = type_explanations[issue_type]
                        report_lines.append(f"\n{explanation['icon']} **{explanation['title']}** ({len(issues)} 个)")
                        report_lines.append(f"   📝 问题说明: {explanation['description']}")
                        report_lines.append(f"   ⚠️  可能影响: {explanation['impact']}")
                        report_lines.append(f"   🔧 解决方案: {explanation['solution']}")
                    else:
                        report_lines.append(f"\n🔵 **{issue_type}** ({len(issues)} 个)")
                        report_lines.append(f"   📝 未知问题类型，请联系技术支持")
                report_lines.append("")
                
                report_lines.append("🔧 **详细修复指南**")
                report_lines.append("═" * 70)
                
                # 按严重程度显示修复建议
                if critical_issues:
                    report_lines.append("\n🚨 **严重错误修复 (必须处理)**")
                    report_lines.append("─" * 50)
                    self._add_detailed_fix_guide(report_lines, critical_issues, issues_by_type, type_explanations)
                
                if warning_issues:
                    report_lines.append("\n⚠️  **警告修复 (建议处理)**")
                    report_lines.append("─" * 50)
                    self._add_detailed_fix_guide(report_lines, warning_issues, issues_by_type, type_explanations)
                
                # 问题文件详细列表
                report_lines.append("\n📋 **问题文件清单**")
                report_lines.append("═" * 70)
                
                for issue_type, issues in issues_by_type.items():
                    if not issues:
                        continue
                        
                    explanation = type_explanations.get(issue_type, {'icon': '🔵', 'title': issue_type})
                    report_lines.append(f"\n{explanation['icon']} **{explanation['title']}** ({len(issues)} 个文件)")
                    report_lines.append("┌" + "─" * 68 + "┐")
                    
                    for i, issue in enumerate(issues, 1):
                        file_path = issue.get('file', '')
                        file_name = os.path.basename(file_path)
                        
                        report_lines.append(f"│ {i:2d}. 📁 {file_name}")
                        
                        # 显示关键信息
                        if 'message' in issue:
                            message = issue['message']
                            # 增加消息长度限制到150字符，支持多行显示
                            if len(message) > 150:
                                # 如果消息太长，按行分割显示
                                lines = message.split('\n')
                                if len(lines) > 1:
                                    # 多行消息，显示前3行
                                    for i, line in enumerate(lines[:3]):
                                        if i == 0:
                                            report_lines.append(f"│     💬 {line}")
                                        else:
                                            report_lines.append(f"│        {line}")
                                    if len(lines) > 3:
                                        report_lines.append(f"│        ... 还有{len(lines)-3}行")
                                else:
                                    # 单行消息太长，截断但保留更多内容
                                    message = message[:147] + "..."
                                    report_lines.append(f"│     💬 {message}")
                            else:
                                # 消息不长，可能包含多行，逐行显示
                                lines = message.split('\n')
                                for i, line in enumerate(lines):
                                    if i == 0:
                                        report_lines.append(f"│     💬 {line}")
                                    else:
                                        report_lines.append(f"│        {line}")
                        
                        # 显示GUID相关的详细信息
                        if issue_type in ['guid_mismatch', 'guid_invalid_svn', 'guid_invalid_git', 'guid_invalid_both', 'svn_meta_no_guid']:
                            self._add_guid_details(report_lines, issue, issue_type)
                        
                        # 显示Avatar文件清单不完整的详细信息
                        elif issue_type == 'avatar_filelist_incomplete':
                            self._add_avatar_filelist_details(report_lines, issue)
                        
                        # 显示Weapon文件清单不完整的详细信息
                        elif issue_type == 'weapon_filelist_incomplete':
                            self._add_weapon_filelist_details(report_lines, issue)
                        
                        # 显示其他特定问题的关键信息
                        elif 'missing_guid' in issue:
                            missing_guid = issue['missing_guid']
                            report_lines.append(f"│     🔍 缺失ID: {missing_guid}")
                        elif 'missing_file' in issue:
                            missing_file = os.path.basename(issue['missing_file'])
                            report_lines.append(f"│     📂 缺失文件: {missing_file}")
                        elif 'git_guid' in issue and 'svn_guid' in issue:
                            # 显示完整GUID，按8位分组便于阅读
                            git_guid = issue['git_guid']
                            svn_guid = issue['svn_guid']
                            report_lines.append(f"│     🔄 Git ID: {git_guid}")
                            report_lines.append(f"│     🔄 SVN ID: {svn_guid}")
                        
                        if i < len(issues):
                            report_lines.append("│" + " " * 68 + "│")
                    
                    report_lines.append("└" + "─" * 68 + "┘")
            
                # 添加完整的GUID对比报告
                self._generate_comprehensive_guid_comparison_report(report_lines, blocking_issues)
            
                # 最后的建议
                report_lines.append("\n🎯 **处理建议**")
                report_lines.append("═" * 70)
                report_lines.append("1. 🔴 **优先处理严重错误** - 这些问题会阻止资源正常工作")
                report_lines.append("2. 🟡 **然后处理警告** - 这些问题可能影响性能或兼容性")
                report_lines.append("3. 💡 **遇到问题时** - 可以咨询技术美术或程序员")
                report_lines.append("4. 🔄 **修复后** - 重新检查确保问题已解决")
                report_lines.append("")
                report_lines.append("📞 **需要帮助？** 请联系技术支持或查看项目文档")
                
            else:
                # 无问题时的庆祝界面
                report_lines.append("🎉 **恭喜！所有检查都通过了！**")
                report_lines.append("┌" + "─" * 60 + "┐")
                report_lines.append("│                                                          │")
                report_lines.append("│  🎨 所有美术资源都符合项目规范！                          │")
                report_lines.append("│  ✅ 可以安全地上传到Git仓库                              │")
                report_lines.append("│                                                          │")
                report_lines.append("│  检查项目:                                               │")
                report_lines.append("│  📁 文件配置完整                                         │")
                report_lines.append("│  🔑 文件ID正确                                           │")
                report_lines.append("│  🔗 引用关系完整                                         │")
                report_lines.append("│  🎯 材质模板规范                                         │")
                report_lines.append("│  📏 图片尺寸适当                                         │")
                report_lines.append("│  🔤 文件名规范                                           │")
                report_lines.append("│                                                          │")
                report_lines.append("└" + "─" * 60 + "┘")
                report_lines.append("")
                report_lines.append("💪 **太棒了！可以放心上传了！**")
            
            # 返回报告数据
            return {
                'total_files': total_files,
                'total_issues': len(blocking_issues),
                'critical_issues': len(critical_issues),
                'warning_issues': len(warning_issues),
                'info_issues': len(info_issues),
                'issues_by_type': issues_by_type,
                'report_text': '\n'.join(report_lines),
                'has_errors': len(blocking_issues) > 0
            }
            
        except Exception as e:
            error_report = f"生成报告时发生错误: {str(e)}"
            return {
                'total_files': total_files,
                'total_issues': 0,
                'issues_by_type': {},
                'report_text': error_report,
                'has_errors': True,
                'generation_error': str(e)
            }
    
    def _add_guid_details(self, report_lines: List[str], issue: Dict, issue_type: str):
        """添加GUID相关问题的详细信息"""
        import re
        import json
        
        # 获取相关的GUID信息 - 兼容多种可能的字段名称
        # 获取相关的GUID信息 - 兼容多种可能的字段名称
        mat_file_guid = issue.get('mat_file_guid', issue.get('material_guid', ''))
        meta_file_guid = issue.get('meta_file_guid', issue.get('meta_guid', ''))
        svn_guid = issue.get('svn_guid', issue.get('svn_meta_guid', ''))
        git_guid = issue.get('git_guid', issue.get('git_meta_guid', ''))
        svn_meta_guid = issue.get('svn_meta_guid', svn_guid)
        git_meta_guid = issue.get('git_meta_guid', git_guid)
        
        # 首先尝试直接读取文件内容获取GUID
        file_path = issue.get('file', '')
        actual_guid_found = False
        
        if file_path:
            try:
                # 读取.mat文件的GUID
                mat_guids = []
                if file_path.endswith('.mat') and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        try:
                            data = json.loads(content)
                            if 'm_GUID' in data:
                                mat_guids.append(data['m_GUID'])
                            if 'm_RootObjectIdentifier' in data and 'm_GUID' in data['m_RootObjectIdentifier']:
                                mat_guids.append(data['m_RootObjectIdentifier']['m_GUID'])
                        except:
                            # 使用正则表达式作为备选
                            import re
                            guid_matches = re.findall(r'"m_GUID":\s*"([a-f0-9]{32})"', content, re.IGNORECASE)
                            mat_guids.extend(guid_matches)
                
                # 读取.meta文件的GUID
                meta_guid = ''
                meta_path = file_path + '.meta'
                if os.path.exists(meta_path):
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        try:
                            data = json.loads(content)
                            if 'm_MetaHeader' in data and 'm_GUID' in data['m_MetaHeader']:
                                meta_guid = data['m_MetaHeader']['m_GUID']
                        except:
                            # 使用正则表达式作为备选
                            import re
                            guid_match = re.search(r'"m_GUID":\s*"([a-f0-9]{32,33})"', content, re.IGNORECASE)
                            if guid_match:
                                meta_guid = guid_match.group(1)
                
                # 显示实际的GUID信息
                if mat_guids or meta_guid:
                    report_lines.append("│     📋 **GUID详细信息:**")
                    
                    if mat_guids:
                        # 找到主要的GUID (通常是第一个32位的)
                        main_mat_guid = next((guid for guid in mat_guids if len(guid) == 32), mat_guids[0] if mat_guids else '')
                        if main_mat_guid:
                            if meta_guid and len(meta_guid) == 32 and main_mat_guid == meta_guid:
                                report_lines.append(f"│     📄 .mat文件GUID: {main_mat_guid} ✅")
                            else:
                                report_lines.append(f"│     📄 .mat文件GUID: {main_mat_guid} ❌")
                    
                    if meta_guid:
                        if len(meta_guid) == 32:
                            report_lines.append(f"│     📄 .meta文件GUID: {meta_guid} ✅")
                        else:
                            report_lines.append(f"│     📄 .meta文件GUID: {meta_guid} ❌ (长度错误: {len(meta_guid)}位)")
                    
                    # 显示对比结果
                    if mat_guids and meta_guid:
                        main_mat_guid = next((guid for guid in mat_guids if len(guid) == 32), mat_guids[0] if mat_guids else '')
                        if main_mat_guid and meta_guid:
                            if main_mat_guid == meta_guid:
                                report_lines.append("│     ✅ **GUID匹配**")
                            else:
                                report_lines.append("│     ❌ **GUID不匹配**")
                                if len(meta_guid) == 33 and meta_guid[:-1] == main_mat_guid:
                                    report_lines.append("│     🔍 **问题分析:** .meta文件GUID末尾多了一个字符")
                                    report_lines.append(f"│     🔧 **修复方案:** 删除.meta文件GUID末尾的 '{meta_guid[-1]}'")
                                else:
                                    report_lines.append("│     🔧 **修复方案:** 将.meta文件GUID替换为.mat文件GUID")
                    
                    actual_guid_found = True
                    
            except Exception as e:
                report_lines.append("│     📋 **GUID详细信息:**")
                report_lines.append(f"│     ❌ 读取文件失败: {str(e)}")
        
        # 如果没有找到实际的GUID信息，检查是否有其他GUID信息
        if not actual_guid_found:
            has_guid_info = any([mat_file_guid, meta_file_guid, svn_guid, git_guid, svn_meta_guid, git_meta_guid])
            
            if has_guid_info:
                # 根据问题类型显示不同的GUID信息
                if issue_type == 'guid_mismatch':
                    report_lines.append("│     📋 **GUID详细信息:**")
                    if svn_guid and git_guid:
                        if svn_guid != git_guid:
                            report_lines.append(f"│     🔄 SVN GUID: {svn_guid} ❌")
                            report_lines.append(f"│     🔄 Git GUID: {git_guid} ✅")
                        else:
                            report_lines.append(f"│     🔄 SVN GUID: {svn_guid}")
                            report_lines.append(f"│     🔄 Git GUID: {git_guid}")
                    
                    # 如果有.mat文件和.meta文件的GUID，也显示出来
                    if mat_file_guid:
                        report_lines.append(f"│     📄 .mat文件GUID: {mat_file_guid}")
                    if meta_file_guid and meta_file_guid != mat_file_guid:
                        report_lines.append(f"│     📄 .meta文件GUID: {meta_file_guid}")
                
                elif issue_type == 'guid_invalid_svn':
                    report_lines.append("│     📋 **GUID详细信息:**")
                    if svn_guid:
                        report_lines.append(f"│     🔄 SVN GUID: {svn_guid} ❌ (格式错误)")
                    if git_guid:
                        report_lines.append(f"│     🔄 Git GUID: {git_guid} ✅")
                    if svn_meta_guid and svn_meta_guid != svn_guid:
                        report_lines.append(f"│     📄 SVN .meta GUID: {svn_meta_guid} ❌")
                    if git_meta_guid and git_meta_guid != git_guid:
                        report_lines.append(f"│     📄 Git .meta GUID: {git_meta_guid} ✅")
                
                elif issue_type == 'guid_invalid_git':
                    report_lines.append("│     📋 **GUID详细信息:**")
                    if svn_guid:
                        report_lines.append(f"│     🔄 SVN GUID: {svn_guid} ✅")
                    if git_guid:
                        report_lines.append(f"│     🔄 Git GUID: {git_guid} ❌ (格式错误)")
                    if svn_meta_guid and svn_meta_guid != svn_guid:
                        report_lines.append(f"│     📄 SVN .meta GUID: {svn_meta_guid} ✅")
                    if git_meta_guid and git_meta_guid != git_guid:
                        report_lines.append(f"│     📄 Git .meta GUID: {git_meta_guid} ❌")
                
                elif issue_type == 'guid_invalid_both':
                    report_lines.append("│     📋 **GUID详细信息:**")
                    if svn_guid:
                        report_lines.append(f"│     🔄 SVN GUID: {svn_guid} ❌ (格式错误)")
                    if git_guid:
                        report_lines.append(f"│     🔄 Git GUID: {git_guid} ❌ (格式错误)")
                    if svn_meta_guid and svn_meta_guid != svn_guid:
                        report_lines.append(f"│     📄 SVN .meta GUID: {svn_meta_guid} ❌")
                    if git_meta_guid and git_meta_guid != git_guid:
                        report_lines.append(f"│     📄 Git .meta GUID: {git_meta_guid} ❌")
                
                elif issue_type == 'svn_meta_no_guid':
                    report_lines.append("│     📋 **GUID详细信息:**")
                    if git_guid:
                        report_lines.append(f"│     🔄 Git GUID: {git_guid} ✅")
                    if git_meta_guid and git_meta_guid != git_guid:
                        report_lines.append(f"│     📄 Git .meta GUID: {git_meta_guid} ✅")
                    report_lines.append("│     📄 SVN .meta GUID: 缺失 ❌")
            else:
                # 显示调试信息
                report_lines.append("│     📋 **GUID详细信息:**")
                report_lines.append("│     🔍 **调试信息 - 所有字段:**")
                for key, value in issue.items():
                    if 'guid' in key.lower() or 'id' in key.lower():
                        report_lines.append(f"│       {key}: {value}")
                if not any('guid' in key.lower() or 'id' in key.lower() for key in issue.keys()):
                    report_lines.append("│       (未找到GUID相关字段)")
        
        # 显示建议的解决方案
        report_lines.append("│     💡 **建议:** 以Git中的GUID为准，更新本地文件")
    
    def _add_avatar_filelist_details(self, report_lines: List[str], issue: Dict):
        """添加Avatar文件清单GUID问题的详细信息"""
        missing_guids = issue.get('missing_guids', [])
        package_name = issue.get('package_name', '未知包')
        
        if not missing_guids:
            report_lines.append("│     ❌ 未能获取GUID问题详细信息")
            return
        
        report_lines.append(f"│     📦 **文件包:** {package_name}")
        report_lines.append("│     📋 **GUID问题详细信息:**")
        report_lines.append("│     ")
        
        # 按问题类型分组显示
        format_errors = [item for item in missing_guids if item.get('issue_type') == 'format_error']
        missing_entries = [item for item in missing_guids if item.get('issue_type') == 'missing']
        
        # 显示GUID不一致错误（需要修正）
        if format_errors:
            report_lines.append("│     ❌ **GUID不一致错误（需要修正）:**")
            for idx, error_info in enumerate(format_errors[:5], 1):
                file_name = os.path.basename(error_info.get('file', '未知文件'))
                git_guid = error_info.get('correct_guid', '未知')  # Git中正确的GUID
                svn_guid = error_info.get('wrong_guid', '未知')    # SVN/all.filelist中错误的GUID
                
                self._add_guid_comparison_details(report_lines, file_name, git_guid, svn_guid, idx)
            
            if len(format_errors) > 5:
                report_lines.append(f"│        ... 还有 {len(format_errors) - 5} 个GUID不一致")
            report_lines.append("│     ")
        
        # 显示缺失的GUID（需要添加）
        if missing_entries:
            report_lines.append("│     ❌ **缺失的GUID（需要添加到all.filelist）:**")
            for idx, missing_info in enumerate(missing_entries[:5], 1):
                file_name = os.path.basename(missing_info.get('file', '未知文件'))
                git_guid = missing_info.get('correct_guid', '未知')
                report_lines.append(f"│        {idx}. 📝 **{file_name}**")
                report_lines.append(f"│           📝 **SVN GUID:** 缺失 ❌")
                report_lines.append(f"│           📝 **Git GUID:** {git_guid} ✅")
                report_lines.append(f"│           📝 **状态:** 需要添加到all.filelist")
                report_lines.append("│        ")
            
            if len(missing_entries) > 5:
                report_lines.append(f"│        ... 还有 {len(missing_entries) - 5} 个缺失文件")
            report_lines.append("│     ")
        
        # 修复步骤
        report_lines.append("│     🔧 **修复步骤:**")
        report_lines.append("│     1. 打开 all.filelist 文件")
        
        if format_errors:
            report_lines.append("│     2. 找到上述标记为❌的SVN GUID，替换为对应的✅Git GUID")
        if missing_entries:
            step_num = 3 if format_errors else 2
            report_lines.append(f"│     {step_num}. 添加上述缺失文件的GUID记录")
        
        final_step = len([x for x in [format_errors, missing_entries] if x]) + 1
        report_lines.append(f"│     {final_step}. 保存文件并重新检查")
    
    def _add_guid_comparison_details(self, report_lines: List[str], file_name: str, git_guid: str, svn_guid: str, idx: int):
        """添加GUID对比的详细信息显示"""
        report_lines.append(f"│        {idx}. 📁 **{file_name}**")
        report_lines.append(f"│           📝 **SVN GUID:** {svn_guid} ❌")
        report_lines.append(f"│           📝 **Git GUID:** {git_guid} ✅")
        
        # 生成对比显示，标记不同的字符
        if len(git_guid) == len(svn_guid) == 32:
            # 显示完整GUID
            report_lines.append("│           📊 **详细对比:**")
            report_lines.append(f"│              SVN: {svn_guid} ❌")
            report_lines.append(f"│              Git: {git_guid} ✅")
            
            # 显示字符级对比
            comparison_line = "│              差异: "
            diff_markers = ""
            for i, (git_char, svn_char) in enumerate(zip(git_guid, svn_guid)):
                if i > 0 and i % 8 == 0:
                    diff_markers += "-"
                if git_char != svn_char:
                    diff_markers += "^"
                else:
                    diff_markers += " "
            report_lines.append(comparison_line + diff_markers)
            
            # 显示具体差异位置
            diff_positions = []
            for i, (git_char, svn_char) in enumerate(zip(git_guid, svn_guid)):
                if git_char != svn_char:
                    diff_positions.append(f"位置{i+1}({svn_char}→{git_char})")
            
            if diff_positions:
                diff_text = ", ".join(diff_positions[:5])  # 显示前5个差异
                if len(diff_positions) > 5:
                    diff_text += f" 等{len(diff_positions)}处"
                report_lines.append(f"│           🔍 **差异详情:** {diff_text}")
                report_lines.append(f"│           📊 **差异统计:** 共{len(diff_positions)}个字符不同")
        elif len(git_guid) != len(svn_guid):
            report_lines.append(f"│           ⚠️  **长度不匹配:** SVN({len(svn_guid)}位) vs Git({len(git_guid)}位)")
        
        report_lines.append("│        ")

    def _generate_comprehensive_guid_comparison_report(self, report_lines: List[str], guid_issues: List[Dict[str, str]]):
        """生成完整的GUID对比报告"""
        if not guid_issues:
            return
            
        # 分类GUID问题
        mismatch_issues = [issue for issue in guid_issues if issue.get('type') == 'guid_mismatch']
        duplicate_issues = [issue for issue in guid_issues if issue.get('type') == 'guid_duplicate_git']
        missing_issues = [issue for issue in guid_issues if issue.get('type') == 'guid_reference_missing']
        
        if mismatch_issues or duplicate_issues:
            report_lines.append("")
            report_lines.append("╔══════════════════════════════════════════════════════════════════════════════════════════════════╗")
            report_lines.append("║                                    📊 GUID详细对比报告                                            ║")
            report_lines.append("╚══════════════════════════════════════════════════════════════════════════════════════════════════╝")
            
        # GUID不匹配对比
        if mismatch_issues:
            report_lines.append("")
            report_lines.append("🔄 **SVN vs Git GUID不匹配对比:**")
            report_lines.append("─" * 100)
            
            for idx, issue in enumerate(mismatch_issues[:10], 1):  # 最多显示10个
                file_name = os.path.basename(issue.get('file', '未知文件'))
                svn_guid = issue.get('svn_guid', issue.get('local_guid', ''))
                git_guid = issue.get('git_guid', issue.get('expected_guid', ''))
                
                if svn_guid and git_guid:
                    report_lines.append(f"")
                    report_lines.append(f"📁 **{idx}. {file_name}**")
                    report_lines.append(f"   📝 SVN GUID: {svn_guid} ❌")
                    report_lines.append(f"   📝 Git GUID: {git_guid} ✅")
                    
                    # 计算差异
                    if len(svn_guid) == len(git_guid) == 32:
                        diff_count = sum(1 for s, g in zip(svn_guid, git_guid) if s != g)
                        diff_positions = [i+1 for i, (s, g) in enumerate(zip(svn_guid, git_guid)) if s != g]
                        
                        if diff_count > 0:
                            report_lines.append(f"   🔍 差异统计: {diff_count}个字符不同")
                            if diff_count <= 8:
                                pos_text = ", ".join([f"位置{pos}" for pos in diff_positions[:8]])
                                report_lines.append(f"   📍 差异位置: {pos_text}")
                        
                        # 显示差异标记
                        diff_markers = ""
                        for i, (s, g) in enumerate(zip(svn_guid, git_guid)):
                            if i > 0 and i % 8 == 0:
                                diff_markers += "-"
                            diff_markers += "^" if s != g else " "
                        report_lines.append(f"   📊 差异标记: {diff_markers}")
                    
            if len(mismatch_issues) > 10:
                report_lines.append(f"")
                report_lines.append(f"... 还有 {len(mismatch_issues) - 10} 个GUID不匹配问题")
                
        # GUID冲突对比  
        if duplicate_issues:
            report_lines.append("")
            report_lines.append("⚠️ **GUID冲突详情 (不同文件使用相同GUID):**")
            report_lines.append("─" * 100)
            
            for idx, issue in enumerate(duplicate_issues[:5], 1):  # 最多显示5个
                file_name = os.path.basename(issue.get('file', '未知文件'))
                git_file_name = issue.get('git_file_name', '未知Git文件')
                guid = issue.get('guid', '')
                
                if guid:
                    report_lines.append(f"")
                    report_lines.append(f"⚠️ **{idx}. GUID冲突**")
                    report_lines.append(f"   🆔 GUID: {guid}")
                    report_lines.append(f"   📄 SVN文件: {file_name}")
                    report_lines.append(f"   📄 Git文件: {git_file_name}")
                    report_lines.append(f"   💡 建议: 请统一文件名或重新生成GUID")
                    
            if len(duplicate_issues) > 5:
                report_lines.append(f"")
                report_lines.append(f"... 还有 {len(duplicate_issues) - 5} 个GUID冲突")
        
        # 缺失GUID引用
        if missing_issues:
            report_lines.append("")
            report_lines.append("❌ **缺失的GUID引用:**")
            report_lines.append("─" * 100)
            
            for idx, issue in enumerate(missing_issues[:5], 1):  # 最多显示5个
                file_name = os.path.basename(issue.get('file', '未知文件'))
                missing_guid = issue.get('guid', '')
                
                if missing_guid:
                    report_lines.append(f"")
                    report_lines.append(f"❌ **{idx}. 缺失引用**")
                    report_lines.append(f"   🆔 被引用GUID: {missing_guid}")
                    report_lines.append(f"   📄 引用文件: {file_name}")
                    
                    # 尝试获取引用文件的SVN GUID
                    referring_file_guid = issue.get('referring_file_guid', '')
                    referring_file_guid_status = issue.get('referring_file_guid_status', '未知状态')
                    
                    if referring_file_guid:
                        report_lines.append(f"   🔗 引用文件GUID: {referring_file_guid}")
                    else:
                        # 显示为什么没有找到SVN GUID
                        report_lines.append(f"   ⚠️  引用文件GUID状态: {referring_file_guid_status}")
                    
                    report_lines.append(f"   💡 建议: 确保被引用的资源文件已包含在上传列表中")
                    
            if len(missing_issues) > 5:
                report_lines.append(f"")
                report_lines.append(f"... 还有 {len(missing_issues) - 5} 个缺失的GUID引用")

        if mismatch_issues or duplicate_issues or missing_issues:
            report_lines.append("")
            report_lines.append("═" * 100)
            report_lines.append("")

    def _add_weapon_filelist_details(self, report_lines: List[str], issue: Dict):
        """添加Weapon文件清单GUID问题的详细信息"""
        missing_guids = issue.get('missing_guids', [])
        package_name = issue.get('package_name', '未知包')
        
        if not missing_guids:
            report_lines.append("│     ❌ 未能获取GUID问题详细信息")
            return
        
        report_lines.append(f"│     📦 **文件包:** {package_name}")
        report_lines.append("│     📋 **GUID问题详细信息:**")
        report_lines.append("│     ")
        
        # 按问题类型分组显示
        format_errors = [item for item in missing_guids if item.get('issue_type') == 'format_error']
        missing_entries = [item for item in missing_guids if item.get('issue_type') == 'missing']
        
        # 显示GUID不一致错误（需要修正）
        if format_errors:
            report_lines.append("│     ❌ **GUID不一致错误（需要修正）:**")
            for idx, error_info in enumerate(format_errors[:5], 1):
                file_name = os.path.basename(error_info.get('file', '未知文件'))
                git_guid = error_info.get('correct_guid', '未知')  # Git中正确的GUID
                svn_guid = error_info.get('wrong_guid', '未知')    # SVN/all.filelist中错误的GUID
                
                self._add_guid_comparison_details(report_lines, file_name, git_guid, svn_guid, idx)
            
            if len(format_errors) > 5:
                report_lines.append(f"│        ... 还有 {len(format_errors) - 5} 个GUID不一致")
            report_lines.append("│     ")
        
        # 显示缺失的GUID（需要添加）
        if missing_entries:
            report_lines.append("│     ❌ **缺失的GUID（需要添加到all.filelist）:**")
            for idx, missing_info in enumerate(missing_entries[:5], 1):
                file_name = os.path.basename(missing_info.get('file', '未知文件'))
                git_guid = missing_info.get('correct_guid', '未知')
                report_lines.append(f"│        {idx}. 📝 **{file_name}**")
                report_lines.append(f"│           📝 **SVN GUID:** 缺失 ❌")
                report_lines.append(f"│           📝 **Git GUID:** {git_guid} ✅")
                report_lines.append(f"│           📝 **状态:** 需要添加到all.filelist")
                report_lines.append("│        ")
            
            if len(missing_entries) > 5:
                report_lines.append(f"│        ... 还有 {len(missing_entries) - 5} 个缺失文件")
            report_lines.append("│     ")
        
        # 修复步骤
        report_lines.append("│     🔧 **修复步骤:**")
        report_lines.append("│     1. 打开 all.filelist 文件")
        
        if format_errors:
            report_lines.append("│     2. 找到上述标记为❌的SVN GUID，替换为对应的✅Git GUID")
        if missing_entries:
            step_num = 3 if format_errors else 2
            report_lines.append(f"│     {step_num}. 添加上述缺失文件的GUID记录")
        
        final_step = len([x for x in [format_errors, missing_entries] if x]) + 1
        report_lines.append(f"│     {final_step}. 保存文件并重新检查")
    
    def _add_detailed_fix_guide(self, report_lines: List[str], issues: List[Dict], issues_by_type: Dict, type_explanations: Dict):
        """添加详细的修复指南"""
        issue_types_in_list = set(issue.get('type', 'unknown') for issue in issues)
        
        # 过滤掉不需要显示详细修复指南的问题类型
        skip_detailed_guide = {
            'svn_meta_no_guid', 'guid_invalid_svn', 'guid_invalid_git', 'guid_invalid_both',
            'svn_meta_read_error', 'git_meta_read_error', 'git_path_calc_error',
            'guid_reference_parse_error', 'guid_reference_check_error', 'guid_reference_system_error',
            'internal_dependency_check_error', 'template_check_system_error',
            'meta_check_error', 'guid_consistency_error', 'uniqueness_check_error',
            'chinese_check_error', 'image_check_error', 'image_size_check_error',
            'analysis_error', 'check_error'
        }
        
        for issue_type in issue_types_in_list:
            if issue_type not in issues_by_type or issue_type in skip_detailed_guide:
                continue
                
            type_issues = issues_by_type[issue_type]
            explanation = type_explanations.get(issue_type, {'icon': '🔵', 'title': issue_type})
            
            report_lines.append(f"\n{explanation['icon']} **{explanation['title']}** ({len(type_issues)} 个)")
            
            # 根据问题类型提供具体的操作步骤
            if issue_type == 'meta_missing_both':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 打开游戏编辑器")
                report_lines.append("   2. 在Project窗口中找到问题文件")
                report_lines.append("   3. 右键点击文件 → Reimport")
                report_lines.append("   4. 等待导入完成，.meta文件会自动生成")
            
            elif issue_type == 'guid_mismatch':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 确认Git中的版本是最新的")
                report_lines.append("   2. 复制Git中的.meta文件覆盖本地版本")
                report_lines.append("   3. 或者删除本地.meta文件，重新导入")
            
            elif issue_type == 'invalid_template':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 在编辑器中打开材质文件")
                report_lines.append("   2. 在Inspector中更改Shader")
                report_lines.append("   3. 选择项目允许的材质模板")
                report_lines.append("   4. 重新设置材质参数")
                report_lines.append("   📝 **允许的模板:** Character_NPR_Opaque, Scene_Prop_Opaque 等")
            
            elif issue_type == 'chinese_filename':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 在文件管理器中重命名文件")
                report_lines.append("   2. 使用英文名称，可以用拼音")
                report_lines.append("   3. 在编辑器中刷新(Ctrl+R)")
                report_lines.append("   4. 检查引用是否正常")
            
            elif issue_type in ['image_width_not_power_of_2', 'image_height_not_power_of_2']:
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 使用图像编辑软件(如Photoshop)")
                report_lines.append("   2. 调整图像尺寸为2的幂次方")
                report_lines.append("   3. 推荐尺寸: 256, 512, 1024, 2048")
                report_lines.append("   4. 重新导入到编辑器")
            
            elif issue_type == 'image_too_large':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 评估是否真的需要这么大的尺寸")
                report_lines.append("   2. 如果不需要，缩小到合适尺寸")
                report_lines.append("   3. 如果需要，在编辑器中设置压缩")
                report_lines.append("   4. 调整Import Settings中的Max Size")
            
            elif issue_type == 'guid_reference_missing':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 检查是否缺少贴图、模型等文件")
                report_lines.append("   2. 将缺失的文件添加到上传列表")
                report_lines.append("   3. 或者在材质中移除无效引用")
                report_lines.append("   4. 重新检查依赖关系")
            
            elif issue_type == 'avatar_filelist_incomplete':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 找到Avatar文件包中的all.filelist文件")
                report_lines.append("   2. 用文本编辑器打开all.filelist")
                report_lines.append("   3. 根据上面显示的详细信息:")
                report_lines.append("      • 添加标记为✅的正确GUID")
                report_lines.append("      • 删除标记为❌的错误GUID")
                report_lines.append("   4. 保存文件后重新上传检查")
                report_lines.append("   📝 **注意:** 每个文件的GUID可以在对应的.meta文件中找到")
            
            elif issue_type == 'avatar_missing_filelist':
                report_lines.append("   📋 **操作步骤:**")
                report_lines.append("   1. 在Avatar文件包目录中创建all.filelist文件")
                report_lines.append("   2. 收集该目录下所有文件的GUID")
                report_lines.append("   3. 将GUID按行写入all.filelist文件")
                report_lines.append("   4. 每个GUID对应一个资源文件")
                report_lines.append("   📝 **提示:** GUID可以从.meta文件的m_GUID字段获取")
            
            else:
                report_lines.append("   📋 **操作建议:**")
                report_lines.append("   1. 检查文件是否完整")
                report_lines.append("   2. 尝试重新导入文件")
                report_lines.append("   3. 如有疑问请联系技术支持")
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_git_repository_guids(self) -> Dict[str, Dict[str, str]]:
        """扫描Git仓库获取所有GUID及其路径信息 - 使用高性能缓存
        
        Returns:
            Dict[str, Dict[str, str]]: {guid: {'meta_path': str, 'relative_resource_path': str, 'resource_name': str}}
        """
        if not self.git_manager.git_path or not os.path.exists(self.git_manager.git_path):
            self.status_updated.emit(f"❌ Git仓库路径无效: {self.git_manager.git_path}")
            return {}
        
        try:
            # 创建缓存管理器
            cache_manager = GitGuidCacheManager(self.git_manager.git_path)
            
            # 使用缓存管理器获取GUID映射，传递进度回调
            def progress_callback(message):
                self.status_updated.emit(message)
            
            git_guids = cache_manager.get_git_repository_guids(progress_callback)
            
            # 输出缓存信息
            cache_info = cache_manager.get_cache_info()
            if cache_info['cache_exists']:
                cache_size_kb = cache_info['cache_file_size'] / 1024
                self.status_updated.emit(f"📊 缓存信息:")
                self.status_updated.emit(f"   📅 上次扫描: {cache_info['last_scan_time']}")
                self.status_updated.emit(f"   🏷️ 提交版本: {cache_info['last_commit_hash']}")
                self.status_updated.emit(f"   📁 缓存大小: {cache_size_kb:.1f} KB")
            
            return git_guids
            
        except Exception as e:
            self.status_updated.emit(f"❌ GUID缓存系统异常: {e}")
            self.status_updated.emit(f"🔄 回退到传统扫描方式...")
            
            # 回退到原始的扫描方式
            return self._fallback_git_repository_scan()
    
    def _fallback_git_repository_scan(self) -> Dict[str, Dict[str, str]]:
        """回退的传统扫描方式"""
        git_guids = {}
        
        self.status_updated.emit(f"🔍 开始传统扫描Git仓库: {self.git_manager.git_path}")
        
        # 统计信息
        scan_stats = {
            'directories_scanned': 0,
            'meta_files_found': 0,
            'valid_guids': 0,
            'parse_errors': 0
        }
        
        try:
            for root, dirs, files in os.walk(self.git_manager.git_path):
                # 跳过.git目录以提高性能
                if '.git' in dirs:
                    dirs.remove('.git')
                
                scan_stats['directories_scanned'] += 1
                
                # 每扫描1000个目录输出一次进度
                if scan_stats['directories_scanned'] % 1000 == 0:
                    self.status_updated.emit(f"  📁 已扫描 {scan_stats['directories_scanned']} 个目录...")
                
                for file in files:
                    if file.endswith('.meta'):
                        scan_stats['meta_files_found'] += 1
                        meta_path = os.path.join(root, file)
                        relative_meta_path = os.path.relpath(meta_path, self.git_manager.git_path)
                        
                        try:
                            analyzer = ResourceDependencyAnalyzer()
                            guid = analyzer.parse_meta_file(meta_path)
                            
                            if guid and len(guid) == 32:
                                # 计算资源文件相对路径
                                if relative_meta_path.endswith('.meta'):
                                    relative_resource_path = relative_meta_path[:-5]
                                else:
                                    relative_resource_path = relative_meta_path
                                
                                # 标准化路径分隔符
                                relative_resource_path = relative_resource_path.replace('\\', '/')
                                
                                git_guids[guid] = {
                                    'meta_path': meta_path,
                                    'relative_meta_path': relative_meta_path.replace('\\', '/'),
                                    'relative_resource_path': relative_resource_path,
                                    'resource_name': os.path.basename(relative_resource_path)
                                }
                                
                                scan_stats['valid_guids'] += 1
                        
                        except Exception as e:
                            scan_stats['parse_errors'] += 1
                            if scan_stats['parse_errors'] <= 3:  # 只显示前3个错误
                                self.status_updated.emit(f"  ❌ 解析meta文件失败: {relative_meta_path}")
                            
        except Exception as e:
            self.status_updated.emit(f"❌ 传统扫描异常: {e}")
        
        # 输出扫描统计信息
        self.status_updated.emit(f"📊 传统扫描完成:")
        self.status_updated.emit(f"   📁 扫描目录数: {scan_stats['directories_scanned']}")
        self.status_updated.emit(f"   📄 找到meta文件: {scan_stats['meta_files_found']}")
        self.status_updated.emit(f"   ✅ 有效GUID: {scan_stats['valid_guids']}")
        self.status_updated.emit(f"   🚫 解析错误: {scan_stats['parse_errors']}")
        
        return git_guids

    def _check_git_sync_status(self) -> Dict[str, Any]:
        """检查Git仓库同步状态，判断是否需要更新"""
        result = {
            'is_up_to_date': True,
            'needs_pull': False,
            'needs_reset': False,
            'remote_ahead': 0,
            'local_ahead': 0,
            'current_branch': '',
            'remote_reachable': False,
            'conflict_risk': False,
            'message': '',
            'details': []
        }
        
        try:
            print("🔍 [SYNC_CHECK] ========== 开始Git同步状态检查 ==========")
            
            if not self.git_manager or not self.git_manager.git_path:
                print("❌ [SYNC_CHECK] Git路径未配置")
                result['message'] = "Git路径未配置"
                return result
            
            print(f"📁 [SYNC_CHECK] Git路径: {self.git_manager.git_path}")
            
            # 1. 获取当前分支 (快速本地操作)
            print("🌿 [SYNC_CHECK] 步骤1/3: 获取当前分支...")
            current_branch = self.git_manager.get_current_branch()
            result['current_branch'] = current_branch
            
            if not current_branch:
                print("❌ [SYNC_CHECK] 无法获取当前分支")
                result['message'] = "无法获取当前分支"
                return result
            
            print(f"✅ [SYNC_CHECK] 当前分支: {current_branch}")
            
            # 2. 极速检查远程连接 (1秒超时)
            print("🌐 [SYNC_CHECK] 步骤2/3: 检查远程连接 (1秒快速检查)...")
            try:
                # 首先检查远程仓库URL是否配置
                remote_check = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    cwd=self.git_manager.git_path,
                    capture_output=True,
                    text=True,
                    timeout=1
                , creationflags=SUBPROCESS_FLAGS)
                
                if remote_check.returncode != 0:
                    print("❌ [SYNC_CHECK] 未配置远程仓库")
                    result['message'] = "未配置远程仓库，跳过同步检查"
                    return result
                
                remote_url = remote_check.stdout.strip()
                print(f"🔗 [SYNC_CHECK] 远程URL: {remote_url}")
                
                # 极速检查远程连接（1秒超时）
                fetch_result = subprocess.run(
                    ['git', 'ls-remote', '--heads', 'origin'],  # 更快的检查方式
                    cwd=self.git_manager.git_path,
                    capture_output=True,
                    text=True,
                    timeout=1  # 极短超时，快速失败
                , creationflags=SUBPROCESS_FLAGS)
                
                if fetch_result.returncode == 0:
                    result['remote_reachable'] = True
                    print("✅ [SYNC_CHECK] 远程连接正常")
                else:
                    print(f"⚠️ [SYNC_CHECK] 远程连接异常: {fetch_result.stderr}")
                    result['message'] = "远程仓库连接异常，跳过同步检查"
                    return result
                    
            except subprocess.TimeoutExpired:
                print("⏰ [SYNC_CHECK] 远程连接超时 (1秒) - 网络可能较慢")
                result['message'] = "远程仓库连接超时，跳过同步检查"
                return result
            except subprocess.CalledProcessError as e:
                print(f"❌ [SYNC_CHECK] 远程连接失败: {e}")
                result['message'] = "无法连接到远程仓库，跳过同步检查"
                return result
            
            # 3. 快速获取远程更新 (5秒超时)
            print("📥 [SYNC_CHECK] 步骤3/3: 获取远程更新 (5秒超时)...")
            try:
                fetch_result = subprocess.run(
                    ['git', 'fetch', 'origin', '--quiet'],  # 添加quiet减少输出
                    cwd=self.git_manager.git_path,
                    capture_output=True,
                    text=True,
                    timeout=5  # 进一步缩短超时到5秒
                , creationflags=SUBPROCESS_FLAGS)
                
                if fetch_result.returncode == 0:
                    print("✅ [SYNC_CHECK] 远程信息获取成功")
                else:
                    print(f"⚠️ [SYNC_CHECK] 获取远程信息异常: {fetch_result.stderr}")
                    result['message'] = "获取远程信息失败"
                    return result
                    
            except subprocess.TimeoutExpired:
                print("⏰ [SYNC_CHECK] 获取远程更新超时 (5秒) - 网络较慢，跳过同步检查")
                result['message'] = "获取远程更新超时，跳过同步检查"
                return result
            except subprocess.CalledProcessError as e:
                print(f"❌ [SYNC_CHECK] 获取远程更新失败: {e}")
                result['message'] = "获取远程更新失败"
                return result
            
            # 4. 检查分支同步状态 (快速本地操作)
            print("📊 [SYNC_CHECK] 分析分支差异...")
            try:
                # 检查本地分支与远程分支的差异
                rev_list_cmd = ['git', 'rev-list', '--count', '--left-right', f'HEAD...origin/{current_branch}']
                print(f"🔧 [SYNC_CHECK] 执行命令: {' '.join(rev_list_cmd)}")
                
                rev_result = subprocess.run(
                    rev_list_cmd,
                    cwd=self.git_manager.git_path,
                    capture_output=True,
                    text=True,
                    timeout=5  # 本地操作，5秒足够
                , creationflags=SUBPROCESS_FLAGS)
                
                print(f"📋 [SYNC_CHECK] Git命令返回值: {rev_result.returncode}")
                print(f"📋 [SYNC_CHECK] Git命令输出: '{rev_result.stdout.strip()}'")
                if rev_result.stderr:
                    print(f"📋 [SYNC_CHECK] Git命令错误输出: '{rev_result.stderr.strip()}'")
                
                if rev_result.returncode == 0:
                    # 解析结果：local_ahead remote_ahead
                    output = rev_result.stdout.strip()
                    if output:
                        counts = output.split('\t')
                        print(f"🔍 [SYNC_CHECK] 分割后的数据: {counts}")
                        
                        if len(counts) >= 2:
                            result['local_ahead'] = int(counts[0]) if counts[0] else 0
                            result['remote_ahead'] = int(counts[1]) if counts[1] else 0
                        elif len(counts) == 1:
                            # 可能只有一个数字，检查是否用空格分割
                            space_counts = output.split()
                            if len(space_counts) >= 2:
                                result['local_ahead'] = int(space_counts[0]) if space_counts[0] else 0
                                result['remote_ahead'] = int(space_counts[1]) if space_counts[1] else 0
                                print(f"🔍 [SYNC_CHECK] 空格分割后的数据: {space_counts}")
                    else:
                        print("🔍 [SYNC_CHECK] Git命令输出为空，可能没有差异")
                    
                    print(f"📈 [SYNC_CHECK] 本地领先: {result['local_ahead']}, 远程领先: {result['remote_ahead']}")
                    
                    # 判断是否需要同步
                    if result['remote_ahead'] > 0:
                        result['is_up_to_date'] = False
                        result['needs_pull'] = True
                        print(f"⚠️ [SYNC_CHECK] 设置is_up_to_date=False，因为remote_ahead={result['remote_ahead']}")
                        
                        if result['local_ahead'] > 0:
                            # 本地和远程都有新提交，可能有冲突
                            result['conflict_risk'] = True
                            result['needs_reset'] = True
                            result['message'] = f"分支分歧：本地领先{result['local_ahead']}个提交，远程领先{result['remote_ahead']}个提交"
                            result['details'].append("⚠️ 检测到分支分歧，推荐使用重置更新避免冲突")
                            print("⚠️ [SYNC_CHECK] 检测到分支分歧")
                        else:
                            # 只有远程有新提交，可以安全合并
                            result['message'] = f"远程仓库有{result['remote_ahead']}个新提交需要拉取"
                            result['details'].append("ℹ️ 可以安全拉取远程更新")
                            print("📥 [SYNC_CHECK] 需要拉取远程更新")
                    else:
                        print("✅ [SYNC_CHECK] 远程没有新提交，保持is_up_to_date=True")
                else:
                    print(f"⚠️ [SYNC_CHECK] 分支比较失败: {rev_result.stderr}")
                
            except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired) as e:
                print(f"❌ [SYNC_CHECK] 检查分支状态失败: {e}")
                result['message'] = f"检查分支状态失败: {e}"
                return result
            
            # 5. 检查工作区状态 (快速本地操作)
            print("🔍 [SYNC_CHECK] 检查工作区状态...")
            try:
                status_result = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    cwd=self.git_manager.git_path,
                    capture_output=True,
                    text=True,
                    timeout=3  # 本地操作，3秒足够
                , creationflags=SUBPROCESS_FLAGS)
                
                if status_result.returncode == 0:
                    if status_result.stdout.strip():
                        result['details'].append("⚠️ 工作区有未提交的更改")
                        if result['needs_pull']:
                            result['needs_reset'] = True  # 有未提交更改时建议重置
                            result['details'].append("💡 建议使用重置更新来处理工作区更改")
                        print("⚠️ [SYNC_CHECK] 工作区有未提交更改")
                    else:
                        print("✅ [SYNC_CHECK] 工作区干净")
                        
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                print("⚠️ [SYNC_CHECK] 检查工作区状态失败，忽略")
                pass  # 忽略状态检查失败
            
            # 6. 生成最终建议
            if result['is_up_to_date']:
                result['message'] = "Git仓库已是最新状态"
                print("✅ [SYNC_CHECK] Git仓库已是最新状态")
            
            # 输出最终检查结果
            print("🎯 [SYNC_CHECK] ========== 最终检查结果 ==========")
            print(f"📊 [SYNC_CHECK] is_up_to_date: {result['is_up_to_date']}")
            print(f"📊 [SYNC_CHECK] needs_pull: {result['needs_pull']}")  
            print(f"📊 [SYNC_CHECK] needs_reset: {result['needs_reset']}")
            print(f"📊 [SYNC_CHECK] local_ahead: {result['local_ahead']}")
            print(f"📊 [SYNC_CHECK] remote_ahead: {result['remote_ahead']}")
            print(f"📊 [SYNC_CHECK] message: {result['message']}")
            print("🎉 [SYNC_CHECK] ========== Git同步状态检查完成 ==========")
            return result
            
        except Exception as e:
            error_msg = f"Git状态检查失败: {e}"
            print(f"💥 [SYNC_CHECK] {error_msg}")
            result['message'] = error_msg
            return result


class FolderUploadModeDialog(QDialog):
    """文件夹上传模式选择对话框"""
    
    REPLACE_MODE = "replace"  # 替换模式
    MERGE_MODE = "merge"      # 合并模式
    
    def __init__(self, folder_names, parent=None):
        super().__init__(parent)
        self.folder_names = folder_names
        self.selected_mode = None
        
        self.setWindowTitle("文件夹上传模式选择")
        self.setModal(True)
        self.resize(500, 350)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 文件夹信息
        info_label = QLabel("检测到您拖入了文件夹：")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 文件夹名称显示
        folder_display = QLabel()
        if len(self.folder_names) == 1:
            folder_display.setText(f"📁 {self.folder_names[0]}")
        else:
            folder_text = "\n".join([f"📁 {name}" for name in self.folder_names])
            folder_display.setText(folder_text)
        folder_display.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px; margin-bottom: 15px;")
        layout.addWidget(folder_display)
        
        # 选择提示
        select_label = QLabel("请选择上传模式：")
        select_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(select_label)
        
        # 替换模式选项
        self.replace_radio = QRadioButton("替换模式")
        self.replace_radio.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.replace_radio)
        
        replace_desc = QLabel("• 删除Git仓库中的同名文件夹\n• 用拖入的文件夹完全替换\n• 确保文件夹内容完全一致")
        replace_desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 15px;")
        layout.addWidget(replace_desc)
        
        # 合并模式选项
        self.merge_radio = QRadioButton("合并模式")
        self.merge_radio.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.merge_radio)
        
        merge_desc = QLabel("• 保持Git仓库中的现有文件\n• 添加或更新拖入文件夹中的文件\n• 不会删除Git仓库中的其他文件")
        merge_desc.setStyleSheet("color: #666; margin-left: 20px; margin-bottom: 15px;")
        layout.addWidget(merge_desc)
        
        # 警告信息
        warning_label = QLabel("⚠️ 注意：替换模式会删除Git仓库中的同名文件夹！")
        warning_label.setStyleSheet("color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 8px; border-radius: 4px; margin-bottom: 15px;")
        layout.addWidget(warning_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.setEnabled(False)  # 初始状态为禁用
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # 监听单选按钮变化
        self.replace_radio.toggled.connect(self.on_selection_changed)
        self.merge_radio.toggled.connect(self.on_selection_changed)
        
    def on_selection_changed(self):
        """处理选择变化"""
        # 只有用户选择了选项，确定按钮才启用
        self.ok_button.setEnabled(
            self.replace_radio.isChecked() or self.merge_radio.isChecked()
        )
    
    def get_selected_mode(self):
        """获取选择的模式"""
        if self.replace_radio.isChecked():
            return self.REPLACE_MODE
        elif self.merge_radio.isChecked():
            return self.MERGE_MODE
        return None


class BranchSelectorDialog(QDialog):
    """分支选择对话框"""
    
    def __init__(self, branches, current_branch="", parent=None):
        super().__init__(parent)
        self.branches = branches
        self.filtered_branches = branches.copy()  # 过滤后的分支列表
        self.current_branch = current_branch
        self.selected_branch = ""
        
        self.setWindowTitle(f"选择分支 (共 {len(branches)} 个分支)")
        self.setModal(True)
        self.resize(600, 450)  # 稍微增加高度以容纳搜索框
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索分支:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词过滤分支...")
        self.search_input.textChanged.connect(self.filter_branches)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 分支计数标签
        self.count_label = QLabel(f"显示 {len(self.filtered_branches)} / {len(self.branches)} 个分支")
        self.count_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.count_label)
        
        # 分支列表
        self.branch_list = QListWidget()
        self.populate_branch_list()
        layout.addWidget(self.branch_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        # 清空搜索按钮
        clear_search_btn = QPushButton("清空搜索")
        clear_search_btn.clicked.connect(self.clear_search)
        button_layout.addWidget(clear_search_btn)
        
        button_layout.addStretch()  # 添加弹性空间
        
        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self.accept)
        button_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点到搜索框
        self.search_input.setFocus()
    
    def populate_branch_list(self):
        """填充分支列表"""
        self.branch_list.clear()
        
        if not self.filtered_branches:
            # 没有匹配的分支时显示提示
            item = QListWidgetItem("没有找到匹配的分支")
            item.setFlags(Qt.NoItemFlags)  # 不可选择
            item.setTextAlignment(Qt.AlignCenter)
            self.branch_list.addItem(item)
            return
        
        for branch in self.filtered_branches:
            item = QListWidgetItem(branch)
            if branch == self.current_branch:
                item.setText(f"★ {branch} (当前分支)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                # 设置当前分支为选中状态
                self.branch_list.addItem(item)
                self.branch_list.setCurrentItem(item)
            else:
                self.branch_list.addItem(item)
    
    def filter_branches(self):
        """根据搜索关键词过滤分支"""
        search_text = self.search_input.text().lower().strip()
        
        if not search_text:
            # 搜索框为空时显示所有分支
            self.filtered_branches = self.branches.copy()
        else:
            # 过滤包含关键词的分支（不区分大小写）
            self.filtered_branches = [
                branch for branch in self.branches 
                if search_text in branch.lower()
            ]
        
        # 更新分支列表和计数
        self.populate_branch_list()
        self.count_label.setText(f"显示 {len(self.filtered_branches)} / {len(self.branches)} 个分支")
    
    def clear_search(self):
        """清空搜索框"""
        self.search_input.clear()
    
    def get_selected_branch(self):
        """获取选中的分支"""
        current_item = self.branch_list.currentItem()
        if current_item and current_item.flags() != Qt.NoItemFlags:  # 确保不是提示项
            text = current_item.text()
            if text.startswith("★ "):
                return text.replace("★ ", "").replace(" (当前分支)", "")
            return text
        return ""


class SimpleBranchComboBox(QComboBox):
    """简单的分支组合框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(False)
        self._user_is_interacting = False  # 用户交互标志
        self._last_user_interaction_time = 0  # 最后用户交互时间
        
        # 监听用户交互
        self.currentIndexChanged.connect(self._on_user_selection_changed)
        
    def set_branches(self, branches, current_branch="", force_update=False):
        """设置分支列表"""
        # 检查是否应该跳过更新（保护用户交互）
        # 但是如果当前分支已经改变，应该强制更新显示
        current_combo_branch = self.get_current_branch_name()
        branch_changed = current_combo_branch != current_branch and current_branch
        
        if not force_update and not branch_changed and self._is_recent_user_interaction():
            print(f"🛡️ [DEBUG] 检测到近期用户交互，跳过分支列表更新")
            return
        
        # 暂时断开信号连接，避免在设置过程中触发用户交互事件
        self.currentIndexChanged.disconnect(self._on_user_selection_changed)
        
        try:
            self.clear()
            if branches:
                current_index = -1  # 记录当前分支的索引
                for i, branch in enumerate(branches):
                    display_text = branch
                    if branch == current_branch:
                        display_text = f"★ {branch} (当前)"
                        current_index = i  # 记录当前分支的位置
                    self.addItem(display_text)
                
                # 确保选中当前分支
                if current_index >= 0:
                    self.setCurrentIndex(current_index)
                    print(f"🎯 [DEBUG] 已设置当前分支选中: {current_branch} (索引: {current_index})")
                elif current_branch:
                    # 如果当前分支不在列表中，尝试查找匹配项
                    for i in range(self.count()):
                        item_text = self.itemText(i)
                        if current_branch in item_text or item_text.endswith(f"{current_branch} (当前)"):
                            self.setCurrentIndex(i)
                            print(f"🎯 [DEBUG] 通过匹配设置当前分支选中: {current_branch} (索引: {i})")
                            break
                
                # 如果分支发生了变化，重置用户交互标志
                if branch_changed:
                    self._user_is_interacting = False
                    print(f"🔄 [DEBUG] 分支已切换，重置用户交互标志: {current_combo_branch} -> {current_branch}")
                    
        finally:
            # 重新连接信号
            self.currentIndexChanged.connect(self._on_user_selection_changed)
    
    def _on_user_selection_changed(self, index):
        """用户选择改变时的回调"""
        import time
        self._user_is_interacting = True
        self._last_user_interaction_time = time.time()
        print(f"👤 [DEBUG] 用户手动选择分支，索引: {index}, 分支: {self.currentText()}")
        
        # 延迟重置交互标志，给异步操作一些缓冲时间
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, self._reset_user_interaction_flag)
    
    def _reset_user_interaction_flag(self):
        """重置用户交互标志"""
        self._user_is_interacting = False
        print(f"🔓 [DEBUG] 重置用户交互标志")
    
    def _is_recent_user_interaction(self) -> bool:
        """检查是否为近期用户交互"""
        import time
        return self._user_is_interacting and (time.time() - self._last_user_interaction_time) < 3.0  # 3秒内算作近期交互
    
    def get_current_branch_name(self):
        """获取当前选中的分支名称（去除装饰）"""
        text = self.currentText()
        if text.startswith("★ "):
            return text.replace("★ ", "").replace(" (当前)", "")
        return text


class DragDropListWidget(QListWidget):
    """支持拖拽的文件列表组件"""
    
    files_dropped = pyqtSignal(list)  # 文件拖拽信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        
        # 设置样式，使拖拽区域更明显
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            QListWidget:hover {
                border-color: #0078d4;
                background-color: #f0f8ff;
            }
        """)
        
        # 添加提示文本
        self.placeholder_item = QListWidgetItem("拖拽任意文件或文件夹到此处，或使用上方按钮选择")
        self.placeholder_item.setFlags(Qt.NoItemFlags)
        self.placeholder_item.setTextAlignment(Qt.AlignCenter)
        self.addItem(self.placeholder_item)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        print(f"DEBUG: dragEnterEvent called, hasUrls: {event.mimeData().hasUrls()}")
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            print("DEBUG: Drag accepted")
        else:
            event.ignore()
            print("DEBUG: Drag ignored")
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        print(f"DEBUG: dropEvent called, hasUrls: {event.mimeData().hasUrls()}")
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    file_paths.append(local_path)
                    print(f"DEBUG: Added file path: {local_path}")
            
            if file_paths:
                print(f"DEBUG: Emitting files_dropped signal with {len(file_paths)} files")
                self.files_dropped.emit(file_paths)
                event.acceptProposedAction()
            else:
                print("DEBUG: No valid file paths found")
                event.ignore()
        else:
            print("DEBUG: No URLs in mime data")
            event.ignore()
    
    def add_file_item(self, file_path: str):
        """添加文件项到列表"""
        # 移除占位符
        if self.count() > 0 and self.item(0) == self.placeholder_item:
            self.takeItem(0)
        
        item = QListWidgetItem(file_path)
        self.addItem(item)
    
    def clear_all_items(self):
        """清空所有项目并重新添加占位符"""
        self.clear()
        self.placeholder_item = QListWidgetItem("拖拽任意文件或文件夹到此处，或使用上方按钮选择")
        self.placeholder_item.setFlags(Qt.NoItemFlags)
        self.placeholder_item.setTextAlignment(Qt.AlignCenter)
        self.addItem(self.placeholder_item)


class LocalDeletedButGitExistsDialog(QDialog):
    """本地删除但Git存在引用的警告对话框"""
    
    def __init__(self, deleted_references, parent=None):
        super().__init__(parent)
        self.deleted_references = deleted_references
        self.user_choice = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("⚠️ 本地资源已删除警告")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # 移除问号按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("⚠️ 检测到本地资源已删除但仍被引用")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #d32f2f;")
        layout.addWidget(title)
        
        # 说明文字（使用HTML加粗关键词）
        description = QLabel(
            "以下材质引用的资源在本地SVN中已被删除，但Git仓库中仍然存在。<br>"
            "这可能导致其他使用者从Git获取后无法找到对应的本地资源。<br><br>"
            "请选择：<br>"
            "• <b>终止上传</b>：查看详细信息并修复问题后再上传<br>"
            "• <b>继续上传</b>：忽略警告，继续上传（不推荐）"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 10pt; padding: 10px;")
        layout.addWidget(description)
        
        # 创建表格显示问题
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["引用文件", "缺失资源", "资源类型", "GUID"])
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setRowCount(len(self.deleted_references))
        
        for row, ref_info in enumerate(self.deleted_references):
            table.setItem(row, 0, QTableWidgetItem(ref_info['referencing_file']))
            table.setItem(row, 1, QTableWidgetItem(ref_info['missing_file']))
            table.setItem(row, 2, QTableWidgetItem(ref_info['resource_type']))
            table.setItem(row, 3, QTableWidgetItem(ref_info['guid'][:16] + "..."))
        
        layout.addWidget(table)
        
        # 统计信息
        stats = QLabel(f"共发现 {len(self.deleted_references)} 个问题")
        stats.setStyleSheet("font-size: 10pt; font-weight: bold; color: #d32f2f;")
        layout.addWidget(stats)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        abort_button = QPushButton("终止上传")
        abort_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 12pt;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        abort_button.clicked.connect(self.on_abort)
        button_layout.addWidget(abort_button)
        
        continue_button = QPushButton("继续上传")
        continue_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                font-size: 12pt;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        continue_button.clicked.connect(self.on_continue)
        button_layout.addWidget(continue_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_abort(self):
        """用户选择终止"""
        self.user_choice = 'abort'
        self.accept()
    
    def on_continue(self):
        """用户选择继续"""
        self.user_choice = 'continue'
        self.accept()
    
    def get_user_choice(self):
        """获取用户选择"""
        return self.user_choice


class ArtResourceManager(QMainWindow):
    """美术资源管理器主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 🔇 抑制PyInstaller临时目录警告
        self._suppress_pyinstaller_warnings()
        
        # 🗑️ 处理删除旧exe的命令行参数
        self._handle_delete_old_exe()
        
        self.config_manager = ConfigManager()
        self.git_manager = GitSvnManager()
        self.upload_files = []
        # 文件夹上传模式跟踪
        self.folder_upload_modes = {}  # 格式：{folder_path: {"mode": "replace", "target_path": "..."}}
        # 本地删除但Git存在的引用列表
        self.local_deleted_but_git_exists = []
        
        # 🆕 初始化热更新管理器
        self.hot_updater = None
        if HOT_UPDATE_AVAILABLE:
            try:
                # 🌐 热更新服务器配置选择
                # 选项1: 使用现有Git服务器（推荐）
                git_update_url = "https://github.com/jasonaofa/Xproject.git"
                
                # 选项2: 本地测试服务器
                local_test_url = "http://localhost:8000/api"
                
                # 选项3: 可以配置为其他服务器
                # custom_url = "https://your-server.com/api"
                
                # 当前使用本地测试，您可以改为git_update_url
                # 🔧 热更新服务器配置选项
                update_server_options = {
                    "simple_file_local": "http://localhost:8002/api",  # 本地访问
                    "simple_file_lan": self._get_lan_server_url(),  # 局域网访问（动态检测或配置）
                    "github_api": "http://localhost:8001/api",  # GitHub API服务器
                    "github_pages": "https://jasonaofa.github.io/Xproject",  # GitHub Pages
                    "local_test": "http://localhost:8000/api"  # 本地测试服务器
                }
                
                # 从version.json文件读取当前版本
                current_version = self._read_current_version()
                self.hot_updater = HotUpdateManager(
                    current_version=current_version,
                    update_server_url=update_server_options["simple_file_lan"]  # 🔧 使用局域网地址，其他电脑可访问
                )
                print("✅ 热更新功能已启用")
                print(f"🌐 [DEBUG] 更新服务器地址: {self.hot_updater.update_server_url}")
            except Exception as e:
                print(f"⚠️ 热更新初始化失败: {e}")
                self.hot_updater = None
        
        # 初始化统计管理器
        if STATISTICS_AVAILABLE:
            try:
                self.statistics_ui = create_statistics_ui_manager(self)
                print("✅ 统计功能已启用")
            except Exception as e:
                print(f"⚠️ 统计功能初始化失败: {e}")
                self.statistics_ui = None
        else:
            self.statistics_ui = None
            print("ℹ️ 统计功能不可用")
        
        self.init_ui()
        self.load_settings()
    
    def _read_current_version(self):
        """从version.json文件读取当前版本"""
        try:
            version_file = os.path.join(os.path.dirname(__file__), "version.json")
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
                    return version_data.get('version', '1.0.0')
            else:
                print("⚠️ version.json文件不存在，使用默认版本")
                return '1.0.0'
        except Exception as e:
            print(f"⚠️ 读取版本文件失败: {e}")
            return '1.0.0'
    
    def _get_lan_server_url(self):
        """获取局域网服务器地址"""
        try:
            # 1. 尝试从配置文件读取
            config_file = "server_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    manual_lan = config.get("endpoints", {}).get("manual_lan", "")
                    if manual_lan and not manual_lan.startswith("http://192.168.1.100"):
                        print(f"📡 使用配置文件中的服务器地址: {manual_lan}")
                        return manual_lan
            
            # 2. 尝试扫描常见的局域网地址
            common_ips = [
                "10.0.6.167","10.0.6.231", "10.0.6.230", "10.0.6.232",   # 您的网段
                "192.168.1.100", "192.168.1.101", "192.168.1.102",
                "192.168.0.100", "192.168.0.101", "192.168.0.102",
                "10.0.0.100", "10.0.0.101", "10.0.0.102"
            ]
            
            for ip in common_ips:
                test_url = f"http://{ip}:8002/api/version_info"
                try:
                    import requests
                    response = requests.get(test_url, timeout=1)
                    if response.status_code == 200:
                        server_url = f"http://{ip}:8002/api"
                        print(f"🎯 自动检测到服务器: {server_url}")
                        return server_url
                except:
                    continue
            
            # 3. 如果都失败，返回默认地址
            default_url = "http://localhost:8002/api"
            print(f"⚠️ 无法检测到局域网服务器，使用默认地址: {default_url}")
            return default_url
            
        except Exception as e:
            print(f"⚠️ 获取服务器地址失败: {e}")
            return "http://localhost:8002/api"

    def init_ui(self):
        """初始化用户界面"""
        # 动态获取当前版本号
        current_version = self._read_current_version()  # 直接从文件读取，确保准确性
        if self.hot_updater:
            current_version = self.hot_updater.get_current_version()
        self.setWindowTitle(f"美术资源管理工具 v{current_version}")
        
        # 🆕 创建菜单栏
        self.create_menu_bar()
        
        # 设置窗口图标为默认状态（白色图标）
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            icon_path = os.path.join(sys._MEIPASS, 'app_icon_bai.ico')
        else:
            # 开发环境
            icon_path = os.path.join(os.path.dirname(__file__), 'app_icon_bai.ico')
            
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            print(f"🎨 [DEBUG] 设置默认图标: app_icon_bai.ico")
        else:
            print(f"警告: 默认图标文件不存在，尝试备用图标 {icon_path}")
            # 备用：使用绿色图标
            fallback_name = 'app_icon_lv.ico'
            if getattr(sys, 'frozen', False):
                fallback_path = os.path.join(sys._MEIPASS, fallback_name)
            else:
                fallback_path = os.path.join(os.path.dirname(__file__), fallback_name)
            if os.path.exists(fallback_path):
                self.setWindowIcon(QIcon(fallback_path))
                print(f"🎨 [DEBUG] 使用备用图标: {fallback_name}")
        
        # 从配置加载窗口几何信息
        geometry = self.config_manager.get_window_geometry()
        self.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
        
        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # 上半部分：配置和操作区域
        config_widget = self.create_config_widget()
        splitter.addWidget(config_widget)
        
        # 下半部分：日志和结果区域
        log_widget = self.create_log_widget()
        splitter.addWidget(log_widget)
        
        # 设置分割比例
        splitter.setSizes([400, 400])
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 管理菜单（仅管理员可见）
        admin_menu = menubar.addMenu('管理(&M)')
        
        # 查看上传统计
        if hasattr(self, 'statistics_ui') and self.statistics_ui:
            stats_action = QAction('上传统计(&S)', self)
            stats_action.setStatusTip('查看美术同事上传统计')
            stats_action.triggered.connect(self.statistics_ui.show_statistics_dialog)
            admin_menu.addAction(stats_action)
            
            # 导出统计报告
            export_stats_action = QAction('导出统计报告(&E)', self)
            export_stats_action.setStatusTip('导出详细统计报告')
            export_stats_action.triggered.connect(self.statistics_ui.export_statistics_report)
            admin_menu.addAction(export_stats_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
        # 检查更新菜单项
        if self.hot_updater:
            check_update_action = QAction('检查更新(&U)', self)
            check_update_action.setStatusTip('检查是否有可用的更新')
            check_update_action.triggered.connect(self._on_check_updates_clicked)
            help_menu.addAction(check_update_action)
            
            help_menu.addSeparator()
        
        # 关于菜单项
        about_action = QAction('关于(&A)', self)
        about_action.setStatusTip('关于美术资源管理工具')
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def _on_check_updates_clicked(self):
        """检查更新菜单点击处理"""
        if not self.hot_updater:
            QMessageBox.information(self, "提示", "热更新功能不可用")
            return
        
        try:
            # 在单独线程中检查更新，避免阻塞UI
            self.update_thread = UpdateCheckThread(self.hot_updater)
            self.update_thread.update_found.connect(self._on_update_found)
            self.update_thread.no_update.connect(self._on_no_update)
            self.update_thread.check_failed.connect(self._on_update_check_failed)
            self.update_thread.start()
            
            # 显示检查中的状态
            self.statusBar().showMessage("正在检查更新...")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"检查更新时发生错误：\n{e}")
    
    def _on_update_found(self, update_info):
        """发现更新时的处理"""
        self.statusBar().showMessage("发现新版本!")
        
        try:
            # 显示更新对话框
            dialog = UpdateDialog(update_info, self)
            if dialog.exec_() == QDialog.Accepted:
                self._start_update(update_info)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示更新对话框时发生错误：\n{e}")
    
    def _on_no_update(self):
        """没有更新时的处理"""
        self.statusBar().showMessage("当前已是最新版本")
        QMessageBox.information(self, "检查更新", "当前已是最新版本！")
    
    def _on_update_check_failed(self, error_msg):
        """更新检查失败时的处理"""
        self.statusBar().showMessage("更新检查失败")
        QMessageBox.warning(self, "更新检查失败", f"无法检查更新：\n{error_msg}")
    
    def _start_update(self, update_info):
        """开始更新"""
        try:
            # 在单独线程中执行更新
            self.update_execute_thread = UpdateExecuteThread(self.hot_updater, update_info)
            self.update_execute_thread.update_progress.connect(self._on_update_progress)
            self.update_execute_thread.update_completed.connect(self._on_update_completed)
            self.update_execute_thread.update_failed.connect(self._on_update_failed)
            self.update_execute_thread.start()
            
            # 显示更新进度对话框
            self.progress_dialog = QProgressDialog("正在下载更新...", "取消", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始更新时发生错误：\n{e}")
    
    def _on_update_progress(self, progress, message):
        """更新进度"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(progress)
            self.progress_dialog.setLabelText(message)
    
    def _on_update_completed(self):
        """更新完成"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        self.statusBar().showMessage("更新完成")
        
        # 显示更新完成信息，然后关闭应用
        QMessageBox.information(self, "更新完成", 
                              "更新已完成！\n\n"
                              "应用程序将关闭，请手动启动新版本。\n"
                              "新版本位置：当前目录下的版本化exe文件\n"
                              "（如：美术资源上传工具_v1.0.7.exe）")
        
        # 直接退出应用程序
        QApplication.quit()
    
    def _on_update_failed(self, error_msg):
        """更新失败"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        self.statusBar().showMessage("更新失败")
        QMessageBox.critical(self, "更新失败", f"更新过程中发生错误：\n{error_msg}")
    
    def _restart_application(self):
        """重启应用程序（已弃用，保留兼容性）"""
        # 这个方法已经不再使用，更新完成后直接退出应用
        # 用户需要手动启动新版本
        pass
    
    def _find_updated_exe(self):
        """查找更新后的exe文件"""
        try:
            # 检查重启信息
            restart_info_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "restart_info.json")
            print(f"🔍 查找重启信息: {restart_info_path}")
            
            if os.path.exists(restart_info_path):
                print(f"📄 重启信息文件存在")
                with open(restart_info_path, 'r', encoding='utf-8') as f:
                    restart_info = json.load(f)
                
                print(f"📋 重启信息内容: {restart_info}")
                
                # 优先使用新的exe路径
                new_exe_path = restart_info.get("new_exe_path", "")
                print(f"🎯 新exe路径: {new_exe_path}")
                
                if new_exe_path:
                    # 处理可能的编码问题
                    if not os.path.exists(new_exe_path):
                        # 尝试在当前目录查找相同名称的文件
                        exe_name = os.path.basename(new_exe_path)
                        current_dir_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), exe_name)
                        print(f"🔄 尝试当前目录路径: {current_dir_path}")
                        if os.path.exists(current_dir_path):
                            print(f"✅ 在当前目录找到文件: {current_dir_path}")
                            return current_dir_path
                        
                        # 尝试查找v1.0.7版本的exe文件
                        v107_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "美术资源上传工具_v1.0.7.exe")
                        print(f"🔄 尝试v1.0.7路径: {v107_path}")
                        if os.path.exists(v107_path):
                            print(f"✅ 找到v1.0.7版本: {v107_path}")
                            return v107_path
                    else:
                        print(f"✅ 新exe路径有效: {new_exe_path}")
                        return new_exe_path
                
                # 兼容旧格式
                exe_path = restart_info.get("exe_path", "")
                if exe_path and os.path.exists(exe_path):
                    print(f"✅ 使用旧格式exe路径: {exe_path}")
                    return exe_path
            else:
                print(f"❌ 重启信息文件不存在")
            
            return None
        except Exception as e:
            print(f"⚠️ 查找更新exe失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _cleanup_restart_info(self):
        """清理重启信息"""
        try:
            restart_info_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "restart_info.json")
            if os.path.exists(restart_info_path):
                os.remove(restart_info_path)
                print("🧹 清理重启信息")
        except Exception as e:
            print(f"⚠️ 清理重启信息失败: {e}")
    
    def _handle_delete_old_exe(self):
        """处理删除旧exe的命令行参数"""
        try:
            # 检查命令行参数
            import sys
            if len(sys.argv) >= 3 and sys.argv[1] == "--delete-old-exe":
                old_exe_path = sys.argv[2]
                
                if os.path.exists(old_exe_path):
                    # 延迟删除，确保旧进程已经退出
                    import time
                    import threading
                    
                    def delayed_delete():
                        time.sleep(2)  # 等待2秒确保旧进程退出
                        try:
                            os.remove(old_exe_path)
                            print(f"✅ 已删除旧版本: {old_exe_path}")
                        except Exception as e:
                            print(f"⚠️ 删除旧版本失败: {e}")
                    
                    # 在后台线程中执行删除
                    delete_thread = threading.Thread(target=delayed_delete)
                    delete_thread.daemon = True
                    delete_thread.start()
                    
                    print(f"🗑️ 计划删除旧版本: {old_exe_path}")
                else:
                    print(f"⚠️ 旧exe文件不存在: {old_exe_path}")
                    
        except Exception as e:
            print(f"❌ 处理删除旧exe失败: {e}")
    
    def _suppress_pyinstaller_warnings(self):
        """抑制PyInstaller临时目录警告"""
        try:
            import sys
            import os
            
            # 检查是否在PyInstaller环境中
            if getattr(sys, 'frozen', False):
                # 设置环境变量来抑制警告
                os.environ['PYINSTALLER_SUPPRESS_WARNINGS'] = '1'
                
                # 重定向stderr来抑制特定的警告消息
                import io
                from contextlib import redirect_stderr
                
                # 创建一个过滤器来忽略特定的警告
                class WarningFilter:
                    def __init__(self, original_stderr):
                        self.original_stderr = original_stderr
                    
                    def write(self, text):
                        # 过滤掉PyInstaller临时目录的警告
                        if 'Failed to remove temporary directory' not in text and '_MEI' not in text:
                            self.original_stderr.write(text)
                    
                    def flush(self):
                        self.original_stderr.flush()
                
                # 应用过滤器
                sys.stderr = WarningFilter(sys.stderr)
                print("🔇 已启用PyInstaller警告过滤器")
                
        except Exception as e:
            # 如果抑制失败，不影响程序运行
            pass
    
    def _cleanup_old_versions(self, new_exe_path):
        """清理旧版本exe文件"""
        try:
            import threading
            import time
            
            def delayed_cleanup():
                time.sleep(3)  # 等待3秒确保新版本启动
                try:
                    current_dir = os.path.dirname(new_exe_path)
                    new_exe_name = os.path.basename(new_exe_path)
                    
                    # 查找并删除旧版本exe文件
                    for filename in os.listdir(current_dir):
                        if (filename.endswith('.exe') and 
                            filename != new_exe_name and
                            filename.startswith('美术资源上传工具')):
                            
                            old_file_path = os.path.join(current_dir, filename)
                            try:
                                os.remove(old_file_path)
                                print(f"✅ 已删除旧版本: {filename}")
                            except Exception as e:
                                print(f"⚠️ 删除旧版本失败: {filename} - {e}")
                                
                except Exception as e:
                    print(f"❌ 清理旧版本失败: {e}")
            
            # 在后台线程中执行清理
            cleanup_thread = threading.Thread(target=delayed_cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
        except Exception as e:
            print(f"❌ 启动清理线程失败: {e}")
    
    def load_settings(self):
        """加载配置"""
        try:
            print("📋 [DEBUG] 加载配置...")
            
            # 加载路径配置
            svn_path = self.config_manager.get_svn_path()
            git_path = self.config_manager.get_git_path()
            
            # 加载并校验SVN路径
            if svn_path:
                if self._check_svn_root_directory(svn_path):
                    self.svn_path_edit.setText(svn_path)
                    print(f"✅ [DEBUG] SVN根目录校验通过: {svn_path}")
                else:
                    print(f"⚠️ [DEBUG] 已保存的SVN路径不是根目录: {svn_path}")
                    # 尝试查找根目录
                    root_path = self._find_repository_root(svn_path, 'svn')
                    if root_path:
                        print(f"🔧 [DEBUG] 找到SVN根目录: {root_path}")
                        self.svn_path_edit.setText(root_path)
                        self.config_manager.set_svn_path(root_path)  # 更新配置
                        self.log_text.append(f"⚠️ SVN路径已自动修正为根目录: {root_path}")
                    else:
                        print(f"❌ [DEBUG] 未找到有效的SVN根目录，清空路径")
                        self.log_text.append(f"⚠️ 已保存的SVN路径无效，已清空: {svn_path}")
            
            # 加载并校验Git路径
            if git_path:
                is_git_root = self._check_git_root_directory(git_path)
                is_git_working_tree = self._verify_git_repository_with_command(git_path)
                
                if is_git_root or is_git_working_tree:
                    self.git_path_edit.setText(git_path)
                    if is_git_root:
                        print(f"✅ [DEBUG] Git根目录校验通过（检测到.git）: {git_path}")
                    elif is_git_working_tree:
                        print(f"✅ [DEBUG] Git工作树校验通过（git命令验证）: {git_path}")
                else:
                    print(f"⚠️ [DEBUG] 已保存的Git路径不是根目录: {git_path}")
                    # 尝试查找根目录
                    root_path = self._find_repository_root(git_path, 'git')
                    if root_path:
                        print(f"🔧 [DEBUG] 找到Git根目录: {root_path}")
                        self.git_path_edit.setText(root_path)
                        self.config_manager.set_git_path(root_path)  # 更新配置
                        self.log_text.append(f"⚠️ Git路径已自动修正为根目录: {root_path}")
                    else:
                        print(f"❌ [DEBUG] 未找到有效的Git根目录，清空路径")
                        self.log_text.append(f"⚠️ 已保存的Git路径无效，已清空: {git_path}")
            

            
            # 设置Git管理器路径
            if git_path and svn_path:
                self.git_manager.set_paths(git_path, svn_path)
                
                # 🚀 超快速启动模式：仅获取当前分支，不进行网络操作
                print("⚡ [DEBUG] 启用超快速启动模式...")
                self.refresh_branches_async(fast_mode=True, ultra_fast=True)
                
                # 🔄 启动后台完整分支获取（延迟启动，避免阻塞界面）
                print("🌐 [DEBUG] 准备后台获取完整分支列表...")
                QTimer.singleShot(1000, lambda: self.refresh_branches_async(fast_mode=True, ultra_fast=False))
                
                # 设置定时器定期检查当前分支显示
                self.setup_branch_sync_timer()
            
            print("✅ [DEBUG] 配置加载完成")
            
            # 更新路径映射按钮文本
            self.update_mapping_button_text()
            
            # 设置初始图标状态为默认（白色）
            self.set_window_icon_status("default")
            
        except Exception as e:
            print(f"❌ [DEBUG] 加载配置失败: {e}")
            self.log_text.append(f"加载配置失败: {str(e)}")
            # 配置加载失败时设置为默认图标
            self.set_window_icon_status("default")
    
    def save_settings(self):
        """保存设置"""
        # 保存路径配置
        self.config_manager.set_svn_path(self.svn_path_edit.text())
        self.config_manager.set_git_path(self.git_path_edit.text())
        
        # 保存窗口几何信息
        geometry = self.geometry()
        self.config_manager.set_window_geometry(geometry.x(), geometry.y(), geometry.width(), geometry.height())
        
        # 保存当前选择的分支
        current_branch = self.branch_combo.currentText()
        if current_branch:
            self.config_manager.set_last_selected_branch(current_branch)
        
        # 保存最近使用的文件
        for file_path in self.upload_files:
            self.config_manager.add_recent_file(file_path)
        
        # 保存配置到文件
        self.config_manager.save_config()
        
    def closeEvent(self, event):
        """程序关闭事件"""
        # 停止定时器
        if hasattr(self, 'branch_sync_timer'):
            self.branch_sync_timer.stop()
            print("⏰ [DEBUG] 分支同步定时器已停止")
        
        self.save_settings()
        event.accept()
    
    def set_window_icon_status(self, status: str = "default"):
        """动态设置窗口图标状态
        
        Args:
            status (str): 图标状态
                - "default": 默认状态 - 绿色图标 (app_icon_lv.ico) - 程序正常运行状态
                - "success": 成功状态 - 绿色图标 (app_icon_lv.ico)  
                - "error": 错误状态 - 红色图标 (app_icon.ico)
                - 也支持旧的布尔值参数以保持兼容性
        """
        try:
            # 兼容旧的布尔值参数
            if isinstance(status, bool):
                if status:  # True = has_error
                    icon_name = 'app_icon.ico'
                    status_text = "错误状态"
                else:  # False = no error (success)
                    icon_name = 'app_icon_lv.ico'
                    status_text = "成功状态"
            else:
                # 新的字符串参数
                if status == "error":
                    icon_name = 'app_icon.ico'  # 错误状态 - 红色图标
                    status_text = "错误状态"
                elif status == "success":
                    icon_name = 'app_icon_lv.ico'  # 成功状态 - 绿色图标
                    status_text = "成功状态"
                else:  # default
                    icon_name = 'app_icon_lv.ico'  # 默认状态 - 绿色图标（程序正常运行状态）
                    status_text = "正常运行状态"
            
            # 获取图标路径（兼容打包后的路径）
            if getattr(sys, 'frozen', False):
                # 打包后的exe环境
                icon_path = os.path.join(sys._MEIPASS, icon_name)
            else:
                # 开发环境
                icon_path = os.path.join(os.path.dirname(__file__), icon_name)
            
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                print(f"🔄 [DEBUG] 图标已切换到{status_text}: {icon_name}")
            else:
                print(f"⚠️ [DEBUG] 图标文件不存在: {icon_path}")
                
        except Exception as e:
            print(f"❌ [DEBUG] 图标切换失败: {str(e)}")
    
    def create_config_widget(self) -> QWidget:
        """创建配置widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 路径配置组
        path_group = QGroupBox("路径配置")
        path_layout = QGridLayout()
        path_group.setLayout(path_layout)
        
        # SVN路径
        path_layout.addWidget(QLabel("SVN仓库路径:"), 0, 0)
        self.svn_path_edit = QLineEdit()
        self.svn_path_edit.setText("E:/newprefab04")
        path_layout.addWidget(self.svn_path_edit, 0, 1)
        svn_browse_btn = QPushButton("浏览")
        svn_browse_btn.clicked.connect(self.browse_svn_path)
        path_layout.addWidget(svn_browse_btn, 0, 2)
        svn_open_btn = QPushButton("打开文件夹")
        svn_open_btn.clicked.connect(self.open_svn_folder)
        path_layout.addWidget(svn_open_btn, 0, 3)
        
        # Git路径
        path_layout.addWidget(QLabel("Git仓库路径:"), 1, 0)
        self.git_path_edit = QLineEdit()
        self.git_path_edit.setText("E:/git8a/assetruntimenew/CommonResource")
        path_layout.addWidget(self.git_path_edit, 1, 1)
        git_browse_btn = QPushButton("浏览")
        git_browse_btn.clicked.connect(self.browse_git_path)
        path_layout.addWidget(git_browse_btn, 1, 2)
        git_open_btn = QPushButton("打开文件夹")
        git_open_btn.clicked.connect(self.open_git_folder)
        path_layout.addWidget(git_open_btn, 1, 3)
        

        
        layout.addWidget(path_group)
        
        # 操作按钮组
        btn_layout = QHBoxLayout()
        
        self.pull_branch_btn = QPushButton("拉取分支")
        self.pull_branch_btn.clicked.connect(self.pull_current_branch)
        btn_layout.addWidget(self.pull_branch_btn)
        
        # 添加修复Git同步问题按钮
        self.fix_sync_btn = QPushButton("修复同步问题")
        self.fix_sync_btn.clicked.connect(self.fix_git_sync_issues)
        self.fix_sync_btn.setToolTip("自动修复Git认证和同步问题")
        btn_layout.addWidget(self.fix_sync_btn)
        
        self.update_new_btn = QPushButton("重置更新仓库")
        self.update_new_btn.clicked.connect(self.reset_update_merge)
        btn_layout.addWidget(self.update_new_btn)
        
        self.delete_btn = QPushButton("一键删除重拉")
        self.delete_btn.clicked.connect(self.delete_duplicates)
        btn_layout.addWidget(self.delete_btn)
        

        
        self.show_git_url_btn = QPushButton("显示git仓url")
        self.show_git_url_btn.clicked.connect(self.show_git_url)
        btn_layout.addWidget(self.show_git_url_btn)
        

        
        layout.addLayout(btn_layout)
        

        
        # 分支操作
        branch_ops_layout = QHBoxLayout()
        
        branch_ops_layout.addWidget(QLabel("分支管理:"))
        self.branch_combo = SimpleBranchComboBox()
        self.branch_combo.setMinimumWidth(250)
        branch_ops_layout.addWidget(self.branch_combo)
        
        self.select_branch_btn = QPushButton("选择分支")
        self.select_branch_btn.clicked.connect(self.open_branch_selector)
        branch_ops_layout.addWidget(self.select_branch_btn)
        
        self.switch_branch_btn = QPushButton("切换到选定分支")
        self.switch_branch_btn.clicked.connect(self.switch_to_selected_branch)
        branch_ops_layout.addWidget(self.switch_branch_btn)
        
        self.show_current_branch_btn = QPushButton("显示当前分支名")
        self.show_current_branch_btn.clicked.connect(self.show_current_branch)
        branch_ops_layout.addWidget(self.show_current_branch_btn)
        
        layout.addLayout(branch_ops_layout)
        
        # 高级功能分组框（可折叠）
        advanced_group = QGroupBox("高级功能（点击展开/收起）")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)  # 默认收起
        advanced_layout = QVBoxLayout()
        advanced_group.setLayout(advanced_layout)
        
        # 连接折叠功能
        advanced_group.toggled.connect(self._toggle_advanced_features)
        
        # 路径映射测试
        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("测试路径映射:"))
        self.test_path_edit = QLineEdit()
        self.test_path_edit.setPlaceholderText("输入SVN文件路径进行测试...")
        test_layout.addWidget(self.test_path_edit)
        
        self.test_path_btn = QPushButton("测试映射")
        self.test_path_btn.clicked.connect(self.test_path_mapping)
        test_layout.addWidget(self.test_path_btn)
        
        advanced_layout.addLayout(test_layout)
        
        # GUID查询
        guid_layout = QHBoxLayout()
        guid_layout.addWidget(QLabel("输入GUID在SVN仓库查询对应资源:"))
        self.guid_edit = QLineEdit()
        guid_layout.addWidget(self.guid_edit)
        
        self.query_btn = QPushButton("查询")
        self.query_btn.clicked.connect(self.query_guid)
        guid_layout.addWidget(self.query_btn)
        
        advanced_layout.addLayout(guid_layout)
        
        # 路径映射管理
        mapping_layout = QHBoxLayout()
        mapping_layout.addWidget(QLabel("路径映射管理:"))
        
        self.manage_mapping_btn = QPushButton("管理映射规则")
        self.manage_mapping_btn.clicked.connect(self.open_path_mapping_manager)
        mapping_layout.addWidget(self.manage_mapping_btn)
        
        self.toggle_mapping_btn = QPushButton("启用/禁用映射")
        self.toggle_mapping_btn.clicked.connect(self.toggle_path_mapping)
        mapping_layout.addWidget(self.toggle_mapping_btn)
        
        advanced_layout.addLayout(mapping_layout)
        
        # GUID缓存管理
        cache_layout = QHBoxLayout()
        cache_layout.addWidget(QLabel("GUID缓存管理:"))
        
        self.clear_cache_btn = QPushButton("清除GUID缓存")
        self.clear_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton:pressed {
                background-color: #D84315;
            }
        """)
        self.clear_cache_btn.clicked.connect(self.clear_guid_cache)
        cache_layout.addWidget(self.clear_cache_btn)
        
        self.show_cache_info_btn = QPushButton("显示缓存信息")
        self.show_cache_info_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton:pressed {
                background-color: #455A64;
            }
        """)
        self.show_cache_info_btn.clicked.connect(self.show_cache_info)
        cache_layout.addWidget(self.show_cache_info_btn)
        
        # 测试Git同步状态按钮
        self.test_git_sync_btn = QPushButton("测试Git同步")
        self.test_git_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8E24AA;
            }
            QPushButton:pressed {
                background-color: #7B1FA2;
            }
        """)
        self.test_git_sync_btn.clicked.connect(self.test_git_sync_status)
        cache_layout.addWidget(self.test_git_sync_btn)
        
        # Git仓库诊断按钮
        self.diagnose_git_btn = QPushButton("诊断Git仓库")
        self.diagnose_git_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
        """)
        self.diagnose_git_btn.clicked.connect(self.diagnose_git_repository_ui)
        cache_layout.addWidget(self.diagnose_git_btn)
        
        advanced_layout.addLayout(cache_layout)
        
        # CRLF问题处理
        crlf_layout = QHBoxLayout()
        crlf_layout.addWidget(QLabel("CRLF问题处理:"))
        
        self.quick_fix_crlf_btn = QPushButton("快速修复CRLF")
        self.quick_fix_crlf_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        self.quick_fix_crlf_btn.clicked.connect(self.quick_fix_crlf)
        crlf_layout.addWidget(self.quick_fix_crlf_btn)
        
        self.smart_fix_crlf_btn = QPushButton("智能修复CRLF")
        self.smart_fix_crlf_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.smart_fix_crlf_btn.clicked.connect(self.smart_fix_crlf)
        crlf_layout.addWidget(self.smart_fix_crlf_btn)
        
        advanced_layout.addLayout(crlf_layout)
        
        # 一键部署git仓库
        deploy_layout = QHBoxLayout()
        deploy_layout.addWidget(QLabel("一键部署:"))
        
        self.deploy_repos_btn = QPushButton("一键部署git仓库")
        self.deploy_repos_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.deploy_repos_btn.clicked.connect(self.deploy_git_repositories)
        deploy_layout.addWidget(self.deploy_repos_btn)
        
        advanced_layout.addLayout(deploy_layout)
        
        # 保存高级功能分组框的引用，用于折叠控制
        self.advanced_group = advanced_group
        layout.addWidget(advanced_group)
        
        # 初始化时隐藏高级功能内容
        self._toggle_advanced_features(False)
        
        # 文件选择区域
        file_group = QGroupBox("选择要上传的文件（支持拖拽任意文件类型）")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)
        
        file_btn_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("选择文件")
        self.select_files_btn.clicked.connect(self.select_files)
        file_btn_layout.addWidget(self.select_files_btn)
        
        self.select_folder_btn = QPushButton("选择文件夹")
        self.select_folder_btn.clicked.connect(self.select_folder)
        file_btn_layout.addWidget(self.select_folder_btn)
        
        self.clear_files_btn = QPushButton("清空列表")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_btn_layout.addWidget(self.clear_files_btn)
        
        # 添加依赖文件按钮（无样式）
        self.add_dependencies_btn = QPushButton("增加依赖文件")
        self.add_dependencies_btn.clicked.connect(self.add_dependency_files)
        file_btn_layout.addWidget(self.add_dependencies_btn)
        
        # 添加检查资源按钮（绿底白字）
        self.check_btn = QPushButton("检查资源")
        self.check_btn.clicked.connect(self.check_and_push)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        file_btn_layout.addWidget(self.check_btn)
        
        file_layout.addLayout(file_btn_layout)
        
        # 使用支持拖拽的文件列表
        self.file_list = DragDropListWidget()
        self.file_list.setMaximumHeight(150)
        self.file_list.files_dropped.connect(self.on_files_dropped)
        file_layout.addWidget(self.file_list)
        
        layout.addWidget(file_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return widget
    
    def create_log_widget(self) -> QWidget:
        """创建日志widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 日志标签页
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        tab_widget.addTab(self.log_text, "操作日志")
        
        # 结果标签页
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 9))
        tab_widget.addTab(self.result_text, "检查结果")
        
        return widget
    
    def _check_svn_root_directory(self, path: str) -> bool:
        """检查是否为SVN仓库根目录"""
        if not path or not os.path.exists(path):
            return False
        
        svn_dir = os.path.join(path, '.svn')
        return os.path.exists(svn_dir) and os.path.isdir(svn_dir)
    
    def _check_git_root_directory(self, path: str) -> bool:
        """检查是否为Git仓库根目录（包括submodule支持）"""
        if not path or not os.path.exists(path):
            return False
        
        git_path = os.path.join(path, '.git')
        
        # 检查.git是否存在
        if not os.path.exists(git_path):
            return False
        
        # 如果.git是目录，直接认为是Git根目录
        if os.path.isdir(git_path):
            return True
        
        # 如果.git是文件（submodule情况），检查文件内容
        if os.path.isfile(git_path):
            try:
                with open(git_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # submodule的.git文件格式：gitdir: ../../../.git/modules/submodule_name
                    if content.startswith('gitdir:'):
                        gitdir_path = content[7:].strip()  # 移除"gitdir: "前缀
                        
                        # 如果是相对路径，转换为绝对路径
                        if not os.path.isabs(gitdir_path):
                            gitdir_path = os.path.join(path, gitdir_path)
                        
                        # 规范化路径并检查是否存在
                        gitdir_path = os.path.normpath(gitdir_path)
                        return os.path.exists(gitdir_path) and os.path.isdir(gitdir_path)
                        
            except Exception as e:
                print(f"⚠️ [DEBUG] 读取.git文件失败: {e}")
                return False
        
        return False
    
    def _find_repository_root(self, start_path: str, repo_type: str) -> str:
        """向上查找仓库根目录"""
        current_path = os.path.abspath(start_path)
        
        while True:
            if repo_type == 'svn' and self._check_svn_root_directory(current_path):
                return current_path
            elif repo_type == 'git' and self._check_git_root_directory(current_path):
                return current_path
            
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:  # 已经到达根目录
                break
            current_path = parent_path
        
        return ""
    
    def _verify_git_repository_with_command(self, path: str) -> bool:
        """使用git命令验证是否为有效的Git仓库根目录"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            , creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0:
                # 获取git根目录路径
                git_root = result.stdout.strip()
                # 比较是否与当前路径一致
                return os.path.abspath(path) == os.path.abspath(git_root)
            
        except Exception as e:
            print(f"⚠️ [DEBUG] Git命令验证失败: {e}")
        
        return False
    
    def browse_svn_path(self):
        """浏览SVN路径"""
        path = QFileDialog.getExistingDirectory(self, "选择SVN仓库路径")
        if path:
            # 检查是否为SVN根目录
            if not self._check_svn_root_directory(path):
                # 尝试向上查找SVN根目录
                root_path = self._find_repository_root(path, 'svn')
                
                if root_path:
                    reply = QMessageBox.question(
                        self,
                        "路径校验",
                        f"所选路径不是SVN仓库根目录！\n\n"
                        f"选择的路径：{path}\n"
                        f"检测到的SVN根目录：{root_path}\n\n"
                        f"是否使用检测到的SVN根目录？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        path = root_path
                        self.log_text.append(f"✅ 已自动修正为SVN根目录: {path}")
                    else:
                        self.log_text.append(f"❌ 用户拒绝使用建议的SVN根目录")
                        return
                else:
                    QMessageBox.warning(
                        self,
                        "路径校验失败",
                        f"所选路径不是有效的SVN仓库根目录！\n\n"
                        f"选择的路径：{path}\n\n"
                        f"请确保选择的目录包含 .svn 文件夹。\n"
                        f"SVN仓库根目录应该是执行 'svn checkout' 命令后创建的目录。"
                    )
                    self.log_text.append(f"❌ SVN路径校验失败: {path}")
                    return
            else:
                self.log_text.append(f"✅ SVN根目录校验通过: {path}")
            
            self.svn_path_edit.setText(path)
            self.config_manager.set_svn_path(path)
    
    def browse_git_path(self):
        """浏览Git路径"""
        path = QFileDialog.getExistingDirectory(self, "选择Git仓库路径")
        if path:
            # 检查是否为Git根目录（包括submodule支持）
            is_git_root = self._check_git_root_directory(path)
            
            # 额外使用git命令验证（对于复杂的submodule情况）
            is_git_working_tree = self._verify_git_repository_with_command(path)
            
            if not is_git_root and not is_git_working_tree:
                # 尝试向上查找Git根目录
                root_path = self._find_repository_root(path, 'git')
                
                if root_path:
                    reply = QMessageBox.question(
                        self,
                        "路径校验",
                        f"所选路径不是Git仓库根目录！\n\n"
                        f"选择的路径：{path}\n"
                        f"检测到的Git根目录：{root_path}\n\n"
                        f"是否使用检测到的Git根目录？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        path = root_path
                        self.log_text.append(f"✅ 已自动修正为Git根目录: {path}")
                    else:
                        self.log_text.append(f"❌ 用户拒绝使用建议的Git根目录")
                        return
                else:
                    QMessageBox.warning(
                        self,
                        "路径校验失败",
                        f"所选路径不是有效的Git仓库根目录！\n\n"
                        f"选择的路径：{path}\n\n"
                        f"请确保选择的目录满足以下条件之一：\n"
                        f"• 包含 .git 目录（普通Git仓库）\n"
                        f"• 包含 .git 文件且指向有效的gitdir（Git submodule）\n"
                        f"• 是一个有效的Git工作树根目录\n\n"
                        f"Git仓库根目录应该是执行 'git clone' 或 'git init' 命令的目录。"
                    )
                    self.log_text.append(f"❌ Git路径校验失败: {path}")
                    return
            else:
                # 确定检测类型并记录
                if is_git_root:
                    self.log_text.append(f"✅ Git根目录校验通过（检测到.git）: {path}")
                elif is_git_working_tree:
                    self.log_text.append(f"✅ Git工作树校验通过（git命令验证）: {path}")
            
            self.git_path_edit.setText(path)
            self.config_manager.set_git_path(path)
            self.git_manager.set_paths(path, self.svn_path_edit.text())
            # 使用异步方法，避免阻塞界面
            self.refresh_branches_async(fast_mode=True)
    

    
    def open_svn_folder(self):
        """打开SVN文件夹"""
        path = self.svn_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "警告", "SVN仓库路径为空！")
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "警告", f"SVN仓库路径不存在：{path}")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], creationflags=SUBPROCESS_FLAGS)
            else:
                subprocess.run(["xdg-open", path], creationflags=SUBPROCESS_FLAGS)
            
            self.log_text.append(f"已打开SVN文件夹: {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹: {str(e)}")
            self.log_text.append(f"打开SVN文件夹失败: {str(e)}")
    
    def open_git_folder(self):
        """打开Git文件夹"""
        path = self.git_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "警告", "Git仓库路径为空！")
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "警告", f"Git仓库路径不存在：{path}")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], creationflags=SUBPROCESS_FLAGS)
            else:
                subprocess.run(["xdg-open", path], creationflags=SUBPROCESS_FLAGS)
            
            self.log_text.append(f"已打开Git文件夹: {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹: {str(e)}")
            self.log_text.append(f"打开Git文件夹失败: {str(e)}")
    

    
    def refresh_branches_async(self, fast_mode: bool = False, ultra_fast: bool = False, force_update_ui: bool = False):
        """异步刷新分支列表"""
        if hasattr(self, 'branch_load_thread') and self.branch_load_thread.isRunning():
            print("⚠️ [DEBUG] 分支加载线程已在运行，跳过...")
            return
        
        try:
            print(f"🔄 [DEBUG] 开始异步加载分支...")
            if ultra_fast:
                print(f"   ⚡ 超快速模式：仅获取当前分支")
            elif fast_mode:
                print(f"   🚀 快速模式：跳过网络操作")
            else:
                print(f"   🌐 完整模式：包含网络操作")
            
            # 设置强制更新标志
            if force_update_ui:
                self._force_branch_update = True
                print(f"   🛠️ 启用强制UI更新模式")
            
            self.branch_load_thread = BranchLoadThread(self.git_manager, fast_mode, ultra_fast)
            self.branch_load_thread.branches_loaded.connect(self.on_branches_loaded)
            self.branch_load_thread.load_failed.connect(self.on_branches_load_failed)
            self.branch_load_thread.start()
            
        except Exception as e:
            print(f"❌ [DEBUG] 启动分支加载线程失败: {e}")
            self.log_text.append(f"启动分支加载线程失败: {str(e)}")
    
    def on_branches_loaded(self, branches: list, current_branch: str):
        """分支加载完成回调"""
        try:
            # 检查是否为超快速模式的结果
            is_ultra_fast_result = len(branches) == 1 and branches[0] == current_branch
            
            if is_ultra_fast_result:
                # 超快速模式的结果（只有当前分支）
                print(f"⚡ [DEBUG] 超快速启动完成，当前分支: {current_branch}")
                # 总是更新显示当前分支，确保分支信息同步
                self.branch_combo.set_branches(branches, current_branch, force_update=True)
            else:
                # 普通模式或完整分支加载的结果
                print(f"🌐 [DEBUG] 完整分支列表加载完成，共 {len(branches)} 个分支，当前分支: {current_branch}")
                
                # 保存用户当前的选择（如果有的话）
                user_selected_branch = None
                if self.branch_combo.count() > 0:
                    current_text = self.branch_combo.currentText()
                    if current_text:
                        # 提取实际的分支名称
                        if current_text.startswith("★ "):
                            user_selected_branch = current_text.replace("★ ", "").replace(" (当前)", "")
                        else:
                            user_selected_branch = current_text
                        print(f"🔄 [DEBUG] 保存用户当前选择: {user_selected_branch}")
                
                # 更新分支列表（检查是否需要强制更新）
                force_update = getattr(self, '_force_branch_update', False)
                self.branch_combo.set_branches(branches, current_branch, force_update=force_update)
                # 重置强制更新标志
                if hasattr(self, '_force_branch_update'):
                    delattr(self, '_force_branch_update')
                
                # 如果用户之前有选择且该分支仍然存在，恢复用户的选择
                # 但只有在该分支不是当前分支时才恢复
                if (user_selected_branch and user_selected_branch != current_branch and 
                    user_selected_branch in branches):
                    for i in range(self.branch_combo.count()):
                        item_text = self.branch_combo.itemText(i)
                        if (user_selected_branch in item_text and 
                            (item_text == user_selected_branch or item_text.startswith(f"★ {user_selected_branch}"))):
                            self.branch_combo.setCurrentIndex(i)
                            print(f"🎯 [DEBUG] 已恢复用户选择的分支: {user_selected_branch}")
                            break
                
                # 记录到日志
                self.log_text.append(f"刷新分支列表完成，共获取到 {len(branches)} 个分支")
                if current_branch:
                    self.log_text.append(f"当前分支: {current_branch}")
                    
        except Exception as e:
            print(f"❌ [DEBUG] 处理分支列表时出错: {e}")
            self.log_text.append(f"处理分支列表时出错: {str(e)}")
    
    def on_branches_load_failed(self, error_message: str):
        """分支加载失败回调"""
        self.log_text.append(f"⚠️ {error_message}")
    
    def refresh_branches(self):
        """同步刷新分支列表（保留用于兼容性）"""
        if self.git_path_edit.text():
            self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
            
        branches = self.git_manager.get_git_branches()
        current_branch = self.git_manager.get_current_branch()
        
        if branches:
            self.branch_combo.set_branches(branches, current_branch)
            self.log_text.append(f"刷新分支列表完成，共获取到 {len(branches)} 个分支")
            if current_branch:
                self.log_text.append(f"当前分支: {current_branch}")
        else:
            self.log_text.append("⚠️ 未获取到任何分支")
    
    def setup_branch_sync_timer(self):
        """设置分支同步定时器"""
        self.branch_sync_timer = QTimer(self)
        self.branch_sync_timer.timeout.connect(self.sync_current_branch_display)
        # 每30秒检查一次当前分支显示
        self.branch_sync_timer.start(30000)
        print("⏰ [DEBUG] 分支同步定时器已启动 (30秒间隔)")
    
    def sync_current_branch_display(self):
        """同步当前分支显示"""
        try:
            if not self.git_path_edit.text():
                return
            
            # 获取当前分支
            current_branch = self.git_manager.get_current_branch()
            if not current_branch:
                return
            
            # 获取组合框当前显示的分支
            current_combo_branch = self.branch_combo.get_current_branch_name()
            
            # 如果当前分支与显示的分支不一致，且不是用户正在交互
            if (current_branch != current_combo_branch and 
                not self.branch_combo._is_recent_user_interaction()):
                
                print(f"🔄 [DEBUG] 检测到分支变化: {current_combo_branch} -> {current_branch}")
                # 触发快速分支刷新
                self.refresh_branches_async(fast_mode=True, ultra_fast=True, force_update_ui=True)
                
        except Exception as e:
            print(f"❌ [DEBUG] 同步分支显示失败: {e}")
    
    def show_current_branch(self):
        """显示当前分支"""
        current_branch = self.git_manager.get_current_branch()
        self.log_text.append(f"当前分支: {current_branch}")
        QMessageBox.information(self, "当前分支", f"当前分支: {current_branch}")
    
    def switch_to_selected_branch(self):
        """切换到选定的分支"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        selected_branch = self.branch_combo.get_current_branch_name()
        if not selected_branch:
            QMessageBox.warning(self, "警告", "请选择要切换的分支！")
            return
        
        current_branch = self.git_manager.get_current_branch()
        if selected_branch == current_branch:
            QMessageBox.information(self, "提示", f"已经在分支 '{selected_branch}' 上了")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认切换分支", 
            f"确定要从分支 '{current_branch}' 切换到分支 '{selected_branch}' 吗？\n\n"
            "⚠️ 注意：切换分支前请确保已保存所有重要更改！\n"
            "⏰ 切换过程可能需要一些时间，请耐心等待。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了分支切换操作")
            return
        
        # 禁用相关按钮，防止重复操作
        self.branch_combo.setEnabled(False)
        
        self.log_text.append(f"🔄 开始切换分支: {current_branch} -> {selected_branch}")
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("正在切换分支...")
        
        # 创建分支切换线程
        self.branch_switch_thread = BranchSwitchThread(self.git_manager, selected_branch, current_branch)
        self.branch_switch_thread.progress_updated.connect(self.progress_bar.setValue)
        self.branch_switch_thread.status_updated.connect(self.log_text.append)
        self.branch_switch_thread.switch_completed.connect(self.on_branch_switch_completed)
        
        # 启动线程
        self.branch_switch_thread.start()
    
    def on_branch_switch_completed(self, success: bool, selected_branch: str, current_branch: str, message: str):
        """分支切换完成回调"""
        try:
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            self.progress_bar.setFormat("")
            
            # 重新启用按钮
            self.branch_combo.setEnabled(True)
            
            if success:
                self.log_text.append(f"✅ 分支切换成功: 已切换到 {selected_branch}")
                self.log_text.append("🔄 GUID缓存已自动清除（分支切换后仓库内容可能变化）")
                self.result_text.append(f"✅ 分支切换成功: {current_branch} -> {selected_branch}")
                QMessageBox.information(self, "切换成功", f"已成功切换到分支: {selected_branch}\n\n🔄 GUID缓存已自动清除，确保下次检查使用最新数据。")
                
                # 异步刷新分支列表，避免阻塞界面（强制更新，因为分支已切换）
                self.refresh_branches_async(fast_mode=True, force_update_ui=True)
                
                # 重置用户交互标志，确保能立即更新显示
                self.branch_combo._user_is_interacting = False
            else:
                self.log_text.append(f"❌ 分支切换失败: {message}")
                self.result_text.append(f"❌ 分支切换失败: {current_branch} -> {selected_branch}")
                QMessageBox.critical(self, "切换失败", f"切换到分支 '{selected_branch}' 失败！\n\n错误信息: {message}")
                
        except Exception as e:
            error_msg = f"处理分支切换结果时发生异常: {str(e)}"
            self.log_text.append(f"❌ {error_msg}")
            QMessageBox.critical(self, "操作异常", error_msg)
            
            # 确保按钮重新启用
            self.branch_combo.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def select_files(self):
        """选择文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要上传的文件", "",
            "Unity资源文件 (*.prefab *.mat *.anim *.controller *.asset *.unity);;所有文件 (*.*)"
        )
        
        for file in files:
            if file not in self.upload_files:
                self.upload_files.append(file)
                self.file_list.add_file_item(file)
    
    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择要上传的文件夹")
        if folder:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path not in self.upload_files:
                        self.upload_files.append(file_path)
                        self.file_list.add_file_item(file_path)
    
    def clear_files(self):
        """清空文件列表"""
        self.upload_files.clear()
        self.file_list.clear_all_items()
        # 清空文件夹上传模式信息
        self.folder_upload_modes.clear()
        # 重置图标状态到默认状态
        self.set_window_icon_status("default")
    
    def check_and_push(self):
        """检查资源（不自动推送）"""
        if not self.upload_files:
            QMessageBox.warning(self, "警告", "请先选择要上传的文件！")
            return
        
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认检查资源", 
            f"即将检查 {len(self.upload_files)} 个文件的资源依赖和GUID冲突，包括：\n\n"
            "🔄 前置步骤（新增）：\n"
            "• Git重置仓库 (git reset --hard)\n"
            "• 清理未跟踪文件 (git clean -f)\n"
            "• 拉取最新代码 (git pull)\n\n"
            "🔍 检查项目：\n"
            "• Meta文件完整性检查\n"
            "• 中文字符检查\n"
            "• 图片尺寸检查\n"
            "• 图片文件扩展名大小写检查\n"
            "• GUID一致性检查\n"
            "• GUID引用检查\n\n"
            f"📁 目标仓库：{self.git_path_edit.text()}\n"
            f"📁 目标目录：CommonResource\n\n"
            "⚠️ 注意：\n"
            "• 重置操作会丢失本地未提交的更改\n"
            "• 检查过程可能需要一些时间\n"
            "• 如果拉取失败，检查将停止\n\n"
            "确定要开始吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了检查操作")
            return
        
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.checker_thread = ResourceChecker(
            self.upload_files, 
            self.git_manager, 
            "CommonResource",
            self.folder_upload_modes
        )
        
        self.checker_thread.progress_updated.connect(self.progress_bar.setValue)
        self.checker_thread.status_updated.connect(self.log_text.append)
        self.checker_thread.check_completed.connect(self.on_check_completed)
        self.checker_thread.detailed_report.connect(self.on_detailed_report_received)
        self.checker_thread.git_sync_required.connect(self.on_git_sync_required)
        self.checker_thread.local_deleted_warning.connect(self.on_local_deleted_warning)
        
        # 设置运行中状态图标
        self.set_window_icon_status("success")  # 运行中使用绿色图标
        
        self.checker_thread.start()
        self.log_text.append("开始检查资源...")
    
    def on_local_deleted_warning(self, deleted_references):
        """接收本地删除但Git存在的引用警告"""
        self.local_deleted_but_git_exists = deleted_references
        self.log_text.append(f"⚠️ 收到 {len(deleted_references)} 个本地删除警告")
    
    def on_git_sync_required(self, sync_info: dict):
        """处理Git同步需求"""
        self.progress_bar.setVisible(False)
        
        # 构建同步状态描述
        current_branch = sync_info.get('current_branch', '未知')
        message = sync_info.get('message', '')
        details = sync_info.get('details', [])
        needs_reset = sync_info.get('needs_reset', False)
        conflict_risk = sync_info.get('conflict_risk', False)
        
        # 构建详细信息
        detail_text = f"🔍 **Git仓库同步检查**\n\n"
        detail_text += f"**当前分支**: {current_branch}\n"
        detail_text += f"**状态**: {message}\n\n"
        
        if details:
            detail_text += "**详细信息**:\n"
            for detail in details:
                detail_text += f"• {detail}\n"
            detail_text += "\n"
        
        if needs_reset:
            detail_text += "**推荐操作**: 重置更新仓库\n"
            detail_text += "重置更新会：\n"
            detail_text += "• 重置本地更改到远程分支状态\n"
            detail_text += "• 拉取最新的远程更新\n"
            detail_text += "• 避免合并冲突\n\n"
        else:
            detail_text += "**推荐操作**: 拉取远程更新\n\n"
        
        detail_text += "❓ **是否要更新仓库后继续检查？**"
        
        # 显示对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("需要更新Git仓库")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(detail_text)
        
        # 添加按钮
        if needs_reset:
            update_button = msg_box.addButton("重置更新仓库", QMessageBox.AcceptRole)
        else:
            update_button = msg_box.addButton("拉取更新", QMessageBox.AcceptRole)
        
        cancel_button = msg_box.addButton("取消检查", QMessageBox.RejectRole)
        msg_box.setDefaultButton(update_button)
        
        # 记录日志
        self.log_text.append(f"⚠️ Git仓库需要更新：{message}")
        if details:
            for detail in details:
                self.log_text.append(f"   {detail}")
        
        # 显示对话框并处理结果
        msg_box.exec()
        
        if msg_box.clickedButton() == update_button:
            self.log_text.append("用户选择更新仓库...")
            if needs_reset:
                self.log_text.append("🔄 执行重置更新操作...")
                self.reset_update_merge(skip_confirmation=True)  # 跳过二次确认
            else:
                self.log_text.append("📥 执行拉取更新操作...")
                self.pull_current_branch()
            
            # 更新完成后自动重新开始检查
            QTimer.singleShot(2000, self.restart_check_after_update)
        else:
            self.log_text.append("用户取消了检查操作")
            self.result_text.append("❌ 检查已取消：需要先更新Git仓库")

    def restart_check_after_update(self):
        """更新后重新开始检查"""
        self.log_text.append("🔄 仓库更新完成，重新开始检查...")
        self.check_and_push()

    def on_check_completed(self, success: bool, message: str):
        """检查完成回调"""
        self.progress_bar.setVisible(False)
        
        # 根据检查结果更新图标状态
        if success:
            self.set_window_icon_status("success")  # 检查通过 - 绿色图标
        else:
            self.set_window_icon_status("error")    # 检查失败 - 红色图标
        
        if success:
            self.result_text.append(f"✓ 检查通过: {message}")
            self.log_text.append("✅ 所有检查通过！准备推送...")
            self.show_push_confirmation_dialog()
        else:
            self.result_text.append(f"✗ 检查失败: {message}")
            QMessageBox.critical(self, "检查失败", message)
    
    def show_push_confirmation_dialog(self):
        """显示推送确认对话框"""
        # 先检查是否有本地删除但仍被引用的资源
        if self.local_deleted_but_git_exists:
            self.log_text.append("⚠️ 发现本地删除但仍被引用的资源，请用户确认...")
            
            # 弹出警告对话框
            dialog = LocalDeletedButGitExistsDialog(self.local_deleted_but_git_exists, self)
            dialog.exec_()
            user_choice = dialog.get_user_choice()
            
            if user_choice == 'abort':
                # 用户选择终止
                self.log_text.append("❌ 用户选择终止上传")
                self.result_text.append("=" * 50)
                self.result_text.append("⚠️ 本地资源已删除但仍被引用：")
                self.result_text.append("=" * 50)
                
                for ref_info in self.local_deleted_but_git_exists:
                    self.result_text.append(f"\n【引用文件】{ref_info['referencing_file']}")
                    self.result_text.append(f"  缺失资源: {ref_info['missing_file']}")
                    self.result_text.append(f"  资源类型: {ref_info['resource_type']}")
                    self.result_text.append(f"  GUID: {ref_info['guid']}")
                    self.result_text.append(f"  Git路径: {ref_info['missing_file_path']}")
                    self.result_text.append(f"  说明: 该资源在本地SVN中已被删除，但材质仍在引用")
                    self.result_text.append(f"  解决方案: 恢复被删除的资源，或更新材质移除对该资源的引用")
                
                self.result_text.append("\n" + "=" * 50)
                self.result_text.append(f"共 {len(self.local_deleted_but_git_exists)} 个问题，上传已终止")
                self.result_text.append("=" * 50)
                
                QMessageBox.warning(self, "上传终止", 
                    f"检测到 {len(self.local_deleted_but_git_exists)} 个本地删除但仍被引用的资源。\n"
                    "详细信息已显示在检查结果中。\n\n"
                    "请修复这些问题后再次上传。")
                return
            else:
                # 用户选择继续
                self.log_text.append("✅ 用户选择继续上传")
                self.local_deleted_but_git_exists = []  # 清空警告
        
        # 继续正常的推送确认流程
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("检查通过 - 确认推送")
        msg_box.setIcon(QMessageBox.Question)
        
        dialog_text = (
            f"🎯 资源检查通过！\n\n"
            f"检查结果:\n"
            f"• 文件数量：{len(self.upload_files)} 个\n"
            f"• 目标仓库：{os.path.basename(self.git_path_edit.text())}\n\n"
            f"是否要将这些文件推送到Git仓库?"
        )
        msg_box.setText(dialog_text)
        
        push_button = msg_box.addButton("推送到Git", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.setDefaultButton(push_button)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == push_button:
            self.log_text.append("用户确认推送文件")
            self.execute_push_operation()
        else:
            self.log_text.append("用户取消了推送操作")
            QMessageBox.information(self, "操作取消", "文件检查通过，但推送操作被取消。\n您可以稍后手动推送这些文件。")
    
    def execute_push_operation(self):
        """执行推送操作"""
        try:
            # 设置运行中状态图标
            self.set_window_icon_status("success")  # 推送中使用绿色图标
            
            # 开始推送操作
            self.log_text.append("开始推送文件到Git仓库...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            git_path = self.git_path_edit.text()
            svn_path = self.svn_path_edit.text()
            
            # 🔍 详细调试输出：推送操作参数
            print(f"🚀 [PUSH_DEBUG] ========== 推送操作调试信息 ==========")
            print(f"   调用函数: ArtResourceManager.execute_push_operation()")
            print(f"   Git路径配置: {git_path}")
            print(f"   SVN路径配置: {svn_path}")
            print(f"   上传文件数量: {len(self.upload_files)}")
            print(f"   上传文件列表:")
            for i, file_path in enumerate(self.upload_files):
                print(f"     {i+1}. {file_path}")
            print(f"   ================================================")
            
            self.git_manager.set_paths(git_path, svn_path)
            
            self.progress_bar.setValue(20)
            
            # 执行推送操作 - 直接使用git_path，不需要额外的target_directory参数
            # 因为git_path已经是完整的目标路径（例如：G:\minirepo\AssetRuntime_Branch07\assetruntime\CommonResource）
            # 传递文件夹上传模式信息以支持替换模式
            success, message = self.git_manager.push_files_to_git(self.upload_files, folder_upload_modes=self.folder_upload_modes)
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            if success:
                success_msg = f"✅ 推送完成！{message}"
                self.log_text.append(success_msg)
                self.result_text.append(success_msg)
                
                # 🔧 记录上传统计（成功）
                if STATISTICS_AVAILABLE:
                    record_successful_upload(
                        file_count=len(self.upload_files),
                        file_paths=self.upload_files,
                        git_path=git_path,
                        additional_info={"target_directory": "CommonResource"}
                    )
                
                # 推送成功后恢复默认图标状态（绿色）
                self.set_window_icon_status("default")
                
                summary_text = (
                    f"📊 推送完成！\n\n"
                    f"推送信息:\n"
                    f"• 文件数量: {len(self.upload_files)} 个\n"
                    f"• 目标仓库: {os.path.basename(self.git_path_edit.text())}\n"
                    f"• 推送结果: {message}\n\n"
                    f"所有文件已成功推送到Git仓库！"
                )
                QMessageBox.information(
                    self, 
                    "推送成功", 
                    f"📊 推送完成！\n\n"
                    f"推送信息:\n"
                    f"• 文件数量: {len(self.upload_files)} 个\n"
                    f"• 目标仓库: {os.path.basename(self.git_path_edit.text())}\n"
                    f"• 当前分支：{self.git_manager.get_current_branch()}\n\n"
                    f"{message}"
                )
            else:
                error_msg = f"✗ 推送失败: {message}"
                self.log_text.append(error_msg)
                self.result_text.append(error_msg)
                
                # 🔧 记录上传统计（失败）
                if STATISTICS_AVAILABLE:
                    record_failed_upload(
                        file_count=len(self.upload_files),
                        file_paths=self.upload_files,
                        error_message=message,
                        git_path=git_path,
                        additional_info={"target_directory": "CommonResource"}
                    )
                
                # 推送失败设置错误图标状态（红色）
                self.set_window_icon_status("error")
                
                # 🚨 改进的错误提示消息
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Critical)
                error_dialog.setWindowTitle("❌ 推送失败")
                error_dialog.setText(
                    f"🚨 文件推送到Git远程仓库失败\n\n"
                    f"💡 重要说明：\n"
                    f"• 文件未成功上传到远程Git仓库\n"
                    f"• 团队其他成员无法获取这些文件\n"
                    f"• 如果开启了自动回滚，本地更改已被撤销\n\n"
                    f"📊 失败详情：\n{message}"
                )
                error_dialog.setDetailedText(
                    f"推送失败诊断信息：\n\n"
                    f"请检查以下项目：\n"
                    f"• Git仓库路径是否正确\n"
                    f"• 网络连接是否正常\n"
                    f"• 是否有推送权限\n"
                    f"• 分支是否存在冲突\n"
                    f"• Git认证是否配置正确\n\n"
                    f"建议操作：\n"
                    f"1. 检查网络连接和Git服务器状态\n"
                    f"2. 尝试手动执行 'git pull' 同步远程更改\n"
                    f"3. 解决可能的冲突后重新推送\n"
                    f"4. 如需帮助，请联系技术支持"
                )
                error_dialog.exec_()
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            error_msg = f"推送操作发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
            # 推送异常设置错误图标状态（红色）
            self.set_window_icon_status("error")
            QMessageBox.critical(self, "推送异常", f"推送文件到Git仓库时发生异常：\n{error_msg}")
    
    def on_detailed_report_received(self, report: dict):
        """处理详细报告"""
        try:
            # 显示详细报告
            if 'report_text' in report:
                # 使用新的报告格式
                self.result_text.clear()
                self.result_text.append(report['report_text'])
            else:
                # 兼容旧的报告格式
                self.result_text.clear()
                self.result_text.append("检查报告")
                self.result_text.append("=" * 40)
                
                if not report.get('has_errors', True):
                    self.result_text.append("✅ 所有检查通过！")
                else:
                    total_issues = report.get('total_issues', 0)
                    self.result_text.append(f"❌ 发现 {total_issues} 个问题")
                    
                    issues_by_type = report.get('issues_by_type', {})
                    for category, issues in issues_by_type.items():
                        if issues:
                            self.result_text.append(f"\n{category}: {len(issues)} 个问题")
                            for issue in issues[:5]:
                                file_name = os.path.basename(issue.get('file', ''))
                                message = issue.get('message', '')
                                self.result_text.append(f"  • {file_name}: {message}")
                            if len(issues) > 5:
                                self.result_text.append(f"  ... 还有 {len(issues) - 5} 个问题")
            
            # 更新日志
            if not report.get('has_errors', True):
                self.log_text.append("✅ 检查完成：所有文件通过检查")
            else:
                total_issues = report.get('total_issues', 0)
                file_count = report.get('total_files', len(self.upload_files))
                self.log_text.append(f"❌ 检查完成：{file_count} 个文件中发现 {total_issues} 个问题")
        
        except Exception as e:
            error_msg = f"处理检查报告时发生错误: {str(e)}"
            self.result_text.append(error_msg)
            self.log_text.append(error_msg)
    
    def pull_current_branch(self):
        """拉取当前分支"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认拉取分支", 
            "此操作将从远程仓库拉取当前分支的最新代码，包括：\n\n"
            "• 获取远程仓库最新信息 (git fetch)\n"
            "• 拉取并合并当前分支 (git pull)\n\n"
            "⚠️ 注意：如果有冲突可能需要手动解决！确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了拉取操作")
            return
        
        self.log_text.append("开始拉取当前分支...")
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        try:
            self.progress_bar.setValue(30)
            success, message = self.git_manager.pull_current_branch()
            self.progress_bar.setValue(100)
            
            if success:
                self.log_text.append(f"✓ 拉取成功: {message}")
                self.log_text.append("🔄 GUID缓存已自动清除（仓库内容已更新）")
                self.result_text.append(f"✓ Git分支拉取成功: {message}")
                QMessageBox.information(self, "拉取成功", f"{message}\n\n🔄 GUID缓存已自动清除，确保下次检查使用最新数据。")
                # 异步刷新分支列表，避免阻塞界面（强制更新，因为可能有新分支）
                self.refresh_branches_async(fast_mode=True, force_update_ui=True)
                self.show_current_branch()
            else:
                self.log_text.append(f"✗ 拉取失败: {message}")
                self.result_text.append(f"✗ Git分支拉取失败: {message}")
                QMessageBox.critical(self, "拉取失败", f"拉取Git分支失败：\n{message}")
                
        except Exception as e:
            error_msg = f"拉取操作发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
            QMessageBox.critical(self, "操作异常", error_msg)
        
        finally:
            self.progress_bar.setVisible(False)
    
    def fix_git_sync_issues(self):
        """修复Git同步和认证问题"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        reply = QMessageBox.question(
            self, 
            "修复Git同步问题", 
            "此功能将自动修复常见的Git同步和认证问题：\n\n"
            "• 配置Git凭据存储（避免重复输入密码）\n"
            "• 测试远程仓库连接\n"
            "• 尝试同步远程更改\n"
            "• 提供详细的解决方案指导\n\n"
            "⚠️ 如果需要输入用户名密码，请按提示操作。\n\n"
            "确定要开始修复吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了Git同步问题修复")
            return
        
        self.log_text.append("🔧 开始修复Git同步和认证问题...")
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        try:
            self.progress_bar.setValue(20)
            self.log_text.append("🔍 检查Git配置...")
            
            self.progress_bar.setValue(50)
            success, message = self.git_manager.auto_fix_git_sync_issues()
            self.progress_bar.setValue(100)
            
            if success:
                self.log_text.append(f"✓ 修复成功: {message}")
                self.result_text.append(f"✓ Git同步问题修复成功")
                QMessageBox.information(
                    self, 
                    "修复成功", 
                    f"{message}\n\n"
                    "💡 现在您可以正常推送文件了！\n"
                    "如果之前需要输入密码，现在密码已被保存。"
                )
            else:
                self.log_text.append(f"⚠️ 修复提示: {message}")
                self.result_text.append(f"⚠️ Git同步问题需要手动处理")
                
                # 显示详细的解决方案
                if "认证失败" in message:
                    QMessageBox.information(
                        self, 
                        "需要手动认证", 
                        f"{message}\n\n"
                        "💡 完成上述步骤后，Git认证问题将得到解决。"
                    )
                else:
                    QMessageBox.warning(self, "修复提示", message)
                
        except Exception as e:
            error_msg = f"修复过程发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
            QMessageBox.critical(self, "操作异常", error_msg)
        
        finally:
            self.progress_bar.setVisible(False)
    
    def reset_update_merge(self, skip_confirmation=False):
        """重置更新仓库"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        # 如果不是自动调用，需要用户确认
        if not skip_confirmation:
            reply = QMessageBox.question(
                self, 
                "确认重置更新仓库", 
                "此操作将重置更新Git仓库到远程最新状态，包括：\n\n"
                "• 获取远程仓库最新信息 (git fetch)\n"
                "• 清理所有未跟踪的文件和目录 (git clean -f -d)\n"
                "• 强制重置到远程分支最新状态 (git reset --hard origin/分支名)\n\n"
                "⚠️ 警告：此操作会丢失所有未提交的本地更改！\n"
                "✅ 优势：彻底解决分支冲突，确保与远程仓库完全同步\n\n"
                "确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                self.log_text.append("用户取消了重置操作")
                return
        
        # 设置运行中状态图标
        self.set_window_icon_status("success")  # 重置中使用绿色图标
        
        self.log_text.append("开始重置Git仓库...")
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        try:
            success, message = self.git_manager.reset_git_repository()
            self.progress_bar.setValue(100)
            
            if success:
                self.log_text.append(f"✓ 重置成功: {message}")
                self.log_text.append("🔄 GUID缓存已自动清除（仓库内容已重置）")
                self.result_text.append(f"✓ Git仓库重置成功: {message}")
                QMessageBox.information(self, "重置成功", f"{message}\n\n🔄 GUID缓存已自动清除，确保下次检查使用最新数据。")
                # 重置成功后恢复默认图标状态（绿色）
                self.set_window_icon_status("default")
                # 异步刷新分支列表，避免阻塞界面（强制更新，因为状态已重置）
                self.refresh_branches_async(fast_mode=True, force_update_ui=True)
                self.show_current_branch()
            else:
                self.log_text.append(f"✗ 重置失败: {message}")
                self.result_text.append(f"✗ Git仓库重置失败: {message}")
                QMessageBox.critical(self, "重置失败", f"重置Git仓库失败：\n{message}")
                # 重置失败也恢复默认图标状态（绿色）
                self.set_window_icon_status("default")
                
        except Exception as e:
            error_msg = f"重置操作发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
            QMessageBox.critical(self, "操作异常", error_msg)
        
        finally:
            self.progress_bar.setVisible(False)
    
    def delete_duplicates(self):
        """一键删除重拉 - 删除本地仓库并重新克隆"""
        git_path = self.git_path_edit.text().strip()
        if not git_path:
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        if not os.path.exists(git_path):
            QMessageBox.warning(self, "警告", f"Git仓库路径不存在：{git_path}")
            return
        
        # 获取远程仓库URL
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  cwd=git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                QMessageBox.critical(self, "错误", "无法获取远程仓库URL，请确保这是一个有效的Git仓库！")
                return
                
            remote_url = result.stdout.strip()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取远程仓库URL失败：{str(e)}")
            return
        
        # 获取当前分支名
        current_branch = ""
        try:
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                current_branch = result.stdout.strip()
        except:
            pass
        
        # 确认对话框
        parent_dir = os.path.dirname(git_path)
        repo_name = os.path.basename(git_path)
        
        warning_msg = f"⚠️ 危险操作确认 ⚠️\n\n"
        warning_msg += f"即将执行一键删除重拉操作：\n\n"
        warning_msg += f"📁 仓库路径：{git_path}\n"
        warning_msg += f"🌐 远程URL：{remote_url}\n"
        if current_branch:
            warning_msg += f"🌿 当前分支：{current_branch}\n"
        warning_msg += f"\n🗑️ 操作步骤：\n"
        warning_msg += f"  1. 完全删除本地仓库目录及所有内容\n"
        warning_msg += f"  2. 在原位置重新克隆远程仓库\n"
        if current_branch:
            warning_msg += f"  3. 切换到原分支：{current_branch}\n"
        warning_msg += f"\n❌ 警告：本地所有未提交的更改将永久丢失！\n"
        warning_msg += f"❌ 警告：本地分支和stash将全部丢失！\n"
        warning_msg += f"\n确定要继续吗？"
        
        reply = QMessageBox.question(
            self,
            "确认一键删除重拉",
            warning_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了一键删除重拉操作")
            return
        
        # 二次确认
        confirm_msg = f"🚨 最后确认 🚨\n\n"
        confirm_msg += f"您真的要删除整个目录并重新克隆吗？\n"
        confirm_msg += f"路径：{git_path}\n\n"
        confirm_msg += f"此操作不可撤销！"
        
        final_reply = QMessageBox.question(
            self,
            "最后确认",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if final_reply != QMessageBox.Yes:
            self.log_text.append("用户在最后确认时取消了操作")
            return
        
        # 设置运行中状态图标
        self.set_window_icon_status("success")  # 删除重拉中使用绿色图标
        
        # 开始执行操作
        self.log_text.append("🚨 开始执行一键删除重拉操作...")
        self.log_text.append(f"📁 目标路径: {git_path}")
        self.log_text.append(f"🌐 远程URL: {remote_url}")
        
        # 禁用相关按钮，防止重复操作
        self.delete_btn.setEnabled(False)
        self.pull_branch_btn.setEnabled(False)
        self.update_new_btn.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("准备删除重拉操作...")
        
        # 创建取消按钮（临时添加到界面）
        if not hasattr(self, 'cancel_delete_btn'):
            self.cancel_delete_btn = QPushButton("取消操作")
            self.cancel_delete_btn.clicked.connect(self.cancel_delete_reclone)
            self.cancel_delete_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; font-weight: bold; }")
        
        # 将取消按钮添加到进度条旁边
        progress_layout = self.progress_bar.parent().layout()
        if progress_layout and self.cancel_delete_btn not in [progress_layout.itemAt(i).widget() for i in range(progress_layout.count())]:
            progress_layout.addWidget(self.cancel_delete_btn)
        
        self.cancel_delete_btn.setVisible(True)
        
        # 创建并启动删除重拉线程
        self.delete_reclone_thread = DeleteAndRecloneThread(
            git_path, remote_url, current_branch, parent_dir, repo_name
        )
        
        # 连接信号
        self.delete_reclone_thread.progress_updated.connect(self.progress_bar.setValue)
        self.delete_reclone_thread.status_updated.connect(self.on_delete_reclone_status_updated)
        self.delete_reclone_thread.operation_completed.connect(self.on_delete_reclone_completed)
        
        # 启动线程
        self.delete_reclone_thread.start()
    
    def on_delete_reclone_status_updated(self, status: str):
        """删除重拉状态更新回调"""
        self.log_text.append(status)
        self.progress_bar.setFormat(status)
    
    def on_delete_reclone_completed(self, success: bool, message: str):
        """删除重拉操作完成回调"""
        try:
            # 隐藏进度条和取消按钮
            self.progress_bar.setVisible(False)
            self.progress_bar.setFormat("")
            if hasattr(self, 'cancel_delete_btn'):
                self.cancel_delete_btn.setVisible(False)
            
            # 重新启用按钮
            self.delete_btn.setEnabled(True)
            self.pull_branch_btn.setEnabled(True)
            self.update_new_btn.setEnabled(True)
            
            if success:
                self.log_text.append("🎉 一键删除重拉操作完成！")
                self.result_text.append(f"✅ 一键删除重拉成功：{self.git_path_edit.text()}")
                
                # 删除重拉成功后恢复默认图标状态（绿色）
                self.set_window_icon_status("default")
                
                # 刷新分支列表
                self.refresh_branches_async(fast_mode=True, force_update_ui=True)
                
                QMessageBox.information(
                    self, 
                    "操作完成", 
                    f"一键删除重拉操作已完成！\n\n"
                    f"仓库已重新克隆到：{self.git_path_edit.text()}\n"
                    f"请检查分支列表和文件内容。"
                )
            else:
                self.log_text.append(f"❌ 操作失败：{message}")
                QMessageBox.critical(self, "操作失败", f"一键删除重拉失败：\n\n{message}")
                # 删除重拉失败也恢复默认图标状态（绿色）
                self.set_window_icon_status("default")
                
        except Exception as e:
            self.log_text.append(f"❌ 处理操作结果时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"处理操作结果时出错：{str(e)}")
    
    def cancel_delete_reclone(self):
        """取消删除重拉操作"""
        if hasattr(self, 'delete_reclone_thread') and self.delete_reclone_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认取消",
                "确定要取消删除重拉操作吗？\n\n"
                "注意：如果已经开始删除目录，取消操作可能导致仓库处于不完整状态。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.log_text.append("⚠️ 用户请求取消删除重拉操作...")
                
                # 终止线程
                self.delete_reclone_thread.terminate()
                self.delete_reclone_thread.wait(3000)  # 等待3秒
                
                # 隐藏进度条和取消按钮
                self.progress_bar.setVisible(False)
                self.progress_bar.setFormat("")
                if hasattr(self, 'cancel_delete_btn'):
                    self.cancel_delete_btn.setVisible(False)
                
                # 重新启用按钮
                self.delete_btn.setEnabled(True)
                self.pull_branch_btn.setEnabled(True)
                self.update_new_btn.setEnabled(True)
                
                self.log_text.append("❌ 删除重拉操作已取消")
                QMessageBox.warning(self, "操作已取消", "删除重拉操作已被取消。\n\n如果操作已部分完成，请检查仓库状态。")
    

    
    def show_git_url(self):
        """显示git仓url"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  cwd=self.git_path_edit.text(), 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                url = result.stdout.strip()
                self.log_text.append(f"Git仓库URL: {url}")
                
                dialog = QDialog(self)
                dialog.setWindowTitle("Git仓库URL")
                dialog.setMinimumWidth(500)
                dialog.setMinimumHeight(150)
                
                layout = QVBoxLayout()
                dialog.setLayout(layout)
                
                url_text = QTextEdit()
                url_text.setPlainText(url)
                url_text.setReadOnly(True)
                url_text.setMaximumHeight(60)
                layout.addWidget(url_text)
                
                button_layout = QHBoxLayout()
                
                copy_btn = QPushButton("复制")
                copy_btn.clicked.connect(lambda: self.copy_url_to_clipboard(url))
                button_layout.addWidget(copy_btn)
                
                ok_btn = QPushButton("确定")
                ok_btn.clicked.connect(dialog.accept)
                ok_btn.setDefault(True)
                button_layout.addWidget(ok_btn)
                
                layout.addLayout(button_layout)
                dialog.exec_()
                
            else:
                QMessageBox.warning(self, "错误", "无法获取Git仓库URL")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取Git URL失败: {str(e)}")
    
    def copy_url_to_clipboard(self, url: str):
        """复制URL到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            self.log_text.append(f"已复制URL到剪贴板: {url}")
            QMessageBox.information(self, "复制成功", "Git仓库URL已复制到剪贴板！")
        except Exception as e:
            QMessageBox.critical(self, "复制失败", f"复制到剪贴板失败: {str(e)}")
    
    def query_guid(self):
        """查询GUID"""
        guid = self.guid_edit.text().strip()
        if not guid:
            QMessageBox.warning(self, "警告", "请输入GUID！")
            return
        
        if not self.svn_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置SVN仓库路径！")
            return
        
        self.log_text.append(f"在SVN仓库中查询GUID: {guid}")
        
        found_files = []
        svn_path = self.svn_path_edit.text()
        
        for root, dirs, files in os.walk(svn_path):
            for file in files:
                if file.endswith('.meta'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if guid in content:
                                found_files.append(file_path)
                    except Exception:
                        continue
        
        if found_files:
            result_msg = f"找到 {len(found_files)} 个匹配的文件:\n"
            for file in found_files[:10]:
                result_msg += f"  {file}\n"
            if len(found_files) > 10:
                result_msg += f"  ... 还有 {len(found_files) - 10} 个文件"
            
            self.result_text.append(result_msg)
            QMessageBox.information(self, "查询结果", result_msg)
        else:
            msg = f"未找到GUID为 {guid} 的文件"
            self.result_text.append(msg)
            QMessageBox.information(self, "查询结果", msg)

    def clear_guid_cache(self):
        """清除GUID缓存"""
        try:
            if not self.git_manager.git_path or not os.path.exists(self.git_manager.git_path):
                QMessageBox.warning(self, "警告", "Git仓库路径无效，无法清除缓存")
                return
            
            # 创建缓存管理器并清除缓存
            cache_manager = GitGuidCacheManager(self.git_manager.git_path)
            
            if cache_manager.clear_cache():
                QMessageBox.information(self, "成功", "GUID缓存已清除！\n下次上传时将重新建立缓存。")
                self.log_text.append("✅ GUID缓存已清除")
            else:
                QMessageBox.warning(self, "失败", "清除GUID缓存失败")
                self.log_text.append("❌ 清除GUID缓存失败")
                
        except Exception as e:
            error_msg = f"清除缓存时发生异常: {e}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_text.append(f"❌ {error_msg}")
    
    def show_cache_info(self):
        """显示GUID缓存信息"""
        try:
            if not self.git_manager.git_path or not os.path.exists(self.git_manager.git_path):
                QMessageBox.warning(self, "警告", "Git仓库路径无效，无法获取缓存信息")
                return
            
            # 创建缓存管理器并获取缓存信息
            cache_manager = GitGuidCacheManager(self.git_manager.git_path)
            cache_info = cache_manager.get_cache_info()
            
            # 构建信息字符串
            info_lines = []
            if cache_info['cache_exists']:
                info_lines.append(f"✅ 缓存状态: 存在")
                info_lines.append(f"📅 上次扫描时间: {cache_info['last_scan_time']}")
                info_lines.append(f"🏷️ Git提交版本: {cache_info['last_commit_hash']}")
                info_lines.append(f"🎯 缓存GUID数量: {cache_info['total_guids']:,}")
                info_lines.append(f"📁 缓存文件大小: {cache_info['cache_file_size'] / 1024:.1f} KB")
                
                # 计算性能提升预期
                if cache_info['total_guids'] > 1000:
                    estimated_time_saved = cache_info['total_guids'] / 100  # 粗略估算
                    info_lines.append(f"⚡ 预计节省扫描时间: ~{estimated_time_saved:.0f}秒")
            else:
                info_lines.append("❌ 缓存状态: 不存在")
                info_lines.append("📝 说明: 首次上传时将自动建立缓存")
            
            info_text = "\n".join(info_lines)
            
            QMessageBox.information(self, "GUID缓存信息", info_text)
            self.log_text.append("📊 已显示GUID缓存信息")
            
        except Exception as e:
            error_msg = f"获取缓存信息时发生异常: {e}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_text.append(f"❌ {error_msg}")

    def test_git_sync_status(self):
        """测试Git同步状态检查功能"""
        if not self.git_manager or not self.git_manager.git_path:
            QMessageBox.warning(self, "警告", "请先配置Git路径")
            return
            
        try:
            self.log_text.append("🔍 开始测试Git同步状态检查...")
            
            # 创建一个临时的ResourceChecker实例来测试Git同步检查
            checker = ResourceChecker([], self.git_manager, "")
            result = checker._check_git_sync_status()
            
            # 格式化显示同步状态信息
            status_text = f"""**Git同步状态测试结果**

**基本状态**
- 仓库最新: {'是' if result['is_up_to_date'] else '否'}
- 需要拉取: {'是' if result['needs_pull'] else '否'}
- 需要重置: {'是' if result['needs_reset'] else '否'}
- 冲突风险: {'是' if result['conflict_risk'] else '否'}

**分支信息**
- 当前分支: {result.get('current_branch', '未知')}
- 本地领先: {result['local_ahead']} 个提交
- 远程领先: {result['remote_ahead']} 个提交
- 远程可达: {'是' if result.get('remote_reachable', False) else '否'}

**状态消息**
{result.get('message', '无消息')}

**详细信息**"""
            
            if result.get('details'):
                for detail in result['details']:
                    status_text += f"\n- {detail}"
            else:
                status_text += "\n- 无详细信息"
                
            # 使用对话框显示结果
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Git同步状态测试结果")
            msg_box.setText(status_text)
            
            # 根据结果设置图标
            if result['is_up_to_date']:
                msg_box.setIcon(QMessageBox.Information)
            elif result['conflict_risk']:
                msg_box.setIcon(QMessageBox.Warning)
            else:
                msg_box.setIcon(QMessageBox.Question)
            
            msg_box.exec_()
            
            self.log_text.append("✅ Git同步状态测试完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"Git同步状态测试失败：{str(e)}")
            self.log_text.append(f"❌ Git同步状态测试失败：{str(e)}")

    def diagnose_git_repository_ui(self):
        """Git仓库诊断UI"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        try:
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 执行诊断
            diagnosis = self.git_manager.diagnose_git_repository()
            
            # 构建诊断报告
            report = "🔍 Git仓库诊断报告\n"
            report += "=" * 50 + "\n\n"
            
            report += f"📁 Git路径: {diagnosis['git_path']}\n"
            report += f"✅ 路径存在: {'是' if diagnosis['path_exists'] else '否'}\n"
            report += f"🔧 是Git仓库: {'是' if diagnosis['is_git_repo'] else '否'}\n"
            report += f"🌿 当前分支: {diagnosis['current_branch']}\n"
            report += f"📊 分支状态: {diagnosis['branch_status']}\n"
            report += f"🌐 远程状态: {diagnosis['remote_status']}\n"
            report += f"📝 工作区状态: {diagnosis['working_tree_status']}\n\n"
            
            if diagnosis['issues']:
                report += "❌ 发现的问题:\n"
                for issue in diagnosis['issues']:
                    report += f"   • {issue}\n"
                report += "\n"
            
            if diagnosis['recommendations']:
                report += "💡 建议解决方案:\n"
                for rec in diagnosis['recommendations']:
                    report += f"   • {rec}\n"
                report += "\n"
            
            if not diagnosis['issues']:
                report += "✅ Git仓库状态正常！\n"
            
            # 显示诊断结果
            QMessageBox.information(self, "Git仓库诊断", report)
            
            # 记录到日志
            self.log_text.append("🔍 Git仓库诊断完成")
            
        except Exception as e:
            QMessageBox.critical(self, "诊断失败", f"诊断Git仓库时发生错误：\n{str(e)}")
        finally:
            self.progress_bar.setVisible(False)

    def add_dependency_files(self):
        """增加依赖文件功能"""
        if not self.upload_files:
            QMessageBox.warning(self, "警告", "请先选择要上传的文件！")
            return
        
        if not self.svn_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置SVN仓库路径！")
            return
        
        try:
            # 禁用按钮，防止重复点击
            self.add_dependencies_btn.setEnabled(False)
            self.add_dependencies_btn.setText("分析中...")
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 创建依赖分析器
            analyzer = ResourceDependencyAnalyzer()
            
            # 设置搜索目录（SVN仓库路径）
            search_directories = [self.svn_path_edit.text()]
            
            self.log_text.append("🔍 开始分析文件依赖...")
            self.log_text.append(f"📁 搜索目录: {self.svn_path_edit.text()}")
            self.log_text.append(f"📄 分析文件数: {len(self.upload_files)}")
            
            # 执行依赖分析
            result = analyzer.find_dependency_files(self.upload_files, search_directories)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 处理分析结果
            self._process_dependency_analysis_result(result)
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "分析失败", f"分析文件依赖时发生错误：\n{str(e)}")
            self.log_text.append(f"❌ 分析文件依赖失败：{str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 恢复按钮状态
            self.add_dependencies_btn.setEnabled(True)
            self.add_dependencies_btn.setText("增加依赖文件")
    
    def _process_dependency_analysis_result(self, result: Dict[str, Any]):
        """处理依赖分析结果"""
        try:
            stats = result['analysis_stats']
            
            # 显示分析统计
            self.log_text.append("📊 依赖分析完成:")
            self.log_text.append(f"   原始文件: {stats['total_original']}")
            self.log_text.append(f"   找到依赖文件: {stats['total_dependencies']}")
            self.log_text.append(f"   找到Meta文件: {stats['total_meta_files']}")
            self.log_text.append(f"   缺失依赖: {stats['total_missing']}")
            
            # 收集所有要添加的文件
            files_to_add = []
            
            # 标准化现有上传文件列表（用于重复检查）
            normalized_upload_files = set()
            for upload_file in self.upload_files:
                normalized_upload_files.add(os.path.normpath(os.path.abspath(upload_file)))
            
            # 添加依赖文件
            for dep_file in result['dependency_files']:
                normalized_dep_file = os.path.normpath(os.path.abspath(dep_file))
                if normalized_dep_file not in normalized_upload_files:
                    files_to_add.append(dep_file)
                    self.log_text.append(f"➕ 添加依赖文件: {os.path.basename(dep_file)}")
                else:
                    self.log_text.append(f"🔍 跳过重复的依赖文件: {os.path.basename(dep_file)}")
            
            # 添加meta文件
            for meta_file in result['meta_files']:
                normalized_meta_file = os.path.normpath(os.path.abspath(meta_file))
                if normalized_meta_file not in normalized_upload_files:
                    files_to_add.append(meta_file)
                    self.log_text.append(f"➕ 添加Meta文件: {os.path.basename(meta_file)}")
                else:
                    self.log_text.append(f"🔍 跳过重复的Meta文件: {os.path.basename(meta_file)}")
            
            # 统计原始文件本身的meta文件
            original_meta_count = 0
            original_meta_files = []
            for file_path in result['original_files']:
                if not file_path.endswith('.meta'):
                    meta_path = file_path + '.meta'
                    if meta_path in result['meta_files']:
                        original_meta_count += 1
                        original_meta_files.append(meta_path)
                        if meta_path not in self.upload_files:
                            self.log_text.append(f"📝 原始文件 {os.path.basename(file_path)} 的Meta文件将被添加")
            
            if original_meta_count > 0:
                self.log_text.append(f"📝 其中包含 {original_meta_count} 个原始文件对应的Meta文件")
                # 显示具体的原始文件meta文件
                for meta_file in original_meta_files:
                    self.log_text.append(f"   - {os.path.basename(meta_file)}")
            
            # 显示缺失的依赖
            if result['missing_dependencies']:
                self.log_text.append("⚠️ 缺失的依赖:")
                for missing in result['missing_dependencies'][:10]:  # 只显示前10个
                    self.log_text.append(f"   GUID: {missing['guid'][:8]}... 被文件: {os.path.basename(missing['referenced_by'])} 引用")
                if len(result['missing_dependencies']) > 10:
                    self.log_text.append(f"   ... 还有 {len(result['missing_dependencies']) - 10} 个缺失依赖")
            
            # 询问用户是否添加文件
            if files_to_add:
                reply = QMessageBox.question(
                    self,
                    "添加依赖文件",
                    f"分析完成！\n\n"
                    f"找到 {len(files_to_add)} 个新的依赖文件（包括meta文件）\n"
                    f"当前上传列表: {len(self.upload_files)} 个文件\n"
                    f"添加后总计: {len(self.upload_files) + len(files_to_add)} 个文件\n\n"
                    f"是否将这些依赖文件添加到上传列表？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    # 添加文件到上传列表
                    added_count = 0
                    for file_path in files_to_add:
                        if os.path.exists(file_path):
                            # 使用标准化路径进行重复检查
                            normalized_file_path = os.path.normpath(os.path.abspath(file_path))
                            existing_normalized = [os.path.normpath(os.path.abspath(f)) for f in self.upload_files]
                            
                            if normalized_file_path not in existing_normalized:
                                self.upload_files.append(file_path)
                                added_count += 1
                                
                                # 添加到UI列表
                                self.file_list.add_file_item(file_path)
                            else:
                                self.log_text.append(f"⚠️ 最终检查：跳过重复文件 {os.path.basename(file_path)}")
                    
                    self.log_text.append(f"✅ 成功添加 {added_count} 个依赖文件到上传列表")
                    self.log_text.append(f"📋 当前上传列表总计: {len(self.upload_files)} 个文件")
                    
                    # 更新状态栏
                    self.statusBar().showMessage(f"已添加 {added_count} 个依赖文件")
                else:
                    self.log_text.append("❌ 用户取消添加依赖文件")
            else:
                QMessageBox.information(
                    self,
                    "分析完成",
                    f"分析完成！\n\n"
                    f"没有找到新的依赖文件需要添加。\n"
                    f"当前上传列表已经包含了所有必要的依赖。"
                )
                self.log_text.append("✅ 没有找到新的依赖文件需要添加")
            
        except Exception as e:
            QMessageBox.critical(self, "处理失败", f"处理依赖分析结果时发生错误：\n{str(e)}")
            self.log_text.append(f"❌ 处理依赖分析结果失败：{str(e)}")
            import traceback
            traceback.print_exc()

    def on_files_dropped(self, file_paths: List[str]):
        """处理拖拽文件事件"""
        print(f"DEBUG: on_files_dropped called with {len(file_paths)} files")
        for i, path in enumerate(file_paths):
            print(f"DEBUG: File {i+1}: {path}")
        
        svn_repo_path = self.svn_path_edit.text().strip()
        if not svn_repo_path:
            QMessageBox.warning(self, "路径验证失败", 
                              "请先设置SVN仓库路径！\n\n"
                              "只有来自指定SVN仓库的文件才能上传。")
            self.log_text.append("❌ 拖拽失败：未设置SVN仓库路径")
            return
        
        if not os.path.exists(svn_repo_path):
            QMessageBox.warning(self, "路径验证失败", 
                              f"SVN仓库路径不存在：{svn_repo_path}\n\n"
                              "请检查SVN仓库路径设置。")
            self.log_text.append(f"❌ 拖拽失败：SVN仓库路径不存在")
            return
        
        # 分离文件和文件夹
        files = [path for path in file_paths if os.path.isfile(path)]
        folders = [path for path in file_paths if os.path.isdir(path)]
        
        print(f"DEBUG: 分离结果 - 文件: {len(files)}, 文件夹: {len(folders)}")
        
        total_added = 0
        
        # 处理文件（使用现有逻辑）
        if files:
            print(f"DEBUG: 处理文件: {files}")
            valid_files, invalid_files = self._validate_dropped_files(files, svn_repo_path)
            
            if invalid_files:
                self._show_invalid_files_warning(invalid_files, svn_repo_path, len(valid_files))
            
            if valid_files:
                added_count = self._add_valid_files(valid_files)
                total_added += added_count
                
                if added_count > 0:
                    self.log_text.append(f"✅ 通过拖拽添加了 {added_count} 个文件")
        
        # 处理文件夹（新逻辑）
        if folders:
            print(f"DEBUG: 处理文件夹: {folders}")
            
            # 验证文件夹是否在SVN仓库目录下
            valid_folders, invalid_folders = self._validate_dropped_files(folders, svn_repo_path)
            
            if invalid_folders:
                self._show_invalid_files_warning(invalid_folders, svn_repo_path, len(valid_folders))
            
            if valid_folders:
                folder_added_count = self._handle_folder_drops(valid_folders)
                total_added += folder_added_count
        
        # 显示总结信息
        if total_added > 0:
            success_msg = f"成功添加了 {total_added} 个有效文件到上传列表"
            self.log_text.append(f"✅ 拖拽操作完成，共添加 {total_added} 个文件")
            QMessageBox.information(self, "添加成功", success_msg)
        elif not files and not folders:
            self.log_text.append("❌ 没有有效文件或文件夹可添加")
        else:
            self.log_text.append("❌ 没有添加新文件（文件可能已存在或不在Assets目录下）")

    def _validate_dropped_files(self, file_paths: List[str], svn_repo_path: str) -> Tuple[List[str], List[str]]:
        """验证拖拽的文件或文件夹是否在SVN仓库目录下"""
        valid_files = []
        invalid_files = []
        
        normalized_svn_path = os.path.abspath(svn_repo_path).replace('\\', '/')
        
        for file_path in file_paths:
            normalized_file_path = os.path.abspath(file_path).replace('\\', '/')
            
            if normalized_file_path.startswith(normalized_svn_path):
                valid_files.append(file_path)
            else:
                invalid_files.append(file_path)
        
        return valid_files, invalid_files

    def _show_invalid_files_warning(self, invalid_files: List[str], svn_repo_path: str, valid_count: int):
        """显示无效文件警告"""
        invalid_count = len(invalid_files)
        
        error_msg = f"检测到 {invalid_count} 个文件或文件夹不在指定的SVN仓库目录中：\n\n"
        error_msg += f"SVN仓库路径：{svn_repo_path}\n\n"
        
        error_msg += "无效的路径：\n"
        for i, invalid_file in enumerate(invalid_files[:5], 1):
            error_msg += f"  {i}. {invalid_file}\n"
        if invalid_count > 5:
            error_msg += f"  ... 还有 {invalid_count - 5} 个\n"
        
        error_msg += "\n❌ 只有位于该SVN仓库目录下的文件或文件夹才能被添加！"
        
        if valid_count > 0:
            error_msg += f"\n\n✅ 其中 {valid_count} 个有效路径将被处理并添加到上传列表。"
        
        QMessageBox.warning(self, "文件路径验证失败", error_msg)
        self.log_text.append(f"❌ 路径验证失败：{invalid_count} 个文件或文件夹不在SVN仓库目录中")

    def _add_valid_files(self, valid_files: List[str]) -> int:
        """添加有效文件到上传列表"""
        added_count = 0
        svn_repo_path = self.svn_path_edit.text().strip()
        
        for file_path in valid_files:
            if os.path.isfile(file_path):
                if self._is_valid_assets_file(file_path, svn_repo_path):
                    if file_path not in self.upload_files:
                        self.upload_files.append(file_path)
                        self.file_list.add_file_item(file_path)
                        added_count += 1
                else:
                    self.log_text.append(f"⚠️ 跳过非Assets目录下的文件: {os.path.basename(file_path)}")
                    
            elif os.path.isdir(file_path):
                folder_added_count = 0
                for root, _, files in os.walk(file_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        if self._is_valid_assets_file(full_path, svn_repo_path):
                            if full_path not in self.upload_files:
                                self.upload_files.append(full_path)
                                self.file_list.add_file_item(full_path)
                                added_count += 1
                                folder_added_count += 1
                if folder_added_count > 0:
                    self.log_text.append(f"✅ 从文件夹 {os.path.basename(file_path)} 添加了 {folder_added_count} 个文件")
        return added_count
    
    def _is_valid_assets_file(self, file_path: str, svn_repo_path: str) -> bool:
        """检查文件是否在SVN仓库的Assets目录下"""
        try:
            normalized_file_path = os.path.abspath(file_path).replace('\\', '/')
            normalized_svn_path = os.path.abspath(svn_repo_path).replace('\\', '/')
            
            if not normalized_file_path.startswith(normalized_svn_path):
                return False
            
            if '/Assets/' not in normalized_file_path:
                return False
                
            return True
            
        except Exception as e:
            return False

    def _handle_folder_drops(self, folder_paths: List[str]) -> int:
        """处理文件夹拖拽的主方法"""
        total_added = 0
        
        for folder_path in folder_paths:
            folder_name = os.path.basename(folder_path)
            
            # 为每个文件夹显示模式选择对话框
            dialog = FolderUploadModeDialog([folder_name], self)
            
            if dialog.exec_() == QDialog.Accepted:
                selected_mode = dialog.get_selected_mode()
                
                print(f"DEBUG: 用户为文件夹 {folder_name} 选择了模式: {selected_mode}")
                
                if selected_mode == FolderUploadModeDialog.REPLACE_MODE:
                    added_count = self._handle_replace_mode(folder_path)
                    total_added += added_count
                elif selected_mode == FolderUploadModeDialog.MERGE_MODE:
                    added_count = self._handle_merge_mode(folder_path)
                    total_added += added_count
                
                self._log_folder_mode_selection(folder_path, selected_mode)
            else:
                # 用户取消了文件夹的上传
                self.log_text.append(f"❌ 用户取消了文件夹 {folder_name} 的上传")
        
        return total_added
    
    def _handle_replace_mode(self, folder_path: str) -> int:
        """处理替换模式：记录文件夹信息，在推送时执行删除"""
        folder_name = os.path.basename(folder_path)
        
        # 计算在Git仓库中的目标路径
        svn_repo_path = self.svn_path_edit.text().strip()
        git_path = self.git_path_edit.text().strip()
        
        # 计算相对于SVN仓库的路径
        relative_path = os.path.relpath(folder_path, svn_repo_path)
        
        # 应用路径映射
        mapped_path = self.git_manager.apply_path_mapping(relative_path)
        
        # 在Git仓库中的完整目标路径
        target_folder_path = os.path.join(git_path, mapped_path).replace('\\', '/')
        
        # 记录文件夹上传模式信息
        self.folder_upload_modes[folder_path] = {
            "mode": "replace",
            "target_path": target_folder_path,
            "folder_name": folder_name
        }
        
        print(f"DEBUG: 替换模式 - 源路径: {folder_path}")
        print(f"DEBUG: 替换模式 - 目标路径: {target_folder_path}")
        
        # 添加文件夹中的所有文件到上传列表
        added_count = self._add_folder_files_to_upload_list(folder_path)
        
        return added_count
    
    def _handle_merge_mode(self, folder_path: str) -> int:
        """处理合并模式：使用现有的添加文件逻辑"""
        # 合并模式就是现有的逻辑，直接添加文件夹中的所有文件
        added_count = self._add_folder_files_to_upload_list(folder_path)
        
        return added_count
    
    def _add_folder_files_to_upload_list(self, folder_path: str) -> int:
        """将文件夹中的所有有效文件添加到上传列表"""
        added_count = 0
        svn_repo_path = self.svn_path_edit.text().strip()
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                if self._is_valid_assets_file(full_path, svn_repo_path):
                    if full_path not in self.upload_files:
                        self.upload_files.append(full_path)
                        self.file_list.add_file_item(full_path)
                        added_count += 1
        
        return added_count
    
    def _log_folder_mode_selection(self, folder_path: str, mode: str):
        """记录文件夹模式选择的日志"""
        folder_name = os.path.basename(folder_path)
        
        if mode == FolderUploadModeDialog.REPLACE_MODE:
            self.log_text.append(f"🔄 文件夹 {folder_name} 选择了替换模式")
            self.log_text.append(f"   ⚠️ 将删除Git仓库中的同名文件夹")
        elif mode == FolderUploadModeDialog.MERGE_MODE:
            self.log_text.append(f"📁 文件夹 {folder_name} 选择了合并模式")
            self.log_text.append(f"   ✅ 将与Git仓库中的现有文件合并")

    def open_branch_selector(self):
        """打开分支选择对话框 - 使用已缓存的分支数据"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        # 直接从branch_combo获取已缓存的分支数据
        branches = []
        current_branch = ""
        
        # 从combo box中提取分支列表
        for i in range(self.branch_combo.count()):
            branch_text = self.branch_combo.itemText(i)
            if branch_text.startswith("★ "):
                # 当前分支
                branch_name = branch_text.replace("★ ", "").replace(" (当前)", "")
                branches.append(branch_name)
                current_branch = branch_name
            else:
                branches.append(branch_text)
        
        # 如果combo box为空，尝试从git管理器的缓存获取
        if not branches:
            branches = self.git_manager.get_git_branches(fetch_remote=False, use_cache=True)
            current_branch = self.git_manager.get_current_branch()
        
        # 如果还是没有分支数据，提示用户
        if not branches:
            QMessageBox.information(self, "提示", "暂无分支数据，请稍等片刻让程序完成初始化后再试。")
            return
        
        # 直接显示分支选择对话框，无需等待
        try:
            dialog = BranchSelectorDialog(branches, current_branch, self)
            
            if dialog.exec_() == QDialog.Accepted:
                selected_branch = dialog.get_selected_branch()
                if selected_branch:
                    # 在combo box中选择对应分支
                    index = self.branch_combo.findText(selected_branch)
                    if index >= 0:
                        self.branch_combo.setCurrentIndex(index)
                    else:
                        # 如果找不到分支，可能是新分支，添加到combo box
                        self.branch_combo.addItem(selected_branch)
                        self.branch_combo.setCurrentText(selected_branch)
                    
                    self.log_text.append(f"已选择分支: {selected_branch}")
                else:
                    self.log_text.append("未选择任何分支")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示分支选择对话框时出错: {str(e)}")
    
    def test_path_mapping(self):
        """测试路径映射功能"""
        test_path = self.test_path_edit.text().strip()
        if not test_path:
            QMessageBox.warning(self, "警告", "请输入要测试的路径")
            return
        
        try:
            # 显示测试开始
            self.log_text.append(f"\n🧪 开始测试路径映射...")
            self.log_text.append(f"   测试路径: {test_path}")
            
            # 执行路径映射测试
            result_path = self.git_manager.test_path_mapping(test_path)
            
            # 显示结果
            if result_path and result_path != test_path:
                self.log_text.append(f"   ✅ 映射成功!")
                self.log_text.append(f"   映射结果: {result_path}")
                
                # 弹出结果对话框
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("路径映射测试结果")
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setText("路径映射测试完成！")
                msg_box.setDetailedText(f"原始路径: {test_path}\n\n映射结果: {result_path}")
                msg_box.exec_()
                
            else:
                self.log_text.append(f"   ⚠️ 没有应用映射规则")
                QMessageBox.information(self, "测试结果", f"路径没有匹配任何映射规则\n\n原始路径: {test_path}")
            
        except Exception as e:
            error_msg = f"路径映射测试失败: {str(e)}"
            self.log_text.append(f"   ❌ {error_msg}")
            QMessageBox.critical(self, "错误", error_msg)
    
    def open_path_mapping_manager(self):
        """打开路径映射管理对话框"""
        try:
            dialog = PathMappingManagerDialog(self.git_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                self.log_text.append("✅ 路径映射配置已更新")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开路径映射管理器失败: {str(e)}")
    
    def toggle_path_mapping(self):
        """切换路径映射启用/禁用状态"""
        try:
            current_state = self.git_manager.path_mapping_enabled
            new_state = not current_state
            
            self.git_manager.set_path_mapping_enabled(new_state)
            
            status_text = "启用" if new_state else "禁用"
            self.log_text.append(f"🔧 路径映射已{status_text}")
            
            # 更新按钮文本
            self.toggle_mapping_btn.setText(f"{'禁用' if new_state else '启用'}映射")
            
            QMessageBox.information(self, "设置更新", f"路径映射已{status_text}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"切换路径映射状态失败: {str(e)}")
    
    def update_mapping_button_text(self):
        """更新路径映射按钮文本"""
        if hasattr(self, 'toggle_mapping_btn'):
            enabled = self.git_manager.path_mapping_enabled
            self.toggle_mapping_btn.setText(f"{'禁用' if enabled else '启用'}映射")
    
    def _toggle_advanced_features(self, checked):
        """控制高级功能的显示/隐藏"""
        if hasattr(self, 'advanced_group'):
            # 获取高级功能分组框内的所有控件
            layout = self.advanced_group.layout()
            if layout:
                # 遍历布局中的所有项目并设置可见性
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget:
                            widget.setVisible(checked)
                        elif hasattr(item, 'layout') and item.layout():
                            # 如果是嵌套布局，递归设置其中控件的可见性
                            self._set_layout_visible(item.layout(), checked)
            
            # 调整分组框的大小
            if checked:
                self.advanced_group.setMaximumHeight(16777215)  # 恢复默认最大高度
            else:
                self.advanced_group.setMaximumHeight(30)  # 只显示标题栏的高度
    
    def _set_layout_visible(self, layout, visible):
        """递归设置布局中所有控件的可见性"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setVisible(visible)
                elif hasattr(item, 'layout') and item.layout():
                    self._set_layout_visible(item.layout(), visible)
    
    def deploy_git_repositories(self):
        """一键部署git仓库"""
        # 选择部署目录
        deploy_dir = QFileDialog.getExistingDirectory(
            self, 
            "选择部署目录", 
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not deploy_dir:
            self.log_text.append("用户取消了部署操作")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认部署",
            f"即将在以下目录部署Git仓库：\n\n"
            f"目标目录: {deploy_dir}\n\n"
            f"部署步骤：\n"
            f"1. 克隆主仓库: assetruntimenew.git\n"
            f"2. 运行主仓库中的 Pull_CommonResource.bat 脚本\n\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了部署操作")
            return
        
        # 禁用部署按钮
        self.deploy_repos_btn.setEnabled(False)
        self.deploy_repos_btn.setText("部署中...")
        
        # 创建部署线程
        self.deploy_thread = DeployRepositoriesThread(deploy_dir)
        self.deploy_thread.progress_updated.connect(self.progress_bar.setValue)
        self.deploy_thread.status_updated.connect(self.on_deploy_status_updated)
        self.deploy_thread.deployment_completed.connect(self.on_deployment_completed)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 添加取消按钮功能（复用删除重拉的取消按钮逻辑）
        if hasattr(self, 'cancel_btn') and self.cancel_btn:
            self.cancel_btn.setVisible(True)
            self.cancel_btn.setText("取消部署")
            self.cancel_btn.clicked.disconnect()  # 断开之前的连接
            self.cancel_btn.clicked.connect(self.cancel_deployment)
        
        # 开始部署
        self.deploy_thread.start()
        self.log_text.append("🚀 开始执行一键部署git仓库操作...")
        self.log_text.append(f"📁 部署目录: {deploy_dir}")
        self.log_text.append(f"🌐 主仓库: {self.deploy_thread.main_repo_url}")
        self.log_text.append(f"📜 脚本路径: {deploy_dir}/assetruntimenew/Pull_CommonResource.bat")
    
    def cancel_deployment(self):
        """取消部署操作"""
        if hasattr(self, 'deploy_thread') and self.deploy_thread and self.deploy_thread.isRunning():
            self.log_text.append("⚠️ 正在取消部署操作...")
            self.deploy_thread.terminate()
            self.deploy_thread.wait(3000)  # 等待3秒
            
            # 恢复UI状态
            self.deploy_repos_btn.setEnabled(True)
            self.deploy_repos_btn.setText("一键部署git仓库")
            self.progress_bar.setVisible(False)
            
            if hasattr(self, 'cancel_btn') and self.cancel_btn:
                self.cancel_btn.setVisible(False)
            
            self.log_text.append("❌ 部署操作已取消")
    
    def on_deploy_status_updated(self, status: str):
        """部署状态更新"""
        self.log_text.append(status)
        # 滚动到底部
        self.log_text.moveCursor(self.log_text.textCursor().End)
    
    def on_deployment_completed(self, success: bool, message: str, main_repo_path: str, sub_repo_path: str):
        """部署完成"""
        # 恢复按钮状态
        self.deploy_repos_btn.setEnabled(True)
        self.deploy_repos_btn.setText("一键部署git仓库")
        
        # 隐藏进度条和取消按钮
        self.progress_bar.setVisible(False)
        if hasattr(self, 'cancel_btn') and self.cancel_btn:
            self.cancel_btn.setVisible(False)
        
        if success:
            self.log_text.append("🎉 一键部署git仓库操作完成！")
            self.result_text.append(f"✅ 部署成功！")
            self.result_text.append(f"主仓库路径: {main_repo_path}")
            self.result_text.append(f"CommonResource已通过脚本拉取完成")
            
            # 显示成功对话框
            QMessageBox.information(
                self, 
                "部署成功", 
                f"一键部署git仓库操作已完成！\n\n"
                f"主仓库路径: {main_repo_path}\n"
                f"CommonResource: 已通过 Pull_CommonResource.bat 脚本拉取\n\n"
                f"{message}"
            )
        else:
            self.log_text.append(f"❌ 部署失败: {message}")
            QMessageBox.critical(self, "部署失败", f"一键部署git仓库失败：\n\n{message}")
    
    def quick_fix_crlf(self):
        """快速修复CRLF问题"""
        try:
            git_path = self.git_path_edit.text().strip()
            if not git_path:
                QMessageBox.warning(self, "警告", "请先设置Git仓库路径")
                return
            
            if not os.path.exists(git_path):
                QMessageBox.warning(self, "警告", "Git仓库路径不存在")
                return
            
            # 显示确认对话框
            reply = QMessageBox.question(self, "确认修复", 
                                       "🔧 即将执行快速CRLF修复：\n\n"
                                       "• 设置 core.safecrlf=false\n"
                                       "• 设置 core.autocrlf=false\n"
                                       "• 重置Git缓存\n\n"
                                       "⚠️ 注意：这将修改当前仓库的Git配置\n"
                                       "确定要继续吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply != QMessageBox.Yes:
                return
            
            # 调用Git管理器的CRLF修复器
            if not self.git_manager.crlf_fixer:
                QMessageBox.warning(self, "错误", "CRLF修复器未初始化")
                return
            
            result = self.git_manager.crlf_fixer.quick_fix()
            
            if result['success']:
                QMessageBox.information(self, "成功", 
                                      f"✅ 快速修复成功！\n\n{result['message']}")
            else:
                QMessageBox.warning(self, "失败", 
                                  f"❌ 快速修复失败：\n{result['message']}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"快速修复异常：{str(e)}")
    
    def smart_fix_crlf(self):
        """智能修复CRLF问题"""
        try:
            git_path = self.git_path_edit.text().strip()
            if not git_path:
                QMessageBox.warning(self, "警告", "请先设置Git仓库路径")
                return
            
            if not os.path.exists(git_path):
                QMessageBox.warning(self, "警告", "Git仓库路径不存在")
                return
            
            # 显示确认对话框
            reply = QMessageBox.question(self, "确认修复", 
                                       "🧠 即将执行智能CRLF修复：\n\n"
                                       "• 检测常见CRLF问题\n"
                                       "• 智能创建.gitattributes文件\n"
                                       "• 处理Unity二进制文件\n"
                                       "• 预防性修复潜在问题\n\n"
                                       "✅ 这是推荐的修复方式，对团队协作友好\n"
                                       "确定要继续吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply != QMessageBox.Yes:
                return
            
            # 调用Git管理器的CRLF修复器
            if not self.git_manager.crlf_fixer:
                QMessageBox.warning(self, "错误", "CRLF修复器未初始化")
                return
            
            result = self.git_manager.crlf_fixer.preventive_fix()
            
            if result['success']:
                QMessageBox.information(self, "成功", 
                                      f"✅ 智能修复成功！\n\n{result['message']}")
            else:
                QMessageBox.warning(self, "失败", 
                                  f"❌ 智能修复失败：\n{result['message']}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"智能修复异常：{str(e)}")
    
    def check_for_updates(self):
        """检查更新"""
        if not self.hot_updater:
            QMessageBox.information(self, "提示", "热更新功能不可用")
            return
        
        # 在单独线程中检查更新，避免阻塞UI
        self.update_thread = UpdateCheckThread(self.hot_updater)
        self.update_thread.update_found.connect(self.on_update_found)
        self.update_thread.no_update.connect(self.on_no_update)
        self.update_thread.check_failed.connect(self.on_update_check_failed)
        self.update_thread.start()
        
        # 显示检查中的状态
        self.statusBar().showMessage("正在检查更新...")
    
    def on_update_found(self, update_info):
        """发现更新时的处理"""
        self.statusBar().showMessage("发现新版本!")
        
        # 显示更新对话框
        dialog = UpdateDialog(update_info, self)
        if dialog.exec_() == QDialog.Accepted:
            self.start_update(update_info)
    
    def on_no_update(self):
        """没有更新时的处理"""
        self.statusBar().showMessage("当前已是最新版本")
        QMessageBox.information(self, "检查更新", "当前已是最新版本！")
    
    def on_update_check_failed(self, error_msg):
        """更新检查失败时的处理"""
        self.statusBar().showMessage("更新检查失败")
        QMessageBox.warning(self, "更新检查失败", f"无法检查更新：\n{error_msg}")
    
    def start_update(self, update_info):
        """开始更新"""
        # 在单独线程中执行更新
        self.update_thread = UpdateExecuteThread(self.hot_updater, update_info)
        self.update_thread.update_progress.connect(self.on_update_progress)
        self.update_thread.update_completed.connect(self.on_update_completed)
        self.update_thread.update_failed.connect(self.on_update_failed)
        self.update_thread.start()
        
        # 显示更新进度对话框
        self.progress_dialog = QProgressDialog("正在下载更新...", "取消", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
    
    def on_update_progress(self, progress, message):
        """更新进度"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(progress)
            self.progress_dialog.setLabelText(message)
    
    def on_update_completed(self):
        """更新完成"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        self.statusBar().showMessage("更新完成")
        
        # 显示更新完成信息，然后关闭应用
        QMessageBox.information(self, "更新完成", 
                              "更新已完成！\n\n"
                              "应用程序将关闭，请手动启动新版本。\n"
                              "新版本位置：当前目录下的版本化exe文件\n"
                              "（如：美术资源上传工具_v1.0.7.exe）")
        
        # 直接退出应用程序
        QApplication.quit()
    
    def on_update_failed(self, error_msg):
        """更新失败"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        self.statusBar().showMessage("更新失败")
        QMessageBox.critical(self, "更新失败", f"更新过程中发生错误：\n{error_msg}")
    
    def restart_application(self):
        """重启应用程序"""
        try:
            # 保存当前配置
            self.save_settings()
            
            # 重启应用
            if getattr(sys, 'frozen', False):
                # 打包后的exe
                subprocess.Popen([sys.executable])
            else:
                # 开发环境
                subprocess.Popen([sys.executable, __file__])
            
            # 退出当前应用
            QApplication.quit()
            
        except Exception as e:
            QMessageBox.critical(self, "重启失败", f"无法重启应用程序：\n{e}")
    
    def show_about_dialog(self):
        """显示关于对话框"""
        version = self._read_current_version()  # 直接从文件读取，确保准确性
        if self.hot_updater:
            version = self.hot_updater.get_current_version()
        
        about_text = f"""
        <h3>美术资源管理工具</h3>
        <p><b>版本:</b> {version}</p>
        <p><b>功能:</b> 专业的MiniGame资源上传和管理工具</p>
        <p><b>特性:</b></p>
        <ul>
           
            <li>🌐 Avatar/MiniUniverse子目录支持</li>
            <li>🎨 材质模板验证</li>
            <li>🔄 热更新功能</li>
            <li>📊 完整的资源检查报告</li>
        </ul>
        <p><b>作者:</b> TA团队</p>
        <p><b>更新时间:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
        """
        
        QMessageBox.about(self, "关于", about_text)


class DeployRepositoriesThread(QThread):
    """部署仓库线程"""
    
    progress_updated = pyqtSignal(int)  # 进度更新
    status_updated = pyqtSignal(str)    # 状态更新
    deployment_completed = pyqtSignal(bool, str, str, str)  # 部署完成 (success, message, main_repo_path, sub_repo_path)
    
    def __init__(self, deploy_dir):
        super().__init__()
        self.deploy_dir = deploy_dir
        self.main_repo_url = "http://client_gitlab.miniworldplus.com:83/miniwan/assetruntimenew.git"
        self.sub_repo_url = "http://client_gitlab.miniworldplus.com:83/miniwan/commonresource.git"
        self.main_repo_path = ""
        self.sub_repo_path = ""
    
    def run(self):
        """执行部署操作"""
        try:
            # 步骤1：部署主仓库 (60%)
            self.status_updated.emit("📦 开始部署主仓库 assetruntimenew.git...")
            self.progress_updated.emit(10)
            
            self.main_repo_path = os.path.join(self.deploy_dir, "assetruntimenew")
            success, message = self._clone_repository(self.main_repo_url, self.main_repo_path, "主仓库")
            if not success:
                self.deployment_completed.emit(False, message, "", "")
                return
            
            self.progress_updated.emit(60)
            self.status_updated.emit("✅ 主仓库部署完成")
            
            # 步骤2：运行Pull_CommonResource.bat (40%)
            self.status_updated.emit("🔄 正在运行 Pull_CommonResource.bat...")
            self.progress_updated.emit(70)
            
            success, message = self._run_pull_script()
            if not success:
                self.deployment_completed.emit(False, message, self.main_repo_path, "")
                return
            
            self.progress_updated.emit(100)
            self.status_updated.emit("✅ Pull_CommonResource.bat 执行完成")
            
            # 完成
            self.status_updated.emit("🎉 Git仓库部署完成！")
            self.deployment_completed.emit(
                True, 
                "Git仓库部署完成，CommonResource已通过脚本拉取！", 
                self.main_repo_path, 
                ""
            )
            
        except Exception as e:
            self.deployment_completed.emit(False, f"部署过程中发生错误: {str(e)}", "", "")
    
    def _clone_repository(self, repo_url: str, target_path: str, repo_name: str) -> tuple:
        """克隆仓库"""
        try:
            # 检查目标目录是否已存在
            if os.path.exists(target_path):
                self.status_updated.emit(f"⚠️ {repo_name}目录已存在，正在删除...")
                import shutil
                shutil.rmtree(target_path)
            
            # 执行git clone
            self.status_updated.emit(f"⬇️ 正在克隆{repo_name}...")
            
            import subprocess
            # 设置Git配置以提高克隆性能和稳定性
            git_env = os.environ.copy()
            git_env['GIT_HTTP_LOW_SPEED_LIMIT'] = '1000'  # 最低速度1KB/s
            git_env['GIT_HTTP_LOW_SPEED_TIME'] = '30'     # 30秒超时
            
            process = subprocess.Popen(
                ['git', 'clone', '--progress', repo_url, target_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=self.deploy_dir,
                env=git_env,
                creationflags=SUBPROCESS_FLAGS
            )
            
            # 实时读取输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line:
                        # 解析git clone的进度信息
                        if "Receiving objects:" in line or "Resolving deltas:" in line:
                            self.status_updated.emit(f"📥 {repo_name}: {line}")
                        elif "Cloning into" in line:
                            self.status_updated.emit(f"🔄 {repo_name}: {line}")
                        elif line and not line.startswith("warning:"):
                            self.status_updated.emit(f"ℹ️ {repo_name}: {line}")
            
            # 检查返回码
            return_code = process.poll()
            if return_code != 0:
                return False, f"{repo_name}克隆失败，返回码: {return_code}"
            
            # 验证克隆结果
            if not os.path.exists(target_path):
                return False, f"{repo_name}克隆失败，目标目录不存在"
            
            git_dir = os.path.join(target_path, '.git')
            if not os.path.exists(git_dir):
                return False, f"{repo_name}克隆失败，.git目录不存在"
            
            return True, f"{repo_name}克隆成功"
            
        except FileNotFoundError:
            return False, f"Git命令未找到，请确保已安装Git并添加到系统PATH"
        except Exception as e:
            return False, f"{repo_name}克隆失败: {str(e)}"
    
    def _run_pull_script(self) -> tuple:
        """运行Pull_CommonResource.bat脚本"""
        try:
            script_path = os.path.join(self.main_repo_path, "Pull_CommonResource.bat")
            
            # 检查脚本是否存在
            if not os.path.exists(script_path):
                return False, f"Pull_CommonResource.bat 脚本不存在: {script_path}"
            
            self.status_updated.emit(f"📜 找到脚本: {script_path}")
            self.status_updated.emit("⚡ 开始执行 Pull_CommonResource.bat...")
            
            import subprocess
            import time
            
            # 在主仓库目录下运行脚本
            process = subprocess.Popen(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=self.main_repo_path,
                shell=True,
                creationflags=SUBPROCESS_FLAGS
            )
            
            # 设置超时和无输出检测
            last_output_time = time.time()
            timeout_seconds = 300  # 5分钟超时
            no_output_timeout = 60  # 60秒无输出超时
            script_progress = 70  # 脚本开始时的进度
            
            # 实时读取输出
            while True:
                output = process.stdout.readline()
                current_time = time.time()
                
                # 检查进程是否结束
                if output == '' and process.poll() is not None:
                    self.status_updated.emit("🔍 脚本进程已结束，正在验证结果...")
                    break
                
                # 检查总超时
                if current_time - last_output_time > timeout_seconds:
                    self.status_updated.emit("⏰ 脚本执行超时，正在终止进程...")
                    process.terminate()
                    process.wait(timeout=10)
                    return False, "Pull_CommonResource.bat 执行超时"
                
                if output:
                    line = output.strip()
                    if line:
                        last_output_time = current_time  # 更新最后输出时间
                        
                        # 显示脚本输出并更新进度
                        if "Cloning into" in line or "Already up to date" in line:
                            self.status_updated.emit(f"📥 脚本输出: {line}")
                            script_progress = min(85, script_progress + 5)  # 增加进度
                            self.progress_updated.emit(script_progress)
                        elif "error:" in line.lower() or "fatal:" in line.lower():
                            self.status_updated.emit(f"❌ 脚本错误: {line}")
                        elif "remove" in line.lower() or "rm " in line:
                            script_progress = min(75, script_progress + 2)  # 清理阶段
                            self.progress_updated.emit(script_progress)
                            self.status_updated.emit(f"ℹ️ 脚本输出: {line}")
                        elif "set and pull" in line.lower() or "submodule" in line.lower():
                            script_progress = min(80, script_progress + 3)  # 子模块阶段
                            self.progress_updated.emit(script_progress)
                            self.status_updated.emit(f"ℹ️ 脚本输出: {line}")
                        elif line and not line.startswith("warning:"):
                            self.status_updated.emit(f"ℹ️ 脚本输出: {line}")
                
                # 检查无输出超时（仅在有输出后才开始计算）
                elif current_time - last_output_time > no_output_timeout:
                    # 检查进程是否还在运行
                    if process.poll() is None:
                        self.status_updated.emit("⏳ 脚本长时间无输出，可能正在后台处理...")
                        self.status_updated.emit("🔍 正在检查CommonResource目录...")
                        
                        # 检查CommonResource目录是否存在且有内容
                        common_resource_path = os.path.join(self.main_repo_path, "CommonResource")
                        if os.path.exists(common_resource_path):
                            # 检查目录是否有.git目录（表示是git仓库）
                            git_dir = os.path.join(common_resource_path, ".git")
                            if os.path.exists(git_dir):
                                self.status_updated.emit("✅ 检测到CommonResource已成功拉取")
                                self.progress_updated.emit(95)  # 更新进度到95%
                                # 强制结束进程
                                process.terminate()
                                process.wait(timeout=5)
                                break
                        
                        # 重置超时计时器，继续等待
                        last_output_time = current_time
            
            # 验证拉取结果
            common_resource_path = os.path.join(self.main_repo_path, "CommonResource")
            if os.path.exists(common_resource_path):
                git_dir = os.path.join(common_resource_path, ".git")
                if os.path.exists(git_dir):
                    self.status_updated.emit("✅ Pull_CommonResource.bat 执行成功")
                    self.status_updated.emit(f"📁 CommonResource目录已创建: {common_resource_path}")
                    return True, "Pull_CommonResource.bat 执行成功，CommonResource已拉取"
                else:
                    return False, "CommonResource目录存在但不是Git仓库"
            else:
                # 检查返回码
                return_code = process.poll()
                if return_code is not None and return_code != 0:
                    return False, f"Pull_CommonResource.bat 执行失败，返回码: {return_code}"
                else:
                    return False, "Pull_CommonResource.bat 执行完成但CommonResource目录未创建"
            
        except Exception as e:
            return False, f"运行 Pull_CommonResource.bat 失败: {str(e)}"


class DeleteAndRecloneThread(QThread):
    """删除重拉线程"""
    
    progress_updated = pyqtSignal(int)  # 进度更新
    status_updated = pyqtSignal(str)    # 状态更新
    operation_completed = pyqtSignal(bool, str)  # 操作完成 (success, message)
    
    def __init__(self, git_path, remote_url, current_branch, parent_dir, repo_name):
        super().__init__()
        self.git_path = git_path
        self.remote_url = remote_url
        self.current_branch = current_branch
        self.parent_dir = parent_dir
        self.repo_name = repo_name
    
    def run(self):
        """执行删除重拉操作"""
        try:
            # 步骤1：删除本地仓库 (20%)
            self.status_updated.emit("🗑️ 正在删除本地仓库目录...")
            self.progress_updated.emit(10)
            
            if os.path.exists(self.git_path):
                # 先尝试关闭可能占用文件的Git进程
                self._close_git_processes()
                # 强制删除目录
                self._force_remove_directory(self.git_path)
                self.status_updated.emit("✅ 本地仓库目录已删除")
            
            self.progress_updated.emit(20)
            
            # 步骤2：重新克隆 (20% -> 80%)
            self.status_updated.emit("📥 正在重新克隆远程仓库...")
            self.progress_updated.emit(30)
            
            # 使用git clone并监控进度
            clone_process = subprocess.Popen(
                ['git', 'clone', '--progress', self.remote_url, self.repo_name],
                cwd=self.parent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=SUBPROCESS_FLAGS
            )
            
            # 监控克隆进度
            progress = 30
            while True:
                output = clone_process.stdout.readline()
                if output == '' and clone_process.poll() is not None:
                    break
                
                if output:
                    # 尝试解析git的进度信息
                    if 'Receiving objects:' in output or 'Resolving deltas:' in output:
                        # 提取百分比
                        import re
                        percent_match = re.search(r'(\d+)%', output)
                        if percent_match:
                            git_percent = int(percent_match.group(1))
                            # 映射到我们的进度范围 (30-80)
                            progress = 30 + int(git_percent * 0.5)
                            self.progress_updated.emit(min(progress, 80))
                    
                    self.status_updated.emit(f"📥 克隆中: {output.strip()}")
            
            # 检查克隆结果
            if clone_process.returncode != 0:
                self.operation_completed.emit(False, "仓库克隆失败")
                return
            
            self.progress_updated.emit(80)
            self.status_updated.emit("✅ 仓库克隆成功")
            
            # 步骤3：切换分支 (80% -> 90%)
            if self.current_branch and self.current_branch not in ["main", "master"]:
                self.status_updated.emit(f"🌿 正在切换到分支: {self.current_branch}")
                self.progress_updated.emit(85)
                
                try:
                    checkout_result = subprocess.run(
                        ['git', 'checkout', self.current_branch],
                        cwd=self.git_path,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        timeout=30
                    , creationflags=SUBPROCESS_FLAGS)
                    
                    if checkout_result.returncode == 0:
                        self.status_updated.emit(f"✅ 已切换到分支: {self.current_branch}")
                    else:
                        self.status_updated.emit(f"⚠️ 无法切换到分支 {self.current_branch}，保持默认分支")
                        
                except Exception as e:
                    self.status_updated.emit(f"⚠️ 切换分支时出错: {str(e)}")
            
            self.progress_updated.emit(90)
            
            # 完成
            self.progress_updated.emit(100)
            self.status_updated.emit("🎉 一键删除重拉操作完成！")
            self.operation_completed.emit(True, "操作成功完成")
            
        except Exception as e:
            self.operation_completed.emit(False, f"操作失败: {str(e)}")
    
    def _force_remove_directory(self, path):
        """强制删除目录，处理只读文件和权限问题"""
        import shutil
        import stat
        
        def handle_remove_readonly(func, path, exc):
            """处理只读文件删除错误的回调函数"""
            try:
                # 如果是权限错误，尝试修改文件权限
                if exc[1].errno == 13 or exc[1].errno == 5:  # Permission denied
                    # 移除只读属性
                    os.chmod(path, stat.S_IWRITE)
                    # 重试删除
                    func(path)
                else:
                    # 其他错误，尝试强制删除
                    if os.path.isfile(path):
                        os.chmod(path, stat.S_IWRITE)
                        os.unlink(path)
                    elif os.path.isdir(path):
                        os.chmod(path, stat.S_IWRITE)
                        os.rmdir(path)
            except Exception as e:
                self.status_updated.emit(f"⚠️ 删除文件时遇到问题: {path} - {str(e)}")
        
        try:
            # 首先尝试普通删除
            shutil.rmtree(path)
        except Exception:
            try:
                # 如果普通删除失败，使用错误处理回调函数
                self.status_updated.emit("🔧 遇到只读文件，正在强制删除...")
                shutil.rmtree(path, onerror=handle_remove_readonly)
            except Exception:
                # 如果还是失败，尝试使用系统命令
                try:
                    import platform
                    if platform.system() == "Windows":
                        self.status_updated.emit("💪 使用系统命令强制删除...")
                        import subprocess
                        # 使用rmdir /s /q命令强制删除
                        result = subprocess.run(
                            ['rmdir', '/s', '/q', path],
                            shell=True,
                            capture_output=True,
                            text=True
                        , creationflags=SUBPROCESS_FLAGS)
                        if result.returncode != 0:
                            raise Exception(f"系统命令删除失败: {result.stderr}")
                    else:
                        # Linux/Mac使用rm -rf
                        result = subprocess.run(
                            ['rm', '-rf', path],
                            capture_output=True,
                            text=True
                        , creationflags=SUBPROCESS_FLAGS)
                        if result.returncode != 0:
                            raise Exception(f"系统命令删除失败: {result.stderr}")
                except Exception as e:
                    raise Exception(f"无法删除目录 {path}: {str(e)}")
    
    def _close_git_processes(self):
        """尝试关闭可能占用Git仓库文件的进程"""
        try:
            import platform
            if platform.system() == "Windows":
                # 在Windows上，尝试关闭可能的Git进程
                import subprocess
                try:
                    # 查找并关闭git.exe进程
                    subprocess.run(['taskkill', '/f', '/im', 'git.exe'], 
                                 capture_output=True, timeout=5, creationflags=SUBPROCESS_FLAGS)
                    # 查找并关闭可能的编辑器进程
                    subprocess.run(['taskkill', '/f', '/im', 'notepad.exe'], 
                                 capture_output=True, timeout=5, creationflags=SUBPROCESS_FLAGS)
                    subprocess.run(['taskkill', '/f', '/im', 'code.exe'], 
                                 capture_output=True, timeout=5, creationflags=SUBPROCESS_FLAGS)
                    self.status_updated.emit("🔧 已尝试关闭相关进程")
                except:
                    pass  # 忽略错误，这只是尝试性操作
        except:
            pass  # 忽略所有错误


class BranchLoadThread(QThread):
    """分支加载线程 - 异步加载分支列表"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    branches_loaded = pyqtSignal(list, str)  # branches, current_branch
    load_failed = pyqtSignal(str)  # error_message
    
    def __init__(self, git_manager, fast_mode: bool = False, ultra_fast: bool = False):
        super().__init__()
        self.git_manager = git_manager
        self.fast_mode = fast_mode  # 快速模式：不执行git fetch
        self.ultra_fast = ultra_fast  # 超快速模式：只获取当前分支
    
    def run(self):
        """异步加载分支列表"""
        try:
            if self.ultra_fast:
                # 超快速模式：只获取当前分支，不获取分支列表
                print("⚡ [DEBUG] 超快速模式：仅获取当前分支...")
                current_branch = self.git_manager.get_current_branch()
                if current_branch:
                    # 只返回当前分支
                    self.branches_loaded.emit([current_branch], current_branch)
                    print(f"   ✅ 当前分支: {current_branch}")
                else:
                    self.branches_loaded.emit([], "")
                    print("   ⚠️ 无法获取当前分支")
                return
            
            # 普通快速模式或完整模式
            if self.fast_mode:
                self.status_updated.emit("正在快速加载分支列表...")
            else:
                self.status_updated.emit("正在获取分支列表...")
            self.progress_updated.emit(20)
            
            # 获取分支列表（快速模式不fetch远程）
            branches = self.git_manager.get_git_branches(fetch_remote=not self.fast_mode)
            self.progress_updated.emit(70)
            
            # 获取当前分支
            current_branch = self.git_manager.get_current_branch()
            self.progress_updated.emit(100)
            
            if branches:
                self.status_updated.emit(f"获取到 {len(branches)} 个分支")
                self.branches_loaded.emit(branches, current_branch)
            else:
                self.load_failed.emit("未获取到任何分支")
                
        except Exception as e:
            error_msg = f"加载分支列表失败: {str(e)}"
            self.load_failed.emit(error_msg)


class PathMappingManagerDialog(QDialog):
    """路径映射管理对话框"""
    
    def __init__(self, git_manager, parent=None):
        super().__init__(parent)
        self.git_manager = git_manager
        self.setWindowTitle("路径映射规则管理")
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        self.init_ui()
        self.load_rules()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 顶部控制区域
        control_layout = QHBoxLayout()
        
        # 启用/禁用路径映射
        self.enable_checkbox = QCheckBox("启用路径映射")
        self.enable_checkbox.setChecked(self.git_manager.path_mapping_enabled)
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        control_layout.addWidget(self.enable_checkbox)
        
        control_layout.addStretch()
        
        # 按钮
        self.add_rule_btn = QPushButton("添加规则")
        self.add_rule_btn.clicked.connect(self.add_rule)
        control_layout.addWidget(self.add_rule_btn)
        
        self.edit_rule_btn = QPushButton("编辑规则")
        self.edit_rule_btn.clicked.connect(self.edit_rule)
        control_layout.addWidget(self.edit_rule_btn)
        
        self.delete_rule_btn = QPushButton("删除规则")
        self.delete_rule_btn.clicked.connect(self.delete_rule)
        control_layout.addWidget(self.delete_rule_btn)
        
        self.test_rule_btn = QPushButton("测试规则")
        self.test_rule_btn.clicked.connect(self.test_rule)
        control_layout.addWidget(self.test_rule_btn)
        
        layout.addLayout(control_layout)
        
        # 规则列表
        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(6)
        self.rule_table.setHorizontalHeaderLabels([
            "启用", "规则名称", "描述", "源路径模式", "目标路径模式", "优先级"
        ])
        
        # 设置列宽
        header = self.rule_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 启用列
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 规则名称
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 描述
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 源路径模式
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # 目标路径模式
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 优先级
        
        self.rule_table.setColumnWidth(0, 60)
        self.rule_table.setColumnWidth(5, 80)
        
        self.rule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rule_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.rule_table)
        
        # 测试区域
        test_group = QGroupBox("规则测试")
        test_layout = QHBoxLayout()
        test_group.setLayout(test_layout)
        
        test_layout.addWidget(QLabel("测试路径:"))
        self.test_path_edit = QLineEdit()
        self.test_path_edit.setPlaceholderText("输入Assets路径，如: Assets\\entity\\100060\\prefab.prefab")
        test_layout.addWidget(self.test_path_edit)
        
        self.run_test_btn = QPushButton("运行测试")
        self.run_test_btn.clicked.connect(self.run_test)
        test_layout.addWidget(self.run_test_btn)
        
        layout.addWidget(test_group)
        
        # 测试结果
        self.test_result = QTextEdit()
        self.test_result.setMaximumHeight(120)
        self.test_result.setReadOnly(True)
        layout.addWidget(self.test_result)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_rules)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_rules(self):
        """加载路径映射规则到表格"""
        rules = self.git_manager.get_path_mapping_rules()
        
        self.rule_table.setRowCount(len(rules))
        
        for row, (rule_id, rule_data) in enumerate(rules.items()):
            # 启用复选框
            checkbox = QCheckBox()
            checkbox.setChecked(rule_data.get('enabled', True))
            checkbox.stateChanged.connect(lambda state, rid=rule_id: self.on_rule_enabled_changed(rid, state))
            self.rule_table.setCellWidget(row, 0, checkbox)
            
            # 规则名称
            name_item = QTableWidgetItem(rule_data.get('name', rule_id))
            name_item.setData(Qt.UserRole, rule_id)
            self.rule_table.setItem(row, 1, name_item)
            
            # 描述
            desc_item = QTableWidgetItem(rule_data.get('description', ''))
            self.rule_table.setItem(row, 2, desc_item)
            
            # 源路径模式
            source_item = QTableWidgetItem(rule_data.get('source_pattern', ''))
            self.rule_table.setItem(row, 3, source_item)
            
            # 目标路径模式
            target_item = QTableWidgetItem(rule_data.get('target_pattern', ''))
            self.rule_table.setItem(row, 4, target_item)
            
            # 优先级
            priority_item = QTableWidgetItem(str(rule_data.get('priority', 999)))
            self.rule_table.setItem(row, 5, priority_item)
    
    def on_enable_changed(self, state):
        """路径映射总开关变化"""
        enabled = state == Qt.Checked
        self.git_manager.set_path_mapping_enabled(enabled)
    
    def on_rule_enabled_changed(self, rule_id, state):
        """单个规则启用状态变化"""
        enabled = state == Qt.Checked
        rules = self.git_manager.get_path_mapping_rules()
        if rule_id in rules:
            rules[rule_id]['enabled'] = enabled
            self.git_manager.update_path_mapping_rule(rule_id, rules[rule_id])
    
    def add_rule(self):
        """添加新规则"""
        dialog = PathMappingRuleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            rule_data = dialog.get_rule_data()
            rule_id = rule_data.get('rule_id', f"rule_{len(self.git_manager.get_path_mapping_rules()) + 1}")
            
            self.git_manager.add_path_mapping_rule(rule_id, rule_data)
            self.load_rules()
    
    def edit_rule(self):
        """编辑选中的规则"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要编辑的规则")
            return
        
        rule_id = self.rule_table.item(current_row, 1).data(Qt.UserRole)
        rules = self.git_manager.get_path_mapping_rules()
        
        if rule_id not in rules:
            QMessageBox.warning(self, "错误", "规则不存在")
            return
        
        dialog = PathMappingRuleDialog(self, rules[rule_id], rule_id)
        if dialog.exec_() == QDialog.Accepted:
            rule_data = dialog.get_rule_data()
            self.git_manager.update_path_mapping_rule(rule_id, rule_data)
            self.load_rules()
    
    def delete_rule(self):
        """删除选中的规则"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要删除的规则")
            return
        
        rule_id = self.rule_table.item(current_row, 1).data(Qt.UserRole)
        rule_name = self.rule_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除规则 '{rule_name}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.git_manager.remove_path_mapping_rule(rule_id)
            self.load_rules()
    
    def test_rule(self):
        """测试选中的规则"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要测试的规则")
            return
        
        test_path = QInputDialog.getText(self, "测试规则", "输入测试路径:")[0]
        if not test_path:
            return
        
        rule_id = self.rule_table.item(current_row, 1).data(Qt.UserRole)
        rules = self.git_manager.get_path_mapping_rules()
        
        if rule_id not in rules:
            return
        
        rule = rules[rule_id]
        
        try:
            import re
            if re.match(rule['source_pattern'], test_path):
                result = re.sub(rule['source_pattern'], rule['target_pattern'], test_path)
                self.test_result.setText(f"✅ 规则匹配成功\n原始路径: {test_path}\n映射结果: {result}")
            else:
                self.test_result.setText(f"❌ 规则不匹配\n测试路径: {test_path}\n匹配模式: {rule['source_pattern']}")
        except Exception as e:
            self.test_result.setText(f"❌ 测试失败: {str(e)}")
    
    def run_test(self):
        """运行完整的路径映射测试"""
        test_path = self.test_path_edit.text().strip()
        if not test_path:
            QMessageBox.warning(self, "警告", "请输入测试路径")
            return
        
        result = self.git_manager.apply_path_mapping(test_path)
        
        if result != test_path:
            self.test_result.setText(f"✅ 路径映射成功\n原始路径: {test_path}\n映射结果: {result}")
        else:
            self.test_result.setText(f"⚠️ 没有匹配的规则\n测试路径: {test_path}")
    
    def save_rules(self):
        """保存规则并关闭对话框"""
        self.accept()


class PathMappingRuleDialog(QDialog):
    """路径映射规则编辑对话框"""
    
    def __init__(self, parent=None, rule_data=None, rule_id=None):
        super().__init__(parent)
        self.rule_data = rule_data or {}
        self.rule_id = rule_id
        
        self.setWindowTitle("编辑路径映射规则" if rule_data else "添加路径映射规则")
        self.setMinimumSize(600, 400)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 表单区域
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        form_layout.addRow("规则名称:", self.name_edit)
        
        self.description_edit = QLineEdit()
        form_layout.addRow("描述:", self.description_edit)
        
        self.source_pattern_edit = QLineEdit()
        form_layout.addRow("源路径模式 (正则):", self.source_pattern_edit)
        
        self.target_pattern_edit = QLineEdit()
        form_layout.addRow("目标路径模式:", self.target_pattern_edit)
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 999)
        self.priority_spin.setValue(1)
        form_layout.addRow("优先级:", self.priority_spin)
        
        self.enabled_checkbox = QCheckBox("启用此规则")
        self.enabled_checkbox.setChecked(True)
        form_layout.addRow("", self.enabled_checkbox)
        
        layout.addLayout(form_layout)
        
        # 帮助信息
        help_text = QTextEdit()
        help_text.setMaximumHeight(120)
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <b>正则表达式帮助:</b><br>
        • <code>^Assets[\\\\\/]entity[\\\\\/]</code> - 匹配以 Assets\\entity\\ 或 Assets/entity/ 开头的路径<br>
        • <code>^Assets[\\\\\/]ui[\\\\\/]</code> - 匹配以 Assets\\ui\\ 或 Assets/ui/ 开头的路径<br>
        • 目标模式示例: <code>Assets\\\\Resources\\\\minigame\\\\entity\\\\</code><br>
        • 优先级数字越小优先级越高
        """)
        layout.addWidget(help_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_data(self):
        """加载规则数据"""
        if self.rule_data:
            self.name_edit.setText(self.rule_data.get('name', ''))
            self.description_edit.setText(self.rule_data.get('description', ''))
            self.source_pattern_edit.setText(self.rule_data.get('source_pattern', ''))
            self.target_pattern_edit.setText(self.rule_data.get('target_pattern', ''))
            self.priority_spin.setValue(self.rule_data.get('priority', 1))
            self.enabled_checkbox.setChecked(self.rule_data.get('enabled', True))
    
    def get_rule_data(self):
        """获取规则数据"""
        data = {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.text().strip(),
            'source_pattern': self.source_pattern_edit.text().strip(),
            'target_pattern': self.target_pattern_edit.text().strip(),
            'priority': self.priority_spin.value(),
            'enabled': self.enabled_checkbox.isChecked()
        }
        
        if self.rule_id:
            data['rule_id'] = self.rule_id
        
        return data


class BranchSelectorDialog(QDialog):
    """分支选择对话框"""
    
    def __init__(self, branches, current_branch="", parent=None):
        super().__init__(parent)
        self.branches = branches
        self.filtered_branches = branches.copy()  # 过滤后的分支列表
        self.current_branch = current_branch
        self.selected_branch = ""
        
        self.setWindowTitle(f"选择分支 (共 {len(branches)} 个分支)")
        self.setModal(True)
        self.resize(600, 450)  # 稍微增加高度以容纳搜索框
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索分支:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词过滤分支...")
        self.search_input.textChanged.connect(self.filter_branches)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 分支计数标签
        self.count_label = QLabel(f"显示 {len(self.filtered_branches)} / {len(self.branches)} 个分支")
        self.count_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.count_label)
        
        # 分支列表
        self.branch_list = QListWidget()
        self.populate_branch_list()
        layout.addWidget(self.branch_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        # 清空搜索按钮
        clear_search_btn = QPushButton("清空搜索")
        clear_search_btn.clicked.connect(self.clear_search)
        button_layout.addWidget(clear_search_btn)
        
        button_layout.addStretch()  # 添加弹性空间
        
        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self.accept)
        button_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点到搜索框
        self.search_input.setFocus()
    
    def populate_branch_list(self):
        """填充分支列表"""
        self.branch_list.clear()
        
        if not self.filtered_branches:
            # 没有匹配的分支时显示提示
            item = QListWidgetItem("没有找到匹配的分支")
            item.setFlags(Qt.NoItemFlags)  # 不可选择
            item.setTextAlignment(Qt.AlignCenter)
            self.branch_list.addItem(item)
            return
        
        for branch in self.filtered_branches:
            item = QListWidgetItem(branch)
            if branch == self.current_branch:
                item.setText(f"★ {branch} (当前分支)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                # 设置当前分支为选中状态
                self.branch_list.addItem(item)
                self.branch_list.setCurrentItem(item)
            else:
                self.branch_list.addItem(item)
    
    def filter_branches(self):
        """根据搜索关键词过滤分支"""
        search_text = self.search_input.text().lower().strip()
        
        if not search_text:
            # 搜索框为空时显示所有分支
            self.filtered_branches = self.branches.copy()
        else:
            # 过滤包含关键词的分支（不区分大小写）
            self.filtered_branches = [
                branch for branch in self.branches 
                if search_text in branch.lower()
            ]
        
        # 更新分支列表和计数
        self.populate_branch_list()
        self.count_label.setText(f"显示 {len(self.filtered_branches)} / {len(self.branches)} 个分支")
    
    def clear_search(self):
        """清空搜索框"""
        self.search_input.clear()
    
    def get_selected_branch(self):
        """获取选中的分支"""
        current_item = self.branch_list.currentItem()
        if current_item and current_item.flags() != Qt.NoItemFlags:  # 确保不是提示项
            text = current_item.text()
            if text.startswith("★ "):
                return text.replace("★ ", "").replace(" (当前分支)", "")
            return text
        return ""


class UpdateCheckThread(QThread):
    """更新检查线程"""
    update_found = pyqtSignal(dict)
    no_update = pyqtSignal()
    check_failed = pyqtSignal(str)
    
    def __init__(self, hot_updater):
        super().__init__()
        self.hot_updater = hot_updater
    
    def run(self):
        try:
            has_update, update_info = self.hot_updater.check_for_updates()
            if has_update:
                self.update_found.emit(update_info)
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_failed.emit(str(e))


class UpdateExecuteThread(QThread):
    """更新执行线程"""
    update_progress = pyqtSignal(int, str)
    update_completed = pyqtSignal()
    update_failed = pyqtSignal(str)
    
    def __init__(self, hot_updater, update_info):
        super().__init__()
        self.hot_updater = hot_updater
        self.update_info = update_info
    
    def run(self):
        try:
            # 下载更新
            self.update_progress.emit(10, "正在下载更新文件...")
            if not self.hot_updater.download_update(self.update_info):
                self.update_failed.emit("下载更新失败")
                return
            
            self.update_progress.emit(70, "正在应用更新...")
            
            # 应用更新
            if self.hot_updater.apply_update():
                self.update_progress.emit(100, "更新完成")
                self.update_completed.emit()
            else:
                self.update_failed.emit("应用更新失败")
                
        except Exception as e:
            self.update_failed.emit(str(e))


class UpdateDialog(QDialog):
    """更新确认对话框"""
    
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("发现新版本")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel(f"发现新版本 {self.update_info.get('latest_version', 'Unknown')}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3;")
        layout.addWidget(title_label)
        
        # 当前版本
        current_version = self.update_info.get('current_version', 'Unknown')
        current_label = QLabel(f"当前版本: {current_version}")
        layout.addWidget(current_label)
        
        # 更新说明
        description = self.update_info.get('description') or self.update_info.get('release_notes', '无更新说明')
        desc_label = QLabel("更新说明:")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(desc_label)
        
        desc_text = QTextEdit()
        desc_text.setPlainText(description)
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(120)
        layout.addWidget(desc_text)
        
        # 文件信息
        files = self.update_info.get('files', [])
        if files:
            files_label = QLabel(f"更新文件: {len(files)} 个")
            files_label.setStyleSheet("margin-top: 10px;")
            layout.addWidget(files_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        update_btn = QPushButton("立即更新")
        update_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; }")
        update_btn.clicked.connect(self.accept)
        button_layout.addWidget(update_btn)
        
        later_btn = QPushButton("稍后提醒")
        later_btn.clicked.connect(self.reject)
        button_layout.addWidget(later_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)


def main():
    """主函数"""
    debug_print("开始主函数...")
    
    # 🗑️ 处理删除旧版本exe的命令行参数
    if len(sys.argv) >= 3 and sys.argv[1] == "--delete-old-exe":
        old_exe_path = sys.argv[2]
        debug_print(f"收到删除旧版本请求: {old_exe_path}")
        
        # 等待一段时间确保旧进程完全退出
        import time
        time.sleep(2)
        
        try:
            if os.path.exists(old_exe_path):
                os.remove(old_exe_path)
                debug_print(f"✅ 成功删除旧版本: {old_exe_path}")
            else:
                debug_print(f"⚠️ 旧版本文件不存在: {old_exe_path}")
        except Exception as e:
            debug_print(f"❌ 删除旧版本失败: {e}")
    
    try:
        debug_print("创建QApplication...")
        app = QApplication(sys.argv)
        debug_print("QApplication创建成功")
        
        # 设置应用程序图标为默认状态（白色图标）
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            icon_path = os.path.join(sys._MEIPASS, 'app_icon_bai.ico')
        else:
            # 开发环境
            icon_path = os.path.join(os.path.dirname(__file__), 'app_icon_bai.ico')
        
        debug_print(f"默认图标路径: {icon_path}")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            debug_print("设置应用程序默认图标成功")
        else:
            debug_print(f"默认图标文件不存在，尝试备用图标: {icon_path}")
            # 备用：使用绿色图标
            fallback_name = 'app_icon_lv.ico'
            if getattr(sys, 'frozen', False):
                fallback_path = os.path.join(sys._MEIPASS, fallback_name)
            else:
                fallback_path = os.path.join(os.path.dirname(__file__), fallback_name)
            if os.path.exists(fallback_path):
                app.setWindowIcon(QIcon(fallback_path))
                debug_print(f"使用备用图标: {fallback_name}")
        
        # 设置应用程序样式
        app.setStyle('Fusion')
        debug_print("设置样式成功")
        
        debug_print("创建主窗口...")
        window = ArtResourceManager()
        debug_print("主窗口创建成功")
        
        debug_print("显示窗口...")
        window.show()
        debug_print("窗口显示成功")
        
        debug_print("启动事件循环...")
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"主函数错误: {e}")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")


if __name__ == '__main__':
    main()