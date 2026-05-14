# Usage Examples / 使用示例

Practical examples for common use cases.
常见用例的实用示例。

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

### Basic Processing

#### Process Single Vehicle

```bash
# Basic processing
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# With progress bar
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

# Custom output directory
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --output D:/Results/V0001
```

#### Python API

```python
from scripts.core.vehicle_processor import VehicleDataProcessor

# Basic usage
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")
result = processor.process()

# With custom config
config = {
    'generate_json': True,
    'generate_excel': True,
    'generate_sqlite': False,  # Skip SQLite
}
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE", config=config)
result = processor.process()
```

### Batch Processing

#### Multiple Vehicles

```bash
# Process multiple vehicles
python scripts/cli/vehicle_skills_cli.py batch \
    E:/Vehicle_Date/V0001 \
    E:/Vehicle_Date/V0002 \
    E:/Vehicle_Date/V0003

# With progress
python scripts/cli/vehicle_skills_cli.py batch \
    E:/Vehicle_Date/V000* \
    --progress
```

#### Python Script

```python
import glob
from pathlib import Path
from scripts.cli.vehicle_skills_cli import batch_process

# Find all vehicle folders
vehicle_folders = [
    Path(f) for f in glob.glob("E:/Vehicle_Date/V000*_RIPPLE")
]

# Batch process
results = batch_process(vehicle_folders, progress=True)

# Summary
success_count = sum(1 for r in results if r['success'])
print(f"Processed: {success_count}/{len(results)} vehicles")
```

### Data Validation

#### Validate Before Processing

```bash
# Check if data is valid
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001

# Output example:
# Status: ✓ Valid
# RIPPLE: Yes (2 components)
# SLOPE: Yes (2 components)
```

#### Python API

```python
from scripts.cli.vehicle_skills_cli import validate_vehicle_folder

results = validate_vehicle_folder(Path("E:/Vehicle_Date/V0001"))

if results['valid']:
    print("Data is valid, ready to process")
    print(f"RIPPLE components: {results['ripple_components']}")
    print(f"SLOPE components: {results['slope_components']}")
else:
    print("Validation failed:")
    for error in results['errors']:
        print(f"  - {error}")
```

### Working with Results

#### Access JSON Output

```python
import json

# Load processed data
with open("V0001_RIPPLE_output/V0001_RIPPLE_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Get vehicle info
vehicle_id = data['vehicle']['vehicle_id']
vehicle_model = data['vehicle']['vehicle_info'].get('车型', 'Unknown')

# Count components and conditions
total_components = len(data['components'])
total_conditions = sum(
    len(c['conditions']) for c in data['components'].values()
)

print(f"Vehicle: {vehicle_id} ({vehicle_model})")
print(f"Components: {total_components}")
print(f"Conditions: {total_conditions}")
```

#### Query SQLite Database

```python
import sqlite3

# Connect to database
conn = sqlite3.connect("V0001_RIPPLE_output/V0001_RIPPLE.db")
cursor = conn.cursor()

# Query all results
cursor.execute("""
    SELECT component_code, condition_id, time_vpp, image_path
    FROM ripple_results
    ORDER BY time_vpp DESC
    LIMIT 10
""")

# Get top 10 by VPP
print("Top 10 conditions by VPP:")
for row in cursor.fetchall():
    comp, cond, vpp, img = row
    print(f"  {comp} - {cond}: {vpp} Ipp")

# Query specific component
cursor.execute("""
    SELECT condition_name, freq_peak_frequency_khz
    FROM ripple_results
    WHERE component_code = 'ACCM_A'
""")

print("\nACCM_A frequency peaks:")
for row in cursor.fetchall():
    name, freq = row
    print(f"  {name}: {freq} kHz")

conn.close()
```

#### Process Excel Report

```python
import pandas as pd

# Read Excel report
excel_file = "V0001_RIPPLE_output/V0001_RIPPLE_summary.xlsx"

# Read specific sheet
vehicle_info = pd.read_excel(excel_file, sheet_name='Vehicle Information')
component_summary = pd.read_excel(excel_file, sheet_name='Component Summary')
detailed_results = pd.read_excel(excel_file, sheet_name='Detailed Results')

# Filter conditions
high_vpp = detailed_results[detailed_results['Vpp (Ipp)'] > 50]
print(f"Conditions with VPP > 50: {len(high_vpp)}")

# Group by component
by_component = detailed_results.groupby('Component')['Vpp (Ipp)'].agg(['mean', 'max', 'min'])
print("\nStatistics by component:")
print(by_component)
```

### Advanced Configuration

#### Custom Vehicle Fields

```yaml
# config/custom/vehicle_fields.yaml
field_mappings:
  battery_capacity_kwh:
    keywords: ["电池容量", "Battery Capacity", "kWh"]
    required: false
    unit_conversion:
      factor: 1.0
      decimal_places: 1
  
  motor_power_kw:
    keywords: ["电机功率", "Motor Power", "kW"]
    required: false
```

