# API Reference / API 参考

Complete API documentation for vehicle-slope-data skill.
vehicle-slope-data 技能的完整 API 文档。

---

## Overview / 概览

Vehicle-Slope-Data is a specialized skill for processing voltage slope (du/dt) test data from vehicle components. It reuses configurations from vehicle-ripple-data and provides slope-specific processing.

Vehicle-Slope-Data 是专门用于处理车辆部件电压斜率（du/dt）测试数据的技能。它复用 vehicle-ripple-data 的配置并提供斜率专用处理。

## Dependencies / 依赖

- **Required** / 必需: `vehicle-ripple-data` skill
- **Python Version** / Python 版本: 3.8+
- **Key Packages** / 主要包: pandas, openpyxl, pyyaml

---

## SlopeConfigManager / 斜率配置管理器

**File:** `config/__init__.py`

Manages slope-specific configurations while reusing ripple skill configurations.
管理斜率专用配置，同时复用纹波技能配置。

### Methods / 方法

#### `__init__(config_dir=None)`

Initialize configuration manager.
初始化配置管理器。

**Parameters / 参数:**
- `config_dir` (str, optional): Path to configuration directory. Defaults to skill directory.
  配置目录路径。默认为技能目录。

**Example / 示例:**
```python
from config import SlopeConfigManager

config = SlopeConfigManager()
# or with custom path
config = SlopeConfigManager("C:/custom/config/path")
```

#### `get_vehicle_fields()`

Get vehicle field definitions.
获取车辆字段定义。

**Returns / 返回:**
- `dict`: Vehicle field definitions (reused from ripple skill)
  车辆字段定义（复用纹波技能）

**Example / 示例:**
```python
fields = config.get_vehicle_fields()
# Returns: {'component': {...}, 'condition_name': {...}, ...}
```

#### `get_matching_rules()`

Get fuzzy matching rules.
获取模糊匹配规则。

**Returns / 返回:**
- `dict`: Matching rules configuration
  匹配规则配置

**Example / 示例:**
```python
rules = config.get_matching_rules()
# Includes: exact_match, normalized_match, fuzzy_match, feature_match
```

#### `get_excel_template()`

Get Excel report template for slope data.
获取斜率数据的 Excel 报告模板。

**Returns / 返回:**
- `dict`: Excel template configuration
  Excel 模板配置

**Note / 注意:**
Different from ripple template - includes slope-specific columns like max_slope, avg_slope.
与纹波模板不同 - 包含斜率专用列如 max_slope、avg_slope。

#### `get_styles()`

Get Excel styling configuration.
获取 Excel 样式配置。

**Returns / 返回:**
- `dict`: Style definitions (reused from ripple skill)
  样式定义（复用纹波技能）

---

## SlopeProcessor / 斜率处理器

**File:** `scripts/slope_processor.py`

Main processor for voltage slope test data.
电压斜率测试数据的主处理器。

### Methods / 方法

#### `__init__(config_manager=None)`

Initialize processor with configuration.
使用配置初始化处理器。

**Parameters / 参数:**
- `config_manager` (SlopeConfigManager, optional): Configuration manager instance
  配置管理器实例

**Example / 示例:**
```python
from config import SlopeConfigManager
from scripts.slope_processor import SlopeProcessor

config = SlopeConfigManager()
processor = SlopeProcessor(config)
```

#### `process_vehicle(vehicle_id, input_dir, output_dir=None)`

Process all slope data for a vehicle.
处理车辆的所有斜率数据。

**Parameters / 参数:**
- `vehicle_id` (str): Vehicle identifier (e.g., 'V0001')
  车辆标识符（如 'V0001'）
- `input_dir` (str): Input directory containing component folders
  包含部件文件夹的输入目录
- `output_dir` (str, optional): Output directory. Defaults to input_dir + '_output'
  输出目录。默认为 input_dir + '_output'

**Returns / 返回:**
- `dict`: Processing results including:
  处理结果，包括：
  - `processed_conditions`: Number of processed conditions / 处理的工况数
  - `failed_conditions`: List of failed conditions / 失败的工况列表
  - `output_files`: Generated file paths / 生成的文件路径

