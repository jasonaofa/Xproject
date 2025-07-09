#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git分支获取修复测试脚本
用于验证增强的get_current_branch方法是否能够正确处理各种Git状态
"""

import os
import sys
import subprocess
import tempfile
import shutil
import platform

# 添加Windows特定的subprocess标志
if platform.system() == 'Windows':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0

def test_git_branch_detection():
    """测试Git分支检测功能"""
    print("🧪 开始测试Git分支检测功能...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"📁 创建临时目录: {temp_dir}")
    
    try:
        # 初始化Git仓库
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        print("✅ Git仓库初始化成功")
        
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 添加并提交文件
        subprocess.run(['git', 'add', 'test.txt'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        print("✅ 初始提交完成")
        
        # 创建分支
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        print("✅ 创建测试分支完成")
        
        # 测试正常分支状态
        print("\n🔍 测试1: 正常分支状态")
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              cwd=temp_dir, 
                              capture_output=True, 
                              text=True, creationflags=SUBPROCESS_FLAGS)
        print(f"   当前分支: {result.stdout.strip()}")
        
        # 测试分离头指针状态
        print("\n🔍 测试2: 分离头指针状态")
        subprocess.run(['git', 'checkout', 'HEAD~0'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                              cwd=temp_dir, 
                              capture_output=True, 
                              text=True, creationflags=SUBPROCESS_FLAGS)
        print(f"   HEAD状态: {result.stdout.strip()}")
        
        # 测试获取提交哈希
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              cwd=temp_dir, 
                              capture_output=True, 
                              text=True, creationflags=SUBPROCESS_FLAGS)
        print(f"   提交哈希: {result.stdout.strip()}")
        
        print("\n✅ 所有测试完成！")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git命令执行失败: {e}")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"🧹 清理临时目录: {temp_dir}")

def test_enhanced_branch_detection():
    """测试增强的分支检测策略"""
    print("\n🧪 开始测试增强的分支检测策略...")
    
    # 模拟增强的get_current_branch方法
    def enhanced_get_current_branch(git_path):
        """模拟增强的get_current_branch方法"""
        if not os.path.exists(git_path):
            return ""
        
        try:
            # 策略1: git branch --show-current
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=git_path, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            # 策略2: git rev-parse --abbrev-ref HEAD
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  cwd=git_path, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                current_branch = result.stdout.strip()
                if current_branch == "HEAD":
                    # 分离头指针状态
                    commit_result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                                 cwd=git_path, 
                                                 capture_output=True, 
                                                 text=True,
                                                 timeout=5, creationflags=SUBPROCESS_FLAGS)
                    if commit_result.returncode == 0:
                        return f"DETACHED_HEAD_{commit_result.stdout.strip()}"
                else:
                    return current_branch
            
            # 策略3: git status --porcelain -b
            result = subprocess.run(['git', 'status', '--porcelain', '-b'], 
                                  cwd=git_path, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if lines:
                    first_line = lines[0]
                    if first_line.startswith('## '):
                        branch_info = first_line[3:]
                        if '...' in branch_info:
                            branch_name = branch_info.split('...')[0]
                        else:
                            branch_name = branch_info
                        
                        if branch_name and branch_name != "HEAD":
                            return branch_name
            
            # 策略4: git branch
            result = subprocess.run(['git', 'branch'], 
                                  cwd=git_path, 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('*'):
                        branch_name = line[1:].strip()
                        if branch_name:
                            return branch_name
            
            return ""
            
        except Exception as e:
            print(f"   错误: {e}")
            return ""
    
    # 创建临时目录进行测试
    temp_dir = tempfile.mkdtemp()
    print(f"📁 创建临时目录: {temp_dir}")
    
    try:
        # 初始化Git仓库
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        
        # 创建测试文件
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 添加并提交文件
        subprocess.run(['git', 'add', 'test.txt'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        
        # 测试正常分支
        print("\n🔍 测试正常分支状态:")
        branch = enhanced_get_current_branch(temp_dir)
        print(f"   检测结果: {branch}")
        
        # 创建新分支
        subprocess.run(['git', 'checkout', '-b', 'feature-branch'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        print("\n🔍 测试切换到新分支:")
        branch = enhanced_get_current_branch(temp_dir)
        print(f"   检测结果: {branch}")
        
        # 测试分离头指针
        subprocess.run(['git', 'checkout', 'HEAD~0'], cwd=temp_dir, check=True, creationflags=SUBPROCESS_FLAGS)
        print("\n🔍 测试分离头指针状态:")
        branch = enhanced_get_current_branch(temp_dir)
        print(f"   检测结果: {branch}")
        
        print("\n✅ 增强分支检测测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"🧹 清理临时目录: {temp_dir}")

if __name__ == "__main__":
    print("🚀 Git分支获取修复测试")
    print("=" * 50)
    
    # 检查Git是否可用
    try:
        subprocess.run(['git', '--version'], check=True, capture_output=True, creationflags=SUBPROCESS_FLAGS)
        print("✅ Git可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Git不可用，请确保已安装Git")
        sys.exit(1)
    
    # 运行测试
    test_git_branch_detection()
    test_enhanced_branch_detection()
    
    print("\n🎉 所有测试完成！")
    print("\n💡 如果测试通过，说明修复方案有效。")
    print("   现在可以重新运行美术资源上传工具，应该能够正常获取分支信息了。") 