```python
# Use custom config
processor = VehicleDataProcessor(
    "E:/Vehicle_Date/V0001_RIPPLE",
    config={'config_dir': 'config/custom'}
)
```

#### Custom Matching Rules

```yaml
# config/custom/matching_rules.yaml
matching:
  similarity_threshold: 0.8  # Stricter matching
  enable_feature_match: true
  
custom_rules:
  "custom_condition_1":
    condition_name: "Custom Test"
    soc_level: "≥70%"
```

### Error Handling

#### Handle Processing Errors

```python
from scripts.core.vehicle_processor import VehicleDataProcessor
import traceback

try:
    processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")
    result = processor.process()
    
    # Check for warnings
    if result['metadata']['warnings']:
        print("Warnings:")
        for warning in result['metadata']['warnings']:
            print(f"  - {warning}")
    
except FileNotFoundError as e:
    print(f"Missing file: {e}")
except ValueError as e:
    print(f"Invalid data: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()
```

#### Validate Component Folders

```python
from pathlib import Path

folder = Path("E:/Vehicle_Date/V0001_RIPPLE")

# Check structure
required_files = ['vehicle_info.md']
for req_file in required_files:
    if not (folder / req_file).exists():
        print(f"Missing: {req_file}")

# Check components
components = [d for d in folder.iterdir() if d.is_dir() and not d.name.endswith('_output')]
if not components:
    print("No component folders found")
else:
    print(f"Found {len(components)} components")
    for comp in components:
        stats_file = comp / 'statistics.xlsx'
        if not stats_file.exists():
            print(f"  Warning: {comp.name} missing statistics.xlsx")
```

---

<a name="中文"></a>
## 🇨🇳 中文

### 基础处理

#### 处理单个车辆

```bash
# 基础处理
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# 带进度条
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

# 自定义输出目录
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --output D:/Results/V0001
```

#### Python API

```python
from scripts.core.vehicle_processor import VehicleDataProcessor

# 基础用法
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")
result = processor.process()

# 自定义配置
config = {
    'generate_json': True,
    'generate_excel': True,
    'generate_sqlite': False,  # 跳过SQLite
}
processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE", config=config)
result = processor.process()
```

### 批量处理

#### 多个车辆

```bash
# 处理多个车辆
python scripts/cli/vehicle_skills_cli.py batch \
    E:/Vehicle_Date/V0001 \
    E:/Vehicle_Date/V0002 \
    E:/Vehicle_Date/V0003

# 带进度
python scripts/cli/vehicle_skills_cli.py batch \
    E:/Vehicle_Date/V000* \
    --progress
```

#### Python脚本

```python
import glob
from pathlib import Path
from scripts.cli.vehicle_skills_cli import batch_process

# 查找所有车辆文件夹
vehicle_folders = [
    Path(f) for f in glob.glob("E:/Vehicle_Date/V000*_RIPPLE")
]

# 批量处理
results = batch_process(vehicle_folders, progress=True)

# 汇总
success_count = sum(1 for r in results if r['success'])
print(f"已处理: {success_count}/{len(results)} 辆车")
```

### 数据验证

#### 处理前验证

```bash
# 检查数据是否有效
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001

# 输出示例：
# 状态: ✓ 有效
# 纹波: 是 (2个组件)
# 斜率: 是 (2个组件)
```

#### Python API

```python
from scripts.cli.vehicle_skills_cli import validate_vehicle_folder

results = validate_vehicle_folder(Path("E:/Vehicle_Date/V0001"))

if results['valid']:
    print("数据有效，可以处理")
    print(f"纹波组件数: {results['ripple_components']}")
    print(f"斜率组件数: {results['slope_components']}")
else:
    print("验证失败:")
    for error in results['errors']:
        print(f"  - {error}")
```

### 处理结果

#### 访问JSON输出

```python
import json

# 加载处理后的数据
with open("V0001_RIPPLE_output/V0001_RIPPLE_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 获取车辆信息
vehicle_id = data['vehicle']['vehicle_id']
vehicle_model = data['vehicle']['vehicle_info'].get('车型', 'Unknown')

# 统计组件和工况数
total_components = len(data['components'])
total_conditions = sum(
    len(c['conditions']) for c in data['components'].values()
)

print(f"车辆: {vehicle_id} ({vehicle_model})")
print(f"组件数: {total_components}")
print(f"工况数: {total_conditions}")
```

#### 查询SQLite数据库

