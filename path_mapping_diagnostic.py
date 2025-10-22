#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径映射诊断工具
分析当前路径映射配置是否正确，找出资源误上传的原因
"""

import os
import json
import re
from typing import Dict, List, Any

class PathMappingDiagnostic:
    """路径映射诊断器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.git_path = self.config.get("git_path", "")
        self.svn_path = self.config.get("svn_path", "")
        
        # 内置的路径映射规则（从art_resource_manager.py复制 - 修复后版本）
        self.path_mapping_rules = {
            "remotes_entity_mapping": {
                "name": "远程实体资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]remotes[\\\/]entity($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/remotes/entity/",
                "priority": 1
            },
            "entity_to_minigame": {
                "name": "实体资源映射", 
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]entity[\\\/]",
                "target_pattern": "Assets/Resources/minigame/entity/",
                "priority": 2
            },
            "ui_mapping": {
                "name": "UI资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]ui($|[\\\/])",
                "target_pattern": "Assets/Resources/ui/",
                "priority": 3
            },
            "audio_mapping": {
                "name": "音频资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]audio($|[\\\/])",
                "target_pattern": "Assets/Resources/audio/",
                "priority": 4
            },
            "texture_mapping": {
                "name": "贴图资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]texture($|[\\\/])",
                "target_pattern": "Assets/Resources/textures/",
                "priority": 5
            },
            "prefab_mapping": {
                "name": "Prefab资源映射",
                "enabled": True,
                "source_pattern": r"^Assets[\\\/]prefab($|[\\\/])",
                "target_pattern": "Assets/Resources/minigame/prefab/",
                "priority": 6
            },
            "direct_assets_mapping": {
                "name": "直接Assets映射（新增）",
                "enabled": False,  # 默认禁用，可根据需要启用
                "source_pattern": r"^Assets[\\\/]",
                "target_pattern": "Assets/",
                "priority": 999
            },
            "assets_to_minigame": {
                "name": "Assets根目录映射（通用规则）",
                "enabled": True,
                "source_pattern": r"^Assets[\\/](?!Resources[\\/]minigame[\\/])(?!remotes[\\/]entity[\\/])(?!entity[\\/])",
                "target_pattern": "Assets/Resources/minigame/",
                "priority": 998
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
    
    def analyze_path_mapping_issue(self):
        """分析路径映射问题"""
        print("🔍 路径映射诊断分析")
        print("=" * 60)
        
        # 1. 显示当前配置
        print(f"📋 当前配置:")
        print(f"   Git路径: {self.git_path}")
        print(f"   SVN路径: {self.svn_path}")
        print()
        
        # 2. 分析Git路径结构
        print(f"🎯 Git路径结构分析:")
        git_parts = self.git_path.replace('/', '\\').split('\\')
        print(f"   路径组成: {' -> '.join(git_parts)}")
        
        # 检查是否已经包含CommonResource
        if 'CommonResource' in git_parts:
            print(f"   ✅ Git路径已包含CommonResource目录")
            print(f"   📍 CommonResource位置: 第{git_parts.index('CommonResource') + 1}级目录")
        else:
            print(f"   ⚠️ Git路径未包含CommonResource目录")
        
        # 检查是否包含assetruntimenew
        if 'assetruntimenew' in git_parts:
            print(f"   ✅ Git路径已包含assetruntimenew目录")
            print(f"   📍 assetruntimenew位置: 第{git_parts.index('assetruntimenew') + 1}级目录")
        else:
            print(f"   ⚠️ Git路径未包含assetruntimenew目录")
        print()
        
        # 3. 模拟路径映射过程
        print(f"🧪 路径映射模拟测试:")
        test_paths = [
            "Assets\\remotes\\entity\\140492\\Model\\body.prefab",
            "Assets\\entity\\100060\\Model\\body.prefab", 
            "Assets\\ui\\MainMenu\\background.png",
            "Assets\\audio\\bgm\\main_theme.ogg",
            "Assets\\texture\\characters\\hero_diffuse.png",
            "Assets\\prefab\\weapons\\sword_001.prefab"
        ]
        
        for test_path in test_paths:
            print(f"\n   测试路径: {test_path}")
            mapped_path = self._apply_path_mapping(test_path)
            final_path = os.path.join(self.git_path, mapped_path).replace('/', '\\')
            
            print(f"   映射结果: {mapped_path}")
            print(f"   最终路径: {final_path}")
            
            # 检查路径是否合理
            if final_path.count('assetruntimenew') > 1:
                print(f"   ❌ 警告: 检测到重复的assetruntimenew目录!")
            if final_path.count('CommonResource') > 1:
                print(f"   ❌ 警告: 检测到重复的CommonResource目录!")
            if final_path.count('Assets') > 1:
                print(f"   ❌ 警告: 检测到重复的Assets目录!")
        
        print("\n" + "=" * 60)
        
        # 4. 问题诊断和建议
        print(f"🎯 问题诊断:")
        
        # 检查Git路径是否过深
        if self.git_path.endswith('CommonResource'):
            print(f"   ✅ Git路径配置正确，直接指向CommonResource目录")
        elif 'CommonResource' in self.git_path:
            print(f"   ⚠️ Git路径包含CommonResource但不以其结尾")
            print(f"   💡 建议: 检查Git路径是否应该以CommonResource结尾")
        else:
            print(f"   ❌ Git路径未包含CommonResource")
            print(f"   💡 建议: Git路径应该指向CommonResource目录")
        
        # 检查路径映射是否会导致重复
        print(f"\n💡 修复建议:")
        if self.git_path.endswith('CommonResource'):
            print(f"   1. 当前Git路径已指向CommonResource，路径映射应该直接使用相对路径")
            print(f"   2. 可能需要调整路径映射规则，避免重复添加目录结构")
        
        print(f"   3. 建议禁用或修改某些路径映射规则，避免路径重复")
        print(f"   4. 或者调整Git路径配置，使其指向正确的基础目录")
    
    def _apply_path_mapping(self, assets_path: str) -> str:
        """应用路径映射规则（简化版本）"""
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
                    return result
                    
            except Exception as e:
                print(f"   ⚠️ 规则{rule_id}处理失败: {e}")
                continue
        
        # 没有匹配的规则，返回原路径
        return assets_path
    
    def suggest_fixes(self):
        """建议修复方案"""
        print("\n🔧 修复方案建议:")
        print("=" * 60)
        
        print("方案1: 调整Git路径配置")
        print("   - 如果您想直接上传到CommonResource目录")
        print("   - 保持当前Git路径不变")
        print("   - 禁用或修改路径映射规则")
        
        print("\n方案2: 调整路径映射规则")
        print("   - 保持当前路径映射规则")
        print("   - 修改Git路径为更上级的目录")
        print("   - 让路径映射规则处理完整的目录结构")
        
        print("\n方案3: 混合方案")
        print("   - 根据资源类型使用不同的处理方式")
        print("   - 某些资源直接上传，某些资源使用路径映射")
        
        print("\n🎯 推荐方案:")
        if self.git_path.endswith('CommonResource'):
            print("   由于您的Git路径已经指向CommonResource，建议:")
            print("   1. 禁用通用的路径映射规则")
            print("   2. 只保留必要的特殊映射规则") 
            print("   3. 或者将Git路径调整为上一级目录")


def main():
    """主函数"""
    diagnostic = PathMappingDiagnostic()
    diagnostic.analyze_path_mapping_issue()
    diagnostic.suggest_fixes()


if __name__ == "__main__":
    main()
