---
name: vehicle-database
description: 车辆纹波与斜率测试数据统一管理工具，采用双库架构（Ripple.db + Slope.db），支持多格式数据源聚合（JSON/SQLite/Excel）和跨车辆查询/导出。
version: 3.4.0
author: CurlyLiu
tags: [database, vehicle, ripple, slope, cli, sqlite, dual-db]
requires:
  - python>=3.8
  - click
  - sqlite3
  - pandas
  - openpyxl
---

# 车辆数据库技能

车辆纹波与斜率测试数据统一管理和查询工具。

**架构**：双数据库设计（Ripple.db + Slope.db）— V3.4起分离。

## 功能特性

- **多格式数据源聚合**：支持 JSON、SQLite、Excel 三种格式自动检测和导入
- **双库架构**：Ripple.db（纹波数据）+ Slope.db（斜率数据），独立存储但共享 Schema
- **统一数据模型**：标准化的 vehicles、components、test_conditions 表
- **CLI 命令行工具**：完整的命令行接口，支持初始化、导入、查询、导出
- **批量操作**：支持多车辆批量导入、更新、删除
- **数据导出**：支持导出为 JSON、Excel、SQLite 格式
- **跨库查询**：`--type ripple|slope` 参数选择目标数据库
- **配置持久化**：自动保存数据源路径到 `~/.vehicle_database/config.json`

## 数据架构

```
F:/Vehicle_Database/
├── Ripple.db  (ripple_results + 共享表)
│   ├── vehicles, components, test_conditions
│   ├── ripple_results
│   └── data_batches, matching_logs
│
└── Slope.db   (slope_results + 共享表)
    ├── vehicles, components, test_conditions
    ├── slope_results
    └── data_batches, matching_logs
```

每个数据库都包含完整的共享表集合。当车辆同时有纹波和斜率数据时，vehicle_info 会同步到两个数据库。

## 支持的导入格式

| 优先级 | 格式 | 文件模式 | 说明 |
|:------:|:----:|:---------|:-----|
| 1 | JSON | `*_RIPPLE_data.json`, `*_SLOPE_data.json` | 最完整，含所有元数据 |
| 2 | SQLite | `*.db` | 技能生成的数据库文件 |
| 3 | Excel | `*_summary.xlsx` | 汇总报告 |

## 快速开始

### 初始化数据库（必须指定输出位置）

```bash
cd ~/.claude/skills/vehicle-database

# 指定输出目录（自动创建 Vehicle_Database/ 目录，内含 Ripple.db + Slope.db）
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database
```

### 导入车辆数据

```bash
# 添加单个车辆
python vehicle_database.py add V0001

# 添加多个车辆
python vehicle_database.py add V0001 V0002 V0003

# 添加所有车辆
python vehicle_database.py add --all
```

### 查询数据

```bash
# 列出所有车辆（默认查询 Ripple.db）
python vehicle_database.py list

# 从 Slope.db 查询
python vehicle_database.py list --type slope

# 显示车辆详情
python vehicle_database.py show V0001
python vehicle_database.py show V0001 --type slope

# 数据库统计
python vehicle_database.py stats
python vehicle_database.py stats --type slope
```

### 导出数据

```bash
# 导出单个车辆到 JSON
python vehicle_database.py export V0001 --json -o V0001.json

# 从 Slope.db 导出
python vehicle_database.py export V0001 --type slope --json -o V0001_slope.json

# 导出所有车辆到 Excel
python vehicle_database.py export --all --excel -o all_vehicles/

# 合并所有车辆到单个文件
python vehicle_database.py export --all --combine --json -o all_vehicles.json
```

## CLI 命令参考

### 全局选项

| 选项 | 简写 | 说明 |
|------|------|------|
| `--source` | `-s` | 数据源路径（自动保存到配置） |
| `--database` | `-d` | 数据库目录路径 |
| `--format` | `-f` | 输入格式过滤：db/excel/json/all |
| `--verbose` | `-v` | 详细输出模式 |

### 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `init` | 初始化双库（Ripple.db + Slope.db） | `python vehicle_database.py init -o F:/DB` |
| `add` | 添加车辆 | `python vehicle_database.py add V0001` |
| `update` | 更新车辆数据 | `python vehicle_database.py update V0001` |
| `remove` | 从数据库删除车辆 | `python vehicle_database.py remove V0001` |
| `list` | 列出所有车辆 | `python vehicle_database.py list` |
| `list --type slope` | 从 Slope.db 列出 | `python vehicle_database.py list --type slope` |
| `show` | 显示车辆详情 | `python vehicle_database.py show V0001` |
| `stats` | 数据库统计 | `python vehicle_database.py stats` |
| `export` | 导出车辆数据 | `python vehicle_database.py export V0001 --json` |

### `--type` 参数

所有读取/查询/导出命令都支持 `--type` 参数：

- `--type ripple`（默认）：操作 Ripple.db
- `--type slope`：操作 Slope.db

写入命令（add/update/remove）根据源文件类型自动路由到对应数据库。

## 数据模型

### 共享表（Ripple.db 和 Slope.db 都有）

**vehicles** — 车辆基本信息
- vehicle_id (PK)、vehicle_model、manufacturer、level、energy_type
- 尺寸、重量、电池参数、电机参数等

**components** — 部件定义
- channel_code (PK)、component_name、unit、component_type

**test_conditions** — 测试工况
- condition_id (PK)、condition_name、soc_level、category

### Ripple.db 特有

**ripple_results** — 纹波测试结果
- 时域：effective_value、vpp_value
- 频域：peak_frequency_khz、peak_amplitude、frequency_rms
- 元数据：image_path、match_confidence、match_method

### Slope.db 特有

**slope_results** — 斜率测试结果
- slope_max、slope_min、slope_max_abs、slope_unit
- 元数据：image_path、match_confidence、match_method

## 配置文件

保存在：`~/.vehicle_database/config.json`

```json
{
  "source_path": "F:/Vehicle_Date",
  "database_path": "F:/Vehicle_Database"
}
```

> 向后兼容：如果 `database_path` 指向 `.db` 文件（旧配置），会自动提取其所在目录。

## 扩展开发

### 添加新的导入器

```python
from src.importers.base import BaseImporter

class NewFormatImporter(BaseImporter):
    def can_import(self, file_path: Path) -> bool:
        return file_path.suffix == '.new'

    def import_data(self, conn, vehicle_id: str, file_path: Path) -> ImportResult:
        # 实现导入逻辑
        pass
```

## 许可证

MIT License
