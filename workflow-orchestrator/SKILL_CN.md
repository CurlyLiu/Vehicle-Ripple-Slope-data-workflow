---
name: workflow-orchestrator
description: 车辆纹波/斜率测试数据处理的跨阶段增量处理引擎。为每个阶段的输入计算指纹，与缓存对比判定是否需要重新执行，避免对未变更数据重复计算，大幅提升批量处理效率。
version: 1.0.0
author: CurlyLiu
tags: [workflow, incremental, orchestrator, cache, fingerprint, batch]
requires:
  - python>=3.8
---

# 工作流编排技能

车辆纹波/斜率测试数据工作流的跨阶段增量处理引擎。为每个阶段的输入计算指纹（SHA-256 / mtime+size），与缓存对比判定是否需要重新执行。避免对未变更数据重复计算，大幅提升批量处理效率。

## 功能特性

- **单车增量处理**：仅重新执行输入有变化的阶段
- **批量增量处理**：扫描多辆车，逐车决策
- **强制全量重跑**：清空缓存后全部重新执行
- **指纹缓存**：小文件用 SHA-256，大文件用 mtime+size
- **执行计划预览**：`plan` 命令可在执行前预览将运行哪些阶段
- **执行日志**：自动保存执行结果到 `.workflow_execution_log.json`

## 工作流阶段

```
阶段1 (AutoHandleFiles GUI) ──→ 手动执行，引擎不管理
         │
         ▼
阶段2_纹波 (vehicle-ripple-data) ──→ 增量
阶段2_斜率 (vehicle-slope-data) ──→ 增量（或由阶段2_纹波统一处理）
         │
         ▼
阶段3 (vehicle-report-generation) ──→ 增量
         │
         ▼
阶段4 (vehicle-database 导入) ──→ 增量
```

> **注意**：阶段1（AutoHandleFiles GUI）仍须手动执行。引擎管理阶段2-4。

## 指纹策略

| 阶段 | 输入文件 | 指纹算法 | 说明 |
|------|----------|:--------:|:-----|
| stage1 | `test_data/*.dmd` | `fast` (mtime+size) | 大文件用轻量指纹 |
| stage2_ripple | `statistics.xlsx` + 规则文件 | `sha256` | 小文件用内容哈希 |
| stage2_slope | `statistics.xlsx` + 规则文件 | `sha256` | 同上 |
| stage3 | `_summary.xlsx` + 模板 | `sha256` | 阶段2汇总文件+报告模板 |
| stage4 | `*_data.json` | `sha256` | 用于数据库导入 |

## 缓存文件

```
{Vehicle_Date}/{VehicleID}/.workflow_cache.json
```

缓存内容示例：
```json
{
  "stage1": { "fingerprint": "1714003200:10485760", "completed_at": "2026-04-25T10:00:00" },
  "stage2_ripple": { "fingerprint": "a1b2c3d4...", "completed_at": "2026-04-25T10:05:00" },
  "stage2_slope": { "fingerprint": "e5f6g7h8...", "completed_at": "2026-04-25T10:06:00" },
  "stage3": { "fingerprint": "i9j0k1l2...", "completed_at": "2026-04-25T10:08:00" },
  "stage4": { "fingerprint": "m3n4o5p6...", "completed_at": "2026-04-25T10:10:00" }
}
```

### 执行日志文件

每次执行后自动保存执行日志：

```
{Vehicle_Date}/{VehicleID}/.workflow_execution_log.json
```

内容包含完整的执行计划和各阶段执行结果：
```json
{
  "vehicle_id": "V0001",
  "executed_at": "2026-05-09T14:30:00",
  "plan": [...],
  "execution": [...]
}
```

## CLI 命令

### 单车处理

```bash
# 生成执行计划（仅预览，不执行）
python incremental_workflow.py plan V0001 --base-dir F:/Vehicle_Date

# 执行增量工作流
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date --force

# 仅执行指定阶段
python incremental_workflow.py run V0001 --stages 2_ripple
python incremental_workflow.py run V0001 --stages 2_slope
python incremental_workflow.py run V0001 --stages 3
python incremental_workflow.py run V0001 --stages 4

# 清空缓存
python incremental_workflow.py clear-cache V0001
```

### 批量处理

```bash
# 批量扫描并增量处理所有车辆（阶段2→3→4）
python incremental_workflow.py batch --scan F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# 仅批量导入数据库（阶段4）
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `command` | `plan` / `run` / `clear-cache` / `batch` |
| `vehicle_id` | 车辆ID（plan/run/clear-cache 需要） |
| `--scan` | 批量扫描目录（batch 命令使用） |
| `--base-dir` | 车辆数据根目录（默认: F:/Vehicle_Date） |
| `--skills-dir` | 技能安装目录（默认: ~/.claude/skills） |
| `--force` | 强制全量重跑，清空缓存 |
| `--stages` | 指定阶段: `all`, `1`, `2`, `3`, `4`, `2_ripple`, `2_slope` |

## 执行计划示例

### 单车示例

```
======================================================================
车辆 V0001 增量处理执行计划
======================================================================
[跳过] [stage1                        ] 无 test_data 目录
[执行] [stage2_ripple                 ] 首次运行
[跳过] [stage2_slope                  ] 由 stage2_ripple 统一处理
[执行] [stage3                        ] 首次运行
[跳过] [stage3_ripple_FM_V            ] 无汇总文件
...
======================================================================
总计: 2 个阶段需执行, 38 个阶段可跳过
预估总耗时: 20 分钟
======================================================================
```

> **注意**：当车辆同时存在 RIPPLE 和 SLOPE 数据且 `stage2_ripple` 需执行时，`vehicle_skills_cli.py process` 会统一处理两者，`stage2_slope` 自动标记为"由 stage2_ripple 统一处理"而跳过，避免 SLOPE 被重复处理。

### 批量处理汇总示例

```
======================================================================
批量增量处理汇总
======================================================================
总车辆数: 18
成功: 16
无需处理: 2
失败: 0
总耗时: 192.3s

Vehicle ID   阶段2          阶段3      阶段4          状态       耗时
----------------------------------------------------------------------
V0001        执行(R+S)      执行(4/4)  跳过           OK       9.3
V0002        执行(R+S)      跳过       执行(12/12)    OK       23.6
V0005        执行(R+S)      跳过       执行(26/26)    OK       63.2
V0017        执行(R+S)      跳过       跳过           OK       2.1
...
======================================================================
批量日志已保存: F:/Vehicle_Date/.workflow_batch_log.json
```

## 与其他技能的集成

编排器通过 CLI 自动检测并调用其他技能：

- **阶段2**：调用 `vehicle_skills_cli.py process`（vehicle-ripple-data / vehicle-slope-data）
- **阶段3**：调用 `vehicle_report_cli.py generate`（vehicle-report-generation）
- **阶段4**：调用 `vehicle_database.py add`（vehicle-database）

## 依赖

- Python >= 3.8
- 仅使用标准库（json, hashlib, pathlib, subprocess）
