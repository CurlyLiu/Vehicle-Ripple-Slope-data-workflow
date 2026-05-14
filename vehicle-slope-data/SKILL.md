---
name: vehicle-slope-data
description: Integrate and structure vehicle voltage slope test data for downstream analysis and report generation. Use this skill when processing voltage slope statistics from vehicle component folders (FM, RM, DCC, ACC, PTC, ACCM, LV, FAN, BATT, etc.) with {VehicleID}_SLOPE naming convention. This skill prepares structured data for database construction, generates Excel summary reports with standardized format (Vehicle Information in vertical Parameter|Value layout), creates comprehensive error reports in Chinese language, and organizes all outputs in {VehicleID}_SLOPE_output folder. Handles component-channel mapping, condition matching with same logic as vehicle-ripple-data (exact match, bracket removal, feature-based), data validation, SQLite database generation, Excel export, automatic error_report.md generation. Based on vehicle-ripple-data architecture but specialized for slope data with different statistics columns.
version: "1.3"
---

# Vehicle Voltage Slope Test Data Integration & Report Generation

Integrate and structure vehicle voltage slope test data by consolidating Excel statistics, applying condition mapping rules, preparing unified data for downstream analysis, SQLite database construction, and Excel report generation with standardized format.

## Overview

This skill processes test data from a **vehicle slope folder** containing:

**Folder Naming Convention:**
- **Standard format**: `{VehicleID}_SLOPE` (e.g., `V0001_SLOPE`, `V0002_SLOPE`)
  - `VehicleID`: Vehicle identifier (e.g., V0001, V0002)
  - `SLOPE`: Fixed suffix indicating this folder contains voltage slope test data
- **Legacy format**: `{VehicleID}` (e.g., `V0001`) - still supported for backward compatibility

**Vehicle ID Extraction Logic:**
```python
def extract_vehicle_id(folder_name):
    """Extract vehicle ID from folder name"""
    # Handle {VehicleID}_SLOPE format
    if folder_name.endswith('_SLOPE'):
        return folder_name[:-6]  # Remove '_SLOPE' suffix
    # Handle legacy {VehicleID} format
    return folder_name
```

**Examples:**
| Folder Name | Extracted Vehicle ID |
|:------------|:---------------------|
| V0001_SLOPE | V0001 |
| V0002_SLOPE | V0002 |
| V1234_SLOPE | V1234 |
| V0001 (legacy) | V0001 |

**Folder Structure Support:**

The skill now supports two input modes:

1. **Direct SLOPE folder** (recommended): Input `V0001_SLOPE` directly
2. **Parent folder with auto-detection**: Input parent folder `V0001`, skill automatically finds `V0001_SLOPE` subfolder

```
E:\Vehicle_Date\V0001\           # Parent folder (input this)
├── vehicle_info.md              # Vehicle info (read from parent)
├── V0001_SLOPE\                 # Auto-detected SLOPE subfolder
│   ├── FM_A/
│   ├── FM_V/
│   └── ...
└── V0001_SLOPE\V0001_SLOPE_output\  # Output generated here
```

**Auto-Detection Logic:**
- If input folder name ends with `_SLOPE` → use it directly
- Otherwise → search for subfolder ending with `_SLOPE`
- If not found → treat input folder as vehicle folder (legacy mode)

## ⚠️ CRITICAL NOTES

### Note 1: Statistics Excel Format for Slope Data

**CRITICAL**: Slope data uses a DIFFERENT statistics format than ripple data:

**Slope Statistics Excel Format** (4 columns):
| Column | Description |
|--------|-------------|
| 文件名 | File name/condition identifier |
| 斜率最大值(V/s) | Maximum slope value (Volts per second) |
| 斜率最小值(V/s) | Minimum slope value (Volts per second) |
| 斜率绝对值最大值(V/s) | Maximum absolute slope value (Volts per second) |

**Example data:**
| 文件名 | 斜率最大值(V/s) | 斜率最小值(V/s) | 斜率绝对值最大值(V/s) |
|:-------|:---------------|:---------------|:---------------------|
| 87_超车80-140 | 1250.5 | -980.3 | 1250.5 |
| 20_直流充电暖风 | 450.2 | -320.1 | 450.2 |

