#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove command for CLI."""

import sys

import click

from ..core import DatabaseConnection, _delete_vehicle, resolve_database_path, resolve_source_path


@click.command()
@click.argument("vehicle_ids", nargs=-1)
@click.option("--all", "remove_all", is_flag=True, help="Remove all vehicles from database")
@click.pass_context
def remove(ctx, vehicle_ids, remove_all):
    """Remove vehicles from database only (keep source files)."""
    source_path = resolve_source_path(ctx, interactive=False)
    db_dir = resolve_database_path(ctx, source_path)
    ripple_db = db_dir / "Ripple.db"
    slope_db = db_dir / "Slope.db"
    if not ripple_db.exists() and not slope_db.exists():
        click.echo("Database not found.")
        sys.exit(1)
    if remove_all:
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
        if not vehicle_ids:
            click.echo("No vehicles in database.")
            return
        if not click.confirm(f"Remove ALL {len(vehicle_ids)} vehicles from database?"):
            click.echo("Cancelled.")
            return
    elif not vehicle_ids:
        click.echo("Error: Specify vehicle IDs or use --all")
        sys.exit(1)
    click.echo(f"Removing {len(vehicle_ids)} vehicle(s)...")
    removed_count = 0
    failed_count = 0
    for vehicle_id in vehicle_ids:
        removed_any = False
        try:
            # v1.6 hotfix P2.3: 加 try/except 隔离单车失败 (FK 约束 / sqlite lock 等)
            # 避免中途异常逃出循环导致 removed_count 状态不一致
            if ripple_db.exists():
                with DatabaseConnection(ripple_db) as db:
                    db.execute("SELECT 1 FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
                    if db.fetchone():
                        _delete_vehicle(db, vehicle_id, 'ripple')
                        removed_any = True
            if slope_db.exists():
                with DatabaseConnection(slope_db) as db:
                    db.execute("SELECT 1 FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
                    if db.fetchone():
                        _delete_vehicle(db, vehicle_id, 'slope')
                        removed_any = True
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            click.echo(f"  Removing {vehicle_id}... FAILED ({type(e).__name__}: {e})")
            failed_count += 1
            continue

        if removed_any:
            click.echo(f"  Removing {vehicle_id}... OK")
            removed_count += 1
        else:
            click.echo(f"  Removing {vehicle_id}... NOT FOUND")
    click.echo(f"Removed {removed_count} vehicles from database.")
    if failed_count > 0:
        click.echo(f"Failed: {failed_count} vehicles.")
    click.echo("Note: Source files were not affected.")
