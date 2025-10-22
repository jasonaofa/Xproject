#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径映射快速修复工具
提供几种路径映射方案，让用户选择最合适的
"""

import os
import json
import shutil
from typing import Dict, Any

class PathMappingFixer:
    """路径映射修复器"""
    
    def __init__(self):
        self.config_file = "config.json"
        self.art_resource_manager_file = "art_resource_manager.py"
        self.backup_file = f"{self.art_resource_manager_file}.backup_path_mapping"
    
    def show_options(self):
        """显示修复选项"""
        print("🔧 路径映射修复选项")
        print("=" * 60)
        print("当前问题：资源上传到了错误的路径")
        print("Git路径：H:/0124v_03/assetruntimenew/CommonResource")
        print()
        
        print("📋 可选方案：")
        print()
        print("方案1：禁用路径映射（推荐）")
        print("   - 直接使用原始Assets路径")
        print("   - 结果：CommonResource/Assets/remotes/entity/140492/...")
        print("   - 适合：Git路径已经指向正确目标目录")
        print()
        
        print("方案2：简化路径映射")
        print("   - 去除Assets前缀，直接使用Resources路径")
        print("   - 结果：CommonResource/Resources/minigame/entity/140492/...")
        print("   - 适合：希望扁平化目录结构")
        print()
        
        print("方案3：保持当前路径映射")
        print("   - 使用完整的Assets/Resources路径")
        print("   - 结果：CommonResource/Assets/Resources/minigame/entity/140492/...")
        print("   - 适合：需要完整的Unity项目结构")
        print()
        
        print("方案4：自定义配置")
        print("   - 手动配置路径映射规则")
        print("   - 结果：根据您的具体需求定制")
        print()
    
    def apply_solution_1(self):
        """方案1：禁用路径映射"""
        print("🔧 应用方案1：禁用路径映射")
        
        # 创建备份
        if not os.path.exists(self.backup_file):
            shutil.copy2(self.art_resource_manager_file, self.backup_file)
            print(f"✅ 已创建备份：{self.backup_file}")
        
        # 读取文件内容
        with open(self.art_resource_manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改路径映射开关
        content = content.replace(
            'self.path_mapping_enabled = True',
            'self.path_mapping_enabled = False  # 🔧 已禁用路径映射，直接使用原始路径'
        )
        
        # 保存修改
        with open(self.art_resource_manager_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 方案1应用完成")
        print("📋 效果：资源将直接使用原始Assets路径上传")
        print("🎯 目标路径示例：CommonResource/Assets/remotes/entity/140492/...")
        
    def apply_solution_2(self):
        """方案2：简化路径映射（去除Assets前缀）"""
        print("🔧 应用方案2：简化路径映射")
        
        # 创建备份
        if not os.path.exists(self.backup_file):
            shutil.copy2(self.art_resource_manager_file, self.backup_file)
            print(f"✅ 已创建备份：{self.backup_file}")
        
        # 读取文件内容
        with open(self.art_resource_manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改路径映射规则，去除Assets前缀
        replacements = [
            ('"Assets/Resources/minigame/remotes/entity/"', '"Resources/minigame/remotes/entity/"'),
            ('"Assets/Resources/minigame/entity/"', '"Resources/minigame/entity/"'),
            ('"Assets/Resources/ui/"', '"Resources/ui/"'),
            ('"Assets/Resources/audio/"', '"Resources/audio/"'),
            ('"Assets/Resources/textures/"', '"Resources/textures/"'),
            ('"Assets/Resources/minigame/prefab/"', '"Resources/minigame/prefab/"'),
            ('"Assets/"', '""'),  # 直接Assets映射为空
            ('"Assets/Resources/minigame/"', '"Resources/minigame/"')
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        # 保存修改
        with open(self.art_resource_manager_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 方案2应用完成")
        print("📋 效果：资源将使用简化的Resources路径")
        print("🎯 目标路径示例：CommonResource/Resources/minigame/entity/140492/...")
    
    def restore_backup(self):
        """恢复备份"""
        if os.path.exists(self.backup_file):
            shutil.copy2(self.backup_file, self.art_resource_manager_file)
            print(f"✅ 已恢复备份：{self.backup_file}")
        else:
            print("⚠️ 未找到备份文件")
    
    def interactive_fix(self):
        """交互式修复"""
        self.show_options()
        
        while True:
            print("\n请选择修复方案（输入数字）：")
            print("1 - 禁用路径映射（推荐）")
            print("2 - 简化路径映射") 
            print("3 - 保持当前设置")
            print("9 - 恢复备份")
            print("0 - 退出")
            
            choice = input("您的选择: ").strip()
            
            if choice == "1":
                self.apply_solution_1()
                print("\n🎉 修复完成！请重新启动工具测试上传功能。")
                break
            elif choice == "2":
                self.apply_solution_2()
                print("\n🎉 修复完成！请重新启动工具测试上传功能。")
                break
            elif choice == "3":
                print("保持当前设置，无需修改。")
                break
            elif choice == "9":
                self.restore_backup()
            elif choice == "0":
                print("退出修复工具。")
                break
            else:
                print("❌ 无效选择，请重新输入。")


def main():
    """主函数"""
    fixer = PathMappingFixer()
    fixer.interactive_fix()


if __name__ == "__main__":
    main()

