#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置热更新服务器开机自启动
支持Windows系统
"""

import os
import sys
import shutil
import winreg
from pathlib import Path

def get_startup_folder():
    """获取Windows启动文件夹路径"""
    try:
        # 获取当前用户的启动文件夹
        startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        return startup_folder
    except Exception as e:
        print(f"❌ 获取启动文件夹失败: {e}")
        return None

def create_startup_batch():
    """创建启动批处理文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建启动批处理内容
    batch_content = f'''@echo off
title 美术资源热更新服务器
cd /d "{current_dir}"
echo 🚀 正在启动美术资源热更新服务器...
echo 📍 工作目录: {current_dir}
echo 🔄 启动服务器中...
python simple_file_update_server.py
'''
    
    return batch_content

def add_to_startup_folder():
    """添加到启动文件夹"""
    try:
        startup_folder = get_startup_folder()
        if not startup_folder:
            return False
            
        if not os.path.exists(startup_folder):
            os.makedirs(startup_folder)
        
        # 创建启动批处理文件
        batch_content = create_startup_batch()
        startup_batch_path = os.path.join(startup_folder, "美术资源热更新服务器.bat")
        
        with open(startup_batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        print(f"✅ 已添加到启动文件夹: {startup_batch_path}")
        return True
        
    except Exception as e:
        print(f"❌ 添加到启动文件夹失败: {e}")
        return False

def add_to_registry():
    """添加到注册表启动项"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        batch_path = os.path.join(current_dir, "后台启动热更新服务器.bat")
        
        # 打开注册表项
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Run", 
                           0, winreg.KEY_SET_VALUE)
        
        # 设置启动项
        winreg.SetValueEx(key, "美术资源热更新服务器", 0, winreg.REG_SZ, batch_path)
        winreg.CloseKey(key)
        
        print(f"✅ 已添加到注册表启动项: {batch_path}")
        return True
        
    except Exception as e:
        print(f"❌ 添加到注册表失败: {e}")
        return False

def remove_from_startup():
    """从启动项中移除"""
    success = True
    
    # 从启动文件夹移除
    try:
        startup_folder = get_startup_folder()
        if startup_folder:
            startup_batch_path = os.path.join(startup_folder, "美术资源热更新服务器.bat")
            if os.path.exists(startup_batch_path):
                os.remove(startup_batch_path)
                print("✅ 已从启动文件夹移除")
            else:
                print("ℹ️ 启动文件夹中未找到启动文件")
    except Exception as e:
        print(f"❌ 从启动文件夹移除失败: {e}")
        success = False
    
    # 从注册表移除
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Run", 
                           0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "美术资源热更新服务器")
        winreg.CloseKey(key)
        print("✅ 已从注册表启动项移除")
    except FileNotFoundError:
        print("ℹ️ 注册表中未找到启动项")
    except Exception as e:
        print(f"❌ 从注册表移除失败: {e}")
        success = False
    
    return success

def check_startup_status():
    """检查启动项状态"""
    print("📊 检查开机启动状态...")
    
    # 检查启动文件夹
    startup_folder = get_startup_folder()
    if startup_folder:
        startup_batch_path = os.path.join(startup_folder, "美术资源热更新服务器.bat")
        if os.path.exists(startup_batch_path):
            print(f"✅ 启动文件夹: {startup_batch_path}")
        else:
            print("❌ 启动文件夹: 未设置")
    
    # 检查注册表
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Run", 
                           0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "美术资源热更新服务器")
        winreg.CloseKey(key)
        print(f"✅ 注册表启动项: {value}")
    except FileNotFoundError:
        print("❌ 注册表启动项: 未设置")
    except Exception as e:
        print(f"❌ 注册表检查失败: {e}")

def main():
    """主函数"""
    print("═══════════════════════════════════════")
    print("    美术资源热更新服务器开机启动设置")
    print("═══════════════════════════════════════")
    print()
    
    while True:
        print("请选择操作:")
        print("[1] 设置开机启动（启动文件夹方式）")
        print("[2] 设置开机启动（注册表方式，推荐）")
        print("[3] 移除开机启动")
        print("[4] 检查启动状态")
        print("[5] 测试启动批处理文件")
        print("[0] 退出")
        print()
        
        choice = input("请输入选择 (0-5): ").strip()
        
        if choice == "1":
            print("\n🔧 设置启动文件夹方式...")
            if add_to_startup_folder():
                print("✅ 设置成功！服务器将在下次开机时自动启动")
            else:
                print("❌ 设置失败")
                
        elif choice == "2":
            print("\n🔧 设置注册表方式...")
            if add_to_registry():
                print("✅ 设置成功！服务器将在下次开机时自动启动")
            else:
                print("❌ 设置失败")
                
        elif choice == "3":
            print("\n🗑️ 移除开机启动...")
            if remove_from_startup():
                print("✅ 移除成功！")
            else:
                print("❌ 移除失败")
                
        elif choice == "4":
            print()
            check_startup_status()
            
        elif choice == "5":
            print("\n🧪 测试启动批处理文件...")
            batch_path = "后台启动热更新服务器.bat"
            if os.path.exists(batch_path):
                print(f"🔄 运行: {batch_path}")
                os.system(f'"{batch_path}"')
            else:
                print(f"❌ 文件不存在: {batch_path}")
                
        elif choice == "0":
            print("\n👋 再见！")
            break
            
        else:
            print("❌ 无效选择，请重新输入")
        
        print("\n" + "─" * 40 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        input("按回车键退出...")

