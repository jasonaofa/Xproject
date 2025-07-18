#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import shutil

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker

def create_test_material_files():
    """创建测试材质文件"""
    test_dir = tempfile.mkdtemp(prefix="test_material_template_")
    print(f"📁 创建测试目录: {test_dir}")
    
    # 创建entity目录结构
    entity_dir = os.path.join(test_dir, "entity")
    os.makedirs(entity_dir)
    
    # 创建角色目录
    character_dir = os.path.join(entity_dir, "character")
    os.makedirs(character_dir)
    
    # 创建场景道具目录
    scene_dir = os.path.join(entity_dir, "scene")
    os.makedirs(scene_dir)
    
    # 创建排除目录
    exclude_dir = os.path.join(entity_dir, "Environment", "Scenes")
    os.makedirs(exclude_dir, exist_ok=True)
    
    # 创建测试材质文件
    test_materials = {
        # 正确的模板
        "good_material1.mat": {
            "path": character_dir,
            "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_Name: GoodMaterial1
  m_Shader: {fileID: 4800000, guid: 12345678901234567890123456789012, type: 3}
  m_ShaderKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap: {}
  disabledShaderPasses: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _MainTex:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    templatemat: Character_NPR_Opaque.templatemat
"""
        },
        
        # 错误的模板
        "bad_material1.mat": {
            "path": character_dir,
            "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_Name: BadMaterial1
  m_Shader: {fileID: 4800000, guid: 12345678901234567890123456789012, type: 3}
  templatemat: InvalidTemplate.templatemat
"""
        },
        
        # 没有模板的材质
        "no_template_material.mat": {
            "path": scene_dir,
            "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_Name: NoTemplateMaterial
  m_Shader: {fileID: 4800000, guid: 12345678901234567890123456789012, type: 3}
"""
        },
        
        # 在排除目录中的材质（不应该被检查）
        "excluded_material.mat": {
            "path": exclude_dir,
            "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_Name: ExcludedMaterial
  m_Shader: {fileID: 4800000, guid: 12345678901234567890123456789012, type: 3}
  templatemat: SomeRandomTemplate.templatemat
"""
        },
        
        # 不在entity目录中的材质（不应该被检查）
        "outside_material.mat": {
            "path": test_dir,
            "content": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_Name: OutsideMaterial
  m_Shader: {fileID: 4800000, guid: 12345678901234567890123456789012, type: 3}
  templatemat: AnotherRandomTemplate.templatemat
"""
        }
    }
    
    # 创建材质文件
    created_files = []
    for filename, info in test_materials.items():
        file_path = os.path.join(info["path"], filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(info["content"])
        created_files.append(file_path)
        print(f"✅ 创建测试文件: {file_path}")
    
    return test_dir, created_files

def test_material_template_check():
    """测试材质模板检查功能"""
    print("🔍 测试材质模板检查功能")
    print("=" * 60)
    
    # 创建测试文件
    test_dir, test_files = create_test_material_files()
    
    try:
        # 创建一个模拟的git_manager
        class MockGitManager:
            def __init__(self):
                self.git_path = test_dir
                self.svn_path = test_dir
        
        # 创建检查器
        checker = ResourceChecker(test_files, MockGitManager(), "CommonResource")
        
        # 运行材质模板检查
        print("\n🔍 运行材质模板检查...")
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
        
        print(f"\n📋 问题分类:")
        for issue_type, type_issues in issue_types.items():
            print(f"   {issue_type}: {len(type_issues)} 个")
            for issue in type_issues:
                filename = os.path.basename(issue['file'])
                print(f"     - {filename}: {issue['message']}")
        
        # 验证预期结果
        print(f"\n✅ 验证预期结果:")
        
        # 应该有1个无效模板错误
        invalid_template_issues = issue_types.get('invalid_template', [])
        print(f"   无效模板问题: {len(invalid_template_issues)} 个 (预期: 1)")
        
        # 应该有1个没有模板的问题
        no_template_issues = issue_types.get('no_template_found', [])
        print(f"   没有模板问题: {len(no_template_issues)} 个 (预期: 1)")
        
        # 不应该有排除目录和entity外的文件问题
        excluded_file_found = any('excluded_material.mat' in issue['file'] for issue in issues)
        outside_file_found = any('outside_material.mat' in issue['file'] for issue in issues)
        
        print(f"   排除目录文件被检查: {excluded_file_found} (预期: False)")
        print(f"   entity外文件被检查: {outside_file_found} (预期: False)")
        
        # 测试模板查找功能
        print(f"\n🔍 测试模板查找功能...")
        
        # 创建测试内容
        good_content = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  templatemat: Character_NPR_Opaque.templatemat
"""
        
        bad_content = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  templatemat: InvalidTemplate.templatemat
"""
        
        no_template_content = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  m_Name: NoTemplateMaterial
"""
        
        # 测试正确模板的查找
        good_templates = checker._find_template_references(good_content)
        print(f"   正确模板查找结果: {good_templates}")
        
        # 测试错误模板的查找
        bad_templates = checker._find_template_references(bad_content)
        print(f"   错误模板查找结果: {bad_templates}")
        
        # 测试没有模板的查找
        no_templates = checker._find_template_references(no_template_content)
        print(f"   没有模板查找结果: {no_templates}")
        
        print(f"\n✅ 材质模板检查功能测试完成！")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"🧹 清理测试目录: {test_dir}")

if __name__ == "__main__":
    test_material_template_check() 