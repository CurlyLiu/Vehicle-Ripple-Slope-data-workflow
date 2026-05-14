#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core shared utilities for CLI module."""

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

VEHICLE_ID_PATTERN = re.compile(r"^V\d{4,}$")


def validate_vehicle_id(vehicle_id: str) -> bool:
    """Validate vehicle ID format (V followed by 4+ digits)."""
    return bool(VEHICLE_ID_PATTERN.match(vehicle_id))


def sanitize_vehicle_id(vehicle_id: str) -> str:
    """Extract and validate vehicle ID from string."""
    for suffix in ["_RIPPLE", "_SLOPE", "_DATA"]:
        if vehicle_id.endswith(suffix):
            vehicle_id = vehicle_id[:-len(suffix)]
    if not validate_vehicle_id(vehicle_id):
        raise ValueError(f"Invalid vehicle ID format: {vehicle_id}. Expected format: V####")
    return vehicle_id


def _load_yaml_defaults() -> Dict[str, Any]:
    """Load project-level config.yaml as fallback defaults."""
    try:
        import yaml
    except ImportError:
        return {}
    config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            pass
    return {}


class ConfigManager:
    """Manage CLI configuration and paths."""

    CONFIG_FILE = Path.home() / ".vehicle_database" / "config.json"
    DEFAULT_SOURCE = "F:/Vehicle_Date"
    _YAML_DEFAULTS: Dict[str, Any] = {}

    def __init__(self):
        self.config: Dict[str, Any] = {}
        if not ConfigManager._YAML_DEFAULTS:
            ConfigManager._YAML_DEFAULTS = _load_yaml_defaults()
        self._load_config()

    def _load_config(self):
        user_config: Dict[str, Any] = {}
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
            except (json.JSONDecodeError, OSError):
                user_config = {}
        # Merge: user config overrides yaml defaults
        self.config = {**ConfigManager._YAML_DEFAULTS, **user_config}

    def _save_config(self):
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Only save user-overridden keys, not full yaml defaults
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_source_path(self) -> Optional[Path]:
        path = self.config.get("source_path")
        if path:
            return Path(path)
        sync = self.config.get("sync", {})
        source_dir = sync.get("source_dir")
        return Path(source_dir) if source_dir else None

    def set_source_path(self, path: Path):
        self.config["source_path"] = str(path.absolute())
        self._save_config()

    def get_database_path(self) -> Optional[Path]:
        """Backward compat: return parent dir if database_path points to a file."""
        path = self.config.get("database_path")
        if path:
            p = Path(path)
            if p.suffix == '.db':
                return p.parent
            return p
        db_config = self.config.get("database", {})
        default_path = db_config.get("default_path")
        if default_path:
            p = Path(default_path)
            if p.suffix == '.db':
                return p.parent
            return p
        return None

    def set_database_path(self, path: Path):
        """Store database dir (not file) for dual-db support."""
        p = path.absolute()
        if p.suffix == '.db':
            p = p.parent
        self.config["database_path"] = str(p)
        self._save_config()


class DatabaseConnection:
    """Database connection manager."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # VDB-H1 v1.4 修订: 即使 commit 抛错也保证 close,异常路径也尝试 rollback
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        except Exception:
            # commit/rollback 自身抛错 (磁盘满等),尝试 rollback 兜底
            try:
                self.conn.rollback()
            except Exception:
                pass  # 已尽力
        finally:
            self.close()
        return False

    def execute(self, sql: str, parameters: Tuple = ()):
        return self.cursor.execute(sql, parameters)

    def executescript(self, sql: str):
        return self.cursor.executescript(sql)

    def fetchall(self) -> List[sqlite3.Row]:
        return self.cursor.fetchall()

    def fetchone(self) -> Optional[sqlite3.Row]:
        return self.cursor.fetchone()


def _init_single_database(db_file: Path, schema_statements):
    """Initialize a single database file with given schema."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        for sql in schema_statements:
            sql = sql.strip()
            if not sql:
                continue
            try:
                conn.executescript(sql)
            except sqlite3.OperationalError as e:
                # Ignore "duplicate column name" for migrations on existing DBs
                if "duplicate column name" in str(e).lower():
                    continue
                raise
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(db_dir: Path):
    """Initialize dual databases: Ripple.db + Slope.db."""
    from ..database.schema import RIPPLE_SCHEMA, SLOPE_SCHEMA
    db_dir.mkdir(parents=True, exist_ok=True)
    ripple_db = db_dir / "Ripple.db"
    slope_db = db_dir / "Slope.db"
    _init_single_database(ripple_db, RIPPLE_SCHEMA)
    _init_single_database(slope_db, SLOPE_SCHEMA)


