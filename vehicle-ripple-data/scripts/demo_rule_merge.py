#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例脚本: 演示命名规则合并策略

此脚本展示了如何:
1. 加载 SKILL 文件夹中的默认规则
2. 加载车辆文件夹中的自定义规则
3. 合并两个规则（自定义规则优先）
4. 使用合并后的完整规则处理数据
"""

import os
import pandas as pd

def parse_sensor_rules_from_file(filepath):
    """从文件解析传感器命名规则"""
    sensors = {}
    if not os.path.exists(filepath):
        return sensors
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                parts = line.split(':', 1)
                channel_code = parts[0].strip()
                description = parts[1].strip()
                unit = 'A' if channel_code.endswith('_A') else 'V'
                sensors[channel_code] = {
                    'name': description,
                    'unit': unit,
                    'source': 'file'
                }
    return sensors

def merge_sensor_rules(default_rules, vehicle_rules):
    """合并传感器规则 - 车辆规则优先"""
    # 从默认规则开始
    merged = default_rules.copy()
    
    # 用车辆规则覆盖/添加
    for channel_code, rule_info in vehicle_rules.items():
        merged[channel_code] = rule_info
        merged[channel_code]['source'] = 'vehicle'
    
    return merged

def main():
    # 路径配置
    SKILL_REF_DIR = r"C:\Users\31915\.claude\skills\vehicle-ripple-data\references"
    VEHICLE_FOLDER = r"D:\6 PROGRAM\00 DataBase\V0001"
    
    print("=" * 70)
    print("命名规则合并策略演示")
    print("=" * 70)
    
    # 步骤1: 加载默认规则
    print("\n[步骤1] 加载默认规则...")
    default_sensor_file = os.path.join(SKILL_REF_DIR, 'sensor_naming_rules.md')
    default_rules = parse_sensor_rules_from_file(default_sensor_file)
    print(f"  默认规则数量: {len(default_rules)}")
    print(f"  通道列表: {', '.join(sorted(default_rules.keys()))}")
    
    # 步骤2: 加载车辆规则
    print("\n[步骤2] 加载车辆文件夹规则...")
    vehicle_sensor_file = os.path.join(VEHICLE_FOLDER, 'sensor_naming_rules.md')
    vehicle_rules = parse_sensor_rules_from_file(vehicle_sensor_file)
    print(f"  车辆规则数量: {len(vehicle_rules)}")
    print(f"  通道列表: {', '.join(sorted(vehicle_rules.keys()))}")
    
    # 步骤3: 合并规则
    print("\n[步骤3] 合并规则（车辆规则优先）...")
    merged_rules = merge_sensor_rules(default_rules, vehicle_rules)
    print(f"  合并后规则数量: {len(merged_rules)}")
    print(f"  通道列表: {', '.join(sorted(merged_rules.keys()))}")
    
    # 显示来源统计
    from_default = sum(1 for r in merged_rules.values() if r.get('source') == 'file')
    from_vehicle = sum(1 for r in merged_rules.values() if r.get('source') == 'vehicle')
    print(f"\n  来源统计:")
    print(f"    - 来自默认规则: {from_default} 个")
    print(f"    - 来自车辆规则: {from_vehicle} 个")
    print(f"    - 被车辆规则覆盖: {len(vehicle_rules)} 个")
    
    # 步骤4: 验证关键通道
    print("\n[步骤4] 验证关键通道...")
    critical_channels = ['BATT_V', 'BATT_A', 'DCC_V', 'DCC_A', 
                        'Vehicle_Harness_Splitter_V', 'Vehicle_Harness_Splitter_A']
    
    for channel in critical_channels:
        if channel in merged_rules:
            source = merged_rules[channel].get('source', 'unknown')
            status = "[OK]" if source == 'vehicle' else "[OK-默认]"
            print(f"  {status} {channel}: {merged_rules[channel]['name']}")
        else:
            print(f"  [MISSING] {channel}: 缺失!")
    
    # 显示完整的合并后规则表
    print("\n[完整规则表]")
    print("-" * 70)
    print(f"{'通道代码':<30} {'组件名称':<30} {'来源':<10}")
    print("-" * 70)
    for code in sorted(merged_rules.keys()):
        rule = merged_rules[code]
        source_label = "车辆" if rule.get('source') == 'vehicle' else "默认"
        print(f"{code:<30} {rule['name']:<30} {source_label:<10}")
    
    print("\n" + "=" * 70)
    print("合并完成!")
    print("=" * 70)
    print("\n关键优势:")
    print("1. 即使车辆规则不完整，也能识别所有16个标准通道")
    print("2. 车辆可以覆盖默认规则以自定义通道定义")
    print("3. 新增组件（如BATT、DCC）无需修改车辆规则文件")
    print("=" * 70)

if __name__ == '__main__':
    main()
