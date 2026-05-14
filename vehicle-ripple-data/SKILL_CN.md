---
name: vehicle-ripple-data
version: "4.3"
description: 整合和结构化车辆高压纹波测试数据以便下游分析和报告生成。当需要整合来自车辆组件（LV、ACC、DCC、PTC、ACCM、FAN、BATT、Vehicle Harness Splitter等）的测试结果图片和Excel统计数据到统一数据格式、生成标准化Excel报告时使用此技能。本技能可准备用于数据库构建的结构化数据，生成Excel汇总表格，自动创建中文error_report.md报告文档，并将所有输出文件组织到{VehicleID}_RIPPLE_output文件夹中。处理组件-通道映射、工况匹配、数据验证、SQLite数据库生成、Excel导出、中文错误报告生成和输出文件自动组织。
---

# 车辆高压纹波测试数据整合与报告生成

通过整合测试结果图片与Excel统计数据、应用工况映射规则、准备用于下游分析的统一数据、SQLite数据库构建和Excel报告生成来整合和结构化车辆纹波测试数据。

## 输入数据结构

### 分层文件夹结构

**用户应输入父文件夹**（例如: `E:\1 项目\V0001`），该文件夹包含：

```
E:\1 项目\V0001/                    # 父文件夹（用户输入）
├── vehicle_info.md                # 必需：车辆参数（父文件夹级别）
├── vehicle_info.xlsx              # 可选：Excel格式的车辆信息
├── setup.png                      # 可选：车辆设置照片（父文件夹级别）
├── setup.jpg                      # 可选：JPG格式的设置照片
├── test_naming_rules.md           # 可选：共享命名规则（父文件夹级别）
├── test_naming_rules.xlsx         # 可选：Excel格式的规则
├── sensor_naming_rules.md         # 可选：共享传感器规则（父文件夹级别）
├── sensor_naming_rules.xlsx       # 可选：Excel格式的规则
├── test_data/                     # 忽略：原始测试数据文件夹
├── V0001_RIPPLE/                  # RIPPLE数据文件夹（自动检测）
│   ├── FM_V/                      # 组件文件夹（前电驱电压）
│   │   ├── statistics.xlsx        # 统计数据
│   │   └── *.png                  # 结果图片
│   ├── RM_V/                      # 组件文件夹（后电驱电压）
│   ├── LV_V/                      # 组件文件夹（低压电压）
│   ├── LV_A/                      # 组件文件夹（低压电流）
│   ├── DCC_V/                     # 组件文件夹（直流充电电压）
│   ├── DCC_A/                     # 组件文件夹（直流充电电流）
│   └── ... (其他组件)
│   └── V0001_RIPPLE_output/       # 输出文件夹（在RIPPLE文件夹内创建）
│       ├── V0001_RIPPLE_summary.xlsx
│       ├── V0001_RIPPLE.db
│       ├── V0001_RIPPLE_data.json
│       ├── error_report.md        # 中文处理报告
│       └── .cache/                # 增量处理缓存
└── V0001_SLOPE/                   # 电压斜率SLOPE数据文件夹（由vehicle-slope-data技能处理）
```

**处理逻辑：**
1. 用户输入**父文件夹**（例如: `E:\1 项目\V0001`）
2. 技能**自动查找** `{VehicleID}_RIPPLE` 子文件夹
3. 技能从系统级SKILL存放路径的references文件夹中加载**命名规则**和**传感器规则**，也就是test_naming_rules.md和sensor_naming_rules.md，以这些文件内容为基准
4. 技能从父文件夹读取**必需文件**：`vehicle_info.md` 或 `vehicle_info.xlsx`（必需）
5. 技能从父文件夹读取**命名规则**，也就是test_naming_rules.md（可选，如果不存在则以系统级SKILL的**命名规则**为准；如果存在则是系统级SKILL的**命名规则**的补充）
6. 技能从父文件夹读取**传感器规则**，也就是sensor_naming_rules.md（可选，如果不存在则以系统级SKILL的**传感器规则**为准；如果存在则是系统级SKILL的**传感器规则**的补充）
7. 技能处理 `{VehicleID}_RIPPLE` 文件夹中的组件数据
8. 输出保存到 `{VehicleID}_RIPPLE/{VehicleID}_RIPPLE_output/`

