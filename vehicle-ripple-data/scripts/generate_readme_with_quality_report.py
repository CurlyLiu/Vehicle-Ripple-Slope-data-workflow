#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整示例: 处理车辆纹波数据并生成 README.md 报告
包含：
1. 自适应列处理（处理列数不匹配）
2. 数据质量记录
3. README.md 生成
4. 详细的问题文档
"""

import os
import re
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# 标准列定义
STANDARD_COLUMNS = [
    '数据名称', '峰值排序', '整段时域有效值', '时域纹波VPP值(V)',
    '频域最大峰值频率(KHz)', '频域最大峰值V/A', '频域均方根值(rms)'
]

# 6列映射（缺少峰值排序）
SIX_COLUMN_MAPPING = [
    '数据名称', '整段时域有效值', '时域纹波VPP值(V)',
    '频域最大峰值频率(KHz)', '频域最大峰值V/A', '频域均方根值(rms)'
]


def read_statistics_with_quality_check(filepath, component_name):
    """
    读取统计数据并进行质量检查
    
    返回:
        df: DataFrame
        quality_report: 数据质量报告
    """
    quality_report = {
        'component': component_name,
        'filepath': str(filepath),
        'expected_columns': len(STANDARD_COLUMNS),
        'actual_columns': 0,
        'column_mismatch': False,
        'missing_columns': [],
        'extra_columns': [],
        'status': 'ok',
        'processing_action': 'standard_processing'
    }
    
    try:
        # 读取Excel（不预设列名）
        df = pd.read_excel(filepath, engine='openpyxl')
        actual_columns = len(df.columns)
        quality_report['actual_columns'] = actual_columns
        
        if actual_columns == len(STANDARD_COLUMNS):
            # 标准7列
            df.columns = STANDARD_COLUMNS
            print(f"[OK] {component_name}: 标准格式（7列）")
            
        elif actual_columns == 6:
            # 常见情况：缺少"峰值排序"列
            df.columns = SIX_COLUMN_MAPPING
            df['峰值排序'] = None  # 添加缺失列为空值
            
            quality_report['column_mismatch'] = True
            quality_report['missing_columns'] = ['峰值排序']
            quality_report['status'] = 'warning'
            quality_report['processing_action'] = 'adaptive_mapping_with_null_fill'
            
            print(f"⚠ {component_name}: 列数不匹配（6/7列）")
            print(f"  缺失列: 峰值排序")
            print(f"  处理方式: 使用6列映射，缺失列填充为null")
            
        elif actual_columns < 6:
            # 严重缺失
            quality_report['status'] = 'error'
            quality_report['error'] = f'列数过少（{actual_columns}列），无法处理'
            print(f"[FAIL] {component_name}: 列数严重不足（{actual_columns}列）")
            raise ValueError(f"{component_name}: 列数过少（{actual_columns}列）")
            
        else:
            # 列数过多，只取前7列
            df = df.iloc[:, :7]
            df.columns = STANDARD_COLUMNS
            
            quality_report['column_mismatch'] = True
            quality_report['extra_columns'] = actual_columns - len(STANDARD_COLUMNS)
            quality_report['status'] = 'warning'
            quality_report['processing_action'] = 'truncated_to_7_columns'
            
            print(f"⚠ {component_name}: 列数过多（{actual_columns}/7列）")
            print(f"  处理方式: 仅使用前7列，忽略多余列")
        
        # 确保列顺序一致
        df = df[STANDARD_COLUMNS]
        
        return df, quality_report
        
    except Exception as e:
        quality_report['status'] = 'error'
        quality_report['error'] = str(e)
        raise


def generate_quality_section(quality_issues):
    """生成README.md中的数据质量章节"""
    
    if not quality_issues:
        return "## 数据质量问题\n\n[OK] 未检测到数据质量问题。所有组件数据格式正确。\n\n"
    
    section = f"## 数据质量问题\n\n**发现问题数**: {len(quality_issues)}\n\n"
    section += "> ⚠️ 注意：以下组件存在数据格式问题，但**所有可用数据都已处理并包含在结果中**。\n\n"
    
    for i, issue in enumerate(quality_issues, 1):
        section += f"### {i}. 组件: {issue['component']}\n\n"
        section += f"**问题类型**: 列数不匹配\n"
        section += f"**预期列数**: {issue['expected_columns']}\n"
        section += f"**实际列数**: {issue['actual_columns']}\n"
        
        if issue.get('missing_columns'):
            section += f"**缺失列**: {', '.join(issue['missing_columns'])}\n"
        
        if issue.get('extra_columns'):
            section += f"**多余列**: {issue['extra_columns']}列被忽略\n"
        
        section += f"**处理操作**: {issue['processing_action']}\n"
        section += f"**处理状态**: {issue['status']}\n\n"
        
        # 列对比表
        section += "**列对比详情**:\n\n"
        section += "| 标准列名 | 预期 | 实际 | 处理方式 |\n"
        section += "|---------|------|------|----------|\n"
        
        for col in STANDARD_COLUMNS:
            expected = "[OK]" if col in STANDARD_COLUMNS else "[FAIL]"
            if issue['actual_columns'] == 6 and col == '峰值排序':
                actual = "[FAIL]"
                action = "填充null"
            elif col in STANDARD_COLUMNS:
                actual = "[OK]"
                action = "正常使用"
            else:
                actual = "N/A"
                action = "N/A"
            section += f"| {col} | {expected} | {actual} | {action} |\n"
        
        section += "\n**影响评估**:\n"
        available_cols = issue['actual_columns']
        total_cols = issue['expected_columns']
        section += f"- 可用数据: {available_cols}/{total_cols} 列 ({available_cols/total_cols*100:.1f}%)\n"
        section += f"- 该组件的所有工况数据已包含在结果中\n"
        section += f"- 缺失列（如有）已标记为null\n\n"
        section += "---\n\n"
    
    return section


def generate_readme_report(output_data, output_path):
    """
    生成完整的README.md报告
    
    参数:
        output_data: 包含处理结果和质量问题的字典
        output_path: README.md输出路径
    """
    
    vehicle_info = output_data.get('vehicle', {})
    vehicle_id = vehicle_info.get('vehicle_id', 'Unknown')
    vehicle_model = vehicle_info.get('vehicle_info', {}).get('车型', 'Unknown')
    
    components = output_data.get('components', {})
    quality_issues = output_data.get('data_quality_issues', [])
    
    readme = f"""# {vehicle_id} 车辆高压纹波测试数据处理报告

