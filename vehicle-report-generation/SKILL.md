---
name: vehicle-report-generation
description: Automatically generate Word (.docx) vehicle test reports from vehicle-ripple-data and vehicle-slope-data outputs (Excel/SQLite + images). Supports ripple reports, slope reports, multi-channel auto-detection, and three-level dynamic pruning.
version: 1.0.0
author: CurlyLiu
tags: [report, docx, vehicle, ripple, slope, word, template]
requires:
  - python>=3.8
  - python-docx
  - openpyxl
  - click
---

# Vehicle Report Generation Skill

Automatically generate Word (.docx) format vehicle test reports from Excel/SQLite result files and images produced by vehicle-ripple-data and vehicle-slope-data skills.

## Features

- **Ripple reports**: Read ripple analysis results, fill test result values (Vpp) and test data curve images
- **Slope reports**: Read slope analysis results, fill slope values (V/s) and test data curve images
- **Multi-channel support**: Auto-detect component channels, generate independent report for each channel
- **Excel-first, SQLite fallback**: Prefer reading Excel summary files, automatically fallback to SQLite database on encoding issues
- **Three-level dynamic pruning**: Automatically prune empty rows, image pairs, and chapters based on actual test data coverage
- **Test coverage summary**: Auto-insert coverage summary table at report top after pruning

## Usage

### Command Format

```bash
# Generate all reports (ripple + slope, all channels)
python vehicle_report_cli.py generate V0006

# Generate only ripple reports
python vehicle_report_cli.py generate V0006 --type ripple

# Generate only slope reports
python vehicle_report_cli.py generate V0006 --type slope

# Specify component channel
python vehicle_report_cli.py generate V0005 --type ripple --component ACC_A

# Batch generate for all vehicles under target path
python vehicle_report_cli.py batch F:/Vehicle_Date
python vehicle_report_cli.py batch F:/Vehicle_Date --type ripple
python vehicle_report_cli.py batch F:/Vehicle_Date --type slope --skip-existing
```

### Output Paths

- **Ripple report**: `{base_dir}/{vehicle_id}/{vehicle_id}_RIPPLE/{vehicle_id}_RIPPLE_output/{vehicle_id}_RIPPLE_REPORT_{ComponentCode}.docx`
- **Slope report**: `{base_dir}/{vehicle_id}/{vehicle_id}_SLOPE/{vehicle_id}_SLOPE_output/{vehicle_id}_SLOPE_REPORT_{ComponentCode}.docx`

## Report Template Structure

Each channel generates one independent report:

```
Report Title: {VehicleID} Ripple/Slope Test Report — {ComponentName}

├── Chapter 1: SOC ≥ 70% Range
│   ├── Test Result Table (9 test items)
│   └── Test Data Curves (16 image groups + captions)
│
├── Chapter 2: SOC 40%-70% Range
│   ├── Test Result Table
│   └── Test Data Curves
│
└── Chapter 3: SOC ≤ 40% Range
    ├── Test Result Table
    └── Test Data Curves
```

### Test Item Mapping (9 items)

| # | Test Item | Condition 1 | Condition 2 | Condition 3 |
|:-:|-----------|:-----------:|:-----------:|:-----------:|
| 1 | Parking D-gear | Static low temp | Static high temp | — |
| 2 | Hard acceleration | 0-100 accel | Multiple accel | — |
| 3 | Constant speed | Const speed low temp | Const speed high temp | — |
| 4 | Overtaking | Overtake accel | — | — |
| 5 | Coasting | D-gear coasting | — | — |
| 6 | Emergency braking | Emergency brake | — | — |
| 7 | Hill climbing | Hill climb | Hill climb low temp | Hill climb high temp |
| 8 | Parking charge | DC charge cold air | DC charge warm air | — |
| 9 | Parking charge | AC charge cold air | AC charge warm air | — |

## Channel Type Auto-Detection

The report generator automatically determines channel type by `component_code` suffix, dynamically switching units and descriptions:

| Suffix | Type | Ripple Unit | Ripple Threshold | Slope Unit | Standard Requirement Conversion |
|:------:|:----:|:-----------:|:----------------:|:----------:|:--------------------------------|
| `_A` | Current | App | 100App | A/s | "Voltage ripple"→"Current ripple", "30Vpp"→"100App" |
| `_V` | Voltage | Vpp | 30Vpp | V/s | Keep original text |

Implementation: `vehicle-report-generation/scripts/core/ripple_report.py` / `slope_report.py`

## Data Reading Strategy

```
Priority read Excel:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE_summary.xlsx
    or
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE_summary.xlsx

Excel read failure → Fallback to SQLite:
    {VehicleID}_RIPPLE_output/{VehicleID}_RIPPLE.db
    or
    {VehicleID}_SLOPE_output/{VehicleID}_SLOPE.db
```

## Dynamic Pruning Behavior

The report generator automatically performs **three-level pruning** on the template based on actual test data:

1. **Row-level pruning**: When all conditions for a test item have no valid data, delete that row from the test result table.
2. **Image pair-level pruning**: When a test curve image has no corresponding record or the image file does not exist, delete the "image row + caption row" pair from the image table.
3. **Chapter-level pruning**: When both the test result table and image table for a SOC range have no valid content, delete the SOC title paragraph and the two tables beneath it.

After pruning, a **test coverage summary table** is automatically inserted at the top of the report, listing tested SOC ranges, tested condition count, tested curve image count, and data completeness rating (Full / Partial / No Data).

If a component has no valid data at all, the document body retains a "No valid data collected for this component" message instead of outputting large empty tables.

### Disable Pruning (Restore Old Behavior)

To generate reports containing all chapters and empty rows (old fixed-fill behavior), pass `prune=False` when calling via script:

```python
generate_ripple_report(vid, comp, base_dir, template, output, prune=False)
```

CLI enables pruning by default and does not support a command-line switch yet; to batch disable pruning, call directly via script.

## Dependencies

```bash
pip install -r requirements.txt
```

Requires: `python-docx`, `openpyxl`, `click`
