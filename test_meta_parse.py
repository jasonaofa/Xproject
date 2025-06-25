import re
import os

def parse_meta_file(meta_path: str) -> str:
    """解析meta文件获取GUID"""
    try:
        with open(meta_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # 支持YAML格式 - guid: xxxxx
            yaml_match = re.search(r'guid:\s*([a-f0-9]{32})', content, re.IGNORECASE)
            if yaml_match:
                return yaml_match.group(1).lower()
            
            # 支持JSON格式 - "m_GUID": "xxxxx" (字符串形式)
            json_match = re.search(r'"m_GUID":\s*"([a-f0-9]{32})"', content, re.IGNORECASE)
            if json_match:
                return json_match.group(1).lower()
            
            # 忽略对象形式的GUID (如 "m_GUID": { "data[0]": ... })
            # 这种格式我们选择忽略，不进行处理
            
    except Exception as e:
        print(f"解析meta文件失败: {meta_path}, 错误: {e}")
    return None

# 测试Materials目录下的meta文件
materials_dir = "test_files/Materials"
if os.path.exists(materials_dir):
    print(f"=== 测试 {materials_dir} 目录下的meta文件 ===")
    
    meta_files = [f for f in os.listdir(materials_dir) if f.endswith('.meta')]
    
    success_count = 0
    total_count = len(meta_files)
    
    for meta_file in meta_files[:10]:  # 只测试前10个文件
        meta_path = os.path.join(materials_dir, meta_file)
        print(f"\n测试文件: {meta_file}")
        
        guid = parse_meta_file(meta_path)
        if guid:
            print(f"  ✅ 成功解析: {guid}")
            success_count += 1
        else:
            print(f"  ❌ 解析失败")
            # 显示文件内容的前几行
            try:
                with open(meta_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[:5]
                    print(f"  文件内容预览:")
                    for line in lines:
                        print(f"    {line.strip()}")
            except:
                pass
    
    print(f"\n=== 测试结果 ===")
    print(f"成功解析: {success_count}/{min(10, total_count)}")
    print(f"总meta文件数: {total_count}")
else:
    print(f"目录不存在: {materials_dir}") 