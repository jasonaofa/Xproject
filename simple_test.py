#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_path_comparison():
    """测试路径比较功能"""
    print("🧪 测试路径比较功能...")
    
    from art_resource_manager import GitSvnManager, ResourceChecker
    
    # 创建GitSvnManager实例
    git_manager = GitSvnManager()
    
    # 创建ResourceChecker实例（模拟）
    upload_files = ["test_file.png"]
    checker = ResourceChecker(upload_files, git_manager, "CommonResource")
    
    # 测试路径比较
    test_cases = [
        # (上传路径, Git路径, 预期结果)
        ("Assets/entity/140484/male1.png", "Assets/Resources/minigame/entity/140484/male1.png", True),
        ("Assets/entity/140484/male1.png", "Assets/entity/140484/male1.png", True),
        ("Assets/entity/140484/male1.png", "Assets/entity/140485/male1.png", False),
        ("Assets/different/path.png", "Assets/another/path.png", False),
    ]
    
    print(f"📋 路径映射规则数量: {len(git_manager.path_mapping_rules)}")
    print(f"🔧 路径映射状态: {'启用' if git_manager.path_mapping_enabled else '禁用'}")
    print()
    
    for i, (upload_path, git_path, expected) in enumerate(test_cases, 1):
        print(f"测试 {i}: {upload_path} vs {git_path}")
        
        # 显示映射结果
        mapped_path = git_manager.apply_path_mapping(upload_path)
        print(f"  映射后: {mapped_path}")
        
        # 测试比较结果
        result = checker._compare_file_paths(upload_path, git_path)
        print(f"  比较结果: {result} (预期: {expected})")
        
        if result == expected:
            print(f"  ✅ 测试通过")
        else:
            print(f"  ❌ 测试失败")
        
        print("-" * 50)

def test_non_blocking_types():
    """测试非阻塞问题类型"""
    print("\n🧪 测试非阻塞问题类型...")
    
    # 模拟问题列表
    all_issues = [
        {'type': 'guid_file_update', 'file': 'test1.png', 'message': '文件更新'},
        {'type': 'guid_file_update', 'file': 'test2.png', 'message': '文件更新'},
        {'type': 'meta_missing_git', 'file': 'test3.png', 'message': 'Git中缺少meta'},
        {'type': 'guid_duplicate_git', 'file': 'test4.png', 'message': 'GUID冲突'},
    ]
    
    # 使用与ResourceChecker相同的逻辑
    non_blocking_types = {'meta_missing_git', 'guid_file_update'}
    blocking_issues = [issue for issue in all_issues if issue.get('type') not in non_blocking_types]
    warning_issues = [issue for issue in all_issues if issue.get('type') in non_blocking_types]
    
    print(f"总问题数: {len(all_issues)}")
    print(f"阻塞性问题: {len(blocking_issues)}")
    print(f"非阻塞性问题: {len(warning_issues)}")
    
    print("\n阻塞性问题:")
    for issue in blocking_issues:
        print(f"  - {issue['type']}: {issue['message']}")
    
    print("\n非阻塞性问题:")
    for issue in warning_issues:
        print(f"  - {issue['type']}: {issue['message']}")
    
    # 统计文件更新数量
    file_updates = len([issue for issue in warning_issues if issue.get('type') == 'guid_file_update'])
    other_warnings = len(warning_issues) - file_updates
    
    print(f"\n文件更新数量: {file_updates}")
    print(f"其他警告数量: {other_warnings}")
    
    # 判断是否应该允许推送
    should_allow_push = len(blocking_issues) == 0
    print(f"\n是否允许推送: {should_allow_push}")
    
    if should_allow_push:
        if file_updates > 0 and other_warnings > 0:
            message = f"检查通过！发现 {file_updates} 个文件更新和 {other_warnings} 个警告"
        elif file_updates > 0:
            message = f"检查通过！发现 {file_updates} 个文件更新（将覆盖Git中的现有版本）"
        else:
            message = f"检查通过！发现 {len(warning_issues)} 个警告（推送时会自动处理）"
        print(f"消息: {message}")
    else:
        print(f"消息: 发现 {len(blocking_issues)} 个阻塞性问题，请查看详细报告")

if __name__ == "__main__":
    try:
        test_path_comparison()
        test_non_blocking_types()
        print("\n🎉 所有测试完成！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 