# Changelog / 更新日志

All notable changes to this project will be documented in this file.
所有 notable 的更改都将记录在此文件中。

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [1.2.0] - 2025-04-01

### Added / 新增

- 🎯 **Configuration-Driven Architecture** - Reuses Ripple skill configurations
  - 配置驱动架构 - 复用纹波技能配置
  - `config/common/` - Shared vehicle fields, matching rules, and styles
  - `config/slope/excel_template.yaml` - Slope-specific report template
  - 复用纹波技能的字段定义和匹配规则

- 📊 **Voltage Slope Processing** - Specialized for slope (du/dt) analysis
  - 电压斜率处理 - 专门用于斜率（du/dt）分析
  - Dynamic component detection (same sensor channels as Ripple)
  - 动态组件检测（与纹波相同的传感器通道）
  - Handles voltage slope test data from components
  - 处理部件的电压斜率测试数据

- 🔍 **4-Level Fuzzy Matching** - Smart condition name matching
  - 四级模糊匹配 - 智能工况名称匹配
  1. Exact match / 精确匹配
  2. Normalized match (bracket removal) / 规范化匹配（去括号）
  3. Fuzzy match (Levenshtein distance) / 模糊匹配（编辑距离）
  4. Feature match (handles GBK encoding) / 特征匹配（处理GBK编码）

- 🖼️ **Absolute Image Paths** - Store absolute paths for reliability
  - 绝对图片路径 - 存储绝对路径以确保可靠性
  - JSON, Excel, SQLite all use absolute paths
  - JSON、Excel、SQLite均使用绝对路径

- 📈 **Slope Statistics** - Different metrics from Ripple
  - 斜率统计 - 与纹波不同的指标
  - Max slope / 最大斜率
  - Average slope / 平均斜率
  - Threshold crossings / 阈值穿越次数
  - 不同于纹波的纹波值统计

### Dependencies / 依赖

- 🔗 **Ripple Skill Required** - Uses `SlopeConfigManager`
  - 需要纹波技能 - 使用 `SlopeConfigManager`
  - Reuses vehicle fields from `vehicle-ripple-data/config/common/`
  - 复用纹波技能的字段定义

## [1.1.0] - 2025-03-15

### Added / 新增

- ✨ **Core Slope Processor** (`slope_processor.py`)
  - 核心斜率处理器
  - Multi-component batch processing
  - 多部件批量处理
  - SQLite database generation
  - SQLite数据库生成
  - Excel report with charts
  - 带图表的Excel报告

- 🔧 **CLI Interface** (`process_slope.py`)
  - 命令行界面
  - Support for custom input/output directories
  - 支持自定义输入输出目录
  - Vehicle ID specification
  - 车辆ID指定

### Fixed / 修复

- 🐛 **Image Path Handling** - Correctly parse absolute paths from statistics files
  - 图片路径处理 - 正确解析统计文件中的绝对路径

## [1.0.0] - 2025-03-01

### Added / 新增

- 🎉 **Initial Release** - Voltage slope data processing skill
  - 初始发布 - 电压斜率数据处理技能
  - Based on `vehicle-ripple-data` v4.x architecture
  - 基于纹波数据技能 v4.x 架构
  - Support for V0001-V0004 vehicle datasets
  - 支持 V0001-V0004 车辆数据集

---

## Version Notes / 版本说明

### Semantic Versioning / 语义化版本

- **MAJOR** (X.y.z) - Breaking changes / 破坏性变更
- **MINOR** (x.Y.z) - New features, backwards compatible / 新功能，向后兼容
- **PATCH** (x.y.Z) - Bug fixes / Bug 修复

### Slope vs Ripple / 斜率与纹波对比

| Feature / 功能 | Ripple v4.x | Slope v1.x |
|---------------|-------------|------------|
| Data Type / 数据类型 | Ripple (mV) | Slope (V/s) |
| Statistics / 统计指标 | Peak-to-peak, RMS | Max slope, avg slope |
| Config Source / 配置来源 | Self-contained | Reuses Ripple config |
| Components / 部件数 | 14 | 14 |

## Contributing / 贡献

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to suggest changes.
查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何建议更改。