**Key Differences from Ripple Data:**
- Image files are OPTIONAL but SUPPORTED
  - If `statistics.xlsx` exists alone, processing continues normally
  - If `.png`/`.jpg` images exist, they are automatically scanned and matched to conditions
  - Image naming format: `{condition_id}_{component_code}.png`
  - Example: `87_超车80-140_FM_V.png`
- Different column names and structure
- Different data interpretation (slope vs ripple)
- Unit is V/s (Volts per second), not V or A

### Note 2: Merge Strategy for Naming Rules

**NEW APPROACH**: Always merge vehicle folder rules with default rules
- **Step 1**: Load complete default rules from skill reference folder
- **Step 2**: Check vehicle folder for custom rules - if found, merge them (vehicle rules take precedence)
- **Result**: Complete rule coverage guaranteed

### Note 3: Validate ALL Component Folders
**Do not stop after checking one folder.**
- Scan the vehicle folder and find ALL subdirectories
- Validate EACH folder against sensor_naming_rules
- Report ALL invalid folders at once, not just the first one

### Note 4: Chinese Encoding Handling is CRITICAL
**All input files contain Chinese characters and must be read with proper encoding.**

- **CRITICAL**: All files (vehicle_info, test_naming_rules, sensor_naming_rules, statistics.xlsx) contain Chinese text
- **MUST** read files with UTF-8 encoding (try UTF-8 first, fallback to GBK if needed)
- **NEVER** assume ASCII encoding

### Note 5: SOC Value Extraction from Condition ID

The condition ID format is: `{SOC值}_{工况描述}`

Examples:
- `87_超车80-140(运动模式)` → SOC = 87% (high SOC)
- `26_超车80-140（运动模式）` → SOC = 26% (low SOC)

**CORRECT Extraction Logic:**

```python
def extract_soc_from_condition_id(condition_id):
    """Extract SOC value from condition_id"""
    # Extract first numeric value
    match = re.match(r'(\d+)_.*', condition_id)
    if match:
        return int(match.group(1))
    return None

def get_soc_level(soc_value):
    """Map SOC value to SOC level"""
    if soc_value is None:
        return "Unknown"
    elif soc_value >= 70:
        return "≥70%"
    elif soc_value >= 40:
        return "40%-70%"
    else:
        return "≤40%"

# Usage:
soc_value = extract_soc_from_condition_id(condition_id)
soc_level = get_soc_level(soc_value)
```

**Mapping Rules:**
- SOC ≥ 70% → "≥70%"
- 40% ≤ SOC < 70% → "40%-70%"
- SOC < 40% → "≤40%"

### Note 6: Condition Name Mapping (Intelligent Fuzzy Matching)
**Condition name is looked up from test_naming_rules.md using multi-level fuzzy matching.**

**Matching Strategy (Priority Order):**

1. **Exact Match**: Direct dictionary lookup
2. **Normalized Match**: Removes bracket variations `()` `（）`
3. **Fuzzy Match**: Edit distance (Levenshtein) for typos and minor variations
4. **Feature Match**: Extracts keywords, SOC level, slope flag to handle GBK encoding issues

**Examples:**

| Input Condition ID | Match Type | Matched Rule | Condition Name |
|:-------------------|:-----------|:-------------|:---------------|
| `87_超车80-140(运动模式)` | Exact | Same | 超越加速 |
| `87_超车80-140（运动模式）` | Normalized | `87_超车80-140(运动模式)` | 超越加速 |
| `87_超车80-140运动模式` | Fuzzy (0.95) | `87_超车80-140(运动模式)` | 超越加速 |
| `�¶�10_81_匀速80暖风` | Feature | `坡度10_81_匀速80暖风（运动模式）` | 爬坡高温 |
| `88_超车80-140(运动模式)` | Feature | `87_超车80-140(运动模式)` | 超越加速 |

**Implementation:**

