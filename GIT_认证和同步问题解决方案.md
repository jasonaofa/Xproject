# 🔧 Git认证和同步问题解决方案

## 📋 问题描述

在使用美术资源上传工具时，可能遇到以下Git相关问题：

### 常见错误类型

1. **推送被拒绝**
   ```
   ! [rejected] sandboxgame/ugc-0925 -> sandboxgame/ugc-0925 (fetch first)
   error: failed to push some refs to 'http://client_gitlab.miniworldplus.com:83/miniwan/CommonResource.git'
   hint: Updates were rejected because the remote contains work that you do not have locally.
   ```

2. **认证失败**
   - 每次pull都需要输入用户名密码
   - Authentication failed错误
   - could not read Username错误

3. **网络连接问题**
   - Connection timeout
   - Network unreachable

## 🎯 解决方案

### 方案一：使用工具内置功能（推荐）

#### 1. 自动修复功能
在美术资源上传工具中：
1. 点击 **"修复同步问题"** 按钮
2. 确认修复操作
3. 按提示输入Git用户名密码（仅需一次）
4. 等待修复完成

#### 2. 手动同步
在工具中：
1. 点击 **"拉取分支"** 按钮
2. 解决可能的冲突
3. 重新尝试推送文件

### 方案二：命令行手动修复

#### 1. 配置Git凭据存储
```bash
# 进入Git仓库目录
cd "你的Git仓库路径"

# 配置凭据存储（永久保存密码）
git config credential.helper store

# 或者配置临时缓存（24小时）
git config credential.helper "cache --timeout=86400"
```

#### 2. 同步远程更改
```bash
# 获取远程信息
git fetch origin

# 拉取当前分支（会提示输入用户名密码）
git pull origin <分支名>

# 输入用户名和密码后，凭据将被保存
```

#### 3. 解决推送冲突
```bash
# 如果有冲突，先拉取合并
git pull origin <分支名>

# 解决冲突后重新推送
git push origin <分支名>
```

## 🔍 问题诊断

### 检查Git状态
```bash
# 检查当前分支
git branch --show-current

# 检查工作区状态
git status

# 检查远程仓库连接
git ls-remote --heads origin

# 检查凭据配置
git config --get credential.helper
```

### 常见状态说明

| 状态 | 说明 | 解决方案 |
|------|------|----------|
| `ahead 2` | 本地领先远程2个提交 | 可以直接推送 |
| `behind 3` | 本地落后远程3个提交 | 需要先pull |
| `ahead 1, behind 2` | 有分歧 | 需要pull并解决冲突 |
| `nothing to commit` | 工作区干净 | 正常状态 |

## 🛠️ 自动修复功能详解

### 修复流程
1. **检查Git凭据配置**
   - 如果未配置，自动设置 `credential.helper store`
   - 确保下次输入密码后会被保存

2. **测试远程连接**
   - 执行 `git ls-remote --heads origin`
   - 验证网络和认证状态

3. **自动同步**
   - 执行 `git fetch origin`
   - 执行 `git pull origin <当前分支>`
   - 处理可能的认证提示

4. **提供解决方案**
   - 根据错误类型提供具体指导
   - 显示需要手动操作的步骤

### 错误处理

#### 认证失败
- **自动操作**：配置凭据存储
- **用户操作**：按提示输入用户名密码
- **结果**：密码被永久保存，下次无需输入

#### 同步冲突
- **自动操作**：尝试拉取远程更改
- **用户操作**：解决可能的文件冲突
- **结果**：本地和远程保持同步

#### 网络问题
- **检查项**：网络连接、VPN状态、服务器可达性
- **建议**：稍后重试或联系IT支持

## 💡 最佳实践

### 日常使用建议
1. **推送前先拉取**：养成推送前点击"拉取分支"的习惯
2. **及时同步**：定期同步远程更改，避免大量冲突
3. **合理分支**：使用合适的分支进行开发，避免在main分支直接操作

### 凭据管理
1. **使用store模式**：适合个人开发环境
2. **定期更新密码**：如果Git密码变更，需要重新输入一次
3. **安全考虑**：在共享电脑上谨慎使用永久存储

### 冲突处理
1. **小步提交**：频繁提交小的更改，减少冲突可能
2. **沟通协调**：团队协作时及时沟通，避免同时修改同一文件
3. **备份重要更改**：处理冲突前备份重要的本地更改

## 🚨 故障排除

### 如果修复功能无法解决问题

1. **手动重置仓库**
   ```bash
   git reset --hard origin/<分支名>
   git clean -fd
   ```

2. **重新克隆仓库**
   - 备份本地更改
   - 删除本地仓库
   - 重新克隆远程仓库

3. **联系技术支持**
   - 提供错误截图
   - 说明操作步骤
   - 提供Git仓库路径

### 常见问题FAQ

**Q: 为什么每次都要输入密码？**
A: Git凭据存储未配置。使用"修复同步问题"功能或手动配置 `git config credential.helper store`。

**Q: 推送时提示"rejected"怎么办？**
A: 远程仓库有新的提交。先点击"拉取分支"同步远程更改，然后重新推送。

**Q: 修复功能提示认证失败怎么办？**
A: 按照提示在命令行中手动执行git pull，输入正确的用户名密码。

**Q: 网络超时怎么办？**
A: 检查网络连接，确认VPN状态，稍后重试。如果持续失败，联系IT支持。

---

**版本**: v1.0  
**更新时间**: 2024年1月  
**适用工具**: 美术资源上传工具 v1.0.9+

