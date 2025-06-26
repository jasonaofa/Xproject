#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新的GUID唯一性检查功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker, GitSvnManager

def create_test_environment():
    """创建测试环境"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="guid_uniqueness_test_")
    print(f"创建测试环境: {temp_dir}")
    
    # 创建Git仓库目录结构
    git_dir = os.path.join(temp_dir, "git_repo")
    test_files_dir = os.path.join(temp_dir, "test_files")
    
    os.makedirs(git_dir, exist_ok=True)
    os.makedirs(test_files_dir, exist_ok=True)
    
    return temp_dir, git_dir, test_files_dir

def create_test_files(git_dir, test_files_dir):
    """创建测试文件"""
    test_scenarios = []
    
    # 场景1：在Git仓库中创建一个现有文件
    git_existing_file = os.path.join(git_dir, "existing_resource.prefab")
    with open(git_existing_file, 'w', encoding='utf-8') as f:
        f.write("# Existing resource in Git")
    
    git_existing_meta = git_existing_file + '.meta'
    with open(git_existing_meta, 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1
PrefabImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    # 场景2：创建一个与Git冲突的上传文件
    conflict_file = os.path.join(test_files_dir, "conflicting_resource.mat")
    with open(conflict_file, 'w', encoding='utf-8') as f:
        f.write("# This will conflict with Git")
    
    conflict_meta = conflict_file + '.meta'
    with open(conflict_meta, 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1
NativeFormatImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_scenarios.append({
        'name': 'Git冲突',
        'files': [conflict_file],
        'expected_issues': ['guid_duplicate_git']
    })
    
    # 场景3：创建内部重复GUID的文件
    duplicate1_file = os.path.join(test_files_dir, "duplicate1.png")
    with open(duplicate1_file, 'wb') as f:
        # 简单的PNG头
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde')
    
    duplicate1_meta = duplicate1_file + '.meta'
    with open(duplicate1_meta, 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1
TextureImporter:
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    duplicate2_file = os.path.join(test_files_dir, "duplicate2.png")
    with open(duplicate2_file, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde')
    
    duplicate2_meta = duplicate2_file + '.meta'
    with open(duplicate2_meta, 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1
TextureImporter:
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_scenarios.append({
        'name': '内部重复',
        'files': [duplicate1_file, duplicate2_file],
        'expected_issues': ['guid_duplicate_internal']
    })
    
    # 场景4：创建正常文件（不应该有唯一性问题）
    normal_file = os.path.join(test_files_dir, "normal_resource.controller")
    with open(normal_file, 'w', encoding='utf-8') as f:
        f.write("# Normal resource")
    
    normal_meta = normal_file + '.meta'
    with open(normal_meta, 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: cccccccccccccccccccccccccccccc1
NativeFormatImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_scenarios.append({
        'name': '正常文件',
        'files': [normal_file],
        'expected_issues': []
    })
    
    return test_scenarios

def test_guid_uniqueness():
    """测试GUID唯一性检查"""
    print("开始测试GUID唯一性检查功能...")
    
    # 创建测试环境
    temp_dir, git_dir, test_files_dir = create_test_environment()
    
    try:
        # 创建测试文件
        test_scenarios = create_test_files(git_dir, test_files_dir)
        
        # 设置Git管理器
        git_manager = GitSvnManager()
        git_manager.git_path = git_dir
        
        # 测试每个场景
        for scenario in test_scenarios:
            print(f"\n{'='*60}")
            print(f"测试场景: {scenario['name']}")
            print(f"{'='*60}")
            
            # 创建资源检查器
            checker = ResourceChecker(scenario['files'], git_manager, "test_target")
            
            print(f"测试文件:")
            for file_path in scenario['files']:
                print(f"  - {os.path.basename(file_path)}")
            
            # 手动调用GUID唯一性检查方法
            print("\n开始执行GUID唯一性检查...")
            uniqueness_issues = checker._check_guid_uniqueness()
            
            print(f"\n检查完成，发现 {len(uniqueness_issues)} 个唯一性问题:")
            
            # 显示发现的问题
            issues_by_type = {}
            for issue in uniqueness_issues:
                issue_type = issue.get('type', 'unknown')
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append(issue)
            
            for issue_type, issues in issues_by_type.items():
                print(f"\n  【{issue_type}】({len(issues)} 个):")
                for issue in issues:
                    print(f"    - {issue.get('message', '无描述')}")
                    if 'guid' in issue:
                        print(f"      涉及GUID: {issue['guid']}")
                    if 'files' in issue:
                        file_names = [os.path.basename(f) for f in issue['files']]
                        print(f"      涉及文件: {', '.join(file_names)}")
            
            # 验证结果
            print(f"\n验证结果:")
            expected_types = set(scenario['expected_issues'])
            actual_types = set(issues_by_type.keys())
            
            if expected_types == actual_types:
                print(f"  ✅ 检查结果符合预期")
            else:
                print(f"  ❌ 检查结果不符合预期")
                print(f"     期望: {expected_types}")
                print(f"     实际: {actual_types}")
        
        print(f"\n{'='*60}")
        print("所有测试场景执行完成")
        print(f"{'='*60}")
    
    finally:
        # 清理测试环境
        try:
            shutil.rmtree(temp_dir)
            print(f"\n清理测试环境: {temp_dir}")
        except:
            print(f"\n警告: 无法清理测试环境: {temp_dir}")

if __name__ == "__main__":
    test_guid_uniqueness() 