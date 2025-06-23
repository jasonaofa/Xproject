import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import os
import json
import yaml
import re
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                             QFileDialog, QComboBox, QCheckBox, QMessageBox, 
                             QProgressBar, QSplitter, QGroupBox, QGridLayout,
                             QListWidget, QListWidgetItem, QTabWidget, QDialog, QCompleter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QStringListModel
from PyQt5.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent, QDragMoveEvent
from config import ConfigManager


class ResourceDependencyAnalyzer:
    """资源依赖分析器"""
    
    def __init__(self):
        # Unity资源文件扩展名到依赖字段的映射
        self.unity_extensions = {
            '.prefab', '.mat', '.controller', '.anim', '.asset', 
            '.unity', '.fbx', '.png', '.jpg', '.jpeg', '.tga', '.psd'
        }
        
        # 着色器GUID映射
        self.common_shader_guids = {
            "00000000000000001000000000000000": "Standard",
            "00000000000000002000000000000000": "UI/Default",
            "00000000000000003000000000000000": "Sprites/Default"
        }
    
    def parse_meta_file(self, meta_path: str) -> str:
        """解析meta文件获取GUID"""
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 支持YAML和JSON格式
                guid_match = re.search(r'guid:\s*([a-f0-9]{32})', content) or \
                           re.search(r'"m_GUID":\s*"([a-f0-9]{32})"', content)
                if guid_match:
                    return guid_match.group(1)
        except Exception as e:
            print(f"解析meta文件失败: {meta_path}, 错误: {e}")
        return None
    
    def parse_unity_asset(self, file_path: str) -> Set[str]:
        """解析Unity资源文件，提取依赖的GUID"""
        dependencies = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查文件格式
            if content.strip().startswith('{'):
                # JSON格式
                dependencies.update(self._parse_json_asset(content, file_path))
            elif content.startswith('%YAML'):
                # YAML格式
                dependencies.update(self._parse_yaml_asset(content, file_path))
            else:
                # 尝试通用GUID提取
                dependencies.update(self._extract_guids_generic(content))
                
        except Exception as e:
            print(f"解析资源文件失败: {file_path}, 错误: {e}")
        
        return dependencies
    
    def _parse_json_asset(self, content: str, file_path: str) -> Set[str]:
        """解析JSON格式的Unity资源文件"""
        dependencies = set()
        
        try:
            # 使用正则表达式提取所有GUID
            guid_pattern = r'"m_GUID":\s*"([a-f0-9]{32})"'
            guids = re.findall(guid_pattern, content)
            
            # 获取文件自身的GUID
            self_guid = None
            meta_path = file_path + '.meta'
            if os.path.exists(meta_path):
                self_guid = self.parse_meta_file(meta_path)
            
            # 过滤掉自身GUID和常见系统GUID
            for guid in guids:
                if (guid != self_guid and 
                    guid not in self.common_shader_guids and
                    not guid.startswith('00000000000000')):
                    dependencies.add(guid)
                    
        except Exception as e:
            print(f"解析JSON资源失败: {file_path}, 错误: {e}")
            
        return dependencies
    
    def _parse_yaml_asset(self, content: str, file_path: str) -> Set[str]:
        """解析YAML格式的Unity资源文件"""
        dependencies = set()
        
        try:
            # YAML格式的GUID提取
            guid_patterns = [
                r'guid:\s*([a-f0-9]{32})',
                r'm_GUID:\s*([a-f0-9]{32})'
            ]
            
            for pattern in guid_patterns:
                guids = re.findall(pattern, content)
                dependencies.update(guids)
                
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
                elif any(file_path.lower().endswith(ext) for ext in self.unity_extensions):
                    report['files']['asset_files'].append(file_path)
                else:
                    report['files']['other_files'].append(file_path)
            
            # 3. 建立GUID映射
            for meta_file in report['files']['meta_files']:
                guid = self.parse_meta_file(meta_file)
                if guid:
                    asset_file = meta_file[:-5]  # 移除.meta后缀
                    report['guid_map'][guid] = {
                        'asset_file': asset_file,
                        'meta_file': meta_file,
                        'exists': os.path.exists(asset_file)
                    }
            
            # 4. 分析依赖关系
            for asset_file in report['files']['asset_files']:
                if os.path.exists(asset_file):
                    deps = self.parse_unity_asset(asset_file)
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
            if any(file_path.lower().endswith(ext) for ext in self.unity_extensions):
                deps = self.parse_unity_asset(file_path)
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
        
        # Unity内置GUID（不需要检查的系统资源）
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
            return git_guids
        
        try:
            # 扫描Git仓库中的.meta文件
            for root, dirs, files in os.walk(self.git_manager.git_path):
                for file in files:
                    if file.endswith('.meta'):
                        meta_path = os.path.join(root, file)
                        guid = self.analyzer.parse_meta_file(meta_path)
                        if guid:
                            git_guids.add(guid)
        except Exception as e:
            print(f"获取Git仓库GUID失败: {e}")
        
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


