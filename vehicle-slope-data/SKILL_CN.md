---
name: vehicle-slope-data
description: 整合并结构化车辆电压斜率测试数据，用于下游分析和报告生成。当处理车辆组件文件夹（FM、RM、DCC、ACC、PTC、ACCM、LV、FAN、BATT 等）的电压斜率统计数据时使用，文件夹命名需符合 {VehicleID}_SLOPE 规范。本技能为数据库构建准备结构化数据，生成标准格式的 Excel 汇总报告（车辆信息采用纵向 Parameter|Value 布局），创建中文综合处理报告，并将所有输出组织到 {VehicleID}_SLOPE_output 文件夹中。处理组件通道映射、工况匹配（与 vehicle-ripple-data 相同的逻辑：精确匹配、括号去除、基于特征的匹配）、数据验证、SQLite 数据库生成、Excel 导出、自动 error_report.md 生成。基于 vehicle-ripple-data 架构，但专门针对斜率数据（具有不同的统计列）。
version: "1.2"
---

# 车辆电压斜率测试数据整合与报告生成

通过整合 Excel 统计数据、应用工况映射规则，为下游分析准备统一数据，构建 SQLite 数据库，并生成标准格式的 Excel 报告。

## 概述

本技能处理来自**车辆斜率文件夹**的测试数据：

**文件夹命名规范：**
- **标准格式**：`{VehicleID}_SLOPE`（例如：`V0001_SLOPE`、`V0002_SLOPE`）
  - `VehicleID`：车辆标识符（例如：V0001、V0002）
  - `SLOPE`：固定后缀，表示该文件夹包含电压斜率测试数据
- **兼容格式**：`{VehicleID}`（例如：`V0001`）- 为向后兼容而保留

**车辆 ID 提取逻辑：**
```python
def extract_vehicle_id(folder_name):
    """从文件夹名称提取车辆 ID"""
    # 处理 {VehicleID}_SLOPE 格式
    if folder_name.endswith('_SLOPE'):
        return folder_name[:-6]  # 去掉 '_SLOPE' 后缀
    # 处理兼容格式 {VehicleID}
    return folder_name
```

**示例：**
| 文件夹名称 | 提取的车辆 ID |
|:-----------|:--------------|
| V0001_SLOPE | V0001 |
| V0002_SLOPE | V0002 |
| V1234_SLOPE | V1234 |
| V0001（兼容格式） | V0001 |

**支持的文件夹结构：**

本技能现在支持两种输入模式：

1. **直接输入 SLOPE 文件夹**（推荐）：直接输入 `V0001_SLOPE`
2. **输入父文件夹并自动检测**：输入父文件夹 `V0001`，技能自动查找 `V0001_SLOPE` 子文件夹

```
E:\Vehicle_Date\V0001\           # 父文件夹（用户输入）
├── vehicle_info.md              # 车辆信息（从父文件夹读取）
├── V0001_SLOPE\                 # 自动检测到的 SLOPE 子文件夹
│   ├── FM_A/
│   ├── FM_V/
│   └── ...
└── V0001_SLOPE\V0001_SLOPE_output\  # 输出文件生成于此
```

**自动检测逻辑：**
- 如果输入文件夹名称以 `_SLOPE` 结尾 → 直接使用
- 否则 → 搜索以 `_SLOPE` 结尾的子文件夹
- 如果未找到 → 将输入文件夹视为车辆文件夹（兼容模式）

## ⚠️ 关键注意事项

### 注意 1：斜率数据的统计 Excel 格式

**关键**：斜率数据使用**不同于**纹波数据的统计格式：

**斜率统计 Excel 格式**（4 列）：
| 列 | 说明 |
|:---|:-----|
| 文件名 | 文件名/工况标识符 |
| 斜率最大值(V/s) | 斜率最大值（伏特/秒） |
| 斜率最小值(V/s) | 斜率最小值（伏特/秒） |
| 斜率绝对值最大值(V/s) | 斜率绝对值最大值（伏特/秒） |

**示例数据：**
| 文件名 | 斜率最大值(V/s) | 斜率最小值(V/s) | 斜率绝对值最大值(V/s) |
|:-------|:---------------|:---------------|:---------------------|
| 87_超车80-140 | 1250.5 | -980.3 | 1250.5 |
| 20_直流充电暖风 | 450.2 | -320.1 | 450.2 |

