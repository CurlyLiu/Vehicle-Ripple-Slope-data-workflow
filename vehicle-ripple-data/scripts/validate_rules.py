#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆纹波数据规则验证工具
用于在处理前验证数据完整性，提前发现潜在问题

使用方法:
    python validate_rules.py --vehicle-folder V0001
    python validate_rules.py --vehicle-folder V0001 --verbose

功能:
    1. 验证车辆信息文件完整性
    2. 验证命名规则文件格式
    3. 验证组件文件夹结构
    4. 验证图片与Excel匹配
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


class RuleValidator:
    """规则验证器 - 在处理前检查数据完整性"""
    
    def __init__(self, vehicle_folder: str, verbose: bool = False):
        self.vehicle_folder = Path(vehicle_folder)
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.infos = []
        self.stats = {
            "total_components": 0,
            "valid_components": 0,
            "total_conditions": 0,
            "images_found": 0,
            "missing_images": 0
        }
        # 提取vehicle_id（支持{VehID}_RIPPLE和VehID格式）
        self.vehicle_id = self._extract_vehicle_id(self.vehicle_folder.name)
        
    def log(self, message: str):
        """详细日志输出"""
        if self.verbose:
            print(message)
    
    def _extract_vehicle_id(self, folder_name: str) -> str:
        """
        从文件夹名称提取车辆ID
        支持格式:
          - {VehicleID}_RIPPLE (推荐) → 返回 VehicleID
          - {VehicleID} (legacy) → 返回 VehicleID
        
        示例:
          - V0001_RIPPLE → V0001
          - V0002_RIPPLE → V0002
          - V0001 → V0001
        """
        if folder_name.endswith('_RIPPLE'):
            return folder_name[:-7]  # 去掉 '_RIPPLE' 后缀
        return folder_name
    
    def validate_all(self) -> Tuple[bool, List, List, List]:
        """
        执行所有验证
        返回: (是否通过, 错误列表, 警告列表, 信息列表)
        """
        print(f"\n{'='*80}")
        print(f"车辆纹波数据规则验证工具")
        print(f"{'='*80}")
        print(f"车辆文件夹: {self.vehicle_folder}")
        print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 1. 验证车辆信息文件
        self._validate_vehicle_info()
        
        # 2. 验证命名规则文件
        self._validate_naming_rules()
        
        # 3. 验证组件文件夹结构
        self._validate_component_structure()
        
        # 4. 验证图片-Excel匹配
        self._validate_image_excel_match()
        
        # 5. 验证编码
        self._validate_encoding()
        
        # 6. 验证setup图片
        self._validate_setup_image()
        
        return len(self.issues) == 0, self.issues, self.warnings, self.infos
    
    def _validate_vehicle_info(self):
        """验证车辆信息文件"""
        print("[1/6] 验证车辆信息文件...")
        
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
            self._check_vehicle_info_md(md_file)
        elif xlsx_file.exists():
            self._check_vehicle_info_xlsx(xlsx_file)
        
        self.infos.append({
            "type": "info",
            "category": "vehicle_info",
            "message": f"找到车辆信息文件: {md_file.name if md_file.exists() else xlsx_file.name}"
        })
    
    def _check_vehicle_info_md(self, file_path: Path):
        """检查Markdown格式的车辆信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查必填字段
            required_fields = [
                "车辆ID", "车型", "车长mm", "车宽mm", "车高mm",
                "轴距(mm)", "混合动力系统", "驱动形式",
                "动力电池类型", "动力电池总电量(kWh)"
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in content:
                    missing_fields.append(field)
            
            if missing_fields:
                self.warnings.append({
                    "type": "warning",
                    "category": "vehicle_info",
                    "message": f"vehicle_info可能缺少以下字段: {', '.join(missing_fields)}",
                    "suggestion": "请检查并补全车辆信息文件"
                })
            
            self.log(f"  [OK] 成功读取车辆信息文件，共{len(content)}字符")
            
        except UnicodeDecodeError:
            self.issues.append({
                "type": "error",
                "category": "encoding",
                "message": f"{file_path.name}编码错误，应为UTF-8",
                "suggestion": "请用UTF-8编码重新保存文件，不要用GBK或ANSI"
            })
        except Exception as e:
            self.issues.append({
                "type": "error",
                "category": "vehicle_info",
                "message": f"无法读取车辆信息文件: {str(e)}",
                "suggestion": "请检查文件格式是否正确"
            })
    
    def _check_vehicle_info_xlsx(self, file_path: Path):
        """检查Excel格式的车辆信息"""
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                self.issues.append({
                    "type": "error",
                    "category": "vehicle_info",
                    "message": "vehicle_info.xlsx为空",
                    "suggestion": "请添加车辆信息数据"
                })
            else:
                self.log(f"  [OK] Excel文件包含 {len(df)} 行数据")
                
        except Exception as e:
            self.issues.append({
                "type": "error",
                "category": "vehicle_info",
                "message": f"无法读取vehicle_info.xlsx: {str(e)}",
                "suggestion": "请检查Excel文件是否损坏"
            })
    
    def _validate_naming_rules(self):
        """验证命名规则文件"""
        print("[2/6] 验证命名规则文件...")
        
        # Test naming rules
        test_rules_md = self.vehicle_folder / "test_naming_rules.md"
        test_rules_xlsx = self.vehicle_folder / "test_naming_rules.xlsx"
        
        if not test_rules_md.exists() and not test_rules_xlsx.exists():
            self.infos.append({
                "type": "info",
                "category": "naming_rules",
                "message": "未找到test_naming_rules文件，将使用默认规则",
                "suggestion": "如需自定义工况映射，请添加该文件"
            })
        else:
            file_used = test_rules_md if test_rules_md.exists() else test_rules_xlsx
            self.infos.append({
                "type": "info",
                "category": "naming_rules",
                "message": f"找到test_naming_rules: {file_used.name}"
            })
            
            # 检查是否包含所有SOC等级
            if test_rules_md.exists():
                self._check_soc_levels(test_rules_md)
        
        # Sensor naming rules
        sensor_rules_md = self.vehicle_folder / "sensor_naming_rules.md"
        sensor_rules_xlsx = self.vehicle_folder / "sensor_naming_rules.xlsx"
        
        if not sensor_rules_md.exists() and not sensor_rules_xlsx.exists():
            self.infos.append({
                "type": "info",
                "category": "naming_rules",
                "message": "未找到sensor_naming_rules文件，将使用默认规则",
                "suggestion": "如需自定义组件定义，请添加该文件"
            })
        else:
            file_used = sensor_rules_md if sensor_rules_md.exists() else sensor_rules_xlsx
            self.infos.append({
                "type": "info",
                "category": "naming_rules",
                "message": f"找到sensor_naming_rules: {file_used.name}"
            })
    
    def _check_soc_levels(self, file_path: Path):
        """检查是否包含所有SOC等级"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soc_levels = ["≥70%", "40%-70%", "≤40%"]
            missing_soc = []
            
            for soc in soc_levels:
                if soc not in content and soc.replace('%', '') not in content:
                    missing_soc.append(soc)
            
            if missing_soc:
                self.warnings.append({
                    "type": "warning",
                    "category": "naming_rules",
                    "message": f"test_naming_rules可能缺少SOC等级: {', '.join(missing_soc)}",
                    "suggestion": "请确认高/中/低电量三个等级的工况都已定义"
                })
            
            self.log(f"  [OK] 找到{3-len(missing_soc)}/3个SOC等级定义")
            
        except Exception as e:
            self.warnings.append({
                "type": "warning",
                "category": "naming_rules",
                "message": f"无法验证SOC等级: {str(e)}",
                "suggestion": "请手动检查规则文件"
            })
    
    def _validate_component_structure(self):
        """验证组件文件夹结构"""
        print("[3/6] 验证组件文件夹结构...")
        
        # 获取所有子文件夹
        component_folders = [
            d for d in self.vehicle_folder.iterdir() 
            if d.is_dir() 
            and not d.name.startswith('.') 
            and not d.name.endswith('_RIPPLE_output')
            and not d.name == '__pycache__'
        ]
        
        self.stats["total_components"] = len(component_folders)
        
        if len(component_folders) == 0:
            self.issues.append({
                "type": "fatal",
                "category": "structure",
                "message": "未找到任何组件文件夹",
                "suggestion": "请确保车辆文件夹包含组件子文件夹（如LV_V, ACC_A, PTC_V等）"
            })
            return
        
        print(f"  发现 {len(component_folders)} 个组件文件夹")
        
        # 检查每个组件文件夹
        for comp_folder in component_folders:
            self._validate_single_component(comp_folder)
        
        self.stats["valid_components"] = self.stats["total_components"]
    
    def _validate_single_component(self, comp_folder: Path):
        """验证单个组件文件夹"""
        comp_name = comp_folder.name
        self.log(f"\n  检查组件: {comp_name}")
        
        # 检查statistics.xlsx
        stats_file = comp_folder / "statistics.xlsx"
        if not stats_file.exists():
            self.issues.append({
                "type": "error",
                "category": "structure",
                "message": f"组件 {comp_name} 缺少statistics.xlsx",
                "suggestion": "请添加统计数据文件，包含工况ID、VPP值、频率等列"
            })
            return
        
        # 检查Excel格式
        try:
            df = pd.read_excel(stats_file)
            
            if df.empty:
                self.warnings.append({
                    "type": "warning",
                    "category": "excel_format",
                    "message": f"组件 {comp_name} 的statistics.xlsx为空",
                    "suggestion": "请添加测试数据"
                })
            else:
                self.stats["total_conditions"] += len(df)
                self.log(f"    [OK] 包含 {len(df)} 个工况")
                
                # 检查列数
                if len(df.columns) != 7:
                    self.warnings.append({
                        "type": "warning",
                        "category": "excel_format",
                        "message": f"组件 {comp_name} 的statistics.xlsx有{len(df.columns)}列（期望7列）",
                        "suggestion": "检查列是否完整，缺失的列将在处理时填充为null"
                    })
                
                # 检查第一列（应为工况ID）
                if not df.empty:
                    sample_id = str(df.iloc[0, 0])
                    if '_' not in sample_id:
                        self.warnings.append({
                            "type": "warning",
                            "category": "excel_format",
                            "message": f"组件 {comp_name} 的工况ID格式异常: {sample_id}",
                            "suggestion": "工况ID应为SOC_描述格式，如'20_直流充电暖风'"
                        })
                
        except Exception as e:
            self.issues.append({
                "type": "error",
                "category": "excel_format",
                "message": f"无法读取 {comp_name}/statistics.xlsx: {str(e)}",
                "suggestion": "检查Excel文件是否损坏或格式不正确"
            })
        
        # 检查PNG图片
        png_files = list(comp_folder.glob("*.png"))
        jpg_files = list(comp_folder.glob("*.jpg"))
        total_images = len(png_files) + len(jpg_files)
        
        self.stats["images_found"] += total_images
        
        if total_images == 0:
            self.warnings.append({
                "type": "warning",
                "category": "images",
                "message": f"组件 {comp_name} 未找到图片文件(.png或.jpg)",
                "suggestion": "请确认结果图片是否已放入组件文件夹"
            })
        else:
            self.log(f"    [OK] 找到 {total_images} 张图片")
    
    def _validate_image_excel_match(self):
        """验证图片与Excel匹配"""
        print("[4/6] 验证图片与Excel匹配...")
        
        mismatches = 0
        
        for comp_folder in self.vehicle_folder.iterdir():
            if not comp_folder.is_dir() or comp_folder.name.startswith('.'):
                continue
            
            comp_name = comp_folder.name
            stats_file = comp_folder / "statistics.xlsx"
            
            if not stats_file.exists():
                continue
            
            try:
                df = pd.read_excel(stats_file)
                if df.empty:
                    continue
                
                # 获取Excel中的工况ID（假设第一列是ID）
                excel_conditions = set(df.iloc[:, 0].astype(str).tolist())
                
                # 获取图片文件名中的工况ID
                png_files = list(comp_folder.glob("*.png"))
                image_conditions = set()
                
                for png in png_files:
                    # 解析文件名获取condition_id
                    # 格式: {SOC}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amp}.{unit}.png
                    parts = png.stem.split('_')
                    if len(parts) >= 2:
                        # 对于坡度工况：坡度10_{SOC}_{desc}
                        if parts[0] == '坡度10':
                            condition_id = '_'.join(parts[:3])
                        else:
                            condition_id = '_'.join(parts[:2])
                        image_conditions.add(condition_id)
                
                # 检查缺失
                missing_in_excel = image_conditions - excel_conditions
                missing_in_images = excel_conditions - image_conditions
                
                if missing_in_excel:
                    mismatches += 1
                    self.warnings.append({
                        "type": "warning",
                        "category": "match",
                        "message": f"组件 {comp_name} 有{len(missing_in_excel)}个工况在Excel中缺失",
                        "suggestion": f"图片中存在但Excel中缺失: {', '.join(list(missing_in_excel)[:3])}"
                    })
                
                if missing_in_images:
                    mismatches += 1
                    self.stats["missing_images"] += len(missing_in_images)
                    self.warnings.append({
                        "type": "warning",
                        "category": "match",
                        "message": f"组件 {comp_name} 有{len(missing_in_images)}个工况缺少图片",
                        "suggestion": f"Excel中存在但缺少图片: {', '.join(list(missing_in_images)[:3])}"
                    })
                
                if not missing_in_excel and not missing_in_images:
                    self.log(f"  [OK] {comp_name}: {len(excel_conditions)}个工况完全匹配")
                    
            except Exception as e:
                self.warnings.append({
                    "type": "warning",
                    "category": "match",
                    "message": f"无法验证 {comp_name} 的匹配: {str(e)}",
                    "suggestion": "请手动检查图片和Excel是否对应"
                })
        
        if mismatches == 0:
            print("  [OK] 所有组件的图片与Excel完全匹配")
    
    def _validate_encoding(self):
        """验证文件编码"""
        print("[5/6] 验证文件编码...")
        
        encoding_errors = 0
        
        # 检查所有.md文件
        md_files = list(self.vehicle_folder.glob("*.md"))
        md_files.extend(self.vehicle_folder.rglob("**/*.md"))
        
        for md_file in md_files:
            if '.cache' in str(md_file):
                continue
                
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否包含乱码特征
                    if '��' in content or '\ufffd' in content:
                        encoding_errors += 1
                        self.issues.append({
                            "type": "error",
                            "category": "encoding",
                            "message": f"文件 {md_file.name} 包含乱码字符",
                            "suggestion": "请用UTF-8编码重新保存文件"
                        })
            except UnicodeDecodeError:
                encoding_errors += 1
                self.issues.append({
                    "type": "error",
                    "category": "encoding",
                    "message": f"文件 {md_file.name} 编码错误",
                    "suggestion": "请用UTF-8编码重新保存文件（不要用GBK或ANSI）"
                })
        
        if encoding_errors == 0:
            print("  [OK] 所有文件编码正确（UTF-8）")
        
        self.log(f"  检查了 {len(md_files)} 个Markdown文件")
    
    def _validate_setup_image(self):
        """验证setup图片"""
        print("[6/6] 验证车辆照片...")
        
        setup_png = self.vehicle_folder / "setup.png"
        setup_jpg = self.vehicle_folder / "setup.jpg"
        
        if not setup_png.exists() and not setup_jpg.exists():
            self.infos.append({
                "type": "info",
                "category": "setup_image",
                "message": "未找到setup图片（setup.png或setup.jpg）",
                "suggestion": "建议添加车辆照片，用于生成报告时展示"
            })
        else:
            img_file = setup_png if setup_png.exists() else setup_jpg
            self.infos.append({
                "type": "info",
                "category": "setup_image",
                "message": f"找到车辆照片: {img_file.name}"
            })
            self.log(f"  [OK] 车辆照片: {img_file.name}")
    
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
                "images_found": self.stats["images_found"],
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
        print(f"\n[STATS] 数据统计:")
        print(f"  组件总数: {self.stats['total_components']}")
        print(f"  测试工况数: {self.stats['total_conditions']}")
        print(f"  图片文件数: {self.stats['images_found']}")

        # 结果摘要
        if not self.issues and not self.warnings:
            print(f"\n[OK] 验证通过！所有检查项均符合要求。")
            print(f"   数据准备就绪，可以开始处理。\n")
            return True

        # 错误
        if self.issues:
            print(f"\n[FAIL] 发现 {len(self.issues)} 个错误（必须修复）:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n  {i}. [{issue['category']}] {issue['message']}")
                print(f"     建议: {issue['suggestion']}")

        # 警告
        if self.warnings:
            print(f"\n[WARN] 发现 {len(self.warnings)} 个警告（建议处理）:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"\n  {i}. [{warning['category']}] {warning['message']}")
                if 'suggestion' in warning:
                    print(f"     建议: {warning['suggestion']}")
        
        # 信息
        if self.infos:
            print(f"\n[INFO] 信息 ({len(self.infos)}条):")
            for info in self.infos:
                print(f"  - [{info['category']}] {info['message']}")

        print(f"\n{'='*80}")
        if self.issues:
            print("状态: [FAIL] 验证失败，请先修复错误后再处理数据")
            return False
        else:
            print("状态: [WARN] 验证通过，但建议处理警告以提升数据质量")
            return True


def main():
    parser = argparse.ArgumentParser(
        description='车辆纹波数据规则验证工具 - 在处理前检查数据完整性',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --vehicle-folder V0001
  %(prog)s --vehicle-folder V0001 --verbose
  %(prog)s --vehicle-folder V0001 --output-report validation.json
        """
    )
    
    parser.add_argument('--vehicle-folder', '-v', required=True, 
                        help='车辆文件夹路径（包含组件子文件夹）')
    parser.add_argument('--verbose', action='store_true',
                        help='显示详细日志')
    parser.add_argument('--output-report', '-o', metavar='FILE',
                        help='输出验证报告到JSON文件')
    
    args = parser.parse_args()
    
    # 检查车辆文件夹是否存在
    if not os.path.exists(args.vehicle_folder):
        print(f"错误: 文件夹不存在 - {args.vehicle_folder}")
        sys.exit(1)
    
    # 执行验证
    validator = RuleValidator(args.vehicle_folder, verbose=args.verbose)
    passed, issues, warnings, infos = validator.validate_all()
    
    # 打印报告
    validator.print_report()
    
    # 保存报告
    if args.output_report:
        report_file = validator.generate_report(args.output_report)
        print(f"\n验证报告已保存: {report_file}")
    
    # 返回状态码
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
