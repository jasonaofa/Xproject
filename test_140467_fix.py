#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker

def test_140467_fix():
    """测试140467文件的材质模板检查修复"""
    
    print("🔍 测试140467文件的材质模板检查修复")
    print("=" * 60)
    
    # 查找140467目录下的材质文件
    svn_path = "C:/6.1.10_prefab/Assets/entity/140467"
    
    print(f"📁 查找材质文件，路径: {svn_path}")
    print(f"📁 路径是否存在: {os.path.exists(svn_path)}")
    
    mat_files = []
    if os.path.exists(svn_path):
        for root, dirs, files in os.walk(svn_path):
            for file in files:
                if file.lower().endswith('.mat'):
                    full_path = os.path.join(root, file)
                    mat_files.append(full_path)
                    print(f"✅ 找到材质文件: {full_path}")
    
    if not mat_files:
        print("❌ 没有找到材质文件")
        return
    
    print(f"📁 总共找到 {len(mat_files)} 个材质文件")
    
    # 创建ResourceChecker实例
    class MockGitManager:
        def __init__(self):
            self.git_path = ""
            self.svn_path = ""
    
    checker = ResourceChecker(mat_files, MockGitManager(), "CommonResource")
    
    # 运行材质模板检查
    print("\n🔍 运行材质模板检查...")
    issues = checker._check_material_templates()
    
    print(f"\n📊 检查结果:")
    print(f"   发现问题数量: {len(issues)}")
    
    if issues:
        # 按类型分组问题
        issue_types = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        print(f"\n📋 问题详情:")
        for issue_type, type_issues in issue_types.items():
            print(f"   {issue_type}: {len(type_issues)} 个")
            for issue in type_issues:
                filename = os.path.basename(issue['file'])
                message = issue['message']
                template_name = issue.get('template_name', 'N/A')
                print(f"     - {filename}: {message}")
                if template_name != 'N/A':
                    print(f"       使用的模板: {template_name}")
    else:
        print("   ✅ 没有发现问题")
    
    # 验证预期结果
    print(f"\n✅ 验证预期结果:")
    expected_invalid = False
    
    for issue in issues:
        if (issue.get('type') == 'invalid_template' and 
            'DefaultMaterial.templatemat' in issue.get('template_name', '')):
            expected_invalid = True
            break
    
    if expected_invalid:
        print("   ✅ 正确检测到 body_base.mat 使用了不允许的 DefaultMaterial.templatemat 模板")
    else:
        print("   ❌ 未检测到预期的无效模板问题")
    
    print(f"\n🎉 测试完成！")

if __name__ == "__main__":
    test_140467_fix() 