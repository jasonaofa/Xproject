#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试prefab路径映射
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

def test_prefab_paths():
    """测试prefab相关路径"""
    print("🧪 测试prefab路径映射")
    print("=" * 60)
    
    # 加载配置
    config = load_path_mapping_config()
    if not config:
        print("❌ 无法加载配置")
        return
    
    mapping_rules = config.get('rules', {})
    
    print("📋 当前映射规则:")
    for rule_id, rule in mapping_rules.items():
        if rule.get('enabled', True):
            print(f"   - {rule['name']}: {rule['source_pattern']} -> {rule['target_pattern']}")
    
    print("\n" + "=" * 60)
    
    # 测试路径
    test_paths = [
        "Assets\\prefab\\particles\\public\\Texture\\mask_wl_17.png",
        "Assets\\Resources\\minigame\\prefab\\particles\\public\\Texture\\mask_wl_17.png"
    ]
    
    results = []
    for i, path in enumerate(test_paths, 1):
        print(f"\n🔍 测试路径 {i}:")
        mapped_path = apply_path_mapping(path, mapping_rules)
        results.append((path, mapped_path))
        
        if mapped_path == path:
            print(f"   ❌ 没有映射规则匹配此路径")
        else:
            print(f"   ✅ 路径被映射为: {mapped_path}")
    
    print("\n" + "=" * 60)
    print("📊 分析结果:")
    
    # 检查是否有prefab相关的映射规则
    prefab_rules = []
    for rule_id, rule in mapping_rules.items():
        if 'prefab' in rule.get('source_pattern', '').lower() or 'prefab' in rule.get('target_pattern', '').lower():
            prefab_rules.append(rule)
    
    if prefab_rules:
        print("   ✅ 发现prefab相关映射规则:")
        for rule in prefab_rules:
            print(f"      - {rule['name']}: {rule['source_pattern']} -> {rule['target_pattern']}")
    else:
        print("   ❌ 没有发现prefab相关的映射规则")
        print("   💡 建议添加prefab路径映射规则")
    
    # 检查两个路径是否会被认为是同一路径
    path1, mapped1 = results[0]
    path2, mapped2 = results[1]
    
    print(f"\n🔍 路径映射对比:")
    print(f"   路径1: {path1}")
    print(f"   映射1: {mapped1}")
    print(f"   路径2: {path2}")
    print(f"   映射2: {mapped2}")
    
    if mapped1 == mapped2:
        print(f"   ✅ 两个路径会被认为是同一路径")
    else:
        print(f"   ❌ 两个路径会被认为是不同路径")
        print(f"   💡 这就是GUID冲突的原因")

if __name__ == "__main__":
    test_prefab_paths() 