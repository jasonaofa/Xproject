#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def debug_png_reference():
    """详细诊断PNG文件引用问题"""
    
    print("🔍 详细诊断PNG文件引用问题")
    print("=" * 60)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试文件路径（请根据实际情况修改）
    test_file = r"C:\meishufenzhi\Assets\prefab\particles\public\Material\mach_boss_dizzy.mat"
    
    print(f"📄 测试文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        print("💡 请修改脚本中的文件路径为实际存在的文件")
        return
    
    # 1. 详细分析文件内容
    print(f"\n🔍 步骤1: 详细分析文件内容...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 文件大小: {len(content)} 字符")
        
        # 查找所有可能的GUID引用
        print(f"\n🔍 查找所有GUID引用...")
        
        # 更全面的GUID模式
        guid_patterns = [
            (r'"m_GUID":\s*"([a-f0-9]{32})"', "JSON格式m_GUID"),
            (r'guid:\s*([a-f0-9]{32})', "YAML格式guid"),
            (r'm_GUID:\s*([a-f0-9]{32})', "YAML格式m_GUID"),
            (r'texture:\s*{fileID:\s*\d+,\s*guid:\s*([a-f0-9]{32})', "材质贴图引用1"),
            (r'texture:\s*{fileID:\s*0,\s*guid:\s*([a-f0-9]{32})', "材质贴图引用2"),
            (r'texture:\s*{guid:\s*([a-f0-9]{32})', "材质贴图引用3"),
            (r'([a-f0-9]{32})', "通用32位十六进制"),
        ]
        
        all_guids = {}
        for pattern, desc in guid_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                guid = match.lower()
                if guid not in all_guids:
                    all_guids[guid] = []
                all_guids[guid].append(desc)
                print(f"🔑 找到GUID: {guid} (通过: {desc})")
        
        print(f"\n📊 总共找到 {len(all_guids)} 个唯一GUID")
        
        # 2. 检查目标GUID
        target_guid = "c7c65a3a6a7673649a64d18d99fd0f8f"
        if target_guid in all_guids:
            print(f"\n🎯 目标GUID已找到: {target_guid}")
            print(f"   检测方式: {all_guids[target_guid]}")
            
            # 显示目标GUID的上下文
            guid_index = content.lower().find(target_guid)
            if guid_index != -1:
                start = max(0, guid_index - 100)
                end = min(len(content), guid_index + 100)
                context = content[start:end]
                print(f"   上下文:")
                print(f"   {context}")
        else:
            print(f"\n❌ 目标GUID未找到: {target_guid}")
        
        # 3. 扫描SVN仓库
        print(f"\n🔍 步骤2: 扫描SVN仓库...")
        svn_root = analyzer._find_svn_root_from_files([test_file])
        if svn_root:
            print(f"✅ 找到SVN根目录: {svn_root}")
            
            # 扫描GUID映射
            guid_map = {}
            analyzer._scan_directory_for_guids(svn_root, guid_map)
            print(f"✅ 扫描完成，找到 {len(guid_map)} 个GUID映射")
            
            # 检查目标GUID是否在映射中
            if target_guid in guid_map:
                print(f"🎉 目标GUID在SVN仓库中找到!")
                print(f"   对应文件: {guid_map[target_guid]}")
                
                # 检查文件是否存在
                if os.path.exists(guid_map[target_guid]):
                    print(f"✅ 文件存在")
                    
                    # 检查文件类型
                    file_ext = os.path.splitext(guid_map[target_guid])[1].lower()
                    print(f"   文件类型: {file_ext}")
                    
                    if file_ext == '.png':
                        print(f"🎉 这是一个PNG文件!")
                    elif file_ext == '.meta':
                        # 检查对应的资源文件
                        resource_file = guid_map[target_guid][:-5]
                        if os.path.exists(resource_file):
                            resource_ext = os.path.splitext(resource_file)[1].lower()
                            print(f"   对应的资源文件: {resource_file}")
                            print(f"   资源文件类型: {resource_ext}")
                            if resource_ext == '.png':
                                print(f"🎉 对应的资源文件是PNG!")
                else:
                    print(f"❌ 文件不存在: {guid_map[target_guid]}")
            else:
                print(f"❌ 目标GUID在SVN仓库中未找到")
                
                # 搜索包含此GUID的meta文件
                print(f"\n🔍 在SVN仓库中搜索包含目标GUID的文件...")
                found_files = search_guid_in_svn(svn_root, target_guid)
                if found_files:
                    print(f"✅ 找到包含目标GUID的文件:")
                    for file_path in found_files:
                        print(f"   - {file_path}")
                else:
                    print(f"❌ 在SVN仓库中未找到包含目标GUID的文件")
        else:
            print(f"❌ 未找到SVN根目录")
        
        # 4. 测试完整的依赖分析
        print(f"\n🔍 步骤3: 测试完整依赖分析...")
        result = analyzer.find_dependency_files([test_file])
        
        print(f"\n📊 完整分析结果:")
        print(f"   原始文件: {result['analysis_stats']['total_original']}")
        print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
        print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
        print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
        
        # 检查依赖文件列表
        if result['dependency_files']:
            print(f"\n📋 找到的依赖文件:")
            for dep_file in result['dependency_files']:
                file_ext = os.path.splitext(dep_file)[1].lower()
                print(f"   - {os.path.basename(dep_file)} ({file_ext})")
                if file_ext == '.png':
                    print(f"     🎉 这是PNG文件!")
        else:
            print(f"\n❌ 没有找到依赖文件")
        
        # 检查缺失依赖
        if result['missing_dependencies']:
            print(f"\n❌ 缺失的依赖:")
            for missing in result['missing_dependencies']:
                print(f"   GUID: {missing['guid']} 被文件: {os.path.basename(missing['referenced_by'])} 引用")
                if missing['guid'] == target_guid:
                    print(f"   ⚠️ 这是我们要找的目标GUID!")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

def search_guid_in_svn(svn_root, target_guid):
    """在SVN仓库中搜索包含指定GUID的文件"""
    found_files = []
    
    try:
        for root, dirs, files in os.walk(svn_root):
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
    debug_png_reference() 