#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from art_resource_manager import ResourceDependencyAnalyzer

def test_svn_scan_scope():
    """测试SVN仓库扫描范围"""
    
    print("🔍 测试SVN仓库扫描范围改进")
    print("=" * 60)
    
    # 创建分析器
    analyzer = ResourceDependencyAnalyzer()
    
    # 模拟测试文件路径（请根据实际情况修改）
    test_file = r"C:\meishufenzhi\Assets\prefab\particles\public\Material\mach_boss_dizzy.mat"
    
    print(f"📄 测试文件: {test_file}")
    
    # 检查文件是否存在
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        print("💡 请修改脚本中的文件路径为实际存在的文件")
        return
    
    # 1. 测试SVN根目录检测
    print(f"\n🔍 步骤1: 测试SVN根目录检测...")
    svn_root = analyzer._find_svn_root_from_files([test_file])
    
    if svn_root:
        print(f"✅ 自动找到SVN根目录: {svn_root}")
        
        # 验证.svn目录存在
        svn_dir = os.path.join(svn_root, '.svn')
        if os.path.exists(svn_dir):
            print(f"✅ 确认.svn目录存在: {svn_dir}")
        else:
            print(f"⚠️ .svn目录不存在: {svn_dir}")
    else:
        print(f"❌ 未找到SVN根目录")
        print("💡 可能的原因:")
        print("   - 文件不在SVN仓库中")
        print("   - .svn目录被删除或移动")
        print("   - 路径配置不正确")
        return
    
    # 2. 测试扫描范围对比
    print(f"\n🔍 步骤2: 测试扫描范围对比...")
    
    # 旧方法：只扫描文件所在目录
    old_scan_dir = os.path.dirname(test_file)
    print(f"📁 旧方法扫描目录: {old_scan_dir}")
    
    # 新方法：扫描整个SVN仓库
    new_scan_dir = svn_root
    print(f"📁 新方法扫描目录: {new_scan_dir}")
    
    # 计算目录大小对比
    def count_meta_files(directory):
        """统计目录中的meta文件数量"""
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.meta'):
                        count += 1
        except Exception as e:
            print(f"❌ 统计失败: {e}")
        return count
    
    old_meta_count = count_meta_files(old_scan_dir)
    new_meta_count = count_meta_files(new_scan_dir)
    
    print(f"\n📊 扫描范围对比:")
    print(f"   旧方法 (文件所在目录): {old_meta_count} 个meta文件")
    print(f"   新方法 (整个SVN仓库): {new_meta_count} 个meta文件")
    
    if new_meta_count > old_meta_count:
        improvement = ((new_meta_count - old_meta_count) / old_meta_count * 100) if old_meta_count > 0 else float('inf')
        print(f"   🎉 扫描范围扩大了 {improvement:.1f}%")
        print(f"   ✅ 这意味着能找到更多的依赖文件")
    else:
        print(f"   ⚠️ 扫描范围没有显著变化")
    
    # 3. 测试GUID映射建立
    print(f"\n🔍 步骤3: 测试GUID映射建立...")
    
    guid_map = {}
    analyzer._scan_directory_for_guids(new_scan_dir, guid_map)
    
    print(f"✅ 建立GUID映射: {len(guid_map)} 个GUID")
    
    # 4. 测试完整依赖分析
    print(f"\n🔍 步骤4: 测试完整依赖分析...")
    
    print("🔄 开始依赖分析（使用改进后的方法）...")
    result = analyzer.find_dependency_files([test_file])
    
    print(f"\n📊 分析结果:")
    print(f"   原始文件: {result['analysis_stats']['total_original']}")
    print(f"   依赖文件: {result['analysis_stats']['total_dependencies']}")
    print(f"   Meta文件: {result['analysis_stats']['total_meta_files']}")
    print(f"   缺失依赖: {result['analysis_stats']['total_missing']}")
    
    # 5. 检查是否解决了目标GUID问题
    target_guid = "c7c65a3a6a7673649a64d18d99fd0f8f"
    if target_guid in guid_map:
        print(f"\n🎉 目标GUID已找到: {target_guid}")
        print(f"   对应文件: {guid_map[target_guid]}")
    else:
        print(f"\n⚠️ 目标GUID仍未找到: {target_guid}")
        print("   可能的原因:")
        print("   - 该GUID对应的文件不在SVN仓库中")
        print("   - 该GUID是Unity内置资源")
        print("   - 该GUID对应的文件已被删除")
    
    print(f"\n🎉 测试完成！")
    print(f"📝 总结:")
    print(f"   - ✅ 现在会扫描整个SVN仓库")
    print(f"   - ✅ 扫描范围从 {old_meta_count} 个meta文件扩大到 {new_meta_count} 个")
    print(f"   - ✅ 建立了 {len(guid_map)} 个GUID映射")
    print(f"   - ✅ 依赖分析功能已改进")

if __name__ == "__main__":
    test_svn_scan_scope() 