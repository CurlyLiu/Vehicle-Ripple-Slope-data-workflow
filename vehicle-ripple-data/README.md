# Vehicle Ripple Data / 车辆纹波数据处理器

<div align="center">

[![Version](https://img.shields.io/badge/version-4.3.0-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

**Configuration-Driven Vehicle Ripple Data Processing Tool / 配置驱动的车辆纹波数据处理工具**

[English](#english) | [中文](#中文)

</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

Vehicle Ripple Data is a powerful data processing tool designed for automotive high-voltage system ripple testing. It automates the processing of waveform images and statistical data, generating structured JSON, formatted Excel reports, and SQLite databases.

### Features

- ✅ **Configuration-Driven Architecture** - All rules and styles managed via YAML
- ✅ **4-Level Fuzzy Matching** - Precise → Normalized → Fuzzy → Feature matching
- ✅ **Multi-Format Output** - JSON, Excel (V3.0), SQLite, Markdown reports
- ✅ **Absolute Image Paths** - Reliable image referencing
- ✅ **Hot-Reload Configs** - No restart needed after config changes
- ✅ **Unified CLI** - Single command for ripple and slope data
- ✅ **Batch Processing** - Process multiple vehicles at once
- ✅ **Progress Display** - Visual progress bars with real-time status

### Quick Start

#### Installation

```bash
# Clone repository
cd vehicle-ripple-data

# Install dependencies
pip install -r requirements.txt
```

#### Basic Usage

```bash
# Process single vehicle
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# With progress bar
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

# Batch processing
python scripts/cli/vehicle_skills_cli.py batch E:/Vehicle_Date/V0001 E:/Vehicle_Date/V0002

# Validate data
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001

# Show version
python scripts/cli/vehicle_skills_cli.py version
```

#### Python API

```python
from scripts.core.vehicle_processor import VehicleDataProcessor

# Create processor
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")

# Process data
result = processor.process()

# Access results
vehicle_id = result['vehicle']['vehicle_id']
components = result['components']

# Access specific component
for comp_code, comp_data in components.items():
    print(f"Component: {comp_data['component_name']}")
    for cond_id, cond_data in comp_data['conditions'].items():
        print(f"  {cond_id}: {cond_data['image_path']}")
```

### Project Structure

```
vehicle-ripple-data/
├── SKILL.md                          # Detailed documentation
├── CHANGELOG.md                      # Version history
├── CONTRIBUTING.md                   # Contribution guide
├── README.md                         # This file
├── config/                           # Configuration
│   ├── __init__.py                   # ConfigManager
│   ├── common/                       # Shared configs
│   │   ├── vehicle_fields.yaml       # Vehicle field definitions
│   │   ├── matching_rules.yaml       # Fuzzy matching rules
│   │   └── styles.yaml               # Excel styles
│   └── ripple/
│       └── excel_template.yaml       # Excel template
├── scripts/                          # Source code
│   ├── core/
│   │   ├── vehicle_processor.py      # Main processor ⭐
│   │   └── condition_matcher.py      # Fuzzy matcher ⭐
│   ├── cli/
│   │   ├── process_vehicle.py        # Legacy CLI
│   │   └── vehicle_skills_cli.py     # Unified CLI ⭐
│   ├── generate_excel_report.py
│   ├── generate_error_report_cn.py
│   └── incremental_processor.py
├── references/                       # Reference data
│   ├── test_naming_rules.md          # 54 test conditions
│   └── sensor_naming_rules.md        # 24 channel codes
└── docs/                             # Documentation
    ├── api.md                        # API documentation
    └── examples.md                   # Usage examples

⭐ = Core files
```

### Configuration

#### Vehicle Fields (`config/common/vehicle_fields.yaml`)

Define how to extract vehicle information from input files:

```yaml
field_mappings:
  vehicle_model:
    keywords: ["车型", "车辆型号", "Model"]
    required: true
  vehicle_length_mm:
    keywords: ["车长", "长度", "Length"]
    unit_conversion:
      factor: 1.0
      decimal_places: 0
```

#### Matching Rules (`config/common/matching_rules.yaml`)

Configure fuzzy matching for condition names:

```yaml
matching:
  levels:
    - exact        # Exact match
    - normalized   # Remove brackets
    - fuzzy        # Levenshtein distance
    - feature      # SOC + keyword matching
```

### Data Format

#### Input Structure

```
V0001_RIPPLE/
├── ACCM_A/                          # Component folder
│   ├── 87_超车80-140_ACCM_A.png    # Waveform image
│   ├── 88_急加速0-80_ACCM_A.png
│   └── statistics.xlsx              # Statistics (7 columns)
├── DCC_V/                           # Another component
│   └── ...
└── vehicle_info.md                  # Vehicle information
```

#### Image Naming Format

```
{condition_id}_{description}_{channel}_{vpp}Ipp_{freq}kHz_{amp}A.png

Example: 87_超车80-140_ACCM_A_49.78Ipp_6.84kHz_4.195A.png
```

#### Output Files

```
V0001_RIPPLE_output/
├── V0001_RIPPLE_data.json           # Structured data
├── V0001_RIPPLE_summary.xlsx        # Excel report (3 sheets)
├── V0001_RIPPLE.db                  # SQLite database
└── error_report.md                  # Processing report
```

### Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

### Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.

### License

MIT License - See [LICENSE](./LICENSE) for details.

---

<a name="中文"></a>
## 🇨🇳 中文

### 概述

车辆纹波数据处理器是一个专为汽车高压系统纹波测试设计的强大数据处理工具。它自动化处理波形图片和统计数据，生成结构化的JSON、格式化的Excel报告和SQLite数据库。

### 功能特性

- ✅ **配置驱动架构** - 所有规则和样式通过YAML管理
- ✅ **四级模糊匹配** - 精确→规范化→模糊→特征匹配
- ✅ **多格式输出** - JSON、Excel（V3.0）、SQLite、Markdown报告
- ✅ **绝对图片路径** - 可靠的图片引用
- ✅ **热重载配置** - 修改配置后无需重启
- ✅ **统一CLI** - 单一命令处理纹波和斜率数据
- ✅ **批量处理** - 一次处理多个车辆
- ✅ **进度显示** - 可视化进度条和实时状态

### 快速开始

#### 安装

```bash
# 克隆仓库
cd vehicle-ripple-data

# 安装依赖
pip install -r requirements.txt
```

#### 基本使用

```bash
# 处理单个车辆
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# 带进度条
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

# 批量处理
python scripts/cli/vehicle_skills_cli.py batch E:/Vehicle_Date/V0001 E:/Vehicle_Date/V0002

# 验证数据
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001

# 显示版本
python scripts/cli/vehicle_skills_cli.py version
```

#### Python API

```python
from scripts.core.vehicle_processor import VehicleDataProcessor

# 创建处理器
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")

# 处理数据
result = processor.process()

# 访问结果
vehicle_id = result['vehicle']['vehicle_id']
components = result['components']

# 访问特定组件
for comp_code, comp_data in components.items():
    print(f"组件: {comp_data['component_name']}")
    for cond_id, cond_data in comp_data['conditions'].items():
        print(f"  {cond_id}: {cond_data['image_path']}")
```

### 项目结构

```
vehicle-ripple-data/
├── SKILL.md                          # 详细文档
├── CHANGELOG.md                      # 版本历史
├── CONTRIBUTING.md                   # 贡献指南
├── README.md                         # 本文件
├── config/                           # 配置
│   ├── __init__.py                   # ConfigManager
│   ├── common/                       # 共享配置
│   │   ├── vehicle_fields.yaml       # 车辆字段定义
│   │   ├── matching_rules.yaml       # 模糊匹配规则
│   │   └── styles.yaml               # Excel样式
│   └── ripple/
│       └── excel_template.yaml       # Excel模板
├── scripts/                          # 源代码
│   ├── core/
│   │   ├── vehicle_processor.py      # 主处理器 ⭐
│   │   └── condition_matcher.py      # 模糊匹配器 ⭐
│   ├── cli/
│   │   ├── process_vehicle.py        # 旧版CLI
│   │   └── vehicle_skills_cli.py     # 统一CLI ⭐
│   ├── generate_excel_report.py
│   ├── generate_error_report_cn.py
│   └── incremental_processor.py
├── references/                       # 参考数据
│   ├── test_naming_rules.md          # 54个测试工况
│   └── sensor_naming_rules.md        # 24个通道代码
└── docs/                             # 文档
    ├── api.md                        # API文档
    └── examples.md                   # 使用示例

⭐ = 核心文件
```

### 配置说明

#### 车辆字段 (`config/common/vehicle_fields.yaml`)

定义如何从输入文件提取车辆信息：

```yaml
field_mappings:
  vehicle_model:
    keywords: ["车型", "车辆型号", "Model"]
    required: true
  vehicle_length_mm:
    keywords: ["车长", "长度", "Length"]
    unit_conversion:
      factor: 1.0
      decimal_places: 0
```

#### 匹配规则 (`config/common/matching_rules.yaml`)

配置工况名称的模糊匹配：

```yaml
matching:
  levels:
    - exact        # 精确匹配
    - normalized   # 去除括号
    - fuzzy        # 编辑距离
    - feature      # SOC+关键词匹配
```

### 数据格式

#### 输入结构

```
V0001_RIPPLE/
├── ACCM_A/                          # 组件文件夹
│   ├── 87_超车80-140_ACCM_A.png    # 波形图片
│   ├── 88_急加速0-80_ACCM_A.png
│   └── statistics.xlsx              # 统计数据（7列）
├── DCC_V/                           # 另一组件
│   └── ...
└── vehicle_info.md                  # 车辆信息
```

#### 图片命名格式

```
{condition_id}_{description}_{channel}_{vpp}Ipp_{freq}kHz_{amp}A.png

示例: 87_超车80-140_ACCM_A_49.78Ipp_6.84kHz_4.195A.png
```

#### 输出文件

```
V0001_RIPPLE_output/
├── V0001_RIPPLE_data.json           # 结构化数据
├── V0001_RIPPLE_summary.xlsx        # Excel报告（3个工作表）
├── V0001_RIPPLE.db                  # SQLite数据库
└── error_report.md                  # 处理报告
```

### 版本历史

详见 [CHANGELOG.md](./CHANGELOG.md)

### 贡献指南

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

### 许可证

MIT许可证 - 详见 [LICENSE](./LICENSE)

---

## 📞 联系方式 / Contact

- **Issues**: [GitHub Issues](../../issues)
- **Email**: your.email@example.com
- **Documentation**: [Full Documentation](./docs/)

---

<div align="center">

**Made with ❤️ for vehicle data processing**

</div>
