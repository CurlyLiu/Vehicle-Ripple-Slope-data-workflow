# Usage Examples / 使用示例

Practical examples for using vehicle-slope-data skill.
vehicle-slope-data 技能的实际使用示例。

---

## Table of Contents / 目录

1. [Quick Start / 快速开始](#quick-start--快速开始)
2. [Basic Examples / 基础示例](#basic-examples--基础示例)
3. [Advanced Usage / 高级用法](#advanced-usage--高级用法)
4. [Batch Processing / 批量处理](#batch-processing--批量处理)
5. [Common Issues / 常见问题](#common-issues--常见问题)
6. [Best Practices / 最佳实践](#best-practices--最佳实践)

---

## Quick Start / 快速开始

### Example 1: Process Single Vehicle / 处理单个车辆

The simplest way to process slope data for one vehicle:
处理单个车辆斜率数据的最简单方法：

```bash
cd C:\Users\31915\.claude\skills\vehicle-slope-data

python scripts/cli/process_slope.py \
  --vehicle-id V0001 \
  --input-dir "E:/Vehicle_Date/V0001/V0001_SLOPE"
```

**Expected Output / 预期输出：**
```
Processing vehicle V0001...
Processing LV component... Done (45 conditions)
Processing DCC component... Done (45 conditions)

Generated files:
  - E:/Vehicle_Date/V0001/V0001_SLOPE_output/data.json
  - E:/Vehicle_Date/V0001/V0001_SLOPE_output/report.xlsx
  - E:/Vehicle_Date/V0001/V0001_SLOPE_output/data.db
  - E:/Vehicle_Date/V0001/V0001_SLOPE_output/error_report.md

✓ Processing completed: 90 conditions, 0 failed
```

---

## Basic Examples / 基础示例

### Example 2: Custom Output Directory / 自定义输出目录

```bash
python scripts/cli/process_slope.py \
  --vehicle-id V0002 \
  --input-dir "E:/Vehicle_Date/V0002/V0002_SLOPE" \
  --output-dir "C:/Reports/V0002_SLOPE"
```

**Use case / 使用场景：**
- Save reports to a centralized location
- 将报告保存到集中位置
- Separate raw data from processed reports
- 将原始数据与处理后的报告分开

---

### Example 3: Process Multiple Components / 处理多个部件

```python
# Python script for processing specific components
# 处理特定部件的 Python 脚本

from config import SlopeConfigManager
from scripts.slope_processor import SlopeProcessor
import os

# Initialize / 初始化
config = SlopeConfigManager()
processor = SlopeProcessor(config)

# Vehicle info / 车辆信息
vehicle_id = "V0001"
input_base = "E:/Vehicle_Date/V0001/V0001_SLOPE"

# Components to process / 要处理的部件
components = ["LV", "DCC", "ACC", "PTC"]

# Process each component / 处理每个部件
for comp in components:
    comp_dir = os.path.join(input_base, comp)
    if os.path.exists(comp_dir):
        print(f"Processing {comp}...")
        results = processor.process_component(comp_dir, comp)
        print(f"  ✓ Processed {len(results)} conditions")
    else:
        print(f"  ✗ {comp} directory not found")
```

---

## Advanced Usage / 高级用法

### Example 4: Custom Configuration / 自定义配置

```python
# Use custom configuration directory
# 使用自定义配置目录

from config import SlopeConfigManager

# Load custom config / 加载自定义配置
custom_config = SlopeConfigManager("C:/custom/config/path")

# Use with processor / 与处理器一起使用
processor = SlopeProcessor(custom_config)
results = processor.process_vehicle("V0001", "E:/Vehicle_Date/V0001/V0001_SLOPE")
```

---

### Example 5: Accessing Processed Data / 访问处理后的数据

```python
import json
import pandas as pd
import sqlite3

output_dir = "E:/Vehicle_Date/V0001/V0001_SLOPE_output"

# Method 1: Read JSON / 方法1：读取 JSON
with open(f"{output_dir}/data.json", 'r', encoding='utf-8') as f:
    data = json.load(f)
    
print(f"Vehicle: {data['vehicle_id']}")
print(f"Total conditions: {data['total_conditions']}")

# Method 2: Read Excel / 方法2：读取 Excel
df = pd.read_excel(f"{output_dir}/report.xlsx", sheet_name="Conditions")
print(df.head())

# Method 3: Query SQLite / 方法3：查询 SQLite
conn = sqlite3.connect(f"{output_dir}/data.db")
cursor = conn.cursor()

# Get statistics for a component / 获取部件的统计信息
cursor.execute("""
    SELECT condition_name, max_slope, avg_slope 
    FROM conditions 
    WHERE component = 'LV'
""")
results = cursor.fetchall()

for row in results:
    print(f"{row[0]}: max={row[1]}, avg={row[2]}")

conn.close()
```

---

### Example 6: Error Handling / 错误处理

```python
from config import SlopeConfigManager
from scripts.slope_processor import SlopeProcessor
import os

try:
    # Initialize / 初始化
    config = SlopeConfigManager()
    processor = SlopeProcessor(config)
    
    # Process / 处理
    vehicle_id = "V0001"
    input_dir = "E:/Vehicle_Date/V0001/V0001_SLOPE"
    
    results = processor.process_vehicle(vehicle_id, input_dir)
    
    # Check results / 检查结果
    print(f"✓ Successfully processed {results['processed_conditions']} conditions")
    
    if results['failed_conditions']:
        print(f"⚠ Warning: {len(results['failed_conditions'])} conditions failed")
        for failed in results['failed_conditions']:
            print(f"  - {failed['component']}/{failed['condition']}: {failed['error']}")
    
    # Verify output files / 验证输出文件
    output_dir = f"{input_dir}_output"
    expected_files = ['data.json', 'report.xlsx', 'data.db']
    
    for filename in expected_files:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✓ {filename} generated ({size} bytes)")
        else:
            print(f"✗ {filename} missing!")
            
except FileNotFoundError as e:
    print(f"✗ File not found: {e}")
except PermissionError as e:
    print(f"✗ Permission denied: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
```

---

## Batch Processing / 批量处理

### Example 7: Process Multiple Vehicles / 处理多个车辆

```python
# batch_process.py
# 批量处理脚本

from config import SlopeConfigManager
from scripts.slope_processor import SlopeProcessor
import os

# Configuration / 配置
base_dir = "E:/Vehicle_Date"
vehicles = ["V0001", "V0002", "V0003", "V0004"]

# Initialize processor / 初始化处理器
config = SlopeConfigManager()
processor = SlopeProcessor(config)

# Process all vehicles / 处理所有车辆
for vehicle_id in vehicles:
    print(f"\n{'='*50}")
    print(f"Processing {vehicle_id}...")
    print(f"{'='*50}")
    
    input_dir = os.path.join(base_dir, vehicle_id, f"{vehicle_id}_SLOPE")
    
    if not os.path.exists(input_dir):
        print(f"✗ Input directory not found: {input_dir}")
        continue
    
    try:
        results = processor.process_vehicle(vehicle_id, input_dir)
        
        print(f"✓ Completed: {results['processed_conditions']} conditions")
        if results['failed_conditions']:
            print(f"⚠ Failed: {len(results['failed_conditions'])} conditions")
        
    except Exception as e:
        print(f"✗ Error processing {vehicle_id}: {e}")

print("\n✓ Batch processing completed!")
```

**Run the script / 运行脚本：**
```bash
python batch_process.py
```

---

### Example 8: Process Both Ripple and Slope / 同时处理纹波和斜率

```python
# process_both.py
# 同时处理纹波和斜率数据

import sys
import os

# Add ripple skill to path / 将纹波技能添加到路径
sys.path.insert(0, "C:/Users/31915/.claude/skills/vehicle-ripple-data")

from vehicle_ripple_data.scripts.core.vehicle_processor import VehicleProcessor
from vehicle_ripple_data.config import ConfigManager as RippleConfig
from config import SlopeConfigManager
from scripts.slope_processor import SlopeProcessor

vehicle_id = "V0001"
base_dir = "E:/Vehicle_Date/V0001"

# Process Ripple / 处理纹波
print("Processing Ripple data...")
ripple_config = RippleConfig()
ripple_processor = VehicleProcessor(ripple_config)
ripple_results = ripple_processor.process_vehicle(
    vehicle_id, 
    os.path.join(base_dir, f"{vehicle_id}_RIPPLE")
)
print(f"✓ Ripple: {ripple_results['processed_conditions']} conditions")

# Process Slope / 处理斜率
print("\nProcessing Slope data...")
slope_config = SlopeConfigManager()
slope_processor = SlopeProcessor(slope_config)
slope_results = slope_processor.process_vehicle(
    vehicle_id,
    os.path.join(base_dir, f"{vehicle_id}_SLOPE")
)
print(f"✓ Slope: {slope_results['processed_conditions']} conditions")

print("\n✓ Both data types processed successfully!")
```

---

## Common Issues / 常见问题

### Issue 1: "ModuleNotFoundError: No module named 'vehicle_ripple_data'"

**Problem / 问题：**
Slope skill depends on Ripple skill but can't find it.
斜率技能依赖纹波技能但找不到。

**Solution / 解决：**
```python
import sys
sys.path.insert(0, "C:/Users/31915/.claude/skills/vehicle-ripple-data")

# Now import will work / 现在导入可以工作了
from config import SlopeConfigManager
```

---

### Issue 2: Image paths not found / 图片路径未找到

**Problem / 问题：**
Statistics file references images but they're not found.
统计文件引用了图片但找不到。

**Check / 检查：**
```python
# Verify image exists / 验证图片存在
import os

image_path = "E:/Vehicle_Date/V0001/V0001_SLOPE/LV/condition_1.png"
if os.path.exists(image_path):
    print("✓ Image found")
else:
    print(f"✗ Image not found: {image_path}")
    print("Check if path is absolute in statistics file")
    print("检查统计文件中的路径是否为绝对路径")
```

---

### Issue 3: Condition matching failures / 工况匹配失败

**Problem / 问题：**
Some conditions can't be matched to standard names.
某些工况无法匹配到标准名称。

**Debug / 调试：**
```python
from scripts.condition_matcher import ConditionMatcher
from config import SlopeConfigManager

config = SlopeConfigManager()
matcher = ConditionMatcher()

# Test matching / 测试匹配
test_conditions = [
    "LV_斜率测试[工况1]",
    "DCC_Test_Condition_2",
    "Unknown Condition"
]

rules = config.get_matching_rules()

for cond in test_conditions:
    matched, method, confidence = matcher.match_condition(cond, "LV", rules)
    print(f"{cond} -> {matched} ({method}, confidence: {confidence:.2f})")
```

---

### Issue 4: Excel generation errors / Excel 生成错误

**Problem / 问题：**
Excel file generation fails.
Excel 文件生成失败。

**Common causes / 常见原因：**
1. File is open in Excel / 文件在 Excel 中打开
2. Permission denied / 权限被拒绝
3. Invalid template configuration / 模板配置无效

**Solution / 解决：**
```python
import os

output_file = "E:/Vehicle_Date/V0001/V0001_SLOPE_output/report.xlsx"

# Check if file is locked / 检查文件是否被锁定
if os.path.exists(output_file):
    try:
        os.rename(output_file, output_file + ".tmp")
        os.rename(output_file + ".tmp", output_file)
        print("✓ File is not locked")
    except PermissionError:
        print("✗ File is locked. Close Excel and try again.")
        print("✗ 文件被锁定。请关闭 Excel 后重试。")
```

---

## Best Practices / 最佳实践

### 1. Always use absolute paths / 始终使用绝对路径

```python
# Good / 好
input_dir = os.path.abspath("E:/Vehicle_Date/V0001/V0001_SLOPE")

# Bad / 不好
input_dir = "./data/V0001_SLOPE"  # May fail / 可能失败
```

### 2. Verify data before processing / 处理前验证数据

```python
# Check input directory exists / 检查输入目录是否存在
if not os.path.exists(input_dir):
    raise FileNotFoundError(f"Input directory not found: {input_dir}")

# Check for component directories / 检查部件目录
components = ["LV", "DCC", "ACC"]
for comp in components:
    comp_dir = os.path.join(input_dir, comp)
    if os.path.exists(comp_dir):
        print(f"✓ {comp} found")
    else:
        print(f"⚠ {comp} not found")
```

### 3. Handle encoding issues / 处理编码问题

```python
# When reading CSV files / 读取 CSV 文件时
import pandas as pd

# Try different encodings / 尝试不同编码
encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']

for encoding in encodings:
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        print(f"✓ Successfully read with {encoding}")
        break
    except UnicodeDecodeError:
        continue
```

### 4. Organize output / 组织输出

```python
# Create organized output structure / 创建有组织的输出结构
output_base = "C:/Reports"
vehicle_id = "V0001"
date_str = "2025-04-03"

output_dir = os.path.join(output_base, date_str, vehicle_id)
os.makedirs(output_dir, exist_ok=True)

# Process / 处理
processor.process_vehicle(vehicle_id, input_dir, output_dir)
```

### 5. Log processing details / 记录处理详情

```python
import logging
from datetime import datetime

# Setup logging / 设置日志
log_file = f"processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Log processing / 记录处理
logging.info(f"Starting processing for {vehicle_id}")
# ... processing code ...
logging.info(f"Completed: {results['processed_conditions']} conditions")
```

---

## See Also / 另请参阅

- [API Reference](api.md) - Complete API documentation / 完整 API 文档
- [README.md](../README.md) - Main documentation / 主文档
- [CHANGELOG.md](../CHANGELOG.md) - Version history / 版本历史
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guide / 贡献指南
