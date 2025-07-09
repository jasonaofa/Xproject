#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_body_prefab_meta_detection():
    """测试 body.prefab 的 meta 文件检测"""
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 模拟测试文件路径（请根据实际情况修改）
    test_file = "body.prefab"  # 假设这个文件存在
    
    print("🔍 测试 body.prefab 的 meta 文件检测")
    print("=" * 50)
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    # 检查对应的 meta 文件是否存在
    meta_file = test_file + ".meta"
    if os.path.exists(meta_file):
        print(f"✅ Meta文件存在: {meta_file}")
        
        # 解析 meta 文件获取 GUID
        guid = analyzer.parse_meta_file(meta_file)
        if guid:
            print(f"✅ 解析到GUID: {guid}")
        else:
            print(f"❌ 无法解析GUID")
    else:
        print(f"❌ Meta文件不存在: {meta_file}")
    
    # 测试依赖分析
    print("\n🔍 测试依赖分析...")
    result = analyzer.find_dependency_files([test_file])
    
    print(f"\n📊 分析结果:")
    print(f"   原始文件: {result['analysis_stats']['total_original']}")
    print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
    print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
    print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
    
    print(f"\n📁 找到的meta文件:")
    for meta_file in result['meta_files']:
        print(f"   - {meta_file}")
    
    print(f"\n📁 找到的依赖文件:")
    for dep_file in result['dependency_files']:
        print(f"   - {dep_file}")
    
    # 检查原始文件的 meta 是否被包含
    expected_meta = test_file + ".meta"
    if expected_meta in result['meta_files']:
        print(f"\n✅ 原始文件的meta文件已正确包含: {expected_meta}")
    else:
        print(f"\n❌ 原始文件的meta文件未被包含: {expected_meta}")
        print("这是问题所在！")

if __name__ == "__main__":
    test_body_prefab_meta_detection() 