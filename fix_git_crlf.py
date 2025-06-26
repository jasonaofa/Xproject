#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git CRLF 问题修复工具
用于解决Windows系统下Git换行符转换导致的问题
"""

import os
import sys
import subprocess
import argparse

def configure_git_crlf(git_path):
    """配置Git换行符设置"""
    print(f"🔧 正在配置Git换行符设置...")
    print(f"   Git仓库路径: {git_path}")
    
    commands = [
        ("core.autocrlf", "false", "禁用自动换行符转换"),
        ("core.safecrlf", "false", "允许混合换行符"),
        ("core.eol", "lf", "设置默认换行符为LF")
    ]
    
    success_count = 0
    for config_key, config_value, description in commands:
        try:
            print(f"   设置 {config_key} = {config_value} ({description})")
            result = subprocess.run(
                ['git', 'config', config_key, config_value], 
                cwd=git_path, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"   ✅ {config_key} 设置成功")
                success_count += 1
            else:
                print(f"   ❌ {config_key} 设置失败: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ {config_key} 设置异常: {e}")
    
    return success_count == len(commands)

def create_gitattributes(git_path):
    """创建.gitattributes文件"""
    print(f"📄 正在创建.gitattributes文件...")
    
    gitattributes_path = os.path.join(git_path, '.gitattributes')
    
    content = """# Git属性文件 - 控制换行符处理
# 自动生成于Git CRLF修复工具

# 设置默认行为，以防没有设置core.autocrlf
* text=auto

# 文本文件，使用本地行结束符
*.py text
*.js text
*.cs text
*.txt text
*.md text
*.json text
*.xml text
*.yaml text
*.yml text

# Unity特定文件
*.prefab text
*.unity text
*.asset text
*.mat text
*.anim text
*.controller text
*.meta text

# 始终使用LF的文件
*.sh text eol=lf

# 二进制文件
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.dll binary
*.exe binary
*.so binary
*.dylib binary
*.fbx binary
*.mesh binary
*.terraindata binary
*.cubemap binary
*.unitypackage binary
"""
    
    try:
        with open(gitattributes_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"   ✅ .gitattributes 文件创建成功")
        return True
    except Exception as e:
        print(f"   ❌ .gitattributes 文件创建失败: {e}")
        return False

def reset_git_cache(git_path):
    """重置Git缓存"""
    print(f"🔄 正在重置Git缓存...")
    
    try:
        # 移除所有文件的跟踪
        result = subprocess.run(
            ['git', 'rm', '--cached', '-r', '.'], 
            cwd=git_path, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"   ✅ Git缓存清除成功")
        else:
            print(f"   ⚠️ Git缓存清除警告: {result.stderr}")
        
        # 重新添加所有文件
        result = subprocess.run(
            ['git', 'add', '.'], 
            cwd=git_path, 
            capture_output=True, 
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"   ✅ 文件重新添加成功")
            return True
        else:
            print(f"   ❌ 文件重新添加失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ 重置Git缓存异常: {e}")
        return False

def check_git_status(git_path):
    """检查Git状态"""
    print(f"📊 检查Git状态...")
    
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'], 
            cwd=git_path, 
            capture_output=True, 
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                changes = len(result.stdout.strip().split('\n'))
                print(f"   📝 检测到 {changes} 个文件变更")
            else:
                print(f"   ✅ 工作目录干净，没有待提交的更改")
            return True
        else:
            print(f"   ❌ 获取Git状态失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ 检查Git状态异常: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Git CRLF问题修复工具')
    parser.add_argument('git_path', help='Git仓库路径')
    parser.add_argument('--reset-cache', action='store_true', help='重置Git缓存（慎用）')
    parser.add_argument('--check-only', action='store_true', help='仅检查状态，不做修改')
    
    args = parser.parse_args()
    
    git_path = os.path.abspath(args.git_path)
    
    print("=" * 60)
    print("🛠️  Git CRLF问题修复工具")
    print("=" * 60)
    print(f"Git仓库路径: {git_path}")
    
    # 检查路径是否存在
    if not os.path.exists(git_path):
        print(f"❌ 错误：路径不存在 {git_path}")
        return False
    
    # 检查是否为Git仓库
    git_dir = os.path.join(git_path, '.git')
    if not os.path.exists(git_dir):
        print(f"❌ 错误：指定路径不是Git仓库 {git_path}")
        return False
    
    if args.check_only:
        print("🔍 仅检查模式")
        success = check_git_status(git_path)
    else:
        print("🔧 修复模式")
        
        # 步骤1：配置Git换行符设置
        config_success = configure_git_crlf(git_path)
        
        # 步骤2：创建.gitattributes文件
        gitattributes_success = create_gitattributes(git_path)
        
        # 步骤3：重置Git缓存（可选）
        cache_success = True
        if args.reset_cache:
            print("⚠️ 警告：将重置Git缓存，这可能会标记所有文件为已修改")
            confirmation = input("确定要继续吗？(y/N): ")
            if confirmation.lower() == 'y':
                cache_success = reset_git_cache(git_path)
            else:
                print("   跳过缓存重置")
        
        # 步骤4：检查结果
        status_success = check_git_status(git_path)
        
        success = config_success and gitattributes_success and cache_success and status_success
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 操作完成！")
        if not args.check_only:
            print("\n📝 后续建议：")
            print("1. 重新尝试Git推送操作")
            print("2. 如果仍有问题，考虑使用 --reset-cache 选项")
            print("3. 或者联系技术支持")
    else:
        print("❌ 操作失败！")
        print("\n🔧 故障排除：")
        print("1. 确保路径正确且为Git仓库")
        print("2. 确保有足够的权限")
        print("3. 检查Git是否正确安装")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 未预期的错误: {e}")
        sys.exit(1) 