**文件夹命名约定:**
- **父文件夹**: `{车辆ID}` (例如: `V0001`, `V0002`) 或任意自定义名称
- **RIPPLE子文件夹**: `{车辆ID}_RIPPLE` (例如: `V0001_RIPPLE`)
- **输出文件夹**: `{VehicleID}_RIPPLE_output`（在RIPPLE文件夹内创建）

**车辆ID提取逻辑:**
```python
def extract_vehicle_id_from_ripple_folder(folder_name):
    """从RIPPLE文件夹名称提取车辆ID"""
    if folder_name.endswith('_RIPPLE'):
        return folder_name[:-7]  # 移除 '_RIPPLE' 后缀
    return folder_name
```

**必需文件（来自父文件夹）:**
- **车辆信息**（`vehicle_info.md` 或 `vehicle_info.xlsx`）- 27个车辆参数

**可选文件（来自父文件夹）:**
- **测试命名规则**（`test_naming_rules.md` 或 `test_naming_rules.xlsx`）- 将工况名称映射到SOC等级
- **传感器命名规则**（`sensor_naming_rules.md` 或 `sensor_naming_rules.xlsx`）- 定义组件通道
- **设置照片**（`setup.png` 或 `setup.jpg`）- 用于报告的车辆照片

**RIPPLE文件夹内容:**
- **组件文件夹**（每个传感器通道一个，名称必须与sensor_naming_rules匹配）
  - 每个包含 `statistics.xlsx` 和 `.png` 结果图片

**规则优先级（从高到低）:**
1. 父文件夹规则（`E:\1 项目\V0001\test_naming_rules.md`）
2. 技能默认规则（`references/test_naming_rules.md`）

### 车辆信息（vehicle_info.md 或 vehicle_info.xlsx）

**必需字段**（从实际车辆数据中提取所有可用参数）：
- 车型、厂商、级别、能源类型
- 长*宽*高(mm)、轴距(mm)、轮距等
- 发动机参数（型号、排量、功率等）
- 电机参数（功率、扭矩等）
- 电池参数（类型、容量、续航里程等）
- 其他技术参数

**格式：**
- Markdown表格格式（推荐）
- 第一列为参数名称，第二列为参数值

### 测试命名规则（test_naming_rules.md 或 test_naming_rules.xlsx）

将测试工况名称映射到数据标识符。

**作用**：
- 提供condition_name（工况中文名称）
- 辅助验证condition_id格式（但从condition_id直接提取SOC）

**注意**：从condition_id直接提取SOC，test_naming_rules主要用于condition_name映射和验证。

### 传感器命名规则（sensor_naming_rules.md 或 sensor_naming_rules.xlsx）

定义组件通道及其描述。通道代码确定测量单位：
- **以`_A`结尾的代码**：电流测量（单位：A - 安培）
- **以`_V`结尾的代码**：电压测量（单位：V - 伏特）

**默认传感器**（24个通道）：
| 通道 | 组件描述 | 单位 |
|---------|----------|------|
| FM_V | 前电驱系统直流母线端电压 | V |
| FM_A | 前电驱系统直流母线端电流 | A |
| RM_V | 后电驱系统直流母线端电压 | V |
| RM_A | 后电驱系统直流母线端电流 | A |
| DCC_V | 动力电池直流充电端电压 | V |
| DCC_A | 动力电池直流充电端电流 | A |
| ACC_V | OBC输出端电压 | V |
| ACC_A | OBC输出端电流 | A |
| PTC_V | PTC输入端电压 | V |
| PTC_A | PTC输入端电流 | A |
| ACCM_V | 压缩机输入端电压 | V |
| ACCM_A | 压缩机输入端电流 | A |
| LV_V | 12V电池及前端冷却模块风扇的低压电压 | V |
| LV_A | 12V电池及前端冷却模块风扇的低压电流 | A |
| FAN_A | 前端冷却模块风扇的低压电流 | A |
| BATT_V | 动力电池电压 | V |
| BATT_A | 动力电池电流 | A |
| Vehicle_Harness_Splitter_V | 车辆分线器端的电压 | V |
| Vehicle_Harness_Splitter_A | 车辆分线器端的电流 | A |

