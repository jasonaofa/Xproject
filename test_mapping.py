#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import GitSvnManager

def test_path_mapping():
    """测试路径映射功能"""
    print("🧪 开始测试路径映射功能...")
    
    # 创建GitSvnManager实例
    git_manager = GitSvnManager()
    
    # 测试路径
    test_paths = [
        'Assets/entity/140484/Particles/glow.png',
        'Assets/entity/100060/Materials/test.mat',
        'Assets/entity/200001/Textures/icon.png',
        'Assets/other/test.txt'
    ]
    
    print(f"📋 路径映射规则数量: {len(git_manager.path_mapping_rules)}")
    print(f"🔧 路径映射状态: {'启用' if git_manager.path_mapping_enabled else '禁用'}")
    print()
    
    for test_path in test_paths:
        print(f"🔍 测试路径: {test_path}")
        
        try:
            result = git_manager.apply_path_mapping(test_path)
            print(f"✅ 映射结果: {result}")
            
            if result != test_path:
                print(f"📝 路径已映射: {test_path} -> {result}")
            else:
                print(f"⚠️ 路径未映射: 使用原始路径")
                
        except Exception as e:
            print(f"❌ 映射失败: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_path_mapping() 