#!/usr/bin/env python
# -*- coding: utf-8 -*-

from art_resource_manager import GitSvnManager

def test_path_mapping():
    print("🧪 开始测试路径映射功能...")
    
    git_manager = GitSvnManager()
    
    # 测试用例
    test_cases = [
        "Assets\\entity",
        "Assets\\entity\\100060\\file.prefab",
        "Assets\\ui\\main_menu.prefab",
        "Assets\\audio\\bgm.mp3",
        "Assets\\texture\\icon.png",
        "G:\\Svn_repo\\MiniProject_Art_NewPrefab\\Assets\\entity"
    ]
    
    for i, test_path in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {test_path}")
        print(f"{'='*60}")
        
        result = git_manager.test_path_mapping(test_path)
        
        print(f"最终结果: {result}")
        print(f"映射成功: {'✅' if result != test_path else '❌'}")

if __name__ == "__main__":
    test_path_mapping() 