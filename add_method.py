#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from typing import List

def add_missing_method():
    """添加缺失的_find_template_references方法"""
    
    # 读取文件
    with open('art_resource_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # 查找插入位置（在_check_material_templates方法之后）
    insert_line = -1
    for i, line in enumerate(lines):
        if 'return issues' in line and i > 0:
            # 检查前面是否有_check_material_templates方法
            for j in range(i - 50, i):
                if j >= 0 and 'def _check_material_templates' in lines[j]:
                    insert_line = i + 1
                    break
            if insert_line != -1:
                break
    
    if insert_line == -1:
        print("没有找到插入位置")
        return
    
    # 创建新的方法
    new_method = '''
    def _find_template_references(self, content: str) -> List[str]:
        """在材质文件内容中查找模板引用"""
        template_references = []
        
        try:
            # 首先查找直接的模板名称引用
            template_name_patterns = [
                r'Character_NPR_Opaque\.templatemat',
                r'Character_NPR_Masked\.templatemat',
                r'Character_NPR_Tranclucent\.templatemat',
                r'Character_AVATAR_Masked\.templatemat',
                r'Character_AVATAR_Opaque\.templatemat',
                r'Character_AVATAR_Tranclucent\.templatemat',
                r'Character_PBR_Opaque\.templatemat',
                r'Character_PBR_Translucent\.templatemat',
                r'Scene_Prop_Opaque\.templatemat',
                r'Scene_Prop_Tranclucent\.templatemat',
                r'Scene_Prop_Masked\.templatemat',
                r'Sight\.templatemat'
            ]
            
            # 查找直接的模板名称引用
            for pattern in template_name_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    template_name = match.replace('\\\\', '')
                    if template_name not in template_references:
                        template_references.append(template_name)
            
            # 如果没有找到直接的模板名称，尝试查找通用的templatemat引用
            if not template_references:
                templatemat_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*\.templatemat)'
                matches = re.findall(templatemat_pattern, content, re.IGNORECASE)
                for match in matches:
                    if match not in template_references:
                        template_references.append(match)
            
            # 如果仍然没有找到模板引用，尝试查找模板相关的GUID引用
            if not template_references:
                # 查找模板引用的正则表达式模式
                template_guid_patterns = [
                    r'template:\s*{.*?guid:\s*([a-f0-9]{32})',  # YAML格式template引用
                    r'template:\s*{.*?m_GUID:\s*([a-f0-9]{32})',  # YAML格式m_GUID引用
                    r'"template":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"',  # JSON格式template引用
                    r'"template":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"',  # JSON格式m_GUID引用
                ]
                
                for pattern in template_guid_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                    for guid in matches:
                        # 记录找到了模板GUID引用
                        template_references.append(f"TEMPLATE_GUID:{guid}")
            
        except Exception as e:
            print(f"查找模板引用时出错: {e}")
        
        return template_references
'''.split('\n')
    
    # 插入新方法
    new_lines = lines[:insert_line] + new_method + lines[insert_line:]
    
    # 写回文件
    with open('art_resource_manager.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"方法添加完成，插入位置: {insert_line}")

if __name__ == "__main__":
    add_missing_method() 