**与纹波数据的关键区别：**
- **图片文件是可选但受支持的**
  - 如果只有 `statistics.xlsx`，处理仍可正常继续
  - 如果存在 `.png`/`.jpg` 图片，将自动扫描并匹配到对应工况
  - 图片命名格式：`{condition_id}_{component_code}.png`
  - 示例：`87_超车80-140_FM_V.png`
- 不同的列名和数据结构
- 不同的数据含义（斜率 vs 纹波）
- 单位为 V/s（伏特/秒），而非 V 或 A

### 注意 2：命名规则合并策略

**新方法**：始终将车辆文件夹规则与默认规则合并
- **步骤 1**：先从技能参考文件夹加载完整的默认规则
- **步骤 2**：检查车辆文件夹中是否有自定义规则 - 如果有，则合并（车辆规则优先）
- **结果**：保证规则覆盖的完整性

### 注意 3：验证所有组件文件夹
**不要只检查一个文件夹就停止。**
- 扫描车辆文件夹并找到所有子目录
- 将每个文件夹与 sensor_naming_rules 进行验证
- 一次性报告所有无效文件夹，而不是只报告第一个

### 注意 4：中文编码处理至关重要
**所有输入文件都包含中文字符，必须使用正确的编码读取。**

- **关键**：所有文件（vehicle_info、test_naming_rules、sensor_naming_rules、statistics.xlsx）都包含中文文本
- **必须**使用 UTF-8 编码读取（如果 UTF-8 失败则回退到 GBK）
- **切勿**假设 ASCII 编码

### 注意 5：从工况 ID 提取 SOC 值

工况 ID 格式为：`{SOC值}_{工况描述}`

示例：
- `87_超车80-140(运动模式)` → SOC = 87%（高电量）
- `26_超车80-140（运动模式）` → SOC = 26%（低电量）

**正确的提取逻辑：**

```python
def extract_soc_from_condition_id(condition_id):
    """从 condition_id 提取 SOC 值"""
    # 提取第一个数值
    match = re.match(r'(\d+)_.*', condition_id)
    if match:
        return int(match.group(1))
    return None

def get_soc_level(soc_value):
    """将 SOC 值映射到 SOC 等级"""
    if soc_value is None:
        return "未知"
    elif soc_value >= 70:
        return "≥70%"
    elif soc_value >= 40:
        return "40%-70%"
    else:
        return "≤40%"

# 用法：
soc_value = extract_soc_from_condition_id(condition_id)
soc_level = get_soc_level(soc_value)
```

**映射规则：**
- SOC ≥ 70% → "≥70%"
- 40% ≤ SOC < 70% → "40%-70%"
- SOC < 40% → "≤40%"

### 注意 6：工况名称映射（智能模糊匹配）
**工况名称通过 test_naming_rules.md 使用多级模糊匹配来查找。**

**匹配策略（按优先级）：**

1. **精确匹配**：直接字典查找
2. **规范化匹配**：去除括号变体 `()` `（）`
3. **模糊匹配**：编辑距离（Levenshtein）处理拼写错误和微小差异
4. **特征匹配**：提取关键词、SOC 等级、坡度标记以处理 GBK 编码乱码问题

**示例：**

| 输入工况 ID | 匹配类型 | 匹配到的规则 | 工况名称 |
|:------------|:---------|:-------------|:---------|
| `87_超车80-140(运动模式)` | 精确 | 相同 | 超越加速 |
| `87_超车80-140（运动模式）` | 规范化 | `87_超车80-140(运动模式)` | 超越加速 |
| `87_超车80-140运动模式` | 模糊 (0.95) | `87_超车80-140(运动模式)` | 超越加速 |
| `�¶�10_81_匀速80暖风` | 特征 | `坡度10_81_匀速80暖风（运动模式）` | 爬坡高温 |
| `88_超车80-140(运动模式)` | 特征 | `87_超车80-140(运动模式)` | 超越加速 |

**实现：**

```python
from scripts.condition_matcher import ConditionMatcher, get_condition_name

# 方法 1：使用 ConditionMatcher 类
matcher = ConditionMatcher(test_rules)
result = matcher.match(condition_id)

if result:
    condition_name = result.condition_name
    match_type = result.match_type      # 'exact', 'normalized', 'fuzzy', 'feature'
    confidence = result.confidence      # 0.0 - 1.0

# 方法 2：使用便捷函数（向后兼容）
condition_name = get_condition_name(condition_id, test_rules)
```

