#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def check_material_textures():
    """检查材质文件中的贴图引用"""
    
    print("🔍 检查材质文件中的贴图引用")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 检查特定的材质文件
    material_files = [
        "juxie_fuhao.mat",  # 这是GUID 8964d7b89a36a244ab36a6aaca1bb016 指向的文件
        "sanguang.mat",
        "juxie_rongjie01.mat",
        "juxie_rongjie02.mat",
        "juxie_rongjie03.mat",
        "juxie_tuowei.mat",
        "juxie_tuowei02.mat",
        "juxie_tuowei_liang.mat",
        "juxie_huanrao.mat",
        "juxie_tu.mat",
        "paopao.mat",
        "wc_lizi_guangxian.mat"
    ]
    
    # 查找这些文件的实际路径
    svn_root = "G:/Svn_repo/MiniProject_Art_NewPrefab"
    found_materials = []
    
    print(f"🔍 在SVN仓库中查找材质文件...")
    for root, dirs, files in os.walk(svn_root):
        for file in files:
            if file in material_files:
                file_path = os.path.join(root, file)
                found_materials.append(file_path)
                print(f"✅ 找到: {file}")
    
    print(f"\n📊 找到 {len(found_materials)} 个材质文件")
    
    # 分析每个材质文件中的贴图引用
    all_texture_guids = set()
    
    for material_path in found_materials:
        print(f"\n🔍 分析材质文件: {os.path.basename(material_path)}")
        
        try:
            with open(material_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找贴图引用
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
                    found_textures.append(guid)
                    all_texture_guids.add(guid)
            
            if found_textures:
                print(f"   🎨 找到 {len(found_textures)} 个贴图GUID:")
                for guid in found_textures:
                    print(f"      - {guid}")
            else:
                print(f"   ❌ 没有找到贴图引用")
                
        except Exception as e:
            print(f"   ❌ 读取文件失败: {e}")
    
    print(f"\n📊 总共找到 {len(all_texture_guids)} 个唯一的贴图GUID")
    
    # 检查这些贴图GUID是否在SVN中找到
    if all_texture_guids:
        print(f"\n🔍 检查贴图GUID在SVN中的映射...")
        
        guid_map = {}
        analyzer._scan_directory_for_guids(svn_root, guid_map)
        
        found_in_svn = 0
        for guid in all_texture_guids:
            if guid in guid_map:
                found_in_svn += 1
                file_path = guid_map[guid]
                file_ext = os.path.splitext(file_path)[1].lower()
                print(f"   ✅ {guid} -> {os.path.basename(file_path)} ({file_ext})")
                
                # 检查是否是图片文件
                image_extensions = ['.png', '.jpg', '.jpeg', '.tga', '.psd', '.tiff', '.bmp']
                if file_ext in image_extensions:
                    print(f"      🎉 这是图片文件!")
                elif file_ext == '.meta':
                    resource_file = file_path[:-5]
                    if os.path.exists(resource_file):
                        resource_ext = os.path.splitext(resource_file)[1].lower()
                        if resource_ext in image_extensions:
                            print(f"      🎉 对应的资源文件是图片!")
            else:
                print(f"   ❌ {guid} -> 未找到")
        
        print(f"\n📊 SVN匹配结果: {found_in_svn}/{len(all_texture_guids)} 个贴图GUID在SVN中找到")
    
    print(f"\n🎉 检查完成!")

if __name__ == "__main__":
    check_material_textures() 