def resolve_source_path(ctx, interactive: bool = True) -> Optional[Path]:
    """Resolve source path from context or config with path traversal protection.

    Args:
        ctx: Click context object.
        interactive: If True, prompt user when no valid source path is found.
                    Commands that do not need source data (list, show, etc.)
                    should pass False to avoid unnecessary prompts.

    Returns:
        Resolved source path, or None if interactive=False and no path found.
    """
    config = ConfigManager()
    if ctx.obj.get("source"):
        source = Path(ctx.obj["source"]).resolve()
        if not source.is_dir():
            raise click.BadParameter(f"Source path must be an existing directory: {source}")
        if source.exists():
            config.set_source_path(source)
            if ctx.obj.get("verbose"):
                click.echo(f"[VERBOSE] Using source path from CLI: {source}")
            return source
        else:
            raise click.BadParameter(f"Source path does not exist: {source}")
    config_path = config.get_source_path()
    if config_path and config_path.exists():
        if ctx.obj.get("verbose"):
            click.echo(f"[VERBOSE] Using source path from config: {config_path}")
        return config_path
    default = Path(ConfigManager.DEFAULT_SOURCE)
    if default.exists():
        if ctx.obj.get("verbose"):
            click.echo(f"[VERBOSE] Using default source path: {default}")
        return default
    if not interactive:
        return None
    # Interactive mode: prompt user for source path
    click.echo("No data source path configured.")
    click.echo(f"Default path not found: {ConfigManager.DEFAULT_SOURCE}")
    user_input = click.prompt("Please enter the vehicle data source path", type=str)
    source = Path(user_input).resolve()
    if not source.exists():
        raise click.BadParameter(f"Source path does not exist: {source}")
    config.set_source_path(source)
    click.echo(f"Source path saved: {source}")
    return source


def resolve_database_path(ctx, source_path: Optional[Path] = None) -> Path:
    """Resolve database directory from context, config, or derive from source.

    Returns the database *directory* (not a file path). Dual-db files
    (Ripple.db + Slope.db) are created/resolved inside this directory.

    For the 'init' command, -o/--output or -d/--database is mandatory.
    For other commands, falls back to config or source-derived path.

    Backward compat: if -d points to a .db file, returns its parent dir.

    Args:
        ctx: Click context object.
        source_path: Optional source path to derive database location from.

    Returns:
        Resolved database directory path.

    Raises:
        click.BadParameter: If no database path can be resolved.
    """
    cmd_name = ctx.command.name if hasattr(ctx, "command") and ctx.command else ""

    if ctx.obj.get("database"):
        db_path = Path(ctx.obj["database"])
        # Backward compat: if CLI points to a file, use its parent dir
        if db_path.suffix == '.db':
            db_path = db_path.parent
        if ctx.obj.get("verbose"):
            click.echo(f"[VERBOSE] Using database dir from CLI: {db_path}")
        return db_path
    if ctx.obj.get("output"):
        db_path = Path(ctx.obj["output"])
        if ctx.obj.get("verbose"):
            click.echo(f"[VERBOSE] Using database dir from output: {db_path}")
        return db_path

    config = ConfigManager()
    config_db = config.get_database_path()
    if config_db:
        if ctx.obj.get("verbose"):
            click.echo(f"[VERBOSE] Using database dir from config: {config_db}")
        return config_db

    if source_path is not None:
        db_path = source_path.parent / "Vehicle_Database"
        if ctx.obj.get("verbose"):
            click.echo(f"[VERBOSE] Derived database dir from source: {db_path}")
        return db_path

    if cmd_name == "init":
        raise click.BadParameter(
            "init command requires -o/--output or -d/--database to specify where to create the database."
        )

    raise click.BadParameter(
        "Database path not specified. Use -d/--database to specify the database path, "
        "or run 'init' first to create a database."
    )


