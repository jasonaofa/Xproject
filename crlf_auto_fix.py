#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRLF自动修复模块
用于自动检测和修复Git仓库中的CRLF换行符问题
"""

import os
import subprocess
import re
import platform
from typing import List, Tuple

# 添加Windows特定的subprocess标志
if platform.system() == 'Windows':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0


class CRLFAutoFixer:
    """CRLF问题自动修复器"""
    
    def __init__(self, git_path: str):
        """
        初始化CRLF修复器
        
        Args:
            git_path: Git仓库路径
        """
        self.git_path = git_path
        
    def auto_fix_crlf_issue(self, error_message: str) -> Tuple[bool, str]:
        """
        自动修复CRLF问题的智能方法
        
        Args:
            error_message: Git错误消息
            
        Returns:
            Tuple[bool, str]: (是否修复成功, 结果消息)
        """
        try:
            print(f"   🔧 开始自动修复CRLF问题...")
            
            # 1. 检查并设置Git配置
            print(f"   1. 配置Git换行符处理...")
            
            # 设置core.safecrlf=false（临时解决）
            result = subprocess.run(['git', 'config', 'core.safecrlf', 'false'], 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                return False, f"设置core.safecrlf失败: {result.stderr}"
            
            print(f"   ✅ core.safecrlf 设置为 false")
            
            # 2. 智能检测文件类型并创建.gitattributes
            print(f"   2. 检测问题文件并配置属性...")
            gitattributes_path = os.path.join(self.git_path, '.gitattributes')
            
            # 从错误消息中提取文件信息
            problematic_files = self._extract_problematic_files_from_error(error_message)
            
            # 创建或更新.gitattributes文件
            success = self._create_smart_gitattributes(gitattributes_path, problematic_files)
            if not success:
                print(f"   ⚠️ .gitattributes 创建失败，继续尝试其他方法")
            
            # 3. 对于Unity特定的二进制文件，强制标记为binary
            print(f"   3. 处理Unity二进制文件...")
            self._handle_unity_binary_files(problematic_files)
            
            print(f"   ✅ CRLF问题自动修复完成")
            return True, "CRLF问题已自动修复"
            
        except Exception as e:
            return False, f"自动修复失败: {str(e)}"
    
    def _extract_problematic_files_from_error(self, error_message: str) -> List[str]:
        """从Git错误消息中提取有问题的文件路径"""
        problematic_files = []
        
        try:
            # 常见的CRLF错误格式：
            # "warning: LF will be replaced by CRLF in path/to/file.ext"
            # "fatal: LF would be replaced by CRLF in path/to/file.ext"
            
            patterns = [
                r'LF (?:will be|would be) replaced by CRLF in (.+)',
                r'CRLF (?:will be|would be) replaced by LF in (.+)',
                r'in file (.+?)(?:\s|$)',  # 其他格式
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, error_message, re.MULTILINE)
                for match in matches:
                    file_path = match.strip().strip('"\'')
                    if file_path and file_path not in problematic_files:
                        problematic_files.append(file_path)
                        print(f"   检测到问题文件: {file_path}")
            
        except Exception as e:
            print(f"   ⚠️ 提取问题文件失败: {e}")
        
        return problematic_files
    
    def _create_smart_gitattributes(self, gitattributes_path: str, problematic_files: List[str]) -> bool:
        """根据问题文件智能创建.gitattributes规则"""
        try:
            # 检查现有内容
            existing_content = ""
            if os.path.exists(gitattributes_path):
                with open(gitattributes_path, 'r', encoding='utf-8', errors='ignore') as f:
                    existing_content = f.read()
            
            # 分析文件扩展名
            extensions_to_fix = set()
            binary_extensions = {'.mesh', '.terraindata', '.cubemap', '.fbx', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.dll', '.exe', '.so', '.dylib'}
            
            for file_path in problematic_files:
                ext = os.path.splitext(file_path)[1].lower()
                if ext:
                    extensions_to_fix.add(ext)
            
            # 生成新规则
            new_rules = []
            
            # 添加基本规则（如果不存在）
            if "* text=auto" not in existing_content:
                new_rules.extend([
                    "",
                    "# Auto-generated CRLF fix rules",
                    "* text=auto",
                    ""
                ])
            
            # 为问题文件添加特定规则
            for ext in extensions_to_fix:
                rule_pattern = f"*{ext}"
                
                if rule_pattern not in existing_content:
                    if ext in binary_extensions:
                        new_rules.append(f"*{ext} binary")
                        print(f"   添加二进制规则: *{ext} binary")
                    else:
                        new_rules.append(f"*{ext} text eol=lf")
                        print(f"   添加文本规则: *{ext} text eol=lf")
            
            # 写入文件
            if new_rules:
                with open(gitattributes_path, 'a', encoding='utf-8', newline='\n') as f:
                    f.write('\n'.join(new_rules) + '\n')
                print(f"   ✅ .gitattributes 已更新，添加了 {len(new_rules)} 条规则")
                return True
            else:
                print(f"   ✅ .gitattributes 无需更新")
                return True
                
        except Exception as e:
            print(f"   ❌ 创建智能.gitattributes失败: {e}")
            return False
    
    def _handle_unity_binary_files(self, problematic_files: List[str]):
        """特别处理Unity二进制文件"""
        try:
            unity_binary_extensions = {'.mesh', '.terraindata', '.cubemap', '.asset'}
            
            for file_path in problematic_files:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in unity_binary_extensions:
                    print(f"   🎮 处理Unity二进制文件: {file_path}")
                    
                    # 对于这些文件，我们可以尝试重新设置文件属性
                    full_path = os.path.join(self.git_path, file_path)
                    if os.path.exists(full_path):
                        # 使用git update-index来强制设置属性
                        result = subprocess.run(['git', 'update-index', '--assume-unchanged', file_path], 
                                              cwd=self.git_path, 
                                              capture_output=True, 
                                              text=True,
                                              encoding='utf-8',
                                              errors='ignore',
                                              timeout=10, creationflags=SUBPROCESS_FLAGS)
                        
                        if result.returncode == 0:
                            print(f"   ✅ Unity文件属性已设置: {file_path}")
                        else:
                            print(f"   ⚠️ Unity文件属性设置失败: {file_path}")
            
        except Exception as e:
            print(f"   ❌ 处理Unity二进制文件失败: {e}")
    
    def quick_fix_common_issues(self) -> Tuple[bool, str]:
        """
        快速修复常见的CRLF问题（不需要错误消息）
        
        Returns:
            Tuple[bool, str]: (是否修复成功, 结果消息)
        """
        try:
            print(f"🔧 执行快速CRLF修复...")
            
            # 1. 设置基本Git配置
            subprocess.run(['git', 'config', 'core.safecrlf', 'false'], 
                          cwd=self.git_path, capture_output=True, timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            # 2. 创建基本的.gitattributes文件
            gitattributes_path = os.path.join(self.git_path, '.gitattributes')
            
            # 基本的Unity项目规则
            basic_rules = [
                "# Git属性配置文件 - 处理换行符和文件类型",
                "* text=auto",
                "",
                "# Unity文本文件",
                "*.cs text",
                "*.js text", 
                "*.boo text",
                "*.shader text",
                "*.cginc text",
                "",
                "# Unity场景和预设文件",
                "*.unity text",
                "*.prefab text",
                "*.mat text",
                "*.asset text",
                "*.meta text",
                "*.controller text",
                "*.anim text",
                "",
                "# Unity二进制文件",
                "*.fbx binary",
                "*.mesh binary",
                "*.terraindata binary", 
                "*.cubemap binary",
                "",
                "# 图像文件",
                "*.png binary",
                "*.jpg binary",
                "*.jpeg binary",
                "*.gif binary",
                "*.psd binary",
                "*.tga binary",
                "",
                "# 音频和视频文件",
                "*.mp3 binary",
                "*.wav binary",
                "*.ogg binary",
                "*.mp4 binary",
                "*.mov binary",
                "",
                "# 其他二进制文件",
                "*.dll binary",
                "*.exe binary",
                "*.zip binary",
                "*.7z binary"
            ]
            
            # 检查是否需要创建或更新
            create_file = True
            if os.path.exists(gitattributes_path):
                with open(gitattributes_path, 'r', encoding='utf-8', errors='ignore') as f:
                    existing = f.read()
                    if "* text=auto" in existing and "*.mesh binary" in existing:
                        create_file = False
                        print(f"   ✅ .gitattributes 已存在且包含必要规则")
            
            if create_file:
                with open(gitattributes_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write('\n'.join(basic_rules) + '\n')
                print(f"   ✅ 已创建基本的.gitattributes文件")
            
            return True, "快速CRLF修复完成"
            
        except Exception as e:
            return False, f"快速修复失败: {str(e)}"
    
    def quick_fix(self) -> dict:
        """快速修复方法（为UI调用提供统一接口）"""
        success, message = self.quick_fix_common_issues()
        return {'success': success, 'message': message}
    
    def preventive_fix(self) -> dict:
        """预防性修复方法（为UI调用提供统一接口）"""
        try:
            print(f"🧠 执行智能预防性CRLF修复...")
            
            # 1. 执行快速修复
            success, message = self.quick_fix_common_issues()
            if not success:
                return {'success': False, 'message': f"快速修复失败: {message}"}
            
            # 2. 额外的预防性措施
            # 设置更严格的Git配置
            subprocess.run(['git', 'config', 'core.autocrlf', 'false'], 
                          cwd=self.git_path, capture_output=True, timeout=10, creationflags=SUBPROCESS_FLAGS)
            
            # 3. 刷新Git索引
            subprocess.run(['git', 'add', '--renormalize', '.'], 
                          cwd=self.git_path, capture_output=True, timeout=30, creationflags=SUBPROCESS_FLAGS)
            
            print(f"   ✅ 预防性修复完成")
            return {'success': True, 'message': "智能预防性CRLF修复完成"}
            
        except Exception as e:
            return {'success': False, 'message': f"预防性修复失败: {str(e)}"}


def main():
    """测试函数"""
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python crlf_auto_fix.py <git_repo_path>")
        return
    
    git_path = sys.argv[1]
    if not os.path.exists(git_path):
        print(f"错误: 路径不存在 {git_path}")
        return
    
    fixer = CRLFAutoFixer(git_path)
    success, message = fixer.quick_fix_common_issues()
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")


if __name__ == "__main__":
    main() 