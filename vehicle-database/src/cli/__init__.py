#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vehicle Database CLI - New Command Structure.

车辆测试数据管理工具

Usage:
    vehicle_database.py init [--output DIR]
    vehicle_database.py add V0001 [V0002...] | --all
    vehicle_database.py update V0001 [V0002...] | --all
    vehicle_database.py remove V0001 [V0002...] | --all
    vehicle_database.py list [--format table|json]
    vehicle_database.py show V0001
    vehicle_database.py stats
    vehicle_database.py export V0001 [--excel|--json|--sqlite] [-o OUTPUT]
"""

import click

from .commands import add, export, init, list_vehicles, remove, show, stats, update


@click.group()
@click.option("--source", "-s", help="Vehicle data source path")
@click.option("--database", "-d", help="Database path")
@click.option("--format", "-f", "format_filter",
               type=click.Choice(["db", "excel", "json", "all"]),
               default="all", help="Input format filter")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, source, database, format_filter, verbose):
    """Vehicle Database CLI - 车辆测试数据管理工具"""
    ctx.ensure_object(dict)
    ctx.obj["source"] = source
    ctx.obj["database"] = database
    ctx.obj["format_filter"] = format_filter
    ctx.obj["verbose"] = verbose


cli.add_command(init)
cli.add_command(add)
cli.add_command(update)
cli.add_command(remove)
cli.add_command(list_vehicles)
cli.add_command(show)
cli.add_command(stats)
cli.add_command(export)


__all__ = ["cli"]
