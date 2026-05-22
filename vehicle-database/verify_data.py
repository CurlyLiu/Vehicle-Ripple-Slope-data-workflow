#!/usr/bin/env python3
"""验证数据库中的车辆信息是否完整

对比 JSON 源文件和 .db 数据库中的车辆信息，检查：
1. 车辆数量是否一致
2. 每辆车的 vehicle_info_json 是否包含完整字段
3. 独立列（如 price_wan, length_mm 等）是否有值
4. 是否有 '-' 或空值问题

Usage:
    python verify_data.py F:/Vehicle_Database/vehicle_database.db F:/Vehicle_Date
"""

import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict


def verify_database(db_path: str, source_dir: str):
    """验证数据库完整性"""
    db_path = Path(db_path)
    source_dir = Path(source_dir)

    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print("车辆数据库完整性验证报告")
    print("=" * 70)

    # 1. 统计车辆数量
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    db_count = cursor.fetchone()[0]
    print(f"\n【1】数据库车辆总数: {db_count}")

    # 2. 检查每辆车的信息完整性
    cursor.execute("SELECT * FROM vehicles ORDER BY vehicle_id")
    vehicles = cursor.fetchall()

    # 定义关键字段（中英文对照）
    key_fields = [
        ('vehicle_model', '车型'),
        ('manufacturer', '制造商'),
        ('level', '级别'),
        ('energy_type', '能源类型'),
        ('length_mm', '长度(mm)'),
        ('width_mm', '宽度(mm)'),
        ('height_mm', '高度(mm)'),
        ('wheelbase_mm', '轴距(mm)'),
        ('front_track_mm', '前轮距(mm)'),
        ('rear_track_mm', '后轮距(mm)'),
        ('min_ground_clearance_mm', '最小离地间隙(mm)'),
        ('curb_weight_kg', '整备质量(kg)'),
        ('max_weight_kg', '最大满载质量(kg)'),
        ('front_motor_max_power_kw', '前电机最大功率(kW)'),
        ('rear_motor_max_power_kw', '后电机最大功率(kW)'),
        ('front_motor_max_torque_nm', '前电机最大扭矩(N·m)'),
        ('rear_motor_max_torque_nm', '后电机最大扭矩(N·m)'),
        ('system_total_power_kw', '系统综合功率(kW)'),
        ('high_voltage_architecture', '高压架构'),
        ('battery_type', '电池类型'),
        ('battery_capacity_kwh', '电池能量(kWh)'),
        ('fast_charge_power_kw', '快充功率(kW)'),
        ('front_suspension', '前悬类型'),
        ('rear_suspension', '后悬类型'),
        ('engine_model', '发动机型号'),
        ('transmission_type', '变速箱类型'),
        ('displacement_l', '排量(L)'),
        ('engine_max_power_kw', '发动机最大净功率(kW/rpm)'),
        ('engine_max_torque_nm', '发动机最大净扭矩(N·m/rpm)'),
        ('price_wan', '指导价格（万元）'),
    ]

    print(f"\n【2】独立列字段填充情况:")
    print("-" * 50)

    field_stats = defaultdict(lambda: {'filled': 0, 'empty': 0, 'dash': 0})

    for v in vehicles:
        vehicle_id = v['vehicle_id']
        for field, cn_name in key_fields:
            val = v[field]
            if val is None:
                field_stats[field]['empty'] += 1
            elif str(val).strip() == '-':
                field_stats[field]['dash'] += 1
            else:
                field_stats[field]['filled'] += 1

    # 按填充率排序显示
    for field, cn_name in key_fields:
        stats = field_stats[field]
        total = stats['filled'] + stats['empty'] + stats['dash']
        fill_rate = stats['filled'] / total * 100 if total > 0 else 0
        status = "OK" if fill_rate >= 80 else "WARN" if fill_rate >= 50 else "MISSING"
        print(f"  [{status}] {cn_name:20s} ({field:30s}): {stats['filled']:2d}/{total} ({fill_rate:.0f}%)")

    # 3. 检查 vehicle_info_json 完整性
    print(f"\n【3】vehicle_info_json 完整性检查:")
    print("-" * 50)

    json_issues = []
    for v in vehicles:
        vehicle_id = v['vehicle_id']
        json_str = v['vehicle_info_json']

        if not json_str:
            json_issues.append(f"  {vehicle_id}: vehicle_info_json 为空!")
            continue

        try:
            info = json.loads(json_str)
            if not info or len(info) < 5:
                json_issues.append(f"  {vehicle_id}: vehicle_info_json 字段过少 ({len(info)} 个字段)")
        except json.JSONDecodeError:
            json_issues.append(f"  {vehicle_id}: vehicle_info_json JSON 解析失败!")

    if json_issues:
        for issue in json_issues:
            print(issue)
    else:
        print(f"  全部 {len(vehicles)} 辆车的 vehicle_info_json 正常")

    # 4. 对比源文件
    print(f"\n【4】与源文件对比:")
    print("-" * 50)

    if source_dir.exists():
        # 查找所有 JSON 文件
        json_files = list(source_dir.rglob("*_vehicle_info.json"))
        print(f"  源目录找到 {len(json_files)} 个 vehicle_info JSON 文件")

        # 对比每辆车
        mismatches = []
        for v in vehicles:
            vehicle_id = v['vehicle_id']
            json_str = v['vehicle_info_json']

            # 查找对应的源 JSON
            source_json = None
            for jf in json_files:
                if vehicle_id in jf.name:
                    with open(jf, 'r', encoding='utf-8') as f:
                        source_data = json.load(f)
                        source_json = source_data.get('vehicle_info', source_data)
                    break

            if source_json and json_str:
                db_json = json.loads(json_str)
                # 检查字段数量
                source_keys = set(str(k) for k in source_json.keys())
                db_keys = set(str(k) for k in db_json.keys())

                missing_in_db = source_keys - db_keys
                extra_in_db = db_keys - source_keys

                if missing_in_db:
                    mismatches.append(f"  {vehicle_id}: DB 缺少字段: {', '.join(sorted(missing_in_db))}")
                if extra_in_db:
                    pass  # DB 多出的字段不影响

        if mismatches:
            for m in mismatches:
                print(m)
        else:
            print(f"  全部 {len(vehicles)} 辆车与源文件一致")
    else:
        print(f"  源目录不存在: {source_dir}")

    # 5. 统计测试结果数量
    print(f"\n【5】测试结果统计:")
    print("-" * 50)

    cursor.execute("SELECT COUNT(*) FROM ripple_results")
    ripple_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM slope_results")
    slope_count = cursor.fetchone()[0]

    print(f"  纹波结果: {ripple_count} 条")
    print(f"  斜率结果: {slope_count} 条")

    # 每辆车的测试数据
    cursor.execute("""
        SELECT v.vehicle_id,
               COUNT(DISTINCT r.id) as ripple_count,
               COUNT(DISTINCT s.id) as slope_count
        FROM vehicles v
        LEFT JOIN ripple_results r ON v.vehicle_id = r.vehicle_id
        LEFT JOIN slope_results s ON v.vehicle_id = s.vehicle_id
        GROUP BY v.vehicle_id
        ORDER BY v.vehicle_id
    """)
    print(f"\n  每辆车测试数据:")
    for row in cursor.fetchall():
        status = "OK" if row['ripple_count'] > 0 and row['slope_count'] > 0 else "WARN"
        print(f"    [{status}] {row['vehicle_id']}: 纹波 {row['ripple_count']:3d}, 斜率 {row['slope_count']:3d}")

    conn.close()

    print("\n" + "=" * 70)
    print("验证完成")
    print("=" * 70)
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        db_path = sys.argv[1]
        source_dir = sys.argv[2]
    else:
        # 默认路径
        db_path = "F:/Vehicle_Database/vehicle_database.db"
        source_dir = "F:/Vehicle_Date"

    verify_database(db_path, source_dir)
