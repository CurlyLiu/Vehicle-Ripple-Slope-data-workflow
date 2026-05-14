#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add command for CLI."""

import sys

import click

from ..core import (
    DatabaseConnection,
    find_vehicle_folders,
    get_vehicle_id_from_path,
    import_vehicle,
    resolve_database_path,
    resolve_source_path,
)
from ...exporters import JsonExporter, ExcelExporter


@click.command()
@click.argument("vehicle_ids", nargs=-1)
@click.option("--all", "import_all", is_flag=True, help="Import all vehicles from source")
@click.pass_context
def add(ctx, vehicle_ids, import_all):
    """Add vehicles from source to database."""
    source_path = resolve_source_path(ctx)
    db_dir = resolve_database_path(ctx, source_path)
    ripple_db = db_dir / "Ripple.db"
    slope_db = db_dir / "Slope.db"
    if not ripple_db.exists() and not slope_db.exists():
        click.echo("Database not found. Run init first.")
        sys.exit(1)
    if import_all:
        vehicles = find_vehicle_folders(source_path)
    elif vehicle_ids:
        vehicles = [source_path / vid for vid in vehicle_ids]
    else:
        click.echo("Error: Specify vehicle IDs or use --all")
        sys.exit(1)
    if not vehicles:
        click.echo("No vehicles found to import.")
        return
    click.echo(f"Adding {len(vehicles)} vehicle(s)...")
    if ctx.obj.get("verbose"):
        click.echo(f"[VERBOSE] Source: {source_path}, Database dir: {db_dir}")
    success_count = 0

    # NEW-1 + HR-N1 + P2.4-revised v1.4: 用 with DatabaseConnection 替代 try/finally
    # __exit__ 在异常时自动 rollback,正常时统一 commit
    # 配合 importer 内部去掉 commit,实现真正的原子事务
    from contextlib import ExitStack
    with ExitStack() as stack:
        db_ripple = stack.enter_context(DatabaseConnection(ripple_db)) if ripple_db.exists() else None
        db_slope = stack.enter_context(DatabaseConnection(slope_db)) if slope_db.exists() else None

        for vehicle_path in vehicles:
            if not vehicle_path.exists():
                click.echo(f"  {vehicle_path.name}: NOT FOUND")
                continue
            vehicle_id = get_vehicle_id_from_path(vehicle_path)
            click.echo(f"  Adding {vehicle_id}...", nl=False)
            if ctx.obj.get("verbose"):
                click.echo(f"[VERBOSE] Importing from {vehicle_path}...")

            # VDB-C1 v1.4 修订: 用 SAVEPOINT 隔离每辆车,失败时仅 ROLLBACK TO 当前车
            # 配合 importer re-raise + DELETE 前置,确保失败车的 DELETE 也被回滚
            savepoint_name = f"vh_{vehicle_id.replace('-', '_')}"
            if db_ripple:
                db_ripple.conn.execute(f"SAVEPOINT {savepoint_name}")
            if db_slope:
                db_slope.conn.execute(f"SAVEPOINT {savepoint_name}")

            try:
                result = import_vehicle(db_ripple, db_slope, vehicle_id, vehicle_path, ctx.obj["format_filter"])
                if result.success:
                    # 提交此车的 savepoint
                    if db_ripple:
                        db_ripple.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    if db_slope:
                        db_slope.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    click.echo(f" OK ({result.components_imported} components, {result.conditions_imported} conditions)")
                    success_count += 1
                else:
                    # v1.6 hotfix P4.1: 防御性分支 (此分支理论不会走到, 因为 importer 现在 raise)
                    # 保留作为兜底, 防御未来 importer 行为变化
                    if db_ripple:
                        db_ripple.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        db_ripple.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    if db_slope:
                        db_slope.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        db_slope.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    click.echo(" FAILED")
                    for error in result.errors:
                        click.echo(f"    Error: {error}")
            except (KeyboardInterrupt, SystemExit):
                # 不要吞 Ctrl-C
                if db_ripple:
                    try:
                        db_ripple.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    except Exception:
                        pass
                if db_slope:
                    try:
                        db_slope.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    except Exception:
                        pass
                raise
            except Exception as e:
                # VDB-C1 v1.4: 单车异常,回滚此车 savepoint,继续下一车
                if db_ripple:
                    try:
                        db_ripple.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        db_ripple.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    except Exception:
                        pass
                if db_slope:
                    try:
                        db_slope.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        db_slope.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    except Exception:
                        pass
                click.echo(f" FAILED ({type(e).__name__}: {e})")
                if ctx.obj.get("verbose"):
                    import traceback
                    click.echo(traceback.format_exc())

        click.echo(f"Added {success_count}/{len(vehicles)} vehicles.")

        # Auto-export combined JSON and Excel
        if success_count > 0:
            _auto_export_combined(db_ripple, db_slope, db_dir)

    # CR-N7 v1.4: add.py exit 码传播,避免 stage4 cache 静默污染
    # exit 2 = 完全失败 (success_count==0 且有车辆)
    # exit 3 = 部分失败 (success_count < len(vehicles))
    # exit 0 = 全部成功 (或无车辆,无害)
    if success_count == 0 and len(vehicles) > 0:
        sys.exit(2)
    elif success_count < len(vehicles):
        sys.exit(3)


def _auto_export_combined(db_ripple, db_slope, db_dir):
    """Export all vehicles to combined JSON and Excel files per database."""
    if db_ripple and db_ripple.conn:
        json_path = db_dir / "Ripple.json"
        excel_path = db_dir / "Ripple.xlsx"
        try:
            db_ripple.execute("SELECT vehicle_id FROM vehicles")
            all_ids = [row[0] for row in db_ripple.fetchall()]
            if all_ids:
                click.echo(f"  Exporting Ripple JSON...", nl=False)
                exporter = JsonExporter(data_type='ripple')
                result = exporter.export_all(db_ripple.conn, json_path)
                click.echo(f" OK ({result.records_exported} records)" if result.success else " FAILED")
                click.echo(f"  Exporting Ripple Excel...", nl=False)
                exporter = ExcelExporter(data_type='ripple')
                result = exporter.export_all(db_ripple.conn, excel_path)
                click.echo(f" OK ({result.records_exported} records)" if result.success else " FAILED")
        except Exception as e:
            click.echo(f"  Ripple auto-export error: {e}")

    if db_slope and db_slope.conn:
        json_path = db_dir / "Slope.json"
        excel_path = db_dir / "Slope.xlsx"
        try:
            db_slope.execute("SELECT vehicle_id FROM vehicles")
            all_ids = [row[0] for row in db_slope.fetchall()]
            if all_ids:
                click.echo(f"  Exporting Slope JSON...", nl=False)
                exporter = JsonExporter(data_type='slope')
                result = exporter.export_all(db_slope.conn, json_path)
                click.echo(f" OK ({result.records_exported} records)" if result.success else " FAILED")
                click.echo(f"  Exporting Slope Excel...", nl=False)
                exporter = ExcelExporter(data_type='slope')
                result = exporter.export_all(db_slope.conn, excel_path)
                click.echo(f" OK ({result.records_exported} records)" if result.success else " FAILED")
        except Exception as e:
            click.echo(f"  Slope auto-export error: {e}")
