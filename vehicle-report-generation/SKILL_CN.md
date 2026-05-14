---
name: vehicle-report-generation
description: 根据 vehicle-ripple-data 和 vehicle-slope-data 生成的 Excel/SQLite 结果文件及图片，自动生成 Word (.docx) 格式的车辆检测报告。支持纹波报告、斜率报告、多通道自动检测、三级动态裁剪。
version: 1.0.0
author: CurlyLiu
tags: [report, docx, vehicle, ripple, slope, word, template]
requires:
  - python>=3.8
  - python-docx
  - openpyxl
  - click
---

# 车辆报告生成技能

根据 vehicle-ripple-data 和 vehicle-slope-data 技能输出的 Excel/SQLite 结果文件及图片，自动生成 Word (.docx) 格式的车辆检测报告。

## 功能特性

- **纹波报告**：读取纹波分析结果，填充检验结果数值（Vpp）和试验数据曲线图片
- **斜率报告**：读取斜率分析结果，填充斜率数值（V/s）和试验数据曲线图片
- **多通道支持**：自动检测组件通道，为每个通道生成独立报告
- **Excel优先，SQLite回退**：优先读取Excel摘要文件，遇到编码问题时自动回退到SQLite数据库
- **三级动态裁剪**：根据实际测试数据自动裁剪空行、图片对、章节
- **测试覆盖度摘要**：裁剪后自动在报告顶部插入覆盖度摘要表

## 使用方式

### 命令格式

```bash
# 生成全部报告（纹波+斜率，所有通道）
python vehicle_report_cli.py generate V0006

# 仅生成纹波报告
python vehicle_report_cli.py generate V0006 --type ripple

# 仅生成斜率报告
python vehicle_report_cli.py generate V0006 --type slope

# 指定组件通道
python vehicle_report_cli.py generate V0005 --type ripple --component ACC_A

# 批量生成目标路径下所有车辆的报告
python vehicle_report_cli.py batch F:/Vehicle_Date
python vehicle_report_cli.py batch F:/Vehicle_Date --type ripple
python vehicle_report_cli.py batch F:/Vehicle_Date --type slope --skip-existing
```

### 输出路径

- **纹波报告**：`{base_dir}/{vehicle_id}/{vehicle_id}_RIPPLE/{vehicle_id}_RIPPLE_output/{vehicle_id}_RIPPLE_REPORT_{ComponentCode}.docx`
- **斜率报告**：`{base_dir}/{vehicle_id}/{vehicle_id}_SLOPE/{vehicle_id}_SLOPE_output/{vehicle_id}_SLOPE_REPORT_{ComponentCode}.docx`

## 报告模板结构

每个通道生成一份独立报告：

```
报告标题: {VehicleID} 纹波/斜率检测报告 — {ComponentName}

├── 第1章: SOC ≥ 70% 区间数据
│   ├── 检验结果表格 (9个检验项目)
│   └── 试验数据曲线 (16组图片+图注)
│
├── 第2章: SOC 40%-70% 区间数据
│   ├── 检验结果表格
│   └── 试验数据曲线
│
└── 第3章: SOC ≤ 40% 区间数据
    ├── 检验结果表格
    └── 试验数据曲线
```

### 检验项目映射 (9项检验)

| 序号 | 检验项目 | 工况一 | 工况二 | 工况三 |
|:----:|:---------|:-------|:-------|:-------|
| 1 | 停车D档工况 | 静止低温 | 静止高温 | — |
| 2 | 急加速工况 | 零百加速 | 多次加速 | — |
| 3 | 匀速工况 | 匀速低温 | 匀速高温 | — |
| 4 | 超车工况 | 超越加速 | — | — |
| 5 | 滑行工况 | D档滑行 | — | — |
| 6 | 紧急制动工况 | 紧急制动 | — | — |
| 7 | 爬坡工况 | 爬坡 | 爬坡低温 | 爬坡高温 |
| 8 | 停车充电 | 直流充电冷风 | 直流充电暖风 | — |
| 9 | 停车充电 | 交流充电冷风 | 交流充电暖风 | — |

## 通道类型自动识别

报告生成器根据 `component_code` 后缀自动判断通道类型，动态切换单位和描述：

| 通道后缀 | 类型 | 纹波单位 | 纹波阈值 | 斜率单位 | 标准要求列转换 |
|:--------:|:----:|:--------:|:--------:|:--------:|:-------------|
| `_A` | 电流 | App | 100App | A/s | "电压纹波"→"电流纹波"，"30Vpp"→"100App" |
| `_V` | 电压 | Vpp | 30Vpp | V/s | 保持原文 |

实现位置: `vehicle-report-generation/scripts/core/ripple_report.py` / `slope_report.py`

## 数据读取策略

```
优先读取Excel:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE_summary.xlsx
    或
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE_summary.xlsx

Excel读取失败 → 回退到SQLite:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE.db
    或
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE.db
```

## 动态裁剪行为

报告生成时会自动根据实际测试数据对模板进行**三级裁剪**：

1. **行级裁剪**：某检验项目的所有工况（工况一/二/三）均无有效数据时，从检验结果表格中删除该行。
2. **图片对级裁剪**：某张试验曲线图无对应记录或图片文件不存在时，从图片表格中成对删除"图片行 + 图注行"。
3. **章节级裁剪**：某个SOC区间的检验结果表格与图片表格均无有效内容时，删除该SOC标题段落及其下的两个表格。

裁剪后，报告顶部会自动插入**测试覆盖度摘要表**，列出已测SOC区间、已测工况数、已测试验曲线图数及数据完整度评级（完整覆盖 / 部分覆盖 / 无数据）。

若某个组件完全没有采集到任何有效数据，文档主体会保留"该组件未采集到任何有效数据"提示，而非输出大量空表。

### 关闭裁剪（恢复旧行为）

如需生成包含全部章节和空行的报告（旧版固定填充行为），可通过脚本调用时传入 `prune=False`：

```python
generate_ripple_report(vid, comp, base_dir, template, output, prune=False)
```

CLI 默认启用裁剪，暂不支持命令行开关；如需批量关闭，建议直接通过脚本调用。

## 依赖

```bash
pip install -r requirements.txt
```

需要：`python-docx`、`openpyxl`、`click`
