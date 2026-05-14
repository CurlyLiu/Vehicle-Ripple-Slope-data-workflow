#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Init command for CLI."""

import click

from ..core import (
    ConfigManager,
    DatabaseConnection,
    find_vehicle_folders,
    get_vehicle_id_from_path,
    import_vehicle,
    init_database,
    resolve_database_path,
    resolve_source_path,
)
from .add import _auto_export_combined


@click.command()
@click.option("--output", "-o", help="Output directory for database")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (for CI/automation)")
@click.pass_context
def init(ctx, output, yes):
    """Initialize database with schema and auto-import all vehicles.

    WARNING (HR-N3 v1.4): This command has TWO side effects:
      1. Creates fresh Ripple.db + Slope.db schemas (overwrites existing)
      2. Auto-imports ALL vehicles from source_path (mass import, may take HOURS)

    Use `add <vehicle_id>` or `add --all` for incremental imports without
    re-initializing schemas. Only use `init` when:
      - Setting up the database for the first time
      - Or intentionally rebuilding from scratch

    To recover from accidental DB deletion, prefer restoring from snapshot
    (e.g., ~/skill-snapshot-2026-05-11.zip) rather than running init.

    Use --yes/-y to skip confirmation (for CI/automation).
    """
    if output:
        ctx.obj["output"] = output
    source_path = resolve_source_path(ctx)
    db_dir = resolve_database_path(ctx, source_path)
    click.echo(f"Initializing database at: {db_dir}")
    # HR-N3 + VDB-H5 v1.4: 显眼警告 mass-import 副作用 + 交互式确认
    click.echo("[WARN] init will auto-import ALL vehicles from source. This may take hours.")
    click.echo("[INFO] For incremental imports, use `add <vehicle_id>` instead.")
    if not yes and not click.confirm("Continue with mass-import?", default=False):
        click.echo("Aborted. No changes made.")
        return
    init_database(db_dir)
    click.echo("Database schema created (Ripple.db + Slope.db).")
    config = ConfigManager()
    config.set_source_path(source_path)
    config.set_database_path(db_dir)
    click.echo(f"Scanning for vehicles in: {source_path}")
    vehicles = find_vehicle_folders(source_path)
    if not vehicles:
        click.echo("No vehicles found.")
        return
    click.echo(f"Found {len(vehicles)} vehicle(s). Importing...")
    success_count = 0
    ripple_db_path = db_dir / "Ripple.db"
    slope_db_path = db_dir / "Slope.db"
    with DatabaseConnection(ripple_db_path) as db_ripple, DatabaseConnection(slope_db_path) as db_slope:
        for vehicle_path in vehicles:
            vehicle_id = get_vehicle_id_from_path(vehicle_path)
            click.echo(f"  Importing {vehicle_id}...", nl=False)
            if ctx.obj.get("verbose"):
                click.echo(f"[VERBOSE] Found source: {vehicle_path}")
            result = import_vehicle(db_ripple, db_slope, vehicle_id, vehicle_path, ctx.obj["format_filter"])
            if result.success:
                click.echo(f" OK ({result.components_imported} components, {result.conditions_imported} conditions)")
                success_count += 1
            else:
                click.echo(" FAILED")
                for error in result.errors:
                    click.echo(f"    Error: {error}")

        if success_count > 0:
            _auto_export_combined(db_ripple, db_slope, db_dir)
    click.echo(f"Initialized with {success_count}/{len(vehicles)} vehicles imported.")
