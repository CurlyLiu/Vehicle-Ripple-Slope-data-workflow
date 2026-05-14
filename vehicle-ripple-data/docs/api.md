# API Documentation / API文档

Complete API reference for Vehicle Ripple Data.
车辆纹波数据的完整API参考。

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

## Core Classes

### VehicleDataProcessor

Main processor class for vehicle ripple data.

```python
from scripts.core.vehicle_processor import VehicleDataProcessor

processor = VehicleDataProcessor(vehicle_folder: str, config: Optional[Dict] = None)
result = processor.process()
```

#### Constructor Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vehicle_folder` | str | Yes | Path to vehicle data folder |
| `config` | Dict | No | Processing configuration options |

#### Configuration Options

```python
config = {
    'generate_json': True,      # Generate JSON output
    'generate_excel': True,     # Generate Excel report
    'generate_sqlite': True,    # Generate SQLite database
    'output_dir': None,         # Custom output directory
}
```

#### Methods

##### `process() -> Dict[str, Any]`

Main processing method. Executes the complete pipeline.

**Returns:**
- `vehicle`: Vehicle ID and information
- `components`: Dict of component data
- `metadata`: Processing metadata

**Example:**
```python
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")
result = processor.process()

# Access vehicle info
vehicle_id = result['vehicle']['vehicle_id']
vehicle_info = result['vehicle']['vehicle_info']

# Access components
for comp_code, comp_data in result['components'].items():
    print(f"Component: {comp_data['component_name']}")
    for cond_id, cond_data in comp_data['conditions'].items():
        print(f"  Condition: {cond_data['condition_name']}")
        print(f"  Image: {cond_data['image_path']}")
```

##### `generate_json(output_path: str) -> None`

Generate JSON output file separately.

##### `generate_excel(output_path: str) -> None`

Generate Excel report separately.

##### `generate_sqlite(output_path: str) -> None`

Generate SQLite database separately.

### ConditionMatcher

Fuzzy matching for condition names.

```python
from scripts.core.condition_matcher import ConditionMatcher

matcher = ConditionMatcher(rules: Dict[str, Dict])
result = matcher.match(condition_id: str)
```

#### Methods

##### `match(condition_id: str) -> Optional[MatchResult]`

Find matching condition name.

**Parameters:**
- `condition_id`: Raw condition ID from filename

**Returns:**
- `MatchResult` object or None

**Example:**
```python
rules = {
    '87_超车80-140': {'condition_name': '超车', 'soc_level': '≥70%'},
}

matcher = ConditionMatcher(rules)
result = matcher.match('87_超车80-140')

if result:
    print(f"Matched: {result.matched_id}")
    print(f"Name: {result.condition_name}")
    print(f"Type: {result.match_type}")  # exact, normalized, fuzzy, feature
    print(f"Confidence: {result.confidence}")
```

### ConfigManager

Configuration management with hot-reload support.

```python
from config import ConfigManager, get_config_manager

config_manager = get_config_manager()
config = config_manager.load('common/vehicle_fields')
```

#### Methods

##### `load(config_name: str, use_cache: bool = True) -> Dict[str, Any]`

Load configuration file.

**Parameters:**
- `config_name`: Config path (e.g., 'common/vehicle_fields')
- `use_cache`: Use cached version if available

**Example:**
```python
# Load vehicle fields
vehicle_fields = config_manager.load('common/vehicle_fields')

# Load matching rules
matching_rules = config_manager.load('common/matching_rules')

# Load Excel template
template = config_manager.load('ripple/excel_template')
```

##### `reload(config_name: Optional[str] = None) -> None`

Reload configuration (force refresh).

---

<a name="中文"></a>
## 🇨🇳 中文

## 核心类

### VehicleDataProcessor

车辆纹波数据处理的主处理器类。

```python
from scripts.core.vehicle_processor import VehicleDataProcessor

processor = VehicleDataProcessor(vehicle_folder: str, config: Optional[Dict] = None)
result = processor.process()
```

#### 构造函数参数

| 参数 | 类型 | 必需 | 说明 |
|-----------|------|----------|-------------|
| `vehicle_folder` | str | 是 | 车辆数据文件夹路径 |
| `config` | Dict | 否 | 处理配置选项 |

#### 配置选项

```python
config = {
    'generate_json': True,      # 生成JSON输出
    'generate_excel': True,     # 生成Excel报告
    'generate_sqlite': True,    # 生成SQLite数据库
    'output_dir': None,         # 自定义输出目录
}
```

#### 方法

##### `process() -> Dict[str, Any]`

主处理方法。执行完整处理流程。

**返回：**
- `vehicle`: 车辆ID和信息
- `components`: 组件数据字典
- `metadata`: 处理元数据