### 组件文件夹内容

每个组件文件夹包含：
- `statistics.xlsx`：所有工况的测试指标
- `.png`文件：每个工况一个，按工况ID命名

**statistics.xlsx格式（标准7列）：**
| 列索引 | 列名 | 描述 |
|--------|------|------|
| 0 | 数据名称 | 工况标识符（如"87_超车80-140"）|
| 1 | 整段时域有效值 | 时域有效值 |
| 2 | 时域纹波VPP值（V）| 时域纹波VPP值 |
| 3 | 峰值排序 | 频谱峰值排序详情（文本）|
| 4 | 频域最大峰值频率(KHZ) | 频域峰值频率 |
| 5 | 频域最大峰值V/A | 频域峰值幅度 |
| 6 | 频域均方根值（rms）| 频域RMS |

**注意：** 由于编码问题，实际读取时建议使用列索引（iloc）而非列名。

**图片文件名格式：**
```
{condition_id}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}.{unit}.png

示例：
20_直流充电暖风_LV_V_1.28VPP_20.00kHz-0.003V.png
87_超车80-140_LV_V_8.39VPP_0.61kHz-0.106V.png
坡度10_32_匀速80冷风_LV_V_1.85VPP_3.94kHz-0.054V.png
```

解析为：
- `condition_id`: "87_超车80-140" 或 "坡度10_32_匀速80冷风"
- `channel`: "LV_V"（必须与组件文件夹名称匹配）
- `vpp`: "8.39VPP" → 8.39
- `freq`: "0.61kHz" → 0.61
- `amplitude`: "0.106V" → 0.106
- `unit`: "V" 或 "A"（由sensor_naming_rules确定）

---

## 关键注意事项

### 注意事项1：图片文件名解析
**这是导致空图片路径的常见原因。**

**图片文件名有两种格式**，需要不同的解析：

**标准格式：**
```
{SOC值}_{工况描述}_{通道}_{VPP值}VPP_{频率}kHz-{幅度}{单位}.png
```
- 示例: `20_直流充电暖风_ACCM_A_15.81VPP_24.06kHz-1.623A.png`
- 解析的 `condition_id`: `20_直流充电暖风`（**不是**仅 `20`）

**坡度工况格式（坡度工况）：**
```
坡度10_{SOC值}_{工况描述}_{通道}_{VPP值}VPP_{频率}kHz-{幅度}{单位}.png
```
- 示例: `坡度10_32_匀速80冷风_ACCM_A_46.78VPP_17.50kHz-1.631A.png`
- 解析的 `condition_id`: `坡度10_32_匀速80冷风`

需要把提取出的工况描述与test_naming_rules进行对应得到工况名称。

**验证：** 解析后，验证所有工况的 `image_info['condition_id'] == excel_condition_id`。任何不匹配都会导致空图片路径。

### 注意事项2：statistics.xlsx 编码问题
**这是实际处理中最常见的问题。**

**问题：**
- 许多 statistics.xlsx 文件使用 GBK 编码保存
- pandas 读取时中文字符显示为乱码（如 `数据名称` 显示为 `�ļ���`）
- 直接使用列名访问会导致 KeyError

**解决方案：**
1. **使用列索引而非列名访问数据**
   ```python
   # 不要这样做：
   condition_id = row['数据名称']  # 会失败，如果列名是乱码
   
   # 这样做：
   condition_id = str(row.iloc[0]).strip()  # 第0列：数据名称
   effective_value = row.iloc[1]             # 第1列：整段时域有效值
   vpp = row.iloc[2]                         # 第2列：时域纹波Vpp值
   peak_ranking = row.iloc[3]                # 第3列：峰值排序
   freq_khz = row.iloc[4]                    # 第4列：频域最大峰值频率
   peak_amp = row.iloc[5]                    # 第5列：频域最大峰值
   rms = row.iloc[6]                         # 第6列：频域均方根值
   ```

