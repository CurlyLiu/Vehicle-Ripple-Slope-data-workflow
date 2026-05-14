# Vehicle Ripple / Slope Data Workflow

车辆高压纹波与电压斜率测试数据处理完整工作流。

## Overview

本项目是一个 monorepo，聚合了车辆纹波/斜率测试数据处理的 5 个核心 skill，覆盖从原始数据分析、数据整合、报告生成到统一数据库管理的完整流程。

## Workflow

```
Dewesoft .dmd 原始数据
         │
         ▼
┌─────────────────────────────┐
│ Stage 1: AutoHandleFiles    │  PySide6 GUI, pyDmdReader, scipy
│ 纹波分析 + 斜率分析 + FFT    │
└─────────────────────────────┘
         │
         ├──→ {VehicleID}_RIPPLE/
         └──→ {VehicleID}_SLOPE/
         │
         ▼
┌────────────────────────────────────────────┐
│ Stage 2: Data Integration (ripple/slope)   │
│ vehicle-ripple-data / vehicle-slope-data   │
└────────────────────────────────────────────┘
         │
         ├──→ {VehicleID}_RIPPLE_output/
         └──→ {VehicleID}_SLOPE_output/
         │
         ▼
┌─────────────────────────────────┐
│ Stage 3: Report Generation      │
│ vehicle-report-generation       │
└─────────────────────────────────┘
         │
         ├──→ {VehicleID}_RIPPLE_REPORT_{Component}.docx
         └──→ {VehicleID}_SLOPE_REPORT_{Component}.docx
         │
         ▼
┌─────────────────────────────────┐
│ Stage 4: Unified Database       │
│ vehicle-database                │
└─────────────────────────────────┘
```

详见完整工作流文档：[WORKFLOW.md](WORKFLOW.md)

## Skills

| Skill | Description | Version |
|-------|-------------|---------|
| [vehicle-ripple-data](vehicle-ripple-data/) | 车辆高压纹波测试数据整合，支持组件通道映射、工况匹配、数据验证、SQLite/Excel 导出 | 4.4 |
| [vehicle-slope-data](vehicle-slope-data/) | 车辆电压斜率测试数据整合，基于 ripple-data 架构，适配斜率统计列 | 1.3 |
| [workflow-orchestrator](workflow-orchestrator/) | 跨阶段增量工作流引擎，指纹缓存避免重复计算 | 1.0.0 |
| [vehicle-database](vehicle-database/) | 双数据库架构（Ripple.db + Slope.db），支持多格式聚合与跨车查询 | 3.4.0 |
| [vehicle-report-generation](vehicle-report-generation/) | 自动生成 Word (.docx) 测试报告，支持纹波/斜率报告、三级动态裁剪 | 1.0.0 |

## Repository Structure

```
.
├── README.md                          # 本文件
├── WORKFLOW.md                        # 完整工作流规划书
├── .gitignore                         # 全局 gitignore
├── vehicle-ripple-data/               # 纹波数据整合 Skill
├── vehicle-slope-data/                # 斜率数据整合 Skill
├── workflow-orchestrator/             # 增量工作流引擎
├── vehicle-database/                  # 统一数据库管理
└── vehicle-report-generation/         # 报告自动生成
```

## Tech Stack

- **Python** >= 3.8
- **Data Processing**: pandas, openpyxl, sqlite3
- **Report Generation**: python-docx
- **CLI**: click
- **GUI**: PySide6 (Stage 1)
- **Workflow Engine**: SHA-256 fingerprint + mtime/size cache

## License

MIT
