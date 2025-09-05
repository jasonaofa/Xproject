# 🎯 Timeline文件夹材质模板特殊规则

## 📋 功能概述

为了支持Timeline动画制作的需求，工具现在允许`entity`目录下`Timeline`文件夹内的材质使用特殊的模板：
- `DefaultMaterial.templatemat`
- `DefaultToonMat.templatemat`

## 🎪 适用范围

### ✅ 允许使用特殊模板的路径模式
```
Assets/entity/{任意编号}/Timeline/{任意子目录}/.../*.mat
```

**示例：**
- `Assets/entity/140467/Timeline/prefab/Material/effect.mat` ✅
- `Assets/entity/100001/Timeline/Animation/material.mat` ✅  
- `Assets/entity/999999/Timeline/effect.mat` ✅

### ❌ 不允许使用特殊模板的路径
```
Assets/entity/{任意编号}/{非Timeline目录}/.../*.mat
```

**示例：**
- `Assets/entity/140467/Model/Material/character.mat` ❌
- `Assets/entity/100001/Prefab/material.mat` ❌
- `Assets/entity/999999/effect.mat` ❌

## 🔧 技术实现

### 关键代码修改位置
**文件：** `art_resource_manager.py`  
**方法：** `_check_material_templates()`  
**行数：** 约4320-4380行

### 实现逻辑
```python
# 检查文件是否在Timeline文件夹下
is_timeline_material = False
normalized_path = os.path.normpath(file_path)
path_parts = normalized_path.split(os.sep)

# 查找entity目录索引
entity_index = -1
for i, part in enumerate(path_parts):
    if part.lower() == 'entity':
        entity_index = i
        break

if entity_index != -1:
    # 检查是否在entity/.../Timeline/...路径下
    remaining_parts = path_parts[entity_index + 1:]
    for part in remaining_parts:
        if part.lower() == 'timeline':
            is_timeline_material = True
            break
```

### 模板验证逻辑
```python
# Timeline文件夹下材质的额外允许模板
timeline_allowed_templates = {
    'DefaultMaterial.templatemat',
    'DefaultToonMat.templatemat'
}

# 验证逻辑
if template_name in allowed_templates:
    # 标准模板检查
    found_valid_template = True
elif is_timeline_material and template_name in timeline_allowed_templates:
    # Timeline特殊规则检查
    found_valid_template = True
else:
    # 不允许的模板，报告错误
    pass
```

## 📊 允许的模板总览

### Timeline文件夹下可用模板（完整列表）
| 模板类型 | 模板名称 | 适用场景 |
|---------|---------|---------|
| **特殊模板** | `DefaultMaterial.templatemat` | Timeline动画专用 |
| **特殊模板** | `DefaultToonMat.templatemat` | Timeline卡通材质 |
| **角色模板** | `Character_NPR_Opaque.templatemat` | NPR不透明角色 |
| **角色模板** | `Character_NPR_Masked.templatemat` | NPR遮罩角色 |
| **角色模板** | `Character_NPR_Tranclucent.templatemat` | NPR半透明角色 |
| **场景模板** | `Scene_Prop_Opaque.templatemat` | 场景道具不透明 |
| **特效模板** | `fx_basic_ADD.templatemat` | 基础叠加特效 |
| ... | （其他所有标准模板）| - |

### 非Timeline文件夹下可用模板
- ✅ 所有标准模板（Character_*, Scene_*, fx_*, 等）
- ❌ **不可使用** `DefaultMaterial.templatemat`
- ❌ **不可使用** `DefaultToonMat.templatemat`

## 🔍 检查日志示例

### Timeline文件夹下使用特殊模板
```
✅ timeline_effect.mat (Timeline) 使用了允许的特殊模板: DefaultMaterial.templatemat
```

### 非Timeline文件夹下使用特殊模板（错误）
```
❌ 使用了不允许的材质模板: DefaultMaterial.templatemat
```

### Timeline文件夹下使用无效模板（错误）
```
❌ 使用了不允许的材质模板: UnknownTemplate.templatemat 
   (Timeline文件夹下可使用: Character_NPR_Opaque.templatemat, ..., DefaultMaterial.templatemat, DefaultToonMat.templatemat, ...)
```

## ✅ 验证测试结果

基于自动化测试验证：

| 测试场景 | 预期结果 | 实际结果 | 状态 |
|---------|---------|---------|-----|
| Timeline + DefaultMaterial | 允许 | 允许 | ✅ |
| Timeline + DefaultToonMat | 允许 | 允许 | ✅ |
| Timeline + 标准模板 | 允许 | 允许 | ✅ |
| Timeline + 无效模板 | 拒绝 | 拒绝 | ✅ |
| 非Timeline + DefaultMaterial | 拒绝 | 拒绝 | ✅ |
| 非Timeline + 标准模板 | 允许 | 允许 | ✅ |

**测试通过率：100%**

## 🚀 使用说明

1. **无需额外配置** - 规则自动生效
2. **路径识别** - 工具自动识别`Timeline`文件夹
3. **错误提示** - 违规使用时提供详细的允许模板列表
4. **向下兼容** - 不影响现有材质检查规则

## 📝 注意事项

- ⚠️  路径匹配**不关心大小写**（timeline、Timeline、TIMELINE 都识别）
- ⚠️  只要路径中包含`Timeline`文件夹即可，无论层级深度
- ⚠️  特殊模板仅在Timeline文件夹下有效，其他位置仍然报错
- ⚠️  Timeline文件夹下仍然可以使用所有标准模板 