2. **标准7列顺序（即使列名乱码）**：
   - Column 0: 数据名称
   - Column 1: 整段时域有效值
   - Column 2: 时域纹波Vpp值（V）
   - Column 3: 峰值排序
   - Column 4: 频域最大峰值频率(KHZ)
   - Column 5: 频域最大峰值V/A
   - Column 6: 频域均方根值（rms）

### 注意事项3：命名规则的合并策略
**这是错误的常见来源 - 通过合并策略修复。**

**方法**：始终将父文件夹规则与默认规则合并
- **步骤1**：从技能参考文件夹加载完整的默认规则（54个测试工况、24个传感器通道）
- **步骤2**：检查父文件夹中的自定义规则 - 如果找到，将其合并（父文件夹规则优先）
- **结果**：保证完整的规则覆盖

### 注意事项4：验证所有组件文件夹
**不要在检查一个文件夹后就停止。**
- 扫描车辆文件夹并查找所有子目录
- 验证每个文件夹与sensor_naming_rules的匹配性
- 一次性报告所有无效文件夹，而不是仅报告第一个
- **重要性**：车辆可能有15+个组件文件夹。只检查一个意味着遗漏错误。

### 注意事项5：单位分配是确定性的
- 以`_A`结尾的通道代码 = 电流（单位：A）
- 以`_V`结尾的通道代码 = 电压（单位：V）
- 这是基于后缀自动确定的 - 无需猜测

### 注意事项6：中文编码处理至关重要
**所有输入文件包含中文字符，必须使用正确的编码读取。**
- **关键**：所有文件（vehicle_info、test_naming_rules、sensor_naming_rules、statistics.xlsx）包含中文文本
- **必须**使用UTF-8编码读取文件（首先尝试UTF-8，如失败则回退到GBK）
- **永远不要**假设为ASCII编码 - 这将损坏中文字符
- 写入输出时，始终使用UTF-8编码以正确保留中文文本
- **重要性**：编码不正确将导致中文文本乱码（如"坦克500"变成"����500"），使输出无法使用

### 注意事项7：SOC值提取
**statistics.xlsx中的工况ID直接包含SOC值。**

工况ID格式：`{SOC值}_{工况描述}` 或 `坡度10_{SOC值}_{工况描述}`（坡度工况）

示例：
- `87_超车80-140(运动模式)` → SOC = 87（≥70%）
- `26_超车80-140（运动模式）` → SOC = 26（≤40%）
- `坡度10_21_匀速80暖风（运动模式）` → SOC = 21（≤40%，带"坡度10_"前缀）

**正确提取逻辑（始终使用此）：**

```python
def extract_soc_from_condition_id(condition_id):
    """从condition_id提取SOC值 - 永远不要使用test_naming_rules提取SOC"""
    # 处理"坡度10_"前缀
    if condition_id.startswith('坡度10_'):
        condition_id = condition_id[5:]  # 移除"坡度10_"
    
    # 提取第一个数值
    match = re.match(r'(\d+)_.*', condition_id)
    if match:
        return int(match.group(1))
    return None

def get_soc_level(soc_value):
    """映射SOC值到SOC等级 - 始终使用此函数"""
    if soc_value is None:
        return "Unknown"
    elif soc_value >= 70:
        return "≥70%"
    elif soc_value >= 40:
        return "40%-70%"
    else:
        return "≤40%"

# 用法（对每个工况）：
soc_value = extract_soc_from_condition_id(condition_id)
soc_level = get_soc_level(soc_value)  # 这对有效数字始终有效！

# test_naming_rules仅用于工况名称查找，不是SOC等级！
condition_name = test_rules.get(condition_id, {}).get('condition_name', 
                                                       condition_id.split('_', 1)[1] if '_' in condition_id else condition_id)
```

**映射规则：**
- SOC ≥ 70% → "≥70%"
- 40% ≤ SOC < 70% → "40%-70%"
- SOC < 40% → "≤40%"

