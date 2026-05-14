---
name: vehicle-ripple-data
description: Integrate and structure vehicle high-voltage ripple test data for downstream analysis and report generation. Use this skill when consolidating test result images and Excel statistics from vehicle components (LV, ACC, DCC, PTC, ACCM, FAN, BATT, Vehicle Harness Splitter) into a unified data format and generating Excel reports. This skill prepares structured data for database construction, generates Excel summary tables with standardized format, creates comprehensive error reports in Chinese language, and organizes all outputs in {VehicleID}_RIPPLE_output folder. Handles component-channel mapping, condition matching, data validation, SQLite database generation, Excel export, automatic error_report.md generation, and output file organization.
version: "4.4"
---

# Vehicle High-Voltage Ripple Test Data Integration & Report Generation

Integrate and structure vehicle ripple test data by consolidating result images with Excel statistics, applying condition mapping rules, preparing unified data for downstream analysis, SQLite database construction, and Excel report generation with standardized format.

## Input Data Structure

### Hierarchical Folder Structure

**User should input the parent folder** (e.g., `E:\1 项目\V0001`), which contains:

```
E:\1 项目\V0001/                    # Parent folder (user input)
├── vehicle_info.md                # REQUIRED: Vehicle parameters (parent level)
├── vehicle_info.xlsx              # Alternative: Excel format vehicle info
├── setup.png                      # Optional: Vehicle setup photo
├── setup.jpg                      # Alternative: JPG format setup photo
├── test_naming_rules.md           # Optional: Shared naming rules (parent level)
├── test_naming_rules.xlsx         # Alternative: Excel format rules
├── sensor_naming_rules.md         # Optional: Shared sensor rules (parent level)
├── sensor_naming_rules.xlsx       # Alternative: Excel format rules
├── test_data/                     # IGNORED: Raw test data folder
├── V0001_RIPPLE/                  # RIPPLE data folder (auto-detected)
│   ├── FM_V/                      # Component folder (Front Motor Voltage)
│   │   ├── statistics.xlsx        # Statistics data
│   │   └── *.png                  # Result images
│   ├── RM_V/                      # Component folder (Rear Motor Voltage)
│   ├── LV_V/                      # Component folder (Low Voltage)
│   ├── LV_A/                      # Component folder (Low Current)
│   ├── DCC_V/                     # Component folder (DC Charging Voltage)
│   ├── DCC_A/                     # Component folder (DC Charging Current)
│   └── ... (other components)
│   └── V0001_RIPPLE_output/       # Output folder (created inside RIPPLE folder)
│       ├── V0001_RIPPLE_summary.xlsx
│       ├── V0001_RIPPLE.db
│       ├── V0001_RIPPLE_data.json
│       ├── error_report.md        # Chinese processing report
│       └── .cache/                # Incremental processing cache
└── V0001_SLOPE/                   # SLOPE data folder (handled by vehicle-slope-data skill)
```

**Processing Logic:**
1. User inputs the **parent folder** (e.g., `E:\1 项目\V0001`)
2. Skill **automatically finds** the `{VehicleID}_RIPPLE` subfolder
3. Skill loads **naming rules** and **sensor rules** from the system-level SKILL references folder (test_naming_rules.md and sensor_naming_rules.md) as baseline
4. Skill reads **required files** from parent folder: `vehicle_info.md` or `vehicle_info.xlsx` (REQUIRED)
5. Skill reads **naming rules** from parent folder (optional, supplements system defaults if present)
6. Skill reads **sensor rules** from parent folder (optional, supplements system defaults if present)
7. Skill processes `{VehicleID}_RIPPLE` folder for component data
8. Output saved to `{VehicleID}_RIPPLE/{VehicleID}_RIPPLE_output/`

**Folder Naming Convention:**
- **Parent folder**: `{VehicleID}` (e.g., `V0001`, `V0002`) or any custom name
- **RIPPLE subfolder**: `{VehicleID}_RIPPLE` (e.g., `V0001_RIPPLE`)
- **Output folder**: `{VehicleID}_RIPPLE_output` (created inside RIPPLE folder)