def find_vehicle_folders(source_path: Path) -> List[Path]:
    """Find all vehicle folders in source path."""
    vehicles = []
    if not source_path.exists():
        return vehicles
    for item in source_path.iterdir():
        if item.is_dir():
            name = item.name
            if name.startswith("V") and len(name) >= 5:
                if name[1:5].isdigit() or (name.endswith("_RIPPLE") and name[1:-7].isdigit()):
                    vehicles.append(item)
    return sorted(vehicles)


def get_vehicle_id_from_path(vehicle_path: Path) -> str:
    """Extract clean vehicle ID from folder path."""
    vehicle_id = vehicle_path.name
    if vehicle_id.endswith("_RIPPLE"):
        vehicle_id = vehicle_id[:-7]
    return vehicle_id


def _delete_vehicle(db: DatabaseConnection, vehicle_id: str, data_type: str = 'ripple'):
    """Delete vehicle and all related records from database.

    Args:
        db: Database connection.
        vehicle_id: Vehicle identifier.
        data_type: 'ripple' or 'slope' — determines which results table to delete from.
    """
    table_name = 'ripple_results' if data_type == 'ripple' else 'slope_results'
    db.execute(f"DELETE FROM {table_name} WHERE vehicle_id = ?", (vehicle_id,))
    db.execute("DELETE FROM data_batches WHERE vehicle_id = ?", (vehicle_id,))
    db.execute("DELETE FROM matching_logs WHERE vehicle_id = ?", (vehicle_id,))
    db.execute("DELETE FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))


def import_vehicle(db_ripple, db_slope, vehicle_id: str, vehicle_path: Path, format_filter: str):
    """Import vehicle data into dual databases (Ripple.db + Slope.db).

    Uses DataFormatDetector to find data sources, then routes each source
    to the appropriate database based on data_type.

    Args:
        db_ripple: DatabaseConnection for Ripple.db (or None if not available).
        db_slope: DatabaseConnection for Slope.db (or None if not available).
        vehicle_id: Vehicle identifier.
        vehicle_path: Path to the vehicle source folder.
        format_filter: Format filter (all, json, excel, sqlite, db).

    Returns:
        ImportResult from importers.base (aggregated across all matched sources).
    """
    from ..importers import JsonImporter, ExcelImporter, SqliteImporter
    from ..importers.auto_detect import DataFormatDetector
    from ..importers.base import ImportResult

    sources = DataFormatDetector.detect(vehicle_path)

    if format_filter != "all":
        fmt = format_filter if format_filter != "db" else "sqlite"
        sources = [s for s in sources if s.format == fmt]

    if not sources:
        return ImportResult(
            vehicle_id=vehicle_id,
            data_type="unknown",
            errors=[f"No suitable data source found in {vehicle_path} for format filter: {format_filter}"],
        )

    total_result = ImportResult(vehicle_id=vehicle_id, data_type="unknown")

    # CR-N4 v1.4: import 前 DELETE 该 vehicle_id 的旧 results 行,避免减行重导留孤儿数据
    # 之前用 INSERT OR REPLACE,但旧 (component_code, condition_id) 组合若新数据不再产生,
    # 旧行会永久残留 → 数据库与 JSON 不一致
    # 仅删除 results 表,保留 components/test_conditions 字典表 (跨车辆共享)
    has_ripple_source = any(s.data_type == 'ripple' for s in sources)
    has_slope_source = any(s.data_type == 'slope' for s in sources)
    if has_ripple_source and db_ripple is not None:
        try:
            db_ripple.execute("DELETE FROM ripple_results WHERE vehicle_id = ?", (vehicle_id,))
        except Exception as e:
            total_result.warnings.append(f"Pre-import DELETE ripple_results failed: {e}")
    if has_slope_source and db_slope is not None:
        try:
            db_slope.execute("DELETE FROM slope_results WHERE vehicle_id = ?", (vehicle_id,))
        except Exception as e:
            total_result.warnings.append(f"Pre-import DELETE slope_results failed: {e}")

    for source in sources:
        importer = None
        if source.format == "json":
            importer = JsonImporter()
        elif source.format == "excel":
            importer = ExcelImporter()
        elif source.format == "sqlite":
            importer = SqliteImporter()

        if importer is None:
            continue

        # Route to the correct database based on data_type
        target_db = None
        if source.data_type == 'ripple' and db_ripple is not None:
            target_db = db_ripple
        elif source.data_type == 'slope' and db_slope is not None:
            target_db = db_slope

        if target_db is None:
            total_result.warnings.append(
                f"Skipping {source.data_type} data: target database not available"
            )
            continue

        result = importer.import_data(target_db.conn, vehicle_id, source.path)
        total_result.components_imported += result.components_imported
        total_result.conditions_imported += result.conditions_imported
        total_result.warnings.extend(result.warnings)
        total_result.errors.extend(result.errors)
        if result.data_type != "unknown":
            total_result.data_type = result.data_type

    # Sync vehicle_info to all databases that have data for this vehicle
    try:
        has_ripple = any(s.data_type == 'ripple' for s in sources)
        has_slope = any(s.data_type == 'slope' for s in sources)
        if has_ripple and db_ripple is not None:
            _sync_vehicle_info(db_ripple, vehicle_id, vehicle_path)
        if has_slope and db_slope is not None:
            _sync_vehicle_info(db_slope, vehicle_id, vehicle_path)
    except Exception as e:
        total_result.warnings.append(f"Vehicle info sync warning: {e}")

    return total_result


def _load_vehicle_info_md(path: Path) -> Optional[Dict[str, str]]:
    """解析 vehicle_info.md Markdown表格，返回 {中文字段名: 值} 字典"""
    if not path.exists():
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(path, 'r', encoding='gbk') as f:
            lines = f.readlines()

    headers = None
    data_row = None
    for i, line in enumerate(lines):
        line = line.strip()
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.split('|')[1:-1]]
        if not parts:
            continue
        # 检查下一行是否为分隔符 (包含 :---)
        if i + 1 < len(lines) and ':--' in lines[i + 1]:
            headers = parts
            if i + 2 < len(lines):
                data_parts = [p.strip() for p in lines[i + 2].split('|')[1:-1]]
                if data_parts and len(data_parts) == len(headers):
                    data_row = data_parts
            break

    if headers and data_row:
        return dict(zip(headers, data_row))
    return None


