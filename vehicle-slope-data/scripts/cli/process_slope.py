#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆斜率数据处理 - 命令行入口
支持单车辆处理和批量处理

使用方法:
    # 处理单个车辆（推荐格式: {VehID}_SLOPE）
    python cli/process_slope.py process --folder V0001_SLOPE

    # 验证后处理
    python cli/process_slope.py process --folder V0001_SLOPE --validate-first

    # 只生成特定格式
    python cli/process_slope.py process --folder V0001_SLOPE --format json,excel

    # 批量处理（显式列表）
    python cli/process_slope.py batch V0001_SLOPE V0002_SLOPE V0003_SLOPE

    # 批量处理（自动扫描父目录）
    python cli/process_slope.py batch --scan E:/Vehicle_Date

    # 批量处理带进度条
    python cli/process_slope.py batch --scan E:/Vehicle_Date --progress
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path (vehicle-slope-data/)
# __file__ is at .../scripts/cli/process_slope.py
# parent.parent.parent = project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.slope_processor import SlopeDataProcessor
from scripts.validate_slope import SlopeValidator
from scripts.generate_error_report_cn import generate_error_report_cn
from scripts.version_utils import get_slope_version


# Lazy version loading
_VERSION: Optional[str] = None


def get_version() -> str:
    """Lazy-load version"""
    global _VERSION
    if _VERSION is None:
        _VERSION = get_slope_version()
    return _VERSION


def print_banner():
    """打印CLI横幅"""
    version = get_version()
    try:
        banner = f"""
+==============================================================+
|        Vehicle Slope Data CLI / 车辆斜率数据处理工具          |
|                     Version {version:<10}                  |
+==============================================================+
        """
        print(banner)
    except UnicodeEncodeError:
        print("=" * 60)
        print(f"  Vehicle Slope Data CLI v{version}")
        print("=" * 60)


def show_progress(current: int, total: int, message: str = ""):
    """显示进度条"""
    if total == 0:
        return
    percent = int(100 * current / total)
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = '=' * filled + '-' * (bar_length - filled)
    sys.stdout.write('\r')
    sys.stdout.write(f'[{bar}] {percent:3d}% {message}')
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write('\n')
        sys.stdout.flush()


def scan_parent_folder(parent_folder: Path) -> List[Path]:
    """扫描父目录自动发现 SLOPE 车辆文件夹"""
    vehicles = []

    if not parent_folder.exists():
        print(f"错误: 文件夹不存在 - {parent_folder}")
        return vehicles

    if not parent_folder.is_dir():
        print(f"错误: 路径不是文件夹 - {parent_folder}")
        return vehicles

    # Check if parent itself is a SLOPE folder
    if parent_folder.name.endswith('_SLOPE'):
        vehicles.append(parent_folder)
        print(f"  发现车辆: {parent_folder.name}")
        return vehicles

    print(f"\n扫描中: {parent_folder}\n")

    for item in sorted(parent_folder.iterdir()):
        if not item.is_dir():
            continue
        # Check for SLOPE subfolder or direct SLOPE folder
        if item.name.endswith('_SLOPE'):
            vehicles.append(item)
            print(f"  [发现] {item.name}")
        else:
            slope_sub = item / f"{item.name}_SLOPE"
            if slope_sub.exists():
                vehicles.append(slope_sub)
                print(f"  [发现] {item.name} -> {slope_sub.name}")

    return vehicles


def validate_format(fmt_str: str) -> List[str]:
    """验证并解析格式选项"""
    valid_formats = {'all', 'json', 'excel', 'sqlite'}
    formats = [f.strip() for f in fmt_str.split(',')]
    invalid = set(formats) - valid_formats
    if invalid:
        print(f"警告: 未知格式选项: {', '.join(invalid)}")
    return formats


def safe_get_vehicle_model(data: Dict[str, Any]) -> str:
    """安全获取车型名称

    C8 v1.6 hotfix: 兼容中文键(车型)和英文键(vehicle_model),
    旧代码只查中文键导致 vehicle_info_formatter 输出英文键时显示 Unknown.
    """
    vehicle = data.get('vehicle', {})
    if isinstance(vehicle, dict):
        info = vehicle.get('vehicle_info', {})
        if isinstance(info, dict):
            return (
                info.get('车型')
                or info.get('vehicle_model')
                or info.get('vehicle_id')
                or 'Unknown'
            )
    return 'Unknown'


