#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的路径结构映射
验证更新后的路径映射规则是否正确
"""

import os
import re
import json

class NewPathStructureTester:
    """新路径结构测试器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.git_path = self.config.get("git_path", "H:/0124v_03/assetruntimenew/CommonResource")
        
        # 更新后的路径映射规则
        self.path_mapping_rules = {
            "remotes_entity_mapping": {
                "name": "🌐 远程实体资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]remotes[\\\/]entity($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/remotes/entity/",
                "priority": 1,
                "category": "实体资源"
            },
            "entity_to_minigame": {
                "name": "👤 本地实体资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]entity[\\\/]",
                "target_pattern": "Assets/Resources/minigame/entity/",
                "priority": 2,
                "category": "实体资源"
            },
            "ui_mapping": {
                "name": "🖼️ UI界面资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]ui($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/ui/",
                "priority": 3,
                "category": "界面资源"
            },
            "audio_mapping": {
                "name": "🎵 音频资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]audio($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/sounds/",
                "priority": 4,
                "category": "音频资源"
            },
            "texture_mapping": {
                "name": "🖌️ 贴图资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]texture($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/textures/",
                "priority": 5,
                "category": "贴图资源"
            },
            "effects_mapping": {
                "name": "✨ 特效资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]effects($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/prefab/effects/",
                "priority": 6,
                "category": "特效资源"
            },
            "prefab_mapping": {
                "name": "🧩 Prefab预制体映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]prefab($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/prefab/",
                "priority": 7,
                "category": "游戏预制体"
            },
            "assets_to_minigame": {
                "name": "📦 通用资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\/](?!Resources[\\/])(?!remotes[\\/]entity[\\/])(?!entity[\\/])(?!ui[\\/])(?!audio[\\/])(?!texture[\\/])(?!effects[\\/])(?!prefab[\\/])",
                "target_pattern": "Assets/Resources/minigame/",
                "priority": 998,
                "category": "通用资源"
            }
        }
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists("config.json"):
                with open("config.json", 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def apply_path_mapping(self, assets_path: str) -> str:
        """应用路径映射规则"""
        # 按优先级排序规则
        sorted_rules = sorted(
            [(rule_id, rule) for rule_id, rule in self.path_mapping_rules.items() if rule.get('enabled', True)],
            key=lambda x: x[1].get('priority', 999)
        )
        
        for rule_id, rule in sorted_rules:
            try:
                source_pattern = rule.get('source_pattern', '')
                target_pattern = rule.get('target_pattern', '')
                
                if re.match(source_pattern, assets_path, re.IGNORECASE):
                    # 应用映射
                    result = re.sub(source_pattern, target_pattern, assets_path, count=1, flags=re.IGNORECASE)
                    return result, rule['name'], rule.get('category', '未分类')
                    
            except Exception as e:
                print(f"   ⚠️ 规则{rule_id}处理失败: {e}")
                continue
        
        # 没有匹配的规则，返回原路径
        return assets_path, "无匹配规则", "未分类"
    
    def test_new_path_structure(self):
        """测试新的路径结构"""
        print("🔄 新路径结构映射测试")
        print("=" * 80)
        
        print(f"📍 当前Git路径: {self.git_path}")
        print(f"🎯 新的路径结构规范:")
        print(f"   - 实体资源: CommonResource/Assets/Resources/minigame/entity/100060/...")
        print(f"   - 远程实体: CommonResource/Assets/Resources/minigame/remotes/entity/140492/...")
        print(f"   - UI资源: CommonResource/Assets/Resources/minigame/ui/...")
        print(f"   - 音频资源: CommonResource/Assets/Resources/minigame/sounds/...")
        print(f"   - 特效资源: CommonResource/Assets/Resources/minigame/prefab/...")
        print(f"   - 其他资源: CommonResource/Assets/Resources/minigame/...")
        print()
        
        # 测试用例
        test_cases = [
            {
                "path": "Assets/remotes/entity/140492/Model/body.prefab",
                "expected_category": "实体资源",
                "description": "远程实体模型"
            },
            {
                "path": "Assets/entity/100060/Model/character.prefab",
                "expected_category": "实体资源", 
                "description": "本地实体模型"
            },
            {
                "path": "Assets/ui/MainMenu/background.png",
                "expected_category": "界面资源",
                "description": "UI界面背景"
            },
            {
                "path": "Assets/audio/bgm/main_theme.ogg",
                "expected_category": "音频资源",
                "description": "背景音乐"
            },
            {
                "path": "Assets/audio/sfx/explosion.wav",
                "expected_category": "音频资源",
                "description": "音效文件"
            },
            {
                "path": "Assets/texture/characters/hero_diffuse.png",
                "expected_category": "贴图资源",
                "description": "角色贴图"
            },
            {
                "path": "Assets/effects/explosion.prefab",
                "expected_category": "特效资源",
                "description": "爆炸特效"
            },
            {
                "path": "Assets/effects/particles/fire.prefab",
                "expected_category": "特效资源",
                "description": "粒子特效"
            },
            {
                "path": "Assets/prefab/weapons/sword_001.prefab",
                "expected_category": "游戏预制体",
                "description": "武器预制体"
            },
            {
                "path": "Assets/materials/wood.mat",
                "expected_category": "通用资源",
                "description": "材质文件"
            },
            {
                "path": "Assets/shaders/custom.shader",
                "expected_category": "通用资源",
                "description": "着色器文件"
            }
        ]
        
        print("📋 路径映射测试结果:")
        print("-" * 80)
        
        success_count = 0
        total_count = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            original_path = test_case["path"]
            expected_category = test_case["expected_category"]
            description = test_case["description"]
            
            print(f"\n{i:2d}. {description}")
            print(f"    原始路径: {original_path}")
            
            # 应用路径映射
            mapped_path, rule_name, category = self.apply_path_mapping(original_path)
            final_path = os.path.join(self.git_path, mapped_path).replace('\\', '/')
            
            print(f"    映射规则: {rule_name}")
            print(f"    资源类别: {category}")
            print(f"    映射结果: {mapped_path}")
            print(f"    最终路径: {final_path}")
            
            # 验证结果
            if category == expected_category:
                print(f"    ✅ 测试通过")
                success_count += 1
            else:
                print(f"    ❌ 测试失败 - 期望类别: {expected_category}, 实际类别: {category}")
            
            # 检查路径合理性
            warnings = []
            if final_path.count('CommonResource') > 1:
                warnings.append("重复的CommonResource目录")
            if final_path.count('Assets') > 1:
                warnings.append("重复的Assets目录")
            if final_path.count('Resources') > 1:
                warnings.append("重复的Resources目录")
            if final_path.count('minigame') > 1:
                warnings.append("重复的minigame目录")
            
            if warnings:
                print(f"    ⚠️ 警告: {', '.join(warnings)}")
        
        # 测试总结
        print("\n" + "=" * 80)
        print("📊 测试总结:")
        print(f"   总测试数: {total_count}")
        print(f"   成功数: {success_count}")
        print(f"   失败数: {total_count - success_count}")
        print(f"   成功率: {success_count/total_count*100:.1f}%")
        
        if success_count == total_count:
            print(f"🎉 所有测试通过！新的路径结构映射工作正常。")
        else:
            print(f"⚠️ 部分测试失败，请检查路径映射规则。")
        
        return success_count == total_count


def main():
    """主函数"""
    tester = NewPathStructureTester()
    tester.test_new_path_structure()


if __name__ == "__main__":
    main()

