#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试依赖分析功能 - 验证原始文件meta文件处理
"""

import os
import sys
import tempfile
import shutil

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def create_test_files():
    """创建测试文件"""
    test_dir = tempfile.mkdtemp()
    print(f"📁 创建测试目录: {test_dir}")
    
    # 创建测试文件结构
    files_to_create = [
        # 原始文件
        "test.prefab",
        "test.prefab.meta",
        "material.mat",
        "material.mat.meta",
        "texture.png",
        "texture.png.meta",
        
        # 依赖文件
        "dependency.fbx",
        "dependency.fbx.meta",
        "shader.shader",
        "shader.shader.meta",
    ]
    
    for file_name in files_to_create:
        file_path = os.path.join(test_dir, file_name)
        with open(file_path, 'w') as f:
            if file_name.endswith('.meta'):
                # 创建meta文件内容
                f.write(f"guid: {file_name.replace('.meta', '').replace('.', '')}123456789abcdef\n")
            elif file_name == 'test.prefab':
                # 创建prefab文件，引用其他文件
                f.write('''
{
  "m_GUID": "test123456789abcdef123456789abcdef",
  "materials": [
    {
      "m_GUID": "material123456789abcdef123456789abcdef"
    }
  ],
  "textures": [
    {
      "m_GUID": "texture123456789abcdef123456789abcdef"
    }
  ]
}
                ''')
            elif file_name == 'material.mat':
                # 创建材质文件，引用着色器
                f.write('''
{
  "m_GUID": "material123456789abcdef123456789abcdef",
  "shader": {
    "m_GUID": "shader123456789abcdef123456789abcdef"
  }
}
                ''')
            else:
                # 其他文件
                f.write(f"# Test file: {file_name}\n")
    
    return test_dir

def test_dependency_analysis():
    """测试依赖分析功能"""
    print("🧪 开始测试依赖分析功能...")
    
    # 创建测试文件
    test_dir = create_test_files()
    
    try:
        # 创建分析器
        analyzer = ResourceDependencyAnalyzer()
        
        # 准备测试文件列表（只包含部分原始文件）
        original_files = [
            os.path.join(test_dir, "test.prefab"),
            os.path.join(test_dir, "material.mat"),
        ]
        
        print(f"📄 原始文件: {[os.path.basename(f) for f in original_files]}")
        
        # 执行依赖分析
        result = analyzer.find_dependency_files(original_files, [test_dir])
        
        # 显示结果
        print("\n📊 分析结果:")
        print(f"   原始文件数: {result['analysis_stats']['total_original']}")
        print(f"   依赖文件数: {result['analysis_stats']['total_dependencies']}")
        print(f"   Meta文件数: {result['analysis_stats']['total_meta_files']}")
        print(f"   缺失依赖数: {result['analysis_stats']['total_missing']}")
        
        print("\n📁 找到的依赖文件:")
        for dep_file in result['dependency_files']:
            print(f"   ➕ {os.path.basename(dep_file)}")
        
        print("\n📄 找到的Meta文件:")
        for meta_file in result['meta_files']:
            print(f"   ➕ {os.path.basename(meta_file)}")
        
        # 检查原始文件的meta文件是否被添加
        print("\n🔍 检查原始文件对应的Meta文件:")
        original_meta_files = []
        for file_path in original_files:
            if not file_path.endswith('.meta'):
                meta_path = file_path + '.meta'
                if meta_path in result['meta_files']:
                    original_meta_files.append(os.path.basename(meta_path))
                    print(f"   ✅ {os.path.basename(meta_path)} (对应 {os.path.basename(file_path)})")
                else:
                    print(f"   ❌ 未找到 {os.path.basename(meta_path)} (对应 {os.path.basename(file_path)})")
        
        # 验证结果
        expected_meta_files = ["test.prefab.meta", "material.mat.meta"]
        missing_meta = [f for f in expected_meta_files if f not in original_meta_files]
        
        if missing_meta:
            print(f"\n❌ 测试失败: 缺少原始文件的Meta文件: {missing_meta}")
            return False
        else:
            print(f"\n✅ 测试通过: 所有原始文件的Meta文件都被正确添加")
            return True
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        shutil.rmtree(test_dir)
        print(f"🧹 清理测试目录: {test_dir}")

def main():
    """主函数"""
    print("=" * 60)
    print("🧪 依赖分析功能测试")
    print("=" * 60)
    
    success = test_dependency_analysis()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！")
    else:
        print("❌ 测试失败！")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main() 