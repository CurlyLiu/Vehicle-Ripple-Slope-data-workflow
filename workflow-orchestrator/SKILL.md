---
name: workflow-orchestrator
description: Cross-stage incremental workflow engine for vehicle ripple/slope test data processing. Computes fingerprints for each stage's input, compares with cache to decide re-execution scope. Avoids redundant computation, significantly improving batch processing efficiency.
version: 1.0.0
author: CurlyLiu
tags: [workflow, incremental, orchestrator, cache, fingerprint, batch]
requires:
  - python>=3.8
---

# Workflow Orchestrator Skill

Cross-stage incremental processing engine for the vehicle ripple/slope test data workflow. Computes fingerprints (SHA-256 / mtime+size) for each stage's input, compares with cache to determine whether re-execution is needed. Avoids redundant computation on unchanged data, significantly improving batch processing efficiency.

## Features

- **Per-vehicle incremental processing**: Only re-run stages with changed inputs
- **Batch incremental processing**: Scan multiple vehicles, decide per-vehicle
- **Force full re-run**: Clear cache and re-execute all stages
- **Fingerprint-based cache**: SHA-256 for small files, mtime+size for large files
- **Execution plan preview**: `plan` command shows what will run before execution
- **Execution log**: Auto-saves execution results to `.workflow_execution_log.json`

## Workflow Stages

```
Stage1 (AutoHandleFiles GUI) ──→ Manual, not managed by engine
         │
         ▼
Stage2_ripple (vehicle-ripple-data) ──→ Incremental
Stage2_slope (vehicle-slope-data) ──→ Incremental (or unified by stage2_ripple)
         │
         ▼
Stage3 (vehicle-report-generation) ──→ Incremental
         │
         ▼
Stage4 (vehicle-database import) ──→ Incremental
```

> **Note**: Stage1 (AutoHandleFiles GUI) must still be executed manually. The engine manages stages 2-4.

## Fingerprint Strategy

| Stage | Input Files | Algorithm | Note |
|-------|-------------|:---------:|:-----|
| stage1 | `test_data/*.dmd` | `fast` (mtime+size) | Large files use lightweight fingerprint |
| stage2_ripple | `statistics.xlsx` + rule files | `sha256` | Small files use content hash |
| stage2_slope | `statistics.xlsx` + rule files | `sha256` | Same as above |
| stage3 | `_summary.xlsx` + template | `sha256` | Stage2 summary + report template |
| stage4 | `*_data.json` | `sha256` | For database import |

## Cache File

```
{Vehicle_Date}/{VehicleID}/.workflow_cache.json
```

Example content:
```json
{
  "stage1": { "fingerprint": "1714003200:10485760", "completed_at": "2026-04-25T10:00:00" },
  "stage2_ripple": { "fingerprint": "a1b2c3d4...", "completed_at": "2026-04-25T10:05:00" },
  "stage2_slope": { "fingerprint": "e5f6g7h8...", "completed_at": "2026-04-25T10:06:00" },
  "stage3": { "fingerprint": "i9j0k1l2...", "completed_at": "2026-04-25T10:08:00" },
  "stage4": { "fingerprint": "m3n4o5p6...", "completed_at": "2026-04-25T10:10:00" }
}
```

### Execution Log File

Auto-saved after each execution:

```
{Vehicle_Date}/{VehicleID}/.workflow_execution_log.json
```

Contains the full execution plan and stage results:
```json
{
  "vehicle_id": "V0001",
  "executed_at": "2026-05-09T14:30:00",
  "plan": [...],
  "execution": [...]
}
```

## CLI Commands

### Single Vehicle

```bash
# Generate execution plan (preview only, no execution)
python incremental_workflow.py plan V0001 --base-dir F:/Vehicle_Date

# Execute incremental workflow
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date

# Force full re-run
python incremental_workflow.py run V0001 --base-dir F:/Vehicle_Date --force

# Execute only specific stage
python incremental_workflow.py run V0001 --stages 2_ripple
python incremental_workflow.py run V0001 --stages 2_slope
python incremental_workflow.py run V0001 --stages 3
python incremental_workflow.py run V0001 --stages 4

# Clear cache
python incremental_workflow.py clear-cache V0001
```

### Batch Processing

```bash
# Batch scan and incrementally process all vehicles (stages 2→3→4)
python incremental_workflow.py batch --scan F:/Vehicle_Date

# Force full re-run for all
python incremental_workflow.py batch --scan F:/Vehicle_Date --force

# Batch import database only (stage 4)
python incremental_workflow.py batch --scan F:/Vehicle_Date --stages 4
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `command` | `plan` / `run` / `clear-cache` / `batch` |
| `vehicle_id` | Vehicle ID (required for plan/run/clear-cache) |
| `--scan` | Batch scan directory (used with batch command) |
| `--base-dir` | Vehicle data root directory (default: F:/Vehicle_Date) |
| `--skills-dir` | Skill installation directory (default: ~/.claude/skills) |
| `--force` | Force full re-run, clear cache |
| `--stages` | Target stage: `all`, `1`, `2`, `3`, `4`, `2_ripple`, `2_slope` |

## Execution Plan Example

### Single Vehicle

```
======================================================================
Vehicle V0001 Incremental Processing Plan
======================================================================
[SKIP] [stage1                        ] No test_data directory
[RUN ] [stage2_ripple                 ] First run
[SKIP] [stage2_slope                  ] Unified by stage2_ripple
[RUN ] [stage3                        ] First run
[SKIP] [stage3_ripple_FM_V            ] No summary file
...
======================================================================
Total: 2 stages to run, 38 stages skippable
Estimated total time: 20 minutes
======================================================================
```

> **Note**: When a vehicle has both RIPPLE and SLOPE data and `stage2_ripple` needs to run, `vehicle_skills_cli.py process` handles both uniformly, and `stage2_slope` is automatically marked as "unified by stage2_ripple" to avoid duplicate processing.

### Batch Summary

```
======================================================================
Batch Incremental Processing Summary
======================================================================
Total vehicles: 18
Success: 16
No processing needed: 2
Failed: 0
Total time: 192.3s

Vehicle ID   Stage2          Stage3      Stage4          Status   Time
----------------------------------------------------------------------
V0001        RUN(R+S)        RUN(4/4)    SKIP            OK       9.3
V0002        RUN(R+S)        SKIP        RUN(12/12)      OK       23.6
V0005        RUN(R+S)        SKIP        RUN(26/26)      OK       63.2
V0017        RUN(R+S)        SKIP        SKIP            OK       2.1
...
======================================================================
Batch log saved: F:/Vehicle_Date/.workflow_batch_log.json
```

## Integration with Other Skills

The orchestrator auto-detects and calls other skills via CLI:

- **Stage 2**: Calls `vehicle_skills_cli.py process` (vehicle-ripple-data / vehicle-slope-data)
- **Stage 3**: Calls `vehicle_report_cli.py generate` (vehicle-report-generation)
- **Stage 4**: Calls `vehicle_database.py add` (vehicle-database)

## Dependencies

- Python >= 3.8
- Standard library only (json, hashlib, pathlib, subprocess)