**调试：**

```python
# 获取详细的匹配信息
details = matcher.get_match_details(condition_id)
print(f"输入: {details['input']}")
print(f"精确匹配: {details['exact_match']}")
print(f"规范化匹配: {details['normalized_match']}")
print(f"前 3 个模糊匹配: {details['fuzzy_matches'][:3]}")
print(f"特征匹配: {details['feature_match']}")
```

## 输入数据结构

### 1. 车辆文件夹结构

```
V0001_SLOPE/                    # 车辆文件夹（推荐：{VehicleID}_SLOPE 格式）
├── vehicle_info.md             # 或 vehicle_info.xlsx（必需）
├── test_naming_rules.md        # 或 test_naming_rules.xlsx（可选，缺失时使用默认规则）
├── sensor_naming_rules.md      # 或 sensor_naming_rules.xlsx（可选，缺失时使用默认规则）
├── FM_A/                       # 组件文件夹（必须与 sensor_naming_rules 匹配）
│   └── statistics.xlsx         # 斜率统计数据（4 列格式）
│   └── *.png（可选）           # 斜率图像文件
├── FM_V/
│   └── statistics.xlsx
├── RM_A/
├── RM_V/
├── DCC_A/
├── DCC_V/
├── ACC_A/
├── ACC_V/
├── PTC_A/
├── PTC_V/
├── ACCM_A/
├── ACCM_V/
├── LV_A/
├── LV_V/
├── FAN_A/
├── BATT_A/
├── BATT_V/
└── ...
```

**兼容格式（仍然支持）：**
```
V0001/                          # 不带 _SLOPE 后缀的兼容格式
├── vehicle_info.md
├── ...
└── V0001_SLOPE_output/         # 输出文件夹（自动生成）
```

### 2. 车辆信息（vehicle_info.md 或 vehicle_info.xlsx）

**必需字段**（27 个参数）：
- `车辆ID`（主键）
- `车型`, `车长mm`, `车宽mm`, `车高mm`
- `轴距(mm)`, `前轮距(mm)`, `后轮距(mm)`, `最小离地间隙(mm)`
- `混合动力系统`, `驱动形式`
- `前电机最大功率(kW)`, `后电机最大功率(kW)`
- `前电机最大扭矩(N·m)`, `后电机最大扭矩(N·m)`
- `系统综合功率(kW)`, `高压架构`
- `动力电池类型`, `动力电池总电量(kWh)`, `快充功率(kW)`
- `前悬类型`, `后悬类型`
- `发动机型号`, `变速箱类型`, `排量(L)`
- `发动机最大净功率(kW/rpm)`, `发动机最大净扭矩(N·m/rpm)`
- `指导价格（万元）`

**Markdown 格式**（vehicle_info.md）：
```markdown
| 车辆ID | 车型 | 车长mm | ... |
|:-------|:-----|-------:|:----|
| V0001  | 坦克500 Hi4-Z | 5078 | ... |
```

### 3. 测试命名规则（test_naming_rules.md 或 test_naming_rules.xlsx）

将测试工况名称映射到 3 个 SOC 等级的数据标识符。

**Markdown 格式**（test_naming_rules.md）：
```markdown
| 电量状态 | 工况名称 | 数据命名举例 |
|:---------|:---------|:-------------|
| ≥70%     | 超越加速 | 87_超车80-140(运动模式) |
| ≥70%     | 紧急制动 | 88_急减速120-0(运动模式) |
| ...      | ...      | ...          |
| 40%-70%  | 超越加速 | 64_超车80-140(运动模式) |
| ≤40%     | 超越加速 | 26_超车80-140（运动模式） |
```

**列说明**：
- `电量状态`：SOC 等级（≥70%、40%-70%、≤40%）
- `工况名称`：可读的工况名称
- `数据命名举例`：文件名和统计文件中使用的数据标识符

### 4. 传感器命名规则（sensor_naming_rules.md 或 sensor_naming_rules.xlsx）

定义组件通道及其描述。

