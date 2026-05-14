#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例脚本: 处理列数不匹配的数据文件

此脚本展示了如何:
1. 检测 statistics.xlsx 文件的列数
2. 根据实际列数动态调整列名映射
3. 处理缺失列（用 None/null 填充）
4. 记录数据质量问题但继续处理
"""

import pandas as pd
import os
from pathlib import Path

def read_statistics_with_flexible_columns(filepath, component_name="Unknown"):
    """
    灵活读取统计数据，处理列数不匹配问题
    
    标准格式（7列）:
    - 数据名称, 峰值排序, 整段时域有效值, 时域纹波VPP值(V), 
      频域最大峰值频率(KHz), 频域最大峰值V/A, 频域均方根值(rms)
    
    参数:
        filepath: statistics.xlsx 文件路径
        component_name: 组件名称（用于日志记录）
    
    返回:
        DataFrame 和 数据质量报告
    """
    
    # 标准列名（7列）
    standard_columns = [
        '数据名称', '峰值排序', '整段时域有效值', '时域纹波VPP值(V)',
        '频域最大峰值频率(KHz)', '频域最大峰值V/A', '频域均方根值(rms)'
    ]
    
    # 读取原始数据（不指定列名）
    df = pd.read_excel(filepath, engine='openpyxl', header=0)
    actual_columns = len(df.columns)
    standard_count = len(standard_columns)
    
    # 数据质量报告
    quality_report = {
        'component': component_name,
        'filepath': filepath,
        'expected_columns': standard_count,
        'actual_columns': actual_columns,
        'column_mismatch': actual_columns != standard_count,
        'missing_columns': [],
        'status': 'ok'
    }
    
    if actual_columns == standard_count:
        # 标准情况：7列
        df.columns = standard_columns
        print(f"[OK] {component_name}: 标准格式（{actual_columns}列）")
        
    elif actual_columns == 6:
        # 常见情况：缺少"峰值排序"列（6列）
        # DCC_A 就是这种格式
        df.columns = [
            '数据名称', '整段时域有效值', '时域纹波VPP值(V)',
            '频域最大峰值频率(KHz)', '频域最大峰值V/A', '频域均方根值(rms)'
        ]
        # 添加缺失的列为空值
        df['峰值排序'] = None
        
        quality_report['missing_columns'] = ['峰值排序']
        quality_report['status'] = 'warning'
        
        print(f"[WARN] {component_name}: 列数不匹配（{actual_columns}/7列）")
        print(f"  缺失列: 峰值排序")
        print(f"  处理方式: 使用6列映射，缺失列填充为null")
        
    elif actual_columns < 6:
        # 严重缺失：少于6列
        quality_report['status'] = 'error'
        quality_report['error'] = f'列数过少（{actual_columns}列），无法处理'
        
        print(f"[ERROR] {component_name}: 列数严重不足（{actual_columns}列）")
        print(f"  错误: 数据文件损坏或格式不正确")
        raise ValueError(f"{component_name}: 列数过少（{actual_columns}列），无法处理")
        
    else:
        # 意外情况：多于7列
        # 使用前7列，忽略多余列
        df = df.iloc[:, :7]
        df.columns = standard_columns
        
        quality_report['status'] = 'warning'
        quality_report['extra_columns'] = actual_columns - standard_count
        
        print(f"[WARN] {component_name}: 列数过多（{actual_columns}/7列）")
        print(f"  处理方式: 仅使用前7列，忽略多余列")
    
    # 确保列顺序一致
    df = df[standard_columns]
    
    return df, quality_report


def main():
    """主函数：演示如何处理 V0001 的数据"""
    
    print("=" * 70)
    print("列数不匹配处理演示 - V0001")
    print("=" * 70)
    
    # V0001 路径
    vehicle_folder = r"D:\6 PROGRAM\00 DataBase\V0001"
    
    # 测试两个组件：一个正常，一个有问题的
    test_components = [
        ("LV_V", "正常组件（7列）"),
        ("DCC_A", "问题组件（6列，缺少峰值排序）")
    ]
    
    quality_reports = []
    
    for component_name, description in test_components:
        stats_file = os.path.join(vehicle_folder, component_name, 'statistics.xlsx')
        
        if not os.path.exists(stats_file):
            print(f"\n[FAIL] {component_name}: 文件不存在")
            continue
        
        print(f"\n{'='*70}")
        print(f"处理组件: {component_name} - {description}")
        print(f"{'='*70}")
        
        try:
            df, report = read_statistics_with_flexible_columns(stats_file, component_name)
            quality_reports.append(report)
            
            print(f"\n处理结果:")
            print(f"  工况数量: {len(df)}")
            print(f"  列数: {len(df.columns)}")
            print(f"  列名: {', '.join(df.columns.tolist())}")
            
            # 显示前3行数据示例
            print(f"\n数据示例（前3行）:")
            print(df.head(3).to_string(index=False))
            
            if report['status'] == 'warning':
                print(f"\n[WARN] 数据质量警告:")
                if report.get('missing_columns'):
                    print(f"  - 缺失列: {', '.join(report['missing_columns'])}")
                print(f"  - 这些列将填充为 null，但其他数据仍可用")
            
        except Exception as e:
            print(f"\n[ERR] 处理失败: {str(e)}")
            quality_reports.append({
                'component': component_name,
                'status': 'error',
                'error': str(e)
            })
    
    # 汇总报告
    print(f"\n{'='*70}")
    print("数据质量汇总报告")
    print(f"{'='*70}")
    
    ok_count = sum(1 for r in quality_reports if r['status'] == 'ok')
    warning_count = sum(1 for r in quality_reports if r['status'] == 'warning')
    error_count = sum(1 for r in quality_reports if r['status'] == 'error')
    
    print(f"总计组件: {len(quality_reports)}")
    print(f"  [OK] 正常: {ok_count}")
    print(f"  [WARN] 警告（可处理）: {warning_count}")
    print(f"  [ERR] 错误: {error_count}")
    
    print(f"\n详细报告:")
    for report in quality_reports:
        status_icon = "[OK]" if report['status'] == 'ok' else "[WARN]" if report['status'] == 'warning' else "[ERR]"
        print(f"  {status_icon} {report['component']}: {report['status']}")
        if report.get('missing_columns'):
            print(f"    - 缺失列: {', '.join(report['missing_columns'])}")
    
    print(f"\n{'='*70}")
    print("演示完成!")
    print(f"{'='*70}")
    print("\n关键改进:")
    print("1. 自适应列映射 - 根据实际列数调整")
    print("2. 缺失列填充 - 用 null 填充缺失数据")
    print("3. 继续处理 - 不跳过有问题的组件")
    print("4. 质量报告 - 详细记录数据问题")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
