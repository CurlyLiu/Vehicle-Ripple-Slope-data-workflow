#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vehicle Skills Unified CLI Tool / 车辆技能统一命令行工具

Unified command-line interface for processing vehicle ripple and slope data.
支持处理车辆纹波和斜率数据的统一命令行接口。

Usage / 使用方式:
    python vehicle_skills_cli.py process <vehicle_folder> [options]
    python vehicle_skills_cli.py batch <folder1> <folder2> ... [options]
    python vehicle_skills_cli.py batch --scan <parent_folder> [options]
    python vehicle_skills_cli.py validate <vehicle_folder>
    python vehicle_skills_cli.py version

Examples / 示例:
    # Process single vehicle / 处理单个车辆
    python vehicle_skills_cli.py process E:/Vehicle_Date/V0001

    # Process with progress bar / 带进度条处理
    python vehicle_skills_cli.py process E:/Vehicle_Date/V0001 --progress

    # Batch processing (explicit list) / 批量处理（显式列表）
    python vehicle_skills_cli.py batch E:/Vehicle_Date/V0001 E:/Vehicle_Date/V0002

    # Batch processing (auto-scan) / 批量处理（自动扫描）
    python vehicle_skills_cli.py batch --scan E:/Vehicle_Date

    # Validate data only / 仅验证数据
    python vehicle_skills_cli.py validate E:/Vehicle_Date/V0001
"""

import sys
import argparse
import importlib.util
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import time
import subprocess

# Fix Windows terminal encoding for Unicode output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Skill root directories
# __file__ is at .../scripts/cli/vehicle_skills_cli.py
# parent.parent.parent = skill root (vehicle-ripple-data)
_RIPPLE_SKILL_ROOT = Path(__file__).parent.parent.parent
_SLOPE_SKILL_ROOT = _RIPPLE_SKILL_ROOT.parent / 'vehicle-slope-data'

# Stage 3 report generation skill root
_REPORT_SKILL_ROOT = _RIPPLE_SKILL_ROOT.parent / 'vehicle-report-generation'
_REPORT_CLI_PATH = _REPORT_SKILL_ROOT / 'vehicle_report_cli.py'
_REPORT_GENERATION_TIMEOUT = 300  # 5 minutes timeout


# ---------------------------------------------------------------------------
# Dynamic module loading helpers (avoid 'scripts' package name collision)
# ---------------------------------------------------------------------------

_RIPPLE_VP_PATH = _RIPPLE_SKILL_ROOT / 'scripts' / 'core' / 'vehicle_processor.py'
_SLOPE_SP_PATH = _SLOPE_SKILL_ROOT / 'scripts' / 'slope_processor.py'


def _load_vehicle_processor():
    """Load VehicleDataProcessor directly from file to avoid package conflicts."""
    # Ensure dependencies are findable: scripts/core/ for condition_matcher,
    # skill root for config module
    ripple_core = str(_RIPPLE_SKILL_ROOT / 'scripts' / 'core')
    ripple_root = str(_RIPPLE_SKILL_ROOT)
    if ripple_core not in sys.path:
        sys.path.insert(0, ripple_core)
    if ripple_root not in sys.path:
        sys.path.insert(0, ripple_root)

    spec = importlib.util.spec_from_file_location(
        '_ripple_vehicle_processor', str(_RIPPLE_VP_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VehicleDataProcessor


def _load_slope_processor():
    """Load SlopeDataProcessor directly from file to avoid package conflicts."""
    # Slope processor needs condition_matcher from ripple-data and config from slope-data
    ripple_core = str(_RIPPLE_SKILL_ROOT / 'scripts' / 'core')
    slope_root = str(_SLOPE_SKILL_ROOT)
    slope_scripts = str(_SLOPE_SKILL_ROOT / 'scripts')
    if ripple_core not in sys.path:
        sys.path.insert(0, ripple_core)
    if slope_root not in sys.path:
        sys.path.insert(0, slope_root)
    if slope_scripts not in sys.path:
        sys.path.insert(0, slope_scripts)

    spec = importlib.util.spec_from_file_location(
        '_slope_processor', str(_SLOPE_SP_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SlopeDataProcessor


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def print_banner():
    """Print CLI banner / 打印CLI横幅"""
    try:
        banner = """
