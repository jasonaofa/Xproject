#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import shutil

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker

def test_new_templates():
    """测试新添加的特效模板是否正确工作"""
    
    print("🔍 测试新添加的特效模板")
    print("=" * 60)
    
    # 创建临时测试目录
    test_dir = tempfile.mkdtemp(prefix="test_new_templates_")
    print(f"📁 创建测试目录: {test_dir}")
    
    try:
        # 创建entity目录结构
        entity_dir = os.path.join(test_dir, "entity")
        material_dir = os.path.join(entity_dir, "effects")
        os.makedirs(material_dir)
        
        # 创建测试材质文件
        test_materials = {
            # 应该通过的特效模板
            "fx_basic_add.mat": {
                "template": "fx_basic_ADD.templatemat",
                "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: fx_basic_add
  fx_basic_ADD.templatemat
""",
                "expected": "valid"
            },
            
            "fx_dissolve_test.mat": {
                "template": "fx_dissolve_ADD.templatemat",
                "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: fx_dissolve_test
  fx_dissolve_ADD.templatemat
""",
                "expected": "valid"
            },
            
            "particle_effect.mat": {
                "template": "standard_particle_additive.templatemat",
                "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: particle_effect
  standard_particle_additive.templatemat
""",
                "expected": "valid"
            },
            
            "polar_distortion.mat": {
                "template": "PolarDistortion.templatemat",
                "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: polar_distortion
  PolarDistortion.templatemat
""",
                "expected": "valid"
            },
            
            # 应该失败的模板
            "invalid_fx.mat": {
                "template": "fx_invalid_template.templatemat",
                "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: invalid_fx
  fx_invalid_template.templatemat
""",
                "expected": "invalid"
            },
            
            "old_default.mat": {
                "template": "DefaultMaterial.templatemat",
                "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_Name: old_default
  DefaultMaterial.templatemat
""",
                "expected": "invalid"
            }
        }
        
        # 创建测试文件
        test_files = []
        for filename, info in test_materials.items():
            file_path = os.path.join(material_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(info["content"])
            test_files.append(file_path)
            print(f"✅ 创建测试文件: {filename} (模板: {info['template']}, 预期: {info['expected']})")
        
        # 创建ResourceChecker实例
        class MockGitManager:
            def __init__(self):
                self.git_path = test_dir
                self.svn_path = test_dir
        
        checker = ResourceChecker(test_files, MockGitManager(), "CommonResource")
        
        # 运行材质模板检查
        print(f"\n🔍 运行材质模板检查...")
        issues = checker._check_material_templates()
        
        print(f"\n📊 检查结果:")
        print(f"   发现问题数量: {len(issues)}")
        
        # 分析问题类型
        issue_types = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        if issues:
            print(f"\n📋 问题详情:")
            for issue_type, type_issues in issue_types.items():
                print(f"   {issue_type}: {len(type_issues)} 个")
                for issue in type_issues:
                    filename = os.path.basename(issue['file'])
                    message = issue['message']
                    template_name = issue.get('template_name', 'N/A')
                    print(f"     - {filename}: {message}")
                    if template_name != 'N/A':
                        print(f"       模板: {template_name}")
        
        # 验证预期结果
        print(f"\n✅ 验证预期结果:")
        
        # 应该有2个无效模板问题
        invalid_template_issues = issue_types.get('invalid_template', [])
        print(f"   无效模板问题: {len(invalid_template_issues)} 个 (预期: 2)")
        
        # 检查具体的无效模板
        found_invalid_fx = False
        found_default_material = False
        
        for issue in invalid_template_issues:
            template_name = issue.get('template_name', '')
            if template_name == 'fx_invalid_template.templatemat':
                found_invalid_fx = True
            elif template_name == 'DefaultMaterial.templatemat':
                found_default_material = True
        
        print(f"   检测到fx_invalid_template: {found_invalid_fx} (预期: True)")
        print(f"   检测到DefaultMaterial: {found_default_material} (预期: True)")
        
        # 检查特效模板是否被正确识别
        print(f"\n🔍 检查特效模板识别情况:")
        valid_fx_templates = [
            "fx_basic_ADD.templatemat",
            "fx_dissolve_ADD.templatemat", 
            "standard_particle_additive.templatemat",
            "PolarDistortion.templatemat"
        ]
        
        for template in valid_fx_templates:
            found_issue = any(issue.get('template_name') == template for issue in issues)
            if found_issue:
                print(f"   ❌ {template} 被错误地报告为问题")
            else:
                print(f"   ✅ {template} 被正确识别为有效模板")
        
        # 总结
        print(f"\n🎯 测试总结:")
        if (len(invalid_template_issues) == 2 and 
            found_invalid_fx and found_default_material):
            print("   ✅ 所有测试通过！新的特效模板规则正确工作")
        else:
            print("   ❌ 测试失败，需要检查模板配置")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\n🧹 清理测试目录: {test_dir}")

if __name__ == "__main__":
    test_new_templates() 