def process_single_vehicle(vehicle_folder: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """处理单个车辆，返回结果字典"""
    result = {
        'vehicle_id': '',
        'success': False,
        'duration': 0,
        'components': 0,
        'conditions': 0,
        'error': None,
        'output_dir': None
    }

    start_time = time.time()

    # 验证文件夹存在
    if not vehicle_folder.exists():
        result['error'] = f"文件夹不存在 - {vehicle_folder}"
        return result

    # 提取 vehicle_id
    folder_name = vehicle_folder.name
    vehicle_id = folder_name[:-6] if folder_name.endswith('_SLOPE') else folder_name
    result['vehicle_id'] = vehicle_id

    print(f"\n{'-'*60}")
    print(f"处理车辆: {vehicle_id}")
    print(f"文件夹: {vehicle_folder.absolute()}")
    print(f"{'-'*60}")

    try:
        # 步骤1: 验证（如果启用）
        if args.validate_first:
            print("[步骤1/3] 验证数据完整性...")
            validator = SlopeValidator(str(vehicle_folder), verbose=args.verbose)
            validation_result = validator.validate_all()
            # Handle both 4-tuple and single-object returns
            if isinstance(validation_result, tuple):
                passed, issues, warnings, infos = validation_result
            else:
                passed = getattr(validation_result, 'passed', True)
                issues = getattr(validation_result, 'issues', [])
                warnings = getattr(validation_result, 'warnings', [])

            if not passed:
                print("\n验证失败，请修复以下错误:")
                for issue in issues:
                    msg = issue['message'] if isinstance(issue, dict) else str(issue)
                    print(f"  - {msg}")
                result['error'] = f"验证失败: {len(issues)} 个错误"
                return result

            if warnings:
                print(f"\n  {len(warnings)}个警告（处理将继续）")

            print("[OK] 验证通过\n")

        # 步骤2: 处理数据
        print("[步骤2/3] 处理车辆数据...")

        # 解析格式选项
        formats = validate_format(args.format)

        config = {
            'generate_json': 'all' in formats or 'json' in formats,
            'generate_excel': 'all' in formats or 'excel' in formats,
            'generate_sqlite': 'all' in formats or 'sqlite' in formats,
            'output_dir': getattr(args, 'output_dir', None)
        }

        # 执行处理
        processor = SlopeDataProcessor(str(vehicle_folder), config)
        data = processor.process()

        result['components'] = len(data['components'])
        result['conditions'] = data['metadata']['total_conditions']
        result['output_dir'] = str(processor.output_dir)

        # 显示结果摘要
        print("\n处理完成!")
        vehicle_model = safe_get_vehicle_model(data)
        print(f"车型: {vehicle_model}")
        print(f"组件数: {result['components']}")
        print(f"工况数: {result['conditions']}")

        # 步骤3: 生成错误报告
        print("\n[步骤3/3] 生成处理报告...")

        # C8 v1.6 hotfix: details 改为显示实际参数数(原先硬编码'已完成'),
        # 与 ripple 流程对齐(显示 "260个参数")便于调试 vehicle_info 加载状态
        vehicle_info_count = len(processor.vehicle_info) if hasattr(processor, 'vehicle_info') else 0
        completed_functions = [
            {'name': '车辆信息加载', 'success': True,
             'details': f'{vehicle_info_count}个参数' if vehicle_info_count else '已完成'},
            {'name': '测试命名规则加载', 'success': True, 'details': f"{len(processor.test_rules)}个工况"},
            {'name': '传感器命名规则加载', 'success': True, 'details': f"{len(processor.sensor_rules)}个通道"},
            {'name': '组件数据处理', 'success': True, 'details': f"{result['components']}个组件"},
        ]

        generated_files = []
        if config['generate_json']:
            generated_files.append({
                'name': f"{vehicle_id}_SLOPE_data.json",
                'type': 'JSON',
                'description': '结构化数据导出'
            })
        if config['generate_excel']:
            generated_files.append({
                'name': f"{vehicle_id}_SLOPE_summary.xlsx",
                'type': 'Excel',
                'description': 'V1.0格式报告，包含3个工作表'
            })
        if config['generate_sqlite']:
            generated_files.append({
                'name': f"{vehicle_id}_SLOPE.db",
                'type': 'SQLite',
                'description': '数据库，包含4个表'
            })

        processing_stats = {
            'total_components': result['components'],
            'processed_components': result['components'],
            'total_conditions': result['conditions']
        }

        # Convert warnings to dict format expected by report generator
        raw_warnings = data['metadata'].get('warnings', [])
        formatted_warnings = []
        for w in raw_warnings:
            if isinstance(w, dict):
                formatted_warnings.append(w)
            else:
                formatted_warnings.append({'type': 'warning', 'message': str(w), 'component': ''})

        generate_error_report_cn(
            vehicle_folder=str(vehicle_folder),
            vehicle_id=vehicle_id,
            vehicle_model=vehicle_model,
            processing_status=True,
            completed_functions=completed_functions,
            generated_files=generated_files,
            errors=[],
            warnings=formatted_warnings,
            processing_stats=processing_stats,
            output_folder=str(processor.output_dir)
        )

        print("[OK] 处理报告生成完成")

        # C9 v1.6 hotfix: 自动触发跨阶段一致性校验(slope)
        # 旧流程仅 vehicle_skills_cli.py 调用 validator,而本 CLI 单独跑时会覆盖
        # error_report 导致 <!-- cross-format-validation --> 块丢失。
        # 这里在生成 error_report 后再追加 validation 块,确保两条调用路径都有.
        try:
            ripple_scripts = Path(__file__).resolve().parents[3] / 'vehicle-ripple-data' / 'scripts'
            if str(ripple_scripts) not in sys.path:
                sys.path.insert(0, str(ripple_scripts))
            from validate_cross_format import CrossFormatValidator
            validator = CrossFormatValidator(vehicle_id, processor.output_dir, data_type="slope")
            validator.validate_and_report()
        except Exception as e:
            # 校验失败不阻断主流程(规划书 §4.1 兼容策略)
            print(f"  [WARN] 跨阶段校验器调用失败: {e}")

        result['success'] = True

    except KeyboardInterrupt:
        print("\n\n处理被用户中断")
        result['error'] = "用户中断"
        result['duration'] = time.time() - start_time
        raise  # Re-raise to stop batch processing
    except Exception as e:
        print(f"\n处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        result['error'] = str(e)

    result['duration'] = time.time() - start_time
    return result


def print_batch_summary(results: List[Dict[str, Any]]):
    """打印批量处理汇总"""
    total = len(results)
    success_count = sum(1 for r in results if r['success'])
    failed_count = total - success_count
    total_duration = sum(r['duration'] for r in results)
    total_conditions = sum(r['conditions'] for r in results)

    print(f"\n{'='*60}")
    print(f"批量处理汇总")
    print(f"{'='*60}")
    print(f"总计: {total} 辆车")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"总耗时: {total_duration:.2f} 秒")
    print(f"总工况数: {total_conditions}")
    print(f"{'='*60}\n")

    # Per-vehicle table
    print("各车辆结果:")
    print(f"{'车辆ID':<15} {'状态':<8} {'组件数':<8} {'工况数':<8} {'耗时(s)':<10} {'输出目录'}")
    print("-" * 80)

    for r in results:
        status = "OK" if r['success'] else "FAIL"
        comp_str = str(r['components']) if r['success'] else "-"
        cond_str = str(r['conditions']) if r['success'] else "-"
        out_dir = str(r.get('output_dir') or '-') if r['success'] else str(r.get('error') or '-')
        print(f"{r['vehicle_id']:<15} {status:<8} {comp_str:<8} {cond_str:<8} {r['duration']:<10.2f} {out_dir}")

    print(f"\n{'='*60}")


def main():
    """主函数"""
    version = get_version()
    parser = argparse.ArgumentParser(
        prog='vehicle-slope',
        description=f'''
车辆电压斜率数据处理工具 - 支持单车辆和批量处理 v{version}

处理车辆电压斜率测试数据，生成JSON、Excel和SQLite报告。
支持 {{VehicleID}}_SLOPE 文件夹命名格式。

示例:
  # 处理单个车辆
  %(prog)s process --folder V0001_SLOPE
  %(prog)s process --folder V0001_SLOPE --validate-first

  # 批量处理（显式列表）
  %(prog)s batch V0001_SLOPE V0002_SLOPE

  # 批量处理（自动扫描）
  %(prog)s batch --scan E:/Vehicle_Date
  %(prog)s batch --scan E:/Vehicle_Date --progress
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # --- Process command ---
    process_parser = subparsers.add_parser(
        'process',
        help='处理单个车辆',
        description='处理单个车辆的斜率数据'
    )
    process_parser.add_argument(
        '--folder', '-f',
        required=True,
        help='车辆文件夹路径（支持{VehID}_SLOPE或{VehID}格式）'
    )
    process_parser.add_argument(
        '--validate-first', '-v',
        action='store_true',
        help='处理前先验证数据完整性（推荐）'
    )
    process_parser.add_argument(
        '--format', '-fmt',
        default='all',
        help='输出格式: all, json, excel, sqlite（逗号分隔多个）'
    )
    process_parser.add_argument(
        '--output-dir', '-o',
        help='输出目录（默认: vehicle_folder/{VehicleID}_SLOPE_output）'
    )
    process_parser.add_argument(
        '--verbose', '-V',
        action='store_true',
        help='显示详细日志'
    )

    # --- Batch command ---
    batch_parser = subparsers.add_parser(
        'batch',
        help='批量处理多个车辆',
        description='批量处理多个车辆的斜率数据。支持显式列表或自动扫描。'
    )
    batch_parser.add_argument(
        'folders',
        nargs='*',
        type=str,
        help='车辆文件夹路径列表（使用--scan时可省略）'
    )
    batch_parser.add_argument(
        '--scan', '-s',
        type=str,
        metavar='PARENT_FOLDER',
        help='自动扫描父目录下的所有 SLOPE 车辆文件夹'
    )
    batch_parser.add_argument(
        '--validate-first', '-v',
        action='store_true',
        help='处理前先验证数据完整性'
    )
    batch_parser.add_argument(
        '--format', '-fmt',
        default='all',
        help='输出格式: all, json, excel, sqlite（逗号分隔多个）'
    )
    batch_parser.add_argument(
        '--progress', '-p',
        action='store_true',
        help='显示进度条'
    )
    batch_parser.add_argument(
        '--verbose', '-V',
        action='store_true',
        help='显示详细日志'
    )

    # --- Version ---
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {version}'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == 'process':
        print_banner()
        folder = Path(args.folder)
        result = process_single_vehicle(folder, args)

        if result['success']:
            print(f"\n处理完成! 耗时: {result['duration']:.2f} 秒")
            return 0
        else:
            print(f"\n处理失败: {result['error']}")
            return 1

    elif args.command == 'batch':
        print_banner()

        # Determine folders
        folders = []
        if args.scan:
            folders = scan_parent_folder(Path(args.scan))
            if not folders:
                print(f"\n未找到 SLOPE 车辆文件夹: {args.scan}")
                return 1
        elif args.folders:
            folders = [Path(f) for f in args.folders]
        else:
            print("错误: 必须提供文件夹列表或使用 --scan 选项")
            print("用法:")
            print("  %(prog)s batch V0001_SLOPE V0002_SLOPE")
            print("  %(prog)s batch --scan E:/Vehicle_Date")
            return 1

        # Deduplicate
        seen = set()
        unique_folders = []
        for folder in folders:
            resolved = folder.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique_folders.append(folder)
        folders = unique_folders

        print(f"\n批量处理 {len(folders)} 辆车\n")

        results = []
        try:
            for i, folder in enumerate(folders, 1):
                if args.progress:
                    print(f"\n[{i}/{len(folders)}] 开始处理...")

                result = process_single_vehicle(folder, args)
                results.append(result)

                if args.progress:
                    show_progress(i, len(folders), f"已完成 {i}/{len(folders)} 辆车")
        except KeyboardInterrupt:
            print("\n\n批量处理被用户中断")
        finally:
            # Always print summary, even on interrupt
            if results:
                print_batch_summary(results)

        success_count = sum(1 for r in results if r['success'])
        if success_count == len(results) and len(results) > 0:
            print("\n所有车辆处理成功!")
            return 0
        else:
            print(f"\n  {len(results) - success_count} 辆车处理失败")
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
