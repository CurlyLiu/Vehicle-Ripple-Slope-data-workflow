# Contributing Guide / 贡献指南

Thank you for your interest in contributing to Vehicle Ripple Data!  
感谢您对车辆纹波数据项目的贡献兴趣！

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a branch** for your changes
4. **Make your changes** and test them
5. **Submit a pull request**

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/vehicle-ripple-data.git
cd vehicle-ripple-data

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Code Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (not 80)
- **Docstrings**: Google style
- **Type hints**: Required for all public functions
- **Comments**: In both English and Chinese for clarity

Example:
```python
def process_vehicle(folder: Path, config: Optional[Dict] = None) -> Dict[str, Any]:
    """Process vehicle data / 处理车辆数据
    
    Args / 参数:
        folder: Path to vehicle folder / 车辆文件夹路径
        config: Optional configuration / 可选配置
    
    Returns / 返回:
        Processing results / 处理结果
    """
    pass
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html

# Run specific test
pytest tests/test_vehicle_processor.py::test_process_vehicle
```

### Submitting Changes

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/)
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `refactor:` Code refactoring
   - `test:` Tests
   - `perf:` Performance improvement
3. **Write tests** for new functionality
4. **Update documentation** if needed
5. **Submit PR** with clear description

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Example:
```
feat(cli): add progress bar display

Add visual progress bar with percentage and current item.
支持显示百分比和当前项目的可视化进度条。

Closes #123
```

### Reporting Bugs

Use GitHub Issues with template:

**Bug Report Template**:
```markdown
**Description**: Clear bug description
**Steps to Reproduce**:
1. Step one
2. Step two
**Expected Behavior**: What should happen
**Actual Behavior**: What actually happens
**Environment**: Python version, OS, etc.
**Logs**: Error messages or stack traces
```

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints

---

<a name="中文"></a>
## 🇨🇳 中文

### 开始贡献

1. **Fork仓库** 到您的GitHub账户
2. **克隆您的fork** 到本地
3. **创建分支** 用于您的更改
4. **进行更改** 并测试
5. **提交Pull Request**

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/vehicle-ripple-data.git
cd vehicle-ripple-data

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 代码风格

我们遵循PEP 8，但有一些修改：

- **行长度**: 100字符（不是80）
- **文档字符串**: Google风格
- **类型提示**: 所有公共函数都需要
- **注释**: 中英双语，便于理解

示例：
```python
def process_vehicle(folder: Path, config: Optional[Dict] = None) -> Dict[str, Any]:
    """Process vehicle data / 处理车辆数据
    
    Args / 参数:
        folder: Path to vehicle folder / 车辆文件夹路径
        config: Optional configuration / 可选配置
    
    Returns / 返回:
        Processing results / 处理结果
    """
    pass
```

### 测试

```bash
# 运行所有测试
pytest tests/

# 带覆盖率运行
pytest tests/ --cov=scripts --cov-report=html

# 运行特定测试
pytest tests/test_vehicle_processor.py::test_process_vehicle
```

### 提交更改

1. **创建分支**: `git checkout -b feature/your-feature-name`
2. **提交更改**: 遵循 [Conventional Commits](https://www.conventionalcommits.org/)
   - `feat:` 新功能
   - `fix:` 错误修复
   - `docs:` 文档
   - `refactor:` 代码重构
   - `test:` 测试
   - `perf:` 性能优化
3. **编写测试** 覆盖新功能
4. **更新文档** 如有需要
5. **提交PR** 并附上清晰描述

### 提交信息格式

```
<类型>(<范围>): <主题>

<正文>

<页脚>
```

示例：
```
feat(cli): add progress bar display

Add visual progress bar with percentage and current item.
支持显示百分比和当前项目的可视化进度条。

Closes #123
```

### 报告Bug

使用GitHub Issues并遵循模板：

**Bug报告模板**：
```markdown
**描述**: 清晰的bug描述
**复现步骤**:
1. 步骤一
2. 步骤二
**预期行为**: 应该发生什么
**实际行为**: 实际发生了什么
**环境**: Python版本、操作系统等
**日志**: 错误信息或堆栈跟踪
```

### 行为准则

- 尊重和包容
- 欢迎新手
- 专注于建设性反馈
- 尊重不同观点

---

## 📋 Checklist / 检查清单

Before submitting PR / 提交PR前：

- [ ] Code follows style guide / 代码遵循风格指南
- [ ] Tests added/updated / 测试已添加/更新
- [ ] Documentation updated / 文档已更新
- [ ] CHANGELOG.md updated / CHANGELOG.md已更新
- [ ] Commit messages follow convention / 提交信息遵循规范
- [ ] No merge conflicts / 无合并冲突

---

## 🆘 Getting Help / 获取帮助

- **GitHub Discussions**: [](../../discussions)
- **Issues**: [](../../issues)
- **Email**: your.email@example.com

---

<div align="center">

**Thank you for contributing! / 感谢您的贡献！** 🎉

</div>
