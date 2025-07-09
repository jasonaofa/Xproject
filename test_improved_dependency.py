#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_improved_dependency_analysis():
    """测试改进后的依赖分析功能"""
    
    print("🔍 测试改进后的依赖分析功能")
    print("=" * 60)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试文件路径（请根据实际情况修改）
    test_file = r"C:\meishufenzhi\Assets\prefab\particles\public\Material\mach_boss_dizzy.mat"
    
    print(f"📄 测试文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return False
    
    # 测试SVN根目录查找
    print(f"\n🔍 测试SVN根目录查找...")
    svn_root = analyzer._find_svn_root_from_files([test_file])
    if svn_root:
        print(f"✅ 找到SVN根目录: {svn_root}")
    else:
        print(f"❌ 未找到SVN根目录")
        return False
    
    # 测试GUID映射扫描
    print(f"\n🔍 测试GUID映射扫描...")
    guid_map = {}
    analyzer._scan_directory_for_guids(svn_root, guid_map)
    print(f"✅ 扫描完成，找到 {len(guid_map)} 个GUID映射")
    
    # 测试材质文件解析
    print(f"\n🔍 测试材质文件解析...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 测试YAML解析
        yaml_guids = analyzer._parse_yaml_asset(content, test_file)
        print(f"✅ YAML解析找到 {len(yaml_guids)} 个GUID:")
        for guid in yaml_guids:
            print(f"   - {guid}")
        
        # 检查是否找到目标GUID
        target_guid = "c7c65a3a6a7673649a64d18d99fd0f8f"
        if target_guid in yaml_guids:
            print(f"✅ 找到目标GUID: {target_guid}")
        else:
            print(f"❌ 未找到目标GUID: {target_guid}")
            
            # 手动搜索目标GUID
            print(f"🔍 手动搜索目标GUID...")
            if target_guid in content.lower():
                print(f"✅ 在文件内容中找到目标GUID")
                # 显示上下文
                guid_index = content.lower().find(target_guid)
                start = max(0, guid_index - 50)
                end = min(len(content), guid_index + 50)
                context = content[start:end]
                print(f"   上下文: {context}")
            else:
                print(f"❌ 在文件内容中未找到目标GUID")
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return False
    
    # 测试完整依赖分析
    print(f"\n🔍 测试完整依赖分析...")
    result = analyzer.find_dependency_files([test_file])
    
    print(f"\n📊 完整分析结果:")
    print(f"   原始文件: {result['analysis_stats']['total_original']}")
    print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
    print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
    print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
    
    if result['missing_dependencies']:
        print(f"\n❌ 缺失的依赖:")
        for missing in result['missing_dependencies']:
            print(f"   GUID: {missing['guid']} 被文件: {os.path.basename(missing['referenced_by'])} 引用")
            if missing['guid'] == target_guid:
                print(f"   ⚠️ 这是我们要找的目标GUID!")
    else:
        print(f"\n✅ 没有缺失的依赖")
    
    return True

if __name__ == "__main__":
    success = test_improved_dependency_analysis()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 改进后的依赖分析功能测试完成")
    else:
        print("⚠️ 测试过程中遇到问题") 