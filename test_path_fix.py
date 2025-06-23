#!/usr/bin/env python3
"""
测试目标Meta文件路径计算
"""

import os
import tempfile
from art_resource_manager import ResourceChecker, GitSvnManager

def test_target_meta_path():
    """测试目标Meta文件路径计算"""
    print("测试目标Meta文件路径计算...")
    
    # 创建临时Git仓库
    with tempfile.TemporaryDirectory() as temp_dir:
        git_repo_path = os.path.join(temp_dir, "test_git_repo")
        os.makedirs(git_repo_path, exist_ok=True)
        
        # 设置Git管理器
        git_manager = GitSvnManager()
        git_manager.git_path = git_repo_path
        
        # 创建检查器
        checker = ResourceChecker([], git_manager, "CommonResource")
        
        # 测试路径计算
        test_file = "/some/path/wuqi.png"
        target_meta_path = checker._get_target_meta_path(test_file)
        
        print(f"Git仓库路径: {git_repo_path}")
        print(f"目标目录: CommonResource")
        print(f"测试文件: {test_file}")
        print(f"计算的目标Meta路径: {target_meta_path}")
        
        # 验证路径格式
        expected_path = os.path.join(git_repo_path, "CommonResource", "wuqi.png.meta")
        print(f"期望的路径: {expected_path}")
        
        is_correct = target_meta_path == expected_path
        print(f"路径正确: {is_correct}")
        
        # 检查是否有重复的CommonResource
        has_duplicate = "CommonResource\\CommonResource" in target_meta_path or "CommonResource/CommonResource" in target_meta_path
        print(f"是否有重复目录: {has_duplicate}")
        
        return is_correct and not has_duplicate

def test_actual_check():
    """测试实际的检查功能"""
    print("\n测试实际的Meta文件检查功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建Git仓库和CommonResource目录
        git_repo_path = os.path.join(temp_dir, "test_git_repo")
        common_resource_path = os.path.join(git_repo_path, "CommonResource")
        os.makedirs(common_resource_path, exist_ok=True)
        
        # 创建测试文件
        test_file = os.path.join(temp_dir, "wuqi.png")
        with open(test_file, 'w') as f:
            f.write("fake png content")
        
        # 设置Git管理器
        git_manager = GitSvnManager()
        git_manager.git_path = git_repo_path
        
        # 测试场景1：目标位置没有meta文件
        print("场景1：目标位置没有meta文件")
        checker = ResourceChecker([test_file], git_manager, "CommonResource")
        issues = checker._check_meta_files()
        print(f"检查结果: {len(issues)} 个问题")
        if issues:
            issue = issues[0]
            print(f"目标位置: {issue.get('expected_target_meta', 'N/A')}")
        
        # 测试场景2：在目标位置创建meta文件
        print("\n场景2：目标位置存在meta文件")
        target_meta_path = os.path.join(common_resource_path, "wuqi.png.meta")
        with open(target_meta_path, 'w') as f:
            f.write('{"m_MetaHeader": {"m_GUID": "test-guid"}}')
        
        checker = ResourceChecker([test_file], git_manager, "CommonResource")
        issues = checker._check_meta_files()
        print(f"检查结果: {len(issues)} 个问题")
        print(f"Meta文件存在: {os.path.exists(target_meta_path)}")
        
        return len(issues) == 0  # 第二个场景应该没有问题

def main():
    """主测试函数"""
    print("=" * 50)
    print("目标Meta文件路径计算测试")
    print("=" * 50)
    
    try:
        # 测试路径计算
        path_test_result = test_target_meta_path()
        print(f"路径计算测试: {'✓ 通过' if path_test_result else '✗ 失败'}")
        
        # 测试实际检查
        check_test_result = test_actual_check()
        print(f"实际检查测试: {'✓ 通过' if check_test_result else '✗ 失败'}")
        
        print("\n" + "=" * 50)
        if path_test_result and check_test_result:
            print("🎉 所有测试通过！路径计算修复成功。")
        else:
            print("⚠️ 部分测试失败，需要进一步检查。")
            
    except Exception as e:
        print(f"测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 