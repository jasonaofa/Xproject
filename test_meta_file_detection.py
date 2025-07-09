#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import shutil

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def create_test_files():
    """创建测试文件"""
    test_dir = tempfile.mkdtemp(prefix="test_meta_")
    
    # 创建测试文件
    test_files = {
        "body.prefab": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &12345678901234567890123456789012
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  serializedVersion: 6
  m_Component:
  - component: {fileID: 12345678901234567890123456789013}
  m_Layer: 0
  m_Name: Body
  m_TagString: Untagged
  m_Icon: {fileID: 0}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1""",
        
        "body.prefab.meta": """fileFormatVersion: 2
guid: 12345678901234567890123456789012
PrefabImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: """,
        
        "material.mat": """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_Name: TestMaterial
  m_Shader: {fileID: 46, guid: 0000000000000000f000000000000000, type: 0}""",
        
        "material.mat.meta": """fileFormatVersion: 2
guid: 87654321098765432109876543210987
NativeFormatImporter:
  externalObjects: {}
  userData: 
  assetBundleName: 
  assetBundleVariant: """
    }
    
    # 写入文件
    for filename, content in test_files.items():
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return test_dir

def test_meta_file_detection():
    """测试meta文件检测"""
    
    print("🔍 测试原始文件的meta文件检测")
    print("=" * 60)
    
    # 创建测试文件
    test_dir = create_test_files()
    print(f"📁 创建测试目录: {test_dir}")
    
    try:
        # 创建分析器
        analyzer = ResourceDependencyAnalyzer()
        
        # 测试文件列表
        test_files = [
            os.path.join(test_dir, "body.prefab"),
            os.path.join(test_dir, "material.mat")
        ]
        
        print(f"\n📄 测试文件:")
        for file_path in test_files:
            print(f"   - {os.path.basename(file_path)}")
        
        # 执行依赖分析
        print(f"\n🔍 开始依赖分析...")
        result = analyzer.find_dependency_files(test_files, [test_dir])
        
        # 显示分析结果
        print(f"\n📊 分析结果:")
        print(f"   原始文件: {result['analysis_stats']['total_original']}")
        print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
        print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
        print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
        
        print(f"\n📁 找到的meta文件:")
        for meta_file in result['meta_files']:
            print(f"   - {os.path.basename(meta_file)}")
        
        print(f"\n📁 找到的依赖文件:")
        for dep_file in result['dependency_files']:
            print(f"   - {os.path.basename(dep_file)}")
        
        # 检查原始文件的meta是否被包含
        expected_meta_files = [
            os.path.join(test_dir, "body.prefab.meta"),
            os.path.join(test_dir, "material.mat.meta")
        ]
        
        print(f"\n✅ 检查原始文件的meta文件:")
        all_found = True
        for expected_meta in expected_meta_files:
            if expected_meta in result['meta_files']:
                print(f"   ✅ {os.path.basename(expected_meta)} - 已包含")
            else:
                print(f"   ❌ {os.path.basename(expected_meta)} - 未包含")
                all_found = False
        
        if all_found:
            print(f"\n🎉 所有原始文件的meta文件都被正确检测到！")
        else:
            print(f"\n⚠️ 部分原始文件的meta文件未被检测到")
        
        # 检查GUID映射
        print(f"\n🔑 GUID映射:")
        for file_path, guid in result['file_to_guid_map'].items():
            print(f"   {os.path.basename(file_path)} -> {guid}")
        
        return all_found
        
    finally:
        # 清理测试文件
        shutil.rmtree(test_dir)
        print(f"\n🧹 清理测试目录: {test_dir}")

def test_specific_body_prefab():
    """专门测试body.prefab的情况"""
    
    print("\n" + "=" * 60)
    print("🔍 专门测试 body.prefab 的meta文件检测")
    print("=" * 60)
    
    # 检查当前目录是否有body.prefab文件
    body_prefab = "body.prefab"
    body_meta = "body.prefab.meta"
    
    if not os.path.exists(body_prefab):
        print(f"❌ 当前目录没有找到 {body_prefab}")
        return False
    
    print(f"✅ 找到测试文件: {body_prefab}")
    
    # 检查meta文件
    if os.path.exists(body_meta):
        print(f"✅ 找到meta文件: {body_meta}")
    else:
        print(f"❌ 没有找到meta文件: {body_meta}")
        return False
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 执行分析
    result = analyzer.find_dependency_files([body_prefab])
    
    print(f"\n📊 分析结果:")
    print(f"   原始文件: {result['analysis_stats']['total_original']}")
    print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
    print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
    
    print(f"\n📁 找到的meta文件:")
    for meta_file in result['meta_files']:
        print(f"   - {meta_file}")
    
    # 检查body.prefab.meta是否被包含
    if body_meta in result['meta_files']:
        print(f"\n✅ {body_meta} 已被正确包含在结果中！")
        return True
    else:
        print(f"\n❌ {body_meta} 未被包含在结果中！")
        return False

if __name__ == "__main__":
    # 运行测试
    test1_result = test_meta_file_detection()
    test2_result = test_specific_body_prefab()
    
    print("\n" + "=" * 60)
    print("📋 测试总结:")
    print(f"   模拟文件测试: {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"   实际文件测试: {'✅ 通过' if test2_result else '❌ 失败'}")
    
    if test1_result and test2_result:
        print("🎉 所有测试都通过了！meta文件检测功能正常工作。")
    else:
        print("⚠️ 部分测试失败，需要进一步检查。") 