#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update command for CLI.

v1.6 hotfix P1.1: 完全重写为 add.py 同款 ExitStack+SAVEPOINT+exit code 模式
- NEW-1 原子性: 共享 with 块, importer raise 触发 SAVEPOINT rollback
- HR-N1: 共享 DatabaseConnection 跨多车
- CR-N7: exit codes 0/2/3 (avoid stage4 cache 静默污染)
- CR-N4: 删除冗余 _delete_vehicle 调用 (import_vehicle 内部已 DELETE 前置)
"""

import sys
from contextlib import ExitStack

import click

from ..core import (
    DatabaseConnection,
    import_vehicle,
    resolve_database_path,
    resolve_source_path,
)


@click.command()
@click.argument("vehicle_ids", nargs=-1)
@click.option("--all", "update_all", is_flag=True, help="Update all vehicles in database")
@click.pass_context
def update(ctx, vehicle_ids, update_all):
    """Re-import vehicles (atomic delete + re-import via import_vehicle).

    v1.6 hotfix P1.1: import_vehicle 内部已 DELETE results 前置 (CR-N4),
    无需在 update.py 显式调 _delete_vehicle —— 那是 v1.4 的冗余设计。
    """
    source_path = resolve_source_path(ctx)
    db_dir = resolve_database_path(ctx, source_path)
    ripple_db = db_dir / "Ripple.db"
    slope_db = db_dir / "Slope.db"
    if not ripple_db.exists() and not slope_db.exists():
        click.echo("Database not found. Run init first.")
        sys.exit(1)
    if update_all:
        # Collect IDs from both databases
        all_ids = set()
        if ripple_db.exists():
            with DatabaseConnection(ripple_db) as db:
                db.execute("SELECT vehicle_id FROM vehicles")
                all_ids.update(row[0] for row in db.fetchall())
        if slope_db.exists():
            with DatabaseConnection(slope_db) as db:
                db.execute("SELECT vehicle_id FROM vehicles")
                all_ids.update(row[0] for row in db.fetchall())
        vehicle_ids = sorted(all_ids)
    elif not vehicle_ids:
        click.echo("Error: Specify vehicle IDs or use --all")
        sys.exit(1)
    if not vehicle_ids:
        click.echo("No vehicles to update.")
        return

    click.echo(f"Updating {len(vehicle_ids)} vehicle(s)...")
    if ctx.obj.get("verbose"):
        click.echo(f"[VERBOSE] Source: {source_path}, Database dir: {db_dir}")

    success_count = 0

    # v1.6 hotfix P1.1: ExitStack + SAVEPOINT 模式 (与 add.py 一致)
    with ExitStack() as stack:
        db_ripple = stack.enter_context(DatabaseConnection(ripple_db)) if ripple_db.exists() else None
        db_slope = stack.enter_context(DatabaseConnection(slope_db)) if slope_db.exists() else None

        for vehicle_id in vehicle_ids:
            vehicle_path = source_path / vehicle_id
            if not vehicle_path.exists():
                vehicle_path = source_path / f"{vehicle_id}_RIPPLE"
            if not vehicle_path.exists():
                click.echo(f"  {vehicle_id}: SOURCE NOT FOUND")
                continue
            click.echo(f"  Updating {vehicle_id}...", nl=False)
            if ctx.obj.get("verbose"):
                click.echo(f"[VERBOSE] Re-importing {vehicle_id}...")

            savepoint_name = f"vh_{vehicle_id.replace('-', '_')}"
            if db_ripple:
                db_ripple.conn.execute(f"SAVEPOINT {savepoint_name}")
            if db_slope:
                db_slope.conn.execute(f"SAVEPOINT {savepoint_name}")

            try:
                # import_vehicle 内部已 DELETE 前置 (CR-N4),无需显式调 _delete_vehicle
                result = import_vehicle(
                    db_ripple, db_slope, vehicle_id, vehicle_path, ctx.obj["format_filter"]
                )
                if result.success:
                    if db_ripple:
                        db_ripple.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    if db_slope:
                        db_slope.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    click.echo(f" OK ({result.components_imported} components, {result.conditions_imported} conditions)")
                    success_count += 1
                else:
                    # importer 已 re-raise (NEW-1), 此分支理论不会走到 - 防御性处理
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

        click.echo(f"Updated {success_count}/{len(vehicle_ids)} vehicles.")

    # v1.6 hotfix P1.1: CR-N7 exit codes (与 add.py 一致)
    # exit 2 = 完全失败 / exit 3 = 部分失败 / exit 0 = 全部成功
    if success_count == 0 and len(vehicle_ids) > 0:
        sys.exit(2)
    elif success_count < len(vehicle_ids):
        sys.exit(3)