def _sync_vehicle_info(db: DatabaseConnection, vehicle_id: str, vehicle_path: Path) -> None:
    """
    从 vehicle_info.md 或 vehicle_info.xlsx 同步完整车辆信息到数据库。

    该函数在 import_vehicle 最后被调用，确保无论使用 JSON/SQLite/Excel
    哪种导入器，vehicles 表中的车辆基本信息都会被更新为最新内容。
    """
    info_md = vehicle_path / "vehicle_info.md"
    info_xlsx = vehicle_path / "vehicle_info.xlsx"

    vehicle_info: Optional[Dict[str, str]] = None

    # HR-N7 + P2.10 v1.4: md 与 xlsx 都存在时,mtime 差异大于 60s 给出警告
    # 避免用户编辑 xlsx 后期望生效,但实际 md 优先被读取
    if info_md.exists() and info_xlsx.exists():
        try:
            md_mtime = info_md.stat().st_mtime
            xlsx_mtime = info_xlsx.stat().st_mtime
            if abs(md_mtime - xlsx_mtime) > 60:  # 1 min 阈值
                from datetime import datetime as _dt
                newer = 'xlsx' if xlsx_mtime > md_mtime else 'md'
                import sys as _sys
                print(
                    f"[WARN] {vehicle_id}: vehicle_info.md ({_dt.fromtimestamp(md_mtime).isoformat(timespec='seconds')}) "
                    f"与 .xlsx ({_dt.fromtimestamp(xlsx_mtime).isoformat(timespec='seconds')}) "
                    f"mtime 差异较大 (newer={newer})。使用 md (优先级更高)。建议选择一种格式以避免歧义。",
                    file=_sys.stderr
                )
        except OSError:
            pass

    if info_md.exists():
        vehicle_info = _load_vehicle_info_md(info_md)
    elif info_xlsx.exists():
        try:
            import pandas as pd
            df = pd.read_excel(info_xlsx)
            if not df.empty:
                row = df.iloc[0]
                vehicle_info = {str(k): str(v) if pd.notna(v) else '' for k, v in row.items()}
        except Exception as e:
            # HR-N7 + P2.10 v1.4: xlsx 解析失败时显式日志,避免静默吞
            import sys as _sys
            print(
                f"[ERROR] {vehicle_id}: vehicle_info.xlsx 解析失败: {type(e).__name__}: {e}",
                file=_sys.stderr
            )

    if not vehicle_info:
        return

    # 中文字段名 → 数据库英文字段名 映射
    key_mapping: Dict[str, str] = {
        '车型': 'vehicle_model',
        '车辆型号': 'vehicle_model',
        '制造商': 'manufacturer',
        '级别': 'level',
        '能源类型': 'energy_type',
        '车长mm': 'length_mm',
        '车宽mm': 'width_mm',
        '车高mm': 'height_mm',
        '轴距(mm)': 'wheelbase_mm',
        '前轮距(mm)': 'front_track_mm',
        '后轮距(mm)': 'rear_track_mm',
        '最小离地间隙(mm)': 'min_ground_clearance_mm',
        '整备质量(kg)': 'curb_weight_kg',
        '最大满载质量(kg)': 'max_weight_kg',
        '前电机最大功率(kW)': 'front_motor_max_power_kw',
        '后电机最大功率(kW)': 'rear_motor_max_power_kw',
        '前电机最大扭矩(N·m)': 'front_motor_max_torque_nm',
        '后电机最大扭矩(N·m)': 'rear_motor_max_torque_nm',
        '系统综合功率(kW)': 'system_total_power_kw',
        '高压架构': 'high_voltage_architecture',
        '电池类型': 'battery_type',
        '电池能量(kWh)': 'battery_capacity_kwh',
        '快充功率(kW)': 'fast_charge_power_kw',
        '前悬类型': 'front_suspension',
        '后悬类型': 'rear_suspension',
        '发动机型号': 'engine_model',
        '变速箱类型': 'transmission_type',
        '排量(L)': 'displacement_l',
        '发动机最大净功率(kW/rpm)': 'engine_max_power_kw',
        '发动机最大净扭矩(N·m/rpm)': 'engine_max_torque_nm',
        '指导价格（万元）': 'price_wan',
    }

    mapped: Dict[str, Any] = {}
    for src_key, db_key in key_mapping.items():
        val = vehicle_info.get(src_key)
        if val and str(val).strip():
            # 尝试转为数字
            s = str(val).strip()
            try:
                if '.' in s:
                    mapped[db_key] = float(s)
                else:
                    mapped[db_key] = int(s)
            except ValueError:
                mapped[db_key] = s

    if not mapped:
        return

    # 始终保存原始 JSON
    mapped['vehicle_info_json'] = json.dumps(vehicle_info, ensure_ascii=False)

    # 检查车辆是否已存在
    db.execute("SELECT 1 FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
    exists = db.fetchone() is not None

    if exists:
        # UPDATE
        fields = list(mapped.keys())
        values = list(mapped.values())
        set_clause = ", ".join(f"{f} = ?" for f in fields)
        db.execute(
            f"UPDATE vehicles SET {set_clause} WHERE vehicle_id = ?",
            values + [vehicle_id]
        )
    else:
        # INSERT (需要 vehicle_id 和至少 vehicle_model)
        mapped['vehicle_id'] = vehicle_id
        if 'vehicle_model' not in mapped:
            mapped['vehicle_model'] = vehicle_id
        fields = list(mapped.keys())
        placeholders = ", ".join("?" for _ in fields)
        db.execute(
            f"INSERT INTO vehicles ({', '.join(fields)}) VALUES ({placeholders})",
            list(mapped.values())
        )