```python
from scripts.condition_matcher import ConditionMatcher, get_condition_name

# Method 1: Using ConditionMatcher class
matcher = ConditionMatcher(test_rules)
result = matcher.match(condition_id)

if result:
    condition_name = result.condition_name
    match_type = result.match_type      # 'exact', 'normalized', 'fuzzy', 'feature'
    confidence = result.confidence      # 0.0 - 1.0

# Method 2: Using convenience function (backward compatible)
condition_name = get_condition_name(condition_id, test_rules)
```

**Debugging:**

```python
# Get detailed matching information
details = matcher.get_match_details(condition_id)
print(f"Input: {details['input']}")
print(f"Exact match: {details['exact_match']}")
print(f"Normalized match: {details['normalized_match']}")
print(f"Top fuzzy matches: {details['fuzzy_matches'][:3]}")
print(f"Feature match: {details['feature_match']}")
```

## Input Data Structure

### 1. Vehicle Folder Structure

```
V0001_SLOPE/                    # Vehicle folder (recommended: {VehicleID}_SLOPE format)
├── vehicle_info.md             # or vehicle_info.xlsx (required)
├── test_naming_rules.md        # or test_naming_rules.xlsx (optional, uses default if missing)
├── sensor_naming_rules.md      # or sensor_naming_rules.xlsx (optional, uses default if missing)
├── FM_A/                       # Component folder (must match sensor_naming_rules)
│   └── statistics.xlsx         # Slope statistics (4 columns format)
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

**Legacy format (still supported):**
```
V0001/                          # Legacy format without _SLOPE suffix
├── vehicle_info.md
├── ...
└── V0001_SLOPE_output/         # Output folder (auto-generated)
```

### 2. Vehicle Information (vehicle_info.md or vehicle_info.xlsx)

**Required fields** (27 parameters):
- `车辆ID` (primary key)
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

**Markdown format** (vehicle_info.md):
```markdown
| 车辆ID | 车型 | 车长mm | ... |
|:-------|:-----|-------:|:----|
| V0001  | 坦克500 Hi4-Z | 5078 | ... |
```

### 3. Test Naming Rules (test_naming_rules.md or test_naming_rules.xlsx)

Maps test condition names to data identifiers across 3 SOC levels.

**Markdown format** (test_naming_rules.md):
```markdown
| 电量状态 | 工况名称 | 数据命名举例 |
|:---------|:---------|:-------------|
| ≥70%     | 超越加速 | 87_超车80-140(运动模式) |
| ≥70%     | 紧急制动 | 88_急减速120-0(运动模式) |
| ...      | ...      | ...          |
| 40%-70%  | 超越加速 | 64_超车80-140(运动模式) |
| ≤40%     | 超越加速 | 26_超车80-140（运动模式） |
```

**Columns**:
- `电量状态`: SOC level (≥70%, 40%-70%, ≤40%)
- `工况名称`: Human-readable condition name
- `数据命名举例`: Data identifier used in filenames and statistics

### 4. Sensor Naming Rules (sensor_naming_rules.md or sensor_naming_rules.xlsx)

Defines component channels and their descriptions.

**Markdown format** (sensor_naming_rules.md):
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

**Validation**: Component folder names MUST match channel codes exactly.

### 5. Component Folder Contents (Slope Data)

Each component folder must contain:
- `statistics.xlsx`: Slope test metrics for all conditions (4 columns format)
- **Image files are optional** (`.png` or `.jpg`). If present, they are scanned and matched:
  - Naming: `{condition_id}_{component_code}.png`
  - Matched image paths are stored in `image_path` field and included in Excel output

**Slope Statistics Excel Format**:
| Column | Description |
|--------|-------------|
| 文件名 | Condition identifier (e.g., "87_超车80-140") |
| 斜率最大值(V/s) | Maximum slope value (V/s) |
| 斜率最小值(V/s) | Minimum slope value (V/s) |
| 斜率绝对值最大值(V/s) | Maximum absolute slope value (V/s) |

**Example:**
| 文件名 | 斜率最大值(V/s) | 斜率最小值(V/s) | 斜率绝对值最大值(V/s) |
|:-------|---------------:|---------------:|---------------------:|
| 87_超车80-140 | 1250.5 | -980.3 | 1250.5 |
| 20_直流充电暖风 | 450.2 | -320.1 | 450.2 |
| 坡度10_32_匀速80冷风 | 380.7 | -290.5 | 380.7 |

## Processing Logic

### Step 1: Validate Vehicle Folder and Extract Vehicle ID

1. **Extract Vehicle ID from folder name:**
   - If folder name ends with `_SLOPE` → vehicle_id = folder_name without `_SLOPE` suffix
   - Otherwise → vehicle_id = folder_name (legacy format)
   - Example: `V0001_SLOPE` → vehicle_id = `V0001`

2. **Validate folder exists and contains required files:**
   - Check that the specified vehicle folder exists
   - Verify it contains at least: `vehicle_info.md` OR `vehicle_info.xlsx`

### Step 2: Load Naming Rules with Chinese Encoding

**CRITICAL: All naming rules files contain Chinese text and must be read with proper encoding (UTF-8 or GBK).**

**NEW RULE LOADING STRATEGY: Load default rules first, then merge with vehicle folder rules.**

1. **Test naming rules** - **MERGE STRATEGY**:
   - **STEP 1**: ALWAYS load default rules from skill reference folder first
   - **STEP 2**: Check if vehicle folder has custom rules
     - If YES → Merge vehicle rules with default rules (vehicle rules take precedence)
     - If NO → Use default rules as-is
   - Build lookup: `{condition_id}` → `{soc_level, condition_name}`

2. **Sensor naming rules** - **MERGE STRATEGY**:
   - **STEP 1**: ALWAYS load default rules from skill reference folder first
   - **STEP 2**: Check if vehicle folder has custom rules
     - If YES → Merge vehicle rules with default rules
     - If NO → Use default rules as-is
   - Build lookup: `{channel_code}` → `{component_name, unit}`

### Step 3: Load Vehicle Info with Chinese Encoding

Read vehicle info file (prefer .md if both exist):
- **CRITICAL**: Read with UTF-8 encoding first, fallback to GBK if UTF-8 fails
- Parse markdown table OR read Excel
- Extract vehicle_id and all 27 parameters
- **Preserve Chinese characters** in all fields

### Step 4: Discover and Validate Components

1. **Scan vehicle folder** for ALL subdirectories
2. **Identify ALL component folders**: 
   - Find every folder that could be a component folder (exclude docs like .md files)
   - **MUST** check ALL folders in the vehicle directory
3. **Validate EACH folder**: 
   - For EACH folder found, check if name matches a channel code in sensor_naming_rules
   - **CRITICAL**: If ANY folder name doesn't match a sensor code → ERROR and stop
4. **Verify minimum components**: 
   - If no valid component folders found → ERROR and stop

### Step 5: Process Each Component

For each valid component folder:

1. **Load Statistics**
   - Read `statistics.xlsx`
   - **CRITICAL**: Validate column names match slope format:
     - Expected: 文件名, 斜率最大值(V/s), 斜率最小值(V/s), 斜率绝对值最大值(V/s)
     - If column count != 4 or column names don't match → ERROR
   - Extract all condition rows

2. **Validate Data Types**
   - Ensure slope values are numeric
   - Handle missing values gracefully (set to null)

3. **Build Component Data**
   - **Extract SOC value from condition_id**:
     - Parse condition_id format: `{SOC值}_{工况描述}`
     - Extract first numeric value as SOC percentage
   - **Map SOC to SOC level**:
     - SOC ≥ 70% → "≥70%"
     - 40% ≤ SOC < 70% → "40%-70%"
     - SOC < 40% → "≤40%"
   - **Get condition name** from test_naming_rules lookup
   - Store slope statistics

### Step 6: Output Structured Data

Generate hierarchical JSON:

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
          }
        }
      }
    }
  },
  "metadata": {
    "processing_date": "2025-03-21",
    "total_components": 16,
    "total_conditions": 768,
    "data_type": "slope",
    "test_naming_rules_source": "vehicle_folder",
    "sensor_naming_rules_source": "default"
  }
}
```

