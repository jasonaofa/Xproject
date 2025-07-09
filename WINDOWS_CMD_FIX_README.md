# Windows CMD窗口修复方案

## 问题描述

在使用美术资源上传工具时，程序会不停地弹出CMD窗口，影响用户体验。

## 根本原因

在Windows系统上，当使用`subprocess.run()`或`subprocess.Popen()`执行外部命令时，默认会创建可见的命令行窗口。这导致每次执行Git命令时都会弹出CMD窗口。

## 修复方案

### 1. 添加Windows特定的subprocess标志

在所有相关文件中添加了Windows特定的subprocess标志：

```python
import platform

# 添加Windows特定的subprocess标志
if platform.system() == 'Windows':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0
```

### 2. 更新所有subprocess调用

为所有的`subprocess.run()`和`subprocess.Popen()`调用添加了`creationflags=SUBPROCESS_FLAGS`参数：

#### subprocess.run() 示例：
```python
# 修复前
result = subprocess.run(['git', 'branch', '--show-current'], 
                      cwd=self.git_path, 
                      capture_output=True, 
                      text=True,
                      encoding='utf-8',
                      errors='ignore',
                      timeout=5)

# 修复后
result = subprocess.run(['git', 'branch', '--show-current'], 
                      cwd=self.git_path, 
                      capture_output=True, 
                      text=True,
                      encoding='utf-8',
                      errors='ignore',
                      timeout=5,
                      creationflags=SUBPROCESS_FLAGS)
```

#### subprocess.Popen() 示例：
```python
# 修复前
process = subprocess.Popen(
    ['git', 'clone', '--progress', repo_url, target_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    cwd=self.deploy_dir,
    env=git_env
)

# 修复后
process = subprocess.Popen(
    ['git', 'clone', '--progress', repo_url, target_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    cwd=self.deploy_dir,
    env=git_env,
    creationflags=SUBPROCESS_FLAGS
)
```

## 修复的文件

1. **art_resource_manager.py** - 主程序文件
   - 添加了SUBPROCESS_FLAGS定义
   - 修复了所有Git命令调用
   - 修复了taskkill命令调用
   - 修复了脚本执行调用

2. **test_git_fix.py** - 测试脚本
   - 添加了SUBPROCESS_FLAGS定义
   - 修复了所有测试用的Git命令调用

3. **crlf_auto_fix.py** - CRLF修复模块
   - 添加了SUBPROCESS_FLAGS定义
   - 修复了所有Git配置命令调用

## 修复的命令类型

- `git branch --show-current` - 获取当前分支
- `git rev-parse --abbrev-ref HEAD` - 获取HEAD引用
- `git status --porcelain -b` - 获取状态信息
- `git branch` - 获取分支列表
- `git fetch` - 获取远程信息
- `git checkout` - 切换分支
- `git pull` - 拉取更新
- `git push` - 推送更改
- `git add` - 添加文件
- `git commit` - 提交更改
- `git config` - 配置Git
- `git clone` - 克隆仓库
- `taskkill` - 终止进程
- 其他所有subprocess调用

## 技术细节

### CREATE_NO_WINDOW 标志

`subprocess.CREATE_NO_WINDOW` 是Windows特定的标志，它告诉系统：
- 不要为新进程创建控制台窗口
- 进程在后台运行，不会显示任何窗口
- 适用于GUI应用程序中的后台命令执行

### 跨平台兼容性

修复方案保持了跨平台兼容性：
- 在Windows上使用 `CREATE_NO_WINDOW` 标志
- 在其他平台上使用 `0`（无特殊标志）
- 不影响Linux和macOS的正常运行

## 验证方法

1. **运行主程序**：启动美术资源上传工具，执行Git操作时不应再弹出CMD窗口
2. **运行测试脚本**：执行 `python test_git_fix.py` 验证修复效果
3. **检查日志**：所有Git操作的结果仍然会显示在程序的日志窗口中

## 注意事项

- 修复后，Git命令仍然正常执行，只是不再显示CMD窗口
- 所有错误信息和输出仍然会通过程序的日志系统显示
- 如果需要在调试时看到Git命令的输出，可以临时注释掉 `creationflags=SUBPROCESS_FLAGS` 参数

## 总结

通过添加 `creationflags=SUBPROCESS_FLAGS` 参数，成功解决了Windows系统上CMD窗口不停弹出的问题，提升了用户体验，同时保持了所有功能的正常运行。 