**Example / 示例:**
```python
results = processor.process_vehicle(
    vehicle_id="V0001",
    input_dir="E:/Vehicle_Date/V0001/V0001_SLOPE",
    output_dir="E:/Vehicle_Date/V0001/V0001_SLOPE_output"
)

print(f"Processed {results['processed_conditions']} conditions")
print(f"Generated files: {results['output_files']}")
```

#### `process_component(component_dir, component_name)`

Process slope data for a single component.
处理单个部件的斜率数据。

**Parameters / 参数:**
- `component_dir` (str): Path to component directory
  部件目录路径
- `component_name` (str): Name of the component (e.g., 'LV', 'DCC')
  部件名称（如 'LV'、'DCC'）

**Returns / 返回:**
- `list`: List of processed condition data
  处理的工况数据列表

**Example / 示例:**
```python
conditions = processor.process_component(
    component_dir="E:/Vehicle_Date/V0001/V0001_SLOPE/LV",
    component_name="LV"
)
```

#### `process_single_condition(stats_file, image_file, component_name)`

Process a single slope test condition.
处理单个斜率测试工况。

**Parameters / 参数:**
- `stats_file` (str): Path to statistics CSV file
  统计 CSV 文件路径
- `image_file` (str): Path to test image
  测试图片路径
- `component_name` (str): Component name
  部件名称

**Returns / 返回:**
- `dict`: Processed condition data including:
  处理的工况数据，包括：
  - `condition_name`: Matched condition name / 匹配的工况名称
  - `statistics`: Slope statistics / 斜率统计
  - `image_path`: Absolute image path / 绝对图片路径

---

## ConditionMatcher / 工况匹配器

**File:** `scripts/condition_matcher.py`

Matches condition names using fuzzy matching algorithms.
使用模糊匹配算法匹配工况名称。

### Methods / 方法

#### `match_condition(condition_name, component_name, matching_rules)`

Match a condition name to standard names.
将工况名称匹配到标准名称。

**Parameters / 参数:**
- `condition_name` (str): Raw condition name from file
  文件中的原始工况名称
- `component_name` (str): Component name
  部件名称
- `matching_rules` (dict): Matching rules from config
  配置中的匹配规则

**Returns / 返回:**
- `tuple`: (matched_name, match_method, confidence)
  （匹配名称，匹配方法，置信度）

**Match Methods / 匹配方法:**
1. `exact` - Exact match / 精确匹配
2. `normalized` - After bracket removal / 去括号后匹配
3. `fuzzy` - Levenshtein distance / 编辑距离匹配
4. `feature` - Character feature matching / 字符特征匹配

**Example / 示例:**
```python
from scripts.condition_matcher import ConditionMatcher

matcher = ConditionMatcher()
rules = config.get_matching_rules()

matched, method, confidence = matcher.match_condition(
    condition_name="LV_电压斜率测试[工况1]",
    component_name="LV",
    matching_rules=rules
)

print(f"Matched to: {matched} using {method} (confidence: {confidence})")
```

---

## DataExporter / 数据导出器

**File:** `scripts/slope_processor.py` (within SlopeProcessor)

Exports processed data to various formats.
将处理的数据导出为多种格式。

### Methods / 方法

#### `export_to_json(data, output_file)`

Export data to JSON format.
导出数据为 JSON 格式。

**Parameters / 参数:**
- `data` (dict): Data to export
  要导出的数据
- `output_file` (str): Output file path
  输出文件路径

#### `export_to_excel(data, output_file, template)`

Export data to Excel with formatting.
使用格式导出数据为 Excel。

**Parameters / 参数:**
- `data` (dict): Data to export
  要导出的数据
- `output_file` (str): Output file path
  输出文件路径
- `template` (dict): Excel template configuration
  Excel 模板配置

**Note / 注意:**
Slope Excel includes columns: condition_name, max_slope, avg_slope, threshold_crossings
斜率 Excel 包含列：condition_name、max_slope、avg_slope、threshold_crossings

#### `export_to_sqlite(data, db_file)`

Export data to SQLite database.
导出数据为 SQLite 数据库。

**Parameters / 参数:**
- `data` (dict): Data to export
  要导出的数据
- `db_file` (str): Database file path
  数据库文件路径

