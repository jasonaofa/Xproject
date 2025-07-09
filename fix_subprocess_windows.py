#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复subprocess.run调用，添加Windows窗口隐藏标志
"""

import re
import os

def fix_subprocess_calls(file_path):
    """修复文件中的subprocess.run调用"""
    print(f"🔧 修复文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配subprocess.run调用，但不包含creationflags参数
    pattern = r'(subprocess\.run\([^)]*)\)'
    
    def replace_func(match):
        call_str = match.group(1)
        
        # 如果已经包含creationflags，跳过
        if 'creationflags' in call_str:
            return match.group(0)
        
        # 检查是否以逗号结尾
        if call_str.rstrip().endswith(','):
            # 在最后一个逗号后添加creationflags
            return call_str + f' creationflags=SUBPROCESS_FLAGS)'
        else:
            # 在最后添加逗号和creationflags
            return call_str + f', creationflags=SUBPROCESS_FLAGS)'
    
    # 执行替换
    new_content = re.sub(pattern, replace_func, content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 修复完成: {file_path}")

def main():
    """主函数"""
    files_to_fix = [
        'art_resource_manager.py',
        'test_git_fix.py',
        'crlf_auto_fix.py'
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            fix_subprocess_calls(file_path)
        else:
            print(f"⚠️ 文件不存在: {file_path}")

if __name__ == "__main__":
    main() 