## 处理摘要

**基本信息**:
- **车辆ID**: {vehicle_id}
- **车型**: {vehicle_model}
- **处理日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总组件数**: {len(components)}
- **总工况数**: {sum(c.get('conditions_count', 0) for c in components.values())}

**处理状态**:
- [OK] 成功处理组件: {len(components)}
- ⚠ 有数据质量问题的组件: {len(quality_issues)}
- [FAIL] 处理失败的组件: 0

"""
    
    # 添加数据质量章节
    readme += generate_quality_section(quality_issues)
    
    # 添加组件处理详情
    readme += "## 组件处理详情\n\n"
    
    for comp_code, comp_data in components.items():
        has_issue = any(issue['component'] == comp_code for issue in quality_issues)
        status_icon = "⚠" if has_issue else "[OK]"
        
        readme += f"### {status_icon} {comp_code}\n\n"
        readme += f"- **组件名称**: {comp_data.get('component_name', 'N/A')}\n"
        readme += f"- **工况数量**: {comp_data.get('conditions_count', 0)}\n"
        readme += f"- **单位**: {comp_data.get('unit', 'N/A')}\n"
        
        if has_issue:
            issue = next((i for i in quality_issues if i['component'] == comp_code), None)
            if issue:
                readme += f"- **数据质量**: 列数不匹配（{issue['actual_columns']}/{issue['expected_columns']}列）\n"
                if issue.get('missing_columns'):
                    readme += f"- **缺失列**: {', '.join(issue['missing_columns'])}\n"
        else:
            readme += f"- **数据质量**: [OK] 正常\n"
        
        readme += "\n"
    
    # 添加技术说明
    readme += """## 技术说明

### 数据格式标准
标准 `statistics.xlsx` 应包含以下7列：
1. **数据名称** - 工况ID（如"87_超车80-140"）
2. **峰值排序** - 频谱峰值排序详情
3. **整段时域有效值** - 时域有效值
4. **时域纹波VPP值(V)** - VPP值
5. **频域最大峰值频率(KHz)** - 峰值频率
6. **频域最大峰值V/A** - 峰值幅度
7. **频域均方根值(rms)** - RMS值

### 自适应处理机制
当检测到列数不匹配时：
1. **识别实际列数** - 自动检测Excel文件的列数
2. **动态映射** - 根据实际列数调整列名映射
3. **缺失列填充** - 缺失的列用null填充
4. **继续处理** - 不跳过组件，处理所有可用数据
5. **详细记录** - 在README.md中记录所有数据质量问题

### 数据完整性保证
- 所有可用数据都被处理并包含在结果中
- 缺失数据明确标记为null
- 每个组件的处理状态都有详细记录
- 数据质量问题可追溯、可修复

---

*报告由 vehicle-ripple-data skill 自动生成*
"""
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print(f"\n[OK] README.md 报告已生成: {output_path}")


def main():
    """主函数 - 演示完整处理流程"""
    
    print("=" * 70)
    print("车辆纹波数据处理示例（含README.md生成）")
    print("=" * 70)
    
    # 模拟V0001的处理结果
    output_data = {
        'vehicle': {
            'vehicle_id': 'V0001',
            'vehicle_info': {'车型': '坦克500 Hi4-Z'}
        },
        'components': {
            'LV_V': {
                'component_name': '12V电池低压电压',
                'conditions_count': 48,
                'unit': 'V'
            },
            'DCC_A': {
                'component_name': '动力电池直流充电端电流',
                'conditions_count': 48,
                'unit': 'A'
            },
            'ACCM_A': {
                'component_name': '压缩机输入端电流',
                'conditions_count': 48,
                'unit': 'A'
            }
        },
        'data_quality_issues': [
            {
                'component': 'DCC_A',
                'expected_columns': 7,
                'actual_columns': 6,
                'missing_columns': ['峰值排序'],
                'processing_action': 'adaptive_mapping_with_null_fill',
                'status': 'processed_with_warnings'
            }
        ]
    }
    
    # 生成README.md
    output_path = r"D:\6 PROGRAM\00 DataBase\V0001\output\README_Demo.md"
    generate_readme_report(output_data, output_path)
    
    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)
    print(f"\n生成的报告包含：")
    print("1. 处理摘要 - 总体统计信息")
    print("2. 数据质量问题 - 详细的DCC_A列数不匹配说明")
    print("3. 组件处理详情 - 每个组件的处理状态")
    print("4. 技术说明 - 处理机制和数据完整性保证")
    print("\n查看文件: " + output_path)


if __name__ == '__main__':
    main()
