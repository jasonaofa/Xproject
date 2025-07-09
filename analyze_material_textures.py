#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def analyze_material_textures():
    """专门分析材质文件中的贴图引用"""
    
    print("🔍 专门分析材质文件中的贴图引用")
    print("=" * 60)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 请用户输入材质文件路径
    test_file = input("请输入材质文件路径 (例如: sanguang.mat): ").strip()
    
    if not test_file:
        print("❌ 未输入文件路径")
        return
    
    # 如果只输入了文件名，尝试在当前目录查找
    if not os.path.isabs(test_file):
        # 在当前目录及其子目录中查找
        for root, dirs, files in os.walk('.'):
            if test_file in files:
                test_file = os.path.join(root, test_file)
                break
    
    print(f"📄 分析文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 文件不存在: {test_file}")
        return
    
    # 1. 详细分析文件内容
    print(f"\n🔍 步骤1: 详细分析文件内容...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 文件大小: {len(content)} 字符")
        
        # 显示文件前500字符
        print(f"\n📄 文件开头内容:")
        print("-" * 50)
        print(content[:500])
        print("-" * 50)
        
        # 2. 查找所有可能的贴图引用
        print(f"\n🔍 步骤2: 查找贴图引用...")
        
        # 更全面的贴图引用模式
        texture_patterns = [
            (r'texture:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})', "标准贴图引用"),
            (r'texture:\s*{fileID:\s*0,\s*guid:\s*([a-f0-9]{32})', "fileID为0的贴图引用"),
            (r'texture:\s*{guid:\s*([a-f0-9]{32})', "只有guid的贴图引用"),
            (r'texture:\s*{.*?guid:\s*([a-f0-9]{32})', "任意内容的贴图引用"),
            (r'm_Texture:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})', "m_Texture引用"),
            (r'm_Texture:\s*{guid:\s*([a-f0-9]{32})', "m_Texture只有guid"),
            (r'texture2D:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})', "texture2D引用"),
            (r'texture2D:\s*{guid:\s*([a-f0-9]{32})', "texture2D只有guid"),
        ]
        
        found_textures = {}
        for pattern, desc in texture_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                guid = match.lower()
                if guid not in found_textures:
                    found_textures[guid] = []
                found_textures[guid].append(desc)
                print(f"🔑 找到贴图GUID: {guid} (通过: {desc})")
        
        print(f"\n📊 总共找到 {len(found_textures)} 个贴图GUID")
        
        # 3. 查找所有GUID（包括非贴图的）
        print(f"\n🔍 步骤3: 查找所有GUID...")
        
        all_guid_patterns = [
            (r'guid:\s*([a-f0-9]{32})', "标准guid"),
            (r'm_GUID:\s*([a-f0-9]{32})', "m_GUID"),
            (r'([a-f0-9]{32})', "通用32位十六进制"),
        ]
        
        all_guids = {}
        for pattern, desc in all_guid_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                guid = match.lower()
                if guid not in all_guids:
                    all_guids[guid] = []
                all_guids[guid].append(desc)
        
        print(f"📊 总共找到 {len(all_guids)} 个所有类型的GUID")
        
        # 显示所有GUID
        for guid, sources in all_guids.items():
            is_texture = "🎨 贴图" if guid in found_textures else "📄 其他"
            print(f"   {is_texture} {guid} (通过: {', '.join(sources)})")
        
        # 4. 测试YAML解析
        print(f"\n🔍 步骤4: 测试YAML解析...")
        yaml_guids = analyzer._parse_yaml_asset(content, test_file)
        print(f"✅ YAML解析找到 {len(yaml_guids)} 个GUID")
        
        # 检查贴图GUID是否被YAML解析器找到
        texture_guids_found = 0
        for guid in found_textures:
            if guid in yaml_guids:
                texture_guids_found += 1
                print(f"   ✅ 贴图GUID {guid} 被YAML解析器找到")
            else:
                print(f"   ❌ 贴图GUID {guid} 未被YAML解析器找到")
        
        print(f"\n📊 YAML解析结果: {texture_guids_found}/{len(found_textures)} 个贴图GUID被找到")
        
        # 5. 扫描SVN仓库
        print(f"\n🔍 步骤5: 扫描SVN仓库...")
        svn_root = analyzer._find_svn_root_from_files([test_file])
        if svn_root:
            print(f"✅ 找到SVN根目录: {svn_root}")
            
            guid_map = {}
            analyzer._scan_directory_for_guids(svn_root, guid_map)
            print(f"✅ 扫描完成，找到 {len(guid_map)} 个GUID映射")
            
            # 检查贴图GUID是否在SVN中找到
            texture_guids_in_svn = 0
            for guid in found_textures:
                if guid in guid_map:
                    texture_guids_in_svn += 1
                    file_path = guid_map[guid]
                    file_ext = os.path.splitext(file_path)[1].lower()
                    print(f"   ✅ 贴图GUID {guid} -> {os.path.basename(file_path)} ({file_ext})")
                    if file_ext == '.png':
                        print(f"      🎉 这是PNG文件!")
                    elif file_ext == '.meta':
                        resource_file = file_path[:-5]
                        if os.path.exists(resource_file):
                            resource_ext = os.path.splitext(resource_file)[1].lower()
                            if resource_ext == '.png':
                                print(f"      🎉 对应的资源文件是PNG!")
                else:
                    print(f"   ❌ 贴图GUID {guid} 在SVN中未找到")
            
            print(f"\n📊 SVN匹配结果: {texture_guids_in_svn}/{len(found_textures)} 个贴图GUID在SVN中找到")
            
        else:
            print(f"❌ 未找到SVN根目录")
            return
        
        # 6. 测试完整依赖分析
        print(f"\n🔍 步骤6: 测试完整依赖分析...")
        result = analyzer.find_dependency_files([test_file])
        
        print(f"\n📊 完整分析结果:")
        print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
        print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
        print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
        
        # 检查PNG文件
        png_files = [f for f in result['dependency_files'] if f.lower().endswith('.png')]
        if png_files:
            print(f"\n🎉 找到 {len(png_files)} 个PNG文件:")
            for png_file in png_files:
                print(f"   - {os.path.basename(png_file)}")
        else:
            print(f"\n❌ 没有找到PNG文件")
        
        # 检查缺失依赖
        if result['missing_dependencies']:
            print(f"\n❌ 缺失的依赖:")
            for missing in result['missing_dependencies']:
                print(f"   GUID: {missing['guid']} 被文件: {os.path.basename(missing['referenced_by'])} 引用")
                if missing['guid'] in found_textures:
                    print(f"      ⚠️ 这是一个贴图GUID!")
        
        # 7. 提供建议
        print(f"\n💡 分析和建议:")
        if len(found_textures) == 0:
            print("   - 材质文件中没有找到贴图引用")
            print("   - 可能这个材质没有使用贴图")
        elif texture_guids_found < len(found_textures):
            print("   - 部分贴图GUID没有被YAML解析器找到")
            print("   - 可能需要改进GUID解析模式")
        elif texture_guids_in_svn < len(found_textures):
            print("   - 部分贴图GUID在SVN仓库中未找到")
            print("   - 可能贴图文件不在SVN仓库中")
        elif len(png_files) == 0:
            print("   - 找到了贴图GUID但没有PNG文件")
            print("   - 可能贴图文件不是PNG格式")
        else:
            print("   - 贴图依赖分析正常")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_material_textures() 