**Vehicle ID Extraction Logic:**
```python
def extract_vehicle_id_from_ripple_folder(folder_name):
    """Extract vehicle ID from RIPPLE folder name"""
    if folder_name.endswith('_RIPPLE'):
        return folder_name[:-7]  # Remove '_RIPPLE' suffix
    return folder_name
```

**Required Files (from parent folder):**
- **Vehicle info** (`vehicle_info.md` or `vehicle_info.xlsx`) - 27 vehicle parameters

**Optional Files (from parent folder):**
- **Test naming rules** (`test_naming_rules.md` or `test_naming_rules.xlsx`) - maps condition names to SOC levels
- **Sensor naming rules** (`sensor_naming_rules.md` or `sensor_naming_rules.xlsx`) - defines component channels
- **Setup image** (`setup.png` or `setup.jpg`) - vehicle photo for reports

**RIPPLE Folder Contents:**
- **Component folders** (one per sensor channel, names must match sensor_naming_rules)
  - Each contains `statistics.xlsx` and `.png` result images

**Rule Priority (highest to lowest):**
1. Parent folder rules (`E:\1 项目\V0001\test_naming_rules.md`)
2. Skill default rules (`references/test_naming_rules.md`)

### Vehicle Information (vehicle_info.md or vehicle_info.xlsx)

**Required fields** (extract all available parameters from actual vehicle data):
- Vehicle model, manufacturer, class, energy type
- Length*Width*Height(mm), wheelbase(mm), track width, etc.
- Engine parameters (model, displacement, power, etc.)
- Motor parameters (power, torque, etc.)
- Battery parameters (type, capacity, range, etc.)
- Other technical parameters

**Format:**
- Markdown table format (recommended)
- First column: parameter name, Second column: parameter value

### Test Naming Rules (test_naming_rules.md or test_naming_rules.xlsx)

Maps test condition names to data identifiers.

**Purpose:**
- Provides condition_name (Chinese condition name)
- Assists in validating condition_id format (but SOC is extracted directly from condition_id)

**Note:** SOC is extracted directly from condition_id; test_naming_rules is mainly used for condition_name mapping and validation.

### Sensor Naming Rules (sensor_naming_rules.md or sensor_naming_rules.xlsx)

Defines component channels and their descriptions. Channel codes determine measurement units:
- **Codes ending with `_A`**: Current measurement (unit: A - Amperes)
- **Codes ending with `_V`**: Voltage measurement (unit: V - Volts)

**Default Sensors** (24 channels):
| Channel | Component Description | Unit |
|---------|----------------------|------|
| FM_V | Front motor DC bus voltage | V |
| FM_A | Front motor DC bus current | A |
| RM_V | Rear motor DC bus voltage | V |
| RM_A | Rear motor DC bus current | A |
| DCC_V | Battery DC charging voltage | V |
| DCC_A | Battery DC charging current | A |
| ACC_V | OBC output voltage | V |
| ACC_A | OBC output current | A |
| PTC_V | PTC input voltage | V |
| PTC_A | PTC input current | A |
| ACCM_V | Compressor input voltage | V |
| ACCM_A | Compressor input current | A |
| LV_V | 12V battery low voltage | V |
| LV_A | 12V battery low current | A |
| FAN_A | Front cooling fan current | A |
| BATT_V | Battery voltage | V |
| BATT_A | Battery current | A |
| Vehicle_Harness_Splitter_V | Vehicle harness splitter voltage | V |
| Vehicle_Harness_Splitter_A | Vehicle harness splitter current | A |

### Component Folder Contents

Each component folder contains:
- `statistics.xlsx`: Test metrics for all conditions
- `.png` files: One per condition, named with condition ID