**关键规则：**
1. **始终直接从condition_id提取SOC** - 不要依赖test_naming_rules
2. **始终使用数值映射** - test_naming_rules仅用于工况名称
3. **永远不要为有效数字返回"Unknown"** - 20_xxx → "≤40%", 87_xxx → "≥70%"
4. **如果condition_id不在test_naming_rules中** - 仍然正确提取SOC，仅使用condition_id作为名称

### 注意事项8：工况名称映射
**工况名称必须从test_naming_rules.md的"工况名称"列查找，而非从condition_id提取。**

**问题：**
- condition_id格式：`87_超车80-140(运动模式)` 或 `20_直流充电暖风`
- 错误做法：提取描述部分 → "超车80-140" 或 "直流充电暖风"
- 正确做法：在test_rules中查找 → "超越加速" 或 "直流充电暖风"

**正确映射逻辑：**

```python
def get_condition_name(condition_id, test_rules):
    """从test_naming_rules查找获取工况名称"""
    # 首先尝试精确匹配
    if condition_id in test_rules:
        return test_rules[condition_id]['condition_name']
    
    # 尝试模糊匹配（处理括号差异）
    # 移除任何括号以进行匹配
    import re
    clean_id = re.sub(r'[()（）]', '', condition_id)
    
    for rule_id, rule_info in test_rules.items():
        clean_rule_id = re.sub(r'[()（）]', '', rule_id)
        if clean_id == clean_rule_id:
            return rule_info['condition_name']
    
    # 回退：从condition_id提取
    parts = condition_id.split('_', 1)
    if len(parts) > 1:
        return parts[1]
    return condition_id

# 用法：
condition_name = get_condition_name(condition_id, test_rules)
```

**预期结果：**
| condition_id | 错误（从ID提取） | 正确（从规则查找） |
|:-------------|:----------------|:-------------------|
| 坡度10_81_匀速80暖风（运动模式）| 匀速80暖风（运动模式）| 爬坡高温 |
| 87_超车80-140(运动模式) | 超车80-140(运动模式) | 超越加速 |
| 26_超车80-140（运动模式） | 超车80-140（运动模式） | 超越加速 |
| 20_直流充电暖风 | 直流充电暖风 | 直流充电暖风 |
| 90_停车D档热风 | 停车D档热风 | 静止高温 |

---

## 处理流程

### 步骤1：验证车辆文件夹并提取车辆ID

1. **从文件夹名称提取车辆ID：**
   - 如果文件夹名称以 `_RIPPLE` 结尾 → vehicle_id = folder_name 去掉 `_RIPPLE` 后缀
   - 否则 → vehicle_id = folder_name（传统格式）
   - 示例: `V0001_RIPPLE` → vehicle_id = `V0001`

2. **验证文件夹存在并包含必需文件：**
   - 检查指定的车辆文件夹是否存在
   - 验证至少包含: `vehicle_info.md` OR `vehicle_info.xlsx`

### 步骤2：加载命名规则（带中文编码）

**关键：所有命名规则文件包含中文文本，必须使用正确的编码（UTF-8或GBK）读取。**

**新规则加载策略：首先加载默认规则，然后与父文件夹规则合并。**

1. **测试命名规则** - **合并策略**：
   - **步骤1**：始终首先加载技能参考文件夹中的默认规则
   - **步骤2**：检查父文件夹中是否有自定义规则
     - 如果有 → 将父文件夹规则与默认规则合并（父文件夹规则优先）
     - 如果没有 → 按原样使用默认规则
   - 使用UTF-8编码读取markdown文件（回退到GBK）

2. **传感器命名规则** - **合并策略**：
   - **步骤1**：始终首先加载技能参考文件夹中的默认规则
   - **步骤2**：检查父文件夹中是否有自定义规则
     - 如果有 → 将父文件夹规则与默认规则合并
     - 如果没有 → 按原样使用默认规则

### 步骤3：加载车辆信息（带中文编码）

读取车辆信息文件（如果两个都存在则优先使用.md）：
- 首先使用UTF-8编码读取，如果失败则回退到GBK
- 解析markdown表格或读取Excel
- 提取vehicle_id和所有参数
- 在所有字段中**保留中文字符**（车型、混合动力系统等）

