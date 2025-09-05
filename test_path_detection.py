#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

def test_path_detection():
    """测试包含CommonResource的完整路径结构检测"""
    
    # 模拟用户提到的路径结构
    test_paths = [
        'C:/svn/CommonResource/Assets/Resources/minigame/entity/140489/Timeline/Material/tuowei.png',
        'C:/upload/CommonResource/Assets/entity/100001/Model/test.mat',  
        'D:/project/Assets/entity/100002/prefab/item.mat',
        'E:/temp/some/path/Assets/Resources/minigame/entity/100003/Timeline/shader/material.mat'
    ]
    
    print('🔍 检测包含CommonResource的完整路径结构：')
    print('=' * 80)
    
    for path in test_paths:
        print(f'📁 原始路径: {path}')
        
        # 模拟当前的entity检测逻辑
        normalized_path = os.path.normpath(path)
        path_parts = normalized_path.split(os.sep)
        
        # 查找entity目录
        entity_index = -1
        for i, part in enumerate(path_parts):
            if part.lower() == 'entity':
                entity_index = i
                break
        
        if entity_index == -1:
            print('  ❌ 不在entity目录下，会被跳过')
        else:
            print(f'  ✅ 找到entity目录 (索引: {entity_index})')
            
            # 显示entity前的路径部分
            before_entity = path_parts[:entity_index]
            print(f'  📂 entity前的路径: {os.sep.join(before_entity)}')
            
            # 显示entity后的路径部分
            after_entity = path_parts[entity_index + 1:]
            print(f'  📂 entity后的路径: {os.sep.join(after_entity)}')
            
            # 检查是否包含CommonResource
            has_common_resource = any(part == 'CommonResource' for part in before_entity)
            if has_common_resource:
                print('  🏢 包含CommonResource目录')
            else:
                print('  📁 不包含CommonResource目录')
            
            # 检查是否包含完整的Assets/Resources/minigame路径
            path_str = os.sep.join(path_parts).lower()  
            if 'assets' in path_str and 'resources' in path_str and 'minigame' in path_str:
                print('  📦 包含完整的Assets/Resources/minigame路径结构')
            elif 'assets' in path_str:
                print('  📦 包含Assets路径')
            
            # 检查Timeline
            has_timeline = any(part.lower() == 'timeline' for part in after_entity)
            if has_timeline:
                print('  🎬 包含Timeline文件夹')
        
        print()

if __name__ == "__main__":
    test_path_detection() 