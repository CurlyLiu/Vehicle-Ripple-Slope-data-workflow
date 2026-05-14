# Vehicle Ripple / Slope Test Data Processing Workflow

# 车辆纹波/斜率测试数据处理完整工作流

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Version**: V3.6 | **Last Updated**: 2026-05-11 | **Status**: v1.4 Production Ready
>
> A complete workflow for acquiring, integrating, managing, and reporting vehicle high-voltage ripple and voltage slope test data.

---

## Table of Contents / 目录

- [Quick Start / 快速开始](#quick-start--快速开始)
- [Workflow Overview / 工作流总览](#workflow-overview--工作流总览)
- [Stage 1: Raw Data Analysis (AutoHandleFiles)](#stage-1-raw-data-analysis-autohandlefiles)
- [Stage 2: Data Integration](#stage-2-data-integration)
- [Stage 2.5: Cross-Format Validation](#stage-25-cross-format-validation)
- [Stage 3: Report Generation](#stage-3-report-generation)
- [Stage 4: Unified Database Management](#stage-4-unified-database-management)
- [Incremental Processing Engine](#incremental-processing-engine)
- [Condition Rule Version Management](#condition-rule-version-management)
- [Folder Structure Convention](#folder-structure-convention)
- [Execution Flow / 执行流程](#execution-flow--执行流程)
- [CLI Command Reference / CLI命令参考](#cli-command-reference--cli命令参考)
- [Data Mapping & Encoding Specs / 数据映射与编码规范](#data-mapping--encoding-specs--数据映射与编码规范)
- [Known Issues & Solutions / 已知问题与解决方案](#known-issues--solutions--已知问题与解决方案)
- [Tech Stack / 技术栈汇总](#tech-stack--技术栈汇总)
- [Version History / 版本历史](#version-history--版本历史)

---

## Quick Start / 快速开始

### Single Vehicle / 单车辆处理

```bash
# Step 1: Use AutoHandleFiles GUI to process .dmd raw data
# Step 2: Put vehicle_info.md in the vehicle folder
# Step 3: Run data integration (auto-detects ripple + slope)
cd vehicle-ripple-data
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress --auto-report

# Step 4: Import to unified database
cd ../vehicle-database
python vehicle_database.py -s E:/Vehicle_Date add V0001
```

### Batch Processing (Recommended) / 批量处理（推荐）

```bash
cd workflow-orchestrator
python incremental_workflow.py batch --scan F:/Vehicle_Date
```

The incremental engine automatically skips unchanged stages, significantly improving batch processing efficiency.

---

## Workflow Overview / 工作流总览

```
Dewesoft .dmd Raw Data
         |
         v
+-------------------------------+
| Stage 1: AutoHandleFiles      |  PySide6 GUI, pyDmdReader, scipy
| Ripple + Slope + Filter + FFT |
+-------------------------------+
         |
         |---> {VehicleID}_RIPPLE/   --> 7-col statistics.xlsx + 1 .png per condition
         |                              --> Multiple standard channels
         |
         |---> {VehicleID}_SLOPE/    --> 4-col statistics.xlsx (slope stats)
                                       --> Same channels as above
         |
         v
+-------------------------------------------+
| Stage 2: Data Integration (+ Rule Mgmt)   |
| vehicle-ripple-data / vehicle-slope-data  |
| Naming rules: default <- parent override  |
+-------------------------------------------+
         |
         |---> {VehicleID}_RIPPLE_output/
         |      |-- {VehicleID}_RIPPLE_summary.xlsx
         |      |-- {VehicleID}_RIPPLE.db
         |      |-- {VehicleID}_RIPPLE_data.json
         |      +-- error_report.md
         |
         |---> {VehicleID}_SLOPE_output/
                |-- {VehicleID}_SLOPE_summary.xlsx
                |-- {VehicleID}_SLOPE.db
                |-- {VehicleID}_SLOPE_data.json
                +-- error_report.md
         |
         v
+-------------------------------+
| Stage 2.5: Cross-Format       |  Auto-executed, non-blocking
| Validation                    |
| validate JSON/SQLite/Excel    |
+-------------------------------+
         | (failure written to error_report.md top, flow continues)
         |
         |---> [Optional] --auto-report triggers Stage 3
         |
         v
+-------------------------------+
| Stage 3: Report Auto-Generate |  python-docx, openpyxl
| vehicle-report-generation     |
| SOC grouping -> fill tables   |
| -> insert images              |
+-------------------------------+
         |
         |---> {VehicleID}_RIPPLE_REPORT_{ComponentCode}.docx
         |---> {VehicleID}_SLOPE_REPORT_{ComponentCode}.docx
         |
         v
+-------------------------------+
| Stage 4: Unified Database     |  sqlite3, click CLI
| vehicle-database              |
| Multi-format aggregation      |
+-------------------------------+
         |
         +---> F:/Vehicle_Database/
                |-- Ripple.db  (ripple data)
                +-- Slope.db   (slope data)

========================================================================
|  Incremental Engine (workflow-orchestrator)                          |
|  Cross-stage coordination, avoids redundant computation              |
|  Cache: {VehicleID}/.workflow_cache.json                             |
|  Function: fingerprint comparison -> decide stages -> call CLI       |
========================================================================
```

### Stage Responsibility Boundaries

| Stage | Responsibility | Does NOT Do |
|-------|---------------|-------------|
| **Stage 1** | Calculate ripple/slope from .dmd raw data, generate statistics Excel and images | No condition mapping, no SOC grading, no data integration |
| **Stage 2** | Integrate statistics Excel + images, map condition names, SOC grading, generate unified format | No .dmd reading, no signal processing |
| **Stage 2.5** | Auto-validate Stage 2 output JSON/SQLite/Excel consistency | No data modification, does not block subsequent stages |
| **Stage 3** | Read Stage 2/4 output, generate Word test reports by template | No source data modification, no recalculation |
| **Stage 4** | Aggregate multi-vehicle data to unified database, provide query/export CLI | No image generation, no statistical analysis |
| **Auto-trigger** | `vehicle_skills_cli.py --auto-report` auto-calls Stage 3 after Stage 2.5 | Does not replace manual `vehicle_report_cli.py` command |
| **Incremental** | Cross-stage coordination, fingerprint comparison decides rerun scope | Does not replace core stage logic |

---

## Stage 1: Raw Data Analysis (AutoHandleFiles)

### Software Architecture

AutoHandleFiles is a PySide6 desktop application, packaged as a PyInstaller single-file executable.

```
AutoHandleFiles.exe (PyInstaller, Python 3.8)
    |
    +-- PYZ-00.pyz (compressed Python libs)
    |   +-- src/AutoHandleFiles.pyc      <- PySide6 MainWindow GUI
    |   +-- src/dmd_process.pyc          <- Core processing engine (~1300 lines)
    |   +-- src/signal_filter.pyc        <- Digital filters (Butterworth/Bessel)
    |   +-- src/function_filter.pyc      <- Outlier filtering (Hampel etc.)
    |   +-- pyDmdReader/                 <- Dewesoft .dmd read library
    |
    +-- _internal/
        +-- dmd_reader_api.dll           <- Dewesoft native read interface
```

### Core Processing Engine (dmd_process)

**Main Methods:**

| Method | Function |
|--------|----------|
| `calculateChannel()` | Main entry: iterate channels, dispatch ripple/slope calculation |
| `generateOverViewImage()` | Generate time-domain waveform overview (datashader renders millions of points) |
| `generateFFTImage()` | Generate FFT spectrum (scipy.signal.stft) |
| `generateVppImage()` | Generate VPP (peak-to-peak) distribution |
| `generateVoltageSlopeImage()` | Generate voltage slope analysis chart |
| `getMinMaxSegdatas_and_mmap()` | Large file memory-mapped chunked reading |
| `process_segment()` | Single segment processing (filter -> FFT -> statistics) |

**Signal Processing Pipeline:**

```
.dmd raw data
    |
    +---> pyDmdReader read -> numpy array
    |
    +---> Signal filtering (optional)
    |      +-- Butterworth low/high/band pass
    |      +-- Bessel low/high/band pass
    |
    +---> Outlier handling (optional)
    |      +-- Top percentage zeroing
    |      +-- Hampel filter
    |
    +---> Ripple analysis path
    |      +-- Time-domain: VPP (peak-to-peak), RMS
    |      +-- FFT spectrum: peak frequency, peak amplitude, RMS
    |      +-- Output: statistics.xlsx (7 cols) + 1 .png per condition
    |
    +---> Slope analysis path
           +-- Calculate dV/dt (voltage change rate)
           +-- Output: statistics.xlsx (4 cols: max/min/abs max)
```

### Output Data Structure

#### Ripple Output ({VehicleID}_RIPPLE/)

Each component folder contains:
- `statistics.xlsx` -- 7-column statistics table
- `*.png` -- One result image per condition

**statistics.xlsx Format (Ripple):**

| Col Index | Column Name | Description | Unit |
|:---------:|:------------|:------------|:----:|
| 0 | Data Name | Condition identifier, e.g. `87_Overtake80-140(Sport)` | -- |
| 1 | Full-segment RMS | Signal RMS | V/A |
| 2 | Time-domain VPP | Peak-to-Peak | V/A |
| 3 | Peak Ranking | Spectrum peak ranking detail (text) | -- |
| 4 | FFT Peak Frequency (kHz) | Max peak frequency in FFT spectrum | kHz |
| 5 | FFT Peak Amplitude | Amplitude at that frequency | V/A |
| 6 | FFT RMS | Frequency-domain RMS | V/A |

**Image Filename Formats (Two Types):**

```
Standard format:
  {SOC}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
  Example: 87_Overtake80-140_LV_V_8.39VPP_0.61kHz-0.106V.png

Slope format:
  Slope10_{SOC}_{condition_desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
  Example: Slope10_32_Cruise80Cold_LV_V_1.85VPP_3.94kHz-0.054V.png
```

**Image Filename Parsing Notes (V3.5+):**
- **Ipp/Vpp marker detection**: Supports `Ipp`/`Vpp`/`ipp`/`vpp` standard markers, also compatible with non-standard `xpp`/`Xpp` (e.g. `0.70xpp`)
- **Leading/trailing space handling**: Trailing spaces in filenames (e.g. `0.010A .png`) are auto-stripped to avoid condition_id matching failures
- **condition_id extraction**: Extracts all content before the channel marker (Ipp/Vpp/xpp) from the image filename stem as condition_id

#### Slope Output ({VehicleID}_SLOPE/)

Each component folder contains:
- `statistics.xlsx` -- 4-column statistics table
- `*.png` (optional) -- Slope analysis charts, scanned by Stage 2 if present

**statistics.xlsx Format (Slope):**

| Col Index | Column Name | Description | Unit |
|:---------:|:------------|:------------|:----:|
| 0 | Filename | Condition identifier | -- |
| 1 | Slope Max (V/s) | Max rising slope | V/s |
| 2 | Slope Min (V/s) | Max falling slope (negative) | V/s |
| 3 | Slope Abs Max (V/s) | Max absolute slope value | V/s |

**Slope Image Format (Optional):**
```
{condition_id}_{component_code}.png
Example: 87_Overtake80-140_FM_V.png
```

> **Note**: Slope image matching identifies via `_{component_code}` suffix, does not depend on Ipp/Vpp/xpp markers.
> V3.5 defensive fix: `.strip()` applied to `img_stem` to prevent future similar space issues.

### Known Issues & Improvement Suggestions

| Issue | Symptom | Root Cause | Improvement |
|-------|---------|------------|-------------|
| Large file MemoryError | Crash processing large .dmd | Insufficient numpy memory mapping strategy | Optimize `getMinMaxSegdatas_and_mmap` chunk size |
| Temp file cleanup conflict | WinError 32 file in use | ThreadPoolExecutor multi-thread race | Add file lock or serial cleanup |
| .temp subdirectory not created | FileNotFoundError | Directory creation vs write race | `os.makedirs(..., exist_ok=True)` before write |
| Partial .dmd corruption | FILE_INVALID error | Acquisition interruption or transfer corruption | Add file header validation, skip corrupted files |
| Multi-thread exception swallowed | Some channels have no output but no error | QThread exception not propagated to main thread | Add exception callbacks and logging |

---

## Stage 2: Data Integration

### Input Specifications

**Required Files (read from parent folder):**

| File | Format | Required | Description |
|------|--------|:--------:|:------------|
| `vehicle_info.md` | Markdown table | Yes | Vehicle parameters |
| `vehicle_info.xlsx` | Excel | Alternative | Alternative to vehicle_info.md |

**Optional Files (read from parent folder, default rules as fallback):**

| File | Format | Description |
|------|--------|:------------|
| `test_naming_rules.md` | Markdown table | Condition name mapping rules |
| `sensor_naming_rules.md` | Markdown/YAML | Channel code definitions |
| `setup.png/jpg` | Image | Vehicle photo |

**Rule Loading Priority (high to low):**
1. Parent folder custom rules (e.g. `V0001/test_naming_rules.md`)
2. Skill default rules (`references/test_naming_rules.md`)
3. Merge strategy: load default rules first, then override with parent folder rules

### vehicle-ripple-data (Ripple Data Integration)

#### Processing Flow

```
1. Validate parent folder -> extract VehicleID
2. Auto-discover {VehicleID}_RIPPLE/ subfolder
3. Load naming rules (default + parent merged)
4. Load vehicle info (UTF-8 -> GBK fallback)
5. Scan all component folders -> validate channel names one by one
6. For each component:
    +-- Read statistics.xlsx (use iloc[0-6], NOT column names)
    +-- Scan .png files -> parse filenames to extract metadata
    +-- Match condition_id (Excel <-> image)
    +-- Extract SOC from condition_id -> grading
    +-- Fuzzy match condition names
    +-- Build structured data
7. Output: Excel + SQLite + JSON + error_report.md
```

#### Key Processing Logic

**A. Encoding Handling (Critical)**

```python
# Read files containing Chinese
for encoding in ['utf-8', 'gbk']:
    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
        break
    except UnicodeDecodeError:
        continue

# Read statistics.xlsx (column names may be garbled)
condition_id    = str(row.iloc[0]).strip()   # NOT row['Data Name']
effective_value = row.iloc[1]
vpp             = row.iloc[2]
peak_ranking    = row.iloc[3]
freq_khz        = row.iloc[4]
peak_amp        = row.iloc[5]
rms             = row.iloc[6]
```

**B. SOC Extraction (Must extract directly from condition_id, NEVER rely on test_naming_rules)**

```python
# Module-level regex patterns (defined outside class, compile once)
_SLOPE_PREFIX_PATTERN = re.compile(
    r'^(Slope|\xC6\xC2\xB6\xC8)\s*10(?![0-9])[_\-\s]*(\d+)[_\-\s]',
    re.IGNORECASE
)
_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')

def _normalize_condition_id(self, condition_id: str) -> str:
    """Normalize condition_id, handle GBK garbled slope prefix

    GBK-encoded "Slope" may be read as garbled (e.g. \xC6\xC2\xB6\xC8),
    needs unified replacement with standard prefix to ensure
    condition_id in xlsx matches condition_id in image filenames.
    """
    if not condition_id:
        return condition_id
    return re.sub(r'^\xC6\xC2\xB6\xC8\s*10(?![0-9])', 'Slope10', condition_id)

def _extract_soc(self, condition_id: str) -> Optional[int]:
    """Extract SOC value from condition_id

    Supported delimiters: _ (underscore), - (dash), space
    Supported standard formats:
      - Normal: 55_DCChargeHeat -> SOC=55
      - Slope: Slope10_82_Cruise80Heat -> SOC=82
      - Dash sep: 55-DCChargeHeat -> SOC=55
      - Space sep: 55 DCChargeHeat -> SOC=55
    Supported GBK garbled:
      - \xC6\xC2\xB6\xC810_82_Cruise80Heat -> SOC=82 (after _normalize_condition_id)
    """
    if not condition_id:
        return None

    normalized = self._normalize_condition_id(condition_id)

    # Handle Slope10_ prefix (supports standard, GBK garbled, multiple delimiters)
    slope_match = _SLOPE_PREFIX_PATTERN.match(normalized)
    if slope_match:
        soc = slope_match.group(2)
        return int(soc) if soc else None

    # Normal condition: extract leading digit SOC (supports _, -, space)
    soc_match = _SOC_PATTERN.match(normalized)
    if soc_match:
        return int(soc_match.group(1))

    return None

def get_soc_level(soc):
    if soc is None:      return "Unknown"
    elif soc >= 70:      return "GE70%"
    elif soc >= 40:      return "40%-70%"
    else:                return "LE40%"
```

**C. Condition Name Fuzzy Matching (Four-Level Strategy)**

| Level | Strategy | Scenario | Example |
|:----:|----------|----------|---------|
| 1 | Exact match | condition_id completely identical | `87_Overtake80-140(Sport)` -> `Overtake` |
| 2 | Normalized match | Parenthesis difference `()` vs `()` | `87_Overtake80-140(Sport)` -> `Overtake` |
| 3 | Fuzzy match | Levenshtein distance < threshold | `87_Overtake80-140Sport` -> `Overtake` |
| 4 | Feature match | Extract keywords + SOC + slope flag | `\xC6\xC2\xB6\xC810_81_Cruise80Heat` (GBK garbled) -> `ClimbHeat` |

**Feature Extraction Supported Delimiters (V3.5 Update):**

```python
def _extract_features(self, condition_id: str) -> Dict[str, Any]:
    """Extract features from condition_id for fuzzy matching"""
    working_id = condition_id

    # 1. Handle slope prefix (supports standard, GBK garbled, multiple delimiters)
    slope_match = _SLOPE_PREFIX_PATTERN.match(working_id)
    is_slope = slope_match is not None
    if slope_match:
        working_id = working_id[slope_match.end():]

    # 2. Extract SOC (supports _, -, space)
    soc_match = re.match(r'^(\d+)[_\-\s](.*)', working_id)
    if soc_match:
        soc = soc_match.group(1)
        working_id = soc_match.group(2)  # Remove SOC prefix
    else:
        soc = None

    # 3. Extract keywords (from description part)
    keywords = self._extract_keywords(working_id)

    return {
        'soc': soc,
        'is_slope': is_slope,
        'keywords': keywords,
        'original': condition_id
    }
```

**D. Image Filename Parsing (Two Formats)**

```python
# Standard: {SOC}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amp}{unit}.png
# Slope: Slope10_{SOC}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amp}{unit}.png
# condition_id = all content before the channel marker (Ipp/Vpp/xpp)
```

**Parsing Logic (V3.5 Update):**

```python
def _parse_image_filenames(self, img_dir: Path) -> List[Dict[str, Any]]:
    """Parse image filenames, extract condition_id and measurement metadata"""
    result = []
    for img_file in sorted(img_dir.glob('*.png')):
        # 1. Strip leading/trailing spaces (handle "0.010A .png" trailing space)
        img_stem = img_file.stem.strip()

        # 2. Split filename by _
        parts = img_stem.split('_')

        # 3. Find Ipp/Vpp/xpp marker position, determine channel boundary
        marker_index = -1
        for i, part in enumerate(parts):
            if any(marker in part for marker in ('Ipp', 'Vpp', 'ipp', 'vpp', 'xpp', 'Xpp')):
                marker_index = i
                break

        if marker_index == -1:
            # Marker not found, log warning and skip
            continue

        # 4. condition_id = all content before channel marker
        condition_parts = parts[:marker_index]
        condition_id = '_'.join(condition_parts)

        # 5. Extract channel (part before marker position)
        channel = parts[marker_index - 1] if marker_index > 0 else ''

        # ... continue parsing frequency, amplitude etc.
        result.append({
            'condition_id': condition_id,
            'channel': channel,
            'file_path': str(img_file),
            # ... other metadata
        })

    return result
```

**Key Improvements:**

| Improvement | Description |
|-------------|-------------|
| `.strip()` handling | Removes leading/trailing spaces, avoids `"18_ParkD_Cold_ACCM_A"` vs `"18_ParkD_Cold_ACCM_A "` mismatch |
| `xpp`/`Xpp` support | Extends marker detection for non-standard unit markers |
| Delimiter tolerance | condition_id internally uses `_`, but SOC extraction supports `_`/`-`/`space` |

#### Output Files

| File | Description |
|------|:------------|
| `{VehicleID}_RIPPLE_summary.xlsx` | 3 Sheets: Vehicle Info / Component Summary / Detailed Results |
| `{VehicleID}_RIPPLE.db` | SQLite DB: vehicles/components/conditions/test_results |
| `{VehicleID}_RIPPLE_data.json` | Complete structured JSON with all measurement data |
| `error_report.md` | Chinese processing report, records success/warnings/errors |

#### SQLite Schema (Ripple)

```sql
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY,
  vehicle_model TEXT,
  vehicle_info TEXT  -- JSON string storing full 27 parameters
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

### vehicle-slope-data (Slope Data Integration)

#### Key Differences from Ripple

| Dimension | vehicle-ripple-data | vehicle-slope-data |
|-----------|:-------------------:|:------------------:|
| Folder suffix | `_RIPPLE` | `_SLOPE` |
| statistics columns | 7 | 4 |
| Image files | **Required** (1 per condition) | **Optional** (scanned if present) |
| Data unit | V / A | V/s |
| DB table name | `test_results` | `slope_results` |
| Excel detail columns | Time VPP / FFT Peak / RMS | Slope Max / Min / Abs |

#### Processing Flow

Same as ripple, with differences:
1. Validate 4-column format when reading statistics.xlsx
2. Images optional: if `{condition_id}_{component_code}.png` exists, scan and match
3. Data fields mapped to slope_max / slope_min / slope_max_abs

#### SQLite Schema (Slope)

```sql
-- vehicles, components, conditions same as ripple

CREATE TABLE slope_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vehicle_id TEXT,
  component_code TEXT,
  condition_id TEXT,
  slope_max REAL,
  slope_min REAL,
  slope_max_abs REAL,
  unit TEXT DEFAULT 'V/s',
  image_path TEXT,  -- optional, records path if image exists
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
  FOREIGN KEY (component_code) REFERENCES components(component_code),
  FOREIGN KEY (condition_id) REFERENCES conditions(condition_id)
);
```

---

## Stage 2.5: Cross-Format Validation

### Functional Positioning

Automatically executed after Stage 2 (vehicle-ripple-data / vehicle-slope-data) processing completes and before Stage 3 report generation. Validates JSON / SQLite / Excel output consistency to ensure no data loss or errors during integration.

**Compatibility Strategy**: Validation failure does not block subsequent stages, only inserts error report at the top of `error_report.md` as a prominent identifier. Users decide whether to fix and rerun Stage 2.

### Validation Items

| Validation Item | Level | Description |
|:----------------|:-----:|:------------|
| File existence | error | JSON / SQLite / Excel files exist and are non-empty |
| Record count consistency | error | Record counts match across all three files |
| Component count consistency | error | Component channel counts match across all three files |
| Vehicle ID consistency | error | vehicle_id matches across all three files |
| Condition coverage consistency | error | JSON and Excel condition entries correspond one-to-one |
| Image path coverage | warning | Records with image path ratio (ripple GE90%, slope GE30%) |
| Numeric precision consistency | warning | Sample comparison of JSON vs Excel value differences (threshold > 0.01) |
| SOC grading distribution | warning | SOC distribution balance (single interval < 90%) |
| Condition match confidence | warning | Low confidence (< 0.8) condition ratio < 10% |

### Usage

**Auto-trigger**: `vehicle_skills_cli.py process` automatically calls after Stage 2 success

**Manual execution:**
```bash
cd vehicle-ripple-data/scripts
python validate_cross_format.py --vehicle-id V0001 --output-dir F:/Vehicle_Date/V0001/V0001_RIPPLE/V0001_RIPPLE_output --type ripple
python validate_cross_format.py --vehicle-id V0001 --output-dir F:/Vehicle_Date/V0001/V0001_SLOPE/V0001_SLOPE_output --type slope
```

| Parameter | Description |
|-----------|:------------|
| `--vehicle-id` | Vehicle ID |
| `--output-dir` | Stage 2 output directory |
| `--type` | `ripple` or `slope` (default: ripple) |
| `--strict` | Strict mode: warnings also treated as failures |

### Output

Validation results written to `{output_dir}/error_report.md` first line:
```markdown
# Cross-Format Validation Report

**Validation Time**: 2026-04-25T10:30:00
**Result**: Issues found (see details below)

> **Note**: This validation is for informational purposes only,
> does not block subsequent stage execution...

### Error Items
- **Record Count Consistency**: Records: JSON=54, SQLite=54, Excel=0 MISMATCH!

### Passed Validation Items
- **Vehicle ID Consistency**: Vehicle ID: JSON=V0001, SQLite=V0001, Expected=V0001
```

---

## Stage 3: Report Generation (report-generation)

### Functional Positioning

Read Stage 2 generated Excel/SQLite data + raw images, generate Word (.docx) reports conforming to test standards.

### Report Template Structure

One independent report per channel, containing:

```
Report Title: {VehicleID} Ripple/Slope Test Report - {ComponentName}

+-- Chapter 1: SOC GE 70% Range
|   +-- Test Result Table (9 test items)
|   +-- Test Data Curves (16 image pairs + captions)
|
+-- Chapter 2: SOC 40%-70% Range
|   +-- Test Result Table
|   +-- Test Data Curves
|
+-- Chapter 3: SOC LE 40% Range
    +-- Test Result Table
    +-- Test Data Curves
```

### Test Item Mapping (9 Tests)

| No. | Test Item | Condition 1 | Condition 2 | Condition 3 |
|:----:|:----------|:------------|:------------|:------------|
| 1 | Park D Gear | Static Cold | Static Heat | -- |
| 2 | Hard Acceleration | 0-100km/h | Multiple Acceleration | -- |
| 3 | Cruise | Cruise Cold | Cruise Heat | -- |
| 4 | Overtake | Overtake Acceleration | -- | -- |
| 5 | Coasting | D-Gear Coasting | -- | -- |
| 6 | Emergency Brake | Emergency Brake | -- | -- |
| 7 | Climbing | Climbing | Climbing Cold | Climbing Heat |
| 8 | Parked Charging | DC Charge Cold | DC Charge Heat | -- |
| 9 | Parked Charging | AC Charge Cold | AC Charge Heat | -- |

### Channel Type Auto-Recognition

Report generator automatically judges channel type based on `component_code` suffix, dynamically switching units and descriptions:

| Suffix | Type | Ripple Unit | Ripple Threshold | Slope Unit | Standard Requirement Conversion |
|:------:|:----:|:-----------:|:----------------:|:----------:|:--------------------------------|
| `_A` | Current | App | 100App | A/s | "Voltage Ripple"->"Current Ripple", "30Vpp"->"100App" |
| `_V` | Voltage | Vpp | 30Vpp | V/s | Keep original |

Implementation: `vehicle-report-generation/scripts/core/ripple_report.py` / `slope_report.py`

### Data Reading Strategy

```
Prefer Excel:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE_summary.xlsx
    OR
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE_summary.xlsx

Excel read failure -> fallback to SQLite:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE.db
    OR
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE.db
```

### CLI Commands

```bash
# Generate all reports (ripple + slope, all channels)
python vehicle_report_cli.py generate V0006

# Only generate ripple reports
python vehicle_report_cli.py generate V0006 --type ripple

# Only generate slope reports
python vehicle_report_cli.py generate V0006 --type slope

# Specify channel
python vehicle_report_cli.py generate V0005 --type ripple --component ACC_A
```

### Output Paths

```
# Ripple report
{base_dir}/{VehicleID}/{VehicleID}_RIPPLE/{VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE_REPORT_{ComponentCode}.docx

# Slope report
{base_dir}/{VehicleID}/{VehicleID}_SLOPE/{VehicleID}_SLOPE_output/{VehicleID}_SLOPE_REPORT_{ComponentCode}.docx
```

---

## Stage 4: Unified Database Management (vehicle-database)

### Functional Positioning

Aggregate dispersed per-vehicle `_RIPPLE_data.json` / `_SLOPE_data.json` / `.db` / `_summary.xlsx` into `Ripple.db` + `Slope.db` dual databases, supporting cross-vehicle query, statistical analysis, and data export.

### Data Source Auto-Detection

`add` command auto-detects the following data source formats (no priority, all imported):

| Format | File Pattern | Description |
|:------:|:-------------|:------------|
| JSON | `*_RIPPLE_data.json`, `*_SLOPE_data.json` | Most complete, all metadata |
| SQLite | `*.db` | Skill-generated database |
| Excel | `*_summary.xlsx` | Summary report |

### Unified Database Schema (Dual Database Architecture)

> **Note**: Unified database split into `Ripple.db` + `Slope.db` two independent databases. Each contains complete vehicles/components/test_conditions tables, but only contains corresponding type results table.
> - `match_confidence`, `match_method` -- Condition matching metadata
> - `raw_data_json` -- Raw data snapshot
> - `created_at`, `updated_at` -- Timestamps

**Ripple.db**: vehicles, components, test_conditions, data_batches, matching_logs + ripple_results

**Slope.db**: vehicles, components, test_conditions, data_batches, matching_logs + slope_results

Shared Schema:
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

### CLI Commands

```bash
# Initialize (must specify output location, auto-creates Ripple.db + Slope.db)
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database

# Add vehicles (auto-routes to corresponding DB, auto-exports JSON/Excel on success)
python vehicle_database.py add V0001 V0002 V0003
python vehicle_database.py add --all

# Query (default Ripple.db, --type slope queries Slope.db)
python vehicle_database.py list
python vehicle_database.py list --ids
python vehicle_database.py list --type slope
python vehicle_database.py show V0001
python vehicle_database.py show V0001 --type slope
python vehicle_database.py stats
python vehicle_database.py stats --type slope

# Export (default from Ripple.db)
python vehicle_database.py export V0001 --json -o V0001.json
python vehicle_database.py export V0001 --excel -o V0001.xlsx
python vehicle_database.py export --all --excel -o all_vehicles/
python vehicle_database.py export --all --type slope --excel -o all_slope/
python vehicle_database.py export --all --combine --json -o all_vehicles.json
```

### Configuration Persistence

```
~/.vehicle_database/config.json
{
  "source_path": "F:/Vehicle_Date",
  "database_path": "F:/Vehicle_Database"
}
```
> Backward compatible: old config `database_path` pointing to `.db` file auto-extracts parent directory.

---

## Incremental Processing Engine

### Functional Positioning

Cross-stage coordinated incremental processing engine. Computes fingerprints (SHA-256 / mtime+size) for each stage's input, compares with cache to determine whether re-execution is needed. Avoids redundant computation on unchanged data, significantly improving batch processing efficiency.

**Applicable Scenarios**:
- Single vehicle incremental: Only rerun changed stages
- Batch incremental: Scan multiple vehicles, decide per-vehicle
- Force full rerun: Clear cache and re-execute all stages

**Stage 1 (AutoHandleFiles GUI) still requires manual execution**, engine starts incremental processing from Stage 2.

### Fingerprint Strategy

| Stage | Input Files | Fingerprint Algorithm | Description |
|-------|:------------|:----------------------|:------------|
| stage1 | `test_data/*.dmd` | `fast` (mtime+size) | Large files use lightweight fingerprint |
| stage2_ripple | `statistics.xlsx` + rules + `vehicle_info.md/xlsx` | `sha256` + semantic fingerprint | xlsx uses openpyxl cell hash to mask zip metadata diffs; md normalizes newlines |
| stage2_slope | Same as stage2_ripple | Same as above | Same as above |
| stage3 | `_summary.xlsx` + template | `sha256` | Stage 2 summary + report template |
| stage4 | `_data.json` | `sha256` | Stage 2 JSON output |

**v1.4 Key Changes**:
- **vehicle_info included in stage2 fingerprint**: Modifying vehicle model/parameters auto-triggers stage2 rerun, cascading to stage3/4
- **xlsx semantic fingerprint** (`_semantic_fingerprint`): Hash openpyxl cells to avoid "open-save" zip mtime changes causing false change detection
- **md normalization**: `\r\n` -> `\n` + strip trailing spaces, avoids editor newline diffs

### Cache File

```
{Vehicle_Date}/{VehicleID}/.workflow_cache.json
```

Cache example (v1.4+ includes schema_version):
```json
{
  "_schema_version": 2,
  "stage1": { "fingerprint": "1714003200:10485760", "completed_at": "2026-04-25T10:00:00+00:00" },
  "stage2_ripple": { "fingerprint": "a1b2c3d4...", "completed_at": "2026-04-25T10:05:00+00:00" },
  "stage2_slope": { "fingerprint": "e5f6g7h8...", "completed_at": "2026-04-25T10:06:00+00:00" },
  "stage4": { "fingerprint": "i9j0k1l2...", "completed_at": "2026-04-25T10:10:00+00:00" }
}
```

**v1.4 Key Changes**:
- **`_schema_version: 2`** -- Detects old cache, prints upgrade log, new algorithm (vehicle_info in fingerprint) auto-triggers one-time rerun
- **Atomic write**: tmp+rename + fsync prevents crash corruption; falls back to `.workflow_cache.json.bak` if corrupted
- **UTC ISO-8601 timestamps**: All 13 `datetime.now()` changed to `datetime.now(timezone.utc)`, avoids DST ambiguity

### Execution Log File

Auto-saves execution log after each run:

```
{Vehicle_Date}/{VehicleID}/.workflow_execution_log.json
```

Content includes complete execution plan and stage results:
```json
{
  "vehicle_id": "V0001",
  "executed_at": "2026-05-09T14:30:00",
  "plan": [...],
  "execution": [...]
}
```

### CLI Commands

**Working Directory**: `workflow-orchestrator`

#### Single Vehicle

```bash
# Generate execution plan (preview only, no execution)
python incremental_workflow.py plan V0001 --base-dir F:/Vehicle_Date

# Execute incremental workflow
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date

# Force full rerun
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date --force

# Only execute specified stages
python incremental_workflow.py run V0001 --stages 2_ripple
python incremental_workflow.py run V0001 --stages 2_slope
python incremental_workflow.py run V0001 --stages 3

# Clear cache
python incremental_workflow.py clear-cache V0001
```

#### Batch Processing

```bash
# Batch scan and incrementally process all vehicles (Stage 2->3->4)
python incremental_workflow.py batch --scan F:/Vehicle_Date

# Force full rerun
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# Only batch import database (Stage 4)
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4
```

| Parameter | Description |
|-----------|:------------|
| `command` | `plan` / `run` / `clear-cache` / `batch` |
| `vehicle_id` | Vehicle ID (plan/run/clear-cache required) |
| `--scan` | Batch scan directory (batch command) |
| `--base-dir` | Vehicle data root directory (default: F:/Vehicle_Date) |
| `--skills-dir` | Skill install directory (default: ~/.claude/skills) |
| `--force` | Force full rerun, clear cache |
| `--stages` | Specified stages: `all`, `1`, `2`, `3`, `4`, `2_ripple`, `2_slope` |

### Execution Plan Example

#### Single Vehicle Example

```
======================================================================
Vehicle V0001 Incremental Processing Plan
======================================================================
[Skip] [stage1                        ] No test_data directory
[Exec] [stage2_ripple                 ] First run
[Skip] [stage2_slope                  ] Handled by stage2_ripple
[Exec] [stage3_ripple_FM_V            ] First generation
[Exec] [stage3_ripple_FM_A            ] First generation
[Skip] [stage3_ripple_DCC_V           ] No summary file
...
======================================================================
Total: 2 stages to execute, 38 stages skippable
Est. total time: 20 minutes
======================================================================
```

> **Note**: When a vehicle has both RIPPLE and SLOPE data and `stage2_ripple` needs execution, `vehicle_skills_cli.py process` handles both uniformly, `stage2_slope` auto-marked as "handled by stage2_ripple" and skipped, avoiding SLOPE duplicate processing.

#### Batch Processing Summary Example

```
======================================================================
Batch Incremental Processing Summary
======================================================================
Total Vehicles: 18
Success: 16
No processing needed: 2
Failed: 0
Total time: 192.3s

Vehicle ID   Stage 2       Stage 3    Stage 4        Status   Time
----------------------------------------------------------------------
V0001        Exec(R+S)     Exec(4/4)  Skip           OK       9.3
V0002        Exec(R+S)     Skip       Exec(12/12)    OK       23.6
V0005        Exec(R+S)     Skip       Exec(26/26)    OK       63.2
V0017        Exec(R+S)     Skip       Skip           OK       2.1
...
======================================================================
Batch log saved: F:/Vehicle_Date/.workflow_batch_log.json
```

---

## Condition Rule Version Management

### Functional Positioning

Manages versioned loading, upgrading, and auditing of `test_naming_rules.md` and `sensor_naming_rules.md`. Supports three rule file formats:

1. **`@import` Directive Format** (Recommended)
   ```markdown
   @import vehicle-ripple-data:test_naming_rules@1.0

   # Local custom rules
   90_ParkDHeat: Static Heat
   ```

2. **YAML Frontmatter Format**
   ```markdown
   ---
   version: "1.0"
   extends: true
   ---
   # Rule content...
   ```

3. **Traditional Full Rule Format** (Fully compatible with existing files)
   - File content is all rules, no `@import`
   - Traditional format vehicles **do not auto-upgrade**, fully compatible with existing workflow

### Rule Loading Priority

```
1. Local override rules (inside vehicle folder)
2. Referenced standard rule specified version (via @import or frontmatter)
3. Default latest standard rules (skills/references/ directory)
```

### CLI Commands

**Working Directory**: `vehicle-ripple-data`

```bash
# List available versions
python scripts/rule_manager.py list-versions test_naming_rules
python scripts/rule_manager.py list-versions sensor_naming_rules

# Upgrade single vehicle rules
python scripts/rule_manager.py upgrade V0001 --rule test_naming_rules --to 1.1

# Batch upgrade
python scripts/rule_manager.py batch-upgrade --scan F:/Vehicle_Date --rule test_naming_rules --to 1.1

# Audit all vehicle rule versions
python scripts/rule_manager.py audit --scan F:/Vehicle_Date
```

**Version Metadata**: `references/versions.json`
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

## Folder Structure Convention

### Complete Structure

```
F:/Vehicle_Date/                          # Data source root (configurable)
|
+-- V0001/                                # Vehicle parent folder
|   +-- vehicle_info.md                   # Vehicle info (required)
|   +-- setup.png                         # Vehicle photo (optional)
|   +-- test_naming_rules.md              # Condition rules (optional, default fallback)
|   +-- sensor_naming_rules.md            # Sensor rules (optional)
|   +-- test_data/                        # Raw .dmd data (AutoHandleFiles input)
|   |
|   +-- V0001_RIPPLE/                     # Ripple analysis results (Stage 1 output)
|   |   +-- vehicle_info.md               # (Can place here, but parent recommended)
|   |   +-- test_naming_rules.md
|   |   +-- sensor_naming_rules.md
|   |   +-- FM_V/
|   |   |   +-- statistics.xlsx           # 7-column stats
|   |   |   +-- *.png                     # One image per condition
|   |   +-- RM_V/
|   |   +-- LV_V/
|   |   +-- LV_A/
|   |   +-- DCC_V/
|   |   +-- DCC_A/
|   |   +-- ACC_V/
|   |   +-- ACC_A/
|   |   +-- PTC_V/
|   |   +-- PTC_A/
|   |   +-- ACCM_V/
|   |   +-- ACCM_A/
|   |   +-- BATT_V/
|   |   +-- BATT_A/
|   |   +-- FAN_A/
|   |   +-- Vehicle_Harness_Splitter_V/
|   |   +-- Vehicle_Harness_Splitter_A/
|   |   +-- ...
|   |   +-- V0001_RIPPLE_output/          # Stage 2 output
|   |       +-- V0001_RIPPLE_summary.xlsx
|   |       +-- V0001_RIPPLE.db
|   |       +-- V0001_RIPPLE_data.json
|   |       +-- V0001_RIPPLE_REPORT_FM_V.docx    <- Stage 3 output
|   |       +-- V0001_RIPPLE_REPORT_RM_V.docx
|   |       +-- ...
|   |       +-- error_report.md
|   |
|   +-- V0001_SLOPE/                      # Slope analysis results (Stage 1 output)
|       +-- FM_V/
|       |   +-- statistics.xlsx           # 4-column stats
|       |   +-- *.png (optional)
|       +-- RM_V/
|       +-- ... (same channels as ripple)
|       +-- V0001_SLOPE_output/           # Stage 2 output
|           +-- V0001_SLOPE_summary.xlsx
|           +-- V0001_SLOPE.db
|           +-- V0001_SLOPE_data.json
|           +-- V0001_SLOPE_REPORT_FM_V.docx     <- Stage 3 output
|           +-- ...
|           +-- error_report.md
|
+-- V0002/
+-- V0003/
+-- ...

F:/Vehicle_Database/                      # Unified database directory
+-- Ripple.db                             # Stage 4 output (ripple database)
+-- Slope.db                              # Stage 4 output (slope database)
```

### Naming Conventions

| Level | Pattern | Example |
|-------|:--------|:--------|
| Vehicle parent folder | `{VehicleID}` | `V0001` |
| Ripple data folder | `{VehicleID}_RIPPLE` | `V0001_RIPPLE` |
| Slope data folder | `{VehicleID}_SLOPE` | `V0001_SLOPE` |
| Ripple output folder | `{VehicleID}_RIPPLE_output` | `V0001_RIPPLE_output` |
| Slope output folder | `{VehicleID}_SLOPE_output` | `V0001_SLOPE_output` |
| Ripple summary Excel | `{VehicleID}_RIPPLE_summary.xlsx` | `V0001_RIPPLE_summary.xlsx` |
| Slope summary Excel | `{VehicleID}_SLOPE_summary.xlsx` | `V0001_SLOPE_summary.xlsx` |
| Ripple database | `{VehicleID}_RIPPLE.db` | `V0001_RIPPLE.db` |
| Slope database | `{VehicleID}_SLOPE.db` | `V0001_SLOPE.db` |
| Ripple report | `{VehicleID}_RIPPLE_REPORT_{ComponentCode}.docx` | `V0001_RIPPLE_REPORT_FM_V.docx` |
| Slope report | `{VehicleID}_SLOPE_REPORT_{ComponentCode}.docx` | `V0001_SLOPE_REPORT_FM_V.docx` |

---

## Execution Flow / 执行流程

### Single Vehicle Processing

```bash
# ===== Step 1: AutoHandleFiles (GUI Operation) =====
# 1. Open AutoHandleFiles.exe
# 2. Select .dmd files from test_data/ folder
# 3. Configure parameters:
#    - Filter: type/cutoff/order
#    - FFT: window type/overlap rate
#    - Mode: Ripple / Slope / Both
# 4. Click "Calculate" -> Generate RIPPLE/ and SLOPE/ data

# ===== Step 2: Prepare Metadata Files (Manual) =====
# Place in V0001/ directory:
# - vehicle_info.md (required)
# - test_naming_rules.md (optional)
# - sensor_naming_rules.md (optional)
# - setup.png (optional)

# ===== Step 3: Ripple Data Integration =====
# Call vehicle-ripple-data skill
# Input: V0001/ (parent folder, skill auto-discovers V0001_RIPPLE/)
# Output: V0001_RIPPLE_output/

# ===== Step 4: Slope Data Integration =====
# Call vehicle-slope-data skill
# Input: V0001/ (parent folder, skill auto-discovers V0001_SLOPE/)
# Output: V0001_SLOPE_output/

# ===== Step 5: Generate Test Report (Method A: Auto-trigger) =====
# Add --auto-report parameter during Stage 2 processing,
# auto-triggers Stage 3 after Stage 2.5 completes
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --auto-report

# ===== Step 5: Generate Test Report (Method B: Manual) =====
cd vehicle-report-generation
# Generate ripple reports (all channels)
python vehicle_report_cli.py generate V0001 --type ripple
# Generate slope reports (all channels)
python vehicle_report_cli.py generate V0001 --type slope

# ===== Step 6: Import to Unified Database =====
cd vehicle-database
python vehicle_database.py -s F:/Vehicle_Date add V0001
```

### Batch Vehicle Processing

#### Recommended: Incremental Engine Batch Mode (V3.3+)

```bash
# Incrementally process all vehicles (Stage 2->3->4, auto-skip unchanged)
cd workflow-orchestrator
python incremental_workflow.py batch --scan F:/Vehicle_Date

# Force full rerun
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# Only batch import database (Stage 4)
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4
```

#### Traditional: Per-Skill Batch Processing

```bash
# ===== Batch Integration + Auto Report Generation =====
# Method A: Auto-trigger Stage 3
cd vehicle-ripple-data
python scripts/cli/vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress --auto-report

# ===== Batch Integration (Stage 2 only, no report trigger) =====
# Method B: Manual Stage 3 control
cd vehicle-ripple-data
python scripts/cli/vehicle_skills_cli.py batch --scan F:/Vehicle_Date --progress

# Batch slope integration
cd vehicle-slope-data
python scripts/cli/process_slope.py batch --scan F:/Vehicle_Date --progress

# ===== Batch Import Database =====
cd vehicle-database
python vehicle_database.py add --all

# ===== Batch Generate Reports (Manual) =====
cd vehicle-report-generation
python vehicle_report_cli.py batch F:/Vehicle_Date --type all
```

---

## CLI Command Reference / CLI命令参考

### Quick Reference / 速查表

| Skill | CLI Entry | Working Directory |
|-------|:----------|:------------------|
| vehicle-ripple-data | `scripts/cli/vehicle_skills_cli.py` | `vehicle-ripple-data/` |
| vehicle-slope-data | `scripts/cli/process_slope.py` | `vehicle-slope-data/` |
| vehicle-database | `vehicle_database.py` | `vehicle-database/` |
| vehicle-report-generation | `vehicle_report_cli.py` | `vehicle-report-generation/` |
| workflow-orchestrator | `incremental_workflow.py` | `workflow-orchestrator/` |
| rule-manager | `scripts/rule_manager.py` | `vehicle-ripple-data/` |

### Most Common Commands / 常用命令

```bash
# ========== Single Vehicle Full Flow (Auto Report) ==========
cd vehicle-ripple-data
python scripts/cli/vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress --auto-report

# ========== Batch Processing (Recommended: Incremental) ==========
cd workflow-orchestrator
python incremental_workflow.py batch --scan F:/Vehicle_Date

# ========== Incremental Processing ==========
# Generate plan
python incremental_workflow.py plan V0001 --base-dir F:/Vehicle_Date

# Execute incremental workflow
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date

# Force full rerun
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date --force

# ========== Rule Version Management ==========
cd vehicle-ripple-data
python scripts/rule_manager.py list-versions test_naming_rules
python scripts/rule_manager.py audit --scan F:/Vehicle_Date

# ========== Validation & Query ==========
python scripts/cli/vehicle_skills_cli.py validate E:/Vehicle_Date/V0001

cd vehicle-database
python vehicle_database.py list
python vehicle_database.py show V0001
python vehicle_database.py stats
```

---

## Data Mapping & Encoding Specs / 数据映射与编码规范

### Vehicle Info Fields

| Field Name | Description | Type |
|:-----------|:------------|:----:|
| Vehicle ID | Primary key | TEXT |
| Vehicle Model | Model name | TEXT |
| Length mm | Length | REAL |
| Width mm | Width | REAL |
| Height mm | Height | REAL |
| Wheelbase (mm) | Wheelbase | REAL |
| Front Track (mm) | Front track | REAL |
| Rear Track (mm) | Rear track | REAL |
| Min Ground Clearance (mm) | Ground clearance | REAL |
| Hybrid System | Hybrid type | TEXT |
| Drive Type | Drive mode | TEXT |
| Front Motor Max Power (kW) | Front motor power | REAL |
| Rear Motor Max Power (kW) | Rear motor power | REAL |
| Front Motor Max Torque (N.m) | Front motor torque | REAL |
| Rear Motor Max Torque (N.m) | Rear motor torque | REAL |
| System Total Power (kW) | Total power | REAL |
| HV Architecture | Voltage platform | TEXT |
| Battery Type | Battery type | TEXT |
| Battery Capacity (kWh) | Battery capacity | REAL |
| Fast Charge Power (kW) | Fast charge | REAL |
| Front Suspension | Front suspension | TEXT |
| Rear Suspension | Rear suspension | TEXT |
| Engine Model | Engine | TEXT |
| Transmission Type | Transmission | TEXT |
| Displacement (L) | Displacement | REAL |
| Engine Max Net Power (kW/rpm) | Engine power | TEXT |
| Engine Max Net Torque (N.m/rpm) | Engine torque | TEXT |
| Price (10k CNY) | Price | REAL |

### Standard Component Channels

| Channel Code | Component Name | Unit | Type |
|:-------------|:---------------|:----:|:----:|
| FM_V | Front Motor DC Bus Voltage | V | voltage |
| FM_A | Front Motor DC Bus Current | A | current |
| RM_V | Rear Motor DC Bus Voltage | V | voltage |
| RM_A | Rear Motor DC Bus Current | A | current |
| DCC_V | Battery DC Charge Voltage | V | voltage |
| DCC_A | Battery DC Charge Current | A | current |
| ACC_V | OBC Output Voltage | V | voltage |
| ACC_A | OBC Output Current | A | current |
| PTC_V | PTC Input Voltage | V | voltage |
| PTC_A | PTC Input Current | A | current |
| ACCM_V | Compressor Input Voltage | V | voltage |
| ACCM_A | Compressor Input Current | A | current |
| LV_V | 12V Battery Low Voltage | V | voltage |
| LV_A | 12V Battery Low Current | A | current |
| FAN_A | Front Cooling Module Fan Current | A | current |
| BATT_V | Battery Pack Voltage | V | voltage |
| BATT_A | Battery Pack Current | A | current |
| Vehicle_Harness_Splitter_V | Vehicle Harness Splitter Voltage | V | voltage |
| Vehicle_Harness_Splitter_A | Vehicle Harness Splitter Current | A | current |

### Encoding Handling Specifications

| Scenario | Handling | Fallback |
|----------|----------|----------|
| Read .md files | `open(path, 'r', encoding='utf-8')` | On failure try `gbk` |
| Read .xlsx files | `pandas.read_excel()` | Specify `engine='openpyxl'` |
| Access Excel columns | Use `iloc[0], iloc[1]...` | NEVER use column name string access |
| Write output files | `encoding='utf-8'` | Ensure Chinese saves correctly |
| Image filename parsing | Direct string processing | Supports GBK garbled feature matching |

---

## Known Issues & Solutions / 已知问题与解决方案

### AutoHandleFiles Issues

| Priority | Issue | Impact | Solution |
|:--------:|-------|--------|----------|
| High | Large file MemoryError | Program crash | Optimize `getMinMaxSegdatas_and_mmap` chunk size |
| High | Temp file cleanup conflict | WinError 32 | Serialize cleanup or use file lock |
| High | .temp dir not created | FileNotFoundError | `os.makedirs(exist_ok=True)` before write |
| Medium | .dmd corruption | FILE_INVALID | File header validation, skip corrupted |
| Medium | Thread exception swallowed | Silent failure | Add exception callbacks and logging |

### Data Integration Issues

| Priority | Issue | Impact | Solution |
|:--------:|-------|--------|----------|
| High | Excel column name garbled | KeyError | Force `iloc` index access |
| High | Image matching failure | image_path null | Validate filename parsing, check both formats |
| High | **SOC extraction delimiter incompatibility** | Many Unknown SOC grades | V3.5 unified regex: `_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')` supports `_` `-` `space` |
| High | **Slope prefix GBK garbled** | Climbing conditions can't match images | V3.5 `_normalize_condition_id()` replaces `\xC6\xC2\xB6\xC810` with `Slope10`, unifies xlsx and image condition_id |
| Medium | Condition name mismatch | Raw ID shown in reports | Four-level fuzzy matching strategy |
| Medium | SOC grading error | Data in wrong interval | Must extract number directly from condition_id |
| Medium | **Non-standard image markers** | `xpp`/`Xpp` cause parsing failure | V3.5 extended detection |
| Medium | **Image filename trailing spaces** | condition_id with spaces fails matching | V3.5 `img_stem = img_file.stem.strip()` |

### Incremental Engine Issues (Fixed)

| Priority | Issue | Impact | Solution |
|:--------:|-------|--------|----------|
| High | Stage 2 slope duplicate processing | SLOPE processed twice | `_decide_stage2_slope()` adds coverage check |

### Report Generation Issues

| Priority | Issue | Impact | Solution |
|:--------:|-------|--------|----------|
| High | Current/voltage channel unit confusion | Current channel shows wrong unit | Dynamic switch based on `component_code` suffix (`_A`/`_V`) |
| Medium | Excel encoding error | Can't read data | Auto-fallback to SQLite database |
| Medium | Image path changed | Missing images in reports | Use absolute paths or validate existence |

### Database Issues (V3.4 Fixed)

| Priority | Issue | Impact | Solution |
|:--------:|-------|--------|----------|
| High | Single DB table conflict | `_delete_vehicle` error | Split to `Ripple.db` + `Slope.db` dual DB |
| High | JsonExporter hard-coded table | Query wrong table | Add `data_type` parameter, dynamic table selection |
| Medium | Old `--database` points to file | Backward compatibility | `resolve_database_path()` auto-detects `.db` suffix |

---

## Tech Stack / 技术栈汇总

| Stage/Tool | Skill/Tool | Core Technology | Input | Output |
|------------|-----------|-----------------|-------|--------|
| Stage 1 | AutoHandleFiles | PySide6, pyDmdReader, datashader, scipy, numpy | .dmd | .xlsx, .png |
| Stage 2a | vehicle-ripple-data | pandas, openpyxl, sqlite3, fuzzywuzzy | statistics.xlsx, .png | .xlsx, .db, .json, .md |
| Stage 2b | vehicle-slope-data | pandas, openpyxl, sqlite3, fuzzywuzzy | statistics.xlsx, .png(optional) | .xlsx, .db, .json, .md |
| Stage 2.5 | validate_cross_format | pandas, sqlite3, json | .json/.db/.xlsx | error_report.md |
| Stage 3 | vehicle-report-generation | python-docx, openpyxl | .xlsx/.db + .png | .docx |
| Stage 4 | vehicle-database | sqlite3, pandas, click | .json/.db/.xlsx | Ripple.db + Slope.db |
| Incremental | workflow-orchestrator | hashlib, subprocess, pathlib | Stage input/output fingerprints | .workflow_cache.json |
| Rule Mgmt | rule_manager | re, pathlib, yaml(optional) | .md rule files | Versioned rule loading |

---

## Version History / 版本历史

### v1.4 Production Ready (2026-05-11)

**Critical Fixes:**

| Priority | Issue | Fix |
|:--------:|-------|-----|
| Fatal | Importer internal commit breaks update.py atomicity | Remove internal commit from 3 importers, re-raise exceptions, outer `with DatabaseConnection` controls |
| Fatal | Importer orphan data on re-import | `DELETE FROM ripple_results/slope_results WHERE vehicle_id = ?` before `import_vehicle` |
| Fatal | add.py silently swallows failures | Exit codes: 0 (success) / 2 (total fail) / 3 (partial), orchestrator recognizes partial |
| Fatal | `_save_cache` non-atomic write crash | tmp+fsync+os.replace atomic write + retry, fallback to `.bak` |
| Fatal | `batch_log` only writes at end | Per-vehicle atomic write to `.workflow_batch_log.json` |
| Fatal | `_stage4_missing_handled` instance var fails | Class-level flag + batch_run reset |
| High | Partial status wrongly marked OK | PARTIAL state propagation through full chain |
| High | DatabaseConnection.__exit__ leak | try/finally guarantee close |
| High | python-docx run split header rewrite | Cross-run paragraph rebuild |
| High | xpp marker substring false positive | Regex anchor `^\d+(?:\.\d+)?[IVXivx]pp$` |
| High | init mass-import no confirmation | `click.confirm` + `--yes/-y` flag |
| Medium | Cache schema no version | `_schema_version: 2` + upgrade log |
| Medium | vehicle_info in stage2 fingerprint | Semantic fingerprint for xlsx/md |
| Medium | UTC timestamps | All 13 `datetime.now()` -> `datetime.now(timezone.utc)` |

### V3.6 Completed

- Database directory migration: `F:/Vehicle_Date/Vehicle_Database/` -> `F:/Vehicle_Database/`
- Dual DB architecture (Ripple.db + Slope.db)
- Incremental engine batch mode
- Auto-report generation (`--auto-report`)
- Rule version management (`@import` / YAML frontmatter)

### V3.5 Completed

- SOC extraction multi-delimiter support (`_`, `-`, `space`)
- Slope prefix GBK garbled handling (`\xC6\xC2\xB6\xC8` -> `Slope10`)
- Non-standard `xpp`/`Xpp` marker support
- Image filename trailing space handling
- Condition matcher feature extraction delimiter support

### V3.4 Completed

- Unified database dual DB separation
- Cross-format validation (Stage 2.5)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

## Skills / 子项目

This monorepo contains 5 skills:

| Skill | Description |
|-------|:------------|
| [vehicle-ripple-data](vehicle-ripple-data/) | Ripple test data integration |
| [vehicle-slope-data](vehicle-slope-data/) | Slope test data integration |
| [workflow-orchestrator](workflow-orchestrator/) | Incremental processing engine |
| [vehicle-database](vehicle-database/) | Unified data management |
| [vehicle-report-generation](vehicle-report-generation/) | Automated report generation |

For the original unmodified workflow document, see [WORKFLOW.md](WORKFLOW.md).