**Markdown 格式**（sensor_naming_rules.md）：
```markdown
FM_V: 前电驱系统直流母线端电压(V)
FM_A: 前电驱系统直流母线端电流(A)
RM_V: 后电驱系统直流母线端电压(V)
RM_A: 后电驱系统直流母线端电流(A)
DCC_V: 动力电池直流充电端电压(V)
DCC_A: 动力电池直流充电端电流(A)
ACC_V: OBC输出端电压(V)
ACC_A: OBC输出端电流(A)
PTC_V: PTC输入端电压(V)
PTC_A: PTC输入端电流(A)
ACCM_V: 压缩机输入端电压(V)
ACCM_A: 压缩机输入端电流(A)
LV_V: 12V电池及前端冷却模块风扇的低压电压(V)
LV_A: 12V电池及前端冷却模块风扇的低压电流(A)
FAN_A: 前端冷却模块风扇的低压电流(A)
BATT_V: 动力电池电压(V)
BATT_A: 动力电池电流(A)
```

**验证**：组件文件夹名称必须与通道代码完全匹配。

### 5. 组件文件夹内容（斜率数据）

每个组件文件夹必须包含：
- `statistics.xlsx`：所有工况的斜率测试指标（4 列格式）
- **图片文件是可选的**（`.png` 或 `.jpg`）。如果存在，将被扫描并匹配：
  - 命名格式：`{condition_id}_{component_code}.png`
  - 匹配到的图片路径会存储在 `image_path` 字段中，并包含在 Excel 输出里

**斜率统计 Excel 格式：**
| 列 | 说明 |
|:---|:-----|
| 文件名 | 工况标识符（例如："87_超车80-140"） |
| 斜率最大值(V/s) | 斜率最大值（V/s） |
| 斜率最小值(V/s) | 斜率最小值（V/s） |
| 斜率绝对值最大值(V/s) | 斜率绝对值最大值（V/s） |

**示例：**
| 文件名 | 斜率最大值(V/s) | 斜率最小值(V/s) | 斜率绝对值最大值(V/s) |
|:-------|---------------:|---------------:|---------------------:|
| 87_超车80-140 | 1250.5 | -980.3 | 1250.5 |
| 20_直流充电暖风 | 450.2 | -320.1 | 450.2 |
| 坡度10_32_匀速80冷风 | 380.7 | -290.5 | 380.7 |

## 处理逻辑

### 步骤 1：验证车辆文件夹并提取车辆 ID

1. **从文件夹名称提取车辆 ID：**
   - 如果文件夹名称以 `_SLOPE` 结尾 → vehicle_id = 去掉 `_SLOPE` 后缀后的名称
   - 否则 → vehicle_id = 文件夹名称（兼容格式）
   - 示例：`V0001_SLOPE` → vehicle_id = `V0001`

2. **验证文件夹存在且包含必需文件：**
   - 检查指定的车辆文件夹是否存在
   - 验证其中至少包含：`vehicle_info.md` 或 `vehicle_info.xlsx`

### 步骤 2：使用中文编码加载命名规则

**关键：所有命名规则文件都包含中文文本，必须使用正确的编码（UTF-8 或 GBK）读取。**

**新的规则加载策略：先加载默认规则，然后与车辆文件夹规则合并。**

1. **测试命名规则** - **合并策略**：
   - **步骤 1**：始终先从技能参考文件夹加载默认规则
   - **步骤 2**：检查车辆文件夹是否有自定义规则
     - 如果有 → 将车辆规则与默认规则合并（车辆规则优先）
     - 如果没有 → 直接使用默认规则
   - 构建查找表：`{condition_id}` → `{soc_level, condition_name}`

2. **传感器命名规则** - **合并策略**：
   - **步骤 1**：始终先从技能参考文件夹加载默认规则
   - **步骤 2**：检查车辆文件夹是否有自定义规则
     - 如果有 → 将车辆规则与默认规则合并
     - 如果没有 → 直接使用默认规则
   - 构建查找表：`{channel_code}` → `{component_name, unit}`

### 步骤 3：使用中文编码加载车辆信息

读取车辆信息文件（如果两者都存在，优先使用 .md）：
- **关键**：先用 UTF-8 编码读取，如果 UTF-8 失败则回退到 GBK
- 解析 Markdown 表格或读取 Excel
- 提取 vehicle_id 和所有 27 个参数
- **保留所有字段中的中文字符**

### 步骤 4：发现并验证组件

