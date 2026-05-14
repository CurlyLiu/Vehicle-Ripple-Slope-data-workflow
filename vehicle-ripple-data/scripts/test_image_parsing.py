#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像文件名解析验证脚本
用于验证 vehicle-ripple-data skill 中的图像文件名解析逻辑

Usage:
    python test_image_parsing.py

This script validates the critical image filename parsing logic that prevents
null image paths in the output JSON. Run this BEFORE processing vehicle data
to ensure the parsing logic is correct.
"""
import re
import sys

def parse_image_filename(filename):
    """
    解析图像文件名提取元数据
    
    标准格式：{soc}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
    坡度格式：坡度10_{soc}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
    
    示例：
    - 标准：20_直流充电暖风_ACCM_A_15.81VPP_24.06kHz-1.623A.png
    - 坡度：坡度10_32_匀速80冷风_ACCM_A_46.78VPP_17.50kHz-1.631A.png
    """
    # 检查是否是坡度工况
    if filename.startswith('坡度10_'):
        # 坡度工况：坡度10_{soc}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
        pattern = r'坡度10_(\d+)_(.+?)_(.+?)_(\d+\.?\d*)VPP_(\d+\.?\d*)kHz-([\d\.]+)([VA])\.png'
        match = re.match(pattern, filename)
        if match:
            return {
                'condition_id': '坡度10_' + match.group(1) + '_' + match.group(2),
                'condition_desc': match.group(2),
                'channel': match.group(3),
                'vpp': float(match.group(4)),
                'freq': float(match.group(5)),
                'amplitude': float(match.group(6)),
                'unit': match.group(7),
                'is_slope': True
            }
    else:
        # 标准工况：{soc}_{desc}_{channel}_{vpp}VPP_{freq}kHz-{amplitude}{unit}.png
        pattern = r'(.+?)_(.+?)_(.+?)_(\d+\.?\d*)VPP_(\d+\.?\d*)kHz-([\d\.]+)([VA])\.png'
        match = re.match(pattern, filename)
        if match:
            return {
                'condition_id': match.group(1) + '_' + match.group(2),
                'condition_desc': match.group(2),
                'channel': match.group(3),
                'vpp': float(match.group(4)),
                'freq': float(match.group(5)),
                'amplitude': float(match.group(6)),
                'unit': match.group(7),
                'is_slope': False
            }
    return None


def test_parse_standard_condition():
    """测试标准工况文件名解析"""
    test_cases = [
        {
            'filename': '20_直流充电暖风_ACCM_A_15.81VPP_24.06kHz-1.623A.png',
            'expected': {
                'condition_id': '20_直流充电暖风',
                'channel': 'ACCM_A',
                'vpp': 15.81,
                'freq': 24.06,
                'amplitude': 1.623,
                'unit': 'A',
                'is_slope': False
            }
        },
        {
            'filename': '87_超车80-140_RM_V_21.93VPP_6.00kHz-0.450V.png',
            'expected': {
                'condition_id': '87_超车80-140',
                'channel': 'RM_V',
                'vpp': 21.93,
                'freq': 6.00,
                'amplitude': 0.450,
                'unit': 'V',
                'is_slope': False
            }
        }
    ]
    
    print("=" * 60)
    print("测试 1: 标准工况文件名解析")
    print("=" * 60)
    
    all_passed = True
    for i, test in enumerate(test_cases, 1):
        result = parse_image_filename(test['filename'])
        expected = test['expected']
        
        print(f"\n测试用例 {i}:")
        print(f"  文件名: {test['filename']}")
        
        if result is None:
            print(f"  结果: FAILED - 解析失败")
            all_passed = False
            continue
            
        checks = [
            ('condition_id', result['condition_id'] == expected['condition_id']),
            ('channel', result['channel'] == expected['channel']),
            ('vpp', abs(result['vpp'] - expected['vpp']) < 0.01),
            ('freq', abs(result['freq'] - expected['freq']) < 0.01),
            ('amplitude', abs(result['amplitude'] - expected['amplitude']) < 0.001),
            ('unit', result['unit'] == expected['unit']),
            ('is_slope', result['is_slope'] == expected['is_slope'])
        ]
        
        test_passed = all(check[1] for check in checks)
        if test_passed:
            print(f"  结果: PASSED")
        else:
            print(f"  结果: FAILED")
            all_passed = False
            for name, passed in checks:
                status = "OK" if passed else "FAIL"
                print(f"    [{status}] {name}")
    
    return all_passed


def test_parse_slope_condition():
    """测试坡度工况文件名解析"""
    test_cases = [
        {
            'filename': '坡度10_32_匀速80冷风_ACCM_A_46.78VPP_17.50kHz-1.631A.png',
            'expected': {
                'condition_id': '坡度10_32_匀速80冷风',
                'channel': 'ACCM_A',
                'vpp': 46.78,
                'freq': 17.50,
                'amplitude': 1.631,
                'unit': 'A',
                'is_slope': True
            }
        },
        {
            'filename': '坡度10_80_急加速80_RM_V_21.93VPP_6.00kHz-0.450V.png',
            'expected': {
                'condition_id': '坡度10_80_急加速80',
                'channel': 'RM_V',
                'vpp': 21.93,
                'freq': 6.00,
                'amplitude': 0.450,
                'unit': 'V',
                'is_slope': True
            }
        }
    ]
    
    print("\n" + "=" * 60)
    print("测试 2: 坡度工况文件名解析")
    print("=" * 60)
    
    all_passed = True
    for i, test in enumerate(test_cases, 1):
        result = parse_image_filename(test['filename'])
        expected = test['expected']
        
        print(f"\n测试用例 {i}:")
        print(f"  文件名: {test['filename']}")
        
        if result is None:
            print(f"  结果: FAILED - 解析失败")
            all_passed = False
            continue
            
        checks = [
            ('condition_id', result['condition_id'] == expected['condition_id']),
            ('channel', result['channel'] == expected['channel']),
            ('vpp', abs(result['vpp'] - expected['vpp']) < 0.01),
            ('freq', abs(result['freq'] - expected['freq']) < 0.01),
            ('amplitude', abs(result['amplitude'] - expected['amplitude']) < 0.001),
            ('unit', result['unit'] == expected['unit']),
            ('is_slope', result['is_slope'] == expected['is_slope'])
        ]
        
        test_passed = all(check[1] for check in checks)
        if test_passed:
            print(f"  结果: PASSED")
        else:
            print(f"  结果: FAILED")
            all_passed = False
            for name, passed in checks:
                status = "OK" if passed else "FAIL"
                print(f"    [{status}] {name}")
    
    return all_passed


def test_filename_matching():
    """测试文件名与Excel condition_id匹配"""
    test_cases = [
        {
            'name': '标准工况匹配',
            'filename': '20_直流充电暖风_ACCM_A_15.81VPP_24.06kHz-1.623A.png',
            'excel_condition_id': '20_直流充电暖风',
            'should_match': True
        },
        {
            'name': '坡度工况匹配',
            'filename': '坡度10_32_匀速80冷风_ACCM_A_46.78VPP_17.50kHz-1.631A.png',
            'excel_condition_id': '坡度10_32_匀速80冷风',
            'should_match': True
        },
        {
            'name': '不匹配的情况（旧逻辑错误）',
            'filename': '20_直流充电暖风_ACCM_A_15.81VPP_24.06kHz-1.623A.png',
            'excel_condition_id': '20',  # 旧逻辑只会提取"20"
            'should_match': False
        }
    ]
    
    print("\n" + "=" * 60)
    print("测试 3: 文件名与Excel condition_id匹配")
    print("=" * 60)
    
    all_passed = True
    for i, test in enumerate(test_cases, 1):
        result = parse_image_filename(test['filename'])
        
        print(f"\n测试用例 {i}: {test['name']}")
        print(f"  文件名: {test['filename']}")
        print(f"  Excel condition_id: {test['excel_condition_id']}")
        
        if result is None:
            print(f"  结果: FAILED - 解析失败")
            all_passed = False
            continue
        
        matches = result['condition_id'] == test['excel_condition_id']
        expected_match = test['should_match']
        
        if matches == expected_match:
            print(f"  结果: PASSED")
            print(f"    解析condition_id: {result['condition_id']}")
            print(f"    匹配: {matches}")
        else:
            print(f"  结果: FAILED")
            print(f"    解析condition_id: {result['condition_id']}")
            print(f"    期望匹配: {expected_match}, 实际: {matches}")
            all_passed = False
    
    return all_passed


def main():
    """主函数：运行所有测试"""
    print("\n" + "=" * 60)
    print("图像文件名解析验证")
    print("=" * 60)
    print("\n此脚本验证图像文件名解析逻辑，防止产生 null 图像路径。\n")
    
    results = []
    results.append(("标准工况解析", test_parse_standard_condition()))
    results.append(("坡度工况解析", test_parse_slope_condition()))
    results.append(("文件名匹配", test_filename_matching()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] 所有测试通过！")
        print("=" * 60)
        print("\n图像文件名解析逻辑正确，可以安全地处理车辆数据。")
        return 0
    else:
        print("[FAIL] 部分测试失败")
        print("=" * 60)
        print("\n请修复图像文件名解析逻辑后再处理车辆数据。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
