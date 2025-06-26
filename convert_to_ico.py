#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图标转换工具 - 将其他格式的图片转换为ico格式
使用方法：python convert_to_ico.py your_image.png
"""

import sys
import os
from pathlib import Path

def convert_to_ico(input_file, output_file="app_icon.ico"):
    """将图片转换为ico格式"""
    try:
        from PIL import Image
        
        # 打开输入图片
        img = Image.open(input_file)
        
        # 转换为RGBA模式以支持透明度
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 创建多种尺寸的图标
        sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        
        # 保存为ico格式
        img.save(output_file, format='ICO', sizes=sizes)
        
        print(f"✅ 成功转换: {input_file} -> {output_file}")
        print(f"📁 图标文件已保存到: {os.path.abspath(output_file)}")
        
    except ImportError:
        print("❌ 错误：未安装Pillow库")
        print("请运行以下命令安装：pip install Pillow")
        return False
    except Exception as e:
        print(f"❌ 转换失败：{str(e)}")
        return False
    
    return True

def main():
    print("=" * 60)
    print("🎨 图标转换工具")
    print("=" * 60)
    
    if len(sys.argv) != 2:
        print("使用方法：python convert_to_ico.py <图片文件>")
        print("支持的格式：png, jpg, jpeg, bmp, gif等")
        print("示例：python convert_to_ico.py my_icon.png")
        return
    
    input_file = sys.argv[1]
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"❌ 错误：文件不存在 - {input_file}")
        return
    
    # 检查文件格式
    supported_formats = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}
    file_ext = Path(input_file).suffix.lower()
    
    if file_ext not in supported_formats:
        print(f"❌ 错误：不支持的文件格式 - {file_ext}")
        print(f"supported formats: {', '.join(supported_formats)}")
        return
    
    # 执行转换
    if convert_to_ico(input_file):
        print("\n💡 使用说明：")
        print("1. 生成的 app_icon.ico 文件已放在项目根目录")
        print("2. 现在可以运行打包脚本，图标将自动应用到exe文件")
        print("3. 运行命令：python build_exe.py 或 python simple_build.py")

if __name__ == "__main__":
    main() 