```python
import sqlite3

# 连接数据库
conn = sqlite3.connect("V0001_RIPPLE_output/V0001_RIPPLE.db")
cursor = conn.cursor()

# 查询所有结果
cursor.execute("""
    SELECT component_code, condition_id, time_vpp, image_path
    FROM ripple_results
    ORDER BY time_vpp DESC
    LIMIT 10
""")

# 获取VPP前10
print("VPP前10的工况:")
for row in cursor.fetchall():
    comp, cond, vpp, img = row
    print(f"  {comp} - {cond}: {vpp} Ipp")

# 查询特定组件
cursor.execute("""
    SELECT condition_name, freq_peak_frequency_khz
    FROM ripple_results
    WHERE component_code = 'ACCM_A'
""")

print("\nACCM_A频率峰值:")
for row in cursor.fetchall():
    name, freq = row
    print(f"  {name}: {freq} kHz")

conn.close()
```

#### 处理Excel报告

```python
import pandas as pd

# 读取Excel报告
excel_file = "V0001_RIPPLE_output/V0001_RIPPLE_summary.xlsx"

# 读取特定工作表
vehicle_info = pd.read_excel(excel_file, sheet_name='Vehicle Information')
component_summary = pd.read_excel(excel_file, sheet_name='Component Summary')
detailed_results = pd.read_excel(excel_file, sheet_name='Detailed Results')

# 过滤工况
high_vpp = detailed_results[detailed_results['Vpp (Ipp)'] > 50]
print(f"VPP > 50的工况数: {len(high_vpp)}")

# 按组件分组统计
by_component = detailed_results.groupby('Component')['Vpp (Ipp)'].agg(['mean', 'max', 'min'])
print("\n各组件统计:")
print(by_component)
```

### 高级配置

#### 自定义车辆字段

```yaml
# config/custom/vehicle_fields.yaml
field_mappings:
  battery_capacity_kwh:
    keywords: ["电池容量", "Battery Capacity", "kWh"]
    required: false
    unit_conversion:
      factor: 1.0
      decimal_places: 1
  
  motor_power_kw:
    keywords: ["电机功率", "Motor Power", "kW"]
    required: false
```

```python
# 使用自定义配置
processor = VehicleDataProcessor(
    "E:/Vehicle_Date/V0001_RIPPLE",
    config={'config_dir': 'config/custom'}
)
```

#### 自定义匹配规则

```yaml
# config/custom/matching_rules.yaml
matching:
  similarity_threshold: 0.8  # 更严格的匹配
  enable_feature_match: true
  
custom_rules:
  "custom_condition_1":
    condition_name: "自定义测试"
    soc_level: "≥70%"
```

### 错误处理

#### 处理处理错误

```python
from scripts.core.vehicle_processor import VehicleDataProcessor
import traceback

try:
    processor = VehicleDataProcessor("E:/Vehicle_Date/V0001_RIPPLE")
    result = processor.process()
    
    # 检查警告
    if result['metadata']['warnings']:
        print("警告:")
        for warning in result['metadata']['warnings']:
            print(f"  - {warning}")
    
except FileNotFoundError as e:
    print(f"缺少文件: {e}")
except ValueError as e:
    print(f"无效数据: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"意外错误: {e}")
    traceback.print_exc()
```

#### 验证组件文件夹

```python
from pathlib import Path

folder = Path("E:/Vehicle_Date/V0001_RIPPLE")

# 检查结构
required_files = ['vehicle_info.md']
for req_file in required_files:
    if not (folder / req_file).exists():
        print(f"缺少: {req_file}")

# 检查组件
components = [d for d in folder.iterdir() if d.is_dir() and not d.name.endswith('_output')]
if not components:
    print("未找到组件文件夹")
else:
    print(f"找到 {len(components)} 个组件")
    for comp in components:
        stats_file = comp / 'statistics.xlsx'
        if not stats_file.exists():
            print(f"  警告: {comp.name} 缺少 statistics.xlsx")
```

---

## Troubleshooting / 故障排除

### Common Issues / 常见问题

#### Issue: "ModuleNotFoundError: No module named 'scripts'"
**Solution**: Add project root to Python path
```python
import sys
sys.path.insert(0, 'path/to/vehicle-ripple-data')
```

#### Issue: "FileNotFoundError: vehicle_info.md"
**Solution**: Ensure vehicle folder structure is correct
```
V0001_RIPPLE/
├── vehicle_info.md  ← Required
└── ...
```

#### Issue: "UnicodeDecodeError" when reading files
**Solution**: File encoding issues, usually GBK/UTF-8 mismatch
- Tool automatically tries multiple encodings
- Convert files to UTF-8 if needed

#### Issue: "sqlite3.OperationalError: no such column"
**Solution**: Delete old database and reprocess
```bash
rm V0001_RIPPLE_output/V0001_RIPPLE.db
python scripts/cli/vehicle_skills_cli.py process V0001_RIPPLE
```

---

<div align="center">

**[Back to README](../README.md) | [返回README](../README.md)**

</div>
