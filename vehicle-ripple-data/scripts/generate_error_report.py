#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vehicle Ripple Data - Error Report Generator V3.1
Generates error_report.md documenting processing steps, errors, warnings, and generated files.

Version: 3.1
New Feature: Automatic error_report.md generation after processing

Usage:
    from scripts.generate_error_report import generate_error_report
    generate_error_report(vehicle_folder, processing_log, generated_files, errors, warnings)
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional


def generate_error_report(
    vehicle_folder: str,
    vehicle_id: str,
    vehicle_model: str,
    processing_status: bool,
    completed_functions: List[Dict[str, Any]],
    generated_files: List[Dict[str, str]],
    errors: Optional[List[Dict[str, str]]] = None,
    warnings: Optional[List[Dict[str, str]]] = None,
    processing_stats: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate error_report.md after processing vehicle data.
    
    Args:
        vehicle_folder: Path to vehicle folder
        vehicle_id: Vehicle identifier (e.g., V0001)
        vehicle_model: Vehicle model name
        processing_status: True if successful, False if failed
        completed_functions: List of {'name': str, 'success': bool, 'details': str}
        generated_files: List of {'name': str, 'type': str, 'description': str}
        errors: List of {'type': str, 'message': str, 'component': str}
        warnings: List of {'type': str, 'message': str, 'component': str}
        processing_stats: Dict with 'total_components', 'processed_components', 
                         'total_conditions', 'matched_conditions', etc.
    
    Returns:
        Path to generated error_report.md
    """
    
    # Initialize defaults
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []
    if processing_stats is None:
        processing_stats = {}
    """
    Generate error_report.md after processing vehicle data.
    
    Args:
        vehicle_folder: Path to vehicle folder
        vehicle_id: Vehicle identifier (e.g., V0001)
        vehicle_model: Vehicle model name
        processing_status: True if successful, False if failed
        completed_functions: List of {'name': str, 'success': bool, 'details': str}
        generated_files: List of {'name': str, 'type': str, 'description': str}
        errors: List of {'type': str, 'message': str, 'component': str}
        warnings: List of {'type': str, 'message': str, 'component': str}
        processing_stats: Dict with 'total_components', 'processed_components', 
                         'total_conditions', 'matched_conditions', etc.
    
    Returns:
        Path to generated error_report.md
    """
    
    report_path = os.path.join(vehicle_folder, 'error_report.md')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("# Vehicle Ripple Data Processing Report\n\n")
        f.write(f"**Generated**: {timestamp}\n")
        f.write(f"**Version**: 3.1\n\n")
        
        # Processing Summary
        f.write("## Processing Summary\n\n")
        f.write(f"- **Vehicle ID**: {vehicle_id}\n")
        f.write(f"- **Vehicle Model**: {vehicle_model}\n")
        f.write(f"- **Processing Status**: {'[OK] Completed Successfully' if processing_status else '[FAIL] Failed'}\n")
        
        if processing_stats:
            f.write(f"- **Total Components**: {processing_stats.get('total_components', 'N/A')}\n")
            f.write(f"- **Successfully Processed**: {processing_stats.get('processed_components', 'N/A')}\n")
            f.write(f"- **Total Test Conditions**: {processing_stats.get('total_conditions', 'N/A')}\n")
            f.write(f"- **Successfully Matched**: {processing_stats.get('matched_conditions', 'N/A')}\n")
        
        f.write(f"- **Processing Timestamp**: {timestamp}\n\n")
        
        # Completed Functions
        f.write("## Completed Functions\n\n")
        if completed_functions:
            for func in completed_functions:
                status = '[OK]' if func.get('success', False) else '[FAIL]'
                name = func.get('name', 'Unknown Function')
                details = func.get('details', '')
                f.write(f"{status} {name}")
                if details:
                    f.write(f" - {details}")
                f.write("\n")
        else:
            f.write("_No functions completed_\n")
        f.write("\n")
        
        # Generated Files
        f.write("## Generated Files\n\n")
        if generated_files:
            f.write("| File Name | Type | Description |\n")
            f.write("|-----------|------|-------------|\n")
            for file_info in generated_files:
                name = file_info.get('name', 'Unknown')
                file_type = file_info.get('type', 'Unknown')
                desc = file_info.get('description', '')
                f.write(f"| {name} | {file_type} | {desc} |\n")
            f.write("\n")
            
            # File Details
            f.write("### File Details\n\n")
            for file_info in generated_files:
                name = file_info.get('name', '')
                details = file_info.get('details', '')
                if details:
                    f.write(f"**{name}**\n")
                    f.write(f"{details}\n\n")
        else:
            f.write("_No files generated_\n\n")
        
        # Errors Section
        has_fatal = errors and any(e.get('fatal', True) for e in errors)
        if has_fatal:
            f.write("## [FAIL] Fatal Errors (Processing Stopped)\n\n")
            fatal_errors = [e for e in errors if e.get('fatal', True)]
            for i, error in enumerate(fatal_errors, 1):
                f.write(f"{i}. **{error.get('type', 'Error')}**\n")
                if error.get('component'):
                    f.write(f"   - **Component**: {error['component']}\n")
                f.write(f"   - **Message**: {error.get('message', 'Unknown error')}\n")
                if error.get('recommendation'):
                    f.write(f"   - **Recommendation**: {error['recommendation']}\n")
                f.write("\n")
        
        # Warnings Section
        if warnings:
            f.write("## ⚠️ Warnings (Processing Continued)\n\n")
            for i, warning in enumerate(warnings, 1):
                f.write(f"{i}. **{warning.get('type', 'Warning')}**")
                if warning.get('component'):
                    f.write(f" - Component: {warning['component']}")
                f.write("\n")
                f.write(f"   - **Issue**: {warning.get('message', 'Unknown warning')}\n")
                if warning.get('details'):
                    f.write(f"   - **Details**: {warning['details']}\n")
                if warning.get('impact'):
                    f.write(f"   - **Impact**: {warning['impact']}\n")
                if warning.get('recommendation'):
                    f.write(f"   - **Recommendation**: {warning['recommendation']}\n")
                f.write("\n")
        
        # Issues/Unclear Items
        f.write("## Unclear/Issue Items\n\n")
        f.write("### Issues Requiring Attention\n\n")
        
        issues_found = False
        
        # Check for encoding issues
        if warnings:
            encoding_warnings = [w for w in warnings if 'encoding' in w.get('type', '').lower()]
            if encoding_warnings:
                issues_found = True
                f.write("1. **File Encoding Issues**\n")
                f.write("   - **Issue**: Some files may have encoding problems (garbled characters)\n")
                f.write("   - **Impact**: Chinese text may not display correctly\n")
                f.write("   - **Recommendation**: Ensure all input files are saved with UTF-8 encoding\n\n")
        
        # Check for column mismatches
        if warnings:
            column_warnings = [w for w in warnings if 'column' in w.get('type', '').lower()]
            if column_warnings:
                issues_found = True
                f.write("2. **Column Mismatch in Statistics Files**\n")
                f.write("   - **Issue**: Some statistics.xlsx files have unexpected column counts\n")
                f.write("   - **Impact**: Missing data filled with null values\n")
                f.write("   - **Recommendation**: Review and standardize Excel file formats\n\n")
        
        if not issues_found:
            f.write("_No significant issues identified_\n\n")
        
        # Processing Statistics
        if processing_stats:
            f.write("## Processing Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            
            stats_mapping = [
                ('Total Components', 'total_components'),
                ('Successfully Processed', 'processed_components'),
                ('Components with Warnings', 'components_with_warnings'),
                ('Total Test Conditions', 'total_conditions'),
                ('Successfully Matched', 'matched_conditions'),
                ('Match Rate', 'match_rate'),
                ('Total Images Found', 'total_images'),
                ('Data Quality Issues', 'data_quality_issues'),
            ]
            
            for label, key in stats_mapping:
                if key in processing_stats:
                    value = processing_stats[key]
                    if isinstance(value, float):
                        value = f"{value:.1%}" if key == 'match_rate' else f"{value:.2f}"
                    f.write(f"| {label} | {value} |\n")
            
            f.write("\n")
        
        # Footer
        f.write("---\n\n")
        f.write("*This report was automatically generated by vehicle-ripple-data skill v3.1*\n")
    
    return report_path


def create_sample_error_report(vehicle_folder: str = ".") -> str:
    """Create a sample error_report.md for demonstration"""
    
    completed_functions = [
        {'name': 'Vehicle information loaded', 'success': True, 'details': '27 parameters'},
        {'name': 'Test naming rules loaded', 'success': True, 'details': '42 conditions'},
        {'name': 'Sensor naming rules loaded', 'success': True, 'details': '16 channels'},
        {'name': 'Component folders validated', 'success': True, 'details': '16 folders'},
        {'name': 'Statistics data processed', 'success': True, 'details': '390 conditions'},
        {'name': 'Images matched', 'success': True, 'details': '390 images'},
        {'name': 'SQLite database generated', 'success': True, 'details': 'V0001_RIPPLE.db'},
        {'name': 'Excel report generated', 'success': True, 'details': 'V0001_RIPPLE_summary.xlsx'},
        {'name': 'JSON data exported', 'success': True, 'details': 'V0001_RIPPLE_data.json'},
    ]
    
    generated_files = [
        {
            'name': 'V0001_RIPPLE_summary.xlsx',
            'type': 'Excel',
            'description': 'V3.0 format report with 3 sheets',
            'details': '- Vehicle Information: 27 vehicle parameters\n- Component Summary: 16 components with Unit column (A/V)\n- Detailed Results: 390 test conditions with No. (1-390), Unit, and SOC Level columns'
        },
        {
            'name': 'V0001_RIPPLE.db',
            'type': 'SQLite',
            'description': 'Database with 4 tables',
            'details': '- vehicles table: 1 record (V0001)\n- components table: 16 records\n- conditions table: 390 records\n- test_results table: 390 records with full test data'
        },
        {
            'name': 'V0001_RIPPLE_data.json',
            'type': 'JSON',
            'description': 'Structured data export',
            'details': 'Complete structured data for programmatic access including all vehicle info, components, conditions, and measurements'
        },
        {
            'name': 'error_report.md',
            'type': 'Markdown',
            'description': 'This processing report',
            'details': 'Comprehensive report of processing steps, errors, warnings, and generated files'
        },
    ]
    
    warnings = [
        {
            'type': 'Column Mismatch',
            'component': 'DCC_A',
            'message': 'Excel file has 6 columns instead of expected 7',
            'details': 'Missing column: 峰值排序',
            'impact': 'Missing data filled with null values, processing continued',
            'recommendation': 'Review statistics.xlsx and add missing column if needed'
        },
    ]
    
    processing_stats = {
        'total_components': 16,
        'processed_components': 16,
        'components_with_warnings': 1,
        'total_conditions': 390,
        'matched_conditions': 390,
        'match_rate': 1.0,
        'total_images': 390,
        'data_quality_issues': 1,
    }
    
    return generate_error_report(
        vehicle_folder=vehicle_folder,
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
    # Generate sample report for testing
    report_path = create_sample_error_report()
    print(f"Sample error report generated: {report_path}")
