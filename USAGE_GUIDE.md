# 美术资源管理工具使用指南

## 🎯 工具概述

这是一个专为Unity美术资源管理设计的工具，主要解决从SVN仓库向Git仓库传输美术资源时的两个核心问题：

1. **依赖缺失检查** - 确保上传的资源包含所有必要的依赖文件
2. **GUID冲突检查** - 防止资源GUID重复导致的冲突问题

## 🚀 快速开始

### 方法一：使用批处理文件（推荐）
```bash
# 双击运行或在命令行执行
start.bat
```

### 方法二：手动安装运行
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动程序
python art_resource_manager.py
```

## 📋 主要功能

### 1. 路径配置
- **SVN仓库路径**：美术资源的源路径（如：`E:/newprefab04`）
- **Git仓库路径**：目标Git仓库路径（如：`E:/git8a/assetruntimenew/CommonResource`）
- **编辑器路径**：Unity编辑器路径（如：`E:/RPGame5.6.9a`）

### 2. 文件选择
- **选择文件**：单个文件选择
- **选择文件夹**：批量选择文件夹内的所有Unity资源
- **支持格式**：`.prefab`、`.mat`、`.anim`、`.controller`、`.asset`、`.unity`

### 3. 核心检查功能
- **依赖缺失检查**：
  - 分析上传文件的依赖关系
  - 检查依赖是否在上传列表中
  - 检查Git仓库是否已包含缺失的依赖
  - 报告真正缺失的依赖文件

- **GUID冲突检查**：
  - 读取所有`.meta`文件的GUID
  - 对比上传文件与Git仓库中的GUID
  - 识别并报告GUID冲突

### 4. 分支管理
- **查询分支**：显示所有可用的Git分支
- **切换分支**：切换到指定分支
- **显示当前分支**：查看当前所在分支

### 5. 辅助功能
- **GUID查询**：根据GUID在SVN仓库中查找对应资源
- **显示Git仓库URL**：查看Git仓库的远程地址
- **操作日志**：详细记录所有操作过程
- **检查结果**：显示详细的检查结果和错误信息

## 🔍 使用流程

### 标准工作流程
1. **启动工具**
   ```bash
   python art_resource_manager.py
   ```

2. **配置路径**
   - 设置SVN仓库路径
   - 设置Git仓库路径
   - 设置Unity编辑器路径

3. **选择资源**
   - 点击"选择文件"或"选择文件夹"
   - 选择要上传的美术资源文件
   - 在文件列表中确认选择的文件

4. **执行检查**
   - 点击"检查并推送"按钮
   - 等待依赖检查和GUID冲突检查完成
   - 查看检查结果

5. **处理结果**
   - ✅ **检查通过**：可以安全上传资源
   - ❌ **检查失败**：根据错误信息修复问题后重新检查

## ⚠️ 常见问题

### 依赖缺失问题
**问题**：提示"发现依赖缺失"
**解决方案**：
1. 检查上传列表是否包含所有依赖文件
2. 确认Git仓库目标分支是否已有相关依赖
3. 手动添加缺失的依赖文件到上传列表

### GUID冲突问题
**问题**：提示"发现GUID冲突"
**解决方案**：
1. 检查冲突的具体文件
2. 重新生成有冲突文件的GUID（通过Unity编辑器）
3. 或者删除Git仓库中的冲突文件（如果确认可以替换）

### Git分支问题
**问题**：无法获取Git分支或切换失败
**解决方案**：
1. 确认Git仓库路径正确
2. 检查Git命令行工具是否安装
3. 确认有足够的权限访问Git仓库

## 🛠️ 技术细节

### 依赖分析原理
- 解析Unity资源文件（YAML格式）
- 提取`guid:`字段引用
- 提取`path:`字段引用
- 建立完整的依赖关系图

### GUID检查原理
- 读取所有`.meta`文件
- 提取`guid:`字段值
- 构建GUID到文件的映射表
- 检测重复的GUID

### 支持的资源类型
| 扩展名 | 类型 | 主要依赖字段 |
|--------|------|-------------|
| .prefab | 预制体 | m_Component, m_Material, m_Mesh |
| .mat | 材质 | m_Texture, m_Shader |
| .controller | 动画控制器 | m_AnimationClips, m_StateMachine |
| .anim | 动画 | m_AnimationClips |
| .asset | 资源文件 | m_Script, m_MonoScript |
| .unity | 场景文件 | m_RootGameObject, m_Component |

## 📝 配置文件

工具会自动创建`config.json`配置文件保存用户设置：
```json
{
  "svn_path": "E:/newprefab04",
  "git_path": "E:/git8a/assetruntimenew/CommonResource",
  "editor_path": "E:/RPGame5.6.9a",
  "target_directory": "CommonResource",
  "window_geometry": {
    "x": 100,
    "y": 100,
    "width": 1200,
    "height": 800
  },
  "last_selected_branch": "main",
  "recent_files": []
}
```

## 🔧 开发和扩展

### 代码结构
```
art_resource_manager.py     # 主程序文件
├── ResourceDependencyAnalyzer  # 依赖分析器
├── GitSvnManager              # Git/SVN管理器
├── ResourceChecker            # 资源检查线程
└── ArtResourceManager         # 主界面类

config.py                   # 配置管理模块
test_functionality.py       # 功能测试脚本
test_files/                 # 测试文件目录
├── TestPrefab.prefab       # 示例预制体
├── TestPrefab.prefab.meta  # 对应meta文件
├── TestMaterial.mat        # 示例材质
└── TestMaterial.mat.meta   # 对应meta文件
```

### 扩展建议
1. **支持更多资源类型**：添加新的文件扩展名和依赖模式
2. **自动修复功能**：自动下载缺失的依赖文件
3. **批量操作**：支持多个项目的批量处理
4. **集成CI/CD**：与持续集成系统集成
5. **Web界面**：提供Web版本的管理界面

## 📞 技术支持

如果遇到问题：
1. 查看"操作日志"标签页的详细信息
2. 检查"检查结果"标签页的错误报告
3. 确认所有路径配置正确
4. 验证Git和SVN工具是否正常工作

---

**注意**：此工具专为Unity项目设计，需要正确的Unity资源文件格式才能正常工作。 