## Output Options

### Option 1: JSON Output

Return structured JSON object for programmatic use.

### Option 2: SQLite Database

Create/append to SQLite database with schema:

```sql
-- vehicles table (same as ripple)
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

-- components table (same as ripple)
CREATE TABLE components (
  component_code TEXT PRIMARY KEY,
  component_name TEXT,
  unit TEXT
);

-- conditions table (same as ripple)
CREATE TABLE conditions (
  condition_id TEXT PRIMARY KEY,
  condition_name TEXT,
  soc_level TEXT
);

-- slope_results table (DIFFERENT from ripple)
CREATE TABLE slope_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vehicle_id TEXT,
  component_code TEXT,
  condition_id TEXT,
  slope_max REAL,              -- 斜率最大值(V/s)
  slope_min REAL,              -- 斜率最小值(V/s)
  slope_max_abs REAL,          -- 斜率绝对值最大值(V/s)
  unit TEXT DEFAULT 'V/s',
  image_path TEXT,             -- 图片路径（可选）
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
  FOREIGN KEY (component_code) REFERENCES components(component_code),
  FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
);
```

### Option 3: Excel Report

Generate Excel summary report with multiple sheets:

**Sheet 1: Vehicle Information**
- All vehicle parameters in a vertical format with two columns:
  - **Parameter**: Parameter name (e.g., 车型, 车长mm)
  - **Value**: Parameter value