class GitSvnManager:
    """Git和SVN操作管理器"""
    
    def __init__(self):
        self.git_path = ""
        self.svn_path = ""
        self.current_branch = ""
    
    def set_paths(self, git_path: str, svn_path: str):
        """设置Git和SVN路径"""
        self.git_path = git_path
        self.svn_path = svn_path
    
    def get_git_branches(self) -> List[str]:
        """获取Git分支列表"""
        if not self.git_path or not os.path.exists(self.git_path):
            print(f"Git路径无效: {self.git_path}")
            return []
        
        try:
            # 先fetch最新的远程分支信息
            fetch_result = subprocess.run(['git', 'fetch'], 
                          cwd=self.git_path, 
                          capture_output=True, 
                          text=True,
                          encoding='utf-8',
                          errors='ignore')
            
            if fetch_result.returncode != 0:
                print(f"git fetch 警告: {fetch_result.stderr}")
            
            # 获取所有分支（本地 + 远程）
            branches = set()
            
            # 1. 获取本地分支
            result = subprocess.run(['git', 'branch'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line:
                        # 移除当前分支标记 '*'
                        branch = line.replace('* ', '').strip()
                        if branch:
                            branches.add(branch)
            else:
                print(f"获取本地分支失败: {result.stderr}")
            
            # 2. 获取远程分支
            result = subprocess.run(['git', 'branch', '-r'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('origin/HEAD'):
                        # 移除 'origin/' 前缀
                        branch = line.replace('origin/', '').strip()
                        if branch:
                            branches.add(branch)
            else:
                print(f"获取远程分支失败: {result.stderr}")
            
            final_branches = sorted(list(branches))
            return final_branches
            
        except Exception as e:
            print(f"获取Git分支异常: {e}")
        return []
    
    def get_current_branch(self) -> str:
        """获取当前Git分支"""
        if not self.git_path or not os.path.exists(self.git_path):
            return ""
        
        try:
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode == 0:
                self.current_branch = result.stdout.strip()
                return self.current_branch
        except Exception as e:
            print(f"获取当前分支失败: {e}")
        return ""
    
    def checkout_branch(self, branch_name: str) -> bool:
        """切换Git分支"""
        if not self.git_path or not os.path.exists(self.git_path):
            return False
        
        try:
            # 先fetch最新的远程分支
            subprocess.run(['git', 'fetch'], 
                          cwd=self.git_path, 
                          check=True,
                          encoding='utf-8',
                          errors='ignore')
            
            # 切换分支
            result = subprocess.run(['git', 'checkout', branch_name], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode == 0:
                self.current_branch = branch_name
                return True
            else:
                print(f"切换分支失败: {result.stderr}")
        except Exception as e:
            print(f"切换分支异常: {e}")
        return False
    
    def reset_git_repository(self) -> Tuple[bool, str]:
        """快速重置Git本地仓库"""
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        try:
            # 1. 获取当前分支名
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支"
            
            # 2. 清理未跟踪的文件 (git clean -f)
            result = subprocess.run(['git', 'clean', '-f'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode != 0:
                return False, f"清理未跟踪文件失败: {result.stderr}"
            
            # 3. 硬重置到当前分支 (git reset --hard 当前分支名)
            result = subprocess.run(['git', 'reset', '--hard', current_branch], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode != 0:
                return False, f"重置到分支失败: {result.stderr}"
            
            return True, f"快速重置完成 - 清理文件并重置到分支 {current_branch}"
            
        except subprocess.CalledProcessError as e:
            return False, f"Git命令执行失败: {e}"
        except Exception as e:
            return False, f"重置Git仓库时发生异常: {e}"
    
    def pull_current_branch(self) -> Tuple[bool, str]:
        """拉取当前分支的最新代码"""
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        try:
            # 1. 获取当前分支名
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支"
            
            # 2. 获取远程仓库信息 (git fetch)
            result = subprocess.run(['git', 'fetch', 'origin'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode != 0:
                return False, f"获取远程信息失败: {result.stderr}"
            
            # 3. 拉取当前分支 (git pull origin 当前分支名)
            result = subprocess.run(['git', 'pull', 'origin', current_branch], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode != 0:
                return False, f"拉取分支失败: {result.stderr}"
            
            return True, f"拉取成功 - 已更新分支 {current_branch} 到最新版本"
            
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

    def push_files_to_git(self, source_files: List[str], target_directory: str = "CommonResource") -> Tuple[bool, str]:
        """
        将文件推送到Git仓库
        
        Args:
            source_files: 源文件路径列表
            target_directory: 目标目录（相对于Git仓库根目录）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        if not self.git_path or not os.path.exists(self.git_path):
            return False, "Git仓库路径无效"
        
        if not source_files:
            return False, "没有要推送的文件"
        
        try:
            # 1. 确保目标目录存在
            target_base_path = os.path.join(self.git_path, target_directory)
            
            copied_files = []
            failed_files = []
            
            # 2. 复制文件到Git仓库
            for source_file in source_files:
                try:
                    # 计算目标路径
                    target_file_path = self._calculate_target_path(source_file, target_base_path)
                    
                    if not target_file_path:
                        failed_files.append(f"{os.path.basename(source_file)}: 无法计算目标路径")
                        continue
                    
                    # 确保目标目录存在
                    target_dir = os.path.dirname(target_file_path)
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # 复制文件
                    import shutil
                    shutil.copy2(source_file, target_file_path)
                    copied_files.append(target_file_path)
                    
                except Exception as e:
                    failed_files.append(f"{os.path.basename(source_file)}: {str(e)}")
            
            if not copied_files:
                return False, f"所有文件复制失败: {'; '.join(failed_files)}"
            
            # 3. 添加文件到Git
            for file_path in copied_files:
                # 计算相对于Git仓库根目录的路径
                relative_path = os.path.relpath(file_path, self.git_path)
                
                result = subprocess.run(['git', 'add', relative_path], 
                                      cwd=self.git_path, 
                                      capture_output=True, 
                                      text=True,
                                      encoding='utf-8',
                                      errors='ignore')
                if result.returncode != 0:
                    return False, f"添加文件到Git失败: {result.stderr}"
            
            # 4. 提交更改
            commit_message = f"Add {len(copied_files)} resource files via Art Resource Manager"
            result = subprocess.run(['git', 'commit', '-m', commit_message], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode != 0:
                # 检查是否是没有更改的情况
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    return False, "没有新的更改需要提交（文件可能已存在且内容相同）"
                return False, f"提交更改失败: {result.stderr}"
            
            # 5. 推送到远程仓库
            current_branch = self.get_current_branch()
            if not current_branch:
                return False, "无法获取当前分支"
            
            result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            if result.returncode != 0:
                return False, f"推送到远程仓库失败: {result.stderr}"
            
            # 6. 生成成功消息
            success_msg = f"成功推送 {len(copied_files)} 个文件到分支 {current_branch}"
            if failed_files:
                success_msg += f"，{len(failed_files)} 个文件失败: {'; '.join(failed_files[:3])}"
                if len(failed_files) > 3:
                    success_msg += f" 等{len(failed_files)}个"
            
            return True, success_msg
            
        except Exception as e:
            return False, f"推送过程中发生异常: {str(e)}"
    
    def _calculate_target_path(self, source_file: str, target_base_path: str) -> str:
        """
        计算源文件在目标Git仓库中的路径
        
        Args:
            source_file: 源文件路径
            target_base_path: 目标基础路径
            
        Returns:
            str: 目标文件路径，如果无法计算则返回None
        """
        try:
            if not self.svn_path:
                # 如果没有SVN路径，直接使用文件名
                filename = os.path.basename(source_file)
                return os.path.join(target_base_path, filename)
            
            # 规范化路径分隔符
            source_path = source_file.replace('/', '\\')
            svn_path = self.svn_path.replace('/', '\\')
            
            # 检查文件是否在SVN仓库内
            if not source_path.startswith(svn_path):
                # 文件不在SVN仓库内，直接使用文件名
                filename = os.path.basename(source_file)
                return os.path.join(target_base_path, filename)
            
            # 计算相对于SVN仓库根的路径
            relative_to_svn = source_path[len(svn_path):].lstrip('\\')
            
            # 查找Assets目录位置
            assets_index = relative_to_svn.find('Assets\\')
            if assets_index == -1:
                # 没有Assets目录，直接使用文件名
                filename = os.path.basename(source_file)
                return os.path.join(target_base_path, filename)
            
            # 提取Assets后面的路径部分
            assets_relative_path = relative_to_svn[assets_index + len('Assets\\'):]
            
            # 构建目标路径：target_base_path + Assets\Resources\minigame + assets_relative_path
            target_path = os.path.join(
                target_base_path,
                "Assets",
                "Resources",
                "minigame",
                assets_relative_path
            )
            
            return target_path
            
        except Exception as e:
            return None


class ResourceChecker(QThread):
    """资源检查线程 - 基于JSON格式文件的检查逻辑"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    check_completed = pyqtSignal(bool, str)
    detailed_report = pyqtSignal(dict)
    
    def __init__(self, upload_files, git_manager, target_directory):
        super().__init__()
        self.upload_files = upload_files
        self.git_manager = git_manager
        self.target_directory = target_directory
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

    def run(self):
        """运行检查任务"""
        try:
            self.status_updated.emit("开始检查资源...")
            
            # 检查所有问题
            all_issues = []
            
            # 1. Meta文件检查
            self.status_updated.emit("检查Meta文件...")
            self.progress_updated.emit(10)
            meta_issues = self._check_meta_files()
            all_issues.extend(meta_issues)
            
            # 2. 中文字符检查
            self.status_updated.emit("检查中文字符...")
            self.progress_updated.emit(30)
            chinese_issues = self._check_chinese_characters()
            all_issues.extend(chinese_issues)
            
            # 3. 图片尺寸检查
            self.status_updated.emit("检查图片尺寸...")
            self.progress_updated.emit(50)
            image_issues = self._check_image_sizes()
            all_issues.extend(image_issues)
            
            # 4. GUID一致性检查
            self.status_updated.emit("检查GUID一致性...")
            self.progress_updated.emit(70)
            guid_issues = self._check_guid_consistency()
            all_issues.extend(guid_issues)
            
            # 5. GUID引用检查
            self.status_updated.emit("检查GUID引用...")
            self.progress_updated.emit(90)
            reference_issues = self._check_guid_references()
            all_issues.extend(reference_issues)
            
            # 生成详细报告
            report = self._generate_detailed_report(all_issues, len(self.upload_files))
            self.detailed_report.emit(report)
            
            self.progress_updated.emit(100)
            
            if all_issues:
                self.check_completed.emit(False, f"发现 {len(all_issues)} 个问题，请查看详细报告")
            else:
                self.check_completed.emit(True, f"所有 {len(self.upload_files)} 个文件检查通过")
                
        except Exception as e:
            self.check_completed.emit(False, f"检查过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def _check_meta_files(self) -> List[Dict[str, str]]:
        """检查Meta文件完整性 - 严格的GUID一致性检查"""
        issues = []
        
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
                    # 直接使用Git路径作为基础路径，不再添加target_directory
                    # 因为git_path已经包含了CommonResource目录
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
                    # 两边都有.meta文件，检查GUID一致性
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
        """检查图片尺寸"""
        issues = []
        
        for file_path in self.upload_files:
            try:
                _, ext = os.path.splitext(file_path.lower())
                if ext in self.image_types:
                    try:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            width, height = img.size
                            
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
                            
                            # 检查尺寸是否过大
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

    def _check_guid_references(self) -> List[Dict[str, str]]:
        """检查GUID引用"""
        issues = []
        
        # 获取Git仓库中的所有GUID
        try:
            git_guids = self.analyzer._get_git_repository_guids()
        except:
            git_guids = set()
        
        for file_path in self.upload_files:
            try:
                _, ext = os.path.splitext(file_path.lower())
                if ext in self.high_priority_types or ext in self.medium_priority_types:
                    try:
                        referenced_guids = self.analyzer.parse_unity_asset(file_path)
                        
                        for guid in referenced_guids:
                            if guid not in self.builtin_guids and guid not in git_guids:
                                issues.append({
                                    'file': file_path,
                                    'type': 'guid_reference_missing',
                                    'message': f'引用的GUID不存在: {guid}'
                                })
                                
                    except Exception as e:
                        issues.append({
                            'file': file_path,
                            'type': 'guid_reference_error',
                            'message': f'GUID引用检查失败: {str(e)}'
                        })
                        
            except Exception as e:
                issues.append({
                    'file': file_path,
                    'type': 'guid_ref_check_error',
                    'message': f'GUID引用检查失败: {str(e)}'
                })
        
        return issues

    def _generate_detailed_report(self, all_issues: List[Dict[str, str]], total_files: int) -> Dict[str, Any]:
        """生成详细报告"""
        try:
            # 按类型分组问题
            issues_by_type = {}
            for issue in all_issues:
                issue_type = issue.get('type', 'unknown')
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append(issue)
            
            # 生成格式化报告
            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("资源检查详细报告")
            report_lines.append("=" * 80)
            report_lines.append(f"检查时间: {self._get_current_time()}")
            report_lines.append(f"检查文件总数: {total_files}")
            report_lines.append(f"发现问题总数: {len(all_issues)}")
            report_lines.append("")
            
            # 显示检查的文件列表
            report_lines.append("检查的文件列表:")
            report_lines.append("-" * 40)
            for i, file_path in enumerate(self.upload_files, 1):
                report_lines.append(f"  {i}. {file_path}")
            report_lines.append("")
            
            # 显示执行的检查项目
            report_lines.append("执行的检查项目:")
            report_lines.append("-" * 40)
            report_lines.append("  ✓ Meta文件完整性检查 - 严格检查SVN和Git中的.meta文件及GUID一致性")
            report_lines.append("  ✓ 中文字符检查 - 检查文件名是否包含中文字符")
            report_lines.append("  ✓ 图片尺寸检查 - 检查图片尺寸是否为2的幂次且不超过2048")
            report_lines.append("  ✓ GUID一致性检查 - 检查是否存在重复的GUID")
            report_lines.append("  ✓ GUID引用检查 - 检查引用的GUID是否存在于Git仓库中")
            report_lines.append("")
            
            if all_issues:
                report_lines.append("问题分类统计:")
                report_lines.append("-" * 40)
                
                # 问题类型说明 - 更新以支持新的Meta检查类型
                type_descriptions = {
                    # 新的Meta检查类型
                    'meta_missing_both': 'SVN和Git中都缺少.meta文件 - 需要生成.meta文件',
                    'meta_missing_svn': 'SVN中缺少.meta文件 - Git中存在，需要从Git复制',
                    'meta_missing_git': 'Git中缺少.meta文件 - SVN中存在，推送时会复制',
                    'meta_missing_svn_invalid_git': 'SVN中缺少.meta文件且Git中的.meta文件无效',
                    'meta_missing_git_invalid_svn': 'Git中缺少.meta文件且SVN中的.meta文件无效',
                    'guid_mismatch': 'GUID不一致 - SVN和Git中的.meta文件GUID不同',
                    'guid_invalid_both': 'SVN和Git中的.meta文件都没有有效GUID',
                    'guid_invalid_svn': 'SVN中的.meta文件无效GUID',
                    'guid_invalid_git': 'Git中的.meta文件无效GUID',
                    'svn_meta_no_guid': 'SVN中的.meta文件缺少有效GUID',
                    'svn_meta_read_error': 'SVN中的.meta文件读取失败',
                    'git_meta_read_error': 'Git中的.meta文件读取失败',
                    'git_path_calc_error': '计算Git路径失败',
                    
                    # 原有的检查类型
                    'meta_missing': 'Meta文件缺失 - 资源文件没有对应的.meta文件',
                    'meta_empty': 'Meta文件为空 - .meta文件存在但内容为空',
                    'meta_no_guid': 'Meta文件缺少GUID - .meta文件中没有找到guid字段',
                    'meta_read_error': 'Meta文件读取错误 - 无法读取.meta文件内容',
                    'meta_check_error': 'Meta文件检查错误 - 检查过程中发生异常',
                    'chinese_filename': '文件名包含中文字符 - 不建议在Unity资源文件名中使用中文',
                    'chinese_check_error': '中文字符检查错误 - 检查过程中发生异常',
                    'image_width_not_power_of_2': '图片宽度不是2的幂次 - 建议使用2^n尺寸以优化性能',
                    'image_height_not_power_of_2': '图片高度不是2的幂次 - 建议使用2^n尺寸以优化性能',
                    'image_too_large': '图片尺寸过大 - 超过2048像素可能影响性能',
                    'image_check_error': '图片检查错误 - 检查过程中发生异常',
                    'image_size_check_error': '图片尺寸检查错误 - 检查过程中发生异常',
                    'guid_duplicate': 'GUID重复 - 多个文件使用了相同的GUID',
                    'guid_consistency_error': 'GUID一致性检查错误 - 检查过程中发生异常',
                    'guid_reference_missing': 'GUID引用缺失 - 引用了不存在的资源GUID',
                    'guid_reference_error': 'GUID引用检查错误 - 检查过程中发生异常',
                    'guid_ref_check_error': 'GUID引用检查错误 - 检查过程中发生异常'
                }
                
                for issue_type, issues in issues_by_type.items():
                    description = type_descriptions.get(issue_type, f'未知问题类型: {issue_type}')
                    report_lines.append(f"  • {issue_type}: {len(issues)} 个")
                    report_lines.append(f"    说明: {description}")
                report_lines.append("")
                
                report_lines.append("详细问题列表:")
                report_lines.append("=" * 60)
                
                for issue_type, issues in issues_by_type.items():
                    report_lines.append(f"\n【{issue_type}】({len(issues)} 个问题)")
                    report_lines.append("-" * 50)
                    
                    for i, issue in enumerate(issues, 1):
                        file_path = issue.get('file', '')
                        file_name = os.path.basename(file_path)
                        message = issue.get('message', '')
                        
                        report_lines.append(f"  问题 {i}:")
                        report_lines.append(f"    文件名: {file_name}")
                        report_lines.append(f"    完整路径: {file_path}")
                        report_lines.append(f"    问题描述: {message}")
                        
                        # 显示额外的路径信息（如果存在）
                        if 'svn_path' in issue:
                            report_lines.append(f"    SVN路径: {issue['svn_path']}")
                        if 'git_path' in issue:
                            report_lines.append(f"    Git路径: {issue['git_path']}")
                        if 'svn_guid' in issue:
                            report_lines.append(f"    SVN GUID: {issue['svn_guid']}")
                        if 'git_guid' in issue:
                            report_lines.append(f"    Git GUID: {issue['git_guid']}")
                        
                        report_lines.append("")
                
                # 添加修复建议
                report_lines.append("\n修复建议:")
                report_lines.append("=" * 60)
                
                if 'meta_missing_both' in issues_by_type:
                    report_lines.append("\n【meta_missing_both】修复建议:")
                    report_lines.append("  1. 在Unity编辑器中重新导入这些资源文件")
                    report_lines.append("  2. 或者手动创建.meta文件并生成GUID")
                
                if 'meta_missing_svn' in issues_by_type:
                    report_lines.append("\n【meta_missing_svn】修复建议:")
                    report_lines.append("  1. 从Git仓库复制对应的.meta文件到SVN目录")
                    report_lines.append("  2. 确保文件名和路径完全匹配")
                
                if 'meta_missing_git' in issues_by_type:
                    report_lines.append("\n【meta_missing_git】修复建议:")
                    report_lines.append("  1. 推送操作会自动将SVN中的.meta文件复制到Git")
                    report_lines.append("  2. 无需手动处理")
                
                if 'guid_mismatch' in issues_by_type:
                    report_lines.append("\n【guid_mismatch】修复建议:")
                    report_lines.append("  1. 确定哪个GUID是正确的（通常Git中的更权威）")
                    report_lines.append("  2. 更新SVN中的.meta文件使其与Git保持一致")
                    report_lines.append("  3. 或者在Unity中重新生成.meta文件")
                
                if any(t in issues_by_type for t in ['chinese_filename']):
                    report_lines.append("\n【chinese_filename】修复建议:")
                    report_lines.append("  1. 重命名文件，使用英文名称")
                    report_lines.append("  2. 更新引用该文件的其他资源")
                
                if any(t in issues_by_type for t in ['image_width_not_power_of_2', 'image_height_not_power_of_2']):
                    report_lines.append("\n【图片尺寸】修复建议:")
                    report_lines.append("  1. 使用图像编辑软件调整图片尺寸为2的幂次")
                    report_lines.append("  2. 常用尺寸: 32, 64, 128, 256, 512, 1024, 2048")
                    report_lines.append("  3. 在Unity Import Settings中设置合适的压缩格式")
                
            else:
                report_lines.append("🎉 所有检查项目都通过了！")
                report_lines.append("")
                report_lines.append("检查结果:")
                report_lines.append("  ✅ 所有文件都有对应的.meta文件")
                report_lines.append("  ✅ 所有.meta文件都包含有效的GUID")
                report_lines.append("  ✅ SVN和Git中的GUID保持一致")
                report_lines.append("  ✅ 没有发现重复的GUID")
                report_lines.append("  ✅ 文件名符合规范")
                report_lines.append("  ✅ 图片尺寸符合要求")
            
            # 返回报告数据
            return {
                'total_files': total_files,
                'total_issues': len(all_issues),
                'issues_by_type': issues_by_type,
                'report_text': '\n'.join(report_lines),
                'has_errors': len(all_issues) > 0
            }
            
        except Exception as e:
            error_report = f"生成报告时发生错误: {str(e)}"
            return {
                'total_files': total_files,
                'total_issues': len(all_issues),
                'issues_by_type': {},
                'report_text': error_report,
                'has_errors': True,
                'generation_error': str(e)
            }
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BranchSelectorDialog(QDialog):
    """分支选择对话框"""
    
    def __init__(self, branches, current_branch="", parent=None):
        super().__init__(parent)
        self.branches = branches
        self.current_branch = current_branch
        self.selected_branch = ""
        
        self.setWindowTitle(f"选择分支 (共 {len(branches)} 个分支)")
        self.setModal(True)
        self.resize(600, 400)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 分支列表
        self.branch_list = QListWidget()
        for branch in self.branches:
            item = QListWidgetItem(branch)
            if branch == self.current_branch:
                item.setText(f"★ {branch} (当前分支)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.branch_list.addItem(item)
        
        layout.addWidget(self.branch_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self.accept)
        button_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def get_selected_branch(self):
        """获取选中的分支"""
        current_item = self.branch_list.currentItem()
        if current_item:
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
        
    def set_branches(self, branches, current_branch=""):
        """设置分支列表"""
        self.clear()
        if branches:
            for branch in branches:
                display_text = branch
                if branch == current_branch:
                    display_text = f"★ {branch} (当前)"
                self.addItem(display_text)
    
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


class ArtResourceManager(QMainWindow):
    """美术资源管理器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.git_manager = GitSvnManager()
        self.upload_files = []
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("美术资源管理工具")
        
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
    
    def load_settings(self):
        """加载设置"""
        # 加载路径配置
        self.svn_path_edit.setText(self.config_manager.get_svn_path())
        self.git_path_edit.setText(self.config_manager.get_git_path())
        self.editor_path_edit.setText(self.config_manager.get_editor_path())
        
        # 设置Git管理器路径
        if self.git_path_edit.text():
            self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
            self.refresh_branches()
            
            # 恢复上次选择的分支
            last_branch = self.config_manager.get_last_selected_branch()
            if last_branch:
                index = self.branch_combo.findText(last_branch)
                if index >= 0:
                    self.branch_combo.setCurrentIndex(index)
    
    def save_settings(self):
        """保存设置"""
        # 保存路径配置
        self.config_manager.set_svn_path(self.svn_path_edit.text())
        self.config_manager.set_git_path(self.git_path_edit.text())
        self.config_manager.set_editor_path(self.editor_path_edit.text())
        
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
        self.save_settings()
        event.accept()
    
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
        
        # 编辑器路径
        path_layout.addWidget(QLabel("编辑器路径:"), 2, 0)
        self.editor_path_edit = QLineEdit()
        self.editor_path_edit.setText("E:/RPGame5.6.9a")
        path_layout.addWidget(self.editor_path_edit, 2, 1)
        editor_browse_btn = QPushButton("浏览")
        editor_browse_btn.clicked.connect(self.browse_editor_path)
        path_layout.addWidget(editor_browse_btn, 2, 2)
        editor_open_btn = QPushButton("打开文件夹")
        editor_open_btn.clicked.connect(self.open_editor_folder)
        path_layout.addWidget(editor_open_btn, 2, 3)
        
        layout.addWidget(path_group)
        
        # 操作按钮组
        btn_layout = QHBoxLayout()
        
        self.pull_branch_btn = QPushButton("拉取分支")
        self.pull_branch_btn.clicked.connect(self.pull_current_branch)
        btn_layout.addWidget(self.pull_branch_btn)
        
        self.update_new_btn = QPushButton("重置更新仓库")
        self.update_new_btn.clicked.connect(self.reset_update_merge)
        btn_layout.addWidget(self.update_new_btn)
        
        self.delete_btn = QPushButton("一键删除重拉")
        self.delete_btn.clicked.connect(self.delete_duplicates)
        btn_layout.addWidget(self.delete_btn)
        
        self.pull_common_btn = QPushButton("拉取commonresource仓库")
        self.pull_common_btn.clicked.connect(self.pull_common_resource)
        btn_layout.addWidget(self.pull_common_btn)
        
        self.show_git_url_btn = QPushButton("显示git仓url")
        self.show_git_url_btn.clicked.connect(self.show_git_url)
        btn_layout.addWidget(self.show_git_url_btn)
        
        layout.addLayout(btn_layout)
        
        # 分支和资源类型
        branch_layout = QHBoxLayout()
        
        branch_layout.addWidget(QLabel("资源类型:"))
        self.resource_type_combo = QComboBox()
        self.resource_type_combo.addItems(["全部", "Prefab", "Material", "Texture", "Animation", "Script"])
        branch_layout.addWidget(self.resource_type_combo)
        
        self.check_btn = QPushButton("检查资源")
        self.check_btn.clicked.connect(self.check_and_push)
        branch_layout.addWidget(self.check_btn)
        
        layout.addLayout(branch_layout)
        
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

        # GUID查询
        guid_layout = QHBoxLayout()
        guid_layout.addWidget(QLabel("输入guid,在svn仓库查询对应资源:"))
        self.guid_edit = QLineEdit()
        guid_layout.addWidget(self.guid_edit)
        
        self.query_btn = QPushButton("查询")
        self.query_btn.clicked.connect(self.query_guid)
        guid_layout.addWidget(self.query_btn)
        
        layout.addLayout(guid_layout)
        
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
    
    def browse_svn_path(self):
        """浏览SVN路径"""
        path = QFileDialog.getExistingDirectory(self, "选择SVN仓库路径")
        if path:
            self.svn_path_edit.setText(path)
            self.config_manager.set_svn_path(path)
    
    def browse_git_path(self):
        """浏览Git路径"""
        path = QFileDialog.getExistingDirectory(self, "选择Git仓库路径")
        if path:
            self.git_path_edit.setText(path)
            self.config_manager.set_git_path(path)
            self.git_manager.set_paths(path, self.svn_path_edit.text())
            self.refresh_branches()
    
    def browse_editor_path(self):
        """浏览编辑器路径"""
        path = QFileDialog.getExistingDirectory(self, "选择编辑器路径")
        if path:
            self.editor_path_edit.setText(path)
            self.config_manager.set_editor_path(path)
    
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
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            
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
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            
            self.log_text.append(f"已打开Git文件夹: {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹: {str(e)}")
            self.log_text.append(f"打开Git文件夹失败: {str(e)}")
    
    def open_editor_folder(self):
        """打开编辑器文件夹"""
        path = self.editor_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "警告", "编辑器路径为空！")
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "警告", f"编辑器路径不存在：{path}")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            
            self.log_text.append(f"已打开编辑器文件夹: {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹: {str(e)}")
            self.log_text.append(f"打开编辑器文件夹失败: {str(e)}")
    
    def refresh_branches(self):
        """刷新分支列表"""
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
            "⚠️ 注意：切换分支前请确保已保存所有重要更改！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了分支切换操作")
            return
        
        self.log_text.append(f"开始切换分支: {current_branch} -> {selected_branch}")
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        try:
            self.progress_bar.setValue(50)
            success = self.git_manager.checkout_branch(selected_branch)
            self.progress_bar.setValue(100)
            
            if success:
                self.log_text.append(f"✓ 分支切换成功: 已切换到 {selected_branch}")
                self.result_text.append(f"✓ 分支切换成功: {current_branch} -> {selected_branch}")
                QMessageBox.information(self, "切换成功", f"已成功切换到分支: {selected_branch}")
                self.refresh_branches()
            else:
                self.log_text.append(f"✗ 分支切换失败: 无法切换到 {selected_branch}")
                self.result_text.append(f"✗ 分支切换失败: {current_branch} -> {selected_branch}")
                QMessageBox.critical(self, "切换失败", f"切换到分支 '{selected_branch}' 失败！\n请检查分支名称是否正确。")
                
        except Exception as e:
            error_msg = f"分支切换发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
            QMessageBox.critical(self, "操作异常", error_msg)
        
        finally:
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
            "• Meta文件完整性检查\n"
            "• 中文字符检查\n"
            "• 图片尺寸检查\n"
            "• GUID一致性检查\n"
            "• GUID引用检查\n"
            f"• 目标仓库：{self.git_path_edit.text()}\n"
            f"• 目标目录：CommonResource\n\n"
            "⚠️ 注意：检查过程可能需要一些时间，确定要开始吗？",
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
            "CommonResource"
        )
        
        self.checker_thread.progress_updated.connect(self.progress_bar.setValue)
        self.checker_thread.status_updated.connect(self.log_text.append)
        self.checker_thread.check_completed.connect(self.on_check_completed)
        self.checker_thread.detailed_report.connect(self.on_detailed_report_received)
        
        self.checker_thread.start()
        self.log_text.append("开始检查资源...")
    
    def on_check_completed(self, success: bool, message: str):
        """检查完成回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.result_text.append(f"✓ 检查通过: {message}")
            self.log_text.append("✅ 所有检查通过！准备推送...")
            self.show_push_confirmation_dialog()
        else:
            self.result_text.append(f"✗ 检查失败: {message}")
            QMessageBox.critical(self, "检查失败", message)
    
    def show_push_confirmation_dialog(self):
        """显示推送确认对话框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("检查通过 - 确认推送")
        msg_box.setIcon(QMessageBox.Question)
        
        file_count = len(self.upload_files)
        msg_text = (
            f"🎉 资源检查通过！\n\n"
            f"检查结果：\n"
            f"• 文件数量：{file_count} 个\n"
            f"• 目标仓库：{self.git_path_edit.text()}\n"
            f"• 目标目录：CommonResource\n\n"
            f"是否要将这些文件推送到Git仓库？"
        )
        msg_box.setText(msg_text)
        
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
            self.log_text.append("开始推送文件到Git仓库...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
            
            self.progress_bar.setValue(20)
            success, message = self.git_manager.push_files_to_git(self.upload_files, "CommonResource")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            if success:
                success_msg = f"✅ 推送完成！{message}"
                self.log_text.append(success_msg)
                self.result_text.append(success_msg)
                
                QMessageBox.information(
                    self, 
                    "推送成功", 
                    f"文件推送完成！\n\n"
                    f"• 推送文件数：{len(self.upload_files)} 个\n"
                    f"• 目标仓库：{self.git_path_edit.text()}\n"
                    f"• 目标目录：CommonResource\n"
                    f"• 当前分支：{self.git_manager.get_current_branch()}\n\n"
                    f"{message}"
                )
            else:
                error_msg = f"✗ 推送失败: {message}"
                self.log_text.append(error_msg)
                self.result_text.append(error_msg)
                QMessageBox.critical(
                    self, 
                    "推送失败", 
                    f"推送文件到Git仓库时失败：\n\n{message}\n\n"
                    f"请检查：\n"
                    f"• Git仓库路径是否正确\n"
                    f"• 是否有网络连接\n"
                    f"• 是否有推送权限\n"
                    f"• 分支是否存在冲突"
                )
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            error_msg = f"推送操作发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
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
                self.result_text.append(f"✓ Git分支拉取成功: {message}")
                QMessageBox.information(self, "拉取成功", message)
                self.refresh_branches()
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
    
    def reset_update_merge(self):
        """重置更新仓库"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认快速重置", 
            "此操作将快速重置Git本地仓库，包括：\n\n"
            "• 清理所有未跟踪的文件\n"
            "• 硬重置到服务器上的当前分支\n\n"
            "⚠️ 警告：此操作会丢失未提交的更改！确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.log_text.append("用户取消了重置操作")
            return
        
        self.log_text.append("开始重置Git仓库...")
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        try:
            success, message = self.git_manager.reset_git_repository()
            self.progress_bar.setValue(100)
            
            if success:
                self.log_text.append(f"✓ 重置成功: {message}")
                self.result_text.append(f"✓ Git仓库重置成功: {message}")
                QMessageBox.information(self, "重置成功", message)
                self.refresh_branches()
                self.show_current_branch()
            else:
                self.log_text.append(f"✗ 重置失败: {message}")
                self.result_text.append(f"✗ Git仓库重置失败: {message}")
                QMessageBox.critical(self, "重置失败", f"重置Git仓库失败：\n{message}")
                
        except Exception as e:
            error_msg = f"重置操作发生异常: {str(e)}"
            self.log_text.append(f"✗ {error_msg}")
            self.result_text.append(f"✗ {error_msg}")
            QMessageBox.critical(self, "操作异常", error_msg)
        
        finally:
            self.progress_bar.setVisible(False)
    
    def delete_duplicates(self):
        """一键删除重拉"""
        self.log_text.append("执行一键删除重拉...")
    
    def pull_common_resource(self):
        """拉取commonresource仓库"""
        self.log_text.append("拉取commonresource仓库...")
    
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
                                  errors='ignore')
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
        
        valid_files, invalid_files = self._validate_dropped_files(file_paths, svn_repo_path)
        
        if invalid_files:
            self._show_invalid_files_warning(invalid_files, svn_repo_path, len(valid_files))
        
        if not valid_files:
            self.log_text.append("❌ 没有有效文件可添加")
            return
        
        added_count = self._add_valid_files(valid_files)
        
        if added_count > 0:
            success_msg = f"成功添加了 {added_count} 个有效文件到上传列表"
            if invalid_files:
                success_msg += f"\n\n⚠️ 同时跳过了 {len(invalid_files)} 个无效文件"
            
            self.log_text.append(f"✅ 通过拖拽添加了 {added_count} 个文件")
            QMessageBox.information(self, "添加成功", success_msg)
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

    def open_branch_selector(self):
        """打开分支选择对话框"""
        if not self.git_path_edit.text():
            QMessageBox.warning(self, "警告", "请先设置Git仓库路径！")
            return
        
        self.git_manager.set_paths(self.git_path_edit.text(), self.svn_path_edit.text())
        
        branches = self.git_manager.get_git_branches()
        current_branch = self.git_manager.get_current_branch()
        
        if not branches:
            QMessageBox.warning(self, "警告", "无法获取分支列表！\n请检查Git仓库路径是否正确。")
            return
        
        dialog = BranchSelectorDialog(branches, current_branch, self)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_branch = dialog.get_selected_branch()
            if selected_branch:
                index = self.branch_combo.findText(selected_branch)
                if index >= 0:
                    self.branch_combo.setCurrentIndex(index)
                else:
                    self.refresh_branches()
                
                self.log_text.append(f"已选择分支: {selected_branch}")
            else:
                self.log_text.append("未选择任何分支")


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = ArtResourceManager()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main() 