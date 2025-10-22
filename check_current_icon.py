#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查当前图标文件状态
"""

import os
from PIL import Image

def check_icon_colors():
    """检查图标文件的颜色"""
    icons = {
        "app_icon.ico": "红色图标",
        "app_icon_lv.ico": "绿色图标", 
        "app_icon_bai.ico": "白色图标"
    }
    
    for icon_file, description in icons.items():
        if os.path.exists(icon_file):
            try:
                with Image.open(icon_file) as img:
                    # 获取颜色信息
                    colors = img.getcolors(maxcolors=256*256*256)
                    if colors:
                        most_common = max(colors, key=lambda x: x[0])
                        color_rgb = most_common[1][:3]  # 只取RGB，忽略Alpha
                        
                        print(f"📁 {description} ({icon_file}):")
                        print(f"   文件大小: {os.path.getsize(icon_file)} 字节")
                        print(f"   主要颜色: RGB{color_rgb}")
                        
                        # 判断颜色类型
                        r, g, b = color_rgb
                        if r > 200 and g > 200 and b > 200:
                            color_type = "白色系"
                        elif r > 150 and g < 100 and b < 100:
                            color_type = "红色系"
                        elif r < 100 and g > 150 and b < 100:
                            color_type = "绿色系"
                        else:
                            color_type = "其他颜色"
                        
                        print(f"   颜色类型: {color_type}")
                        print()
                        
            except Exception as e:
                print(f"❌ 无法分析 {icon_file}: {e}")
        else:
            print(f"❌ {description} 文件不存在: {icon_file}")

if __name__ == "__main__":
    print("🔍 检查当前图标文件...")
    check_icon_colors()