- Format matches vehicle-ripple-data skill for consistency

**Example:**
| Parameter | Value |
|:----------|:------|
| 车型 | 坦克500 Hi4-Z |
| 车长mm | 5078 |
| 车宽mm | 1860 |
| ... | ... |

**Sheet 2: Component Summary**
- Component Code
- Component Name
- Unit (A or V)
- Conditions Count
- Max Slope Value
- Min Slope Value

**Sheet 3: Detailed Results**
- All test conditions with 9 columns:
  1. **No.** - Sequence number starting from 1
  2. **Component** - Component code
  3. **Unit** - Unit of measurement (A or V)
  4. **Condition ID** - Test condition identifier
  5. **Condition Name** - Test condition name
  6. **SOC Level** - Battery SOC level
  7. **Slope Max (V/s)** - Maximum slope value
  8. **Slope Min (V/s)** - Minimum slope value
  9. **Slope Max Abs (V/s)** - Maximum absolute slope value

**Excel Generation Code Example:**
```python
# Sheet 3: Detailed Results
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
            'Slope Max Abs (V/s)': cond_data['slope']['max_abs_value']
        })
        seq_num += 1
results_df = pd.DataFrame(results_data)
results_df.to_excel(writer, sheet_name='Detailed Results', index=False)
```

## Error Handling

### Fatal Errors (stop processing):
- Vehicle folder does not exist
- Missing vehicle_info file (.md or .xlsx)
- Component folder name doesn't match any sensor code in sensor_naming_rules
- Missing statistics.xlsx in component folder
- Statistics.xlsx has wrong column format (not 4 columns with correct names)
- Invalid data types in Excel (non-numeric where number expected)

### Warnings (log and continue):
- Missing optional vehicle info fields
- Component folder missing (if other folders exist)
- Using default naming rules (not an error, but should be noted)
- Missing data rows in statistics (null values will be used)

## Error Report Generation (error_report.md)

After processing vehicle data, the skill automatically generates an `error_report.md` file in the `{VehicleID}_SLOPE_output` folder.

**Report Structure (Chinese):**
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

### Output Folder Organization

All generated files are organized into a `{VehicleID}_SLOPE_output` subfolder:

```
V0001_SLOPE/                    # Vehicle folder (input files only)
├── vehicle_info.md             # Input: Vehicle parameters
├── test_naming_rules.md        # Input: Test naming rules
├── sensor_naming_rules.md      # Input: Sensor naming rules
├── FM_A/                       # Input: Component data
├── ...
└── V0001_SLOPE_output/         # All outputs organized here
    ├── V0001_SLOPE_summary.xlsx      # Excel report (named with vehicle_id_SLOPE)
    ├── V0001_SLOPE.db                # SQLite database
    ├── V0001_SLOPE_data.json         # JSON data
    └── error_report.md               # Processing report (Chinese)
```

