#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stats command for CLI."""

import sys

import click

from ..core import DatabaseConnection, resolve_database_path, resolve_source_path


@click.command()
@click.option("--type", "data_type", type=click.Choice(["ripple", "slope"]), default="ripple", help="Database type to query")
@click.pass_context
def stats(ctx, data_type):
    """Show database statistics."""
    source_path = resolve_source_path(ctx, interactive=False)
    db_dir = resolve_database_path(ctx, source_path)
    db_file = db_dir / ("Ripple.db" if data_type == 'ripple' else "Slope.db")
    if not db_file.exists():
        click.echo("Database not found.")
        sys.exit(1)
    table_name = 'ripple_results' if data_type == 'ripple' else 'slope_results'
    with DatabaseConnection(db_file) as db:
        db_size = db_file.stat().st_size / (1024 * 1024)
        click.echo(f"Database:       {db_file}")
        click.echo(f"Size:           {db_size:.2f} MB")
        click.echo()
        db.execute("SELECT COUNT(*) FROM vehicles")
        row = db.fetchone()
        vehicle_count = row[0] if row else 0
        click.echo(f"Vehicles:       {vehicle_count}")
        db.execute("SELECT COUNT(*) FROM components")
        row = db.fetchone()
        comp_count = row[0] if row else 0
        click.echo(f"Components:     {comp_count}")
        db.execute("SELECT COUNT(*) FROM test_conditions")
        row = db.fetchone()
        cond_count = row[0] if row else 0
        click.echo(f"Conditions:     {cond_count}")
        click.echo()
        if vehicle_count > 0:
            db.execute(
                f"""SELECT vehicle_id,
                          (SELECT COUNT(DISTINCT component_code) FROM {table_name} WHERE vehicle_id = v.vehicle_id) as comp_count
                   FROM vehicles v
                   ORDER BY comp_count DESC LIMIT 5"""
            )
            click.echo(f"Top 5 Vehicles by Component Count ({data_type}):")
            for row in db.fetchall():
                click.echo(f"  {row[0]:<12} {row[1]} components")
            click.echo()
            db.execute(
                f"""SELECT component_code, COUNT(*) as test_count
                   FROM {table_name}
                   GROUP BY component_code
                   ORDER BY test_count DESC LIMIT 5"""
            )
            click.echo(f"Top 5 Most Tested Components ({data_type}):")
            rows = db.fetchall()
            if rows:
                for row in rows:
                    click.echo(f"  {row[0]:<15} {row[1]} conditions")
            else:
                click.echo("  No test data available")