1. **扫描车辆文件夹**查找所有子目录
2. **识别所有组件文件夹**：
   - 找到每个可能是组件文件夹的目录（排除 .md 文件等文档）
   - **必须**检查车辆目录中的所有文件夹
3. **验证每个文件夹**：
   - 对于找到的每个文件夹，检查其名称是否与 sensor_naming_rules 中的通道代码匹配
   - **关键**：如果有任何文件夹名称与传感器代码不匹配 → 报错并停止
4. **验证最少组件数**：
   - 如果没有找到有效的组件文件夹 → 报错并停止

### 步骤 5：处理每个组件

对于每个有效的组件文件夹：

1. **加载统计数据**
   - 读取 `statistics.xlsx`
   - **关键**：验证列名是否符合斜率格式：
     - 预期：文件名, 斜率最大值(V/s), 斜率最小值(V/s), 斜率绝对值最大值(V/s)
     - 如果列数不等于 4 或列名不匹配 → 报错
   - 提取所有工况行

2. **扫描图片文件**
   - 列出所有 `.png` 和 `.jpg` 文件
   - 解析文件名以提取工况 ID
   - 将图片路径与工况匹配

3. **验证数据类型**
   - 确保斜率值为数值
   - 优雅地处理缺失值（设为 null）

4. **构建组件数据**
   - **从 condition_id 提取 SOC 值**：
     - 解析 condition_id 格式：`{SOC值}_{工况描述}`
     - 提取第一个数值作为 SOC 百分比
   - **映射 SOC 到 SOC 等级**：
     - SOC ≥ 70% → "≥70%"
     - 40% ≤ SOC < 70% → "40%-70%"
     - SOC < 40% → "≤40%"
   - **从 test_naming_rules 查找获取工况名称**
   - 存储斜率统计和图片路径

### 步骤 6：输出结构化数据

生成分层 JSON：

```json
{
  "vehicle": {
    "vehicle_id": "V0001",
    "vehicle_info": {
      "车型": "坦克500 Hi4-Z",
      "车长mm": 5078,
      ...
    }
  },
  "components": {
    "FM_A": {
      "component_name": "前电驱系统直流母线端电流",
      "channel_code": "FM_A",
      "unit": "A",
      "statistics_file": "V0001_SLOPE/FM_A/statistics.xlsx",
      "conditions_count": 48,
      "conditions": {
        "87_超车80-140": {
          "condition_name": "超越加速",
          "soc_level": "≥70%",
          "slope": {
            "max_value": 1250.5,
            "min_value": -980.3,
            "max_abs_value": 1250.5,
            "unit": "V/s"
          },
          "image_path": "E:/.../87_超车80-140_FM_A.png"
        }
      }
    }
  },
  "metadata": {
    "processing_date": "2025-03-21",
    "total_components": 16,
    "total_conditions": 768,
    "data_type": "slope",
    "test_naming_rules_source": "merged",
    "sensor_naming_rules_source": "merged"
  }
}
```

## 输出选项

### 选项 1：JSON 输出

返回结构化的 JSON 对象，供程序使用。

### 选项 2：SQLite 数据库

创建/追加到 SQLite 数据库，Schema 如下：

```sql
-- vehicles 表（与纹波数据相同）
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY,
  vehicle_model TEXT,
  length_mm REAL, width_mm REAL, height_mm REAL,
  wheelbase_mm REAL, front_track_mm REAL, rear_track_mm REAL,
  min_ground_clearance_mm REAL,
  hybrid_system TEXT, drive_type TEXT,
  front_motor_max_power_kw REAL, rear_motor_max_power_kw REAL,
  front_motor_max_torque_nm REAL, rear_motor_max_torque_nm REAL,
  system_total_power_kw REAL, high_voltage_architecture TEXT,
  battery_type TEXT, battery_capacity_kwh REAL, fast_charge_power_kw REAL,
  front_suspension TEXT, rear_suspension TEXT,
  engine_model TEXT, transmission_type TEXT, displacement_l REAL,
  engine_max_power_kw REAL, engine_max_torque_nm REAL,
  price_ten_thousand_yuan REAL
);

-- components 表（与纹波数据相同）
CREATE TABLE components (
  component_code TEXT PRIMARY KEY,
  component_name TEXT,
  unit TEXT
);

-- conditions 表（与纹波数据相同）
CREATE TABLE conditions (
  condition_id TEXT PRIMARY KEY,
  condition_name TEXT,
  soc_level TEXT
);

-- slope_results 表（与纹波数据**不同**）
CREATE TABLE slope_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vehicle_id TEXT,
  component_code TEXT,
  condition_id TEXT,
  slope_max REAL,              -- 斜率最大值(V/s)
  slope_min REAL,              -- 斜率最小值(V/s)
  slope_max_abs REAL,          -- 斜率绝对值最大值(V/s)
  unit TEXT DEFAULT 'V/s',
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
  FOREIGN KEY (component_code) REFERENCES components(component_code),
  FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
);
```