**statistics.xlsx Format (Standard 7 Columns):**
| Column Index | Column Name | Description |
|--------------|-------------|-------------|
| 0 | 数据名称 | Condition identifier (e.g., "87_超车80-140") |
| 1 | 整段时域有效值 | Time-domain effective value |
| 2 | 时域纹波VPP值（V）| Time-domain ripple VPP value |
| 3 | 峰值排序 | Spectrum peak ranking details (text) |
| 4 | 频域最大峰值频率(KHZ) | Frequency-domain peak frequency |
| 5 | 频域最大峰值V/A | Frequency-domain peak amplitude |
| 6 | 频域均方根值（rms）| Frequency-domain RMS |

**Note:** Due to encoding issues, use column indices (iloc) rather than column names when reading.

**Image Filename Format:**
```
{condition_id}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}.{unit}.png

Examples:
20_直流充电暖风_LV_V_1.28VPP_20.00kHz-0.003V.png
87_超车80-140_LV_V_8.39VPP_0.61kHz-0.106V.png
坡度10_32_匀速80冷风_LV_V_1.85VPP_3.94kHz-0.054V.png
```

Parsed as:
- `condition_id`: "87_超车80-140" or "坡度10_32_匀速80冷风"
- `channel`: "LV_V" (must match component folder name)
- `vpp`: "8.39VPP" → 8.39
- `freq`: "0.61kHz" → 0.61
- `amplitude`: "0.106V" → 0.106
- `unit`: "V" or "A" (determined by sensor_naming_rules)

---

## Critical Notes

### Note 1: Image Filename Parsing
**Common cause of null image paths.**

**Image filenames have two formats** requiring different parsing:

**Standard Format:**
```
{SOC}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
```
- Example: `20_直流充电暖风_ACCM_A_15.81VPP_24.06kHz-1.623A.png`
- Parsed `condition_id`: `20_直流充电暖风` (**NOT** just `20`)

**Slope Condition Format:**
```
坡度10_{SOC}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
```
- Example: `坡度10_32_匀速80冷风_ACCM_A_46.78VPP_17.50kHz-1.631A.png`
- Parsed `condition_id`: `坡度10_32_匀速80冷风`

The extracted condition description must be mapped to test_naming_rules to get the condition name.

**Validation:** After parsing, verify that `image_info['condition_id'] == excel_condition_id` for all conditions. Any mismatch results in null image paths.

### Note 2: statistics.xlsx Encoding Issues
**Most common problem in actual processing.**

**Problem:**
- Many statistics.xlsx files are saved with GBK encoding
- pandas reads Chinese characters as garbled text (e.g., `数据名称` shows as `�ļ���`)
- Direct column name access causes KeyError

**Solution:**
1. **Use column indices instead of column names**
   ```python
   # DON'T do this:
   condition_id = row['数据名称']  # Fails if column names are garbled
   
   # DO this:
   condition_id = str(row.iloc[0]).strip()  # Column 0: 数据名称
   effective_value = row.iloc[1]             # Column 1: 整段时域有效值
   vpp = row.iloc[2]                         # Column 2: 时域纹波Vpp值
   peak_ranking = row.iloc[3]                # Column 3: 峰值排序
   freq_khz = row.iloc[4]                    # Column 4: 频域最大峰值频率
   peak_amp = row.iloc[5]                    # Column 5: 频域最大峰值
   rms = row.iloc[6]                         # Column 6: 频域均方根值
   ```

2. **Standard 7-column order** (even if column names are garbled):
   - Column 0: 数据名称
   - Column 1: 整段时域有效值
   - Column 2: 时域纹波Vpp值（V）
   - Column 3: 峰值排序
   - Column 4: 频域最大峰值频率(KHZ)
   - Column 5: 频域最大峰值V/A
   - Column 6: 频域均方根值（rms）

### Note 3: Naming Rules Merge Strategy
**Common source of errors - fixed by merge strategy.**

**Method**: Always merge parent folder rules with default rules
- **Step 1**: Load complete default rules from skill reference folder (54 test conditions, 24 sensor channels)
- **Step 2**: Check parent folder for custom rules - if found, merge them (parent rules take precedence)
- **Result**: Guaranteed complete rule coverage