#### `generate_error_report(failed_conditions, output_file)`

Generate error report for failed conditions.
为失败的工况生成错误报告。

**Parameters / 参数:**
- `failed_conditions` (list): List of failed condition info
  失败工况信息列表
- `output_file` (str): Output report file path
  输出报告文件路径

---

## CLI Interface / 命令行接口

**File:** `scripts/cli/process_slope.py`

### Usage / 用法

```bash
python scripts/cli/process_slope.py [OPTIONS]
```

### Arguments / 参数

| Argument | Required | Description |
|----------|----------|-------------|
| `--vehicle-id` | Yes | Vehicle identifier (e.g., V0001) |
| `--input-dir` | Yes | Input directory path |
| `--output-dir` | No | Output directory (default: input + '_output') |
| `--config-dir` | No | Custom config directory |
| `--verbose` | No | Enable verbose output |

### Examples / 示例

**Basic usage:**
```bash
python scripts/cli/process_slope.py \
  --vehicle-id V0001 \
  --input-dir "E:/Vehicle_Date/V0001/V0001_SLOPE"
```

**With custom output:**
```bash
python scripts/cli/process_slope.py \
  --vehicle-id V0002 \
  --input-dir "E:/Vehicle_Date/V0002/V0002_SLOPE" \
  --output-dir "C:/custom/output"
```

**Verbose mode:**
```bash
python scripts/cli/process_slope.py \
  --vehicle-id V0001 \
  --input-dir "E:/Vehicle_Date/V0001/V0001_SLOPE" \
  --verbose
```

---

## Error Handling / 错误处理

### Common Exceptions / 常见异常

#### `ConfigError`
Raised when configuration files are missing or invalid.
配置文件缺失或无效时抛出。

```python
try:
    config = SlopeConfigManager("/invalid/path")
except ConfigError as e:
    print(f"Configuration error: {e}")
```

#### `ProcessingError`
Raised when data processing fails.
数据处理失败时抛出。

```python
try:
    results = processor.process_vehicle("V0001", "/invalid/path")
except ProcessingError as e:
    print(f"Processing failed: {e}")
```

#### `MatchingError`
Raised when condition matching fails.
工况匹配失败时抛出。

---

## Best Practices / 最佳实践

### 1. Always use absolute paths / 始终使用绝对路径

```python
# Good / 好
input_dir = os.path.abspath("E:/Vehicle_Date/V0001/V0001_SLOPE")

# Bad / 不好
input_dir = "../data/V0001_SLOPE"  # Relative path may fail
```

### 2. Check Ripple skill availability / 检查纹波技能可用性

```python
try:
    from vehicle_ripple_data.config import ConfigManager
    print("Ripple skill available")
except ImportError:
    print("Error: vehicle-ripple-data not installed")
```

### 3. Handle exceptions / 处理异常

```python
try:
    results = processor.process_vehicle(vehicle_id, input_dir)
    if results['failed_conditions']:
        print(f"Warning: {len(results['failed_conditions'])} conditions failed")
except Exception as e:
    print(f"Error: {e}")
```

### 4. Verify output / 验证输出

```python
import os

output_dir = f"{input_dir}_output"
expected_files = ['data.json', 'report.xlsx', 'data.db', 'error_report.md']

for file in expected_files:
    filepath = os.path.join(output_dir, file)
    if os.path.exists(filepath):
        print(f"✓ {file} generated")
    else:
        print(f"✗ {file} missing")
```

---

## API Comparison: Slope vs Ripple / API 对比：斜率 vs 纹波

| Feature | Slope API | Ripple API |
|---------|-----------|------------|
| Config Manager | `SlopeConfigManager` | `ConfigManager` |
| Processor | `SlopeProcessor` | `VehicleProcessor` |
| CLI | `process_slope.py` | `process_vehicle.py` |
| Statistics | max_slope, avg_slope | peak_to_peak, rms |
| Reuses Config | Yes | Self-contained |

---

## See Also / 另请参阅

- [README.md](../README.md) - Main documentation / 主文档
- [examples.md](examples.md) - Usage examples / 使用示例
- [CHANGELOG.md](../CHANGELOG.md) - Version history / 版本历史
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guide / 贡献指南
