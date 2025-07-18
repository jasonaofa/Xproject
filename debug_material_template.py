#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceChecker

def debug_material_template():
    """调试材质模板检查问题"""
    
    print("🔍 调试材质模板检查问题")
    print("=" * 60)
    
    # 根据config.json中的路径，查找140467目录下的材质文件
    svn_path = "C:/6.1.10_prefab/Assets/entity/140467"
    
    # 查找所有mat文件
    mat_files = []
    if os.path.exists(svn_path):
        print(f"✅ 找到SVN路径: {svn_path}")
        for root, dirs, files in os.walk(svn_path):
            for file in files:
                if file.lower().endswith('.mat'):
                    mat_files.append(os.path.join(root, file))
    else:
        print(f"❌ SVN路径不存在: {svn_path}")
        # 让用户手动输入文件路径
        print("请手动输入140467目录中的材质文件路径:")
        manual_path = input("文件路径: ").strip()
        if manual_path and os.path.exists(manual_path):
            mat_files.append(manual_path)
    
    if not mat_files:
        print("❌ 没有找到任何材质文件")
        return
    
    print(f"📁 找到 {len(mat_files)} 个材质文件:")
    for i, file_path in enumerate(mat_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    
    # 允许的材质模板列表
    allowed_templates = {
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
        'Sight.templatemat'
    }
    
    print(f"\n🔍 开始逐个分析材质文件...")
    
    # 创建一个模拟的ResourceChecker实例
    class MockGitManager:
        def __init__(self):
            self.git_path = ""
            self.svn_path = ""
    
    checker = ResourceChecker(mat_files, MockGitManager(), "CommonResource")
    
    for i, file_path in enumerate(mat_files, 1):
        print(f"\n📄 分析文件 {i}/{len(mat_files)}: {os.path.basename(file_path)}")
        print(f"   完整路径: {file_path}")
        
        # 1. 检查文件是否会被过滤
        print(f"   🔍 步骤1: 检查文件路径过滤...")
        
        # 检查是否在entity目录下
        normalized_path = os.path.normpath(file_path)
        path_parts = normalized_path.split(os.sep)
        
        entity_index = -1
        for j, part in enumerate(path_parts):
            if part.lower() == 'entity':
                entity_index = j
                break
        
        if entity_index == -1:
            print(f"   ❌ 文件不在entity目录下，会被跳过")
            continue
        else:
            print(f"   ✅ 文件在entity目录下 (索引: {entity_index})")
        
        # 检查是否在排除的目录中
        excluded_path = False
        remaining_parts = path_parts[entity_index + 1:]
        
        if (len(remaining_parts) >= 2 and 
            remaining_parts[0].lower() == 'environment' and 
            remaining_parts[1].lower() == 'scenes'):
            excluded_path = True
            print(f"   ❌ 文件在排除目录 entity/Environment/Scenes 中，会被跳过")
            continue
        else:
            print(f"   ✅ 文件不在排除目录中，会被检查")
        
        # 2. 读取文件内容
        print(f"   🔍 步骤2: 读取文件内容...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   ✅ 文件读取成功，大小: {len(content)} 字符")
        except Exception as e:
            print(f"   ❌ 文件读取失败: {e}")
            continue
        
        # 3. 显示文件内容的前部分
        print(f"   📄 文件内容预览 (前500字符):")
        print("   " + "-" * 50)
        preview_lines = content[:500].split('\n')
        for line in preview_lines[:10]:  # 只显示前10行
            print(f"   {line}")
        print("   " + "-" * 50)
        
        # 4. 查找模板引用
        print(f"   🔍 步骤3: 查找模板引用...")
        
        # 使用多种模式查找模板引用
        template_patterns = [
            (r'templatemat:\s*([^\s\n]+\.templatemat)', "直接templatemat引用"),
            (r'template:\s*([^\s\n]+\.templatemat)', "template引用"),
            (r'([A-Za-z_][A-Za-z0-9_]*\.templatemat)', "任何templatemat文件"),
            (r'templatemat:\s*([^\s\n]+)', "templatemat字段值"),
            (r'template:\s*([^\s\n]+)', "template字段值"),
        ]
        
        found_templates = []
        for pattern, desc in template_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                template_name = match.strip()
                if template_name not in found_templates:
                    found_templates.append(template_name)
                    print(f"   🔑 找到模板引用: {template_name} (通过: {desc})")
        
        if not found_templates:
            print(f"   ❌ 没有找到任何模板引用")
            
            # 手动搜索是否包含任何已知模板名称
            print(f"   🔍 手动搜索已知模板名称...")
            for template in allowed_templates:
                if template.lower() in content.lower():
                    print(f"   🔑 在内容中找到模板: {template}")
                    found_templates.append(template)
        
        # 5. 验证模板
        print(f"   🔍 步骤4: 验证模板...")
        
        if not found_templates:
            print(f"   ⚠️  警告: 没有找到模板引用")
        else:
            for template_name in found_templates:
                if template_name in allowed_templates:
                    print(f"   ✅ 模板 {template_name} 是允许的")
                else:
                    print(f"   ❌ 模板 {template_name} 不在允许列表中")
                    print(f"      这应该被报告为错误！")
        
        # 6. 测试ResourceChecker的方法
        print(f"   🔍 步骤5: 测试ResourceChecker方法...")
        template_references = checker._find_template_references(content)
        print(f"   ResourceChecker找到的引用: {template_references}")
        
        print(f"   " + "=" * 50)

if __name__ == "__main__":
    debug_material_template() 