#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_json_guid_parsing():
    """测试JSON格式的GUID解析"""
    
    print("🔍 测试JSON格式的GUID解析")
    print("=" * 50)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 测试JSON内容（模拟您提供的格式）
    test_json_content = '''
    {
        "first": {
            "m_GUID": "8964d7b89a36a244ab36a6aaca1bb016",
            "m_PersistentID": 1
        },
        "second": 22
    }
    '''
    
    print(f"📄 测试JSON内容:")
    print(test_json_content)
    
    # 1. 测试JSON解析
    print(f"\n🔍 步骤1: 测试JSON解析...")
    try:
        # 创建临时文件来测试
        temp_file = "temp_test.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(test_json_content)
        
        # 测试解析
        dependencies = analyzer.parse_editor_asset(temp_file)
        print(f"✅ JSON解析找到 {len(dependencies)} 个GUID")
        
        # 检查目标GUID
        target_guid = "8964d7b89a36a244ab36a6aaca1bb016"
        if target_guid in dependencies:
            print(f"🎉 目标GUID已找到: {target_guid}")
        else:
            print(f"❌ 目标GUID未找到: {target_guid}")
        
        # 显示所有找到的GUID
        for guid in dependencies:
            print(f"   - {guid}")
        
        # 清理临时文件
        os.remove(temp_file)
        
    except Exception as e:
        print(f"❌ JSON解析失败: {e}")
        return
    
    # 2. 测试手动正则表达式
    print(f"\n🔍 步骤2: 测试手动正则表达式...")
    
    # 测试各种JSON GUID模式
    json_patterns = [
        (r'"m_GUID":\s*"([a-f0-9]{32})"', "标准m_GUID格式"),
        (r'"guid":\s*"([a-f0-9]{32})"', "标准guid格式"),
        (r'"GUID":\s*"([a-f0-9]{32})"', "大写GUID格式"),
        (r'"texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"', "贴图引用"),
        (r'"texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"', "贴图m_GUID引用"),
    ]
    
    for pattern, desc in json_patterns:
        matches = re.findall(pattern, test_json_content, re.IGNORECASE)
        if matches:
            print(f"   ✅ {desc}: 找到 {len(matches)} 个匹配")
            for match in matches:
                print(f"      - {match}")
        else:
            print(f"   ❌ {desc}: 未找到匹配")
    
    # 3. 测试完整的依赖分析流程
    print(f"\n🔍 步骤3: 测试完整的依赖分析流程...")
    
    # 创建包含目标GUID的测试文件
    test_file_content = '''
    {
        "textureReferences": [
            {
                "first": {
                    "m_GUID": "8964d7b89a36a244ab36a6aaca1bb016",
                    "m_PersistentID": 1
                },
                "second": 22
            }
        ]
    }
    '''
    
    test_file_path = "test_material.json"
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_file_content)
    
    try:
        # 测试完整依赖分析
        result = analyzer.find_dependency_files([test_file_path])
        
        print(f"\n📊 完整分析结果:")
        print(f"   原始文件: {result['analysis_stats']['total_original']}")
        print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
        print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
        print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
        
        # 检查缺失依赖
        if result['missing_dependencies']:
            print(f"\n❌ 缺失的依赖:")
            for missing in result['missing_dependencies']:
                print(f"   GUID: {missing['guid']} 被文件: {os.path.basename(missing['referenced_by'])} 引用")
                if missing['guid'] == target_guid:
                    print(f"      ⚠️ 这是我们要找的目标GUID!")
        else:
            print(f"\n✅ 没有缺失的依赖")
        
        # 清理测试文件
        os.remove(test_file_path)
        
    except Exception as e:
        print(f"❌ 完整分析失败: {e}")
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    print(f"\n🎉 测试完成!")

if __name__ == "__main__":
    test_json_guid_parsing() 