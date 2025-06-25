#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新的GUID引用检查逻辑
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker, GitSvnManager, ResourceDependencyAnalyzer

def create_test_environment():
    """创建测试环境"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="guid_test_")
    print(f"创建测试环境: {temp_dir}")
    
    svn_dir = os.path.join(temp_dir, "svn_repo", "Assets", "entity", "test_character")
    git_dir = os.path.join(temp_dir, "git_repo", "CommonResource", "Assets", "Resources", "minigame", "entity", "test_character")
    
    # 创建目录结构
    os.makedirs(svn_dir, exist_ok=True)
    os.makedirs(git_dir, exist_ok=True)
    
    return temp_dir, svn_dir, git_dir

def create_test_files(svn_dir, git_dir):
    """创建测试文件"""
    test_files = []
    
    # 1. 创建一个完整的资源包（所有依赖都存在）
    # 主角色prefab
    character_prefab = os.path.join(svn_dir, "character.prefab")
    character_prefab_content = '''%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &1234567890123456789
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  serializedVersion: 6
  m_Component:
  - component: {fileID: 1234567890123456790}
  - component: {fileID: 1234567890123456791}
  m_Layer: 0
  m_Name: character
  m_TagString: Untagged
--- !u!23 &1234567890123456791
MeshRenderer:
  m_ObjectHideFlags: 0
  m_Materials:
  - {fileID: 2100000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1, type: 2}
  m_StaticBatchInfo:
    firstSubMesh: 0
    subMeshCount: 0
--- !u!33 &1234567890123456790
MeshFilter:
  m_ObjectHideFlags: 0
  m_Mesh: {fileID: 4300000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1, type: 3}
'''
    
    with open(character_prefab, 'w', encoding='utf-8') as f:
        f.write(character_prefab_content)
    
    # prefab的meta文件
    with open(character_prefab + '.meta', 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: cccccccccccccccccccccccccccccc1
PrefabImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_files.append(character_prefab)
    
    # 2. 创建材质文件（引用纹理）
    material_file = os.path.join(svn_dir, "character.mat")
    material_content = '''%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 6
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_Name: character
  m_Shader: {fileID: 46, guid: 0000000000000000f000000000000000, type: 0}
  m_ShaderKeywords: 
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
        m_Texture: {fileID: 2800000, guid: dddddddddddddddddddddddddddddd1, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
'''
    
    with open(material_file, 'w', encoding='utf-8') as f:
        f.write(material_content)
    
    # 材质的meta文件
    with open(material_file + '.meta', 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1
NativeFormatImporter:
  externalObjects: {}
  mainObjectFileID: 2100000
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_files.append(material_file)
    
    # 3. 创建模型文件
    mesh_file = os.path.join(svn_dir, "character.mesh")
    with open(mesh_file, 'w', encoding='utf-8') as f:
        f.write("# Dummy mesh file content")
    
    with open(mesh_file + '.meta', 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1
ModelImporter:
  serializedVersion: 26
  internalIDToNameTable: []
  externalObjects: {}
  materials:
    materialImportMode: 1
    materialName: 0
    materialSearch: 1
    materialLocation: 1
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_files.append(mesh_file)
    
    # 4. 创建纹理文件（被材质引用）
    texture_file = os.path.join(svn_dir, "character_diffuse.png")
    # 创建一个简单的PNG文件头（1x1像素）
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0bIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
    
    with open(texture_file, 'wb') as f:
        f.write(png_data)
    
    with open(texture_file + '.meta', 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: dddddddddddddddddddddddddddddd1
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {}
  serializedVersion: 11
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_files.append(texture_file)
    
    # 5. 创建一个有缺失依赖的文件
    broken_prefab = os.path.join(svn_dir, "broken_character.prefab")
    broken_prefab_content = '''%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &1234567890123456789
GameObject:
  m_ObjectHideFlags: 0
  m_Component:
  - component: {fileID: 1234567890123456791}
  m_Name: broken_character
--- !u!23 &1234567890123456791
MeshRenderer:
  m_ObjectHideFlags: 0
  m_Materials:
  - {fileID: 2100000, guid: eeeeeeeeeeeeeeeeeeeeeeeeeeeeee1, type: 2}  # 不存在的材质
  m_StaticBatchInfo:
    firstSubMesh: 0
    subMeshCount: 0
'''
    
    with open(broken_prefab, 'w', encoding='utf-8') as f:
        f.write(broken_prefab_content)
    
    with open(broken_prefab + '.meta', 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: fffffffffffffffffffffffffffff1
PrefabImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_files.append(broken_prefab)
    
    # 6. 创建一个可能孤立的纹理文件
    orphan_texture = os.path.join(svn_dir, "unused_texture.png")
    with open(orphan_texture, 'wb') as f:
        f.write(png_data)
    
    with open(orphan_texture + '.meta', 'w', encoding='utf-8') as f:
        f.write('''fileFormatVersion: 2
guid: 1111111111111111111111111111111
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
''')
    
    test_files.append(orphan_texture)
    
    return test_files

def test_guid_reference_check():
    """测试GUID引用检查"""
    print("开始测试新的GUID引用检查逻辑...")
    
    # 创建测试环境
    temp_dir, svn_dir, git_dir = create_test_environment()
    
    try:
        # 创建测试文件
        test_files = create_test_files(svn_dir, git_dir)
        
        print(f"\n创建了 {len(test_files)} 个测试文件:")
        for i, file_path in enumerate(test_files, 1):
            print(f"  {i}. {os.path.basename(file_path)}")
        
        # 设置Git管理器
        git_manager = GitSvnManager()
        git_manager.set_paths(os.path.join(temp_dir, "git_repo", "CommonResource"), 
                             os.path.join(temp_dir, "svn_repo"))
        
        # 创建资源检查器
        checker = ResourceChecker(test_files, git_manager, "CommonResource")
        
        print("\n开始执行GUID引用检查...")
        
        # 手动调用GUID引用检查方法
        guid_issues = checker._check_guid_references()
        
        print(f"\n检查完成，发现 {len(guid_issues)} 个问题:")
        
        # 按类型分组显示问题
        issues_by_type = {}
        for issue in guid_issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        for issue_type, issues in issues_by_type.items():
            print(f"\n【{issue_type}】({len(issues)} 个问题):")
            for i, issue in enumerate(issues, 1):
                print(f"  问题 {i}:")
                print(f"    文件: {os.path.basename(issue.get('file', ''))}")
                print(f"    描述: {issue.get('message', '')}")
                if 'missing_guid' in issue:
                    print(f"    缺失GUID: {issue['missing_guid']}")
                if 'missing_info' in issue:
                    print(f"    缺失类型: {issue['missing_info']}")
                if 'dependency_info' in issue:
                    print(f"    依赖关系: {issue['dependency_info']}")
        
        # 预期结果验证
        print(f"\n预期结果验证:")
        print(f"  - 应该发现 broken_character.prefab 引用了不存在的材质")
        print(f"  - 应该发现 unused_texture.png 可能是孤立文件")
        print(f"  - character.prefab 的依赖应该都存在（完整的资源包）")
        
        if 'guid_reference_missing' in issues_by_type:
            print(f"  ✓ 发现了缺失的GUID引用问题")
        else:
            print(f"  ✗ 未发现预期的GUID引用问题")
            
        if 'potentially_orphaned_file' in issues_by_type:
            print(f"  ✓ 发现了可能的孤立文件")
        else:
            print(f"  ✗ 未发现预期的孤立文件")
        
        print(f"\n测试完成！")
        
    finally:
        # 清理测试环境
        try:
            shutil.rmtree(temp_dir)
            print(f"清理测试环境: {temp_dir}")
        except:
            print(f"清理测试环境失败: {temp_dir}")

if __name__ == "__main__":
    test_guid_reference_check() 