**示例：**
```python
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")
result = processor.process()

# 访问车辆信息
vehicle_id = result['vehicle']['vehicle_id']
vehicle_info = result['vehicle']['vehicle_info']

# 访问组件
for comp_code, comp_data in result['components'].items():
    print(f"组件: {comp_data['component_name']}")
    for cond_id, cond_data in comp_data['conditions'].items():
        print(f"  工况: {cond_data['condition_name']}")
        print(f"  图片: {cond_data['image_path']}")
```

##### `generate_json(output_path: str) -> None`

单独生成JSON输出文件。

##### `generate_excel(output_path: str) -> None`

单独生成Excel报告。

##### `generate_sqlite(output_path: str) -> None`

单独生成SQLite数据库。

### ConditionMatcher

工况名称的模糊匹配。

```python
from scripts.core.condition_matcher import ConditionMatcher

matcher = ConditionMatcher(rules: Dict[str, Dict])
result = matcher.match(condition_id: str)
```

#### 方法

##### `match(condition_id: str) -> Optional[MatchResult]`

查找匹配的工况名称。

**参数：**
- `condition_id`: 文件名中的原始工况ID

**返回：**
- `MatchResult` 对象或 None

**示例：**
```python
rules = {
    '87_超车80-140': {'condition_name': '超车', 'soc_level': '≥70%'},
}

matcher = ConditionMatcher(rules)
result = matcher.match('87_超车80-140')

if result:
    print(f"匹配: {result.matched_id}")
    print(f"名称: {result.condition_name}")
    print(f"类型: {result.match_type}")  # exact, normalized, fuzzy, feature
    print(f"置信度: {result.confidence}")
```

### ConfigManager

支持热重载的配置管理。

```python
from config import ConfigManager, get_config_manager

config_manager = get_config_manager()
config = config_manager.load('common/vehicle_fields')
```

#### 方法

##### `load(config_name: str, use_cache: bool = True) -> Dict[str, Any]`

加载配置文件。

**参数：**
- `config_name`: 配置路径（如 'common/vehicle_fields'）
- `use_cache`: 如可用则使用缓存版本

**示例：**
```python
# 加载车辆字段
vehicle_fields = config_manager.load('common/vehicle_fields')

# 加载匹配规则
matching_rules = config_manager.load('common/matching_rules')

# 加载Excel模板
template = config_manager.load('ripple/excel_template')
```

##### `reload(config_name: Optional[str] = None) -> None`

重新加载配置（强制刷新）。

---

## Data Structures / 数据结构

### Vehicle Result / 车辆结果

```python
{
    'vehicle': {
        'vehicle_id': str,          # Vehicle ID (e.g., "V0001")
        'vehicle_info': Dict         # Vehicle information fields
    },
    'components': Dict[str, ComponentData],
    'metadata': {
        'processing_date': str,     # ISO format datetime
        'total_components': int,
        'total_conditions': int,
        'warnings': List[str],
        'errors': List[str]
    }
}
```

### Component Data / 组件数据

```python
{
    'component_name': str,          # Component name
    'channel_code': str,            # Channel code (e.g., "ACCM_A")
    'unit': str,                    # Unit ("A" or "V")
    'statistics_file': str,         # Relative path to statistics.xlsx
    'conditions_count': int,
    'conditions': Dict[str, ConditionData]
}
```

### Condition Data (Ripple) / 工况数据（纹波）

```python
{
    'condition_name': str,          # Matched condition name
    'soc_level': str,               # SOC level (e.g., "≥70%")
    'time_domain': {
        'effective_value': float,   # Effective value
        'vpp': float                # Peak-to-peak value
    },
    'frequency_domain': {
        'peak_ranking': str,        # Peak ranking (e.g., "6.84kHz")
        'peak_frequency_khz': float,
        'peak_amplitude': float,
        'rms': float
    },
    'image_path': str               # Absolute path to image
}
```

### Condition Data (Slope) / 工况数据（斜率）

```python
{
    'condition_name': str,          # Matched condition name
    'soc_level': str,               # SOC level
    'slope': {
        'max_value': float,         # Maximum slope
        'min_value': float,         # Minimum slope
        'max_abs_value': float,     # Maximum absolute slope
        'unit': str                 # Unit ("V/s")
    },
    'image_path': str               # Absolute path to image
}
```

---

## CLI Commands / CLI命令

### Process / 处理

```bash
python scripts/cli/vehicle_skills_cli.py process <folder> [options]
```

**Options / 选项：**
- `--progress, -p`: Show progress bar / 显示进度条
- `--output, -o`: Custom output directory / 自定义输出目录

### Batch / 批量

```bash
python scripts/cli/vehicle_skills_cli.py batch <folder1> <folder2> ...
```

### Validate / 验证

```bash
python scripts/cli/vehicle_skills_cli.py validate <folder>
```

### Version / 版本

```bash
python scripts/cli/vehicle_skills_cli.py version
```

---

<div align="center">

**[Back to README](../README.md) | [返回README](../README.md)**

</div>
