#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_recursive_dependency():
    """测试递归依赖分析功能"""
    
    print("🔍 测试递归依赖分析功能")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试文件路径
    test_file = "G:/Svn_repo/MiniProject_Art_NewPrefab/Assets/entity/avatar/1000_3401/3401.prefab"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"📁 测试文件: {os.path.basename(test_file)}")
    print(f"📁 完整路径: {test_file}")
    
    # 执行依赖分析
    print(f"\n🔍 开始递归依赖分析...")
    result = analyzer.find_dependency_files([test_file])
    
    # 分析结果
    print(f"\n📊 分析结果:")
    print(f"   原始文件: {len(result['original_files'])}")
    print(f"   依赖文件: {len(result['dependency_files'])}")
    print(f"   Meta文件: {len(result['meta_files'])}")
    print(f"   缺失依赖: {len(result['missing_dependencies'])}")
    
    # 检查是否找到了PNG文件
    png_files = [f for f in result['dependency_files'] if f.lower().endswith('.png')]
    print(f"\n🎨 找到的PNG文件: {len(png_files)}")
    
    if png_files:
        print("   ✅ PNG文件列表:")
        for png_file in png_files:
            print(f"      - {os.path.basename(png_file)}")
    else:
        print("   ❌ 没有找到PNG文件")
    
    # 检查材质文件
    mat_files = [f for f in result['dependency_files'] if f.lower().endswith('.mat')]
    print(f"\n🎨 找到的材质文件: {len(mat_files)}")
    
    if mat_files:
        print("   ✅ 材质文件列表:")
        for mat_file in mat_files:
            print(f"      - {os.path.basename(mat_file)}")
    
    # 检查缺失的依赖
    if result['missing_dependencies']:
        print(f"\n❌ 缺失的依赖:")
        for missing in result['missing_dependencies']:
            print(f"   - GUID: {missing['guid']}")
            print(f"     引用文件: {os.path.basename(missing['referenced_by'])}")
            print(f"     期望路径: {missing['expected_path']}")
    
    # 详细分析每个依赖文件
    print(f"\n🔍 详细依赖分析:")
    for i, dep_file in enumerate(result['dependency_files'], 1):
        file_ext = os.path.splitext(dep_file)[1].lower()
        print(f"   {i:2d}. {os.path.basename(dep_file)} ({file_ext})")
        
        # 如果是材质文件，检查它是否包含贴图引用
        if file_ext == '.mat':
            try:
                with open(dep_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找贴图引用
                import re
                texture_patterns = [
                    r'texture:\s*{.*?guid:\s*([a-f0-9]{32})',
                    r'texture:\s*{.*?m_GUID:\s*([a-f0-9]{32})',
                    r'm_Texture:\s*{.*?guid:\s*([a-f0-9]{32})',
                    r'm_Texture:\s*{.*?m_GUID:\s*([a-f0-9]{32})',
                    r'"texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"',
                    r'"texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"',
                    r'"m_Texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"',
                    r'"m_Texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"',
                ]
                
                found_textures = []
                for pattern in texture_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        guid = match.lower()
                        if guid not in found_textures:
                            found_textures.append(guid)
                
                if found_textures:
                    print(f"      🎨 包含 {len(found_textures)} 个贴图GUID:")
                    for guid in found_textures:
                        # 检查这个GUID是否在结果中找到
                        if guid in result['guid_to_file_map']:
                            texture_file = result['guid_to_file_map'][guid]
                            texture_ext = os.path.splitext(texture_file)[1].lower()
                            if texture_ext in ['.png', '.jpg', '.jpeg', '.tga']:
                                print(f"         ✅ {guid} -> {os.path.basename(texture_file)} (图片)")
                            else:
                                print(f"         ⚠️ {guid} -> {os.path.basename(texture_file)} ({texture_ext})")
                        else:
                            print(f"         ❌ {guid} -> 未找到")
                else:
                    print(f"      ❌ 没有找到贴图引用")
                    
            except Exception as e:
                print(f"      ❌ 读取材质文件失败: {e}")
    
    print(f"\n🎉 递归依赖分析测试完成!")

if __name__ == "__main__":
    test_recursive_dependency() 