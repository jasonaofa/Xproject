# 增加依赖文件功能重复加载问题修复

## 问题描述

在使用"增加依赖文件"功能时，会出现重复加载拖入检查资源的问题，导致GUID重复检查报告错误。

### 典型错误示例
```
问题 1:
文件名: surface_dark.mat
完整路径: C:\6.1.10_prefab\Assets\entity\140489\Timeline\building\Material\surface_dark.mat
问题描述: GUID重复: 3f26866446d8dd44a80d6ca186a7a645 (与C:/6.1.10_prefab/Assets/entity/140489\Timeline\building\Material\surface_dark.mat冲突)
```

## 问题根因分析

### 1. 重复加载流程
1. 用户拖入文件（如 `surface_dark.mat`）到上传列表
2. 点击"增加依赖文件"按钮
3. 系统分析文件依赖关系时，可能会将原始文件再次添加到依赖文件列表
4. 导致同一个文件在上传列表中出现多次

### 2. 路径标准化问题
- 同一个文件的路径可能以不同格式存在（`\` vs `/`）
- 路径比较时未进行标准化，导致重复检查失效

### 3. 具体问题位置
- `_analyze_file_dependencies` 方法：依赖分析时未过滤原始文件
- `_process_dependency_analysis_result` 方法：文件重复检查不完善
- 最终添加文件时缺少标准化路径比较

## 修复方案

### 1. 依赖分析阶段修复

在 `_analyze_file_dependencies` 方法中增加原始文件过滤：

```python
# 标准化原始文件路径列表（用于比较）
normalized_original_files = set()
for orig_file in result['original_files']:
    normalized_original_files.add(os.path.normpath(os.path.abspath(orig_file)))

# 在添加依赖文件前检查是否为原始文件
normalized_dep_file = os.path.normpath(os.path.abspath(dep_file))
if normalized_dep_file not in normalized_original_files:
    result['dependency_files'].append(dep_file)
    # ... 其他处理
else:
    print(f"🔍 [DEBUG] 跳过重复的原始文件: {os.path.basename(dep_file)}")
```

### 2. 结果处理阶段修复

在 `_process_dependency_analysis_result` 方法中增强重复检查：

```python
# 标准化现有上传文件列表（用于重复检查）
normalized_upload_files = set()
for upload_file in self.upload_files:
    normalized_upload_files.add(os.path.normpath(os.path.abspath(upload_file)))

# 使用标准化路径进行重复检查
normalized_dep_file = os.path.normpath(os.path.abspath(dep_file))
if normalized_dep_file not in normalized_upload_files:
    files_to_add.append(dep_file)
    # ... 其他处理
else:
    self.log_text.append(f"🔍 跳过重复的依赖文件: {os.path.basename(dep_file)}")
```

### 3. 最终添加阶段修复

在最终添加文件到上传列表时增加标准化路径检查：

```python
# 使用标准化路径进行重复检查
normalized_file_path = os.path.normpath(os.path.abspath(file_path))
existing_normalized = [os.path.normpath(os.path.abspath(f)) for f in self.upload_files]

if normalized_file_path not in existing_normalized:
    self.upload_files.append(file_path)
    added_count += 1
    self.file_list.add_file_item(file_path)
else:
    self.log_text.append(f"⚠️ 最终检查：跳过重复文件 {os.path.basename(file_path)}")
```

## 修复效果

### 1. 防止重复添加
- 在依赖分析阶段就过滤掉已经在原始文件列表中的文件
- 在结果处理阶段进行二次检查
- 在最终添加阶段进行三重检查

### 2. 路径标准化
- 使用 `os.path.normpath()` 和 `os.path.abspath()` 标准化路径
- 解决不同路径分隔符导致的重复问题

### 3. 详细日志
- 增加详细的调试日志，便于问题追踪
- 明确显示跳过重复文件的原因

## 测试验证

创建了专门的测试脚本 `test_duplicate_fix.py` 来验证修复效果：

```bash
python test_duplicate_fix.py
```

测试结果：
- ✅ 没有发现重复文件
- ✅ 路径标准化正常工作
- ✅ 依赖分析功能正常

## 使用说明

### 修复后的使用流程
1. 拖入要上传的文件
2. 点击"增加依赖文件"按钮
3. 系统会自动分析依赖关系并过滤重复文件
4. 查看日志中的详细信息，确认没有重复添加

### 日志信息解读
- `🔍 [DEBUG] 跳过重复的原始文件: xxx` - 在依赖分析阶段跳过的重复文件
- `🔍 跳过重复的依赖文件: xxx` - 在结果处理阶段跳过的重复文件
- `⚠️ 最终检查：跳过重复文件 xxx` - 在最终添加阶段跳过的重复文件

## 影响范围

### 修改的文件
- `art_resource_manager.py` - 主要修复逻辑

### 修改的方法
- `_analyze_file_dependencies` - 依赖分析时的重复过滤
- `_process_dependency_analysis_result` - 结果处理时的重复检查
- 文件添加逻辑 - 最终添加时的重复检查

### 兼容性
- 修复向后兼容，不影响现有功能
- 只是增加了重复检查逻辑，提高了稳定性

## 常见问题

### Q: 为什么需要三重检查？
A: 
1. 第一重：在依赖分析阶段防止将原始文件当作依赖文件
2. 第二重：在结果处理阶段防止重复的依赖文件
3. 第三重：在最终添加阶段的保险检查

### Q: 路径标准化的作用是什么？
A: 解决同一文件因路径格式不同（如 `\` vs `/`）而被误认为是不同文件的问题。

### Q: 修复后会影响性能吗？
A: 影响微乎其微，因为只是增加了路径标准化和集合查找操作，对于一般的文件数量来说开销很小。

## 总结

本次修复彻底解决了"增加依赖文件"功能中的重复加载问题，通过多层次的重复检查和路径标准化，确保同一个文件不会被重复添加到上传列表中，从而避免了后续的GUID重复检查报错。 