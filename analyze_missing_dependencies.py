#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def analyze_missing_dependency():
    """分析缺失依赖的问题"""
    
    print("🔍 分析缺失依赖问题")
    print("=" * 60)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试文件路径（请根据实际情况修改）
    test_file = r"C:\meishufenzhi\Assets\prefab\particles\public\Material\mach_boss_dizzy.mat"
    svn_root = r"C:\meishufenzhi"  # SVN仓库根目录
    
    print(f"📄 测试文件: {test_file}")
    print(f"📁 SVN根目录: {svn_root}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    # 1. 分析文件内容，提取所有GUID
    print(f"\n🔍 步骤1: 分析文件内容...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 文件大小: {len(content)} 字符")
        print(f"📄 文件前500字符:")
        print("-" * 50)
        print(content[:500])
        print("-" * 50)
        
        # 提取所有可能的GUID
        all_guids = set()
        
        # 标准GUID模式
        guid_patterns = [
            r'"m_GUID":\s*"([a-f0-9]{32})"',  # JSON格式
            r'guid:\s*([a-f0-9]{32})',        # YAML格式
            r'm_GUID:\s*([a-f0-9]{32})',      # YAML格式
            r'([a-f0-9]{32})',                # 通用32位十六进制
        ]
        
        for pattern in guid_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                guid = match.lower()
                all_guids.add(guid)
                print(f"🔑 找到GUID: {guid}")
        
        print(f"\n📊 总共找到 {len(all_guids)} 个GUID")
        
        # 2. 扫描SVN仓库，建立GUID映射
        print(f"\n🔍 步骤2: 扫描SVN仓库...")
        guid_to_file_map = {}
        analyzer._scan_directory_for_guids(svn_root, guid_to_file_map)
        
        print(f"📊 扫描完成，找到 {len(guid_to_file_map)} 个GUID映射")
        
        # 3. 检查缺失的GUID
        print(f"\n🔍 步骤3: 检查缺失的GUID...")
        missing_guids = []
        found_guids = []
        
        for guid in all_guids:
            if guid in guid_to_file_map:
                found_guids.append(guid)
                print(f"✅ 找到GUID {guid} -> {guid_to_file_map[guid]}")
            else:
                missing_guids.append(guid)
                print(f"❌ 缺失GUID {guid}")
        
        print(f"\n📊 统计结果:")
        print(f"   总GUID数: {len(all_guids)}")
        print(f"   找到的GUID: {len(found_guids)}")
        print(f"   缺失的GUID: {len(missing_guids)}")
        
        # 4. 分析缺失GUID的可能原因
        if missing_guids:
            print(f"\n🔍 步骤4: 分析缺失原因...")
            for guid in missing_guids:
                print(f"\n🔍 分析缺失GUID: {guid}")
                
                # 检查是否是内置资源
                if guid.startswith('00000000000000'):
                    print(f"   ℹ️ 这是Unity内置资源GUID")
                    continue
                
                # 检查是否是常见着色器
                if guid in analyzer.common_shader_guids:
                    print(f"   ℹ️ 这是常见着色器GUID: {analyzer.common_shader_guids[guid]}")
                    continue
                
                # 尝试在SVN仓库中搜索这个GUID
                print(f"   🔍 在SVN仓库中搜索GUID: {guid}")
                found_files = search_guid_in_directory(svn_root, guid)
                
                if found_files:
                    print(f"   ✅ 找到包含此GUID的文件:")
                    for file_path in found_files[:5]:  # 只显示前5个
                        print(f"      - {file_path}")
                    if len(found_files) > 5:
                        print(f"      ... 还有 {len(found_files) - 5} 个文件")
                else:
                    print(f"   ❌ 在SVN仓库中未找到此GUID")
        
        # 5. 测试完整的依赖分析
        print(f"\n🔍 步骤5: 测试完整依赖分析...")
        result = analyzer.find_dependency_files([test_file], [svn_root])
        
        print(f"\n📊 完整分析结果:")
        print(f"   原始文件: {result['analysis_stats']['total_original']}")
        print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
        print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
        print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
        
        if result['missing_dependencies']:
            print(f"\n❌ 缺失的依赖:")
            for missing in result['missing_dependencies']:
                print(f"   GUID: {missing['guid']} 被文件: {os.path.basename(missing['referenced_by'])} 引用")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

def search_guid_in_directory(directory, target_guid):
    """在目录中搜索包含指定GUID的文件"""
    found_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.meta'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if target_guid.lower() in content.lower():
                                found_files.append(file_path)
                    except:
                        continue
    except Exception as e:
        print(f"搜索GUID时出错: {e}")
    
    return found_files

if __name__ == "__main__":
    analyze_missing_dependency() 