### Note 4: Validate All Component Folders
**Don't stop after checking one folder.**
- Scan vehicle folder and find all subdirectories
- Validate each folder against sensor_naming_rules
- Report all invalid folders at once, not just the first one
- **Importance**: Vehicles can have 15+ component folders. Checking only one means missing errors.

### Note 5: Unit Assignment is Deterministic
- Channel code ending with `_A` = Current (unit: A)
- Channel code ending with `_V` = Voltage (unit: V)
- This is automatic based on suffix - no guessing needed

### Note 6: Chinese Encoding Handling is Critical
**All input files contain Chinese characters and must be read with proper encoding.**
- **Critical**: All files (vehicle_info, test_naming_rules, sensor_naming_rules, statistics.xlsx) contain Chinese text
- **Must** read files with UTF-8 encoding (try UTF-8 first, fallback to GBK if needed)
- **Never** assume ASCII encoding - this corrupts Chinese characters
- When writing output, always use UTF-8 encoding to preserve Chinese text
- **Importance**: Incorrect encoding results in garbled Chinese text (e.g., "坦克500" becomes "����500"), making output unusable

### Note 7: SOC Value Extraction
**Condition ID in statistics.xlsx directly contains SOC value.**

Condition ID format: `{SOC}_{condition_desc}` or `坡度10_{SOC}_{condition_desc}` (slope conditions)

Examples:
- `87_超车80-140(运动模式)` → SOC = 87 (≥70%)
- `26_超车80-140（运动模式）` → SOC = 26 (≤40%)
- `坡度10_21_匀速80暖风（运动模式）` → SOC = 21 (≤40%, with "坡度10_" prefix)

**Correct Extraction Logic (always use this):**

```python
def extract_soc_from_condition_id(condition_id):
    """Extract SOC value from condition_id - NEVER use test_naming_rules for SOC"""
    # Handle "坡度10_" prefix
    if condition_id.startswith('坡度10_'):
        condition_id = condition_id[5:]  # Remove "坡度10_"
    
    # Extract first numeric value
    match = re.match(r'(\d+)_.*', condition_id)
    if match:
        return int(match.group(1))
    return None

def get_soc_level(soc_value):
    """Map SOC value to SOC level - ALWAYS use this function"""
    if soc_value is None:
        return "Unknown"
    elif soc_value >= 70:
        return "≥70%"
    elif soc_value >= 40:
        return "40%-70%"
    else:
        return "≤40%"

# Usage (for each condition):
soc_value = extract_soc_from_condition_id(condition_id)
soc_level = get_soc_level(soc_value)  # This ALWAYS works for valid numbers!

# test_naming_rules is ONLY for condition name lookup, NOT SOC level!
condition_name = test_rules.get(condition_id, {}).get('condition_name', 
                                                       condition_id.split('_', 1)[1] if '_' in condition_id else condition_id)
```

**Mapping Rules:**
- SOC ≥ 70% → "≥70%"
- 40% ≤ SOC < 70% → "40%-70%"
- SOC < 40% → "≤40%"

**Critical Rules:**
1. **ALWAYS extract SOC directly from condition_id** - Don't rely on test_naming_rules
2. **ALWAYS use numeric mapping** - test_naming_rules is only for condition names
3. **NEVER return "Unknown" for valid numbers** - 20_xxx → "≤40%", 87_xxx → "≥70%"
4. **If condition_id not in test_naming_rules** - Still extract SOC correctly, just use condition_id for name

### Note 8: Condition Name Mapping (Intelligent Fuzzy Matching)
**Condition name is looked up from test_naming_rules.md using multi-level fuzzy matching.**

**Matching Strategy (Priority Order):**

