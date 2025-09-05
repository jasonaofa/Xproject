# 🌐 Avatar/MiniUniverse子目录支持说明

## 📋 新功能概述

美术资源上传工具现已支持检查 `avatar/MiniUniverse` 子目录下的avatar文件包，与普通avatar目录使用相同的检查规则。

## 🎯 支持的目录结构

### ✅ 现在支持的路径
```
Assets/
├── avatar/
│   ├── 1000_1018/          # 普通Avatar文件包
│   │   ├── all.filelist
│   │   ├── Texture/
│   │   └── ...
│   └── MiniUniverse/       # 🆕 新支持的子目录
│       ├── 2000_237/       # MiniUniverse Avatar文件包
│       │   ├── all.filelist
│       │   ├── Texture/
│       │   └── ...
│       └── 3000_456/
│           ├── all.filelist
│           └── ...
```

## 🔍 检查功能

### 自动检测
- ✅ **自动识别**普通avatar和MiniUniverse子目录
- ✅ **统一规则**两种目录使用相同的all.filelist检查规则
- ✅ **区分显示**在状态信息中明确显示文件包位置

### 检查内容
1. **all.filelist文件存在性检查**
2. **all.filelist文件内容完整性检查**
3. **GUID记录完整性验证**
4. **文件包内文件与清单匹配检查**

## 📊 状态信息示例

### 检查过程中的状态显示

#### 发现文件包
```
发现 5 个avatar文件包需要检查 (其中2个在MiniUniverse子目录)
```

#### 检查具体文件包
```
检查avatar文件包: 1000_1018
检查avatar/MiniUniverse文件包: 2000_237
检查avatar/MiniUniverse文件包: 3000_456
```

#### 检查结果
```
✅ avatar文件包 1000_1018 的all.filelist检查通过
✅ avatar/MiniUniverse文件包 2000_237 的all.filelist检查通过
```

### 总结信息
```
✅ 所有Avatar文件包的all.filelist检查通过 (包含2个MiniUniverse文件包)
```

## 🚨 错误信息示例

### 缺少all.filelist文件
```
🔴 缺少Avatar文件清单
avatar/MiniUniverse文件包 2000_237 缺少 all.filelist 文件
```

### all.filelist不完整
```
🔴 Avatar文件清单不完整
all.filelist 缺少 3 个文件的GUID记录: body.png, face.png, hair.mat
```

## 🛠️ 使用方法

### 1. 文件准备
- 将MiniUniverse的avatar文件放在 `Assets/avatar/MiniUniverse/` 目录下
- 每个文件包必须包含 `all.filelist` 文件
- 文件包结构与普通avatar相同

### 2. 上传检查
- 拖拽整个文件夹到上传工具
- 工具会自动检测并分别处理普通avatar和MiniUniverse文件包
- 检查规则完全相同，无需特殊配置

### 3. 结果查看
- 在状态信息中可以看到明确的位置标识
- 错误信息会指明具体是哪个目录下的文件包
- 统计信息会区分显示两种类型的文件包数量

## 📝 注意事项

1. **目录名称**: MiniUniverse子目录名称不区分大小写
2. **检查规则**: 与普通avatar使用完全相同的检查规则
3. **文件结构**: 文件包内部结构必须与普通avatar保持一致
4. **all.filelist**: 必须包含文件包内所有文件的GUID记录

## 🎉 优势

- **🔄 无缝集成**: 无需修改现有工作流程
- **📊 清晰区分**: 状态信息明确显示文件包位置
- **🎯 统一标准**: 使用相同的质量检查标准
- **⚡ 自动识别**: 智能检测不同目录结构

---

**版本更新**: 现已支持Avatar/MiniUniverse子目录检查
**兼容性**: 完全向后兼容，不影响现有avatar文件包检查


