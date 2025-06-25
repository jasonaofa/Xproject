import re

# 测试内容 - 来自实际的meta文件
content1 = '''{
    "m_MetaHeader": {
        "m_Version": 1,
        "m_GUID": "e582b3945840dea40a4bcbee5bc25301",
        "m_AssetType": 0
    },
    "m_AssetImport": {}
}'''

content2 = '''{
    "m_MetaHeader": {
        "m_Version": 1,
        "m_GUID": "692b05ce957cc0d40a5cf5d3b9f669b8",
        "m_AssetType": 13
    },
    "m_AssetImport": {}
}'''

# 当前使用的正则表达式
current_pattern = r'"m_GUID":\s*"([a-f0-9]{32})"'

# 测试YAML格式的模式
yaml_pattern = r'guid:\s*([a-f0-9]{32})'

print("=== 测试当前正则表达式 ===")
print("Pattern:", current_pattern)

for i, content in enumerate([content1, content2], 1):
    print(f"\n--- Content {i} ---")
    match = re.search(current_pattern, content)
    if match:
        print(f"✅ 匹配成功: {match.group(1)}")
    else:
        print("❌ 匹配失败")
        # 尝试找出原因
        print("Content snippet:", repr(content[content.find('"m_GUID"'):content.find('"m_GUID"')+50]))

print("\n=== 测试改进的正则表达式 ===")
# 更宽松的模式，允许更多空格和换行
improved_pattern = r'"m_GUID":\s*"([a-f0-9]{32})"'

for i, content in enumerate([content1, content2], 1):
    print(f"\n--- Content {i} ---")
    match = re.search(improved_pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        print(f"✅ 匹配成功: {match.group(1)}")
    else:
        print("❌ 匹配失败") 