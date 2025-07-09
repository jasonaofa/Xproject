#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证meta文件检测修复的简单脚本
"""

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def verify_meta_detection():
    """验证meta文件检测功能"""
    
    print("🔍 验证meta文件检测修复")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 检查当前目录的文件
    current_files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.endswith('.py') and not f.endswith('.md')]
    
    if not current_files:
        print("❌ 当前目录没有找到测试文件")
        return False
    
    # 选择第一个文件进行测试
    test_file = current_files[0]
    print(f"📄 使用文件进行测试: {test_file}")
    
    # 检查对应的meta文件
    meta_file = test_file + ".meta"
    if os.path.exists(meta_file):
        print(f"✅ 找到对应的meta文件: {meta_file}")
    else:
        print(f"⚠️ 没有找到对应的meta文件: {meta_file}")
        return False
    
    # 执行依赖分析
    print(f"\n🔍 执行依赖分析...")
    result = analyzer.find_dependency_files([test_file])
    
    # 检查结果
    print(f"\n📊 分析结果:")
    print(f"   原始文件: {result['analysis_stats']['total_original']}")
    print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
    print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
    
    # 检查meta文件是否被包含
    if meta_file in result['meta_files']:
        print(f"\n✅ 修复成功！{meta_file} 已被正确包含在结果中")
        return True
    else:
        print(f"\n❌ 修复失败！{meta_file} 未被包含在结果中")
        return False

if __name__ == "__main__":
    success = verify_meta_detection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 验证通过！meta文件检测修复有效。")
    else:
        print("⚠️ 验证失败！需要进一步检查。") 