### 选项 3：Excel 报告

生成包含多个工作表的 Excel 汇总报告：

**工作表 1：车辆信息**
- 所有车辆参数采用纵向格式，两列：
  - **参数**：参数名称（例如：车型, 车长mm）
  - **值**：参数值
- 格式与 vehicle-ripple-data 技能保持一致

**示例：**
| 参数 | 值 |
|:----------|:------|
| 车型 | 坦克500 Hi4-Z |
| 车长mm | 5078 |
| 车宽mm | 1860 |
| ... | ... |

**工作表 2：组件摘要**
- 组件代码
- 组件名称
- 单位（A 或 V）
- 工况数
- 最大斜率值
- 最小斜率值

**工作表 3：详细结果**
- 所有测试工况，共 10 列：
  1. **No.** - 从 1 开始的序号
  2. **Component** - 组件代码
  3. **Unit** - 测量单位（A 或 V）
  4. **Condition ID** - 测试工况标识符
  5. **Condition Name** - 测试工况名称
  6. **SOC Level** - 电池 SOC 等级
  7. **Slope Max (V/s)** - 斜率最大值
  8. **Slope Min (V/s)** - 斜率最小值
  9. **Slope Max Abs (V/s)** - 斜率绝对值最大值
  10. **Image Path** - 图片路径（如果存在）

**Excel 生成代码示例：**
```python
# 工作表 3：详细结果
results_data = []
seq_num = 1
for comp_code, comp_data in data['components'].items():
    unit = comp_data['unit']
    for cond_id, cond_data in comp_data['conditions'].items():
        results_data.append({
            'No.': seq_num,
            'Component': comp_code,
            'Unit': unit,
            'Condition ID': cond_id,
            'Condition Name': cond_data['condition_name'],
            'SOC Level': cond_data['soc_level'],
            'Slope Max (V/s)': cond_data['slope']['max_value'],
            'Slope Min (V/s)': cond_data['slope']['min_value'],
            'Slope Max Abs (V/s)': cond_data['slope']['max_abs_value'],
            'Image Path': cond_data.get('image_path', '')
        })
        seq_num += 1
results_df = pd.DataFrame(results_data)
results_df.to_excel(writer, sheet_name='Detailed Results', index=False)
```

## 错误处理

### 致命错误（停止处理）：
- 车辆文件夹不存在
- 缺少 vehicle_info 文件（.md 或 .xlsx）
- 组件文件夹名称与 sensor_naming_rules 中的任何传感器代码都不匹配
- 组件文件夹中缺少 statistics.xlsx
- statistics.xlsx 列格式错误（不是 4 列或列名不正确）
- Excel 中的数据类型无效（预期为数值但实际不是）

### 警告（记录并继续）：
- 缺少可选的车辆参数字段
- 组件文件夹缺失（如果其他文件夹存在）
- 使用默认命名规则（不是错误，但应记录）
- statistics 中缺少数据行（将使用 null 值）

## 错误报告生成（error_report.md）

处理车辆数据后，技能会自动在 `{VehicleID}_SLOPE_output` 文件夹中生成 `error_report.md` 文件。

**报告结构（中文）：**
```markdown
# 车辆电压斜率数据处理报告

**生成时间**: 2025-03-21 14:30:00
**版本**: 1.0

## 处理摘要
- **车辆ID**: V0001
- **车辆型号**: 坦克500 Hi4-Z
- **处理状态**: ✓ 成功完成
- **组件总数**: 10
- **成功处理**: 10

## 已完成的功能
✓ 车辆信息已加载 - 27个参数
✓ 测试命名规则已加载 - 42个工况
✓ 组件文件夹已验证 - 10个文件夹
✓ 统计数据已处理 - 390个工况

## 生成的文件
| 文件名 | 类型 | 说明 |
|--------|------|------|
| V0001_SLOPE_summary.xlsx | Excel | V1.0格式报告，包含3个工作表 |
| V0001_SLOPE.db | SQLite | 数据库，包含4个表 |
| V0001_SLOPE_data.json | JSON | 结构化数据导出 |

## 错误和警告
### ⚠️ 警告（处理已继续）
_None_

## 处理统计
| 指标 | 值 |
|------|----|
| 总组件数 | 10 |
| 成功处理 | 10 |
| 总工况数 | 390 |
| 数据质量 | 良好 |
```

