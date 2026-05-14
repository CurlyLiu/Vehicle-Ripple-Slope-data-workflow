# Contributing to Vehicle-Slope-Data / 为 Vehicle-Slope-Data 做贡献

Thank you for your interest in contributing to vehicle-slope-data!  
感谢您对为 vehicle-slope-data 做贡献的兴趣！

## Getting Started / 快速开始

### Prerequisites / 前置条件

Before you begin, ensure you have:
开始前，请确保您有：

- Python 3.8+ installed / 已安装 Python 3.8+
- Git installed / 已安装 Git
- `vehicle-ripple-data` skill installed (required dependency) / 已安装 `vehicle-ripple-data` 技能（必需依赖）
- Basic understanding of voltage slope (du/dt) analysis / 了解电压斜率（du/dt）分析的基础知识

### Development Setup / 开发环境设置

1. **Clone the repository** / 克隆仓库
   ```bash
   cd C:\Users\31915\.claude\skills
   git clone <repository-url> vehicle-slope-data
   cd vehicle-slope-data
   ```

2. **Install dependencies** / 安装依赖
   ```bash
   pip install pyyaml pandas openpyxl pillow numpy tqdm colorama
   ```

3. **Verify Ripple skill is available** / 验证纹波技能可用
   ```bash
   python -c "from vehicle_ripple_data.config import ConfigManager; print('OK')"
   ```

4. **Test the skill** / 测试技能
   ```bash
   python scripts/cli/process_slope.py --help
   ```

## How to Contribute / 如何贡献

### Reporting Bugs / 报告 Bug

Before creating a bug report, please:
创建 Bug 报告前，请：

1. Check if the bug already exists in [Issues] / 检查 [Issues] 中是否已存在该 Bug
2. Collect relevant information / 收集相关信息
   - Python version / Python 版本
   - Operating system / 操作系统
   - Error messages / 错误信息
   - Sample data (if possible) / 示例数据（如可能）
3. Create a detailed report / 创建详细报告

**Bug Report Template:**
```markdown
**Description:**
Brief description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. ...

**Expected Behavior:**
What you expected to happen

**Actual Behavior:**
What actually happened

**Environment:**
- OS: [e.g., Windows 10]
- Python: [e.g., 3.9.0]
- Version: [e.g., 1.2.0]

**Additional Context:**
Add any other context about the problem
```

### Suggesting Features / 建议功能

We welcome feature suggestions! Please include:
我们欢迎功能建议！请包含：

- Clear use case / 清晰的使用场景
- Expected behavior / 预期行为
- Why it would be useful / 为什么有用

### Pull Requests / Pull Request 流程

1. **Fork the repository** / Fork 仓库
2. **Create a branch** / 创建分支
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

3. **Make your changes** / 进行修改
4. **Test your changes** / 测试您的修改
   ```bash
   # Run basic tests / 运行基础测试
   python scripts/tests/quick_test.py
   
   # Test with real data / 用真实数据测试
   python scripts/cli/process_slope.py --vehicle-id V0001 --input-dir "E:/Vehicle_Date/V0001/V0001_SLOPE"
   ```

5. **Commit your changes** / 提交您的修改
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push to your fork** / 推送到您的 fork
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** / 创建 Pull Request

## Commit Message Convention / 提交信息规范

We follow [Conventional Commits](https://www.conventionalcommits.org/):
我们遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` - New feature / 新功能
- `fix:` - Bug fix / Bug 修复
- `docs:` - Documentation only / 仅文档
- `style:` - Code style (formatting) / 代码样式（格式化）
- `refactor:` - Code refactoring / 代码重构
- `perf:` - Performance improvement / 性能优化
- `test:` - Adding tests / 添加测试
- `chore:` - Maintenance / 维护工作

**Examples / 示例：**
```bash
git commit -m "feat: add support for FAN component slope analysis"
git commit -m "fix: correct slope calculation for negative values"
git commit -m "docs: update API documentation with examples"
git commit -m "refactor: optimize condition matching algorithm"
```

## Code Style / 代码风格

### Python Code / Python 代码

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use meaningful variable names / 使用有意义的变量名
- Add docstrings for functions and classes / 为函数和类添加文档字符串
- Maximum line length: 100 characters / 最大行长度：100 字符

**Example / 示例：**
```python
def process_slope_data(vehicle_id: str, input_dir: str) -> dict:
    """
    Process voltage slope data for a vehicle.
    
    Args:
        vehicle_id: Vehicle identifier (e.g., 'V0001')
        input_dir: Input directory containing slope test data
        
    Returns:
        dict: Processing results with statistics
    """
    # Implementation here
    pass
```

### Documentation / 文档

- Use bilingual format (English + Chinese) / 使用双语格式（英文+中文）
- Keep examples practical and runnable / 保持示例实用且可运行
- Update CHANGELOG.md for notable changes / 为重要更改更新 CHANGELOG.md

## Project Structure / 项目结构

```
vehicle-slope-data/
├── config/                    # Configuration files / 配置文件
│   ├── __init__.py           # SlopeConfigManager / 斜率配置管理器
│   └── slope/                # Slope-specific config / 斜率专用配置
├── scripts/                   # Core scripts / 核心脚本
│   ├── slope_processor.py    # Main processor / 主处理器
│   ├── cli/                  # CLI tools / 命令行工具
│   └── tests/                # Test scripts / 测试脚本
├── docs/                      # Documentation / 文档
└── references/               # Reference materials / 参考材料
```

## Key Differences from Ripple / 与纹波技能的关键区别

When contributing, remember:
做贡献时，请记住：

1. **Reuse Ripple Config** / 复用纹波配置
   - Vehicle fields come from `vehicle-ripple-data/config/common/`
   - 车辆字段来自纹波技能的通用配置
   - Don't duplicate field definitions / 不要重复定义字段

2. **Slope-Specific Logic** / 斜率专用逻辑
   - Statistics are different (slope vs ripple values)
   - 统计指标不同（斜率值 vs 纹波值）
   - Excel template is separate / Excel 模板是独立的

3. **Maintain Compatibility** / 保持兼容性
   - Don't break existing Ripple skill usage
   - 不要破坏现有的纹波技能使用
   - Test with both skills together / 同时测试两个技能

## Testing / 测试

### Unit Tests / 单元测试

```bash
# Run all tests / 运行所有测试
python -m pytest scripts/tests/

# Run specific test / 运行特定测试
python scripts/tests/quick_test.py
```

### Integration Tests / 集成测试

Test with real vehicle data:
使用真实车辆数据测试：

```bash
# Process a single vehicle / 处理单个车辆
python scripts/cli/process_slope.py \
  --vehicle-id V0001 \
  --input-dir "E:/Vehicle_Date/V0001/V0001_SLOPE" \
  --output-dir "E:/Vehicle_Date/V0001/V0001_SLOPE_output"

# Verify output / 验证输出
ls "E:/Vehicle_Date/V0001/V0001_SLOPE_output/"
```

## Questions? / 有问题？

- Check existing [Issues] / 查看现有的 [Issues]
- Read [README.md](README.md) / 阅读 [README.md]
- Check [docs/api.md](docs/api.md) for API details / 查看 [docs/api.md] 了解 API 详情

## Code of Conduct / 行为准则

- Be respectful and constructive / 保持尊重和建设性
- Welcome newcomers / 欢迎新人
- Focus on what's best for the project / 专注于对项目最有利的事情

Thank you for contributing! / 感谢您的贡献！
