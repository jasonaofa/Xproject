#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试UI修改的脚本
验证：
1. "增加依赖文件"按钮已移动到"清空列表"和"检查资源"之间
2. "增加依赖文件"按钮没有样式
3. "检查资源"按钮是绿底白字
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ui_changes():
    """测试UI修改"""
    
    print("🔍 测试UI修改")
    print("=" * 50)
    
    # 检查文件中的按钮定义
    with open('art_resource_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查"增加依赖文件"按钮的位置
    print("📋 检查按钮位置和样式...")
    
    # 查找文件操作按钮区域
    file_btn_section = content.find('file_btn_layout = QHBoxLayout()')
    if file_btn_section == -1:
        print("❌ 未找到文件按钮布局区域")
        return False
    
    # 查找按钮顺序
    clear_btn_pos = content.find('self.clear_files_btn = QPushButton("清空列表")', file_btn_section)
    add_dep_btn_pos = content.find('self.add_dependencies_btn = QPushButton("增加依赖文件")', file_btn_section)
    check_btn_pos = content.find('self.check_btn = QPushButton("检查资源")', file_btn_section)
    
    print(f"   清空列表按钮位置: {clear_btn_pos}")
    print(f"   增加依赖文件按钮位置: {add_dep_btn_pos}")
    print(f"   检查资源按钮位置: {check_btn_pos}")
    
    # 检查按钮顺序
    if clear_btn_pos < add_dep_btn_pos < check_btn_pos:
        print("✅ 按钮顺序正确：清空列表 -> 增加依赖文件 -> 检查资源")
    else:
        print("❌ 按钮顺序错误")
        return False
    
    # 检查"增加依赖文件"按钮是否有样式
    add_dep_style_start = content.find('self.add_dependencies_btn.setStyleSheet', add_dep_btn_pos)
    if add_dep_style_start == -1:
        print("✅ 增加依赖文件按钮没有样式（符合要求）")
    else:
        print("❌ 增加依赖文件按钮仍有样式")
        return False
    
    # 检查"检查资源"按钮是否有绿底白字样式
    check_style_start = content.find('self.check_btn.setStyleSheet', check_btn_pos)
    if check_style_start != -1:
        # 查找样式内容
        style_end = content.find('""")', check_style_start)
        if style_end != -1:
            style_content = content[check_style_start:style_end + 4]
            if 'background-color: #4CAF50' in style_content and 'color: white' in style_content:
                print("✅ 检查资源按钮有绿底白字样式")
            else:
                print("❌ 检查资源按钮样式不正确")
                return False
        else:
            print("❌ 无法找到检查资源按钮的样式内容")
            return False
    else:
        print("❌ 检查资源按钮没有样式")
        return False
    
    # 检查是否移除了原来的"增加依赖文件"按钮
    old_add_dep_pos = content.find('# 增加依赖文件按钮')
    if old_add_dep_pos == -1:
        print("✅ 已移除原来的增加依赖文件按钮")
    else:
        print("❌ 仍存在原来的增加依赖文件按钮")
        return False
    
    print("\n🎉 所有UI修改验证通过！")
    return True

if __name__ == "__main__":
    success = test_ui_changes()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ UI修改测试通过")
    else:
        print("❌ UI修改测试失败") 