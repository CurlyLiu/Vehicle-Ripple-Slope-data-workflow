#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆斜率数据处理 - 中文错误报告生成器 (共享自vehicle-ripple-data V4.3)
生成error_report.md记录处理步骤、错误、警告和生成的文件
所有输出文件放入{VehicleID}_SLOPE_output文件夹

版本: 1.0
新功能:
1. 中文错误报告
2. 所有输出放入{VehicleID}_SLOPE_output文件夹

使用方法:
    from scripts.generate_error_report_cn import generate_error_report_cn
    generate_error_report_cn(vehicle_folder, vehicle_id, vehicle_model, ...)
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional


def generate_error_report_cn(
    vehicle_folder: str,
    vehicle_id: str,
    vehicle_model: str,
    processing_status: bool,
    completed_functions: List[Dict[str, Any]],
    generated_files: List[Dict[str, str]],
    errors: Optional[List[Dict[str, str]]] = None,
    warnings: Optional[List[Dict[str, str]]] = None,
    processing_stats: Optional[Dict[str, Any]] = None,
    output_folder: Optional[str] = None
) -> str:
    """
    生成中文error_report.md
    
    参数:
        vehicle_folder: 车辆文件夹路径
        vehicle_id: 车辆标识符 (如 V0001)
        vehicle_model: 车辆型号名称
        processing_status: True表示成功, False表示失败
        completed_functions: [{'name': str, 'success': bool, 'details': str}]
        generated_files: [{'name': str, 'type': str, 'description': str}]
        errors: [{'type': str, 'message': str, 'component': str}]
        warnings: [{'type': str, 'message': str, 'component': str}]
        processing_stats: {'total_components', 'processed_components', ...}
        output_folder: 输出文件夹路径 (可选，默认为 {vehicle_id}_SLOPE_output)
    
    返回:
        生成的error_report.md路径
    """
    
    # 初始化默认值
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []
    if processing_stats is None:
        processing_stats = {}
    
    # 使用指定的输出文件夹或默认的 {vehicle_id}_SLOPE_output
    if output_folder is None:
        output_folder = os.path.join(vehicle_folder, f'{vehicle_id}_SLOPE_output')
    
    os.makedirs(output_folder, exist_ok=True)
    
    report_path = os.path.join(output_folder, 'error_report.md')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    status_text = '[OK] 成功完成' if processing_status else '[FAIL] 失败'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        # 标题
        f.write("# 车辆电压斜率数据处理报告\n\n")
        f.write(f"**生成时间**: {timestamp}\n")
        f.write(f"**版本**: 1.0\n\n")
        
        # 处理摘要
        f.write("## 处理摘要\n\n")
        f.write(f"- **车辆ID**: {vehicle_id}\n")
        f.write(f"- **车辆型号**: {vehicle_model}\n")
        f.write(f"- **处理状态**: {status_text}\n")
        f.write(f"- **组件总数**: {processing_stats.get('total_components', 0)}\n")
        f.write(f"- **成功处理**: {processing_stats.get('processed_components', 0)}\n")
        f.write(f"- **总工况数**: {processing_stats.get('total_conditions', 0)}\n\n")
        
        # 已完成的功能
        f.write("## 已完成的功能\n\n")
        for func in completed_functions:
            status = '[OK]' if func.get('success', False) else '[FAIL]'
            name = func.get('name', '')
            details = func.get('details', '')
            if details:
                f.write(f"{status} {name} - {details}\n")
            else:
                f.write(f"{status} {name}\n")
        f.write("\n")
        
        # 生成的文件
        if generated_files:
            f.write("## 生成的文件\n\n")
            f.write("| 文件名 | 类型 | 说明 |\n")
            f.write("|--------|------|------|\n")
            for file_info in generated_files:
                name = file_info.get('name', '')
                file_type = file_info.get('type', '')
                desc = file_info.get('description', '')
                f.write(f"| {name} | {file_type} | {desc} |\n")
            f.write("\n")
        
        # 错误和警告
        if errors:
            f.write("## 错误和警告\n\n")
            f.write("### [FAIL] 错误（处理已停止）\n\n")
            for i, error in enumerate(errors, 1):
                error_type = error.get('type', '未知')
                message = error.get('message', '')
                component = error.get('component', '')
                
                f.write(f"{i}. **{error_type}**")
                if component:
                    f.write(f" - 组件: {component}")
                f.write(f"\n   - {message}\n\n")
        
        if warnings:
            if not errors:
                f.write("## 错误和警告\n\n")
            f.write("### ⚠️ 警告（处理已继续）\n\n")
            for i, warning in enumerate(warnings, 1):
                warning_type = warning.get('type', '未知')
                message = warning.get('message', '')
                component = warning.get('component', '')
                
                f.write(f"{i}. **{warning_type}**")
                if component:
                    f.write(f" - 组件: {component}")
                f.write(f"\n   - {message}\n\n")
        
        # 处理统计
        f.write("## 处理统计\n\n")
        f.write("| 指标 | 值 |\n")
        f.write("|------|----|\n")
        f.write(f"| 总组件数 | {processing_stats.get('total_components', 0)} |\n")
        f.write(f"| 成功处理 | {processing_stats.get('processed_components', 0)} |\n")
        f.write(f"| 总工况数 | {processing_stats.get('total_conditions', 0)} |\n")
        f.write(f"| 错误数 | {len(errors)} |\n")
        f.write(f"| 警告数 | {len(warnings)} |\n")
        f.write(f"| 数据质量 | {'良好' if not errors and not warnings else '有待改进'} |\n")
        f.write("\n")
        
        # 备注
        f.write("---\n\n")
        f.write("**备注**: 本报告由 vehicle-slope-data Skill V1.0 自动生成\n")
    
    return report_path


if __name__ == '__main__':
    # 示例用法
    report_path = generate_error_report_cn(
        vehicle_folder="V0001_SLOPE",
        vehicle_id="V0001",
        vehicle_model="坦克500 Hi4-Z",
        processing_status=True,
        completed_functions=[
            {'name': '车辆信息加载', 'success': True, 'details': '27个参数'},
            {'name': '测试命名规则加载', 'success': True, 'details': '42个工况'},
            {'name': '组件数据处理', 'success': True, 'details': '390个工况'},
        ],
        generated_files=[
            {'name': 'V0001_SLOPE_summary.xlsx', 'type': 'Excel', 'description': 'V1.0格式报告，包含3个工作表'},
            {'name': 'V0001_SLOPE.db', 'type': 'SQLite', 'description': '数据库，包含4个表'},
        ],
        errors=[],
        warnings=[],
        processing_stats={
            'total_components': 10,
            'processed_components': 10,
            'total_conditions': 390
        }
    )
    
    print(f"示例报告已生成: {report_path}")
