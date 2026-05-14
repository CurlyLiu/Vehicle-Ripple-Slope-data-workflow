#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List command for CLI."""

import json
import sys

import click

from ..core import DatabaseConnection, resolve_database_path, resolve_source_path


@click.command(name="list")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.option("--ids", is_flag=True, help="Only output vehicle IDs (one per line)")
@click.option("--type", "data_type", type=click.Choice(["ripple", "slope"]), default="ripple", help="Database type to query")
@click.pass_context
def list_vehicles(ctx, output_format, ids, data_type):
    """List all vehicles in database."""
    source_path = resolve_source_path(ctx, interactive=False)
    db_dir = resolve_database_path(ctx, source_path)
    db_file = db_dir / ("Ripple.db" if data_type == 'ripple' else "Slope.db")
    if not db_file.exists():
        click.echo(f"Database not found: {db_file}")
        sys.exit(1)
    table_name = 'ripple_results' if data_type == 'ripple' else 'slope_results'
    with DatabaseConnection(db_file) as db:
        db.execute(
            f"""SELECT vehicle_id, vehicle_model, manufacturer,
                      (SELECT COUNT(DISTINCT component_code) FROM {table_name} WHERE vehicle_id = vehicles.vehicle_id) as comp_count,
                      (SELECT COUNT(DISTINCT condition_id) FROM {table_name} WHERE vehicle_id = vehicles.vehicle_id) as cond_count
               FROM vehicles ORDER BY vehicle_id"""
        )
        rows = db.fetchall()
    if not rows:
        click.echo("No vehicles in database.")
        return
    if ids:
        for row in rows:
            click.echo(row[0])
        return
    if output_format == "json":
        vehicles = [
            {
                "vehicle_id": row[0],
                "model": row[1],
                "manufacturer": row[2],
                "component_count": row[3],
                "condition_count": row[4]
            }
            for row in rows
        ]
        click.echo(json.dumps(vehicles, ensure_ascii=False, indent=2))
    else:
        click.echo(f"{'Vehicle ID':<12} {'Model':<20} {'Manufacturer':<15} {'Components':<12} {'Conditions':<12}")
        click.echo("-" * 75)
        for row in rows:
            click.echo(f"{row[0]:<12} {row[1] or 'N/A':<20} {row[2] or 'N/A':<15} {row[3]:<12} {row[4]:<12}")
