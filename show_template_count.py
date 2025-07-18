#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker

def show_template_count():
    """显示所有允许的模板数量和列表"""
    
    print("🔍 查看所有允许的材质模板")
    print("=" * 60)
    
    # 创建一个临时的ResourceChecker实例来获取模板列表
    class MockGitManager:
        def __init__(self):
            self.git_path = ""
            self.svn_path = ""
    
    checker = ResourceChecker([], MockGitManager(), "CommonResource")
    
    # 获取允许的模板列表 (从代码中提取)
    allowed_templates = {
        # 角色和场景模板
        'Character_NPR_Opaque.templatemat',
        'Character_NPR_Masked.templatemat',
        'Character_NPR_Tranclucent.templatemat',
        'Character_AVATAR_Masked.templatemat',
        'Character_AVATAR_Opaque.templatemat',
        'Character_AVATAR_Tranclucent.templatemat',
        'Character_PBR_Opaque.templatemat',
        'Character_PBR_Translucent.templatemat',
        'Scene_Prop_Opaque.templatemat',
        'Scene_Prop_Tranclucent.templatemat',
        'Scene_Prop_Masked.templatemat',
        'Sight.templatemat',
        
        # 特效模板
        'fx_basic_ADD.templatemat',
        'fx_basic_fire.templatemat',
        'fx_basic_TRANSLUCENT.templatemat',
        'fx_dissolve_ADD.templatemat',
        'fx_dissolve_fresnel_ADD.templatemat',
        'fx_dissolve_fresnel_TRANSLUCENT.templatemat',
        'fx_dissolve_fresneluvwarp_ADD.templatemat',
        'fx_dissolve_fresneluvwarp_TRANSLUCENT.templatemat',
        'fx_dissolve_TRANSLUCENT.templatemat',
        'fx_dissolve_uvwarp_ADD.templatemat',
        'fx_dissolve_uvwarp_Fire_ADD.templatemat',
        'fx_dissolve_uvwarp_Fire_TRANSLUCENT.templatemat',
        'fx_dissolve_uvwarp_TRANSLUCENT.templatemat',
        'fx_dissolve_vertexesoffsetWithMask_ADD.templatemat',
        'fx_dissolve_vertexesoffsetWithMask_TRANSLUCENT.templatemat',
        'fx_fresnel_ADD.templatemat',
        'fx_fresnel_TRANSLUCENT.templatemat',
        'fx_uvwarp_ADD.templatemat',
        'fx_uvwarp_TRANSLUCENT.templatemat',
        'fx_vertexesoffset_ADD.templatemat',
        'fx_vertexesoffset_TRANSLUCENT.templatemat',
        'fx_vertexesoffsetWithMask_ADD.templatemat',
        'fx_vertexesoffsetWithMask_TRANSLUCENT.templatemat',
        'PolarDistortion.templatemat',
        'standard_particle_additive.templatemat',
        'standard_particle_translucent.templatemat'
    }
    
    # 分类显示
    character_templates = [t for t in allowed_templates if t.startswith('Character_')]
    scene_templates = [t for t in allowed_templates if t.startswith('Scene_')]
    fx_templates = [t for t in allowed_templates if t.startswith('fx_')]
    particle_templates = [t for t in allowed_templates if t.startswith('standard_particle_')]
    other_templates = [t for t in allowed_templates if not any(t.startswith(prefix) for prefix in ['Character_', 'Scene_', 'fx_', 'standard_particle_'])]
    
    print(f"📊 模板统计:")
    print(f"   总计: {len(allowed_templates)} 个模板")
    print(f"   角色模板: {len(character_templates)} 个")
    print(f"   场景模板: {len(scene_templates)} 个")
    print(f"   特效模板: {len(fx_templates)} 个")
    print(f"   粒子模板: {len(particle_templates)} 个")
    print(f"   其他模板: {len(other_templates)} 个")
    
    print(f"\n📋 详细列表:")
    
    print(f"\n【角色模板】({len(character_templates)} 个):")
    for template in sorted(character_templates):
        print(f"   - {template}")
    
    print(f"\n【场景模板】({len(scene_templates)} 个):")
    for template in sorted(scene_templates):
        print(f"   - {template}")
    
    print(f"\n【特效模板】({len(fx_templates)} 个):")
    for template in sorted(fx_templates):
        print(f"   - {template}")
    
    print(f"\n【粒子模板】({len(particle_templates)} 个):")
    for template in sorted(particle_templates):
        print(f"   - {template}")
    
    print(f"\n【其他模板】({len(other_templates)} 个):")
    for template in sorted(other_templates):
        print(f"   - {template}")
    
    print(f"\n🎯 新增的特效模板:")
    new_fx_templates = [
        'fx_basic_ADD.templatemat',
        'fx_basic_fire.templatemat',
        'fx_basic_TRANSLUCENT.templatemat',
        'fx_dissolve_ADD.templatemat',
        'fx_dissolve_fresnel_ADD.templatemat',
        'fx_dissolve_fresnel_TRANSLUCENT.templatemat',
        'fx_dissolve_fresneluvwarp_ADD.templatemat',
        'fx_dissolve_fresneluvwarp_TRANSLUCENT.templatemat',
        'fx_dissolve_TRANSLUCENT.templatemat',
        'fx_dissolve_uvwarp_ADD.templatemat',
        'fx_dissolve_uvwarp_Fire_ADD.templatemat',
        'fx_dissolve_uvwarp_Fire_TRANSLUCENT.templatemat',
        'fx_dissolve_uvwarp_TRANSLUCENT.templatemat',
        'fx_dissolve_vertexesoffsetWithMask_ADD.templatemat',
        'fx_dissolve_vertexesoffsetWithMask_TRANSLUCENT.templatemat',
        'fx_fresnel_ADD.templatemat',
        'fx_fresnel_TRANSLUCENT.templatemat',
        'fx_uvwarp_ADD.templatemat',
        'fx_uvwarp_TRANSLUCENT.templatemat',
        'fx_vertexesoffset_ADD.templatemat',
        'fx_vertexesoffset_TRANSLUCENT.templatemat',
        'fx_vertexesoffsetWithMask_ADD.templatemat',
        'fx_vertexesoffsetWithMask_TRANSLUCENT.templatemat',
        'PolarDistortion.templatemat',
        'standard_particle_additive.templatemat',
        'standard_particle_translucent.templatemat'
    ]
    
    print(f"   本次新增: {len(new_fx_templates)} 个特效和粒子模板")
    print(f"   从原来的 12 个模板增加到现在的 {len(allowed_templates)} 个模板")

if __name__ == "__main__":
    show_template_count() 