1. **Exact Match**: Direct dictionary lookup
2. **Normalized Match**: Removes bracket variations `()` `（）`
3. **Fuzzy Match**: Edit distance (Levenshtein) for typos
4. **Feature Match**: Extracts keywords, SOC level, slope flag for encoding issues

**Examples of Fuzzy Matching:**

| Input Condition ID | Match Type | Matched Rule | Condition Name |
|:-------------------|:-----------|:-------------|:---------------|
| `87_超车80-140(运动模式)` | Exact | Same | 超越加速 |
| `87_超车80-140（运动模式）` | Normalized | `87_超车80-140(运动模式)` | 超越加速 |
| `87_超车80-140运动模式` | Fuzzy (0.95) | `87_超车80-140(运动模式)` | 超越加速 |
| `�¶�10_81_匀速80暖风` | Feature | `坡度10_81_匀速80暖风（运动模式）` | 爬坡高温 |
| `88_超车80-140(运动模式)` | Feature | `87_超车80-140(运动模式)` | 超越加速 |

**Implementation:**

```python
from scripts.core.condition_matcher import ConditionMatcher

# Initialize matcher with test rules
matcher = ConditionMatcher(test_rules)

# Get condition name with fuzzy matching
result = matcher.match(condition_id)

if result:
    print(f"Matched: {result.condition_name}")
    print(f"Type: {result.match_type}")  # exact/normalized/fuzzy/feature
    print(f"Confidence: {result.confidence:.2f}")
else:
    # Fallback to extraction
    condition_name = condition_id.split('_', 1)[1]
```

**Debugging Mismatches:**

```python
# Get detailed matching information
details = matcher.get_match_details(condition_id)
print(details)
# Output: {
#   'input': '87_超车80-140(运动模式',
#   'exact_match': None,
#   'normalized_match': {...},
#   'fuzzy_matches': [...],
#   'final_result': {...}
# }
```

**Expected Results:**
| condition_id | Without Rules | With Fuzzy Matching |
|:-------------|:--------------|:--------------------|
| 坡度10_81_匀速80暖风（运动模式）| 匀速80暖风（运动模式）| 爬坡高温 |
| 87_超车80-140(运动模式) | 超车80-140(运动模式) | 超越加速 |
| 26_超车80-140（运动模式） | 超车80-140（运动模式） | 超越加速 |
| 20_直流充电暖风 | 直流充电暖风 | 直流充电暖风 |
| 90_停车D档热风 | 停车D档热风 | 静止高温 |
| `�¶�10_32_急加速` (GBK乱码) | �¶�10_32_急加速 | 超越加速 |

---

## Processing Workflow

### Step 1: Validate Vehicle Folder and Extract Vehicle ID

1. **Extract Vehicle ID from folder name:**
   - If folder name ends with `_RIPPLE` → vehicle_id = folder_name without `_RIPPLE` suffix
   - Otherwise → vehicle_id = folder_name (legacy format)
   - Example: `V0001_RIPPLE` → vehicle_id = `V0001`

2. **Validate folder exists and contains required files:**
   - Check that the specified vehicle folder exists
   - Verify it contains at least: `vehicle_info.md` OR `vehicle_info.xlsx`

### Step 2: Load Naming Rules (with Chinese Encoding)

**Critical: All naming rules files contain Chinese text and must be read with proper encoding (UTF-8 or GBK).**

**New Rule Loading Strategy: Load default rules first, then merge with parent folder rules.**

1. **Test naming rules** - **Merge Strategy**:
   - **Step 1**: ALWAYS load default rules from skill reference folder first
   - **Step 2**: Check if parent folder has custom rules
     - If YES → Merge parent rules with default rules (parent rules take precedence)
     - If NO → Use default rules as-is
   - Read markdown files with UTF-8 encoding (fallback to GBK)

2. **Sensor naming rules** - **Merge Strategy**:
   - **Step 1**: ALWAYS load default rules from skill reference folder first
   - **Step 2**: Check if parent folder has custom rules
     - If YES → Merge parent rules with default rules
     - If NO → Use default rules as-is

