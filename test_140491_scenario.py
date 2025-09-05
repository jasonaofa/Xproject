#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试140491 prefab的具体场景

场景：
- prefab引用了GUID: e548bb486af857d43ba3118a2fa2f675 (body_skin.mat)
- body_skin.mat文件被删除（或meta被删除，或两者都删除）
- 检查工具应该检测到这个缺失的GUID引用
"""

import re
import os
import tempfile

def create_140491_prefab_sample():
    """创建模拟140491 prefab的关键部分"""
    prefab_content = '''
{
    "m_GUID": "0c5f75cac480a9c47b9319e65540c142",
    "m_RootObjectIdentifier": {
        "m_GUID": "0c5f75cac480a9c47b9319e65540c142",
        "m_PersistentID": 5095957550897127358
    },
    "Objects": [
        {
            "m_RootObjectTypeID": 207,
            "m_SourcePrefabGUID": "e548bb486af857d43ba3118a2fa2f675",
            "Debug_Path": "F:/Minigame_Art_NewPrefab_6.1.10/Assets/remotes/entity/140491/Material/body_skin.mat",
            "m_RootObject": {
                "m_PersistentID": 1049748099054771261,
                "m_GUID": "e548bb486af857d43ba3118a2fa2f675"
            }
        }
    ]
}
'''
    return prefab_content.strip()

def test_json_guid_extraction():
    """测试JSON格式的GUID提取"""
    print("=" * 80)
    print("测试JSON格式GUID提取")
    print("=" * 80)
    
    content = create_140491_prefab_sample()
    print(f"🔍 测试内容（JSON格式prefab）")
    
    # 当前代码中的JSON GUID提取模式
    guid_patterns = [
        r'"m_GUID":\s*"([a-f0-9]{32})"',  # 标准m_GUID格式
        r'"guid":\s*"([a-f0-9]{32})"',    # 标准guid格式
        r'"GUID":\s*"([a-f0-9]{32})"',    # 大写GUID格式
        r'"texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"',  # 贴图引用
        r'"texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"', # 贴图m_GUID引用
        r'"m_Texture":\s*{[^}]*"guid":\s*"([a-f0-9]{32})"', # m_Texture引用
        r'"m_Texture":\s*{[^}]*"m_GUID":\s*"([a-f0-9]{32})"', # m_Texture m_GUID引用
    ]
    
    all_found_guids = set()
    
    for i, pattern in enumerate(guid_patterns):
        try:
            guids = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if guids:
                print(f"   模式 {i+1}: 找到 {len(guids)} 个GUID")
                for guid in guids:
                    all_found_guids.add(guid.lower())
                    print(f"      {guid}")
            else:
                print(f"   模式 {i+1}: 无匹配")
        except Exception as e:
            print(f"   模式 {i+1}: 错误 - {e}")
    
    print(f"\n📊 总结:")
    print(f"   总共找到 {len(all_found_guids)} 个唯一GUID")
    
    # 检查是否找到了关键的body_skin.mat GUID
    target_guid = "e548bb486af857d43ba3118a2fa2f675"
    if target_guid in all_found_guids:
        print(f"   ✅ 找到目标GUID: {target_guid} (body_skin.mat)")
        return True
    else:
        print(f"   ❌ 未找到目标GUID: {target_guid} (body_skin.mat)")
        print(f"   🔍 找到的GUID: {all_found_guids}")
        return False

def test_improved_json_patterns():
    """测试改进的JSON GUID提取模式"""
    print(f"\n" + "=" * 80)
    print("测试改进的JSON GUID提取模式")
    print("=" * 80)
    
    content = create_140491_prefab_sample()
    
    # 改进的模式，专门处理JSON格式
    improved_patterns = [
        r'"m_GUID":\s*"([a-f0-9]{32})"',  # 标准m_GUID
        r'"GUID":\s*"([a-f0-9]{32})"',    # 大写GUID  
        r'"guid":\s*"([a-f0-9]{32})"',    # 小写guid
        r'"SourcePrefabGUID":\s*"([a-f0-9]{32})"',  # SourcePrefabGUID
        r'"m_SourcePrefabGUID":\s*"([a-f0-9]{32})"',  # m_SourcePrefabGUID
        r'([a-f0-9]{32})',  # 通用32位十六进制（后备）
    ]
    
    all_guids = set()
    
    for i, pattern in enumerate(improved_patterns):
        try:
            guids = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if guids:
                print(f"   改进模式 {i+1}: 找到 {len(guids)} 个GUID")
                for guid in guids:
                    all_guids.add(guid.lower())
                    print(f"      {guid}")
            else:
                print(f"   改进模式 {i+1}: 无匹配")
        except Exception as e:
            print(f"   改进模式 {i+1}: 错误 - {e}")
    
    print(f"\n📊 改进模式结果:")
    print(f"   总共找到 {len(all_guids)} 个GUID")
    
    target_guid = "e548bb486af857d43ba3118a2fa2f675"
    if target_guid in all_guids:
        print(f"   ✅ 找到目标GUID: {target_guid}")
        return True
    else:
        print(f"   ❌ 仍未找到目标GUID: {target_guid}")
        return False

def analyze_current_code_issue():
    """分析当前代码可能存在的问题"""
    print(f"\n" + "=" * 80)
    print("分析当前代码可能的问题")
    print("=" * 80)
    
    issues = [
        {
            "问题": "JSON格式检测",
            "描述": "代码可能没有正确识别JSON格式的prefab",
            "影响": "使用了错误的解析模式（YAML而不是JSON）"
        },
        {
            "问题": "m_SourcePrefabGUID模式缺失",
            "描述": "当前的JSON GUID模式没有包含m_SourcePrefabGUID",
            "影响": "无法提取prefab中引用的材质GUID"
        },
        {
            "问题": "文件格式判断逻辑",
            "描述": "parse_editor_asset方法的格式判断可能有问题",
            "影响": "JSON prefab被当作其他格式处理"
        },
        {
            "问题": "调试输出不足",
            "描述": "无法看到具体的GUID提取过程",
            "影响": "难以定位问题所在"
        }
    ]
    
    for issue in issues:
        print(f"\n🔍 {issue['问题']}:")
        print(f"   描述: {issue['描述']}")
        print(f"   影响: {issue['影响']}")
    
    print(f"\n💡 建议修复:")
    print("   1. 添加m_SourcePrefabGUID模式到JSON GUID提取")
    print("   2. 确保JSON格式检测正确")
    print("   3. 增加更详细的调试输出")
    print("   4. 测试具体的140491场景")

def simulate_guid_check_process():
    """模拟GUID检查过程"""
    print(f"\n" + "=" * 80)
    print("模拟GUID检查过程")
    print("=" * 80)
    
    print("📋 检查流程:")
    print("   1. 解析140491.prefab -> 提取GUID引用")
    print("   2. 找到引用: e548bb486af857d43ba3118a2fa2f675 (body_skin.mat)")
    print("   3. 检查本地文件: body_skin.mat不存在")
    print("   4. 检查Git仓库: body_skin.mat.meta存在但body_skin.mat不存在")
    print("   5. 孤儿meta文件检测: 跳过此GUID")
    print("   6. GUID引用检查: e548bb486af857d43ba3118a2fa2f675不在有效GUID列表")
    print("   7. 应该报告: guid_reference_missing错误")
    
    print(f"\n🔍 可能的问题点:")
    print("   ❓ 步骤1失败: prefab解析没有提取到GUID")
    print("   ❓ 步骤5问题: 孤儿meta检测逻辑有误")
    print("   ❓ 步骤6问题: GUID引用检查被跳过")

if __name__ == "__main__":
    print("🧪 测试140491 prefab场景")
    
    # 测试当前JSON GUID提取
    current_success = test_json_guid_extraction()
    
    # 测试改进的模式
    improved_success = test_improved_json_patterns()
    
    # 分析问题
    analyze_current_code_issue()
    
    # 模拟检查过程
    simulate_guid_check_process()
    
    print(f"\n" + "=" * 80)
    print("结论")
    print("=" * 80)
    
    if current_success:
        print("✅ 当前JSON解析应该能找到body_skin.mat的GUID")
        print("❓ 问题可能在GUID检查的其他环节")
    else:
        print("❌ 当前JSON解析无法找到body_skin.mat的GUID")
        print("🔧 需要修复JSON GUID提取模式")
    
    if improved_success:
        print("✅ 改进的模式能正确提取GUID")
    
    print(f"\n🎯 下一步:")
    print("   1. 如果GUID提取有问题 -> 修复JSON解析模式")
    print("   2. 如果GUID提取正确 -> 检查GUID引用检查逻辑")
    print("   3. 添加详细调试输出验证每个步骤")
    print("   4. 使用实际140491文件测试")

