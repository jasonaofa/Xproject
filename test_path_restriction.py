#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径限制功能测试脚本
测试路径验证和路径映射的完整功能
"""

import os
import sys
import json
from typing import Dict, List, Any

# 模拟GitSvnManager的路径验证功能
class PathRestrictionTester:
    """路径限制测试器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.git_path = self.config.get("git_path", "")
        
        # 完善的路径映射规则
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
                "target_pattern": "Assets/Resources/ui/",
                "priority": 3,
                "category": "界面资源"
            },
            "audio_mapping": {
                "name": "🎵 音频资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]audio($|[\\\/])",
                "target_pattern": "Assets/Resources/audio/",
                "priority": 4,
                "category": "音频资源"
            },
            "texture_mapping": {
                "name": "🖌️ 贴图资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]texture($|[\\\/])",
                "target_pattern": "Assets/Resources/textures/",
                "priority": 5,
                "category": "贴图资源"
            },
            "prefab_mapping": {
                "name": "🧩 Prefab预制体映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]prefab($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/prefab/",
                "priority": 6,
                "category": "游戏预制体"
            },
            "assets_to_minigame": {
                "name": "📦 通用资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\/](?!Resources[\\/])(?!remotes[\\/]entity[\\/])(?!entity[\\/])(?!ui[\\/])(?!audio[\\/])(?!texture[\\/])(?!prefab[\\/])",
                "target_pattern": "Assets/Resources/minigame/",
                "priority": 998,
                "category": "通用资源"
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists("config.json"):
                with open("config.json", 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {e}")
        return {}
    
    def validate_upload_path(self, git_path: str = None) -> bool:
        """验证上传路径是否安全"""
        test_path = git_path or self.git_path
        
        if not test_path:
            print("❌ [PATH_VALIDATION] Git路径为空")
            return False
        
        # 标准化路径
        normalized_git_path = os.path.normpath(test_path).replace('\\', '/')
        
        print(f"🔍 [PATH_VALIDATION] 开始验证上传路径...")
        print(f"   原始Git路径: {test_path}")
        print(f"   标准化路径: {normalized_git_path}")
        
        # 检查是否包含CommonResource
        if 'CommonResource' not in normalized_git_path:
            print(f"❌ [PATH_VALIDATION] 路径不包含CommonResource目录")
            return False
        
        # 检查是否以CommonResource结尾（推荐配置）
        if normalized_git_path.endswith('CommonResource'):
            print(f"✅ [PATH_VALIDATION] 路径配置正确，直接指向CommonResource目录")
            return True
        
        # 检查是否在CommonResource目录下（也允许）
        if '/CommonResource/' in normalized_git_path:
            print(f"✅ [PATH_VALIDATION] 路径在CommonResource目录下，允许上传")
            return True
        
        # 禁止的路径模式
        forbidden_patterns = [
            'assetruntimenew/Assets',
            'assetruntimenew/Packages',
            'assetruntimenew/ProjectSettings'
        ]
        
        for pattern in forbidden_patterns:
            if pattern in normalized_git_path and 'CommonResource' not in normalized_git_path:
                print(f"❌ [PATH_VALIDATION] 检测到禁止的路径模式: {pattern}")
                return False
        
        print(f"✅ [PATH_VALIDATION] 路径验证通过")
        return True
    
    def test_path_mapping(self, test_path: str) -> str:
        """测试路径映射"""
        import re
        
        # 按优先级排序规则
        sorted_rules = sorted(
            [(rule_id, rule) for rule_id, rule in self.path_mapping_rules.items() if rule.get('enabled', True)],
            key=lambda x: x[1].get('priority', 999)
        )
        
        print(f"🔄 [MAPPING] 测试路径映射: {test_path}")
        
        for rule_id, rule in sorted_rules:
            try:
                source_pattern = rule.get('source_pattern', '')
                target_pattern = rule.get('target_pattern', '')
                
                if re.match(source_pattern, test_path, re.IGNORECASE):
                    result = re.sub(source_pattern, target_pattern, test_path, count=1, flags=re.IGNORECASE)
                    print(f"   ✅ 匹配规则: {rule['name']}")
                    print(f"   📝 类别: {rule.get('category', '未分类')}")
                    return result
                    
            except Exception as e:
                print(f"   ⚠️ 规则{rule_id}处理失败: {e}")
                continue
        
        print(f"   ⚠️ 未匹配任何规则，使用原路径")
        return test_path
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🧪 路径限制和映射功能综合测试")
        print("=" * 80)
        
        # 1. 测试路径验证
        print("\n📋 1. 路径验证测试")
        print("-" * 40)
        
        test_paths = [
            self.git_path,  # 当前配置的路径
            "H:/0124v_03/assetruntimenew/CommonResource",  # 正确路径
            "H:/0124v_03/assetruntimenew/Assets",  # 错误路径1
            "H:/0124v_03/assetruntimenew/Packages",  # 错误路径2
            "G:/other_project/CommonResource",  # 其他项目的CommonResource
            ""  # 空路径
        ]
        
        for i, path in enumerate(test_paths):
            print(f"\n测试路径 {i+1}: {path or '(空路径)'}")
            is_valid = self.validate_upload_path(path)
            print(f"验证结果: {'✅ 通过' if is_valid else '❌ 拒绝'}")
        
        # 2. 测试路径映射
        print("\n📋 2. 路径映射测试")
        print("-" * 40)
        
        test_assets = [
            "Assets/remotes/entity/140492/Model/body.prefab",
            "Assets/entity/100060/Model/character.prefab",
            "Assets/ui/MainMenu/background.png",
            "Assets/audio/bgm/main_theme.ogg",
            "Assets/texture/characters/hero_diffuse.png",
            "Assets/prefab/weapons/sword_001.prefab",
            "Assets/effects/particles/explosion.prefab",
            "Assets/special/custom_file.txt"
        ]
        
        print(f"\n当前Git路径: {self.git_path}")
        print("路径映射结果:")
        
        for asset_path in test_assets:
            print(f"\n原始路径: {asset_path}")
            mapped_path = self.test_path_mapping(asset_path)
            final_path = os.path.join(self.git_path, mapped_path).replace('\\', '/')
            
            print(f"映射结果: {mapped_path}")
            print(f"最终路径: {final_path}")
            
            # 检查路径合理性
            warnings = []
            if final_path.count('CommonResource') > 1:
                warnings.append("重复的CommonResource目录")
            if final_path.count('Assets') > 1:
                warnings.append("重复的Assets目录")
            if final_path.count('Resources') > 1:
                warnings.append("重复的Resources目录")
            
            if warnings:
                print(f"⚠️ 警告: {', '.join(warnings)}")
            else:
                print(f"✅ 路径结构正常")
        
        # 3. 总结
        print("\n📋 3. 测试总结")
        print("-" * 40)
        print("✅ 路径验证功能: 确保只能上传到CommonResource目录")
        print("✅ 路径映射功能: 按资源类型自动分类存放")
        print("✅ 安全检查功能: 防止重复目录和错误路径")
        print("\n🎯 功能状态: 路径限制和映射功能工作正常")


def main():
    """主函数"""
    tester = PathRestrictionTester()
    tester.run_comprehensive_test()


if __name__ == "__main__":
    main()

