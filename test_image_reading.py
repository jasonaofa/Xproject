#!/usr/bin/env python3
"""
测试内置图片读取功能
"""

import sys
import tempfile
import os
from art_resource_manager import ResourceChecker

def test_png_reading():
    """测试PNG图片尺寸读取"""
    print("测试PNG图片尺寸读取...")
    
    # 创建一个简单的PNG文件头 (2048x1536像素)
    png_header = (
        b'\x89PNG\r\n\x1a\n'  # PNG signature
        b'\x00\x00\x00\rIHDR'  # IHDR chunk
        b'\x00\x00\x08\x00'    # width: 2048
        b'\x00\x00\x06\x00'    # height: 1536
        b'\x08\x02\x00\x00\x00'  # bit depth, color type, etc.
        b'\x00\x00\x00\x00'    # CRC (simplified)
    )
    
    # 创建临时PNG文件
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        f.write(png_header)
        temp_png = f.name
    
    try:
        # 测试内置PNG读取
        checker = ResourceChecker([], None, '')
        
        # 测试PIL方法
        width_pil, height_pil = checker._get_image_dimensions_with_pil(temp_png)
        print(f"PIL方法读取结果: {width_pil}x{height_pil}")
        
        # 测试内置方法
        width_builtin, height_builtin = checker._get_image_dimensions_builtin(temp_png)
        print(f"内置方法读取结果: {width_builtin}x{height_builtin}")
        
        # 测试完整的检查流程
        issues = checker._check_image_dimensions()
        print(f"检查结果: 发现{len(issues)}个问题")
        
        return width_builtin == 2048 and height_builtin == 1536
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_png):
            os.unlink(temp_png)

def test_jpeg_reading():
    """测试JPEG图片尺寸读取"""
    print("\n测试JPEG图片尺寸读取...")
    
    # 创建一个简单的JPEG文件头 (1024x768像素)
    jpeg_header = (
        b'\xff\xd8'  # SOI marker
        b'\xff\xe0'  # APP0 marker
        b'\x00\x10'  # length
        b'JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'  # JFIF data
        b'\xff\xc0'  # SOF0 marker
        b'\x00\x11'  # length
        b'\x08'      # precision
        b'\x03\x00'  # height: 768
        b'\x04\x00'  # width: 1024
        b'\x03'      # components
        b'\x01\x22\x00\x02\x11\x01\x03\x11\x01'  # component data
    )
    
    # 创建临时JPEG文件
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(jpeg_header)
        temp_jpg = f.name
    
    try:
        # 测试内置JPEG读取
        checker = ResourceChecker([], None, '')
        
        # 测试PIL方法
        width_pil, height_pil = checker._get_image_dimensions_with_pil(temp_jpg)
        print(f"PIL方法读取结果: {width_pil}x{height_pil}")
        
        # 测试内置方法
        width_builtin, height_builtin = checker._get_image_dimensions_builtin(temp_jpg)
        print(f"内置方法读取结果: {width_builtin}x{height_builtin}")
        
        return width_builtin == 1024 and height_builtin == 768
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_jpg):
            os.unlink(temp_jpg)

def test_unsupported_format():
    """测试不支持的格式"""
    print("\n测试不支持的格式...")
    
    # 创建一个假的BMP文件
    bmp_header = b'BM' + b'\x00' * 50  # 简单的BMP头
    
    with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as f:
        f.write(bmp_header)
        temp_bmp = f.name
    
    try:
        checker = ResourceChecker([], None, '')
        width, height = checker._get_image_dimensions_builtin(temp_bmp)
        print(f"不支持格式读取结果: {width}x{height}")
        
        return width is None and height is None
        
    finally:
        if os.path.exists(temp_bmp):
            os.unlink(temp_bmp)

def main():
    """主测试函数"""
    print("=" * 50)
    print("内置图片读取功能测试")
    print("=" * 50)
    
    # 测试PNG
    png_success = test_png_reading()
    print(f"PNG测试: {'✓ 通过' if png_success else '✗ 失败'}")
    
    # 测试JPEG
    jpeg_success = test_jpeg_reading()
    print(f"JPEG测试: {'✓ 通过' if jpeg_success else '✗ 失败'}")
    
    # 测试不支持的格式
    unsupported_success = test_unsupported_format()
    print(f"不支持格式测试: {'✓ 通过' if unsupported_success else '✗ 失败'}")
    
    print("\n" + "=" * 50)
    if png_success and jpeg_success and unsupported_success:
        print("所有测试通过！内置图片读取功能正常工作。")
    else:
        print("部分测试失败，请检查代码。")
    print("=" * 50)

if __name__ == "__main__":
    main() 