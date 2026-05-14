#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export command for CLI."""

import sys
from pathlib import Path

import click

from ..core import DatabaseConnection, resolve_database_path, resolve_source_path
from ...exporters import ExcelExporter, JsonExporter, SqliteExporter


@click.command()
@click.argument("vehicle_ids", nargs=-1)
@click.option("--all", "export_all", is_flag=True, help="Export all vehicles")
@click.option("--excel", "export_excel", is_flag=True, help="Export to Excel format")
@click.option("--json", "export_json", is_flag=True, help="Export to JSON format")
@click.option("--sqlite", "export_sqlite", is_flag=True, help="Export to SQLite format")
@click.option("--output", "-o", help="Output file or directory")
@click.option("--force", is_flag=True, help="Overwrite existing files without prompting")
@click.option("--combine", is_flag=True, help="Combine all vehicles into a single file (requires --all)")
@click.option("--type", "data_type", type=click.Choice(["ripple", "slope"]), default="ripple", help="Database type to export from")
@click.pass_context
def export(ctx, vehicle_ids, export_all, export_excel, export_json, export_sqlite, output, force, combine, data_type):
    """Export vehicle data to file."""
    source_path = resolve_source_path(ctx, interactive=False)
    db_dir = resolve_database_path(ctx, source_path)
    db_file = db_dir / ("Ripple.db" if data_type == 'ripple' else "Slope.db")
    if not db_file.exists():
        click.echo("Database not found.")
        sys.exit(1)

    formats = []
    if export_excel:
        formats.append("excel")
    if export_json:
        formats.append("json")
    if export_sqlite:
        formats.append("sqlite")
    if not formats:
        formats = ["json"] if (vehicle_ids and not export_all) else ["excel"]

    if export_all:
        with DatabaseConnection(db_file) as db:
            db.execute("SELECT vehicle_id FROM vehicles")
            vehicle_ids = [row[0] for row in db.fetchall()]
    elif not vehicle_ids:
        click.echo("Error: Specify vehicle IDs or use --all")
        sys.exit(1)

    output_path = Path(output) if output else Path.cwd() / "exports"

    # Combine mode: all vehicles into a single file
    if combine:
        if not export_all:
            click.echo("Error: --combine requires --all")
            sys.exit(1)
        if len(formats) > 1:
            click.echo("Error: --combine supports only one format at a time")
            sys.exit(1)

        fmt = formats[0]
        ext = {"json": "json", "excel": "xlsx", "sqlite": "db"}[fmt]
        if output:
            file_path = output_path if output_path.suffix else output_path / f"all_vehicles.{ext}"
        else:
            file_path = output_path / f"all_vehicles.{ext}"

        if file_path.exists() and not force:
            if not click.confirm(f"File already exists: {file_path}\nOverwrite?"):
                click.echo("Export cancelled.")
                return

        click.echo(f"Exporting all {len(vehicle_ids)} vehicles to single {fmt} file...")
        with DatabaseConnection(db_file) as db:
            if fmt == "json":
                exporter = JsonExporter(data_type=data_type)
            elif fmt == "excel":
                exporter = ExcelExporter(data_type=data_type)
            else:
                exporter = SqliteExporter()
            result = exporter.export_all(db.conn, file_path)
            if result.success:
                click.echo(f"  Exported to {file_path} ({result.records_exported} records)")
            else:
                click.echo("  FAILED")
                for err in result.errors:
                    click.echo(f"    Error: {err}")
        return

    # Normal mode: one file per vehicle
    files_to_overwrite = []
    for vehicle_id in vehicle_ids:
        for fmt in formats:
            if len(vehicle_ids) == 1 and output and not output_path.is_dir():
                file_path = output_path
            else:
                ext = {"json": "json", "excel": "xlsx", "sqlite": "db"}[fmt]
                file_path = output_path / f"{vehicle_id}_export.{ext}"
            if file_path.exists():
                files_to_overwrite.append(file_path)

    if files_to_overwrite and not force:
        click.echo("The following files already exist:")
        for fp in files_to_overwrite:
            click.echo(f"  {fp}")
        if not click.confirm("Overwrite existing files?"):
            click.echo("Export cancelled.")
            return

    click.echo(f"Exporting {len(vehicle_ids)} vehicle(s) to {', '.join(formats)}...")
    success_count = 0
    with DatabaseConnection(db_file) as db:
        for vehicle_id in vehicle_ids:
            vehicle_success = True
            for fmt in formats:
                if len(vehicle_ids) == 1 and output and not output_path.is_dir():
                    file_path = output_path
                else:
                    ext = {"json": "json", "excel": "xlsx", "sqlite": "db"}[fmt]
                    file_path = output_path / f"{vehicle_id}_export.{ext}"
                click.echo(f"  Exporting {vehicle_id} to {fmt}...", nl=False)
                if fmt == "json":
                    exporter = JsonExporter(data_type=data_type)
                elif fmt == "excel":
                    exporter = ExcelExporter(data_type=data_type)
                else:
                    exporter = SqliteExporter()
                result = exporter.export_vehicle(db.conn, vehicle_id, file_path)
                if result.success:
                    click.echo(" OK")
                else:
                    click.echo(" FAILED")
                    for err in result.errors:
                        click.echo(f"    Error: {err}")
                    vehicle_success = False
            if vehicle_success:
                success_count += 1
    click.echo(f"Exported {success_count}/{len(vehicle_ids)} vehicle(s).")
