---
name: vehicle-database
description: Vehicle ripple and slope test data unified management tool with dual-database architecture (Ripple.db + Slope.db), supporting multi-format data aggregation (JSON/SQLite/Excel) and cross-vehicle query/export.
version: 3.4.0
author: CurlyLiu
tags: [database, vehicle, ripple, slope, cli, sqlite, dual-db]
requires:
  - python>=3.8
  - click
  - sqlite3
  - pandas
  - openpyxl
---

# Vehicle Database Skill

Unified management and query tool for vehicle ripple and slope test data.

**Architecture**: Dual-database design (Ripple.db + Slope.db) — separated since V3.4.

## Features

- **Multi-format data aggregation**: Automatic detection and import of JSON, SQLite, Excel formats
- **Dual-database architecture**: Ripple.db (ripple data) + Slope.db (slope data), independent but with shared schema
- **Unified data model**: Standardized vehicles, components, test_conditions tables
- **CLI tool**: Complete command-line interface for init, import, query, export
- **Batch operations**: Multi-vehicle batch import, update, delete
- **Data export**: JSON, Excel, SQLite format export
- **Cross-database query**: `--type ripple|slope` parameter for selecting target database
- **Config persistence**: Auto-saves source path to `~/.vehicle_database/config.json`

## Data Architecture

```
F:/Vehicle_Database/
├── Ripple.db  (ripple_results + shared schema)
│   ├── vehicles, components, test_conditions
│   ├── ripple_results
│   └── data_batches, matching_logs
│
└── Slope.db   (slope_results + shared schema)
    ├── vehicles, components, test_conditions
    ├── slope_results
    └── data_batches, matching_logs
```

Each database has a complete set of shared tables. When a vehicle has both ripple and slope data, vehicle_info is synced to both databases.

## Supported Import Formats

| Priority | Format | File Pattern | Description |
|:--------:|:------:|:-------------|:------------|
| 1 | JSON | `*_RIPPLE_data.json`, `*_SLOPE_data.json` | Most complete data with all metadata |
| 2 | SQLite | `*.db` | Skill-generated database files |
| 3 | Excel | `*_summary.xlsx` | Summary reports |

## Quick Start

### Initialize databases (must specify output location)

```bash
cd ~/.claude/skills/vehicle-database

# Specify output directory (creates Vehicle_Database/ with Ripple.db + Slope.db)
python vehicle_database.py -s F:/Vehicle_Date init -o F:/Vehicle_Database
```

### Import vehicle data

```bash
# Add single vehicle
python vehicle_database.py add V0001

# Add multiple vehicles
python vehicle_database.py add V0001 V0002 V0003

# Add all vehicles
python vehicle_database.py add --all
```

### Query data

```bash
# List all vehicles (default: Ripple.db)
python vehicle_database.py list

# List from Slope.db
python vehicle_database.py list --type slope

# Show vehicle details
python vehicle_database.py show V0001
python vehicle_database.py show V0001 --type slope

# Database statistics
python vehicle_database.py stats
python vehicle_database.py stats --type slope
```

### Export data

```bash
# Export single vehicle to JSON
python vehicle_database.py export V0001 --json -o V0001.json

# Export from Slope.db
python vehicle_database.py export V0001 --type slope --json -o V0001_slope.json

# Export all vehicles to Excel
python vehicle_database.py export --all --excel -o all_vehicles/

# Combine all vehicles into single file
python vehicle_database.py export --all --combine --json -o all_vehicles.json
```

## CLI Reference

### Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--source` | `-s` | Data source path (auto-saved to config) |
| `--database` | `-d` | Database directory path |
| `--format` | `-f` | Input format filter: db/excel/json/all |
| `--verbose` | `-v` | Verbose output mode |

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize dual databases (Ripple.db + Slope.db) | `python vehicle_database.py init -o F:/DB` |
| `add` | Add vehicles | `python vehicle_database.py add V0001` |
| `update` | Update vehicle data | `python vehicle_database.py update V0001` |
| `remove` | Remove vehicles from database | `python vehicle_database.py remove V0001` |
| `list` | List all vehicles | `python vehicle_database.py list` |
| `list --type slope` | List from Slope.db | `python vehicle_database.py list --type slope` |
| `show` | Show vehicle details | `python vehicle_database.py show V0001` |
| `stats` | Database statistics | `python vehicle_database.py stats` |
| `export` | Export vehicle data | `python vehicle_database.py export V0001 --json` |

### `--type` Parameter

All read/query/export commands support `--type` parameter:

- `--type ripple` (default): Operates on Ripple.db
- `--type slope`: Operates on Slope.db

Write commands (add/update/remove) automatically route data to the appropriate database based on source file type.

## Data Model

### Shared Tables (both Ripple.db and Slope.db)

**vehicles** — Vehicle basic information
- vehicle_id (PK), vehicle_model, manufacturer, level, energy_type
- Dimensions, weight, battery parameters, motor parameters

**components** — Component definitions
- channel_code (PK), component_name, unit, component_type

**test_conditions** — Test conditions
- condition_id (PK), condition_name, soc_level, category

### Ripple.db Only

**ripple_results** — Ripple test results
- time_domain: effective_value, vpp_value
- frequency_domain: peak_frequency_khz, peak_amplitude, frequency_rms
- metadata: image_path, match_confidence, match_method

### Slope.db Only

**slope_results** — Slope test results
- slope_max, slope_min, slope_max_abs, slope_unit
- metadata: image_path, match_confidence, match_method

## Config File

Stored at: `~/.vehicle_database/config.json`

```json
{
  "source_path": "F:/Vehicle_Date",
  "database_path": "F:/Vehicle_Database"
}
```

> Backward compatible: If `database_path` points to a `.db` file (old config), the parent directory is automatically used.

## Extension Development

### Adding a new importer

```python
from src.importers.base import BaseImporter

class NewFormatImporter(BaseImporter):
    def can_import(self, file_path: Path) -> bool:
        return file_path.suffix == '.new'

    def import_data(self, conn, vehicle_id: str, file_path: Path) -> ImportResult:
        # Implement import logic
        pass
```

## License

MIT License
