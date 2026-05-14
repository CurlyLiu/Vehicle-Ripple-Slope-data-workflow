# Vehicle Database Skill

车辆纹波与斜率测试数据统一管理和查询工具。

## 功能特性

- **多格式数据源聚合**：支持JSON、SQLite、Excel三种格式自动检测和导入
- **统一数据模型**：标准化的车辆、部件、工况数据模型
- **CLI命令行工具**：完整的命令行接口，支持初始化、导入、查询、导出
- **批量操作**：支持多车辆批量导入、更新、删除
- **数据导出**：支持导出为JSON、Excel、SQLite格式
- **配置持久化**：自动保存数据源路径，下次使用无需重复指定

## 安装

```bash
# 进入skill目录
cd ~/.claude/skills/vehicle-database

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

### 1. 初始化数据库并导入所有车辆

```bash
# 必须指定输出目录 (-o) 或数据库路径 (-d)
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database

# 或直接指定数据库路径
python vehicle_database.py -s F:/Vehicle_Date init -d F:/Vehicle_Database/vehicle.db
```

**说明**：
- `init` 命令**必须**使用 `-o` 或 `-d` 指定数据库位置
- 自动导入 `Vehicle_Date` 中所有车辆数据
- 数据源路径会自动保存，下次无需指定
- 如果未指定 `-s`，且默认路径 `F:/Vehicle_Date` 不存在，会**交互式提示**输入数据源路径

### 2. 添加车辆数据

```bash
# 添加单个车辆
python vehicle_database.py add V0001

# 添加多个车辆
python vehicle_database.py add V0001 V0002 V0003

# 添加所有车辆（从数据源）
python vehicle_database.py add --all

# 指定数据源路径（会保存到配置）
python vehicle_database.py -s F:/Vehicle_Date add V0001
```

### 3. 更新车辆数据

```bash
# 更新单个车辆（重新导入）
python vehicle_database.py update V0001

# 更新多个车辆
python vehicle_database.py update V0001 V0002

# 更新所有车辆
python vehicle_database.py update --all
```

### 4. 删除车辆数据

```bash
# 从数据库删除单个车辆（保留源文件）
python vehicle_database.py remove V0001

# 删除多个车辆
python vehicle_database.py remove V0001 V0002 V0003

# 删除所有车辆
python vehicle_database.py remove --all
```

### 5. 查询数据

```bash
# 列出所有车辆
python vehicle_database.py list

# 仅列出车辆ID（便于管道操作）
python vehicle_database.py list --ids

# 显示车辆详情
python vehicle_database.py show V0001

# 数据库统计
python vehicle_database.py stats
```

### 6. 导出数据

```bash
# 导出单个车辆为JSON
python vehicle_database.py export V0001 --json -o V0001.json

# 导出单个车辆为Excel
python vehicle_database.py export V0001 --excel -o V0001.xlsx

# 导出所有车辆为Excel
python vehicle_database.py export --all --excel -o all_vehicles/

# 导出为SQLite数据库
python vehicle_database.py export V0001 --sqlite -o V0001.db
```

## CLI命令参考

### 全局选项

| 选项 | 简写 | 说明 |
|------|------|------|
| `--source` | `-s` | 数据源路径（Vehicle_Date文件夹） |
| `--database` | `-d` | 数据库路径 |
| `--format` | `-f` | 输入格式过滤：db/excel/json/all |
| `--verbose` | `-v` | 详细输出模式（显示扫描路径、SQL执行详情等） |

### 交互式路径提示

当数据源路径未配置且默认路径 `F:/Vehicle_Date` 不存在时，`init`/`add`/`update` 命令会**交互式提示**输入数据源路径：

```
No data source path configured.
Default path not found: F:/Vehicle_Date
Please enter the vehicle data source path: _
```

输入的路径会被自动保存，下次无需重复输入。

### 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `init` | 初始化数据库并导入所有车辆 | `python vehicle_database.py init` |
| `add` | 添加车辆到数据库 | `python vehicle_database.py add V0001` |
| `update` | 更新车辆数据 | `python vehicle_database.py update V0001` |
| `remove` | 从数据库删除车辆 | `python vehicle_database.py remove V0001` |
| `list` | 列出所有车辆 | `python vehicle_database.py list` |
| `list --ids` | 仅列出车辆ID | `python vehicle_database.py list --ids` |
| `show` | 显示车辆详情 | `python vehicle_database.py show V0001` |
| `stats` | 数据库统计 | `python vehicle_database.py stats` |
| `export` | 导出车辆数据 | `python vehicle_database.py export V0001 --json` |

## 数据源路径解析

工具按以下优先级确定数据源路径：

1. 命令行参数 `--source PATH`
2. 配置文件中保存的路径（上次使用）
3. 默认路径 `F:/Vehicle_Date`

## 输入格式过滤

使用 `--format` 选项可以控制导入时只处理特定格式的源文件：

```bash
# 只导入JSON文件
python vehicle_database.py -f json add V0001

# 只导入Excel文件
python vehicle_database.py -f excel add V0001

# 只导入SQLite数据库文件
python vehicle_database.py -f db add V0001

# 导入所有格式（默认）
python vehicle_database.py -f all add V0001
```

## 数据模型

### 核心表

- **vehicles**: 车辆基本信息
- **components**: 部件定义（通道代码、名称、单位）
- **test_conditions**: 测试工况（工况ID、名称、SOC等级）

## 配置

编辑 `config.yaml`:

```yaml
database:
  default_path: F:/Vehicle_Database/vehicle_database.db

sync:
  source_dir: F:/Vehicle_Date
  source_path: null  # 上次使用的数据源路径（自动更新）
  watch_interval: 60
```

## 完整示例

```bash
# 步骤1：初始化数据库（导入所有车辆）
cd ~/.claude/skills/vehicle-database
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database

# 步骤2：查看已导入的车辆
python vehicle_database.py list

# 步骤3：查看某个车辆的详情
python vehicle_database.py show V0001

# 步骤4：导出数据为Excel
python vehicle_database.py export --all --excel -o F:/Vehicle_Database/exports/

# 步骤5：添加新车辆（如果有新数据）
python vehicle_database.py add V0006

# 步骤6：更新已有车辆数据
python vehicle_database.py update V0001
```

## 注意事项

1. **`init` 强制参数**：`init` 命令**必须**使用 `-o` 或 `-d` 指定数据库位置
2. **删除操作**：`remove` 命令只删除数据库记录，不会删除 `Vehicle_Date` 中的源文件
3. **更新操作**：`update` 会先删除数据库中的旧数据，然后重新导入
4. **交互式提示**：当数据源路径未配置且默认路径不存在时，`init`/`add`/`update` 会交互式提示输入路径
5. **配置保存**：使用 `-s` 指定的路径会自动保存到 `~/.vehicle_database/config.json`，下次无需重复输入
6. **verbose 模式**：使用 `-v` 可查看详细的扫描路径、SQL 执行等信息

## 许可证

MIT License
