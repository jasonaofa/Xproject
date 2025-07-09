#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_png_dependency():
    """测试PNG依赖检测"""
    
    print("🔍 测试PNG依赖检测")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 请修改为您的实际文件路径
    test_file = input("请输入要测试的材质文件路径 (例如: C:\\path\\to\\your\\material.mat): ").strip()
    
    if not test_file:
        print("❌ 未输入文件路径")
        return
    
    print(f"📄 测试文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    # 1. 分析文件内容
    print(f"\n🔍 步骤1: 分析文件内容...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 文件大小: {len(content)} 字符")
        
        # 查找所有GUID
        all_guids = set()
        guid_patterns = [
            r'guid:\s*([a-f0-9]{32})',
            r'm_GUID:\s*([a-f0-9]{32})',
            r'texture:\s*{.*?guid:\s*([a-f0-9]{32})',
            r'([a-f0-9]{32})',
        ]
        
        for pattern in guid_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                guid = match.lower()
                all_guids.add(guid)
        
        print(f"📊 找到 {len(all_guids)} 个唯一GUID")
        
        # 显示前10个GUID
        for i, guid in enumerate(list(all_guids)[:10]):
            print(f"   {i+1}. {guid}")
        
        if len(all_guids) > 10:
            print(f"   ... 还有 {len(all_guids) - 10} 个GUID")
        
    except Exception as e:
        print(f"❌ 文件读取失败: {e}")
        return
    
    # 2. 测试YAML解析
    print(f"\n🔍 步骤2: 测试YAML解析...")
    try:
        yaml_guids = analyzer._parse_yaml_asset(content, test_file)
        print(f"✅ YAML解析找到 {len(yaml_guids)} 个GUID")
        
        # 显示解析到的GUID
        for guid in yaml_guids:
            print(f"   - {guid}")
        
    except Exception as e:
        print(f"❌ YAML解析失败: {e}")
        return
    
    # 3. 测试SVN扫描
    print(f"\n🔍 步骤3: 测试SVN扫描...")
    svn_root = analyzer._find_svn_root_from_files([test_file])
    if svn_root:
        print(f"✅ 找到SVN根目录: {svn_root}")
        
        guid_map = {}
        analyzer._scan_directory_for_guids(svn_root, guid_map)
        print(f"✅ 扫描完成，找到 {len(guid_map)} 个GUID映射")
        
        # 检查YAML解析到的GUID是否在SVN中找到
        found_in_svn = 0
        for guid in yaml_guids:
            if guid in guid_map:
                found_in_svn += 1
                file_path = guid_map[guid]
                file_ext = os.path.splitext(file_path)[1].lower()
                print(f"   ✅ {guid} -> {os.path.basename(file_path)} ({file_ext})")
                if file_ext == '.png':
                    print(f"      🎉 这是PNG文件!")
            else:
                print(f"   ❌ {guid} -> 未找到")
        
        print(f"\n📊 SVN匹配结果: {found_in_svn}/{len(yaml_guids)} 个GUID在SVN中找到")
        
    else:
        print(f"❌ 未找到SVN根目录")
        return
    
    # 4. 测试完整依赖分析
    print(f"\n🔍 步骤4: 测试完整依赖分析...")
    result = analyzer.find_dependency_files([test_file])
    
    print(f"\n📊 完整分析结果:")
    print(f"   原始文件: {result['analysis_stats']['total_original']}")
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
    
    print(f"\n🎉 测试完成!")

if __name__ == "__main__":
    test_png_dependency() 