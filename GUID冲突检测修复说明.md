# 🔧 GUID冲突检测修复说明

## 📋 问题描述

用户反馈：当同一个GUID的文件名被修改时，新版本工具没有检查出GUID冲突，而老版本能检查出来。

**具体问题案例：**
- 上传文件：`tuowei.png` (GUID: `e795133ea527d4348b10c3cc9108efe1`)
- Git中已存在：`003813q8nbwrwqbkhalrpa.png` (相同GUID)
- 路径映射后目录相同，但文件名不同
- 预期：应该检测为GUID冲突
- 实际：被误认为是文件更新

## 🔍 问题根因

在 `_compare_file_paths()` 方法中，缺少对"同目录不同文件名"情况的专门处理。当路径映射规则将两个路径映射到相同目录后，如果文件名不同，应该识别为GUID冲突，而不是文件更新。

## ✅ 修复内容

### 1. 增强路径比较逻辑

**修改文件：** `art_resource_manager.py` 第3953-4000行

**核心修复：**
```python
# 关键修复：检查是否只是文件名不同
# 分离目录和文件名
upload_dir = '/'.join(mapped_upload_normalized.split('/')[:-1])
upload_filename = mapped_upload_normalized.split('/')[-1]
git_dir = '/'.join(git_normalized.split('/')[:-1])  
git_filename = git_normalized.split('/')[-1]

if upload_dir.lower() == git_dir.lower() and upload_filename.lower() != git_filename.lower():
    # 同目录不同文件名 - 这是GUID冲突，不是文件更新
    return False
```

### 2. 添加详细调试信息

为同目录不同文件名的情况提供清晰的调试反馈：
```python
self.status_updated.emit(f"🔍 GUID冲突检测:")
self.status_updated.emit(f"  上传路径: '{upload_normalized}' -> '{mapped_upload_normalized}'")
self.status_updated.emit(f"  Git路径: '{git_normalized}'")
self.status_updated.emit(f"  结果: 同目录'{upload_dir}'下不同文件名 '{upload_filename}' vs '{git_filename}' -> GUID冲突")
```

### 3. 完善注释和文档

为 `_compare_file_paths()` 方法添加了详细的注释，说明其职责和逻辑。

## 🎯 修复效果

### 修复前
- `tuowei.png` vs `003813q8nbwrwqbkhalrpa.png` → 被误认为文件更新 ❌

### 修复后  
- `tuowei.png` vs `003813q8nbwrwqbkhalrpa.png` → 正确识别为GUID冲突 ✅

## 📊 测试验证

| 测试案例 | 上传路径 | Git路径 | 期望结果 | 修复后结果 |
|---------|---------|---------|----------|------------|
| 同目录不同文件名 | `Assets/entity/.../tuowei.png` | `Assets/Resources/minigame/entity/.../003813q8nbwrwqbkhalrpa.png` | GUID冲突 | ✅ GUID冲突 |
| 完全相同路径 | `Assets/entity/.../file.png` | `Assets/Resources/minigame/entity/.../file.png` | 文件更新 | ✅ 文件更新 |
| 完全不同路径 | `Assets/entity/A/file.png` | `Assets/Resources/minigame/entity/B/other.png` | GUID冲突 | ✅ GUID冲突 |

## 🔄 影响范围

**修改方法：**
- `_compare_file_paths()` - 增强文件路径比较逻辑

**影响功能：**
- GUID唯一性检查 (`_check_guid_uniqueness()`)
- 资源冲突检测
- 文件更新判断

**兼容性：**
- ✅ 向下兼容，不影响现有正常功能
- ✅ 增强检测能力，减少漏检
- ✅ 提供更详细的调试信息

## 🚀 使用说明

1. **无需额外配置** - 修复自动生效
2. **查看详细日志** - 工具会在状态栏显示详细的路径比较过程
3. **GUID冲突检测** - 现在能正确识别同目录不同文件名的GUID冲突情况

## 📝 注意事项

- 修复不影响正常的文件更新流程
- 路径映射规则保持不变
- 调试信息仅在检测到冲突时显示，避免日志过多
- 确保Git仓库中相同GUID不同文件名的情况能被正确检测 