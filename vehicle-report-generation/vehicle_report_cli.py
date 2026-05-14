"""报告生成CLI入口."""

import os
import re

import click

from scripts.core.ripple_report import generate_ripple_report
from scripts.core.slope_report import generate_slope_report
from scripts.utils.excel_reader import (
    detect_ripple_components,
    detect_slope_components,
)

DEFAULT_TEMPLATE = os.path.join(
    os.path.dirname(__file__), "templates", "ripple_report_template.docx"
)


@click.group()
def cli():
    """车辆检测报告生成工具."""
    pass


@cli.command()
@click.argument("vehicle_id")
@click.option(
    "--type",
    "report_type",
    type=click.Choice(["ripple", "slope", "all"]),
    default="all",
    help="报告类型",
)
@click.option(
    "--component",
    help="指定组件通道（如ACC_A），不指定则生成所有通道",
)
@click.option(
    "--base-dir",
    default="F:/Vehicle_Date",
    help="车辆数据根目录",
)
@click.option(
    "--template",
    default=DEFAULT_TEMPLATE,
    help="报告模板路径",
)
def generate(vehicle_id, report_type, component, base_dir, template):
    """生成车辆检测报告.

    示例：
        python vehicle_report_cli.py generate V0006
        python vehicle_report_cli.py generate V0006 --type ripple
        python vehicle_report_cli.py generate V0006 --type slope
        python vehicle_report_cli.py generate V0005 --type ripple --component ACC_A
    """
    _generate_reports(
        vehicle_id, report_type, component, base_dir, template
    )


@cli.command()
@click.argument("target_dir")
@click.option(
    "--type",
    "report_type",
    type=click.Choice(["ripple", "slope", "all"]),
    default="all",
    help="报告类型",
)
@click.option(
    "--component",
    help="指定组件通道（如ACC_A），不指定则生成所有通道",
)
@click.option(
    "--template",
    default=DEFAULT_TEMPLATE,
    help="报告模板路径",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    default=False,
    help="跳过已存在的报告",
)
def batch(target_dir, report_type, component, template, skip_existing):
    """批量生成目标路径下所有车辆的检测报告.

    扫描目标路径下所有 V0001、V0002 等车辆文件夹，依次生成报告。

    示例：
        python vehicle_report_cli.py batch F:/Vehicle_Date
        python vehicle_report_cli.py batch F:/Vehicle_Date --type ripple
        python vehicle_report_cli.py batch F:/Vehicle_Date --type slope --skip-existing
    """
    vehicle_ids = _discover_vehicles(target_dir)
    if not vehicle_ids:
        raise click.ClickException(
            f"在 {target_dir} 下未检测到车辆文件夹"
        )

    click.echo(f"检测到 {len(vehicle_ids)} 个车辆: {', '.join(vehicle_ids)}")
    click.echo("-" * 40)

    total_generated = 0
    for vid in vehicle_ids:
        click.echo(f"\n[{vid}] 开始处理...")
        try:
            count = _generate_reports(
                vid, report_type, component, target_dir, template,
                skip_existing=skip_existing
            )
            total_generated += count
        except click.ClickException as e:
            click.echo(f"  跳过: {e.message}")
        except Exception as e:
            click.echo(f"  错误: {e}")

    click.echo("\n" + "=" * 40)
    click.echo(f"批量处理完成，共生成 {total_generated} 份报告。")


def _discover_vehicles(target_dir: str) -> list[str]:
    """扫描目标路径，发现车辆文件夹.

    匹配格式：V 开头，后跟数字的文件夹名（如 V0001、V0002）
    """
    if not os.path.isdir(target_dir):
        raise click.ClickException(f"路径不存在: {target_dir}")

    pattern = re.compile(r"^V\d+$", re.IGNORECASE)
    vehicles = []
    for name in sorted(os.listdir(target_dir)):
        full_path = os.path.join(target_dir, name)
        if os.path.isdir(full_path) and pattern.match(name):
            vehicles.append(name)

    return vehicles


def _generate_reports(
    vehicle_id: str,
    report_type: str,
    component: str | None,
    base_dir: str,
    template: str,
    skip_existing: bool = False,
) -> int:
    """生成报告的核心逻辑，返回生成的报告数量."""
    generated = 0

    if report_type in ("ripple", "all"):
        components = _get_components(
            vehicle_id, base_dir, "ripple", component
        )
        for comp in components:
            output_dir = os.path.join(
                base_dir,
                vehicle_id,
                f"{vehicle_id}_RIPPLE",
                f"{vehicle_id}_RIPPLE_output",
            )
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"{vehicle_id}_RIPPLE_REPORT_{comp}.docx",
            )
            if skip_existing and os.path.exists(output_path):
                click.echo(f"  纹波报告已存在，跳过: {comp}")
                continue
            click.echo(f"  生成纹波报告: {comp} ...")
            generate_ripple_report(
                vehicle_id, comp, base_dir, template, output_path
            )
            generated += 1
            click.echo(f"    -> {output_path}")

    if report_type in ("slope", "all"):
        components = _get_components(
            vehicle_id, base_dir, "slope", component
        )
        for comp in components:
            output_dir = os.path.join(
                base_dir,
                vehicle_id,
                f"{vehicle_id}_SLOPE",
                f"{vehicle_id}_SLOPE_output",
            )
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"{vehicle_id}_SLOPE_REPORT_{comp}.docx",
            )
            if skip_existing and os.path.exists(output_path):
                click.echo(f"  斜率报告已存在，跳过: {comp}")
                continue
            click.echo(f"  生成斜率报告: {comp} ...")
            generate_slope_report(
                vehicle_id, comp, base_dir, template, output_path
            )
            generated += 1
            click.echo(f"    -> {output_path}")

    return generated


def _get_components(vehicle_id, base_dir, data_type, specified_component):
    """获取组件通道列表."""
    if specified_component:
        return [specified_component]

    if data_type == "ripple":
        comps = detect_ripple_components(vehicle_id, base_dir)
    else:
        comps = detect_slope_components(vehicle_id, base_dir)

    if not comps:
        raise click.ClickException(
            f"未检测到 {vehicle_id} 的{data_type}组件通道"
        )
    return comps


if __name__ == "__main__":
    cli()
