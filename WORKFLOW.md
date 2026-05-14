# 车辆纹波/斜率测试数据处理完整工作流规划书

**版本**: V3.6
**更新日期**: 2026-05-11
**状态**: v1.4 整改完成 — 数据库迁移 + 原子性 + 部分失败 + 二次规划 + UTC 时间戳 (R6 复审通过)
**适用范围**: 车辆高压纹波与电压斜率测试数据的采集、整合、管理与报告生成

---

## 目录

1. [工作流总览](#一工作流总览)
2. [阶段1: 原始数据分析 (AutoHandleFiles)](#二阶段1-autohandlefiles--原始数据分析)
3. [阶段2: 数据整合 (ripple-data / slope-data)](#三阶段2-数据整合)
4. [阶段2.5: 跨阶段数据一致性校验](#四阶段25-跨阶段数据一致性校验)
5. [阶段3: 报告生成 (report-generation)](#五阶段3-报告生成)
6. [阶段4: 数据统一管理 (vehicle-database)](#六阶段4-数据统一管理)
7. [增量处理引擎 (workflow-orchestrator)](#七增量处理引擎)
8. [工况规则版本管理](#八工况规则版本管理)
9. [文件夹结构规范](#九文件夹结构规范)
10. [完整执行流程](#十完整执行流程)
11. [五个技能CLI命令完全参考](#十一五个技能cli命令完全参考)
12. [数据映射与编码规范](#十二数据映射与编码规范)
13. [已知问题与解决方案](#十三已知问题与解决方案)
14. [技术栈汇总](#十四技术栈汇总)
15. [待完善事项与版本历史](#十五待完善事项与版本历史)

---

## 一、工作流总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    车辆纹波/斜率测试数据处理完整工作流                          │
└─────────────────────────────────────────────────────────────────────────────┘

  Dewesoft .dmd 原始数据
           │
           ▼
  ┌─────────────────────────────────┐
  │  阶段1: AutoHandleFiles         │  ← PySide6 GUI, pyDmdReader, scipy
  │  纹波分析 + 斜率分析 + 滤波 + FFT │
  └─────────────────────────────────┘
           │
           ├──→ {VehicleID}_RIPPLE/   ──→ 7列statistics.xlsx + 每工况1张.png
           │                           ──→ 多个标准通道（数量视项目而定）
           │
           └──→ {VehicleID}_SLOPE/    ──→ 4列statistics.xlsx (斜率统计)
                                       ──→ 同上，多个标准通道
           │
           ▼
  ┌──────────────────────────────────────────────────────────┐
  │  阶段2: 数据整合技能 (+ 规则版本管理)                      │
  │  vehicle-ripple-data / vehicle-slope-data                  │
  │  命名规则: 默认规则 ←→ 父文件夹规则 (合并覆盖)              │
  └──────────────────────────────────────────────────────────┘
           │
           ├──→ {VehicleID}_RIPPLE_output/
           │    ├── {VehicleID}_RIPPLE_summary.xlsx
           │    ├── {VehicleID}_RIPPLE.db
           │    ├── {VehicleID}_RIPPLE_data.json
           │    └── error_report.md
           │
           └──→ {VehicleID}_SLOPE_output/
                ├── {VehicleID}_SLOPE_summary.xlsx
                ├── {VehicleID}_SLOPE.db
                ├── {VehicleID}_SLOPE_data.json
                └── error_report.md
           │
           ▼
  ┌─────────────────────────────────┐
  │  阶段2.5: 跨阶段数据一致性校验     │  ← 自动执行，兼容策略(不阻断)
  │  validate_cross_format.py        │
  │  校验 JSON / SQLite / Excel 一致性 │
  └─────────────────────────────────┘
           │ (校验失败写入 error_report.md 首行，流程继续)
           │
           ├──→ [可选] --auto-report 自动触发阶段3报告生成
           │     vehicle_skills_cli.py process V0001 --auto-report
           │     或 batch --scan F:/Vehicle_Date --auto-report
           │
           ▼
  ┌─────────────────────────────────┐
  │  阶段3: 报告自动生成              │  ← python-docx, openpyxl
  │  vehicle-report-generation        │
  │  按SOC分组 → 填充表格 → 插入图片    │
  │  (可自动触发或手动执行)            │
  └─────────────────────────────────┘
           │
           ├──→ {VehicleID}_RIPPLE_REPORT_{ComponentCode}.docx
           └──→ {VehicleID}_SLOPE_REPORT_{ComponentCode}.docx
           │
           ▼
  ┌─────────────────────────────────┐
  │  阶段4: 统一数据库管理            │  ← sqlite3, click CLI
  │  vehicle-database                 │
  │  多格式聚合 → 统一SQLite数据库      │
  └─────────────────────────────────┘
           │
           └──→ F:/Vehicle_Database/
                ├── Ripple.db  (纹波数据库: vehicles/components/test_conditions/ripple_results)
                └── Slope.db   (斜率数据库: vehicles/components/test_conditions/slope_results)

  ═══════════════════════════════════════════════════════════════════════════
  │  增量处理引擎 (workflow-orchestrator)  ← 跨阶段协调，避免重复计算         │
  │  缓存文件: {VehicleID}/.workflow_cache.json                              │
  │  功能: 指纹比对 → 决策需执行阶段 → 自动调用CLI → 更新缓存                │
  ═══════════════════════════════════════════════════════════════════════════
```

### 各阶段职责边界

| 阶段 | 职责 | 不做什么 |
|------|------|----------|
| **阶段1** | 从.dmd原始数据计算纹波/斜率，生成统计Excel和图片 | 不做工况映射、不做SOC分级、不做数据整合 |
| **阶段2** | 整合统计Excel+图片，映射工况名，SOC分级，生成统一格式 | 不读取.dmd、不做信号处理 |
| **阶段2.5** | 自动校验阶段2输出的JSON/SQLite/Excel一致性 | 不修改数据、不阻断后续流程 |
| **阶段3** | 读取阶段2/4输出，按模板生成Word检测报告 | 不修改源数据、不重新计算纹波/斜率 |
| **阶段4** | 聚合多车辆数据到统一数据库，提供查询/导出CLI | 不生成图片、不做统计分析 |
| **自动触发** | `vehicle_skills_cli.py --auto-report` 在阶段2.5后自动调用阶段3 | 不替代手动 `vehicle_report_cli.py` 命令 |
| **增量引擎** | 跨阶段协调，指纹比对决定重跑范围 | 不替代各阶段核心逻辑 |

---

## 二、阶段1: AutoHandleFiles — 原始数据分析

### 2.1 软件架构

AutoHandleFiles 是基于 PySide6 的桌面应用，打包为 PyInstaller 单文件可执行程序。

```
AutoHandleFiles.exe (PyInstaller, Python 3.8)
    │
    ├── PYZ-00.pyz (压缩的Python库)
    │   ├── src/AutoHandleFiles.pyc      ← PySide6 MainWindow GUI
    │   ├── src/dmd_process.pyc          ← 核心处理引擎 (~1300行)
    │   ├── src/signal_filter.pyc        ← 数字滤波器 (Butterworth/Bessel)
    │   ├── src/function_filter.pyc      ← 异常值过滤 (Hampel等)
    │   └── pyDmdReader/                 ← Dewesoft .dmd读取库
    │
    └── _internal/
        └── dmd_reader_api.dll           ← Dewesoft原生读取接口
```

### 2.2 核心处理引擎 (dmd_process)

**主要方法:**

| 方法 | 功能 |
|------|------|
| `calculateChannel()` | 主入口：遍历通道，调度纹波/斜率计算 |
| `generateOverViewImage()` | 生成时域波形总览图 (datashader渲染百万点) |
| `generateFFTImage()` | 生成FFT频谱图 (scipy.signal.stft) |
| `generateVppImage()` | 生成VPP(峰峰值)分布图 |
| `generateVoltageSlopeImage()` | 生成电压斜率分析图 |
| `getMinMaxSegdatas_and_mmap()` | 大文件内存映射分块读取 |
| `process_segment()` | 单段数据处理 (滤波 → FFT → 统计) |

**信号处理管线:**

```
.dmd原始数据
    │
    ├──→ pyDmdReader读取 → numpy数组
    │
    ├──→ 信号滤波 (可选)
    │    ├── Butterworth低通/高通/带通
    │    └── Bessel低通/高通/带通
    │
    ├──→ 异常值处理 (可选)
    │    ├── 顶百分比置零
    │    └── Hampel滤波
    │
    ├──→ 纹波分析路径
    │    ├── 时域分析: VPP(峰峰值), 有效值
    │    ├── FFT频谱分析: 峰值频率, 峰值幅度, RMS
    │    └── 输出: statistics.xlsx (7列) + 每工况一张.png
    │
    └──→ 斜率分析路径
         ├── 计算dV/dt (电压变化率)
         └── 输出: statistics.xlsx (4列: 最大/最小/绝对值最大)
```

### 2.3 输出数据结构

#### 纹波输出 ({VehicleID}_RIPPLE/)

每个组件文件夹包含:
- `statistics.xlsx` — 7列统计表
- `*.png` — 每个工况一张结果图

**statistics.xlsx 格式 (纹波):**

| 列索引 | 列名 | 说明 | 单位 |
|:------:|:-----|:-----|:----:|
| 0 | 数据名称 | 工况标识符，如 `87_超车80-140(运动模式)` | — |
| 1 | 整段时域有效值 | 信号的RMS有效值 | V/A |
| 2 | 时域纹波VPP值（V）| 峰峰值 (Peak-to-Peak) | V/A |
| 3 | 峰值排序 | 频谱峰值排序详情 (文本) | — |
| 4 | 频域最大峰值频率(KHZ) | FFT频谱中最大峰值对应的频率 | kHz |
| 5 | 频域最大峰值V/A | 该频率处的幅度值 | V/A |
| 6 | 频域均方根值（rms）| 频域RMS | V/A |

**图片文件名格式 (两种):**

```
标准格式:
  {SOC}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
  例: 87_超车80-140_LV_V_8.39VPP_0.61kHz-0.106V.png

坡度格式:
  坡度10_{SOC}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
  例: 坡度10_32_匀速80冷风_LV_V_1.85VPP_3.94kHz-0.054V.png
```

**图片文件名解析注意事项 (V3.5 新增):**
- **Ipp/Vpp 标记检测**: 支持 `Ipp`/`Vpp`/`ipp`/`vpp` 标准标记，同时兼容非标准标记 `xpp`/`Xpp` (如 `0.70xpp`)
- **首尾空格处理**: 文件名末尾空格（如 `0.010A .png`）会被自动去除，避免 condition_id 匹配失败
- **condition_id 提取**: 从图片文件名 `stem` 中提取 `channel` 标记（Ipp/Vpp/xpp）之前的全部内容作为 condition_id

#### 斜率输出 ({VehicleID}_SLOPE/)

每个组件文件夹包含:
- `statistics.xlsx` — 4列统计表
- `*.png` (可选) — 斜率分析图，如存在会被阶段2扫描

**statistics.xlsx 格式 (斜率):**

| 列索引 | 列名 | 说明 | 单位 |
|:------:|:-----|:-----|:----:|
| 0 | 文件名 | 工况标识符 | — |
| 1 | 斜率最大值(V/s) | 最大上升斜率 | V/s |
| 2 | 斜率最小值(V/s) | 最大下降斜率 (负值) | V/s |
| 3 | 斜率绝对值最大值(V/s) | 斜率绝对值的最大值 | V/s |

**斜率图片格式 (可选):**
```
{condition_id}_{component_code}.png
例: 87_超车80-140_FM_V.png
```

> **注意**: 斜率图片匹配通过 `_{component_code}` 后缀识别，不依赖 Ipp/Vpp/xpp 标记。
> V3.5 防御性修复：对 `img_stem` 做 `.strip()` 去除首尾空格，预防未来类似的空格问题。

### 2.4 已知问题与改进建议

| 问题 | 现象 | 根因 | 改进建议 |
|------|------|------|----------|
| 大文件MemoryError | 处理大.dmd时程序崩溃 | numpy内存映射策略不足 | 优化`getMinMaxSegdatas_and_mmap`分块大小 |
| 临时文件清理冲突 | WinError 32文件被占用 | ThreadPoolExecutor多线程竞争 | 加文件锁或串行清理 |
| .temp子目录未创建 | FileNotFoundError | 目录创建与写入竞态 | 先`os.makedirs(..., exist_ok=True)`再写入 |
| 部分dmd损坏 | FILE_INVALID错误 | 采集中断或传输损坏 | 增加文件头校验，跳过损坏文件 |
| 多线程异常吞没 | 某些通道无输出但无报错 | QThread异常未传播到主线程 | 增加异常回调和日志记录 |

---

## 三、阶段2: 数据整合

### 3.1 输入规范

**必须文件 (从父文件夹读取):**

| 文件 | 格式 | 必填 | 说明 |
|------|------|:----:|------|
| `vehicle_info.md` | Markdown表格 | 是 | 车辆参数（数量视文件内容而定） |
| `vehicle_info.xlsx` | Excel | 备选 | vehicle_info.md的替代 |

**可选文件 (从父文件夹读取，默认规则兜底):**

| 文件 | 格式 | 说明 |
|------|------|------|
| `test_naming_rules.md` | Markdown表格 | 工况名称映射规则 |
| `sensor_naming_rules.md` | Markdown/YAML | 通道代码定义 |
| `setup.png/jpg` | 图片 | 车辆照片 |

**规则加载优先级 (从高到低):**
1. 父文件夹自定义规则 (如 `V0001/test_naming_rules.md`)
2. 技能默认规则 (`references/test_naming_rules.md`)
3. 合并策略: 先加载默认规则全集，再用父文件夹规则覆盖

### 3.2 vehicle-ripple-data (纹波数据整合)

#### 处理流程

```
1. 验证父文件夹 → 提取VehicleID
2. 自动发现 {VehicleID}_RIPPLE/ 子文件夹
3. 加载命名规则 (默认+父文件夹合并)
4. 加载车辆信息 (UTF-8 → GBK回退)
5. 扫描所有组件文件夹 → 逐个验证通道名
6. 对每个组件:
    ├── 读取 statistics.xlsx (用 iloc[0-6], 不用列名)
    ├── 扫描 .png 文件 → 解析文件名提取元数据
    ├── 匹配 condition_id (Excel ↔ 图片)
    ├── 从 condition_id 提取SOC → 分级
    ├── 模糊匹配工况名称
    └── 构建结构化数据
7. 输出: Excel + SQLite + JSON + error_report.md
```

#### 关键处理逻辑

**A. 编码处理 (极重要)**

```python
# 读取含中文文件
for encoding in ['utf-8', 'gbk']:
    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
        break
    except UnicodeDecodeError:
        continue

# 读取statistics.xlsx (列名可能乱码)
condition_id    = str(row.iloc[0]).strip()   # 不用 row['数据名称']
effective_value = row.iloc[1]
vpp             = row.iloc[2]
peak_ranking    = row.iloc[3]
freq_khz        = row.iloc[4]
peak_amp        = row.iloc[5]
rms             = row.iloc[6]
```

**B. SOC提取 (必须直接从condition_id提取，不可依赖test_naming_rules)**

```python
# 模块级正则模式（定义在类外部，编译一次复用）
_SLOPE_PREFIX_PATTERN = re.compile(
    r'^(坡度|�¶�)\s*10(?![0-9])[_\-\s]*(\d+)[_\-\s]',
    re.IGNORECASE
)
_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')

def _normalize_condition_id(self, condition_id: str) -> str:
    """规范化 condition_id，处理 GBK 乱码坡度前缀

    GBK编码下"坡度"可能被读取为乱码(如�¶�)，需统一替换为标准前缀，
    确保xlsx中的condition_id与图片文件名中的condition_id能够匹配。
    """
    if not condition_id:
        return condition_id
    return re.sub(r'^�¶�\s*10(?![0-9])', '坡度10', condition_id)

def _extract_soc(self, condition_id: str) -> Optional[int]:
    """从 condition_id 中提取 SOC 值

    支持的分隔符: _ (下划线), - (短横线), 空格
    支持的标准格式:
      - 普通工况: 55_直流充电暖风 → SOC=55
      - 坡度工况: 坡度10_82_匀速80暖风 → SOC=82
      -  dash分隔: 55-直流充电暖风 → SOC=55
      - 空格分隔: 55 直流充电暖风 → SOC=55
    支持的GBK乱码:
      - �¶�10_82_匀速80暖风 → SOC=82 (经 _normalize_condition_id 处理后)
    """
    if not condition_id:
        return None

    normalized = self._normalize_condition_id(condition_id)

    # 处理坡度10_前缀（支持标准前缀、GBK乱码、多种分隔符）
    slope_match = _SLOPE_PREFIX_PATTERN.match(normalized)
    if slope_match:
        soc = slope_match.group(2)
        return int(soc) if soc else None

    # 普通工况：提取开头的数字SOC（支持_、-、空格分隔符）
    soc_match = _SOC_PATTERN.match(normalized)
    if soc_match:
        return int(soc_match.group(1))

    return None

def get_soc_level(soc):
    if soc is None:      return "Unknown"
    elif soc >= 70:      return ">=70%"
    elif soc >= 40:      return "40%-70%"
    else:                return "<=40%"
```

**C. 工况名称模糊匹配 (四级策略)**

| 级别 | 策略 | 适用场景 | 示例 |
|:----:|------|----------|------|
| 1 | 精确匹配 | condition_id完全一致 | `87_超车80-140(运动模式)` → `超越加速` |
| 2 | 归一化匹配 | 括号差异 `()` vs `（）` | `87_超车80-140（运动模式）` → `超越加速` |
| 3 | 模糊匹配 | Levenshtein距离<阈值 | `87_超车80-140运动模式` → `超越加速` |
| 4 | 特征匹配 | 提取关键词+SOC+坡度标志 | `�¶�10_81_匀速80暖风` (GBK乱码) → `爬坡高温` |

**特征提取支持的分隔符 (V3.5 更新):**

```python
def _extract_features(self, condition_id: str) -> Dict[str, Any]:
    """提取 condition_id 的特征用于模糊匹配"""
    working_id = condition_id

    # 1. 处理坡度前缀（支持标准、GBK乱码、多种分隔符）
    slope_match = _SLOPE_PREFIX_PATTERN.match(working_id)
    is_slope = slope_match is not None
    if slope_match:
        working_id = working_id[slope_match.end():]

    # 2. 提取 SOC（支持 _、-、空格 三种分隔符）
    soc_match = re.match(r'^(\d+)[_\-\s](.*)', working_id)
    if soc_match:
        soc = soc_match.group(1)
        working_id = soc_match.group(2)  # 去掉SOC后的描述部分
    else:
        soc = None

    # 3. 提取关键词（从描述部分）
    keywords = self._extract_keywords(working_id)

    return {
        'soc': soc,
        'is_slope': is_slope,
        'keywords': keywords,
        'original': condition_id
    }
```

**D. 图片文件名解析 (两种格式)**

```python
# 标准格式: {SOC}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amp}{unit}.png
# 坡度格式: 坡度10_{SOC}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amp}{unit}.png
# condition_id = 文件名中channel标记(Ipp/Vpp/xpp)之前的全部内容
```

**解析逻辑 (V3.5 更新):**

```python
def _parse_image_filenames(self, img_dir: Path) -> List[Dict[str, Any]]:
    """解析图片文件名，提取 condition_id 和测量元数据"""
    result = []
    for img_file in sorted(img_dir.glob('*.png')):
        # 1. 去掉首尾空格（处理 "0.010A .png" 这类末尾有空格的文件名）
        img_stem = img_file.stem.strip()

        # 2. 按 _ 分割文件名
        parts = img_stem.split('_')

        # 3. 查找 Ipp/Vpp/xpp 标记位置，确定 channel 边界
        marker_index = -1
        for i, part in enumerate(parts):
            if any(marker in part for marker in ('Ipp', 'Vpp', 'ipp', 'vpp', 'xpp', 'Xpp')):
                marker_index = i
                break

        if marker_index == -1:
            # 未找到标记，记录警告并跳过
            continue

        # 4. 提取 condition_id = channel标记之前的全部内容
        condition_parts = parts[:marker_index]
        condition_id = '_'.join(condition_parts)

        # 5. 提取 channel（标记位置的前一个 part）
        channel = parts[marker_index - 1] if marker_index > 0 else ''

        # ... 继续解析频率、幅度等元数据
        result.append({
            'condition_id': condition_id,
            'channel': channel,
            'file_path': str(img_file),
            # ... 其他元数据
        })

    return result
```

**关键改进:**
| 改进点 | 说明 |
|--------|------|
| `.strip()` 处理 | 去除文件名首尾空格，避免 `"18_停车D档冷风_ACCM_A"` 与 `"18_停车D档冷风_ACCM_A "` 不匹配 |
| `xpp`/`Xpp` 支持 | 扩展标记检测，兼容非标准单位标记 `xpp` |
| 分隔符容错 | condition_id 内部仍使用 `_` 连接，但 SOC 提取阶段支持 `_`/`-`/`空格` 三种分隔符 |

#### 输出文件

| 文件 | 说明 |
|------|------|
| `{VehicleID}_RIPPLE_summary.xlsx` | 3个Sheet: 车辆信息/组件汇总/详细结果 |
| `{VehicleID}_RIPPLE.db` | SQLite数据库: vehicles/components/conditions/test_results |
| `{VehicleID}_RIPPLE_data.json` | 完整结构化JSON，含所有测量数据 |
| `error_report.md` | 中文处理报告，记录成功/警告/错误 |

#### SQLite Schema (纹波)

```sql
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY,
  vehicle_model TEXT,
  vehicle_info TEXT  -- JSON字符串存储完整27个参数
);

CREATE TABLE components (
  component_code TEXT PRIMARY KEY,
  component_name TEXT,
  unit TEXT
);

CREATE TABLE conditions (
  condition_id TEXT PRIMARY KEY,
  condition_name TEXT,
  soc_level TEXT
);

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

### 3.3 vehicle-slope-data (斜率数据整合)

#### 与纹波数据的关键差异

| 维度 | vehicle-ripple-data | vehicle-slope-data |
|------|:-------------------:|:------------------:|
| 文件夹后缀 | `_RIPPLE` | `_SLOPE` |
| statistics列数 | 7列 | 4列 |
| 图片文件 | **必须** (每工况1张) | **可选** (存在则扫描匹配) |
| 数据单位 | V / A | V/s |
| 数据库表名 | `test_results` | `slope_results` |
| Excel详细列 | 时域VPP/频域峰值/RMS | 斜率Max/Min/Abs |

#### 处理流程

与纹波基本相同，差异点:
1. 读取statistics.xlsx时验证4列格式
2. 图片为可选: 若存在 `{condition_id}_{component_code}.png` 则扫描匹配
3. 数据字段映射到 slope_max / slope_min / slope_max_abs

#### SQLite Schema (斜率)

```sql
-- vehicles, components, conditions 表与纹波相同

CREATE TABLE slope_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vehicle_id TEXT,
  component_code TEXT,
  condition_id TEXT,
  slope_max REAL,
  slope_min REAL,
  slope_max_abs REAL,
  unit TEXT DEFAULT 'V/s',
  image_path TEXT,  -- 可选，如存在图片则记录路径
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
  FOREIGN KEY (component_code) REFERENCES components(component_code),
  FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
);
```

---

## 四、阶段2.5: 跨阶段数据一致性校验

### 4.1 功能定位

在阶段2 (vehicle-ripple-data / vehicle-slope-data) 处理完成后、阶段3报告生成前，自动执行跨格式数据一致性校验。校验 JSON / SQLite / Excel 三份输出的一致性，确保数据在整合过程中未发生丢失或错误。

**兼容策略**: 校验失败不阻断后续阶段执行，仅将错误报告插入到 `error_report.md` 的最顶部作为醒目标识。由用户自行判断是否修复后重跑阶段2。

### 4.2 校验项

| 校验项 | 级别 | 说明 |
|:-------|:----:|:-----|
| 文件存在性 | error | JSON / SQLite / Excel 文件是否存在且非空 |
| 记录总数一致性 | error | 三份文件的记录数是否一致 |
| 组件数量一致性 | error | 三份文件包含的组件通道数是否一致 |
| 车辆ID一致性 | error | 三份文件中的 vehicle_id 是否匹配 |
| 工况覆盖一致性 | error | JSON 与 Excel 的工况条目是否一一对应 |
| 图片路径覆盖率 | warning | 带图片路径的记录占比（纹波≥90%，斜率≥30%） |
| 数值精度一致性 | warning | 抽样对比 JSON 与 Excel 的数值差异（阈值>0.01） |
| SOC分级分布 | warning | SOC分布是否均衡（单一区间占比<90%） |
| 工况匹配置信度 | warning | 低置信度(<0.8)工况占比<10% |

### 4.3 使用方式

**自动触发**: `vehicle_skills_cli.py process` 在阶段2处理成功后自动调用

**手动执行**:
```bash
cd ~/.claude/skills/vehicle-ripple-data/scripts
python validate_cross_format.py --vehicle-id V0001 --output-dir F:/Vehicle_Date/V0001/V0001_RIPPLE/V0001_RIPPLE_output --type ripple
python validate_cross_format.py --vehicle-id V0001 --output-dir F:/Vehicle_Date/V0001/V0001_SLOPE/V0001_SLOPE_output --type slope
```

| 参数 | 说明 |
|------|:-----|
| `--vehicle-id` | 车辆ID |
| `--output-dir` | 阶段2输出目录 |
| `--type` | `ripple` 或 `slope` (默认: ripple) |
| `--strict` | 严格模式: 警告也视为失败 |

### 4.4 输出

校验结果写入 `{output_dir}/error_report.md` 首行:
```markdown
# 纹波跨阶段数据一致性校验报告

**校验时间**: 2026-04-25T10:30:00
**校验结果**: 发现问题 (见下方详情)

> **注意**: 本校验仅用于提示，不阻断后续阶段执行...

### 错误项
- **记录总数一致性**: 记录数: JSON=54, SQLite=54, Excel=0 ✗ 不一致!

### 通过的校验项
- **车辆ID一致性**: 车辆ID: JSON=V0001, SQLite=V0001, 期望=V0001
```

---

## 五、阶段3: 报告生成 (report-generation)

### 5.1 功能定位

读取阶段2生成的Excel/SQLite数据 + 原始图片，生成符合检测标准的Word (.docx) 报告。

### 5.2 报告模板结构
每个通道生成一份独立报告，包含:

```
报告标题: {VehicleID} 纹波/斜率检测报告 — {ComponentName}

├── 第1章: SOC ≥ 70% 区间数据
│   ├── 检验结果表格 (9个检验项目)
│   └── 试验数据曲线 (16组图片+图注)
│
├── 第2章: SOC 40%-70% 区间数据
│   ├── 检验结果表格
│   └── 试验数据曲线
│
└── 第3章: SOC ≤ 40% 区间数据
    ├── 检验结果表格
    └── 试验数据曲线
```

### 5.3 检验项目映射 (9项检验)
| 序号 | 检验项目 | 工况一 | 工况二 | 工况三 |
|:----:|:---------|:-------|:-------|:-------|
| 1 | 停车D档工况 | 静止低温 | 静止高温 | — |
| 2 | 急加速工况 | 零百加速 | 多次加速 | — |
| 3 | 匀速工况 | 匀速低温 | 匀速高温 | — |
| 4 | 超车工况 | 超越加速 | — | — |
| 5 | 滑行工况 | D档滑行 | — | — |
| 6 | 紧急制动工况 | 紧急制动 | — | — |
| 7 | 爬坡工况 | 爬坡 | 爬坡低温 | 爬坡高温 |
| 8 | 停车充电 | 直流充电冷风 | 直流充电暖风 | — |
| 9 | 停车充电 | 交流充电冷风 | 交流充电暖风 | — |

### 5.4 通道类型自动识别

报告生成器根据 `component_code` 后缀自动判断通道类型，动态切换单位和描述：

| 通道后缀 | 类型 | 纹波单位 | 纹波阈值 | 斜率单位 | 标准要求列转换 |
|:--------:|:----:|:--------:|:--------:|:--------:|:-------------|
| `_A` | 电流 | App | 100App | A/s | "电压纹波"→"电流纹波"，"30Vpp"→"100App" |
| `_V` | 电压 | Vpp | 30Vpp | V/s | 保持原文 |

实现位置: `vehicle-report-generation/scripts/core/ripple_report.py` / `slope_report.py`

### 5.5 数据读取策略
```
优先读取Excel:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE_summary.xlsx
    或
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE_summary.xlsx

Excel读取失败 → 回退到SQLite:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE.db
    或
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE.db
```

### 5.6 CLI命令参考
```bash
# 生成全部报告 (纹波+斜率, 所有通道)
python vehicle_report_cli.py generate V0006

# 仅生成纹波报告
python vehicle_report_cli.py generate V0006 --type ripple

# 仅生成斜率报告
python vehicle_report_cli.py generate V0006 --type slope

# 指定通道
python vehicle_report_cli.py generate V0005 --type ripple --component ACC_A
```

### 5.7 输出路径
```
# 纹波报告
{base_dir}/{VehicleID}/{VehicleID}_RIPPLE/{VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE_REPORT_{ComponentCode}.docx

# 斜率报告
{base_dir}/{VehicleID}/{VehicleID}_SLOPE/{VehicleID}_SLOPE_output/{VehicleID}_SLOPE_REPORT_{ComponentCode}.docx
```

---

## 六、阶段4: 数据统一管理 (vehicle-database)

### 6.1 功能定位
将分散的各车辆 `_RIPPLE_data.json` / `_SLOPE_data.json` / `.db` / `_summary.xlsx` 聚合到 `Ripple.db` + `Slope.db` 双库中，支持跨车辆查询、统计分析和数据导出。

### 6.2 数据源自动检测

`add` 命令自动检测以下格式的数据源（无优先级，全部导入）：

| 格式 | 文件模式 | 说明 |
|:----:|:---------|:-----|
| JSON | `*_RIPPLE_data.json`, `*_SLOPE_data.json` | 最完整，含所有元数据 |
| SQLite | `*.db` | 技能生成的数据库 |
| Excel | `*_summary.xlsx` | 汇总报告 |

### 6.3 统一数据库Schema (双库架构)

> **注意**: 统一数据库拆分为 `Ripple.db` + `Slope.db` 两个独立数据库，每个库包含完整的 vehicles/components/test_conditions 表，但分别只含对应类型的 results 表。
> - `match_confidence`, `match_method` — 工况匹配元数据
> - `raw_data_json` — 原始数据快照
> - `created_at`, `updated_at` — 时间戳

**Ripple.db**:
```sql
-- vehicles, components, test_conditions, data_batches, matching_logs
CREATE TABLE ripple_results (...);
-- 不含 slope_results 表
```

**Slope.db**:
```sql
-- vehicles, components, test_conditions, data_batches, matching_logs
CREATE TABLE slope_results (...);
-- 不含 ripple_results 表
```

两库共用相同的 vehicles/components/test_conditions Schema：
```sql
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY, vehicle_model TEXT,
  length_mm REAL, width_mm REAL, height_mm REAL,
  wheelbase_mm REAL, front_track_mm REAL, rear_track_mm REAL,
  min_ground_clearance_mm REAL, energy_type TEXT,
  front_motor_max_power_kw REAL, rear_motor_max_power_kw REAL,
  front_motor_max_torque_nm REAL, rear_motor_max_torque_nm REAL,
  system_total_power_kw REAL, high_voltage_architecture TEXT,
  battery_type TEXT, battery_capacity_kwh REAL, fast_charge_power_kw REAL,
  front_suspension TEXT, rear_suspension TEXT,
  engine_model TEXT, transmission_type TEXT, displacement_l REAL,
  engine_max_power_kw TEXT, engine_max_torque_nm TEXT,
  price_wan REAL
);

CREATE TABLE components (
  component_code TEXT PRIMARY KEY, component_name TEXT,
  unit TEXT, component_type TEXT
);

CREATE TABLE test_conditions (
  condition_id TEXT PRIMARY KEY, condition_name TEXT,
  soc_level TEXT, category TEXT
);
```

### 6.4 CLI命令参考
```bash
# 初始化 (必须指定输出位置，自动创建 Ripple.db + Slope.db)
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database

# 添加车辆 (自动路由到对应数据库，成功后自动导出 JSON/Excel)
python vehicle_database.py add V0001 V0002 V0003
python vehicle_database.py add --all

# 查询 (默认 Ripple.db，--type slope 查询 Slope.db)
python vehicle_database.py list
python vehicle_database.py list --ids
python vehicle_database.py list --type slope
python vehicle_database.py show V0001
python vehicle_database.py show V0001 --type slope
python vehicle_database.py stats
python vehicle_database.py stats --type slope

# 导出 (默认从 Ripple.db 导出)
python vehicle_database.py export V0001 --json -o V0001.json
python vehicle_database.py export V0001 --excel -o V0001.xlsx
python vehicle_database.py export --all --excel -o all_vehicles/
python vehicle_database.py export --all --type slope --excel -o all_slope/
python vehicle_database.py export --all --combine --json -o all_vehicles.json
```

### 6.5 配置持久化
```
~/.vehicle_database/config.json
{
  "source_path": "F:/Vehicle_Date",
  "database_path": "F:/Vehicle_Database"
}
```
> 向后兼容：旧配置 `database_path` 指向 `.db` 文件时，自动提取其所在目录。

---

## 七、增量处理引擎 (workflow-orchestrator)

### 7.1 功能定位

跨阶段协调的增量处理引擎，为每个阶段的输入计算指纹（SHA-256 / mtime+size），与缓存对比判定是否需要重新执行。避免对未变更的数据重复计算，大幅提升批量处理效率。

**适用场景**:
- 单车辆增量处理：仅重跑变更的阶段
- 批量增量处理：扫描多辆车，逐车决策
- 强制全量重跑：清空缓存后全部重新执行

**Stage1 (AutoHandleFiles GUI) 仍须手动执行**，引擎从阶段2开始增量处理。

### 7.2 指纹策略

| 阶段 | 输入文件 | 指纹算法 | 说明 |
|------|:---------|:---------|:-----|
| stage1 | `test_data/*.dmd` | `fast` (mtime+size) | 大文件用轻量指纹 |
| stage2_ripple | `statistics.xlsx` + 规则文件 + **`vehicle_info.md/xlsx` (v1.4 新增)** | `sha256` + **语义指纹 (v1.4)** | xlsx 用 openpyxl cell hash 屏蔽 zip metadata 差异;md 规范化换行 |
| stage2_slope | 同 stage2_ripple | 同上 | 同上 |
| stage3 | `_summary.xlsx` + 模板 | `sha256` | 阶段2汇总文件+报告模板 |
| stage4 | `_data.json` | `sha256` | 阶段2 JSON 输出 |

**v1.4 关键变更 (CR-N2 语义指纹)**:
- **vehicle_info 纳入 stage2 指纹**: 修改车型/参数后 stage2 自动重跑,级联触发 stage3/4
- **xlsx 语义指纹** (`_semantic_fingerprint`): 用 openpyxl 读取 cells 后 hash,避免"打开-保存"导致 zip 内部 mtime 变化触发误报变更
- **md 规范化**: `\r\n` → `\n` + 去尾空白,避免编辑器换行差异误触

### 7.3 缓存文件

```
{Vehicle_Date}/{VehicleID}/.workflow_cache.json
```

缓存内容示例 (v1.4 起含 schema_version):
```json
{
  "_schema_version": 2,
  "stage1": { "fingerprint": "1714003200:10485760", "completed_at": "2026-04-25T10:00:00+00:00" },
  "stage2_ripple": { "fingerprint": "a1b2c3d4...", "completed_at": "2026-04-25T10:05:00+00:00" },
  "stage2_slope": { "fingerprint": "e5f6g7h8...", "completed_at": "2026-04-25T10:06:00+00:00" },
  "stage4": { "fingerprint": "i9j0k1l2...", "completed_at": "2026-04-25T10:10:00+00:00" }
}
```

**v1.4 关键变更**:
- **`_schema_version: 2`** — 检测旧 cache 时打印升级日志,新算法 (vehicle_info 纳入指纹) 自动触发一次性重跑
- **原子写**: tmp+rename + fsync 防止崩溃损坏 cache;损坏时自动从 `.workflow_cache.json.bak` 回退
- **UTC ISO-8601 时间戳**: 13 处 `datetime.now()` 全部改为 `datetime.now(timezone.utc)`,避免 DST 二义性

### 7.3.1 执行日志文件

每次执行后自动保存执行日志：

```
{Vehicle_Date}/{VehicleID}/.workflow_execution_log.json
```

内容包含完整的执行计划和各阶段执行结果：
```json
{
  "vehicle_id": "V0001",
  "executed_at": "2026-05-09T14:30:00",
  "plan": [...],
  "execution": [...]
}
```

### 7.4 CLI命令

**工作目录**: `~/.claude/skills/workflow-orchestrator`

#### 单车辆处理

```bash
# 生成执行计划 (仅预览，不执行)
python incremental_workflow.py plan V0001 --base-dir F:/Vehicle_Date

# 执行增量工作流
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date --force

# 仅执行指定阶段
python incremental_workflow.py run V0001 --stages 2_ripple
python incremental_workflow.py run V0001 --stages 2_slope
python incremental_workflow.py run V0001 --stages 3

# 清空缓存
python incremental_workflow.py clear-cache V0001
```

#### 批量处理 (新增)

```bash
# 批量扫描并增量处理所有车辆（阶段2→3→4）
python incremental_workflow.py batch --scan F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# 仅批量导入数据库（阶段4）
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4
```

| 参数 | 说明 |
|------|:-----|
| `command` | `plan` / `run` / `clear-cache` / `batch` |
| `vehicle_id` | 车辆ID (plan/run/clear-cache 需要) |
| `--scan` | 批量扫描目录 (batch 命令使用) |
| `--base-dir` | 车辆数据根目录 (默认: F:/Vehicle_Date) |
| `--skills-dir` | 技能安装目录 (默认: ~/.claude/skills) |
| `--force` | 强制全量重跑，清空缓存 |
| `--stages` | 指定阶段: `all`, `1`, `2`, `3`, `4`, `2_ripple`, `2_slope` |

### 7.5 执行计划示例

#### 单车辆示例

```
======================================================================
车辆 V0001 增量处理执行计划
======================================================================
[跳过] [stage1                        ] 无 test_data 目录
[执行] [stage2_ripple                 ] 首次运行
[跳过] [stage2_slope                  ] 由 stage2_ripple 统一处理
[执行] [stage3_ripple_FM_V            ] 首次生成
[执行] [stage3_ripple_FM_A            ] 首次生成
[跳过] [stage3_ripple_DCC_V           ] 无汇总文件
...
======================================================================
总计: 2 个阶段需执行, 38 个阶段可跳过
预估总耗时: 20 分钟
======================================================================
```

> **注意**: 当车辆同时存在 RIPPLE 和 SLOPE 数据且 `stage2_ripple` 需执行时，`vehicle_skills_cli.py process` 会统一处理两者，`stage2_slope` 自动标记为"由 stage2_ripple 统一处理"而跳过，避免 SLOPE 被重复处理。

#### 批量处理汇总示例

```
======================================================================
批量增量处理汇总
======================================================================
总车辆数: 18
成功: 16
无需处理: 2
失败: 0
总耗时: 192.3s

Vehicle ID   阶段2          阶段3      阶段4          状态       耗时
----------------------------------------------------------------------
V0001        执行(R+S)      执行(4/4)  跳过           OK       9.3
V0002        执行(R+S)      跳过       执行(12/12)    OK       23.6
V0005        执行(R+S)      跳过       执行(26/26)    OK       63.2
V0017        执行(R+S)      跳过       跳过           OK       2.1
...
======================================================================
批量日志已保存: F:/Vehicle_Date/.workflow_batch_log.json
```

---

## 八、工况规则版本管理

### 8.1 功能定位

管理 `test_naming_rules.md` 和 `sensor_naming_rules.md` 的版本化加载、升级和审计。支持三种规则文件格式：

1. **`@import` 指令格式** (推荐)
   ```markdown
   @import vehicle-ripple-data:test_naming_rules@1.0
   
   # 本地自定义规则
   90_停车D档热风: 静止高温
   ```

2. **YAML frontmatter 格式**
   ```markdown
   ---
   version: "1.0"
   extends: true
   ---
   # 规则内容...
   ```

3. **传统完整规则格式** (完全兼容现有文件)
   - 文件内容即全部规则，不使用 `@import`
   - 传统格式车辆**不自动升级**，完全兼容现有工作流

### 8.2 规则加载优先级

```
1. 本地覆盖规则 (车辆文件夹内)
2. 引用的标准规则指定版本 (通过 @import 或 frontmatter)
3. 默认最新标准规则 (skills/references/ 目录)
```

### 8.3 CLI命令

**工作目录**: `~/.claude/skills/vehicle-ripple-data`

```bash
# 列出可用版本
python scripts/rule_manager.py list-versions test_naming_rules
python scripts/rule_manager.py list-versions sensor_naming_rules

# 升级单个车辆规则
python scripts/rule_manager.py upgrade V0001 --rule test_naming_rules --to 1.1

# 批量升级
python scripts/rule_manager.py batch-upgrade --scan F:/Vehicle_Date --rule test_naming_rules --to 1.1

# 审计所有车辆规则版本
python scripts/rule_manager.py audit --scan F:/Vehicle_Date
```

**版本元数据**: `references/versions.json`
```json
{
  "test_naming_rules": {
    "current": "1.0",
    "versions": {
      "1.0": { "file": "test_naming_rules.md", "date": "2025-01-15", "conditions_count": 54 }
    }
  }
}
```

---

## 九、文件夹结构规范

### 9.1 完整结构
```
F:/Vehicle_Date/                          # 数据源根目录 (可配置)
│
├── V0001/                                # 车辆父文件夹
│   ├── vehicle_info.md                   # 车辆信息 (必须)
│   ├── setup.png                         # 车辆照片 (可选)
│   ├── test_naming_rules.md              # 工况规则 (可选，默认兜底)
│   ├── sensor_naming_rules.md            # 传感器规则 (可选)
│   ├── test_data/                        # 原始.dmd数据 (AutoHandleFiles输入)
│   │
│   ├── V0001_RIPPLE/                     # 纹波分析结果 (阶段1输出)
│   │   ├── vehicle_info.md               # (可放此处，但推荐放父文件夹)
│   │   ├── test_naming_rules.md
│   │   ├── sensor_naming_rules.md
│   │   ├── FM_V/
│   │   │   ├── statistics.xlsx           # 7列统计
│   │   │   └── *.png                     # 每工况一张图
│   │   ├── RM_V/
│   │   ├── LV_V/
│   │   ├── LV_A/
│   │   ├── DCC_V/
│   │   ├── DCC_A/
│   │   ├── ACC_V/
│   │   ├── ACC_A/
│   │   ├── PTC_V/
│   │   ├── PTC_A/
│   │   ├── ACCM_V/
│   │   ├── ACCM_A/
│   │   ├── BATT_V/
│   │   ├── BATT_A/
│   │   ├── FAN_A/
│   │   ├── Vehicle_Harness_Splitter_V/
│   │   ├── Vehicle_Harness_Splitter_A/
│   │   └── ...
│   │   └── V0001_RIPPLE_output/          # 阶段2输出
│   │       ├── V0001_RIPPLE_summary.xlsx
│   │       ├── V0001_RIPPLE.db
│   │       ├── V0001_RIPPLE_data.json
│   │       ├── V0001_RIPPLE_REPORT_FM_V.docx    ← 阶段3输出
│   │       ├── V0001_RIPPLE_REPORT_RM_V.docx
│   │       ├── ...
│   │       └── error_report.md
│   │
│   └── V0001_SLOPE/                      # 斜率分析结果 (阶段1输出)
│       ├── FM_V/
│       │   ├── statistics.xlsx           # 4列统计
│       │   └── *.png (可选)
│       ├── RM_V/
│       ├── ... (同纹波的多个通道)
│       └── V0001_SLOPE_output/           # 阶段2输出
│           ├── V0001_SLOPE_summary.xlsx
│           ├── V0001_SLOPE.db
│           ├── V0001_SLOPE_data.json
│           ├── V0001_SLOPE_REPORT_FM_V.docx     ← 阶段3输出
│           ├── ...
│           └── error_report.md
│
├── V0002/
├── V0003/
└── ...

F:/Vehicle_Database/                      # 统一数据库目录
├── Ripple.db                             # 阶段4输出 (纹波数据库)
└── Slope.db                              # 阶段4输出 (斜率数据库)
```

### 9.2 命名约定
| 层级 | 命名模式 | 示例 |
|------|:---------|:-----|
| 车辆父文件夹 | `{VehicleID}` | `V0001` |
| 纹波数据文件夹 | `{VehicleID}_RIPPLE` | `V0001_RIPPLE` |
| 斜率数据文件夹 | `{VehicleID}_SLOPE` | `V0001_SLOPE` |
| 纹波输出文件夹 | `{VehicleID}_RIPPLE_output` | `V0001_RIPPLE_output` |
| 斜率输出文件夹 | `{VehicleID}_SLOPE_output` | `V0001_SLOPE_output` |
| 纹波汇总Excel | `{VehicleID}_RIPPLE_summary.xlsx` | `V0001_RIPPLE_summary.xlsx` |
| 斜率汇总Excel | `{VehicleID}_SLOPE_summary.xlsx` | `V0001_SLOPE_summary.xlsx` |
| 纹波数据库 | `{VehicleID}_RIPPLE.db` | `V0001_RIPPLE.db` |
| 斜率数据库 | `{VehicleID}_SLOPE.db` | `V0001_SLOPE.db` |
| 纹波报告 | `{VehicleID}_RIPPLE_REPORT_{ComponentCode}.docx` | `V0001_RIPPLE_REPORT_FM_V.docx` |
| 斜率报告 | `{VehicleID}_SLOPE_REPORT_{ComponentCode}.docx` | `V0001_SLOPE_REPORT_FM_V.docx` |

---

## 十、完整执行流程

### 10.1 单次车辆处理流程

```bash
# ===== Step 1: AutoHandleFiles (GUI操作) =====
# 1. 打开 AutoHandleFiles.exe
# 2. 选择 test_data/ 文件夹中的 .dmd 文件
# 3. 配置参数:
#    - 滤波器: 类型/截止频率/阶数
#    - FFT: 窗口类型/重叠率
#    - 工作模式: 纹波分析 / 斜率分析 / 两者
# 4. 点击"计算" → 生成 RIPPLE/ 和 SLOPE/ 数据

# ===== Step 2: 准备元数据文件 (手动) =====
# 在 V0001/ 目录下放置:
# - vehicle_info.md (必须)
# - test_naming_rules.md (可选)
# - sensor_naming_rules.md (可选)
# - setup.png (可选)

# ===== Step 3: 纹波数据整合 =====
# 调用 vehicle-ripple-data 技能
# 输入: V0001/ (父文件夹，技能自动发现 V0001_RIPPLE/)
# 输出: V0001_RIPPLE_output/

# ===== Step 4: 斜率数据整合 =====
# 调用 vehicle-slope-data 技能
# 输入: V0001/ (父文件夹，技能自动发现 V0001_SLOPE/)
# 输出: V0001_SLOPE_output/

# ===== Step 5: 生成检测报告 (方式A: 自动触发) =====
# 在阶段2处理时添加 --auto-report 参数，阶段2.5完成后自动触发阶段3
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --auto-report

# ===== Step 5: 生成检测报告 (方式B: 手动执行) =====
cd ~/.claude/skills/vehicle-report-generation
# 生成纹波报告 (所有通道)
python vehicle_report_cli.py generate V0001 --type ripple
# 生成斜率报告 (所有通道)
python vehicle_report_cli.py generate V0001 --type slope

# ===== Step 6: 导入统一数据库 =====
cd ~/.claude/skills/vehicle-database
python vehicle_database.py -s F:/Vehicle_Date add V0001
```

### 10.2 批量车辆处理流程

#### 推荐方式：增量引擎批量模式 (V3.3+)

```bash
# 增量处理所有车辆（阶段2→3→4，自动跳过未变更）
cd ~/.claude/skills/workflow-orchestrator
python incremental_workflow.py batch --scan F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# 仅批量导入数据库（阶段4）
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4
```

#### 传统方式：逐技能批量处理

```bash
# ===== 批量整合 + 自动报告生成 =====
# 方式A: 自动触发阶段3
cd ~/.claude/skills/vehicle-ripple-data
python scripts/cli/vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress --auto-report

# ===== 批量整合 (仅阶段2，不触发报告) =====
# 方式B: 手动控制阶段3
cd ~/.claude/skills/vehicle-ripple-data
python scripts/cli/vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress

# 批量整合斜率数据
cd ~/.claude/skills/vehicle-slope-data
python scripts/cli/process_slope.py batch --scan F:/Vehicle_Date --progress

# ===== 批量导入数据库 =====
cd ~/.claude/skills/vehicle-database
python vehicle_database.py add --all

# ===== 批量生成报告 (手动) =====
cd ~/.claude/skills/vehicle-report-generation
python vehicle_report_cli.py batch F:/Vehicle_Date --type all
```

---

## 十一、五个技能CLI命令完全参考

> 以下CLI命令覆盖工作流的阶段2~阶段4，阶段1 (AutoHandleFiles) 为GUI操作无CLI。

---

### 11.1 vehicle-ripple-data — 纹波数据整合CLI
**CLI入口:** `scripts/cli/vehicle_skills_cli.py` (统一CLI，同时处理RIPPLE和SLOPE)  
**备选入口:** `scripts/cli/process_vehicle.py` (仅RIPPLE的独立CLI)  
**工作目录:** `~/.claude/skills/vehicle-ripple-data`

#### A. 统一CLI — vehicle_skills_cli.py

**命令结构:**
```bash
python scripts/cli/vehicle_skills_cli.py <command> [options]
```

**子命令总览:**

| 子命令 | 功能 |
|--------|------|
| `process` | 处理单个车辆 (自动检测RIPPLE/SLOPE) |
| `batch` | 批量处理多辆车 |
| `validate` | 仅验证文件夹结构，不生成输出 |
| `version` | 显示版本信息 |

**1. process — 单车辆处理**

```bash
python scripts/cli/vehicle_skills_cli.py process <vehicle_folder> [选项]
```

| 参数 | 简写 | 必填 | 说明 | 示例 |
|------|:----:|:----:|:-----|:-----|
| `vehicle_folder` | — | 是 | 车辆父文件夹路径 | `E:/Vehicle_Date/V0001` |
| `--progress` | `-p` | 否 | 显示进度条 | `--progress` |
| `--output` | `-o` | 否 | 自定义输出目录 | `--output F:/results` |
| `--auto-report` | `-r` | 否 | 阶段2.5后自动触发阶段3报告生成 | `--auto-report` |
| `--no-auto-db` | — | 否 | 阶段2完成后不自动导入数据库（增量引擎专用） | `--no-auto-db` |

```bash
# 基本用法
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001

# 带进度条
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

# 自定义输出目录
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --output F:/results

# 处理完成后自动生成报告 (阶段2→2.5→4全链路)
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --auto-report

# 完整参数组合
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress --auto-report
```

**2. batch — 批量处理**

```bash
# 模式A: 显式指定车辆列表
python scripts/cli/vehicle_skills_cli.py batch <folder1> <folder2> ... [选项]

# 模式B: 自动扫描父目录
python scripts/cli/vehicle_skills_cli.py batch --scan <parent_folder> [选项]
```

| 参数 | 简写 | 必填 | 说明 |
|------|:----:|:----:|:-----|
| `vehicle_folders` | — | 否(模式A) | 车辆文件夹路径列表 |
| `--scan` | `-s` | 否(模式B) | 自动扫描父目录 |
| `--progress` | `-p` | 否 | 显示进度条 |
| `--auto-report` | `-r` | 否 | 阶段2.5后自动触发阶段3报告生成 |

```bash
# 显式列表
python scripts/cli/vehicle_skills_cli.py batch E:/Vehicle_Date/V0001 E:/Vehicle_Date/V0002

# 自动扫描 (推荐)
python scripts/cli/vehicle_skills_cli.py batch --scan E:/Vehicle_Date --progress

# 自动扫描 + 自动生成报告 (处理→校验→报告全链路)
python scripts/cli/vehicle_skills_cli.py batch --scan E:/Vehicle_Date --progress --auto-report
```

**3. validate — 结构验证**

```bash
python scripts/cli/vehicle_skills_cli.py validate <vehicle_folder>
```

```bash
# 验证V0001的文件夹结构
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001
```

**4. version — 版本信息**

```bash
python scripts/cli/vehicle_skills_cli.py version
```

#### B. 独立CLI — process_vehicle.py (仅RIPPLE)

```bash
python scripts/cli/process_vehicle.py --folder <folder> [选项]
```

| 参数 | 简写 | 必填 | 说明 | 默认值 |
|------|:----:|:----:|:-----|:-------|
| `--folder` | `-f` | 是 | 车辆文件夹路径 | — |
| `--validate-first` | `-v` | 否 | 处理前验证数据完整性 | `False` |
| `--incremental` | `-i` | 否 | 增量处理 (仅处理变更文件) | `False` |
| `--format` | `-fmt` | 否 | 输出格式: `all`/`json`/`excel`/`sqlite` | `all` |
| `--output-dir` | `-o` | 否 | 自定义输出目录 | `{VehicleID}_RIPPLE_output` |
| `--verbose` | `-V` | 否 | 详细日志 | `False` |
| `--version` | — | 否 | 显示版本并退出 | — |

```bash
# 基本处理
python scripts/cli/process_vehicle.py --folder V0001_RIPPLE

# 验证后处理
python scripts/cli/process_vehicle.py --folder V0001_RIPPLE --validate-first

# 仅生成JSON和Excel
python scripts/cli/process_vehicle.py --folder V0001_RIPPLE --format json,excel

# 增量处理
python scripts/cli/process_vehicle.py --folder V0001_RIPPLE --incremental
```

#### C. 验证工具 — validate_rules.py

```bash
python scripts/validate_rules.py --vehicle-folder <folder> [选项]
```

| 参数 | 简写 | 必填 | 说明 |
|------|:----:|:----:|:-----|
| `--vehicle-folder` | `-v` | 是 | 车辆文件夹路径 |
| `--verbose` | — | 否 | 显示详细日志 |
| `--output-report` | `-o` | 否 | 输出验证报告到JSON文件 |

**验证检查项 (6步):**
1. vehicle_info文件存在性
2. 命名规则文件格式
3. 组件文件夹结构
4. 图片与Excel匹配
5. UTF-8编码检查
6. setup图片存在性

```bash
# 基本验证
python scripts/validate_rules.py --vehicle-folder V0001

# 详细验证并输出报告
python scripts/validate_rules.py --vehicle-folder V0001 --verbose --output-report validation.json
```

#### D. Excel报告生成器 — generate_excel_report.py

```bash
# 从JSON生成
python scripts/generate_excel_report.py --input-json <json> --output-excel <xlsx>

# 从车辆文件夹自动检测JSON
python scripts/generate_excel_report.py --vehicle-folder <folder> --output-excel <xlsx>
```

| 参数 | 必填 | 说明 |
|------|:----:|:-----|
| `--input-json` | 否* | 输入JSON文件路径 |
| `--vehicle-folder` | 否* | 车辆文件夹路径 (自动查找output.json) |
| `--output-excel` | 是 | 输出Excel文件路径 |

* `--input-json` 和 `--vehicle-folder` 至少填一个

```bash
# 从JSON生成
python scripts/generate_excel_report.py --input-json V0001_RIPPLE_data.json --output-excel report.xlsx

# 从车辆文件夹生成
python scripts/generate_excel_report.py --vehicle-folder V0001 --output-excel report.xlsx
```

---

### 11.2 vehicle-slope-data — 斜率数据整合CLI
**CLI入口:** `scripts/cli/process_slope.py`  
**工作目录:** `~/.claude/skills/vehicle-slope-data`

#### 命令结构

```bash
python scripts/cli/process_slope.py <command> [选项]
```

**子命令总览:**

| 子命令 | 功能 |
|--------|------|
| `process` | 处理单个车辆 |
| `batch` | 批量处理多辆车 |

#### 1. process — 单车辆处理

```bash
python scripts/cli/process_slope.py process --folder <FOLDER_PATH> [选项]
```

| 参数 | 简写 | 必填 | 说明 | 默认值 |
|------|:----:|:----:|:-----|:-------|
| `--folder` | `-f` | 是 | 车辆文件夹路径 (支持 `{VehID}_SLOPE` 或 `{VehID}`) | — |
| `--validate-first` | `-v` | 否 | 处理前验证数据 | `False` |
| `--format` | `-fmt` | 否 | 输出格式: `all`/`json`/`excel`/`sqlite` | `all` |
| `--output-dir` | `-o` | 否 | 自定义输出目录 | `{VehicleID}_SLOPE_output` |
| `--verbose` | `-V` | 否 | 详细日志 | `False` |

```bash
# 基本处理 (推荐: {VehicleID}_SLOPE格式)
python scripts/cli/process_slope.py process --folder V0001_SLOPE

# 带验证
python scripts/cli/process_slope.py process --folder V0001_SLOPE --validate-first

# 仅生成JSON和Excel
python scripts/cli/process_slope.py process --folder V0001_SLOPE --format json,excel

# 自定义输出目录
python scripts/cli/process_slope.py process --folder V0001_SLOPE --output-dir C:/Reports/V0001

# 详细模式
python scripts/cli/process_slope.py process --folder V0001_SLOPE --verbose
```

#### 2. batch — 批量处理

```bash
# 模式A: 显式列表
python scripts/cli/process_slope.py batch [FOLDERS...] [选项]

# 模式B: 自动扫描
python scripts/cli/process_slope.py batch --scan <parent_dir> [选项]
```

| 参数 | 简写 | 必填 | 说明 | 默认值 |
|------|:----:|:----:|:-----|:-------|
| `folders` | — | 否(模式A) | 车辆文件夹路径列表 | — |
| `--scan` | `-s` | 否(模式B) | 自动扫描父目录 | `None` |
| `--validate-first` | `-v` | 否 | 处理前验证 | `False` |
| `--format` | `-fmt` | 否 | 输出格式 | `all` |
| `--progress` | `-p` | 否 | 显示进度条 | `False` |
| `--verbose` | `-V` | 否 | 详细日志 | `False` |

```bash
# 显式列表
python scripts/cli/process_slope.py batch V0001_SLOPE V0002_SLOPE V0003_SLOPE

# 自动扫描 (推荐)
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date

# 自动扫描+验证+进度条
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --validate-first --progress

# 仅生成Excel
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --format excel
```

#### 3. 验证工具 — validate_slope.py

```bash
python scripts/validate_slope.py --vehicle-folder <FOLDER_PATH> [选项]
```

| 参数 | 简写 | 必填 | 说明 |
|------|:----:|:----:|:-----|
| `--vehicle-folder` | `-f` | 是 | 车辆文件夹路径 |
| `--verbose` | `-v` | 否 | 详细输出 |
| `--output-report` | — | 否 | 生成JSON验证报告 |

**验证检查项:**
1. vehicle_info完整性
2. 命名规则格式
3. 组件文件夹结构
4. statistics.xlsx格式 (4列验证)
5. UTF-8编码
6. 生成验证报告

```bash
# 基本验证
python scripts/validate_slope.py --vehicle-folder V0001_SLOPE

# 详细验证
python scripts/validate_slope.py --vehicle-folder V0001_SLOPE --verbose

# 输出JSON报告
python scripts/validate_slope.py --vehicle-folder V0001_SLOPE --output-report validation.json
```

#### 4. Excel生成器 — generate_excel_report.py

```bash
python scripts/generate_excel_report.py --input-json <JSON> --output-excel <XLSX>
python scripts/generate_excel_report.py --vehicle-folder <FOLDER> --output-excel <XLSX>
```

```bash
# 从JSON生成
python scripts/generate_excel_report.py --input-json V0001_SLOPE_data.json --output-excel V0001_SLOPE_summary.xlsx

# 从车辆文件夹自动检测
python scripts/generate_excel_report.py --vehicle-folder V0001_SLOPE --output-excel V0001_SLOPE_summary.xlsx
```

#### 返回码

| 代码 | 含义 |
|:----:|:-----|
| 0 | 成功 |
| 1 | 处理/验证失败 |
| 130 | 用户中断 (Ctrl+C) |

---

### 11.3 vehicle-database — 统一数据库管理CLI
**CLI入口:** `vehicle_database.py`  
**工作目录:** `~/.claude/skills/vehicle-database`

#### 命令结构

```bash
python vehicle_database.py [全局选项] <command> [命令选项]
```

#### 全局选项

| 选项 | 简写 | 说明 |
|------|:----:|:-----|
| `--source` | `-s` | 数据源路径 (自动保存到配置) |
| `--database` | `-d` | 数据库目录 (向后兼容: 也可指向旧 .db 文件) |
| `--format` | `-f` | 输入格式过滤: `db`/`excel`/`json`/`all` |
| `--verbose` | `-v` | 详细输出模式 |

#### 子命令总览

| 子命令 | 功能 | 示例 |
|--------|------|:----|
| `init` | 初始化数据库 | `python vehicle_database.py init -o F:/DB` |
| `add` | 添加车辆数据 | `python vehicle_database.py add V0001` |
| `update` | 更新车辆数据 | `python vehicle_database.py update V0001` |
| `remove` | 从数据库删除车辆 | `python vehicle_database.py remove V0001` |
| `list` | 列出所有车辆 | `python vehicle_database.py list` |
| `show` | 显示车辆详情 | `python vehicle_database.py show V0001` |
| `stats` | 数据库统计 | `python vehicle_database.py stats` |
| `export` | 导出车辆数据 | `python vehicle_database.py export V0001 --json` |

#### 1. init — 初始化数据库

```bash
python vehicle_database.py -s <source_path> init [选项]
```

| 选项 | 简写 | 必填 | 说明 |
|------|:----:|:----:|:-----|
| `--output` | `-o` | 是 | 输出目录 (自动创建 Ripple.db + Slope.db) |

```bash
# 指定输出目录
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database

# 使用全局 -d 指定数据库目录
python vehicle_database.py -s F:/Vehicle_Date -d F:/Vehicle_Database init
```

**交互式路径提示:** 当数据源路径未配置且默认路径不存在时，自动提示输入。

#### 2. add — 添加车辆

```bash
python vehicle_database.py [全局选项] add <vehicle_ids...> [选项]
```

| 选项 | 说明 |
|------|:-----|
| `--all` | 添加数据源路径下的所有车辆 |

```bash
# 添加单个车辆 (成功后自动导出 Ripple.json/Ripple.xlsx/Slope.json/Slope.xlsx)
python vehicle_database.py add V0001

# 添加多个车辆
python vehicle_database.py add V0001 V0002 V0003

# 添加所有车辆
python vehicle_database.py add --all

# 指定数据源路径
python vehicle_database.py -s F:/Vehicle_Date add V0001
```

#### 3. update — 更新车辆

```bash
python vehicle_database.py update <vehicle_id>
```

```bash
# 更新单个车辆
python vehicle_database.py update V0001

# 更新所有车辆
python vehicle_database.py update --all
```

#### 4. remove — 删除车辆

```bash
python vehicle_database.py remove <vehicle_id>
```

```bash
# 删除单个车辆
python vehicle_database.py remove V0001

# 删除所有车辆
python vehicle_database.py remove --all
```

#### 5. list — 列出车辆

```bash
python vehicle_database.py list [选项]
```

| 选项 | 说明 |
|------|:-----|
| `--ids` | 仅列出车辆ID (便于管道操作) |
| `--type` | 查询数据库类型: `ripple` (默认) / `slope` |

```bash
# 列出所有车辆详情 (默认 Ripple.db)
python vehicle_database.py list

# 仅列出ID
python vehicle_database.py list --ids

# 查询 Slope.db
python vehicle_database.py list --type slope
```

#### 6. show — 车辆详情

```bash
python vehicle_database.py show <vehicle_id> [选项]
```

| 选项 | 说明 |
|------|:-----|
| `--type` | 查询数据库类型: `ripple` (默认) / `slope` |

```bash
# 查看车辆详情 (默认 Ripple.db)
python vehicle_database.py show V0001

# 查询 Slope.db
python vehicle_database.py show V0001 --type slope
```

#### 7. stats — 数据库统计

```bash
python vehicle_database.py stats [选项]
```

| 选项 | 说明 |
|------|:-----|
| `--type` | 查询数据库类型: `ripple` (默认) / `slope` |

```bash
# 数据库统计 (默认 Ripple.db)
python vehicle_database.py stats

# 查询 Slope.db
python vehicle_database.py stats --type slope
```

#### 8. export — 导出数据

```bash
python vehicle_database.py export <vehicle_id> [选项]
```

| 选项 | 说明 |
|------|:-----|
| `--json` | 导出为JSON格式 |
| `--excel` | 导出为Excel格式 |
| `--sqlite` | 导出为SQLite格式 |
| `-o, --output` | 输出路径 |
| `--all` | 导出所有车辆 |
| `--combine` | 合并所有车辆到单个文件 (需配合 `--all`) |
| `--force` | 覆盖已存在文件 |
| `--type` | 导出数据库类型: `ripple` (默认) / `slope` |

```bash
# 导出为JSON (默认 Ripple.db)
python vehicle_database.py export V0001 --json -o V0001.json

# 导出为Excel
python vehicle_database.py export V0001 --excel -o V0001.xlsx

# 导出所有车辆为Excel
python vehicle_database.py export --all --excel -o all_vehicles/

# 从 Slope.db 导出
python vehicle_database.py export V0001 --type slope --json -o V0001_slope.json
```

#### 配置持久化

配置文件保存在用户家目录:
```
~/.vehicle_database/config.json
{
  "source_path": "F:/Vehicle_Date",
  "database_path": "F:/Vehicle_Database"
}
```
> 向后兼容：旧配置 `database_path` 指向 `.db` 文件时，自动提取其所在目录。

---

### 11.4 vehicle-report-generation — 报告生成CLI
**CLI入口:** `vehicle_report_cli.py`  
**工作目录:** `~/.claude/skills/vehicle-report-generation`

#### 命令结构

```bash
python vehicle_report_cli.py [全局选项] <command> [命令选项]
```

#### 子命令总览

| 子命令 | 功能 |
|--------|------|
| `generate` | 生成单个车辆的报告 |
| `batch` | 批量生成所有车辆的报告 |

#### 1. generate — 单车辆报告

```bash
python vehicle_report_cli.py generate <VEHICLE_ID> [选项]
```

| 参数 | 必填 | 说明 |
|------|:----:|:-----|
| `VEHICLE_ID` | 是 | 车辆标识符 (如 V0001, V0002) |

| 选项 | 类型 | 默认值 | 说明 |
|------|:----:|:-------|:-----|
| `--type` | Choice | `all` | 报告类型: `ripple`/`slope`/`all` |
| `--component` | String | `None` | 指定组件通道 (如 ACC_A)。不指定则生成所有通道 |
| `--base-dir` | Path | `F:/Vehicle_Date` | 车辆数据根目录 |
| `--template` | Path | `templates/ripple_report_template.docx` | 报告模板路径 |

```bash
# 生成全部报告 (纹波+斜率, 所有通道)
python vehicle_report_cli.py generate V0006

# 仅生成纹波报告
python vehicle_report_cli.py generate V0006 --type ripple

# 仅生成斜率报告
python vehicle_report_cli.py generate V0006 --type slope

# 指定通道
python vehicle_report_cli.py generate V0005 --type ripple --component ACC_A

# 指定数据目录
python vehicle_report_cli.py generate V0001 --base-dir E:/Vehicle_Date
```

**输出路径:**
- 纹波: `{base_dir}/{vehicle_id}/{vehicle_id}_RIPPLE/{vehicle_id}_RIPPLE_output/{vehicle_id}_RIPPLE_REPORT_{ComponentCode}.docx`
- 斜率: `{base_dir}/{vehicle_id}/{vehicle_id}_SLOPE/{vehicle_id}_SLOPE_output/{vehicle_id}_SLOPE_REPORT_{ComponentCode}.docx`

#### 2. batch — 批量报告

```bash
python vehicle_report_cli.py batch <TARGET_DIR> [选项]
```

| 参数 | 必填 | 说明 |
|------|:----:|:-----|
| `TARGET_DIR` | 是 | 包含车辆文件夹的目录 (如 F:/Vehicle_Date) |

| 选项 | 类型 | 默认值 | 说明 |
|------|:----:|:-------|:-----|
| `--type` | Choice | `all` | 报告类型: `ripple`/`slope`/`all` |
| `--component` | String | `None` | 指定组件通道 |
| `--template` | Path | `templates/...` | 报告模板路径 |
| `--skip-existing` | Flag | `False` | 跳过已生成报告的车辆 |

```bash
# 批量生成所有报告
python vehicle_report_cli.py batch F:/Vehicle_Date

# 仅批量生成纹波报告
python vehicle_report_cli.py batch F:/Vehicle_Date --type ripple

# 批量生成斜率报告，跳过已存在的
python vehicle_report_cli.py batch F:/Vehicle_Date --type slope --skip-existing
```

**批量行为:**
- 扫描目标目录中匹配 `V\d+` 模式的文件夹
- 逐车辆顺序处理
- 显示进度和汇总统计
- 单车辆失败不影响其他车辆

---

### 11.5 CLI速查表
#### 各技能入口速查

| 技能 | CLI入口 | 工作目录 |
|------|:--------|:---------|
| vehicle-ripple-data | `scripts/cli/vehicle_skills_cli.py` | `~/.claude/skills/vehicle-ripple-data` |
| vehicle-slope-data | `scripts/cli/process_slope.py` | `~/.claude/skills/vehicle-slope-data` |
| vehicle-database | `vehicle_database.py` | `~/.claude/skills/vehicle-database` |
| vehicle-report-generation | `vehicle_report_cli.py` | `~/.claude/skills/vehicle-report-generation` |
| workflow-orchestrator | `incremental_workflow.py` | `~/.claude/skills/workflow-orchestrator` |
| rule-manager | `scripts/rule_manager.py` | `~/.claude/skills/vehicle-ripple-data` |

#### 常用命令速查

```bash
# ========== 单车辆完整流程 (自动报告) ==========
# 方式A: 单命令完成阶段2→2.5→3 (推荐)
# 在 vehicle-ripple-data 目录下
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress --auto-report

# ========== 单车辆完整流程 (手动控制) ==========
# Step 1: 纹波整合
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

# Step 2: 斜率整合 (由 vehicle_skills_cli.py 统一处理，无需单独调用)
# 如必须单独处理斜率（不推荐）：
python scripts/cli/process_slope.py process --folder E:/Vehicle_Date/V0001/V0001_SLOPE

# Step 3: 导入数据库 (在 vehicle-database 目录下)
python vehicle_database.py -s E:/Vehicle_Date add V0001

# Step 4: 生成报告 (在 vehicle-report-generation 目录下)
python vehicle_report_cli.py generate V0001 --type all

# ========== 批量处理 (推荐：增量引擎) ==========
# 增量处理所有车辆（阶段2→3→4，自动跳过未变更）
python incremental_workflow.py batch --scan F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# 仅批量导入数据库（阶段4）
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4

# ========== 批量处理 (传统方式) ==========
# 批量整合 + 自动报告生成 (纹波+斜率)
python scripts/cli/vehicle_skills_cli.py batch --scan E:/Vehicle_Date --progress --auto-report

# 批量整合 (仅斜率)
python scripts/cli/process_slope.py batch --scan E:/Vehicle_Date --progress

# 批量导入数据库
python vehicle_database.py add --all

# 批量生成报告
python vehicle_report_cli.py batch E:/Vehicle_Date --type all

# ========== 增量处理 (workflow-orchestrator) ==========
# 生成执行计划
python incremental_workflow.py plan V0001 --base-dir F:/Vehicle_Date

# 执行增量工作流 (自动跳过未变更阶段)
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date

# 强制全量重跑
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date --force

# 批量增量处理
python incremental_workflow.py batch --scan F:/Vehicle_Date

# ========== 规则版本管理 ==========
# 列出可用版本
python scripts/rule_manager.py list-versions test_naming_rules

# 审计所有车辆规则版本
python scripts/rule_manager.py audit --scan F:/Vehicle_Date

# ========== 验证与查询 ==========
# 验证纹波数据
python vehicle_skills_cli.py validate E:/Vehicle_Date/V0001

# 验证斜率数据 (在 vehicle-slope-data 目录下)
python scripts/validate_slope.py --vehicle-folder E:/Vehicle_Date/V0001/V0001_SLOPE

# 跨阶段一致性校验 (手动)
python scripts/validate_cross_format.py --vehicle-id V0001 --output-dir F:/Vehicle_Date/V0001/V0001_RIPPLE/V0001_RIPPLE_output --type ripple

# 列出数据库中所有车辆
python vehicle_database.py list

# 查看车辆详情
python vehicle_database.py show V0001

# 数据库统计
python vehicle_database.py stats
```

---

## 十二、数据映射与编码规范

### 12.1 车辆信息字段
| 字段名 | 说明 | 类型 |
|:-------|:-----|:----:|
| 车辆ID | 主键 | TEXT |
| 车型 | 车辆型号 | TEXT |
| 车长mm | 长度 | REAL |
| 车宽mm | 宽度 | REAL |
| 车高mm | 高度 | REAL |
| 轴距(mm) | 轴距 | REAL |
| 前轮距(mm) | 前轮距 | REAL |
| 后轮距(mm) | 后轮距 | REAL |
| 最小离地间隙(mm) | 离地间隙 | REAL |
| 混合动力系统 | 混动类型 | TEXT |
| 驱动形式 | 驱动方式 | TEXT |
| 前电机最大功率(kW) | 前电机功率 | REAL |
| 后电机最大功率(kW) | 后电机功率 | REAL |
| 前电机最大扭矩(N·m) | 前电机扭矩 | REAL |
| 后电机最大扭矩(N·m) | 后电机扭矩 | REAL |
| 系统综合功率(kW) | 总功率 | REAL |
| 高压架构 | 电压平台 | TEXT |
| 动力电池类型 | 电池类型 | TEXT |
| 动力电池总电量(kWh) | 电池容量 | REAL |
| 快充功率(kW) | 快充能力 | REAL |
| 前悬类型 | 前悬架 | TEXT |
| 后悬类型 | 后悬架 | TEXT |
| 发动机型号 | 发动机 | TEXT |
| 变速箱类型 | 变速箱 | TEXT |
| 排量(L) | 排量 | REAL |
| 发动机最大净功率(kW/rpm) | 发动机功率 | TEXT |
| 发动机最大净扭矩(N·m/rpm) | 发动机扭矩 | TEXT |
| 指导价格（万元） | 价格 | REAL |

### 12.2 标准组件通道（数量视项目而定）
| 通道代码 | 组件名称 | 单位 | 类型 |
|:---------|:---------|:----:|:----:|
| FM_V | 前电驱系统直流母线端电压 | V | voltage |
| FM_A | 前电驱系统直流母线端电流 | A | current |
| RM_V | 后电驱系统直流母线端电压 | V | voltage |
| RM_A | 后电驱系统直流母线端电流 | A | current |
| DCC_V | 动力电池直流充电端电压 | V | voltage |
| DCC_A | 动力电池直流充电端电流 | A | current |
| ACC_V | OBC输出端电压 | V | voltage |
| ACC_A | OBC输出端电流 | A | current |
| PTC_V | PTC输入端电压 | V | voltage |
| PTC_A | PTC输入端电流 | A | current |
| ACCM_V | 压缩机输入端电压 | V | voltage |
| ACCM_A | 压缩机输入端电流 | A | current |
| LV_V | 12V电池低压电压 | V | voltage |
| LV_A | 12V电池低压电流 | A | current |
| FAN_A | 前端冷却模块风扇电流 | A | current |
| BATT_V | 动力电池电压 | V | voltage |
| BATT_A | 动力电池电流 | A | current |
| Vehicle_Harness_Splitter_V | 车辆线束分线器电压 | V | voltage |
| Vehicle_Harness_Splitter_A | 车辆线束分线器电流 | A | current |

### 12.3 编码处理规范
| 场景 | 处理方式 | 回退策略 |
|------|----------|----------|
| 读取.md文件 | `open(path, 'r', encoding='utf-8')` | 失败则尝试`gbk` |
| 读取.xlsx文件 | `pandas.read_excel()` | 指定`engine='openpyxl'` |
| 访问Excel列 | 用`iloc[0], iloc[1]...` | 绝不用列名字符串访问 |
| 写入输出文件 | `encoding='utf-8'` | 确保中文正确保存 |
| 图片文件名解析 | 直接字符串处理 | 支持GBK乱码的特征匹配 |

---

## 十三、已知问题与解决方案

### 13.1 AutoHandleFiles 问题

| 优先级 | 问题 | 影响 | 解决方案 |
|:------:|------|------|----------|
| 高 | 大文件MemoryError | 程序崩溃 | 优化分块读取策略，限制单块内存 |
| 高 | 临时文件清理冲突 | WinError 32 | 串行化清理或使用文件锁 |
| 高 | .temp目录未创建 | FileNotFoundError | `os.makedirs(exist_ok=True)`前置 |
| 中 | dmd文件损坏 | FILE_INVALID | 文件头校验，损坏则跳过并记录 |
| 中 | 线程异常吞没 | 静默失败 | 增加异常回调和详细日志 |

### 13.2 数据整合阶段问题

| 优先级 | 问题 | 影响 | 解决方案 |
|:------:|------|------|----------|
| 高 | Excel列名乱码 | KeyError | 强制使用`iloc`索引访问 |
| 高 | 图片匹配失败 | image_path为null | 验证文件名解析逻辑，检查两种格式 |
| 高 | **SOC提取分隔符不兼容** | 大量Unknown SOC分级 | V3.5统一正则: `_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')` 支持`_` `-` `空格`三种分隔符 |
| 高 | **坡度前缀GBK乱码** | 爬坡工况无法匹配图片 | V3.5 `_normalize_condition_id()` 将`�¶�10`替换为`坡度10`，统一xlsx与图片文件名的condition_id |
| 中 | 工况名称不匹配 | 报告中显示原始ID | 四级模糊匹配策略 |
| 中 | SOC分级错误 | 数据归入错误区间 | 必须从condition_id直接提取数字 |
| 中 | **图片文件名非标准标记** | `xpp`/`Xpp`标记导致解析失败 | V3.5扩展检测: `any(marker in part for marker in ('Ipp','Vpp','ipp','vpp','xpp','Xpp'))` |
| 中 | **图片文件名末尾空格** | condition_id带空格导致匹配失败 | V3.5 `img_stem = img_file.stem.strip()` 自动去除首尾空格 |
| 低 | 缺少vehicle_info | 处理中断 | 明确错误提示，要求补充文件 |
| 低 | 缺少test_naming_rules.md | 模糊匹配警告增多 | 补充本地规则文件或使用默认规则兜底 |

### 13.3 增量引擎问题 (已修复)

| 优先级 | 问题 | 影响 | 解决方案 |
|:------:|------|------|----------|
| 高 | 阶段2 slope 重复处理 | SLOPE被处理两次 | `_decide_stage2_slope()` 增加覆盖判断：当 `stage2_ripple` 会执行时，SLOPE 标记为"由 stage2_ripple 统一处理" |

### 13.4 报告生成阶段问题

| 优先级 | 问题 | 影响 | 解决方案 |
|:------:|------|------|----------|
| 高 | 电流/电压通道单位混淆 | 电流通道错误显示"电压纹波/Vpp" | 根据`component_code`后缀(`_A`/`_V`)动态切换单位和阈值 |
| 高 | 斜率报告单位未区分 | 电流斜率错误显示"电压斜率/V/s" | 同上，`_A`→"电流斜率/A/s"，`_V`→"电压斜率/V/s" |
| 中 | Excel编码错误 | 无法读取数据 | 自动回退到SQLite数据库 |
| 中 | 图片路径变更 | 报告中图片缺失 | 使用绝对路径或验证路径存在性 |
| 低 | 部分工况缺失 | 表格留空 | 报告中标注"数据缺失" |

### 13.5 数据库阶段问题 (V3.4 已修复)

| 优先级 | 问题 | 影响 | 解决方案 |
|:------:|------|------|----------|
| 高 | 单库表冲突 | `slope_results` 表在 Ripple.db 不存在，导致 `_delete_vehicle` 报错 | 拆分为 `Ripple.db` + `Slope.db` 双库，`_delete_vehicle` 添加 `data_type` 参数 |
| 高 | JsonExporter 硬编码表名 | 连接 Slope.db 时查询 `ripple_results` 报错 | `JsonExporter` 添加 `data_type` 参数，动态选择结果表 |
| 中 | 旧 `--database` 参数指向文件 | 向后兼容性 | `resolve_database_path()` 自动检测 `.db` 后缀，提取 parent 目录 |
| 低 | vehicle_info 重复同步 | 同一辆车同时有纹波+斜率数据时 vehicle_info 可能重复 | `import_vehicle` 根据实际数据源类型分别同步到对应库 |

### 13.6 v1.4 整改批次 (新增,2026-05-11)

**核心修复**:

| 优先级 | 问题 | 影响 | 解决方案 |
|:------:|------|------|----------|
| 致命 | importer 内部 commit 破坏 update.py 原子性 (NEW-1) | DELETE 已 commit,import 失败时数据丢失 | 3 个 importer 去内部 commit + 必须 re-raise 异常,由外层 `with DatabaseConnection` 控制 |
| 致命 | importer 减行重导留孤儿数据 (CR-N4) | 旧记录不属于新 JSON 但仍存在 | `import_vehicle` 前 `DELETE FROM ripple_results/slope_results WHERE vehicle_id = ?` |
| 致命 | add.py 静默吞失败 (CR-N7) | success_count=0 仍 exit 0,stage4 cache 错误标完成 | add.py 末尾 exit 0/2/3 区分成功/完全失败/部分失败;orchestrator 识别 partial 不更新 cache |
| 致命 | `_save_cache` 非原子写崩溃丢失全部历史 (CR-N8) | 写入中途崩溃 → JSON 损坏 → 视为新车辆全 stage 重跑 | tmp+fsync+os.replace 原子写 + retry 处理 Windows 文件锁;损坏时从 `.bak` 回退 |
| 致命 | `batch_log` 仅最后写,中途崩溃丢失全部 (CR-N9) | 24 辆车跑到第 12 辆崩溃 → 已完成 12 条结果全失 | 每辆车完成后立即原子写 `.workflow_batch_log.json` + 单车 try/except 包裹 |
| 致命 | `_stage4_missing_handled` 实例变量失效 (C1 R6) | 24 辆车每辆都新建实例 → flag 重置 → 24 倍重 import | 改 class-level `_stage4_missing_handled_global` + `batch_run` 起始 reset |
| 高 | partial 状态错误标 OK (H1 R6) | 用户看到"成功"但下次又重跑,体验混乱 | 引入 PARTIAL 状态全链路传播,results / display / stats 单独统计 |
| 高 | DatabaseConnection.__exit__ commit 抛错时不 close (VDB-H1 R6) | 连接泄漏 | 改 try/finally 保证 close;commit/rollback 自身失败时兜底 rollback |
| 高 | python-docx run 拆分导致章节标题改写不全 (P1.3 + REPORT-H1 R6) | "电压纹波" 跨 run 时未被替换 | 基类 `_rewrite_titles_and_headers` 跨 run 拼接重建段落;等长替换按 run 边界回写保留字符样式 |
| 高 | xpp marker `in` 子串匹配 false positive (REPORT-H2 R6) | 工况名含 'IPPC'/'VPPT' 等被误识别为 ripple marker | 改用正则锚定 `^\d+(?:\.\d+)?[IVXivx]pp$` (大小写不敏感) |
| 高 | init mass-import 无确认 (VDB-H5 R6) | 用户误触发数小时全量导入 | 加 `click.confirm` + `--yes/-y` 标志支持 CI |
| 高 | slope 报告"标准要求"含 ripple 阈值文案 (NEW-5 R6+) | slope 报告内容错误, build_compliance 始终返回 "—", adapt 仅删除 ripple 阈值未插 slope 阈值 | slope_report.py 三处方法重写: build_result_text 加"最大值绝对值"措辞+末尾阈值断言句; build_compliance 实现 abs > 20000 判定 (电压 V/s 电流 A/s); adapt_standard_requirement ripple→slope 整句替换 + 全角逗号变体 + 兜底替换 (电压纹波/电流纹波/峰峰值/30Vpp/100App) |
| 中 | cache schema 无版本号 (CR-N3) | 升级后用户混淆"算法变 vs 数据变" | `_schema_version: 2` + `_load_cache` 检测打印升级日志 |
| 中 | stage1 manual_required 写 cache (NEW-3) | 用户未跑 GUI 但 cache 标完成 | status 改 "manual_required",`_update_stage_cache` 仅对 "success" 触发 |
| 中 | scan_vehicles 误匹配非标命名 (NEW-4) | V0001abc / V0001.backup 等被识别为车辆 | `re.fullmatch(r'V\d+', name)` |
| 中 | vehicle_info md/xlsx 同时存在时 mtime 差异无警告 (HR-N7) | 用户改 xlsx 期望生效但 md 优先 | mtime 差异 > 60s 打印 [WARN] + xlsx 解析失败显式日志 |
| 中 | datetime.now() naive 导致 DST 二义性 (HR-N8) | 跨时区/DST 切换日有歧义 | 13 处全部改 `datetime.now(timezone.utc)` |
| 低 | vehicle_info* 旧版残留无警告 (CR-N11) | 用户改 vehicle_info1.xlsx 无效但不知道 | batch 启动预检 + [WARN] 提示 |
| 低 | 非组件文件 (zip/rar/docx) 静默丢弃 (NEW-7) | 用户以为已处理但实际遗漏 | `_discover_components` 检测可疑文件给 warning |
| 低 | template fingerprint 不可见 (HR-N2) | template 改 1 字符 → 24 辆车全员 stage3 重跑,用户困惑 | `print_plan` 显示 template mtime + sha256 |
| 低 | init.py mass-import 副作用未文档化 (HR-N3) | 用户运行 init 触发全量导入,以为只建 schema | docstring 详细说明 + 显眼 [WARN] echo |

**已知遗留缺陷**:

| 优先级 | 问题 | 影响 | 计划 |
|:------:|------|------|----------|
| 低 | _files_fingerprint 用 p.name 而非 relative_to | 两个不同目录下同名文件理论上指纹冲突 (生产场景未观察到) | v1.6 hotfix P3.1 已修, 用 relative_to(vehicle_dir) |
| —  | (HR-N5 模板复用问题已通过 NEW-5 R6+ 代码补正,无需重制模板) | — | — |

**架构改动**:

- **数据库目录迁移**: `F:/Vehicle_Date/Vehicle_Database/` → `F:/Vehicle_Database/`
- **`~/.vehicle_database/config.json` 多字段同步**: 顶级 `database_path` + 嵌套 `database.default_path` + `git.repo_path`
- **SKILL.md 版本号**: vehicle-ripple-data V4.3 → V4.4, vehicle-slope-data V1.2 → V1.3
- **CHANGELOG.md**: vehicle-ripple-data 新增 `[4.4.0] - 2026-05-11`

**新增 CLI 行为**:

- `vehicle_database.py add` exit 码: 0 (全部成功) / 2 (完全失败) / 3 (部分失败)
- `vehicle_database.py init` 新增 `--yes/-y` 跳过确认
- `incremental_workflow.py batch` 新增 **二次规划** (stage2 完成后自动重新规划 stage3/4)
- `incremental_workflow.py plan` 显示 template fingerprint (mtime + sha256)
- `incremental_workflow.py` partial 状态分类: success / manual_required / partial / failed / timeout / error

**新增警告类型** (操作员参考):

| 警告 | 触发条件 | 修复 |
|:------|:--------|:----|
| `[WARN] cache 损坏` | `_load_cache` JSONDecodeError | 自动从 .bak 恢复 |
| `[WARN] {vid}: vehicle_info.md 与 .xlsx mtime 差异较大` | 两文件 mtime 差 > 60s | 选择一种格式编辑 |
| `[WARN] {vid}: 发现非标准 vehicle_info 文件` | 检测到 `vehicle_info1.xlsx` 等 | 清理或重命名 |
| `[WARN] 忽略非组件文件` | 顶级目录有 zip/rar/docx 等 | 检查文件位置 |
| `[WARN] init will auto-import ALL vehicles` | 用户运行 init | 改用 `add <vid>` 增量导入 |
| `[INFO] cache schema v1 -> v2 升级检测` | 旧 cache 加载 | 一次性触发 stage2 重跑 |

---

## 十四、技术栈汇总

| 阶段/工具 | 技能/工具 | 核心技术 | 输入 | 输出 |
|-----------|-----------|----------|------|------|
| 阶段1 | AutoHandleFiles | PySide6, pyDmdReader, datashader, scipy, numpy | .dmd | .xlsx, .png |
| 阶段2a | vehicle-ripple-data | pandas, openpyxl, sqlite3, fuzzywuzzy | statistics.xlsx, .png | .xlsx, .db, .json, .md |
| 阶段2b | vehicle-slope-data | pandas, openpyxl, sqlite3, fuzzywuzzy | statistics.xlsx, .png(可选) | .xlsx, .db, .json, .md |
| 阶段2.5 | validate_cross_format | pandas, sqlite3, json | .json/.db/.xlsx | error_report.md (首行插入) |
| 阶段3 | vehicle-report-generation | python-docx, openpyxl | .xlsx/.db + .png | .docx |
| 阶段4 | vehicle-database | sqlite3, pandas, click | .json/.db/.xlsx | Ripple.db + Slope.db |
| 增量引擎 | workflow-orchestrator | hashlib, subprocess, pathlib | 各阶段输入/输出指纹 | .workflow_cache.json |
| 规则管理 | rule_manager | re, pathlib, yaml(可选) | .md规则文件 | 版本化规则加载 |

---

## 十五、待完善事项与版本历史

### 高优先级

1. **AutoHandleFiles 内存优化**
   - 现状: 大.dmd文件触发MemoryError
   - 目标: 支持>10GB文件稳定处理
   - 方案: 优化`getMinMaxSegdatas_and_mmap`的分块策略

2. **AutoHandleFiles 多线程修复**
   - 现状: ThreadPoolExecutor并发清理临时文件冲突
   - 目标: 无WinError 32文件占用错误
   - 方案: 串行清理或引入文件锁机制

3. **AutoHandleFiles .temp目录创建**
   - 现状: 偶发FileNotFoundError
   - 目标: 目录创建与写入原子化
   - 方案: 所有写操作前强制`os.makedirs`

### 已完成 (V3.0)

4. **批量报告生成自动化** ✅
   - 已实现: `vehicle_report_cli.py batch F:/Vehicle_Date --type all`

5. **跨阶段数据一致性校验** ✅
   - 已实现: `validate_cross_format.py` 自动在阶段2后执行

6. **工况规则版本管理** ✅
   - 已实现: `rule_manager.py` 支持 `@import` / YAML frontmatter / 传统格式

7. **一键增量工作流脚本** ✅
   - 已实现: `incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date`
   - 支持增量处理、指纹比对、强制重跑、阶段过滤

### 已完成 (V3.1)

8. **阶段2.5后自动触发阶段3报告生成** ✅
   - 已实现: `vehicle_skills_cli.py process V0001 --auto-report`
   - 通过 `--auto-report` / `-r` 参数开启，阶段2成功后自动调用 `vehicle_report_cli.py generate`
   - 非阻断设计: 报告生成失败不影响主流程
   - 支持单车辆 `process` 和批量 `batch` 两种模式
   - 批量汇总表格新增 `Report` 列显示报告生成状态

### 已完成 (V3.2)

9. **纹波报告电流/电压通道单位修复** ✅
   - 问题: 电流通道(如`DCC_A`)错误显示"电压纹波"、单位"Vpp"、阈值"30Vpp"
   - 修复: `ripple_report.py` 根据 `component_code.endswith("_A")` 动态切换
     - `_A`→"电流纹波/App/100App"，`_V`→"电压纹波/Vpp/30Vpp"
   - 同步修改: `adapt_standard_requirement()` 转换Word模板"标准要求"列文本

10. **斜率报告电流/电压单位区分** ✅
    - 问题: 电流斜率通道错误显示"电压斜率/V/s"
    - 修复: `slope_report.py` 根据 `_A`/`_V` 后缀切换
      - `_A`→"电流斜率/A/s"，`_V`→"电压斜率/V/s"
    - 同步修改: `adapt_standard_requirement()` 将"纹波"替换为"斜率"并删除限值语句

### 已完成 (V3.3)

11. **增量引擎批量模式** ✅
    - 已实现: `incremental_workflow.py batch --scan F:/Vehicle_Date`
    - 支持扫描目录下所有车辆，逐车增量处理，聚合汇总报告
    - 单车辆失败不阻断后续车辆，日志保存至 `.workflow_batch_log.json`
    - 支持 `--force` 强制全量重跑，`--stages` 阶段过滤

12. **阶段2 slope 重复处理修复** ✅
    - 问题: `vehicle_skills_cli.py process` 已同时处理 RIPPLE 和 SLOPE，`stage2_slope` 又单独调用 `process_slope.py` 导致 SLOPE 被处理两次
    - 修复: `_decide_stage2_slope()` 增加覆盖判断，当 `stage2_ripple` 会执行时，SLOPE 标记为"由 stage2_ripple 统一处理"而跳过

### 已完成 (V3.6 / v1.4 整改批次, 2026-05-11)

19. **数据库目录迁移** ✅
    - `F:/Vehicle_Date/Vehicle_Database/` → `F:/Vehicle_Database/`
    - config.json 多字段同步 (顶级 `database_path` + 嵌套 `database.default_path` + `git.repo_path`)
    - 旧单库时代遗留 (`vehicle_database.db`) 清理

20. **importer 真正原子性 (NEW-1 + CR-N4)** ✅
    - 3 个 importer 内部去 `conn.commit()`,异常时 re-raise (不再吞)
    - `import_vehicle` 前 `DELETE FROM ripple_results/slope_results WHERE vehicle_id = ?`
    - add.py 用 `SAVEPOINT/RELEASE/ROLLBACK TO` 隔离每辆车,失败仅回滚当前车

21. **exit 码契约 + partial 状态 (CR-N7 + P1.8)** ✅
    - add.py exit 0 (成功) / 2 (完全失败) / 3 (部分失败)
    - orchestrator 识别 partial → 不更新 cache → 下次重试
    - batch_run 引入 PARTIAL 状态,与 OK/SKIP/FAIL/ERROR 单独统计

22. **cache 原子写 + .bak 回退 (CR-N8)** ✅
    - tmp + fsync + os.replace + retry 处理 Windows 文件锁
    - 损坏时自动从 `.workflow_cache.json.bak` 回退
    - `clear_cache` 同时清理 .bak/.tmp

23. **batch_log 增量原子写 + try/except (CR-N9 + P2.5/P2.7)** ✅
    - 每辆车完成后立即原子写 `.workflow_batch_log.json` (partial=true 标记)
    - 单车循环 try/except,异常车记 ERROR 状态,不中断整批

24. **stage4 single-flight 守护 (C1 R6)** ✅
    - 改 class-level flag (`_stage4_missing_handled_global`)
    - batch_run 起始时 `IncrementalWorkflow.reset_stage4_single_flight()`
    - 失败/partial 时重置允许下一车重试

25. **vehicle_info 纳入 stage2 指纹 (P1.5 + CR-N2)** ✅
    - stage2_ripple/slope 输入新增 `vehicle_info.md/xlsx`
    - 新增 `_semantic_fingerprint`: xlsx 用 openpyxl cell hash, md 规范化换行
    - `_files_fingerprint_smart` 路由: vehicle_info 走语义指纹

26. **cache schema version (P1.6)** ✅
    - `_schema_version: 2`,旧 cache 加载时打印升级日志
    - 升级后首次 batch 自动触发全部车辆 stage2 一次性重跑

27. **stage3 章节标题+表头改写 (P1.3 + REPORT-H1)** ✅
    - 基类 `_rewrite_paragraph_text` + `_rewrite_titles_and_headers`
    - 跨 run 拼接重建,等长替换按 run 边界回写保留字符样式
    - generate() 模板加载后立即调用

28. **二次规划 (P1.4c)** ✅
    - batch_run 内 stage2 完成后自动重新规划,挂入新出现的 stage3/4
    - 避免新车辆需要两轮 batch

29. **stage1 manual_required 不写 cache (NEW-3)** ✅
    - status="manual_required" (不是 "success")
    - `_update_stage_cache` 仅对 "success" 触发

30. **xpp marker 正则锚定 (REPORT-H2 + CR-N5)** ✅
    - 模块级 `_RIPPLE_MARKER_PATTERN = re.compile(r'^\d+(?:\.\d+)?[IVXivx]pp$', re.IGNORECASE)`
    - 拒绝 false positive (IPPC/VPPT/Ipp123 等不再误识别)
    - 仍兼容大小写混合 (Ipp/Vpp/xpp/IPP/VPP/XPP/...)

31. **scan_vehicles 严格正则 (NEW-4)** ✅
    - `re.fullmatch(r'V\d+', name)` 避免 V0001abc / V0001.backup 等误识别

32. **vehicle_info md/xlsx mtime 警告 (HR-N7)** ✅
    - 两者都存在时 mtime 差异 > 60s 打印 [WARN]
    - xlsx 解析失败时显式错误日志 (而非静默 pass)

33. **非组件文件警告 (NEW-7)** ✅
    - 顶级目录有 .zip/.rar/.7z/.tar/.gz/.docx/.pdf 给 warning
    - vehicle_info* 非标命名 (vehicle_info1.xlsx) 给 [WARN] (CR-N11)

34. **datetime UTC 时间戳 (HR-N8)** ✅
    - 13 处 `datetime.now()` → `datetime.now(timezone.utc)`

35. **DatabaseConnection.__exit__ 原子性 (VDB-H1)** ✅
    - try/finally 保证 close;commit/rollback 自身失败时兜底

36. **init.py mass-import 确认 (HR-N3 + VDB-H5)** ✅
    - 显眼 [WARN] echo + `click.confirm` 交互确认
    - 新增 `--yes/-y` 跳过 (供 CI 自动化)

37. **validator sentinel upsert (P1.2)** ✅
    - error_report.md 校验块用 `<!-- cross-format-validation:start/end -->` 包裹
    - 反复运行不再累积重复内容

38. **template fingerprint 日志 (P3.5 + HR-N2)** ✅
    - `print_plan` 显示 template mtime + sha256
    - 帮助用户识别"为何 stage3 全员重跑"

39. **SOC 编码统一为全角 (P1.1 + MED-5)** ✅
    - `condition_matcher.py:332-336` 半角 `>=70%` → 全角 `≥70%`
    - `vehicle_processor.py:_get_soc_level` 改字面 `≥/≤` (原 ≥ escape 让 grep 漏匹配)
    - `validate_cross_format.py:435` SOC dict 改全角
    - 7 个测试 fixture 文件批量改全角 (test_importers.py:363 保留半角用于输入识别测试)

40. **slope 报告内容修复 (NEW-5 R6+)** ✅
    - **背景**: slope_report_template.docx 是 ripple 模板字节相同副本 (sha256: cea9fd2e...),
      模板复用本身合理 (`_rewrite_titles_and_headers` 跨 run 改写),但 slope_report.py 代码
      未正确补齐斜率阈值,导致 slope 报告内容错误。
    - **修复**:
      - `build_result_text`: 加"最大值绝对值"措辞 + 末尾阈值断言句 (电压 20000V/s, 电流 20000A/s)
      - `build_compliance`: 实现 abs > 20000 阈值判定 (此前硬编码返回 "—")
      - `adapt_standard_requirement`: ripple→slope 整句替换 + 全角逗号变体 + 兜底替换
        ("电压纹波"/"电流纹波"/"峰峰值"/"30Vpp"/"100App" → 斜率对应文案)
    - **影响**: V0001-V0024 共 58 份 slope 报告重新生成,验证 "30Vpp"/"100App" 0 残留,
      "电压斜率/电流斜率/20000V/s/20000A/s" 全部正确;V0004 FM_A 显示 4 处"不符合"
      (证明 build_compliance 阈值判定生效)
    - **不影响 ripple**: V0001 FM_V 仍保持 110×电压纹波 / 49×30Vpp / 0×斜率文案

41. **v1.6 hotfix 全面整改 (R7)** ✅
    - **NEW-1 update.py 原子性**: 完全按 add.py 重写 (ExitStack + SAVEPOINT + exit code 0/2/3)
    - **CR-N6 snapshot 命令**: incremental_workflow.py 新增 `snapshot` 子命令 (shutil.make_archive 跨平台)
    - **incremental_processor.py 原子写**: `_atomic_save_json` 工具函数 (tmp+fsync+os.replace+.bak+retry)
    - **excel_reader.py V0006 硬编码**: L137/L168 异常消息改 `{vehicle_id}` 参数化
    - **sqlite_importer.py raise**: L70-79/L88-98 改 `raise` 与 json/excel 一致 (NEW-1 一致性)
    - **slope_processor NEW-7 同步**: `_discover_components` 加 elif is_file + suspicious_exts
    - **remove.py try/except**: 加单车异常隔离避免 removed_count 状态不一致
    - **_files_fingerprint relative_to**: 改用相对路径避免不同目录同名文件冲突

**SKILL.md 同步**:
- `vehicle-ripple-data/SKILL.md` V4.3 → V4.4 + `CHANGELOG.md` 新增 `[4.4.0]`
- `vehicle-slope-data/SKILL.md` V1.2 → V1.3 + Version History 段

**遗留 (v1.6 hotfix 后)**: 无致命/高优 遗留

### 已完成 (V3.5)

14. **SOC提取多分隔符兼容** ✅
    - 问题: V0006/V0009/V0010/V0017 等车辆使用 `-` 或空格作为 condition_id 分隔符，旧正则 `r'(\d+)_.*'` 仅支持下划线，导致大量 SOC 被标记为 Unknown
    - 修复: 统一正则 `_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')` 同时支持 `_` `-` `空格` 三种分隔符
    - 涉及的组件: `vehicle_processor.py`, `slope_processor.py`, `generate_excel_report.py`, `condition_matcher.py`

15. **坡度前缀 GBK 乱码处理** ✅
    - 问题: xlsx 文件以 GBK 编码保存时，"坡度"被读取为乱码（如 `�¶�`），导致 `condition_id.startswith('坡度10_')` 判断失败，爬坡工况无法正确提取 SOC 和匹配图片
    - 修复: 新增 `_normalize_condition_id()` 方法，将 `^�¶�\s*10(?![0-9])` 统一替换为 `坡度10`，确保 xlsx 中的 condition_id 与图片文件名一致
    - 涉及的组件: `vehicle_processor.py`, `slope_processor.py`

16. **图片文件名非标准标记 `xpp` 兼容** ✅
    - 问题: V0017 纹波数据中有 2 个图片文件使用 `xpp` 标记（如 `0.70xpp`），不在原 `Ipp`/`Vpp`/`ipp`/`vpp` 检测列表中，导致 "未找到Vpp/Ipp标记" 警告，condition_id 解析失败
    - 修复: 扩展标记检测为 `any(marker in part for marker in ('Ipp', 'Vpp', 'ipp', 'vpp', 'xpp', 'Xpp'))`
    - 涉及的组件: `vehicle_processor.py`

17. **图片文件名首尾空格处理** ✅
    - 问题: V0017 纹波有 2 个图片文件名末尾有空格（如 `...0.010A .png`），`img_file.stem` 保留空格，导致提取的 condition_id 带空格，与 xlsx 中经 `.strip()` 处理的 condition_id 无法匹配
    - 修复: `img_stem = img_file.stem.strip()` 在解析前去除首尾空格
    - 涉及的组件: `vehicle_processor.py` (纹波), `slope_processor.py` (斜率, 防御性修复)

18. **condition_matcher 特征提取分隔符兼容** ✅
    - 问题: `condition_matcher.py` 的 `_extract_features()` 方法使用 `r'^(\d+)_(.*)'` 提取 SOC，对 `-` 和空格分隔符失效
    - 修复: 改为 `r'^(\d+)[_\-\s](.*)'`，与主 SOC 提取逻辑保持一致
    - 涉及的组件: `condition_matcher.py`

### 已完成 (V3.4)

13. **统一数据库双库分离** ✅
    - 问题: 单 `vehicle.db` 同时存放 `ripple_results` 和 `slope_results`，查询易混淆；`_delete_vehicle` 连接单库时因表不存在报错
    - 修复: 拆分为 `Ripple.db` + `Slope.db` 双库架构
      - `Ripple.db`: vehicles/components/test_conditions/ripple_results/data_batches/matching_logs
      - `Slope.db`: vehicles/components/test_conditions/slope_results/data_batches/matching_logs
    - 新增 `RIPPLE_SCHEMA` + `SLOPE_SCHEMA`，保留 `ALL_SCHEMA` 向后兼容
    - `resolve_database_path()` 返回数据库目录（向后兼容：`-d` 指向 `.db` 文件时自动提取 parent）
    - `import_vehicle()` 根据 `source.data_type` 自动路由到对应库
    - `list/show/stats/export` 添加 `--type ripple|slope` 参数（默认 `ripple`）
    - `JsonExporter` 添加 `data_type` 参数，动态选择结果表名
    - `_delete_vehicle()` 添加 `data_type` 参数，只删除对应类型结果表
    - 规划书修正：五↔六阶段编号互换

### 中优先级

9. **数据库直连报告生成**
   - 现状: 优先读Excel，失败回退SQLite
   - 目标: 可直接从统一vehicle.db生成
   - 方案: 增加`--from-db`模式
   - **注意**: V3.4 已改为双库架构，需同时支持 Ripple.db + Slope.db

10. **AutoHandleFiles 内存优化**
    - 现状: 大.dmd文件触发MemoryError
    - 目标: 支持>10GB文件稳定处理
    - 方案: 优化`getMinMaxSegdatas_and_mmap`分块策略

### 低优先级

11. **报告模板自定义**
    - 支持不同车型/项目切换报告模板

12. **数据可视化仪表盘**
    - 基于vehicle.db构建Web查询界面

13. **历史数据对比分析**
    - 多车辆/多批次横向对比

---

*文档结束*