### Step 3: Load Vehicle Info (with Chinese Encoding)

Read vehicle info file (prefer .md if both exist):
- Read with UTF-8 encoding first, fallback to GBK if UTF-8 fails
- Parse markdown table OR read Excel
- Extract vehicle_id and all parameters
- **Preserve Chinese characters** in all fields (车型, 混合动力系统, etc.)

### Step 4: Discover and Validate Components - **MUST VALIDATE ALL FOLDERS**

1. **Scan vehicle folder** for ALL subdirectories
2. **Identify ALL component folders**
3. **Validate EACH folder** name matches a channel code in sensor_naming_rules
4. **Verify minimum components**

### Step 5: Process Each Component

For each valid component folder:

1. **Load Statistics (using column index access)**
   - Read `statistics.xlsx`
   - **Handle encoding issues**: Since column names may be garbled, use `row.iloc[0-6]` to access data
   - Standard 7-column order: 数据名称, 整段时域有效值, 时域纹波VPP值, 峰值排序, 频域最大峰值频率, 频域最大峰值, 频域均方根值

2. **Scan and Parse Images**
   - List all `.png` files
   - Parse filenames to extract metadata (condition_id, VPP, frequency, amplitude)

3. **Match Conditions**
   - Match condition_id in statistics.xlsx with image filenames
   - Ensure 100% match rate

4. **Extract SOC and SOC Level**
   - Extract SOC value from condition_id
   - Map to SOC level (≥70%, 40%-70%, ≤40%)

5. **Build Component Data**
   - Include all conditions with their detailed measurements

### Step 6: Generate Output Structured Data

Generate hierarchical JSON data structure.

---

## Output Options

### Option 1: JSON Output

Return structured JSON object for programmatic use.

### Option 2: SQLite Database

Create/append to SQLite database with schema:

```sql
-- vehicles table
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY,
  vehicle_model TEXT,
  vehicle_info TEXT
);

-- conditions table
CREATE TABLE conditions (
  condition_id TEXT PRIMARY KEY,
  condition_name TEXT,
  soc_level TEXT
);

-- components table
CREATE TABLE components (
  component_code TEXT PRIMARY KEY,
  component_name TEXT,
  unit TEXT
);

-- test_results table
CREATE TABLE test_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vehicle_id TEXT,
  component_code TEXT,
  condition_id TEXT,
  time_effective_value REAL,
  time_vpp REAL,
  freq_peak_frequency_khz REAL,
  freq_peak_amplitude REAL,
  freq_rms REAL,
  image_path TEXT,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
  FOREIGN KEY (component_code) REFERENCES components(component_code),
  FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
);
```

### Option 3: Excel Report

Generate Excel summary report with multiple sheets:

**Sheet 1: Vehicle Information**
| Parameter | Value |
|-----------|-------|
| Vehicle ID | V0001 |
| Vehicle Model | 坦克500 Hi4-Z |
| ... | ... |

**Sheet 2: Component Summary**
| Component Code | Component Name | Unit | Conditions Count |
|----------------|----------------|------|------------------|
| FM_V | Front motor DC bus voltage(V) | V | 45 |
| RM_V | Rear motor DC bus voltage(V) | V | 45 |
| ... | ... | ... | ... |

**Sheet 3: Detailed Results**
| No. | Component | Unit | Condition ID | Condition Name | SOC Level | Time VPP | Freq Peak (kHz) | Freq Amplitude | Image Path |
|-----|-----------|------|--------------|----------------|-----------|----------|-----------------|----------------|------------|
| 1 | FM_V | V | 20_直流充电暖风 | 直流充电暖风 | ≤40% | 1.28 | 20.00 | 0.003 | ... |
| 2 | FM_V | V | 87_超车80-140 | 超越加速 | ≥70% | 15.20 | 0.92 | 0.814 | ... |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

## Report Generation

### Excel Report Generation

