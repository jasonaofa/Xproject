#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Assets根目录映射方案
"""

import json
import re
import os

def load_path_mapping_config():
    """加载路径映射配置"""
    try:
        with open("path_mapping_config.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return None

def apply_path_mapping(assets_path: str, mapping_rules: dict) -> str:
    """应用路径映射规则"""
    print(f"🔄 原始路径: {assets_path}")
    
    # 按优先级排序规则
    sorted_rules = sorted(
        [(rule_id, rule) for rule_id, rule in mapping_rules.items() if rule.get('enabled', True)],
        key=lambda x: x[1].get('priority', 999)
    )
    
    for rule_id, rule in sorted_rules:
        try:
            source_pattern = rule['source_pattern']
            target_pattern = rule['target_pattern']
            
            if re.match(source_pattern, assets_path):
                # 应用映射规则
                match = re.match(source_pattern, assets_path)
                if match:
                    # 获取匹配的部分长度
                    matched_part = match.group(0)
                    remaining_path = assets_path[len(matched_part):].lstrip('\\/')
                    
                    # 构建映射后的路径
                    if remaining_path:
                        mapped_path = target_pattern + remaining_path
                    else:
                        mapped_path = target_pattern.rstrip('\\')
                else:
                    # 兜底：使用简单替换
                    mapped_path = re.sub(source_pattern, target_pattern, assets_path)
                
                print(f"   ✅ 匹配规则: {rule['name']}")
                print(f"   🔄 映射结果: {mapped_path}")
                return mapped_path
                
        except Exception as e:
            print(f"   ❌ 规则 {rule_id} 处理失败: {e}")
            continue
    
    print(f"   ⚠️ 没有匹配的映射规则")
    return assets_path

def test_assets_root_mapping():
    """测试Assets根目录映射方案"""
    print("🧪 测试Assets根目录映射方案")
    print("=" * 60)
    
    # 方案1: 只映射SVN路径（排除已经是Git格式的路径）
    test_rules_1 = {
        "assets_to_minigame": {
            "name": "Assets根目录映射（排除Git路径）",
            "description": "将Assets目录映射到Assets/Resources/minigame，但排除已经是Git格式的路径",
            "enabled": True,
            "source_pattern": r"^Assets[\\\/](?!Resources[\\\/]minigame[\\\/])",
            "target_pattern": "Assets\\Resources\\minigame\\",
            "priority": 1
        }
    }
    
    # 方案2: 更精确的映射（只映射直接子目录）
    test_rules_2 = {
        "assets_to_minigame": {
            "name": "Assets直接子目录映射",
            "description": "将Assets的直接子目录映射到Assets/Resources/minigame",
            "enabled": True,
            "source_pattern": r"^Assets[\\\/]([^\\\/]+)[\\\/]",
            "target_pattern": "Assets\\Resources\\minigame\\",
            "priority": 1
        }
    }
    
    print("📋 测试映射规则方案1:")
    for rule_id, rule in test_rules_1.items():
        if rule.get('enabled', True):
            print(f"   - {rule['name']}: {rule['source_pattern']} -> {rule['target_pattern']}")
    
    print("\n" + "=" * 60)
    
    # 测试各种路径
    test_paths = [
        "Assets\\prefab\\particles\\public\\Texture\\mask_wl_17.png",
        "Assets\\entity\\100060\\model.fbx",
        "Assets\\ui\\main\\button.png",
        "Assets\\audio\\bgm\\music.mp3",
        "Assets\\texture\\character\\skin.png",
        "Assets\\Resources\\minigame\\prefab\\particles\\public\\Texture\\mask_wl_17.png"
    ]
    
    print("🔍 测试方案1:")
    results_1 = []
    for i, path in enumerate(test_paths, 1):
        print(f"\n🔍 测试路径 {i}:")
        mapped_path = apply_path_mapping(path, test_rules_1)
        results_1.append((path, mapped_path))
        
        if mapped_path == path:
            print(f"   ❌ 没有映射规则匹配此路径")
        else:
            print(f"   ✅ 路径被映射为: {mapped_path}")
    
    print("\n" + "=" * 60)
    print("📊 方案1分析结果:")
    
    # 检查两个关键路径是否会被认为是同一路径
    path1 = "Assets\\prefab\\particles\\public\\Texture\\mask_wl_17.png"
    path2 = "Assets\\Resources\\minigame\\prefab\\particles\\public\\Texture\\mask_wl_17.png"
    
    mapped1 = apply_path_mapping(path1, test_rules_1)
    mapped2 = apply_path_mapping(path2, test_rules_1)
    
    print(f"\n🔍 关键路径映射对比:")
    print(f"   SVN路径: {path1}")
    print(f"   映射结果: {mapped1}")
    print(f"   Git路径: {path2}")
    print(f"   映射结果: {mapped2}")
    
    if mapped1 == mapped2:
        print(f"   ✅ 两个路径会被认为是同一路径")
        print(f"   🎉 方案1成功！")
    else:
        print(f"   ❌ 两个路径仍被认为是不同路径")
        print(f"   💡 需要调整映射规则")
    
    # 测试方案2
    print(f"\n" + "=" * 60)
    print("🔍 测试方案2:")
    
    results_2 = []
    for i, path in enumerate(test_paths, 1):
        print(f"\n🔍 测试路径 {i}:")
        mapped_path = apply_path_mapping(path, test_rules_2)
        results_2.append((path, mapped_path))
        
        if mapped_path == path:
            print(f"   ❌ 没有映射规则匹配此路径")
        else:
            print(f"   ✅ 路径被映射为: {mapped_path}")
    
    print(f"\n" + "=" * 60)
    print("📊 方案2分析结果:")
    
    mapped1_2 = apply_path_mapping(path1, test_rules_2)
    mapped2_2 = apply_path_mapping(path2, test_rules_2)
    
    print(f"\n🔍 关键路径映射对比:")
    print(f"   SVN路径: {path1}")
    print(f"   映射结果: {mapped1_2}")
    print(f"   Git路径: {path2}")
    print(f"   映射结果: {mapped2_2}")
    
    if mapped1_2 == mapped2_2:
        print(f"   ✅ 两个路径会被认为是同一路径")
        print(f"   🎉 方案2成功！")
    else:
        print(f"   ❌ 两个路径仍被认为是不同路径")
        print(f"   💡 需要调整映射规则")

def test_existing_config():
    """测试当前配置文件"""
    print("\n" + "=" * 60)
    print("🔍 测试当前配置文件")
    
    config = load_path_mapping_config()
    if not config:
        print("❌ 无法加载配置")
        return
    
    mapping_rules = config.get('rules', {})
    
    print("📋 当前映射规则:")
    for rule_id, rule in mapping_rules.items():
        if rule.get('enabled', True):
            print(f"   - {rule['name']}: {rule['source_pattern']} -> {rule['target_pattern']}")
    
    # 测试prefab路径
    test_path = "Assets\\prefab\\particles\\public\\Texture\\mask_wl_17.png"
    print(f"\n🔍 测试prefab路径: {test_path}")
    mapped_path = apply_path_mapping(test_path, mapping_rules)
    
    if mapped_path == test_path:
        print(f"   ❌ 当前配置无法映射prefab路径")
    else:
        print(f"   ✅ 当前配置可以映射prefab路径: {mapped_path}")

if __name__ == "__main__":
    test_assets_root_mapping()
    test_existing_config() 