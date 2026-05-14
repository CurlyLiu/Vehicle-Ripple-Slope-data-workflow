#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆纹波数据处理 - 中文错误报告生成器 V4.3
生成error_report.md记录处理步骤、错误、警告和生成的文件
所有输出文件放入{VehicleID}_RIPPLE_output文件夹

版本: 4.3
新功能:
1. V4.3: 支持分层文件夹结构，自动检测{VehID}_RIPPLE子文件夹
2. 中文错误报告
3. 所有输出放入{VehicleID}_RIPPLE_output文件夹

使用方法:
    from scripts.generate_error_report_cn import generate_error_report_cn, move_files_to_output
    
    # V4.3: 传入ripple_folder路径（RIPPLE子文件夹）
    generate_error_report_cn(ripple_folder, vehicle_id, vehicle_model, ...)
    move_files_to_output(ripple_folder, vehicle_id)
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional


def generate_error_report_cn(
    ripple_folder: str = None,
    vehicle_id: str = None,
    vehicle_model: str = None,
    processing_status: bool = None,
    completed_functions: List[Dict[str, Any]] = None,
    generated_files: List[Dict[str, str]] = None,
    errors: Optional[List[Dict[str, str]]] = None,
    warnings: Optional[List[Dict[str, str]]] = None,
    processing_stats: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    生成中文error_report.md，所有输出放入{vehicle_id}_RIPPLE_output文件夹
    
    V4.3更新: 传入RIPPLE子文件夹路径，而非父文件夹
    
    参数:
        ripple_folder: RIPPLE子文件夹路径 (如 "E:/1 项目/V0001/V0001_RIPPLE")
        vehicle_id: 车辆标识符 (如 V0001)
        vehicle_model: 车辆型号名称
        processing_status: True表示成功, False表示失败
        completed_functions: [{'name': str, 'success': bool, 'details': str}]
        generated_files: [{'name': str, 'type': str, 'description': str}]
        errors: [{'type': str, 'message': str, 'component': str}]
        warnings: [{'type': str, 'message': str, 'component': str}]
        processing_stats: {'total_components', 'processed_components', ...}
    
    返回:
        生成的error_report.md路径
    """
    
    # 兼容slope-data调用方式 (vehicle_folder参数)
    if ripple_folder is None and 'vehicle_folder' in kwargs:
        ripple_folder = kwargs['vehicle_folder']

    # 初始化默认值
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []
    if processing_stats is None:
        processing_stats = {}

    # 确定输出文件夹 (V4.3: 支持通过output_folder传入，用于slope-data)
    if 'output_folder' in kwargs and kwargs['output_folder']:
        output_folder = kwargs['output_folder']
        os.makedirs(output_folder, exist_ok=True)
    else:
        output_folder_name = f"{vehicle_id}_RIPPLE_output"
        output_folder = os.path.join(ripple_folder, output_folder_name)
        os.makedirs(output_folder, exist_ok=True)

    report_path = os.path.join(output_folder, 'error_report.md')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 根据输出路径判断数据类型
    data_type = '斜率' if '_SLOPE' in str(output_folder) else '纹波'
    status_text = '[OK] 成功完成' if processing_status else '[FAIL] 失败'

    with open(report_path, 'w', encoding='utf-8') as f:
        # 标题
        f.write(f"# 车辆{data_type}数据处理报告\n\n")
        f.write(f"**生成时间**: {timestamp}\n")
        f.write(f"**版本**: 3.2\n\n")
        
        # 处理摘要
        f.write("## 处理摘要\n\n")
        f.write(f"- **车辆ID**: {vehicle_id}\n")
        f.write(f"- **车辆型号**: {vehicle_model}\n")
        f.write(f"- **处理状态**: {status_text}\n")
        
        if processing_stats:
            f.write(f"- **组件总数**: {processing_stats.get('total_components', 'N/A')}\n")
            f.write(f"- **成功处理**: {processing_stats.get('processed_components', 'N/A')}\n")
            f.write(f"- **测试工况总数**: {processing_stats.get('total_conditions', 'N/A')}\n")
            f.write(f"- **成功匹配**: {processing_stats.get('matched_conditions', 'N/A')}\n")
        
        f.write(f"- **处理时间**: {timestamp}\n\n")
        
        # 已完成的功能
        f.write("## 已完成的功能\n\n")
        if completed_functions:
            for func in completed_functions:
                status = '[OK]' if func.get('success', False) else '[FAIL]'
                name = func.get('name', '未知功能')
                details = func.get('details', '')
                f.write(f"{status} {name}")
                if details:
                    f.write(f" - {details}")
                f.write("\n")
        else:
            f.write("_未完成任何功能_\n")
        f.write("\n")
        
        # 生成的文件
        f.write("## 生成的文件\n\n")
        if generated_files:
            f.write("| 文件名 | 类型 | 说明 |\n")
            f.write("|--------|------|------|\n")
            for file_info in generated_files:
                name = file_info.get('name', '未知')
                file_type = file_info.get('type', '未知')
                desc = file_info.get('description', '')
                f.write(f"| {name} | {file_type} | {desc} |\n")
            f.write("\n")
            
            # 文件详情
            f.write("### 文件详情\n\n")
            for file_info in generated_files:
                name = file_info.get('name', '')
                details = file_info.get('details', '')
                if details:
                    f.write(f"**{name}**\n")
                    f.write(f"{details}\n\n")
        else:
            f.write("_未生成任何文件_\n\n")
        
        # 输出文件夹说明
        f.write("### 输出位置\n\n")
        f.write(f"所有输出文件已保存至: `{output_folder}`\n\n")
        
        # 错误部分
        has_fatal = errors and any(e.get('fatal', True) for e in errors)
        if has_fatal:
            f.write("## [FAIL] 致命错误（处理已停止）\n\n")
            fatal_errors = [e for e in errors if e.get('fatal', True)]
            for i, error in enumerate(fatal_errors, 1):
                f.write(f"{i}. **{error.get('type', '错误')}**\n")
                if error.get('component'):
                    f.write(f"   - **组件**: {error['component']}\n")
                f.write(f"   - **信息**: {error.get('message', '未知错误')}\n")
                if error.get('recommendation'):
                    f.write(f"   - **建议**: {error['recommendation']}\n")
                f.write("\n")
        
        # 警告部分
        if warnings:
            f.write("## ⚠️ 警告（处理已继续）\n\n")
            for i, warning in enumerate(warnings, 1):
                f.write(f"{i}. **{warning.get('type', '警告')}**")
                if warning.get('component'):
                    f.write(f" - 组件: {warning['component']}")
                f.write("\n")
                f.write(f"   - **问题**: {warning.get('message', '未知警告')}\n")
                if warning.get('details'):
                    f.write(f"   - **详情**: {warning['details']}\n")
                if warning.get('impact'):
                    f.write(f"   - **影响**: {warning['impact']}\n")
                if warning.get('recommendation'):
                    f.write(f"   - **建议**: {warning['recommendation']}\n")
                f.write("\n")
        
        # 不清楚/问题项
        f.write("## 不清楚/问题项\n\n")
        f.write("### 需要注意的问题\n\n")
        
        issues_found = False
        
        # 检查编码问题
        if warnings:
            encoding_warnings = [w for w in warnings if 'encoding' in w.get('type', '').lower()]
            if encoding_warnings:
                issues_found = True
                f.write("1. **文件编码问题**\n")
                f.write("   - **问题**: 某些文件可能存在编码问题（乱码字符）\n")
                f.write("   - **影响**: 中文文本可能显示不正确\n")
                f.write("   - **建议**: 确保所有输入文件使用UTF-8编码保存\n\n")
        
        # 检查列不匹配
        if warnings:
            column_warnings = [w for w in warnings if 'column' in w.get('type', '').lower() or '列' in w.get('type', '')]
            if column_warnings:
                issues_found = True
                f.write("2. **统计数据文件列不匹配**\n")
                f.write("   - **问题**: 某些statistics.xlsx文件的列数与预期不符\n")
                f.write("   - **影响**: 缺失数据已用null值填充\n")
                f.write("   - **建议**: 检查并标准化Excel文件格式\n\n")
        
        if not issues_found:
            f.write("_未发现显著问题_\n\n")
        
        # 处理统计
        if processing_stats:
            f.write("## 处理统计\n\n")
            f.write("| 指标 | 数值 |\n")
            f.write("|------|------|\n")
            
            stats_mapping = [
                ('组件总数', 'total_components'),
                ('成功处理', 'processed_components'),
                ('有警告的组件', 'components_with_warnings'),
                ('测试工况总数', 'total_conditions'),
                ('成功匹配', 'matched_conditions'),
                ('匹配率', 'match_rate'),
                ('找到的图片数', 'total_images'),
                ('数据质量问题', 'data_quality_issues'),
            ]
            
            for label, key in stats_mapping:
                if key in processing_stats:
                    value = processing_stats[key]
                    if isinstance(value, float):
                        value = f"{value:.1%}" if key == 'match_rate' else f"{value:.2f}"
                    f.write(f"| {label} | {value} |\n")
            
            f.write("\n")
        
        # 页脚
        f.write("---\n\n")
        skill_name = 'vehicle-slope-data' if data_type == '斜率' else 'vehicle-ripple-data'
        f.write(f"*本报告由 {skill_name} 技能 v3.2 自动生成*\n")
    
    return report_path


def move_files_to_output(ripple_folder: str, vehicle_id: str) -> List[str]:
    """
    将所有生成的文件移动到{vehicle_id}_RIPPLE_output文件夹
    
    V4.2更新: 传入RIPPLE子文件夹路径
    
    参数:
        ripple_folder: RIPPLE子文件夹路径 (如 "E:/1 项目/V0001/V0001_RIPPLE")
        vehicle_id: 车辆ID (如 V0001)
    
    返回:
        移动的文件列表
    """
    output_folder_name = f"{vehicle_id}_RIPPLE_output"
    output_folder = os.path.join(ripple_folder, output_folder_name)
    os.makedirs(output_folder, exist_ok=True)
    
    # 要移动的文件模式
    file_patterns = [
        f'{vehicle_id}_RIPPLE_summary.xlsx',
        f'{vehicle_id}_RIPPLE.db',
        f'{vehicle_id}_RIPPLE_data.json',
        'README.md',
    ]
    
    moved_files = []
    
    for pattern in file_patterns:
        source = os.path.join(ripple_folder, pattern)
        if os.path.exists(source):
            dest = os.path.join(output_folder, pattern)
            shutil.move(source, dest)
            moved_files.append(pattern)
    
    return moved_files


def create_sample_error_report_cn(ripple_folder: str = ".") -> str:
    """创建中文示例error_report.md用于演示"""
    
    completed_functions = [
        {'name': '车辆信息已加载', 'success': True, 'details': '27个参数'},
        {'name': '测试命名规则已加载', 'success': True, 'details': '42个工况'},
        {'name': '传感器命名规则已加载', 'success': True, 'details': '14个通道'},
        {'name': '组件文件夹已验证', 'success': True, 'details': '10个文件夹'},
        {'name': '统计数据已处理', 'success': True, 'details': '390个工况'},
        {'name': '图片已匹配', 'success': True, 'details': '390张图片'},
        {'name': 'SQLite数据库已生成', 'success': True, 'details': 'V0001_RIPPLE.db'},
        {'name': 'Excel报告已生成', 'success': True, 'details': 'V0001_RIPPLE_summary.xlsx'},
        {'name': 'JSON数据已导出', 'success': True, 'details': 'V0001_RIPPLE_data.json'},
    ]
    
    generated_files = [
        {
            'name': 'V0001_RIPPLE_summary.xlsx',
            'type': 'Excel',
            'description': 'V3.0格式报告，包含3个工作表',
            'details': '- 车辆信息: 27个车辆参数\n- 组件汇总: 16个组件，含Unit列(A/V)\n- 详细结果: 390个测试工况，含No.(1-390)、Unit和SOC Level列'
        },
        {
            'name': 'V0001_RIPPLE.db',
            'type': 'SQLite',
            'description': '数据库，包含4个表',
            'details': '- vehicles表: 1条记录 (V0001)\n- components表: 16条记录\n- conditions表: 390条记录\n- test_results表: 390条记录，含完整测试数据'
        },
        {
            'name': 'V0001_RIPPLE_data.json',
            'type': 'JSON',
            'description': '结构化数据导出',
            'details': '完整的结构化数据，包括所有车辆信息、组件、工况和测量数据'
        },
    ]
    
    warnings = [
        {
            'type': '列不匹配',
            'component': 'DCC_A',
            'message': 'Excel文件有6列而不是预期的7列',
            'details': '缺失列: 峰值排序',
            'impact': '缺失数据已用null值填充，处理已继续',
            'recommendation': '检查statistics.xlsx，如需要请添加缺失的列'
        },
    ]
    
    processing_stats = {
        'total_components': 10,
        'processed_components': 10,
        'components_with_warnings': 1,
        'total_conditions': 390,
        'matched_conditions': 390,
        'match_rate': 1.0,
        'total_images': 390,
        'data_quality_issues': 1,
    }
    
    return generate_error_report_cn(
        ripple_folder=ripple_folder,
        vehicle_id='V0001',
        vehicle_model='坦克500 Hi4-Z',
        processing_status=True,
        completed_functions=completed_functions,
        generated_files=generated_files,
        errors=[],
        warnings=warnings,
        processing_stats=processing_stats
    )


if __name__ == '__main__':
    # 生成中文示例报告
    report_path = create_sample_error_report_cn()
    print(f"中文示例报告已生成: {report_path}")
