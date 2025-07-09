#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_improved_texture_detection():
    """测试改进的贴图检测"""
    
    print("🔍 测试改进的贴图检测")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试材质文件路径（请根据实际情况修改）
    test_file = input("请输入材质文件路径 (例如: sanguang.mat): ").strip()
    
    if not test_file:
        print("❌ 未输入文件路径")
        return
    
    # 如果只输入了文件名，尝试在当前目录查找
    if not os.path.isabs(test_file):
        for root, dirs, files in os.walk('.'):
            if test_file in files:
                test_file = os.path.join(root, test_file)
                break
    
    print(f"📄 测试文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 文件不存在: {test_file}")
        return
    
    # 1. 测试改进的YAML解析
    print(f"\n🔍 步骤1: 测试改进的YAML解析...")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        yaml_guids = analyzer._parse_yaml_asset(content, test_file)
        print(f"✅ YAML解析找到 {len(yaml_guids)} 个GUID")
        
        # 显示找到的GUID
        for guid in yaml_guids:
            print(f"   - {guid}")
        
    except Exception as e:
        print(f"❌ YAML解析失败: {e}")
        return
    
    # 2. 测试完整依赖分析
    print(f"\n🔍 步骤2: 测试完整依赖分析...")
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
    
    # 检查其他图片格式
    image_extensions = ['.png', '.jpg', '.jpeg', '.tga', '.psd', '.tiff', '.bmp']
    image_files = [f for f in result['dependency_files'] 
                   if os.path.splitext(f)[1].lower() in image_extensions]
    
    if image_files:
        print(f"\n🎨 找到 {len(image_files)} 个图片文件:")
        for image_file in image_files:
            ext = os.path.splitext(image_file)[1].lower()
            print(f"   - {os.path.basename(image_file)} ({ext})")
    else:
        print(f"\n❌ 没有找到任何图片文件")
    
    # 检查缺失依赖
    if result['missing_dependencies']:
        print(f"\n❌ 缺失的依赖:")
        for missing in result['missing_dependencies']:
            print(f"   GUID: {missing['guid']} 被文件: {os.path.basename(missing['referenced_by'])} 引用")
    
    print(f"\n🎉 测试完成!")

if __name__ == "__main__":
    test_improved_texture_detection() 