**Usage Example:**
```python
from scripts.generate_excel_report import generate_excel_report
import json

# Load processed JSON data
with open('V0001_RIPPLE_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Generate Excel report
generate_excel_report(data, 'V0001_RIPPLE_summary.xlsx')
```

### Chinese Error Report Generation (error_report.md)

**Automatically generated after processing:**

```python
from scripts.generate_error_report_cn import generate_error_report_cn

# Generate Chinese error report in {VehicleID}_RIPPLE_output folder
generate_error_report_cn(
    vehicle_folder="E:/1 项目/V0001/V0001_RIPPLE",
    vehicle_id="V0001",
    vehicle_model="北京越野BJ60增程",
    processing_status=True,
    completed_functions=[
        {'name': '车辆信息已加载', 'success': True, 'details': '27个参数'},
        {'name': '组件已处理', 'success': True, 'details': '2个组件'},
        {'name': 'Excel报告已生成', 'success': True, 'details': 'V0001_RIPPLE_summary.xlsx'},
    ],
    generated_files=[
        {'name': 'V0001_RIPPLE_summary.xlsx', 'type': 'Excel', 'description': 'V3.0格式报告，包含3个工作表'},
        {'name': 'V0001_RIPPLE.db', 'type': 'SQLite', 'description': '数据库，包含4个表'},
        {'name': 'V0001_RIPPLE_data.json', 'type': 'JSON', 'description': '结构化数据导出'},
    ],
    warnings=[]
)
```

**Report Structure:**
```markdown
# Vehicle Ripple Data Processing Report

**Generated**: 2025-03-23 14:30:00
**Version**: 4.4

## Processing Summary
- **Vehicle ID**: V0001
- **Vehicle Model**: 北京越野BJ60增程
- **Processing Status**: ✓ Completed Successfully
- **Total Components**: 2
- **Total Conditions**: 90

## Completed Functions
- Vehicle information loaded
- Test naming rules loaded (54 rules)
- Sensor naming rules loaded (24 channels)
- Component folders validated
- Statistics data processed
- Images matched
- SQLite database generated
- Excel report generated
- JSON data exported

## Generated Files
| Filename | Type | Description |
|----------|------|-------------|
| V0001_RIPPLE_summary.xlsx | Excel | V3.0 format report with 3 sheets |
| V0001_RIPPLE.db | SQLite | Database with 4 tables |
| V0001_RIPPLE_data.json | JSON | Structured data export |
| error_report.md | Markdown | This processing report |

## Component Details
### FM_V
- **Name**: Front motor DC bus voltage(V)
- **Unit**: V
- **Conditions**: 45

### RM_V
- **Name**: Rear motor DC bus voltage(V)
- **Unit**: V
- **Conditions**: 45

## Warnings
None

## Processing Statistics
| Metric | Value |
|--------|-------|
| Total Components | 2 |
| Successfully Processed | 2 |
| Total Conditions | 90 |
| Warnings | 0 |
```

---

## CLI Usage

### Single Vehicle Processing

```bash
# Process single vehicle (auto-detects RIPPLE and SLOPE data)
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# With progress bar
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress
```

### Batch Processing (Multiple Vehicles)

```bash
# Batch with explicit folder list
python scripts/cli/vehicle_skills_cli.py batch E:/Vehicle_Date/V0001 E:/Vehicle_Date/V0002

# Batch with auto-scan (discover all vehicles under parent directory)
python scripts/cli/vehicle_skills_cli.py batch --scan E:/Vehicle_Date

# Batch with progress
python scripts/cli/vehicle_skills_cli.py batch --scan E:/Vehicle_Date --progress
```

**Auto-scan behavior:**
- Scans the parent folder for subdirectories containing `_RIPPLE` or `_SLOPE` data
- Automatically detects both RIPPLE and SLOPE folders per vehicle
- Prints a detailed summary table after processing all vehicles

### Validation

```bash
# Validate folder structure without processing
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001
```

---

## Chinese Version

See `SKILL_CN.md` for the complete Chinese skill documentation.