+==============================================================+
|           Vehicle Skills CLI / 车辆技能命令行工具             |
|                     Version 1.1.0                            |
+==============================================================+
        """
        print(banner)
    except UnicodeEncodeError:
        print("=" * 60)
        print("  Vehicle Skills CLI v1.1.0")
        print("=" * 60)


def get_skill_version(skill_name: str) -> str:
    """Get skill version from SKILL.md / 从SKILL.md获取技能版本"""
    try:
        skill_path = Path(__file__).parent.parent.parent
        if skill_name == 'slope':
            skill_path = skill_path.parent / 'vehicle-slope-data'

        skill_md = skill_path / 'SKILL.md'
        if skill_md.exists():
            with open(skill_md, 'r', encoding='utf-8') as f:
                for line in f:
                    # Look for frontmatter version field like: version: "4.2"
                    match = re.search(r'^version:\s*"?(\d+\.\d+(?:\.\d+)?)"?', line.strip())
                    if match:
                        return match.group(1)
    except Exception:
        pass
    return "Unknown"


def show_progress(current: int, total: int, message: str = ""):
    """Show progress bar / 显示进度条

    Args:
        current: Current progress / 当前进度
        total: Total items / 总数
        message: Current processing message / 当前处理信息
    """
    if total == 0:
        return

    percent = int(100 * current / total)
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = '=' * filled + '-' * (bar_length - filled)

    # Clear line and print progress
    sys.stdout.write('\r')
    sys.stdout.write(f'[{bar}] {percent:3d}% {message}')
    sys.stdout.flush()

    if current >= total:
        sys.stdout.write('\n')
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Folder discovery & validation
# ---------------------------------------------------------------------------

def scan_parent_folder(parent_folder: Path) -> List[Path]:
    """Scan parent folder to auto-discover vehicle folders / 扫描父目录自动发现车辆文件夹

    自动查找包含纹波(RIPPLE)或斜率(SLOPE)数据的车辆文件夹

    Returns:
        List of vehicle folder paths / 车辆文件夹路径列表
    """
    vehicles = []

    if not parent_folder.exists():
        print(f"Error / 错误: Folder not found / 文件夹不存在: {parent_folder}")
        return vehicles

    if not parent_folder.is_dir():
        print(f"Error / 错误: Path is not a directory / 路径不是文件夹: {parent_folder}")
        return vehicles

    # Check if parent folder itself is a vehicle folder
    has_ripple = (parent_folder / f"{parent_folder.name}_RIPPLE").exists()
    has_slope = (parent_folder / f"{parent_folder.name}_SLOPE").exists()

    if has_ripple or has_slope:
        vehicles.append(parent_folder)
        print(f"  Found vehicle / 发现车辆: {parent_folder.name}")
        return vehicles

    # Scan subdirectories / 扫描子目录
    print(f"\nScanning / 扫描中: {parent_folder}\n")

    for item in sorted(parent_folder.iterdir()):
        if not item.is_dir():
            continue

        # Check for RIPPLE or SLOPE subfolders
        has_ripple = (item / f"{item.name}_RIPPLE").exists()
        has_slope = (item / f"{item.name}_SLOPE").exists()

        if has_ripple or has_slope:
            vehicles.append(item)
            print(f"  [FOUND] {item.name} (RIPPLE: {'Yes' if has_ripple else 'No'}, SLOPE: {'Yes' if has_slope else 'No'})")

    return vehicles


def validate_vehicle_folder(folder: Path) -> Dict[str, Any]:
    """Validate vehicle folder structure / 验证车辆文件夹结构

    Returns:
        Dict with validation results / 包含验证结果的字典
    """
    results = {
        'valid': False,
        'has_ripple': False,
        'has_slope': False,
        'ripple_components': 0,
        'slope_components': 0,
        'errors': [],
        'warnings': []
    }

    if not folder.exists():
        results['errors'].append(f"Folder not found / 文件夹不存在: {folder}")
        return results

    if not folder.is_dir():
        results['errors'].append(f"Path is not a directory / 路径不是文件夹: {folder}")
        return results

    # Check for RIPPLE data / 检查纹波数据
    ripple_folder = folder / f"{folder.name}_RIPPLE"
    if ripple_folder.exists():
        results['has_ripple'] = True
        # Count components / 统计组件
        for item in ripple_folder.iterdir():
            if item.is_dir() and not item.name.endswith('_output'):
                results['ripple_components'] += 1

    # Check for SLOPE data / 检查斜率数据
    slope_folder = folder / f"{folder.name}_SLOPE"
    if slope_folder.exists():
        results['has_slope'] = True
        # Count components / 统计组件
        for item in slope_folder.iterdir():
            if item.is_dir() and not item.name.endswith('_output'):
                results['slope_components'] += 1

    # Validate results / 验证结果
    if not results['has_ripple'] and not results['has_slope']:
        results['errors'].append("No RIPPLE or SLOPE data found / 未找到纹波或斜率数据")
    else:
        results['valid'] = True
        if results['has_ripple'] and results['ripple_components'] == 0:
            results['warnings'].append("RIPPLE folder exists but no components found / 纹波文件夹存在但无组件")
        if results['has_slope'] and results['slope_components'] == 0:
            results['warnings'].append("SLOPE folder exists but no components found / 斜率文件夹存在但无组件")

    return results


def _auto_generate_reports(vehicle_id: str, vehicle_folder: Path,
                           has_ripple: bool, has_slope: bool) -> Dict[str, Any]:
    """Auto-trigger Stage 3 report generation via subprocess.

    Non-blocking: failures are logged but not raised.

    Returns:
        Dict with keys: 'triggered', 'ripple_ok', 'slope_ok', 'error'
    """
    result = {
        'triggered': False,
        'ripple_ok': False,
        'slope_ok': False,
        'error': None
    }

    if not _REPORT_CLI_PATH.exists():
        result['error'] = f"Report CLI not found: {_REPORT_CLI_PATH}"
        print(f"  [WARN] {result['error']}")
        return result

    base_dir = str(vehicle_folder.parent)

    report_types = []
    if has_ripple:
        report_types.append('ripple')
    if has_slope:
        report_types.append('slope')

    if not report_types:
        result['error'] = "No ripple or slope data available for report generation"
        return result

    for rtype in report_types:
        try:
            cmd = [
                sys.executable,
                str(_REPORT_CLI_PATH),
                'generate',
                vehicle_id,
                '--type', rtype,
                '--base-dir', base_dir,
            ]

            print(f"  [AUTO] Generating {rtype.upper()} report for {vehicle_id}...")

            proc = subprocess.run(
                cmd,
                cwd=str(_REPORT_SKILL_ROOT),
                capture_output=True,
                text=True,
                timeout=_REPORT_GENERATION_TIMEOUT,
                encoding='utf-8',
                errors='replace'
            )

            if proc.returncode == 0:
                print(f"  [OK] {rtype.upper()} report generated")
                result[f'{rtype}_ok'] = True
            else:
                stderr = proc.stderr.strip() if proc.stderr else "unknown error"
                print(f"  [WARN] {rtype.upper()} report generation failed: {stderr}")

        except subprocess.TimeoutExpired:
            print(f"  [WARN] {rtype.upper()} report generation timed out "
                  f"after {_REPORT_GENERATION_TIMEOUT}s")
        except Exception as e:
            print(f"  [WARN] {rtype.upper()} report generation error: {e}")

    result['triggered'] = True

    # If all report types failed, record an error for summary stats
    if report_types and not any(result[f'{rt}_ok'] for rt in report_types):
        result['error'] = "All report generation attempts failed"

    return result


_DATABASE_CLI_PATH = _RIPPLE_SKILL_ROOT.parent / 'vehicle-database' / 'vehicle_database.py'
_DATABASE_IMPORT_TIMEOUT = 300  # 5 minutes

def _auto_import_database(vehicle_id: str, base_dir: str) -> Dict[str, Any]:
    """Auto-trigger Stage 4 database import via subprocess.

    Non-blocking: failures are logged but not raised.

    Returns:
        Dict with keys: 'triggered', 'success', 'error'
    """
    result = {'triggered': False, 'success': False, 'error': None}

    if not _DATABASE_CLI_PATH.exists():
        result['error'] = f"Database CLI not found: {_DATABASE_CLI_PATH}"
        print(f"  [WARN] {result['error']}")
        return result

    try:
        cmd = [
            sys.executable, str(_DATABASE_CLI_PATH),
            '-s', base_dir, 'add', vehicle_id
        ]
        print(f"  [HOOK] Auto-triggering Stage 4: Database Import for {vehicle_id}")

        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=_DATABASE_IMPORT_TIMEOUT,
            encoding='utf-8', errors='replace'
        )

        if proc.returncode == 0:
            print(f"  [OK] Database import completed")
            result['success'] = True
        else:
            stderr = proc.stderr.strip() if proc.stderr else "unknown error"
            print(f"  [WARN] Database import failed: {stderr}")
            result['error'] = stderr
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Database import timed out after {_DATABASE_IMPORT_TIMEOUT}s")
    except Exception as e:
        print(f"  [WARN] Database import error: {e}")
        result['error'] = str(e)

    result['triggered'] = True
    return result


def _format_task_result(task_result: Any) -> str:
    """Format a task result for display in summary table"""
    if task_result is None:
        return "-"
    if isinstance(task_result, dict):
        if 'error' in task_result:
            return "ERROR"
        if 'conditions' in task_result:
            return str(task_result['conditions'])
        return "OK"
    return "ERROR"


# ---------------------------------------------------------------------------
# Single-vehicle processing
# ---------------------------------------------------------------------------

def process_vehicle(vehicle_folder: Path, progress: bool = False,
                   output_dir: Optional[Path] = None,
                   auto_report: bool = False,
                   auto_db: bool = True) -> Dict[str, Any]:
    """Process single vehicle / 处理单个车辆

    Args:
        vehicle_folder: Path to vehicle folder / 车辆文件夹路径
        progress: Show progress bar / 是否显示进度条
        output_dir: Custom output directory / 自定义输出目录
        auto_report: Auto-generate Word reports / 自动生成Word报告
        auto_db: Auto-import to unified database / 自动导入统一数据库

    Returns:
        Processing results / 处理结果
    """
    results = {
        'vehicle_id': vehicle_folder.name,
        'ripple': None,
        'slope': None,
        'success': False,
        'duration': 0,
        'report_generation': None,
        'database_import': None
    }

    start_time = time.time()

    # Validate first / 首先验证
    validation = validate_vehicle_folder(vehicle_folder)
    if not validation['valid']:
        print(f"Error / 错误: {validation['errors'][0]}")
        return results

    print(f"\nProcessing / 正在处理: {vehicle_folder.name}")
    print(f"  RIPPLE: {'Yes' if validation['has_ripple'] else 'No'} "
          f"({validation['ripple_components']} components / 个组件)")
    print(f"  SLOPE:  {'Yes' if validation['has_slope'] else 'No'} "
          f"({validation['slope_components']} components / 个组件)")

    tasks = []
    if validation['has_ripple']:
        tasks.append('ripple')
    if validation['has_slope']:
        tasks.append('slope')

    if progress:
        print(f"\nStarting processing... / 开始处理...")

    # Process RIPPLE / 处理纹波
    if 'ripple' in tasks:
        try:
            if progress:
                print(f"\n[1/{len(tasks)}] Processing RIPPLE data... / 处理纹波数据...")

            VehicleDataProcessor = _load_vehicle_processor()

            ripple_folder = vehicle_folder / f"{vehicle_folder.name}_RIPPLE"
            processor = VehicleDataProcessor(str(ripple_folder))

            result = processor.process()
            results['ripple'] = {
                'components': len(result['components']),
                'conditions': sum(len(c['conditions']) for c in result['components'].values()),
                'output': str(processor.output_dir)
            }
            print(f"  [OK] RIPPLE completed / 纹波处理完成")

        except Exception as e:
            print(f"  [FAIL] RIPPLE failed / 纹波处理失败: {e}")
            results['ripple'] = {'error': str(e)}

    # Process SLOPE / 处理斜率
    if 'slope' in tasks:
        try:
            if progress:
                print(f"\n[{tasks.index('slope')+1}/{len(tasks)}] Processing SLOPE data... / 处理斜率数据...")

            SlopeDataProcessor = _load_slope_processor()

            slope_folder = vehicle_folder / f"{vehicle_folder.name}_SLOPE"
            processor = SlopeDataProcessor(str(slope_folder))

            result = processor.process()
            results['slope'] = {
                'components': len(result['components']),
                'conditions': sum(len(c['conditions']) for c in result['components'].values()),
                'output': str(processor.output_dir)
            }
            print(f"  [OK] SLOPE completed / 斜率处理完成")

        except Exception as e:
            print(f"  [FAIL] SLOPE failed / 斜率处理失败: {e}")
            results['slope'] = {'error': str(e)}

    results['duration'] = time.time() - start_time

    # Success = ALL expected tasks succeeded (not just any one)
    expected_tasks = []
    if validation['has_ripple']:
        expected_tasks.append('ripple')
    if validation['has_slope']:
        expected_tasks.append('slope')

    actual_successes = []
    for task in expected_tasks:
        task_result = results.get(task)
        if task_result is not None and isinstance(task_result, dict) and 'error' not in task_result:
            actual_successes.append(task)

    results['success'] = len(actual_successes) == len(expected_tasks) and len(expected_tasks) > 0

    # 跨阶段数据一致性校验 (兼容策略: 不阻断后续流程)
    if results['success']:
        try:
            scripts_dir = str(_RIPPLE_SKILL_ROOT / 'scripts')
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from validate_cross_format import CrossFormatValidator

            vehicle_id = vehicle_folder.name
            ripple_output = vehicle_folder / f"{vehicle_id}_RIPPLE" / f"{vehicle_id}_RIPPLE_output"
            if ripple_output.exists():
                validator = CrossFormatValidator(vehicle_id, ripple_output, data_type="ripple")
                validator.validate_and_report()

            slope_output = vehicle_folder / f"{vehicle_id}_SLOPE" / f"{vehicle_id}_SLOPE_output"
            if slope_output.exists():
                validator = CrossFormatValidator(vehicle_id, slope_output, data_type="slope")
                validator.validate_and_report()
        except Exception as e:
            print(f"  [WARN] 跨阶段校验器调用失败: {e}")

    # ===== HOOK: Auto-trigger Stage 3 report generation =====
    if auto_report and results['success']:
        print(f"\n  [HOOK] Stage 2.5 complete → Auto-triggering Stage 3: Report Generation")
        results['report_generation'] = _auto_generate_reports(
            vehicle_folder.name,
            vehicle_folder,
            validation['has_ripple'],
            validation['has_slope']
        )

    # ===== HOOK: Auto-trigger Stage 4 database import =====
    if auto_db and results['success']:
        base_dir = str(vehicle_folder.parent)
        results['database_import'] = _auto_import_database(
            vehicle_folder.name, base_dir
        )

    return results


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def batch_process(folders: List[Path], progress: bool = False,
                 auto_report: bool = False,
                 auto_db: bool = True) -> List[Dict[str, Any]]:
    """Batch process multiple vehicles / 批量处理多个车辆

    Args:
        folders: List of vehicle folders / 车辆文件夹列表
        progress: Show progress bar / 是否显示进度条

    Returns:
        List of processing results / 处理结果列表
    """
    # Deduplicate by resolved path
    seen = set()
    unique_folders = []
    for folder in folders:
        resolved = folder.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_folders.append(folder)

    folders = unique_folders
    results = []
    total = len(folders)

    print(f"\n{'='*60}")
    print(f"Batch Processing / 批量处理")
    print(f"{'='*60}")
    print(f"Total vehicles / 总车辆数: {total}\n")

    for i, folder in enumerate(folders, 1):
        print(f"\n{'-'*60}")
        print(f"[{i}/{total}] {folder.name}")
        print(f"{'-'*60}")

        result = process_vehicle(folder, progress=progress, auto_report=auto_report, auto_db=auto_db)
        results.append(result)

        # Show mini progress across vehicles
        if progress:
            show_progress(i, total, f"Completed {i}/{total} vehicles...")

    return results


def print_batch_summary(results: List[Dict[str, Any]]):
    """Print detailed batch processing summary / 打印详细的批量处理汇总"""

    total = len(results)
    success_count = sum(1 for r in results if r['success'])
    failed_count = total - success_count

    total_duration = sum(r['duration'] for r in results)

    # Calculate totals
    total_ripple_conditions = 0
    total_slope_conditions = 0

    for r in results:
        if isinstance(r.get('ripple'), dict) and 'conditions' in r['ripple']:
            total_ripple_conditions += r['ripple']['conditions']
        if isinstance(r.get('slope'), dict) and 'conditions' in r['slope']:
            total_slope_conditions += r['slope']['conditions']

    print(f"\n{'='*60}")
    print(f"Batch Processing Summary / 批量处理汇总")
    print(f"{'='*60}")
    print(f"Total vehicles / 总计: {total}")
    print(f"Success / 成功: {success_count}")
    print(f"Failed / 失败: {failed_count}")
    print(f"Total Duration / 总耗时: {total_duration:.2f} seconds")
    print(f"Total RIPPLE conditions / 纹波工况总数: {total_ripple_conditions}")
    print(f"Total SLOPE conditions / 斜率工况总数: {total_slope_conditions}")

    # Report generation stats
    report_triggered = 0
    report_ripple_ok = 0
    report_slope_ok = 0
    report_failed = 0

    for r in results:
        rg = r.get('report_generation')
        if rg is not None:
            report_triggered += 1
            if rg.get('ripple_ok'):
                report_ripple_ok += 1
            if rg.get('slope_ok'):
                report_slope_ok += 1
            if rg.get('error') and not rg.get('ripple_ok') and not rg.get('slope_ok'):
                report_failed += 1

    if report_triggered > 0:
        print(f"Reports triggered / 报告触发: {report_triggered}")
        print(f"  RIPPLE reports OK / 纹波报告成功: {report_ripple_ok}")
        print(f"  SLOPE reports OK / 斜率报告成功: {report_slope_ok}")
        if report_failed > 0:
            print(f"  Reports failed / 报告失败: {report_failed}")

    # Database import stats
    db_triggered = 0
    db_success = 0
    for r in results:
        db = r.get('database_import')
        if db is not None:
            db_triggered += 1
            if db.get('success'):
                db_success += 1

    if db_triggered > 0:
        print(f"Database triggered / 数据库导入触发: {db_triggered}")
        print(f"  Database OK / 数据库导入成功: {db_success}")

    print(f"{'='*60}\n")

    # Print per-vehicle table
    print("Per-Vehicle Results / 各车辆结果:")
    print(f"{'Vehicle ID':<15} {'Status':<10} {'RIPPLE':<10} {'SLOPE':<10} {'Report':<10} {'Database':<10} {'Duration(s)':<12}")
    print("-" * 80)

    for r in results:
        vid = r['vehicle_id']
        status = "OK" if r['success'] else "FAIL"
        ripple_str = _format_task_result(r.get('ripple'))
        slope_str = _format_task_result(r.get('slope'))

        report_str = "-"
        rg = r.get('report_generation')
        if rg is not None:
            if rg.get('error') and not rg.get('ripple_ok') and not rg.get('slope_ok'):
                report_str = "FAIL"
            elif rg.get('ripple_ok') or rg.get('slope_ok'):
                report_str = "OK"
            else:
                report_str = "FAIL"

        db_str = "-"
        db = r.get('database_import')
        if db is not None:
            db_str = "OK" if db.get('success') else "FAIL"

        print(f"{vid:<15} {status:<10} {ripple_str:<10} {slope_str:<10} {report_str:<10} {db_str:<10} {r['duration']:<12.2f}")

    print(f"\n{'='*60}")

    # Print failed vehicles
    if failed_count > 0:
        print(f"\nFailed Vehicles / 失败的车辆:")
        for r in results:
            if not r['success']:
                print(f"  - {r['vehicle_id']}")

    print(f"{'='*60}\n")


def show_version():
    """Show version information / 显示版本信息"""
    ripple_version = get_skill_version('ripple')
    slope_version = get_skill_version('slope')

    print("\nVehicle Skills CLI / 车辆技能命令行工具")
    print("=" * 60)
    print(f"CLI Version / CLI版本: 1.1.0")
    print(f"Ripple Skill / 纹波技能: v{ripple_version}")
    print(f"Slope Skill / 斜率技能: v{slope_version}")
    print(f"Python: {sys.version.split()[0]}")
    print("=" * 60)


def show_validation_report(folder: Path, results: Dict[str, Any]):
    """Show validation report / 显示验证报告"""
    print(f"\nValidation Report / 验证报告: {folder.name}")
    print("=" * 60)

    if results['valid']:
        print("Status / 状态: [OK] Valid / 有效")
    else:
        print("Status / 状态: [FAIL] Invalid / 无效")

    print(f"\nData Found / 发现的数据:")
    print(f"  RIPPLE: {'Yes' if results['has_ripple'] else 'No'}")
    if results['has_ripple']:
        print(f"    Components / 组件数: {results['ripple_components']}")

    print(f"  SLOPE:  {'Yes' if results['has_slope'] else 'No'}")
    if results['has_slope']:
        print(f"    Components / 组件数: {results['slope_components']}")

    if results['warnings']:
        print(f"\nWarnings / 警告 ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  ! {warning}")

    if results['errors']:
        print(f"\nErrors / 错误 ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  [FAIL] {error}")

    print("=" * 60)


def main():
    """Main entry point / 主入口点"""
    parser = argparse.ArgumentParser(
        description='Vehicle Skills CLI - Process vehicle ripple and slope data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / 示例:
  # Process single vehicle / 处理单个车辆
  %(prog)s process E:/Vehicle_Date/V0001
  %(prog)s process E:/Vehicle_Date/V0001 --progress

  # Batch with explicit list / 批量处理（显式列表）
  %(prog)s batch E:/Vehicle_Date/V0001 E:/Vehicle_Date/V0002

  # Batch with auto-scan / 批量处理（自动扫描）
  %(prog)s batch --scan E:/Vehicle_Date
  %(prog)s batch --scan E:/Vehicle_Date --progress

  # Validate / 验证
  %(prog)s validate E:/Vehicle_Date/V0001

  # Version / 版本
  %(prog)s version
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands / 可用命令')

    # Process command / 处理命令
    process_parser = subparsers.add_parser(
        'process',
        help='Process single vehicle / 处理单个车辆',
        description='Process ripple and/or slope data for a single vehicle'
    )
    process_parser.add_argument(
        'vehicle_folder',
        type=Path,
        help='Path to vehicle folder / 车辆文件夹路径'
    )
    process_parser.add_argument(
        '--progress', '-p',
        action='store_true',
        help='Show progress bar / 显示进度条'
    )
    process_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Custom output directory / 自定义输出目录'
    )
    process_parser.add_argument(
        '--auto-report', '-r',
        action='store_true',
        help='Auto-generate Word reports after processing / 处理后自动生成Word报告'
    )
    process_parser.add_argument(
        '--auto-db', '-d',
        action='store_true', default=True,
        help='Auto-import to unified database after processing / 处理后自动导入统一数据库'
    )
    process_parser.add_argument(
        '--no-auto-db',
        action='store_false', dest='auto_db',
        help='Disable auto database import / 禁用自动数据库导入'
    )

    # Batch command / 批量命令
    batch_parser = subparsers.add_parser(
        'batch',
        help='Batch process multiple vehicles / 批量处理多个车辆',
        description='Process multiple vehicles in one command. Supports explicit list or auto-scan mode.'
    )
    batch_parser.add_argument(
        'vehicle_folders',
        nargs='*',
        type=Path,
        help='Paths to vehicle folders (optional if --scan is used) / 车辆文件夹路径列表（使用--scan时可省略）'
    )
    batch_parser.add_argument(
        '--scan', '-s',
        type=Path,
        metavar='PARENT_FOLDER',
        help='Auto-scan parent folder for vehicle folders / 自动扫描父目录发现车辆文件夹'
    )
    batch_parser.add_argument(
        '--progress', '-p',
        action='store_true',
        help='Show progress bar / 显示进度条'
    )
    batch_parser.add_argument(
        '--auto-report', '-r',
        action='store_true',
        help='Auto-generate Word reports after processing / 处理后自动生成Word报告'
    )
    batch_parser.add_argument(
        '--auto-db', '-d',
        action='store_true', default=True,
        help='Auto-import to unified database after processing / 处理后自动导入统一数据库'
    )
    batch_parser.add_argument(
        '--no-auto-db',
        action='store_false', dest='auto_db',
        help='Disable auto database import / 禁用自动数据库导入'
    )

    # Validate command / 验证命令
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate vehicle data / 验证车辆数据',
        description='Validate vehicle folder structure without processing'
    )
    validate_parser.add_argument(
        'vehicle_folder',
        type=Path,
        help='Path to vehicle folder / 车辆文件夹路径'
    )

    # Version command / 版本命令
    subparsers.add_parser(
        'version',
        help='Show version information / 显示版本信息',
        description='Display CLI and skill versions'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command / 执行命令
    if args.command == 'process':
        print_banner()
        result = process_vehicle(args.vehicle_folder, progress=args.progress,
                                output_dir=args.output, auto_report=args.auto_report,
                                auto_db=args.auto_db)

        if result['success']:
            print(f"\n[OK] Processing completed / 处理完成!")
            print(f"Duration / 耗时: {result['duration']:.2f} seconds")
            if result['ripple']:
                print(f"RIPPLE: {result['ripple'].get('conditions', 0)} conditions")
            if result['slope']:
                print(f"SLOPE: {result['slope'].get('conditions', 0)} conditions")
        else:
            print(f"\n[FAIL] Processing failed / 处理失败")
            sys.exit(1)

    elif args.command == 'batch':
        print_banner()

        # Determine vehicle folders / 确定车辆文件夹
        folders = []

        if args.scan:
            # Auto-scan mode / 自动扫描模式
            folders = scan_parent_folder(args.scan)
            if not folders:
                print(f"\nNo vehicle folders found in / 未找到车辆文件夹: {args.scan}")
                sys.exit(1)
        elif args.vehicle_folders:
            # Explicit list mode / 显式列表模式
            folders = args.vehicle_folders
        else:
            print("Error / 错误: Must provide either vehicle folders or --scan option")
            print("Usage / 用法:")
            print("  %(prog)s batch V0001 V0002 V0003")
            print("  %(prog)s batch --scan E:/Vehicle_Date")
            sys.exit(1)

        # Process / 处理
        results = batch_process(folders, progress=args.progress, auto_report=args.auto_report, auto_db=args.auto_db)

        # Print detailed summary / 打印详细汇总
        print_batch_summary(results)

        success_count = sum(1 for r in results if r['success'])
        if success_count < len(results):
            sys.exit(1)

    elif args.command == 'validate':
        print_banner()
        results = validate_vehicle_folder(args.vehicle_folder)
        show_validation_report(args.vehicle_folder, results)

        if not results['valid']:
            sys.exit(1)

    elif args.command == 'version':
        show_version()


if __name__ == '__main__':
    main()