### 步骤4：发现并验证组件 - **必须验证所有文件夹**

1. **扫描车辆文件夹**查找所有子目录
2. **识别所有组件文件夹**
3. **验证每个文件夹**名称与sensor_naming_rules匹配
4. **验证最小组件数量**

### 步骤5：处理每个组件

对于每个有效的组件文件夹：

1. **加载统计数据（使用列索引访问）**
   - 读取 `statistics.xlsx`
   - **处理编码问题**：由于列名可能是乱码，使用 `row.iloc[0-6]` 访问数据
   - 标准7列顺序：数据名称、整段时域有效值、时域纹波VPP值、峰值排序、频域最大峰值频率、频域最大峰值、频域均方根值

2. **扫描并解析图片**
   - 查找所有`.png`文件
   - 解析文件名提取元数据（condition_id、VPP、频率、幅度）

3. **匹配工况**
   - 将statistics.xlsx中的condition_id与图片文件名匹配
   - 确保100%匹配率

4. **提取SOC和SOC等级**
   - 从condition_id提取SOC值
   - 映射到SOC等级（≥70%、40%-70%、≤40%）

5. **构建组件数据**
   - 包含所有工况及其详细测量值

### 步骤6：生成输出结构化数据

生成分层JSON数据结构。

---

## 输出选项

### 选项1：JSON输出

返回用于程序化使用的结构化JSON对象。

### 选项2：SQLite数据库

创建/追加到SQLite数据库，包含以下表结构：

```sql
-- vehicles表
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY,
  vehicle_model TEXT,
  vehicle_info TEXT
);

-- conditions表
CREATE TABLE conditions (
  condition_id TEXT PRIMARY KEY,
  condition_name TEXT,
  soc_level TEXT
);

-- components表
CREATE TABLE components (
  component_code TEXT PRIMARY KEY,
  component_name TEXT,
  unit TEXT
);

-- test_results表
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

### 选项3：Excel报告

生成包含多个工作表的标准化Excel汇总报告：

**工作表1：Vehicle Information（车辆信息）**
| Parameter | Value |
|-----------|-------|
| Vehicle ID | V0001 |
| Vehicle Model | 坦克500 Hi4-Z |
| ... | ... |

**工作表2：Component Summary（组件汇总）**
| Component Code | Component Name | Unit | Conditions Count |
|----------------|----------------|------|------------------|
| FM_V | 前电驱系统直流母线端电压(V) | V | 45 |
| RM_V | 后电驱系统直流母线端电压(V) | V | 45 |
| ... | ... | ... | ... |

**工作表3：Detailed Results（详细结果）**
| No. | Component | Unit | Condition ID | Condition Name | SOC Level | Time VPP | Freq Peak (kHz) | Freq Amplitude | Image Path |
|-----|-----------|------|--------------|----------------|-----------|----------|-----------------|----------------|------------|
| 1 | FM_V | V | 20_直流充电暖风 | 直流充电暖风 | ≤40% | 1.28 | 20.00 | 0.003 | ... |
| 2 | FM_V | V | 87_超车80-140 | 超越加速 | ≥70% | 15.20 | 0.92 | 0.814 | ... |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

## 报告生成

### Excel报告生成

**使用示例：**
```python
from scripts.generate_excel_report import generate_excel_report
import json

# 加载处理后的JSON数据
with open('V0001_RIPPLE_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 生成Excel报告
generate_excel_report(data, 'V0001_RIPPLE_summary.xlsx')
```

### 中文错误报告生成 (error_report.md)

**自动生成在处理完成后：**

```python
from scripts.generate_error_report_cn import generate_error_report_cn

# 在{VehicleID}_RIPPLE_output文件夹中生成中文错误报告
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

**报告结构：**
```markdown
# Vehicle Ripple Data Processing Report

**Generated**: 2025-03-23 14:30:00
**Version**: 4.3

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
- **Name**: 前电驱系统直流母线端电压(V)
- **Unit**: V
- **Conditions**: 45

### RM_V
- **Name**: 后电驱系统直流母线端电压(V)
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

## 英文版本

查看 `SKILL.md` 获取完整的英文技能文档。
