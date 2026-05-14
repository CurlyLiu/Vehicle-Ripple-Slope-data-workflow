#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆纹波数据处理 - 命令行入口
完全独立的CLI工具，不依赖SKILL系统

使用方法:
    # 处理单个车辆（推荐格式: {VehID}_RIPPLE）
    python cli/process_vehicle.py --folder V0001_RIPPLE
    
    # 验证后处理（推荐格式）
    python cli/process_vehicle.py --folder V0001_RIPPLE --validate-first
    
    # 只生成特定格式
    python cli/process_vehicle.py --folder V0001_RIPPLE --format json,excel
    
    # 使用增量处理
    python cli/process_vehicle.py --folder V0001_RIPPLE --incremental
    
    # 旧版格式仍然支持
    python cli/process_vehicle.py --folder V0001

Token消耗: 约100-500（仅命令行解析）
相比SKILL调用: 节省90%+ token
"""

import argparse
import sys
import os
from pathlib import Path

# 添加parent到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import VehicleDataProcessor
from incremental_processor import IncrementalProcessor
from validate_rules import RuleValidator
from version_utils import get_ripple_version

# 获取版本号
VERSION = get_ripple_version()


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='vehicle-ripple',
        description='''
车辆纹波数据处理工具

处理车辆高压纹波测试数据，生成JSON、Excel和SQLite报告。

示例:
  %(prog)s --folder V0001
  %(prog)s --folder V0001 --validate-first
  %(prog)s --folder V0001 --incremental --format excel
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 必需参数
    parser.add_argument(
        '--folder', '-f',
        required=True,
        help='车辆文件夹路径（包含vehicle_info.md和组件子文件夹）'
    )
    
    # 可选参数
    parser.add_argument(
        '--validate-first', '-v',
        action='store_true',
        help='处理前先验证数据完整性（推荐）'
    )
    
    parser.add_argument(
        '--incremental', '-i',
        action='store_true',
        help='使用增量处理（只处理变化的文件）'
    )
    
    parser.add_argument(
        '--format', '-fmt',
        default='all',
        help='输出格式: all, json, excel, sqlite（逗号分隔多个）'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        help='输出目录（默认: vehicle_folder/{VehicleID}_RIPPLE_output）'
    )
    
    parser.add_argument(
        '--verbose', '-V',
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}'
    )
    
    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 验证文件夹存在
    vehicle_folder = Path(args.folder)
    if not vehicle_folder.exists():
        print(f"错误: 文件夹不存在 - {vehicle_folder}")
        return 1
    
    print(f"车辆纹波数据处理工具 v{VERSION}")
    print(f"=" * 60)
    print(f"车辆文件夹: {vehicle_folder.absolute()}")
    print()
    
    try:
        # 步骤1: 验证（如果启用）
        if args.validate_first:
            print("[步骤1/3] 验证数据完整性...")
            validator = RuleValidator(str(vehicle_folder), verbose=args.verbose)
            passed, issues, warnings, infos = validator.validate_all()
            
            if not passed:
                print("\n[FAIL] 验证失败，请修复以下错误:")
                for issue in issues:
                    print(f"  - {issue['message']}")
                return 1
            
            if warnings:
                print(f"\n[WARN] {len(warnings)}个警告（处理将继续）")
            
            print("[OK] 验证通过\n")
        
        # 步骤2: 增量检测（如果启用）
        if args.incremental:
            print("[步骤2/3] 检测文件变化...")
            processor = IncrementalProcessor(str(vehicle_folder))
            new, modified, deleted = processor.detect_changes()
            
            if not new and not modified and not deleted:
                print("[OK] 没有检测到变化，跳过处理")
                return 0
            
            print()
        
        # 步骤3: 处理数据
        print("[步骤3/3] 处理车辆数据...")
        
        # 解析格式选项
        formats = [f.strip() for f in args.format.split(',')]
        
        config = {
            'generate_json': 'all' in formats or 'json' in formats,
            'generate_excel': 'all' in formats or 'excel' in formats,
            'generate_sqlite': 'all' in formats or 'sqlite' in formats,
            'output_dir': args.output_dir
        }
        
        # 执行处理
        processor = VehicleDataProcessor(str(vehicle_folder), config)
        result = processor.process()
        
        # 显示结果摘要
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"车辆ID: {result['vehicle']['vehicle_id']}")
        print(f"车型: {result['vehicle']['vehicle_info'].get('车型', 'Unknown')}")
        print(f"组件数: {len(result['components'])}")
        print(f"工况数: {result['metadata']['total_conditions']}")
        
        # 显示输出文件
        output_dir = processor.output_dir
        print(f"\n输出文件:")
        for file in output_dir.iterdir():
            size = file.stat().st_size / 1024  # KB
            print(f"  [OK] {file.name} ({size:.1f} KB)")
        
        # 显示警告
        if result['metadata']['warnings']:
            print(f"\n[WARN] 警告 ({len(result['metadata']['warnings'])}):")
            for warning in result['metadata']['warnings'][:5]:
                print(f"  - {warning}")
            if len(result['metadata']['warnings']) > 5:
                print(f"  ... 还有 {len(result['metadata']['warnings'])-5} 个")
        
        # 更新增量缓存
        if args.incremental:
            inc_processor = IncrementalProcessor(str(vehicle_folder))
            inc_processor.update_cache()
        
        print("\n[OK] 全部完成!")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n处理被用户中断")
        return 130
    except Exception as e:
        print(f"\n[ERROR] 处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
