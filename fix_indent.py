#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def fix_indentation():
    """修复art_resource_manager.py中的缩进问题"""
    
    # 读取文件
    with open('art_resource_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复第4165行和第4166行的缩进问题
    # 查找有问题的行
    lines = content.split('\n')
    
    # 修复第4165行前后的缩进
    for i, line in enumerate(lines):
        if '# 查找模板引用' in line and 'template_references' in lines[i+1]:
            # 找到了有问题的行
            lines[i] = '                    # 查找模板引用'
            lines[i+1] = '                    template_references = self._find_template_references(content)'
            
            # 继续修复后面的缩进
            j = i + 2
            while j < len(lines) and lines[j].strip():
                if lines[j].strip() == 'if not template_references:':
                    lines[j] = '                    if not template_references:'
                elif lines[j].strip() == '# 没有找到模板引用，这可能是问题':
                    lines[j] = '                        # 没有找到模板引用，这可能是问题'
                j += 1
            break
    
    # 写回文件
    with open('art_resource_manager.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print("缩进修复完成")

if __name__ == "__main__":
    fix_indentation() 