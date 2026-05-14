# Vehicle Skills CLI 命令大全 / 车辆技能 CLI 命令参考

> 本文档涵盖纹波技能（vehicle-ripple-data）和斜率技能（vehicle-slope-data）的全部 CLI 用法。

---

## 目录

1. [统一 CLI（同时处理 RIPPLE + SLOPE）](#统一-cli)
2. [斜率独立 CLI（仅处理 SLOPE）](#斜率独立-cli)
3. [文件夹结构规范](#文件夹结构规范)
4. [输出文件说明](#输出文件说明)
5. [常见问题](#常见问题)

---

## 统一 CLI

**入口文件：** `scripts/cli/vehicle_skills_cli.py`

**功能：** 同时处理车辆的纹波（RIPPLE）和斜率（SLOPE）数据，一套命令完成全部操作。

### 快速开始

```bash
cd C:\Users\31915\.claude\skills\vehicle-ripple-data\scripts\cli

# 处理单个车辆
python vehicle_skills_cli.py process F:/Vehicle_Date/V0001

# 批量处理（自动扫描目录下所有车辆）
python vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress

# 批量处理（显式指定车辆）
python vehicle_skills_cli.py batch F:/Vehicle_Date/V0006 F:/Vehicle_Date/V0007 --progress
```

### 命令详解

#### `process` — 处理单个车辆

```bash
python vehicle_skills_cli.py process <vehicle_folder> [选项]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `vehicle_folder` | 车辆根目录（包含 `{VehID}_RIPPLE` 和/或 `{VehID}_SLOPE`） | `F:/Vehicle_Date/V0001` |
| `--progress`, `-p` | 显示进度条 | `--progress` |
| `--output`, `-o` | 自定义输出目录 | `--output F:/output` |

**示例：**

```bash
# 基础用法
python vehicle_skills_cli.py process F:/Vehicle_Date/V0001

# 带进度条
python vehicle_skills_cli.py process F:/Vehicle_Date/V0001 --progress

# 指定输出目录
python vehicle_skills_cli.py process F:/Vehicle_Date/V0001 --output F:/results
```

#### `batch` — 批量处理多个车辆

**模式 A：显式列表**

```bash
python vehicle_skills_cli.py batch <folder1> <folder2> ... [选项]
```

**模式 B：自动扫描**

```bash
python vehicle_skills_cli.py batch --scan <parent_folder> [选项]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `vehicle_folders` | 车辆文件夹路径列表（模式 A） | `F:/Vehicle_Date/V0001` |
| `--scan`, `-s` | 自动扫描父目录（模式 B） | `--scan F:/Vehicle_Date` |
| `--progress`, `-p` | 显示进度条 | `--progress` |

**示例：**

```bash
# 显式列表 - 处理指定车辆
python vehicle_skills_cli.py batch F:/Vehicle_Date/V0006 F:/Vehicle_Date/V0007

# 显式列表 - 带进度条
python vehicle_skills_cli.py batch F:/Vehicle_Date/V0006 F:/Vehicle_Date/V0007 --progress

# 自动扫描 - 处理目录下所有车辆
python vehicle_skills_cli.py batch --scan F:/Vehicle_Date

# 自动扫描 - 带进度条（推荐）
python vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress
```

#### `validate` — 验证车辆数据

仅验证文件夹结构，不生成任何输出文件。

```bash
python vehicle_skills_cli.py validate <vehicle_folder>
```

**示例：**

```bash
python vehicle_skills_cli.py validate F:/Vehicle_Date/V0001
```

**输出示例：**

```
Validation Report / 验证报告: V0001
============================================================
Status / 状态: [OK] Valid / 有效

Data Found / 发现的数据:
  RIPPLE: Yes
    Components / 组件数: 2
  SLOPE:  Yes
    Components / 组件数: 2
```

#### `version` — 显示版本信息

```bash
python vehicle_skills_cli.py version
```

**输出示例：**

```
Vehicle Skills CLI / 车辆技能命令行工具
============================================================
CLI Version / CLI版本: 1.1.0
Ripple Skill / 纹波技能: v4.3
Slope Skill / 斜率技能: v1.2
Python: 3.14.0
============================================================
```

---

## 斜率独立 CLI

**入口文件：** `vehicle-slope-data/scripts/cli/process_slope.py`

**功能：** 仅处理斜率（SLOPE）数据，适合不需要纹波数据的场景。

### 快速开始

```bash
cd ~/.claude/skills/vehicle-slope-data/scripts/cli

# 处理单个车辆
python process_slope.py process --folder F:/Vehicle_Date/V0001/V0001_SLOPE

# 批量处理（自动扫描）
python process_slope.py batch --scan F:/Vehicle_Date --progress
```

### 命令详解

#### `process` — 处理单个车辆

```bash
python process_slope.py process [选项]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `--folder`, `-f` | 车辆 SLOPE 文件夹路径（必填） | `--folder V0001_SLOPE` |
| `--validate-first`, `-v` | 处理前先验证数据完整性 | `--validate-first` |
| `--format`, `-fmt` | 输出格式：`all`, `json`, `excel`, `sqlite` | `--format json,excel` |
| `--output-dir`, `-o` | 自定义输出目录 | `--output-dir F:/output` |
| `--verbose`, `-V` | 显示详细日志 | `--verbose` |

**示例：**

```bash
# 基础用法
python process_slope.py process --folder F:/Vehicle_Date/V0001/V0001_SLOPE

# 验证后处理
python process_slope.py process --folder F:/Vehicle_Date/V0001/V0001_SLOPE --validate-first

# 只生成 JSON 和 Excel
python process_slope.py process --folder F:/Vehicle_Date/V0001/V0001_SLOPE --format json,excel

# 详细日志
python process_slope.py process --folder F:/Vehicle_Date/V0001/V0001_SLOPE --verbose
```

#### `batch` — 批量处理多个车辆

**模式 A：显式列表**

```bash
python process_slope.py batch <folder1> <folder2> ... [选项]
```

**模式 B：自动扫描**

```bash
python process_slope.py batch --scan <parent_folder> [选项]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `folders` | 车辆文件夹路径列表（模式 A） | `V0001_SLOPE V0002_SLOPE` |
| `--scan`, `-s` | 自动扫描父目录（模式 B） | `--scan F:/Vehicle_Date` |
| `--validate-first`, `-v` | 处理前先验证 | `--validate-first` |
| `--format`, `-fmt` | 输出格式 | `--format all` |
| `--progress`, `-p` | 显示进度条 | `--progress` |
| `--verbose`, `-V` | 显示详细日志 | `--verbose` |

**示例：**

```bash
# 显式列表
python process_slope.py batch V0001_SLOPE V0002_SLOPE

# 自动扫描
python process_slope.py batch --scan F:/Vehicle_Date

# 自动扫描 + 进度条 + 先验证（推荐）
python process_slope.py batch --scan F:/Vehicle_Date --progress --validate-first
```

---

## 文件夹结构规范

车辆数据必须遵循以下目录结构：

```
Vehicle_Date/                  # 父目录
├── V0001/                     # 车辆根目录
│   ├── V0001_RIPPLE/          # 纹波数据文件夹
│   │   ├── FM_V/              # 组件文件夹
│   │   │   ├── statistics.xlsx
│   │   │   └── *.png
│   │   ├── RM_V/
│   │   │   ├── statistics.xlsx
│   │   │   └── *.png
│   │   └── V0001_RIPPLE_output/   # 自动生成：纹波输出
│   │       ├── V0001_RIPPLE_data.json
│   │       ├── V0001_RIPPLE_summary.xlsx
│   │       ├── V0001_RIPPLE.db
│   │       └── error_report.md
│   ├── V0001_SLOPE/           # 斜率数据文件夹
│   │   ├── FM_V/
│   │   │   └── statistics.xlsx
│   │   ├── RM_V/
│   │   │   └── statistics.xlsx
│   │   └── V0001_SLOPE_output/    # 自动生成：斜率输出
│   │       ├── V0001_SLOPE_data.json
│   │       ├── V0001_SLOPE_summary.xlsx
│   │       ├── V0001_SLOPE.db
│   │       └── error_report.md
│   └── vehicle_info.xlsx      # 车辆信息（可选）
├── V0002/
│   ├── V0002_RIPPLE/
│   └── V0002_SLOPE/
└── ...
```

**命名规则：**

- 车辆根目录：`{VehicleID}`（如 `V0001`）
- 纹波数据文件夹：`{VehicleID}_RIPPLE`
- 斜率数据文件夹：`{VehicleID}_SLOPE`
- 组件文件夹：任意名称（如 `FM_V`, `RM_V`, `ACC_V` 等）

---

## 输出文件说明

### 纹波输出（RIPPLE）

| 文件 | 格式 | 说明 |
|------|------|------|
| `{VehID}_RIPPLE_data.json` | JSON | 结构化数据，包含所有组件和工况 |
| `{VehID}_RIPPLE_summary.xlsx` | Excel | V3.0 格式报告，含多个工作表 |
| `{VehID}_RIPPLE.db` | SQLite | 数据库文件，含 4 个表 |
| `error_report.md` | Markdown | 处理报告和错误日志 |

### 斜率输出（SLOPE）

| 文件 | 格式 | 说明 |
|------|------|------|
| `{VehID}_SLOPE_data.json` | JSON | 结构化数据 |
| `{VehID}_SLOPE_summary.xlsx` | Excel | V1.0 格式报告，含 3 个工作表 |
| `{VehID}_SLOPE.db` | SQLite | 数据库文件，含 4 个表 |
| `error_report.md` | Markdown | 处理报告和错误日志 |

---

## 常见问题

### Q1: 如何同时处理 RIPPLE 和 SLOPE？

使用统一 CLI：

```bash
python vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress
```

### Q2: 只想处理 SLOPE 数据怎么办？

使用斜率独立 CLI：

```bash
python process_slope.py batch --scan F:/Vehicle_Date --progress
```

### Q3: 批量处理时如何只处理特定车辆？

使用显式列表模式：

```bash
python vehicle_skills_cli.py batch F:/Vehicle_Date/V0006 F:/Vehicle_Date/V0007 --progress
```

### Q4: 输出文件在哪里？

输出文件自动生成在对应数据文件夹内的 `_output` 子目录中：

- 纹波：`{VehicleID}_RIPPLE/{VehicleID}_RIPPLE_output/`
- 斜率：`{VehicleID}_SLOPE/{VehicleID}_SLOPE_output/`

### Q5: 如何处理没有 RIPPLE 或没有 SLOPE 的车辆？

CLI 会自动检测车辆文件夹内是否存在 `_RIPPLE` 和 `_SLOPE` 子文件夹，只处理存在的数据。如果两种数据都不存在，会跳过该车辆并提示错误。

### Q6: 遇到编码问题（中文显示乱码）怎么办？

Windows 命令行默认使用 GBK 编码。建议使用以下方式：

```bash
# 方式 1：使用 PowerShell（推荐）
python vehicle_skills_cli.py batch --scan F:/Vehicle_Date

# 方式 2：设置 UTF-8 编码
chcp 65001
python vehicle_skills_cli.py batch --scan F:/Vehicle_Date
```

### Q7: 如何查看帮助信息？

```bash
# 统一 CLI
python vehicle_skills_cli.py --help
python vehicle_skills_cli.py process --help
python vehicle_skills_cli.py batch --help

# 斜率 CLI
python process_slope.py --help
python process_slope.py process --help
python process_slope.py batch --help
```
