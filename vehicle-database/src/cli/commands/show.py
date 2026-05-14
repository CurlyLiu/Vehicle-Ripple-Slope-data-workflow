#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Show command for CLI."""

import sys

import click

from ..core import DatabaseConnection, resolve_database_path, resolve_source_path


@click.command()
@click.argument("vehicle_id")
@click.option("--type", "data_type", type=click.Choice(["ripple", "slope"]), default="ripple", help="Database type to query")
@click.pass_context
def show(ctx, vehicle_id, data_type):
    """Show detailed vehicle information."""
    source_path = resolve_source_path(ctx, interactive=False)
    db_dir = resolve_database_path(ctx, source_path)
    db_file = db_dir / ("Ripple.db" if data_type == 'ripple' else "Slope.db")
    if not db_file.exists():
        click.echo("Database not found.")
        sys.exit(1)
    table_name = 'ripple_results' if data_type == 'ripple' else 'slope_results'
    with DatabaseConnection(db_file) as db:
        db.execute(
            "SELECT vehicle_id, vehicle_model, manufacturer, created_at, updated_at FROM vehicles WHERE vehicle_id = ?",
            (vehicle_id,)
        )
        row = db.fetchone()
        if not row:
            click.echo(f"Vehicle {vehicle_id} not found in database.")
            sys.exit(1)
        click.echo(f"Vehicle ID:     {row[0]}")
        click.echo(f"Model:          {row[1] or 'N/A'}")
        click.echo(f"Manufacturer:   {row[2] or 'N/A'}")
        click.echo(f"Created:        {row[3]}")
        click.echo(f"Updated:        {row[4]}")
        click.echo()
        db.execute(f"SELECT COUNT(DISTINCT component_code) FROM {table_name} WHERE vehicle_id = ?", (vehicle_id,))
        comp_count = db.fetchone()[0] or 0
        click.echo(f"Components:     {comp_count}")
        db.execute(f"SELECT COUNT(DISTINCT condition_id) FROM {table_name} WHERE vehicle_id = ?", (vehicle_id,))
        row = db.fetchone()
        cond_count = row[0] if row else 0
        click.echo(f"Conditions:     {cond_count}")
        click.echo()
        if comp_count > 0:
            click.echo("Component Breakdown:")
            db.execute(
                f"""SELECT component_code, COUNT(DISTINCT condition_id) as cond_count
                   FROM {table_name}
                   WHERE vehicle_id = ?
                   GROUP BY component_code
                   ORDER BY component_code""",
                (vehicle_id,)
            )
            for row in db.fetchall():
                click.echo(f"  {row[0]:<15} {row[1]} conditions")
        if cond_count > 0:
            click.echo()
            click.echo("Test Results Summary:")
            db.execute(f"SELECT COUNT(*) FROM {table_name} WHERE vehicle_id = ?", (vehicle_id,))
            test_count = db.fetchone()[0] or 0
            click.echo(f"  {data_type.capitalize()} tests: {test_count}")
