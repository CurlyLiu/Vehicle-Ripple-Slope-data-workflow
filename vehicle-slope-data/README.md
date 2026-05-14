# Vehicle Slope Data / 车辆斜率数据处理器

<div align="center">

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

**Configuration-Driven Vehicle Slope Data Processing Tool / 配置驱动的车辆斜率数据处理工具**

[English](#english) | [中文](#中文)

</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

Vehicle Slope Data is a specialized tool for processing vehicle voltage slope test data. It handles slope statistics and optional images, generating structured JSON, formatted Excel reports, and SQLite databases.

**Note**: This skill reuses configuration from Vehicle-Ripple-Data via `SlopeConfigManager`.

### Features

- ✅ **Configuration-Driven** - Shares config with Ripple skill
- ✅ **4-Level Fuzzy Matching** - Same matching engine as Ripple
- ✅ **Multi-Format Output** - JSON, Excel, SQLite, Markdown
- ✅ **Optional Image Support** - Can include slope visualization images
- ✅ **Absolute Image Paths** - Reliable image referencing
- ✅ **Unified CLI** - Works with `vehicle_skills_cli.py`

### Quick Start

#### Prerequisites

Vehicle-Slope-Data requires Vehicle-Ripple-Data for shared configurations.

```bash
# Both skills should be in the same parent directory
vehicle-skills/
├── vehicle-ripple-data/     # Required for config
└── vehicle-slope-data/      # This skill
```

#### Installation

```bash
cd vehicle-slope-data
pip install -r requirements.txt
```

#### Basic Usage

```bash
# Via unified CLI (recommended)
python ../vehicle-ripple-data/scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# Or directly
python scripts/cli/process_slope.py E:/Vehicle_Date/V0001_SLOPE
```

#### Python API

```python
from scripts.slope_processor import SlopeDataProcessor

# Create processor
processor = SlopeDataProcessor("E:/Vehicle_Date/V0001_SLOPE")

# Process data
result = processor.process()

# Access results
for comp_code, comp_data in result['components'].items():
    print(f"Component: {comp_data['component_name']}")
    for cond_id, cond_data in comp_data['conditions'].items():
        slope = cond_data['slope']
        print(f"  {cond_id}: max={slope['max_value']} V/s")
        if cond_data.get('image_path'):
            print(f"    Image: {cond_data['image_path']}")
```

### Project Structure

```
vehicle-slope-data/
├── SKILL.md                          # Detailed documentation
├── CHANGELOG.md                      # Version history
├── CONTRIBUTING.md                   # Contribution guide
├── README.md                         # This file
├── config/                           # Configuration
│   ├── __init__.py                   # SlopeConfigManager ⭐
│   └── slope/
│       └── excel_template.yaml       # Slope-specific template
├── scripts/                          # Source code
│   ├── cli/
│   │   ├── __init__.py
│   │   └── process_slope.py          # Legacy CLI
│   ├── slope_processor.py            # Main processor ⭐
│   ├── condition_matcher.py          # Fuzzy matcher (imported from Ripple at runtime)
│   ├── generate_excel_report.py
│   ├── generate_error_report_cn.py
│   └── validate_slope.py
├── references/                       # Reference data
│   ├── test_naming_rules.md          # Slope test conditions
│   └── sensor_naming_rules.md        # 19 channel codes
└── docs/                             # Documentation
    ├── api.md                        # API documentation
    └── examples.md                   # Usage examples

⭐ = Core files
```

### Configuration Sharing

Slope-Data reuses Ripple-Data's configuration:

```python
from config import SlopeConfigManager

config_manager = SlopeConfigManager()

# Load from Ripple-Data
vehicle_fields = config_manager.load('common/vehicle_fields')
matching_rules = config_manager.load('common/matching_rules')
styles = config_manager.load('common/styles')

# Load Slope-specific
template = config_manager.load('slope/excel_template')
```

### Data Format

#### Input Structure

```
V0001_SLOPE/
├── FM_V/                                # Component folder
│   ├── 18_交流充电暖风_FM_V.png        # Slope image (optional)
│   ├── 坡度10_82_匀速80暖风_FM_V.png   # Slope with grade prefix
│   └── statistics.xlsx                  # 4-column statistics
├── RM_V/                                # Another component
│   └── ...
└── vehicle_info.md                      # Vehicle information
```

#### Statistics Excel Format (4 columns)

| Column | Description |
|--------|-------------|
| 文件名 | Condition ID |
| 斜率最大值(V/s) | Maximum slope value |
| 斜率最小值(V/s) | Minimum slope value |
| 斜率绝对值最大值(V/s) | Maximum absolute slope |

#### Image Naming

```
Standard: {condition_id}_{component_code}.png
Example: 18_交流充电暖风_FM_V.png

With Grade: 坡度10_{condition_id}_{component_code}.png
Example: 坡度10_82_匀速80暖风_FM_V.png
```

### Version History

See [CHANGELOG.md](./CHANGELOG.md) for details.

### Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

### License

MIT License.

---

<a name="中文"></a>
## 🇨🇳 中文

### 概述

车辆斜率数据处理器是专为车辆电压斜率测试设计的工具。它处理斜率统计数据和可选图片，生成结构化的JSON、格式化的Excel报告和SQLite数据库。

**注意**：此技能通过`SlopeConfigManager`复用Vehicle-Ripple-Data的配置。

### 功能特性

- ✅ **配置驱动** - 与纹波技能共享配置
- ✅ **四级模糊匹配** - 与纹波相同的匹配引擎
- ✅ **多格式输出** - JSON、Excel、SQLite、Markdown
- ✅ **可选图片支持** - 可包含斜率可视化图片
- ✅ **绝对图片路径** - 可靠的图片引用
- ✅ **统一CLI** - 与`vehicle_skills_cli.py`配合使用

### 快速开始

#### 前置要求

Vehicle-Slope-Data需要Vehicle-Ripple-Data提供共享配置。

```bash
# 两个技能应在同一父目录下
vehicle-skills/
├── vehicle-ripple-data/     # 必需，用于配置
└── vehicle-slope-data/      # 本技能
```

#### 安装

```bash
cd vehicle-slope-data
pip install -r requirements.txt
```

#### 基本使用

```bash
# 通过统一CLI（推荐）
python ../vehicle-ripple-data/scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# 或直接运行
python scripts/cli/process_slope.py E:/Vehicle_Date/V0001_SLOPE
```

#### Python API

```python
from scripts.slope_processor import SlopeDataProcessor

# 创建处理器
processor = SlopeDataProcessor("E:/Vehicle_Date/V0001_SLOPE")

# 处理数据
result = processor.process()

# 访问结果
for comp_code, comp_data in result['components'].items():
    print(f"组件: {comp_data['component_name']}")
    for cond_id, cond_data in comp_data['conditions'].items():
        slope = cond_data['slope']
        print(f"  {cond_id}: 最大值={slope['max_value']} V/s")
        if cond_data.get('image_path'):
            print(f"    图片: {cond_data['image_path']}")
```

### 项目结构

```
vehicle-slope-data/
├── SKILL.md                          # 详细文档
├── CHANGELOG.md                      # 版本历史
├── CONTRIBUTING.md                   # 贡献指南
├── README.md                         # 本文件
├── config/                           # 配置
│   ├── __init__.py                   # SlopeConfigManager ⭐
│   └── slope/
│       └── excel_template.yaml       # 斜率专用模板
├── scripts/                          # 源代码
│   ├── cli/
│   │   ├── __init__.py
│   │   └── process_slope.py          # 旧版CLI
│   ├── slope_processor.py            # 主处理器 ⭐
│   ├── condition_matcher.py          # 模糊匹配器（从Ripple复制）
│   ├── generate_excel_report.py
│   ├── generate_error_report_cn.py
│   └── validate_slope.py
├── references/                       # 参考数据
│   ├── test_naming_rules.md          # 斜率测试工况
│   └── sensor_naming_rules.md        # 17个通道代码
└── docs/                             # 文档
    ├── api.md                        # API文档
    └── examples.md                   # 使用示例

⭐ = 核心文件
```

### 配置共享

斜率数据复用纹波数据的配置：

```python
from config import SlopeConfigManager

config_manager = SlopeConfigManager()

# 从Ripple-Data加载
vehicle_fields = config_manager.load('common/vehicle_fields')
matching_rules = config_manager.load('common/matching_rules')
styles = config_manager.load('common/styles')

# 加载斜率专用配置
template = config_manager.load('slope/excel_template')
```

### 数据格式

#### 输入结构

```
V0001_SLOPE/
├── FM_V/                                # 组件文件夹
│   ├── 18_交流充电暖风_FM_V.png        # 斜率图片（可选）
│   ├── 坡度10_82_匀速80暖风_FM_V.png   # 带坡度前缀
│   └── statistics.xlsx                  # 4列统计数据
├── RM_V/                                # 另一组件
│   └── ...
└── vehicle_info.md                      # 车辆信息
```

#### 统计Excel格式（4列）

| 列名 | 说明 |
|--------|-------------|
| 文件名 | 工况ID |
| 斜率最大值(V/s) | 最大斜率值 |
| 斜率最小值(V/s) | 最小斜率值 |
| 斜率绝对值最大值(V/s) | 最大绝对斜率 |

#### 图片命名

```
标准格式: {condition_id}_{component_code}.png
示例: 18_交流充电暖风_FM_V.png

坡度格式: 坡度10_{condition_id}_{component_code}.png
示例: 坡度10_82_匀速80暖风_FM_V.png
```

### 版本历史

详见 [CHANGELOG.md](./CHANGELOG.md)。

### 贡献指南

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

### 许可证

MIT许可证。

---

## 📞 联系方式 / Contact

- **Issues**: [GitHub Issues](../../issues)
- **Documentation**: [Full Documentation](./docs/)

---

<div align="center">

**Made with ❤️ for vehicle data processing**

</div>