### 输出文件夹组织

所有生成的文件都组织到 `{VehicleID}_SLOPE_output` 子文件夹中：

```
V0001_SLOPE/                    # 车辆文件夹（仅输入文件）
├── vehicle_info.md             # 输入：车辆参数
├── test_naming_rules.md        # 输入：测试命名规则
├── sensor_naming_rules.md      # 输入：传感器命名规则
├── FM_A/                       # 输入：组件数据
│   ├── statistics.xlsx
│   └── *.png（可选）
├── ...
└── V0001_SLOPE_output/         # 所有输出文件组织于此
    ├── V0001_SLOPE_summary.xlsx      # Excel 报告（以 vehicle_id_SLOPE 命名）
    ├── V0001_SLOPE.db                # SQLite 数据库
    ├── V0001_SLOPE_data.json         # JSON 数据
    └── error_report.md               # 处理报告（中文）
```

## 使用方式

### 命令行 - 单辆车处理

```bash
# 处理单辆车（推荐：{VehicleID}_SLOPE 格式）
python scripts/cli/process_slope.py process --folder V0001_SLOPE

# 先验证再处理
python scripts/cli/process_slope.py process --folder V0001_SLOPE --validate-first

# 仅生成特定格式
python scripts/cli/process_slope.py process --folder V0001_SLOPE --format json,excel

# 兼容格式也支持
python scripts/cli/process_slope.py process --folder V0001
```

### 命令行 - 批量处理（多辆车）

```bash
# 批量处理，显式指定文件夹列表
python scripts/cli/process_slope.py batch V0001_SLOPE V0002_SLOPE V0003_SLOPE

# 批量处理，自动扫描（在父目录下发现所有 SLOPE 文件夹）
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date

# 批量处理，带验证和进度条
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --validate-first --progress

# 批量处理，指定输出格式
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --format excel
```

**自动扫描行为：**
- 扫描指定的父文件夹中的子目录
- 自动检测以 `_SLOPE` 结尾的文件夹
- 也检测包含 `{VehicleID}_SLOPE` 子文件夹的父文件夹
- 打印所有已处理车辆的汇总表

### Python API

```python
from scripts.slope_processor import SlopeDataProcessor

# 初始化处理器
processor = SlopeDataProcessor("V0001_SLOPE")

# 处理数据
result = processor.process()

# 生成输出
processor.generate_json("V0001_SLOPE_data.json")
processor.generate_excel("V0001_SLOPE_summary.xlsx")
processor.generate_sqlite("V0001_SLOPE.db")
```

## 与 vehicle-ripple-data 的关键区别

| 特性 | vehicle-ripple-data | vehicle-slope-data |
|:-----|:--------------------|:-------------------|
| **文件夹后缀** | `_RIPPLE` | `_SLOPE` |
| **统计列数** | 7 列（VPP、频率等） | 4 列（斜率最大/最小/绝对值） |
| **图片文件** | 必需（每个工况一张 .png） | 可选（如果存在则扫描） |
| **数据单位** | V（伏特）或 A（安培） | V/s（伏特/秒） |
| **数据库表** | test_results | slope_results |
| **Excel 列** | 时域 VPP、频域峰值等 | 斜率最大/最小/绝对值 |

## 版本历史

### V1.2（当前）
- 修正图片文件说明：斜率技能确实会扫描图片（如果存在）
- 图片路径存储在 JSON/Excel/SQLite 输出中
- 与报告生成技能兼容

### V1.0（2025-03-21）
- 初始版本
- 支持 {VehicleID}_SLOPE 文件夹命名
- 4 列斜率统计格式
- JSON、Excel、SQLite 输出格式
- 中文错误报告
- 基于 vehicle-ripple-data V4.1 架构
