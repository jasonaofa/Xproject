# Git CRLF 问题解决指南

## 🚨 问题描述

如果您遇到以下错误：
```
fatal: LF would be replaced by CRLF in art_resource_manager.py
fatal: LF would be replaced by CRLF in Assets/Resources/xxx/file.mesh
```

这是Windows和Unix/Linux系统换行符差异导致的。

## 📍 问题分类

### 情况1：软件本身的文件（如 art_resource_manager.py）

**问题源**：这个工具的源代码仓库  
**影响范围**：仅影响工具开发  
**解决方案**：

```bash
# 在工具的源代码目录执行
cd /path/to/tool/source
git config core.autocrlf false
git config core.safecrlf false
git add --renormalize .
git commit -m "Fix CRLF issues"
```

### 情况2：推送到目标仓库的文件

**问题源**：目标Git仓库的换行符设置  
**影响范围**：可能影响团队协作  
**解决方案**：

## 🛠️ 推荐解决方案（按保守程度排序）

### 方案1：临时解决（最保守）
```bash
# 仅在目标仓库临时设置
cd "目标Git仓库路径"
git config core.safecrlf false
# 然后重新推送
```

### 方案2：使用独立工具
```bash
# 使用提供的修复工具
python fix_git_crlf.py "目标Git仓库路径"
```

### 方案3：手动配置（需团队讨论）
```bash
# 在目标仓库创建 .gitattributes 文件
cd "目标Git仓库路径"
echo "* text=auto" > .gitattributes
echo "*.mesh binary" >> .gitattributes
echo "*.prefab text" >> .gitattributes
git add .gitattributes
git commit -m "Add gitattributes for line ending handling"
```

### 方案4：全局设置（影响最大，需谨慎）
```bash
# 全局设置（影响所有Git仓库）
git config --global core.autocrlf false
git config --global core.safecrlf false
```

## ⚠️ 重要注意事项

1. **团队协作**：修改Git配置前请与团队讨论
2. **备份重要**：操作前建议备份重要数据
3. **测试环境**：建议先在测试环境验证
4. **版本控制**：`.gitattributes` 文件应该提交到版本控制

## 🔧 工具功能调整

为保护团队协作环境，本工具已调整为：

- ✅ **不会自动修改**目标仓库的Git配置
- ✅ **遇到CRLF问题时**提供明确的解决指导
- ✅ **提供独立工具**进行精确控制
- ✅ **保护现有设置**，避免影响团队协作

## 📞 技术支持

如果问题持续存在，请：

1. 检查具体的错误信息
2. 确认是哪个仓库的问题（工具源码 vs 目标仓库）
3. 与团队讨论最适合的解决方案
4. 使用提供的独立工具进行修复

## 📝 最佳实践

1. **新项目**：在项目开始时就配置好 `.gitattributes`
2. **现有项目**：与团队协商统一的换行符策略
3. **跨平台**：使用 `* text=auto` 让Git自动处理
4. **二进制文件**：明确标记为 `binary` 避免转换 