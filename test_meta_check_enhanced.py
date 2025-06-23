#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试增强的Meta检查功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker, GitSvnManager, ResourceDependencyAnalyzer

def create_test_files():
    """创建测试文件和目录结构"""
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="meta_test_")
    svn_dir = os.path.join(temp_dir, "svn")
    git_dir = os.path.join(temp_dir, "git", "CommonResource")
    
    # 创建SVN目录结构
    svn_assets_dir = os.path.join(svn_dir, "Assets", "entity", "100028")
    os.makedirs(svn_assets_dir, exist_ok=True)
    
    # 创建Git目录结构
    git_assets_dir = os.path.join(git_dir, "Assets", "Resources", "minigame", "entity", "100028")
    os.makedirs(git_assets_dir, exist_ok=True)
    
    # 测试文件1：SVN和Git都有，GUID一致
    svn_file1 = os.path.join(svn_assets_dir, "test1.png")
    git_file1 = os.path.join(git_assets_dir, "test1.png")
    svn_meta1 = svn_file1 + ".meta"
    git_meta1 = git_file1 + ".meta"
    
    with open(svn_file1, 'w') as f:
        f.write("fake png content")
    with open(git_file1, 'w') as f:
        f.write("fake png content")
    
    # 创建一致的meta文件
    meta_content1 = """fileFormatVersion: 2
guid: 12345678901234567890123456789012
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {}
  serializedVersion: 11
"""
    with open(svn_meta1, 'w') as f:
        f.write(meta_content1)
    with open(git_meta1, 'w') as f:
        f.write(meta_content1)
    
    # 测试文件2：SVN和Git都有，GUID不一致
    svn_file2 = os.path.join(svn_assets_dir, "test2.png")
    git_file2 = os.path.join(git_assets_dir, "test2.png")
    svn_meta2 = svn_file2 + ".meta"
    git_meta2 = git_file2 + ".meta"
    
    with open(svn_file2, 'w') as f:
        f.write("fake png content")
    with open(git_file2, 'w') as f:
        f.write("fake png content")
    
    # 创建不一致的meta文件
    meta_content2_svn = """fileFormatVersion: 2
guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
TextureImporter:
  internalIDToNameTable: []
"""
    meta_content2_git = """fileFormatVersion: 2
guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
TextureImporter:
  internalIDToNameTable: []
"""
    with open(svn_meta2, 'w') as f:
        f.write(meta_content2_svn)
    with open(git_meta2, 'w') as f:
        f.write(meta_content2_git)
    
    # 测试文件3：SVN有，Git没有
    svn_file3 = os.path.join(svn_assets_dir, "test3.png")
    svn_meta3 = svn_file3 + ".meta"
    
    with open(svn_file3, 'w') as f:
        f.write("fake png content")
    
    meta_content3 = """fileFormatVersion: 2
guid: cccccccccccccccccccccccccccccccc
TextureImporter:
  internalIDToNameTable: []
"""
    with open(svn_meta3, 'w') as f:
        f.write(meta_content3)
    
    # 测试文件4：SVN没有，Git有
    svn_file4 = os.path.join(svn_assets_dir, "test4.png")
    git_file4 = os.path.join(git_assets_dir, "test4.png")
    git_meta4 = git_file4 + ".meta"
    
    with open(svn_file4, 'w') as f:
        f.write("fake png content")
    with open(git_file4, 'w') as f:
        f.write("fake png content")
    
    meta_content4 = """fileFormatVersion: 2
guid: dddddddddddddddddddddddddddddddd
TextureImporter:
  internalIDToNameTable: []
"""
    with open(git_meta4, 'w') as f:
        f.write(meta_content4)
    
    # 测试文件5：两边都没有meta
    svn_file5 = os.path.join(svn_assets_dir, "test5.png")
    with open(svn_file5, 'w') as f:
        f.write("fake png content")
    
    return {
        'temp_dir': temp_dir,
        'svn_dir': svn_dir,
        'git_dir': os.path.join(temp_dir, "git"),
        'test_files': [svn_file1, svn_file2, svn_file3, svn_file4, svn_file5]
    }

def test_meta_check():
    """测试Meta检查功能"""
    print("开始测试增强的Meta检查功能...")
    
    # 创建测试文件
    test_data = create_test_files()
    
    try:
        # 创建GitSvnManager
        git_manager = GitSvnManager()
        git_manager.set_paths(test_data['git_dir'], test_data['svn_dir'])
        
        # 创建ResourceChecker
        checker = ResourceChecker(
            upload_files=test_data['test_files'],
            git_manager=git_manager,
            target_directory="CommonResource"
        )
        
        # 执行Meta文件检查
        print("执行Meta文件检查...")
        issues = checker._check_meta_files()
        
        print(f"\n发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"\n问题 {i}:")
            print(f"  文件: {os.path.basename(issue['file'])}")
            print(f"  类型: {issue['type']}")
            print(f"  描述: {issue['message']}")
            
            if 'svn_path' in issue:
                print(f"  SVN路径: {issue['svn_path']}")
            if 'git_path' in issue:
                print(f"  Git路径: {issue['git_path']}")
            if 'svn_guid' in issue:
                print(f"  SVN GUID: {issue['svn_guid']}")
            if 'git_guid' in issue:
                print(f"  Git GUID: {issue['git_guid']}")
        
        # 生成详细报告
        print("\n生成详细报告...")
        report = checker._generate_detailed_report(issues, len(test_data['test_files']))
        
        print("\n详细报告:")
        print("=" * 80)
        print(report['report_text'])
        
        print(f"\n测试完成！发现 {len(issues)} 个问题")
        
        # 验证预期结果
        expected_issues = {
            'guid_mismatch': 1,  # test2.png
            'meta_missing_git': 1,  # test3.png
            'meta_missing_svn': 1,  # test4.png
            'meta_missing_both': 1  # test5.png
        }
        
        actual_issues = {}
        for issue in issues:
            issue_type = issue['type']
            actual_issues[issue_type] = actual_issues.get(issue_type, 0) + 1
        
        print(f"\n预期问题类型: {expected_issues}")
        print(f"实际问题类型: {actual_issues}")
        
        # 检查是否符合预期
        success = True
        for expected_type, expected_count in expected_issues.items():
            actual_count = actual_issues.get(expected_type, 0)
            if actual_count != expected_count:
                print(f"❌ {expected_type}: 预期 {expected_count} 个，实际 {actual_count} 个")
                success = False
            else:
                print(f"✅ {expected_type}: {actual_count} 个")
        
        if success:
            print("\n🎉 所有测试通过！")
        else:
            print("\n❌ 部分测试失败")
        
    finally:
        # 清理临时文件
        print(f"\n清理临时目录: {test_data['temp_dir']}")
        shutil.rmtree(test_data['temp_dir'], ignore_errors=True)

if __name__ == "__main__":
    test_meta_check() 