## Usage

### Command Line - Single Vehicle

```bash
# Process single vehicle (recommended: {VehicleID}_SLOPE format)
python scripts/cli/process_slope.py process --folder V0001_SLOPE

# With validation first
python scripts/cli/process_slope.py process --folder V0001_SLOPE --validate-first

# Only generate specific formats
python scripts/cli/process_slope.py process --folder V0001_SLOPE --format json,excel

# Legacy format also supported
python scripts/cli/process_slope.py process --folder V0001
```

### Command Line - Batch Processing (Multiple Vehicles)

```bash
# Batch with explicit folder list
python scripts/cli/process_slope.py batch V0001_SLOPE V0002_SLOPE V0003_SLOPE

# Batch with auto-scan (discover all SLOPE folders under parent directory)
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date

# Batch with validation and progress bar
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --validate-first --progress

# Batch with specific output format
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --format excel
```

**Auto-scan behavior:**
- Scans the specified parent folder for subdirectories
- Auto-detects folders ending with `_SLOPE`
- Also detects parent folders containing `{VehicleID}_SLOPE` subfolders
- Prints a summary table with all vehicles processed

### Python API

```python
from scripts.slope_processor import SlopeDataProcessor

# Initialize processor
processor = SlopeDataProcessor("V0001_SLOPE")

# Process data
result = processor.process()

# Generate outputs
processor.generate_json("V0001_SLOPE_data.json")
processor.generate_excel("V0001_SLOPE_summary.xlsx")
processor.generate_sqlite("V0001_SLOPE.db")
```

## Key Differences from vehicle-ripple-data

| Feature | vehicle-ripple-data | vehicle-slope-data |
|:--------|:--------------------|:-------------------|
| **Folder suffix** | `_RIPPLE` | `_SLOPE` |
| **Statistics columns** | 7 columns (VPP, frequency, etc.) | 4 columns (slope max/min/abs) |
| **Image files** | Required (.png per condition) | Optional (scanned if present) |
| **Data unit** | V (Volts) or A (Amperes) | V/s (Volts per second) |
| **Database table** | test_results | slope_results |
| **Excel columns** | Time VPP, Freq Peak, etc. | Slope Max/Min/Abs |

## Version History

### V1.3 (current) - 2026-05-12
- 同步 vehicle-ripple-data V4.4 / plan smooth-sniffing-newt.md V3.6 实现
- SOC 多分隔符正则支持 `_` `-` `空格`
- 坡度 GBK 乱码 (`�¶�10`) 自动规范化为 `坡度10`
- 图片文件名首尾空格 .strip() 处理
- 同步 NEW-1 importer 内部去 commit, NEW-3 stage1 manual_required, P1.5 vehicle_info 指纹
- **NEW-5 R6+**: slope_report 阈值与判定修复 (`build_compliance` 实现 abs > 20000 判定;
  `build_result_text` 加"最大值绝对值"措辞 + 末尾阈值断言; `adapt_standard_requirement`
  ripple→slope 整句替换 + 全角逗号变体 + 兜底替换)
- **NEW-7 同步 (v1.6 hotfix P2.2)**: `slope_processor._discover_components` 加 elif is_file +
  suspicious_exts 检测,避免 zip/rar/docx 等可疑文件静默丢弃
- **P3.3 (v1.6 hotfix)**: `slope_processor` metadata 3 处 datetime.now() → UTC 时区
- **HR-N5 闭环**: slope_report_template.docx 模板复用 (sha256 与 ripple 相同),
  通过 NEW-5 代码层补正阈值,无需重制模板

### V1.2
- Image scanning support (optional)
- Image paths stored in JSON/Excel/SQLite outputs
- Compatible with report generation skill

### V1.1 (2025-03-15)
- Core slope processor (slope_processor.py)
- Multi-component batch processing
- SQLite database generation
- Excel report generation

### V1.0 (2025-03-21)
- Initial release
- Support for {VehicleID}_SLOPE folder naming
- 4-column slope statistics format
- JSON, Excel, SQLite output formats
- Chinese error reporting
- Based on vehicle-ripple-data V4.1 architecture
