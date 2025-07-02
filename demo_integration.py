#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示如何将CRLF解决方案集成到美术资源管理器中
"""

from crlf_auto_fix import CRLFAutoFixer
import subprocess
import os


class GitSvnManagerWithCRLF:
    """集成CRLF自动修复功能的Git管理器示例"""
    
    def __init__(self, git_path: str):
        self.git_path = git_path
        self.crlf_fixer = CRLFAutoFixer(git_path)
    
    def push_files_to_git_enhanced(self, source_files: list, target_directory: str = "CommonResource"):
        """
        增强版推送方法，集成CRLF自动修复功能
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            print(f"🚀 开始推送 {len(source_files)} 个文件...")
            
            # ... 这里是原有的文件复制逻辑 ...
            # copied_files = self._copy_files_to_git(source_files, target_directory)
            
            # 模拟文件复制完成
            relative_paths = [f"Assets/Resources/file_{i}.prefab" for i in range(len(source_files))]
            
            # 尝试添加文件到Git
            print(f"📝 添加文件到Git...")
            result = subprocess.run(['git', 'add'] + relative_paths, 
                                  cwd=self.git_path, 
                                  capture_output=True, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore',
                                  timeout=60)
            
            if result.returncode != 0:
                print(f"❌ 添加文件失败: {result.stderr}")
                
                # 🔧 这里是集成的CRLF自动修复逻辑
                if self._is_crlf_error(result.stderr):
                    print(f"🔧 检测到CRLF问题，启动自动修复...")
                    
                    # 调用CRLF自动修复
                    fix_success, fix_message = self.crlf_fixer.auto_fix_crlf_issue(result.stderr)
                    
                    if fix_success:
                        print(f"✅ CRLF问题已修复: {fix_message}")
                        
                        # 重新尝试添加文件
                        print(f"🔄 重新尝试添加文件...")
                        retry_result = subprocess.run(['git', 'add'] + relative_paths, 
                                                    cwd=self.git_path, 
                                                    capture_output=True, 
                                                    text=True,
                                                    encoding='utf-8',
                                                    errors='ignore',
                                                    timeout=60)
                        
                        if retry_result.returncode == 0:
                            print(f"✅ 文件添加成功")
                            result = retry_result  # 更新结果继续后续流程
                        else:
                            return False, f"CRLF修复成功但重新添加失败: {retry_result.stderr}"
                    else:
                        # 自动修复失败，提供用户指导
                        error_message = (
                            "🚨 检测到Git换行符冲突！\n\n"
                            f"自动修复失败: {fix_message}\n\n"
                            "💡 您可以尝试以下解决方案：\n\n"
                            "1️⃣ 使用快速修复功能\n"
                            "2️⃣ 手动运行CRLF修复工具\n"
                            "3️⃣ 重置更新仓库\n\n"
                            "详细错误信息:\n" + result.stderr
                        )
                        return False, error_message
                else:
                    return False, f"Git添加失败: {result.stderr}"
            
            # 继续正常的Git操作流程
            print(f"✅ 文件添加成功，继续提交...")
            
            # ... 这里继续原有的commit和push逻辑 ...
            
            return True, "推送成功"
            
        except Exception as e:
            return False, f"推送异常: {str(e)}"
    
    def _is_crlf_error(self, error_message: str) -> bool:
        """检查是否为CRLF相关错误"""
        crlf_keywords = [
            "LF would be replaced by CRLF",
            "CRLF would be replaced by LF", 
            "LF will be replaced by CRLF",
            "CRLF will be replaced by LF"
        ]
        return any(keyword in error_message for keyword in crlf_keywords)
    
    def quick_fix_crlf_issues(self):
        """快速修复CRLF问题的便捷方法"""
        print(f"🔧 执行CRLF快速修复...")
        success, message = self.crlf_fixer.quick_fix_common_issues()
        
        if success:
            print(f"✅ {message}")
            return True, "CRLF问题已预防性修复"
        else:
            print(f"❌ {message}")
            return False, f"快速修复失败: {message}"


def demo_integration():
    """演示集成效果"""
    print("=" * 60)
    print("🎯 CRLF自动修复功能集成演示")
    print("=" * 60)
    
    # 假设的Git仓库路径
    demo_git_path = r"G:\minirepo\AssetRuntime_Branch08\assetruntime\CommonResource"
    
    if not os.path.exists(demo_git_path):
        print(f"⚠️ 演示路径不存在: {demo_git_path}")
        print(f"请替换为您的实际Git仓库路径")
        return
    
    # 创建集成CRLF功能的管理器
    manager = GitSvnManagerWithCRLF(demo_git_path)
    
    print(f"📂 Git仓库路径: {demo_git_path}")
    print()
    
    # 演示1: 快速修复
    print("🔧 演示1: 预防性CRLF修复")
    success, message = manager.quick_fix_crlf_issues()
    print(f"结果: {message}")
    print()
    
    # 演示2: 推送过程中的自动修复
    print("🚀 演示2: 推送过程中的智能CRLF处理")
    test_files = ["test1.prefab", "test2.mesh", "test3.png"]
    success, message = manager.push_files_to_git_enhanced(test_files)
    print(f"推送结果: {message}")
    print()
    
    print("=" * 60)
    print("✅ 集成演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo_integration() 