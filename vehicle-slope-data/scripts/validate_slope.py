#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆斜率数据验证工具
用于在处理前验证数据完整性，提前发现潜在问题

使用方法:
    python validate_slope.py --vehicle-folder V0001_SLOPE
    python validate_slope.py --vehicle-folder V0001_SLOPE --verbose

功能:
    1. 验证车辆信息文件完整性
    2. 验证命名规则文件格式
    3. 验证组件文件夹结构
    4. 验证斜率统计数据Excel格式（4列）
    5. 验证文件编码(UTF-8)
    6. 生成验证报告
"""

import os
import sys
import argparse
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import json


class SlopeValidator:
    """斜率数据验证器 - 在处理前检查数据完整性"""
    
    def __init__(self, vehicle_folder: str, verbose: bool = False):
        self.vehicle_folder = Path(vehicle_folder)
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.infos = []
        
        # 提取vehicle_id（支持{VehID}_SLOPE和VehID格式）
        self.vehicle_id = self._extract_vehicle_id(self.vehicle_folder.name)
        
        self.stats = {
            "total_components": 0,
            "valid_components": 0,
            "total_conditions": 0
        }
        
        # 斜率统计的期望列
        self.expected_columns = [
            '文件名',
            '斜率最大值(V/s)',
            '斜率最小值(V/s)',
            '斜率绝对值最大值(V/s)'
        ]
    
    def _extract_vehicle_id(self, folder_name: str) -> str:
        """
        从文件夹名称提取车辆ID
        
        支持格式:
          - {VehicleID}_SLOPE (推荐) → 返回 VehicleID
          - {VehicleID} (legacy) → 返回 VehicleID
        
        示例:
          - V0001_SLOPE → V0001
          - V0002_SLOPE → V0002
          - V0001 → V0001
        """
        if folder_name.endswith('_SLOPE'):
            return folder_name[:-6]  # 去掉 '_SLOPE' 后缀
        return folder_name
    
    def log(self, message: str):
        """详细日志输出"""
        if self.verbose:
            print(message)
    
    def validate_all(self) -> Tuple[bool, List, List, List]:
        """
        执行所有验证
        返回: (是否通过, 错误列表, 警告列表, 信息列表)
        """
        print(f"\n{'='*80}")
        print(f"车辆斜率数据验证工具")
        print(f"{'='*80}")
        print(f"车辆文件夹: {self.vehicle_folder}")
        print(f"车辆ID: {self.vehicle_id}")
        print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 1. 验证车辆信息文件
        self._validate_vehicle_info()
        
        # 2. 验证命名规则文件
        self._validate_naming_rules()
        
        # 3. 验证组件文件夹结构
        self._validate_component_structure()
        
        # 4. 验证文件编码
        self._validate_encoding()
        
        return len(self.issues) == 0, self.issues, self.warnings, self.infos
    
    def _validate_vehicle_info(self):
        """验证车辆信息文件"""
        print("[1/4] 验证车辆信息文件...")
        
        md_file = self.vehicle_folder / "vehicle_info.md"
        xlsx_file = self.vehicle_folder / "vehicle_info.xlsx"
        
        if not md_file.exists() and not xlsx_file.exists():
            self.issues.append({
                "type": "fatal",
                "category": "vehicle_info",
                "message": "缺少vehicle_info文件（需要.md或.xlsx）",
                "suggestion": "请添加车辆信息文件，包含车辆ID、车型等27个必填参数"
            })
            return
        
        # 优先检查markdown文件
        if md_file.exists():
            self._validate_vehicle_info_md(md_file)
        elif xlsx_file.exists():
            self._validate_vehicle_info_xlsx(xlsx_file)
        
        self.log("[OK] 车辆信息文件验证通过")
    
    def _validate_vehicle_info_md(self, file_path: Path):
        """验证车辆信息markdown文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                self.warnings.append({
                    "type": "encoding",
                    "category": "vehicle_info",
                    "message": f"{file_path.name} 使用GBK编码，建议转换为UTF-8",
                    "suggestion": "使用文本编辑器将文件保存为UTF-8格式"
                })
            except Exception as e:
                self.issues.append({
                    "type": "fatal",
                    "category": "vehicle_info",
                    "message": f"无法读取 {file_path.name}: {e}",
                    "suggestion": "检查文件是否损坏或权限问题"
                })
                return
        
        # 检查关键字段
        required_fields = ['车辆ID', '车型']
        missing_fields = [f for f in required_fields if f not in content]
        
        if missing_fields:
            self.issues.append({
                "type": "fatal",
                "category": "vehicle_info",
                "message": f"车辆信息缺少必需字段: {', '.join(missing_fields)}",
                "suggestion": "确保文件包含所有27个必需参数"
            })
    
    def _validate_vehicle_info_xlsx(self, file_path: Path):
        """验证车辆信息Excel文件"""
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                self.issues.append({
                    "type": "fatal",
                    "category": "vehicle_info",
                    "message": f"{file_path.name} 为空",
                    "suggestion": "请填写车辆信息数据"
                })
                return
            
            # 检查关键字段
            required_fields = ['车辆ID', '车型']
            columns = df.columns.tolist()
            missing_fields = [f for f in required_fields if f not in columns]
            
            if missing_fields:
                self.issues.append({
                    "type": "fatal",
                    "category": "vehicle_info",
                    "message": f"车辆信息缺少必需字段: {', '.join(missing_fields)}",
                    "suggestion": "确保Excel包含所有27个必需参数"
                })
                
        except Exception as e:
            self.issues.append({
                "type": "fatal",
                "category": "vehicle_info",
                "message": f"无法读取 {file_path.name}: {e}",
                "suggestion": "检查文件格式是否正确"
            })
    
    def _validate_naming_rules(self):
        """验证命名规则文件"""
        print("[2/4] 验证命名规则文件...")
        
        # 测试命名规则
        test_md = self.vehicle_folder / "test_naming_rules.md"
        test_xlsx = self.vehicle_folder / "test_naming_rules.xlsx"
        
        if test_md.exists():
            self._validate_test_rules_md(test_md)
        elif test_xlsx.exists():
            self._validate_test_rules_xlsx(test_xlsx)
        else:
            self.infos.append({
                "type": "info",
                "category": "test_naming_rules",
                "message": "未找到自定义test_naming_rules，将使用默认规则",
                "suggestion": "如需自定义规则，请添加test_naming_rules.md或.xlsx"
            })
        
        # 传感器命名规则
        sensor_md = self.vehicle_folder / "sensor_naming_rules.md"
        sensor_xlsx = self.vehicle_folder / "sensor_naming_rules.xlsx"
        
        if sensor_md.exists():
            self._validate_sensor_rules_md(sensor_md)
        elif sensor_xlsx.exists():
            self._validate_sensor_rules_xlsx(sensor_xlsx)
        else:
            self.infos.append({
                "type": "info",
                "category": "sensor_naming_rules",
                "message": "未找到自定义sensor_naming_rules，将使用默认规则",
                "suggestion": "如需自定义规则，请添加sensor_naming_rules.md或.xlsx"
            })
        
        self.log("[OK] 命名规则文件验证通过")
    
    def _validate_test_rules_md(self, file_path: Path):
        """验证测试命名规则markdown文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            self.warnings.append({
                "type": "encoding",
                "category": "test_naming_rules",
                "message": f"{file_path.name} 编码可能不是UTF-8",
                "suggestion": "建议将文件保存为UTF-8格式"
            })
            return
        
        # 检查基本格式
        if '|' not in content:
            self.warnings.append({
                "type": "format",
                "category": "test_naming_rules",
                "message": f"{file_path.name} 不包含表格格式",
                "suggestion": "确保使用markdown表格格式"
            })
    
    def _validate_test_rules_xlsx(self, file_path: Path):
        """验证测试命名规则Excel文件"""
        try:
            df = pd.read_excel(file_path)
            
            required_cols = ['电量状态', '工况名称', '数据命名举例']
            missing_cols = [c for c in required_cols if c not in df.columns]
            
            if missing_cols:
                self.warnings.append({
                    "type": "format",
                    "category": "test_naming_rules",
                    "message": f"{file_path.name} 缺少必需列: {', '.join(missing_cols)}",
                    "suggestion": "确保包含：电量状态、工况名称、数据命名举例"
                })
                
        except Exception as e:
            self.warnings.append({
                "type": "format",
                "category": "test_naming_rules",
                "message": f"无法读取 {file_path.name}: {e}",
                "suggestion": "检查文件格式是否正确"
            })
    
    def _validate_sensor_rules_md(self, file_path: Path):
        """验证传感器命名规则markdown文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            self.warnings.append({
                "type": "encoding",
                "category": "sensor_naming_rules",
                "message": f"{file_path.name} 编码可能不是UTF-8",
                "suggestion": "建议将文件保存为UTF-8格式"
            })
    
    def _validate_sensor_rules_xlsx(self, file_path: Path):
        """验证传感器命名规则Excel文件"""
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                self.warnings.append({
                    "type": "format",
                    "category": "sensor_naming_rules",
                    "message": f"{file_path.name} 为空",
                    "suggestion": "请填写传感器命名规则"
                })
                
        except Exception as e:
            self.warnings.append({
                "type": "format",
                "category": "sensor_naming_rules",
                "message": f"无法读取 {file_path.name}: {e}",
                "suggestion": "检查文件格式是否正确"
            })
    
    def _validate_component_structure(self):
        """验证组件文件夹结构"""
        print("[3/4] 验证组件文件夹结构...")
        
        # 获取所有子文件夹
        component_folders = []
        for item in self.vehicle_folder.iterdir():
            if item.is_dir() and item.name != 'SKILL_output':
                component_folders.append(item)
        
        if not component_folders:
            self.issues.append({
                "type": "fatal",
                "category": "component_structure",
                "message": "未找到任何组件文件夹",
                "suggestion": "确保车辆文件夹包含组件子文件夹（如FM_A, LV_V等）"
            })
            return
        
        self.stats["total_components"] = len(component_folders)
        
        # 验证每个组件文件夹
        for folder in component_folders:
            self._validate_component_folder(folder)
        
        self.log(f"[OK] 组件文件夹验证通过 ({self.stats['valid_components']}/{self.stats['total_components']})")
    
    def _validate_component_folder(self, folder: Path):
        """验证单个组件文件夹"""
        # 检查statistics.xlsx
        stats_file = folder / "statistics.xlsx"
        
        if not stats_file.exists():
            self.issues.append({
                "type": "fatal",
                "category": "component_structure",
                "message": f"组件 {folder.name} 缺少 statistics.xlsx",
                "suggestion": f"请在 {folder.name} 文件夹中添加 statistics.xlsx"
            })
            return
        
        # 验证Excel文件
        self._validate_statistics_excel(stats_file)
        self.stats["valid_components"] += 1
    
    def _validate_statistics_excel(self, file_path: Path):
        """验证斜率统计Excel文件"""
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                self.warnings.append({
                    "type": "data",
                    "category": "statistics",
                    "message": f"{file_path.parent.name}/statistics.xlsx 为空",
                    "suggestion": "确保文件包含斜率数据"
                })
                return
            
            # 检查列数
            actual_cols = list(df.columns)
            if len(actual_cols) != 4:
                self.issues.append({
                    "type": "fatal",
                    "category": "statistics",
                    "message": f"{file_path.parent.name}/statistics.xlsx 列数不正确 "
                              f"(期望4列，实际{len(actual_cols)}列)",
                    "suggestion": f"期望列: {', '.join(self.expected_columns)}"
                })
                return
            
            # 检查列名
            missing_cols = [c for c in self.expected_columns if c not in actual_cols]
            if missing_cols:
                self.issues.append({
                    "type": "fatal",
                    "category": "statistics",
                    "message": f"{file_path.parent.name}/statistics.xlsx 缺少必需列: {', '.join(missing_cols)}",
                    "suggestion": f"请确保列名完全匹配: {', '.join(self.expected_columns)}"
                })
                return
            
            # 检查数据行数
            self.stats["total_conditions"] += len(df)
            
            # 检查数据类型
            for col in self.expected_columns[1:]:  # 跳过'文件名'列
                non_numeric = []
                for idx, value in enumerate(df[col]):
                    if pd.notna(value):
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            non_numeric.append(idx)
                
                if non_numeric:
                    self.warnings.append({
                        "type": "data",
                        "category": "statistics",
                        "message": f"{file_path.parent.name}/statistics.xlsx 的 '{col}' 列包含非数值数据",
                        "suggestion": f"检查第 {non_numeric[0]+1} 行等的数据格式"
                    })
            
            self.log(f"  [OK] {file_path.parent.name}: {len(df)} 个工况")
            
        except Exception as e:
            self.issues.append({
                "type": "fatal",
                "category": "statistics",
                "message": f"无法读取 {file_path.parent.name}/statistics.xlsx: {e}",
                "suggestion": "检查文件格式是否为有效的Excel文件"
            })
    
    def _validate_encoding(self):
        """验证文件编码"""
        print("[4/4] 验证文件编码...")
        
        # 检查markdown文件
        md_files = list(self.vehicle_folder.glob("*.md"))
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    f.read()
            except UnicodeDecodeError:
                self.warnings.append({
                    "type": "encoding",
                    "category": "file_encoding",
                    "message": f"{md_file.name} 可能不是UTF-8编码",
                    "suggestion": "建议将文件保存为UTF-8格式以确保中文正确显示"
                })
        
        self.log("[OK] 编码验证完成")
    
    def generate_report(self, output_file: Optional[str] = None) -> Path:
        """生成验证报告"""
        if output_file is None:
            output_path = self.vehicle_folder / "validation_report.json"
        else:
            output_path = Path(output_file)
        
        report = {
            "validation_time": datetime.now().isoformat(),
            "vehicle_folder": str(self.vehicle_folder),
            "vehicle_id": self.vehicle_id,
            "summary": {
                "total_components": self.stats["total_components"],
                "total_conditions": self.stats["total_conditions"],
                "issues_count": len(self.issues),
                "warnings_count": len(self.warnings),
                "passed": len(self.issues) == 0
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "infos": self.infos
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def print_report(self):
        """打印验证报告"""
        print(f"\n{'='*80}")
        print("验证报告摘要".center(80))
        print(f"{'='*80}")
        
        # 统计信息
        print(f"\n📊 数据统计:")
        print(f"  组件总数: {self.stats['total_components']}")
        print(f"  有效组件: {self.stats['valid_components']}")
        print(f"  测试工况数: {self.stats['total_conditions']}")
        
        # 结果摘要
        if not self.issues and not self.warnings:
            print(f"\n✅ 验证通过！所有检查项均符合要求。")
            print(f"   数据准备就绪，可以开始处理。\n")
            return True
        
        # 错误
        if self.issues:
            print(f"\n❌ 发现 {len(self.issues)} 个错误（必须修复）:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n  {i}. [{issue['category']}] {issue['message']}")
                print(f"     💡 建议: {issue['suggestion']}")
        
        # 警告
        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告（处理将继续）:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"\n  {i}. [{warning['category']}] {warning['message']}")
                print(f"     💡 建议: {warning['suggestion']}")
        
        # 信息
        if self.infos:
            print(f"\nℹ️  信息 ({len(self.infos)}):")
            for i, info in enumerate(self.infos, 1):
                print(f"  {i}. [{info['category']}] {info['message']}")
        
        print(f"\n{'='*80}\n")
        
        return len(self.issues) == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='车辆斜率数据验证工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基本验证
  python validate_slope.py --vehicle-folder V0001_SLOPE
  
  # 详细输出
  python validate_slope.py --vehicle-folder V0001_SLOPE --verbose
  
  # 生成JSON报告
  python validate_slope.py --vehicle-folder V0001_SLOPE --output-report validation.json
        '''
    )
    
    parser.add_argument(
        '--vehicle-folder', '-f',
        required=True,
        help='车辆文件夹路径（支持{VehID}_SLOPE或{VehID}格式）'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--output-report',
        help='生成JSON格式的验证报告'
    )
    
    args = parser.parse_args()
    
    # 创建验证器
    validator = SlopeValidator(args.vehicle_folder, verbose=args.verbose)
    
    # 执行验证
    passed, issues, warnings, infos = validator.validate_all()
    
    # 打印报告
    validator.print_report()
    
    # 生成JSON报告（如果指定）
    if args.output_report:
        report_path = validator.generate_report(args.output_report)
        print(f"📄 验证报告已保存: {report_path}\n")
    
    # 返回退出码
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
