#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def quick_test_png():
    """快速测试PNG引用问题"""
    
    print("🔍 快速测试PNG引用问题")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试文件路径（请根据实际情况修改）
    test_file = r"C:\meishufenzhi\Assets\prefab\particles\public\Material\mach_boss_dizzy.mat"
    
    print(f"📄 测试文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    # 1. 直接测试YAML解析
    print(f"\n🔍 步骤1: 测试YAML解析...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        yaml_guids = analyzer._parse_yaml_asset(content, test_file)
        print(f"✅ YAML解析找到 {len(yaml_guids)} 个GUID")
        
        target_guid = "c7c65a3a6a7673649a64d18d99fd0f8f"
        if target_guid in yaml_guids:
            print(f"🎉 目标GUID已找到: {target_guid}")
        else:
            print(f"❌ 目标GUID未找到: {target_guid}")
            
            # 手动搜索
            if target_guid in content.lower():
                print(f"✅ 在文件内容中找到目标GUID")
            else:
                print(f"❌ 在文件内容中未找到目标GUID")
        
    except Exception as e:
        print(f"❌ YAML解析失败: {e}")
        return
    
    # 2. 测试SVN扫描
    print(f"\n🔍 步骤2: 测试SVN扫描...")
    svn_root = analyzer._find_svn_root_from_files([test_file])
    if svn_root:
        print(f"✅ 找到SVN根目录: {svn_root}")
        
        guid_map = {}
        analyzer._scan_directory_for_guids(svn_root, guid_map)
        print(f"✅ 扫描完成，找到 {len(guid_map)} 个GUID映射")
        
        if target_guid in guid_map:
            print(f"🎉 目标GUID在SVN中找到!")
            print(f"   对应文件: {guid_map[target_guid]}")
            
            # 检查文件类型
            file_ext = os.path.splitext(guid_map[target_guid])[1].lower()
            if file_ext == '.png':
                print(f"🎉 这是一个PNG文件!")
            elif file_ext == '.meta':
                resource_file = guid_map[target_guid][:-5]
                if os.path.exists(resource_file):
                    resource_ext = os.path.splitext(resource_file)[1].lower()
                    if resource_ext == '.png':
                        print(f"🎉 对应的资源文件是PNG!")
        else:
            print(f"❌ 目标GUID在SVN中未找到")
    else:
        print(f"❌ 未找到SVN根目录")
    
    # 3. 测试完整依赖分析
    print(f"\n🔍 步骤3: 测试完整依赖分析...")
    result = analyzer.find_dependency_files([test_file])
    
    print(f"\n📊 分析结果:")
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
            print(f"   GUID: {missing['guid']}")
            if missing['guid'] == target_guid:
                print(f"   ⚠️ 这是我们要找的目标GUID!")

if __name__ == "__main__":
    quick_test_png() 