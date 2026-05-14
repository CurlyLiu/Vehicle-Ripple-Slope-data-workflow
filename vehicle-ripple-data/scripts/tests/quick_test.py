#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速回归测试 - 验证关键修复

不依赖pytest，可直接运行
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

def test_multi_format_vehicle_info():
    """测试多格式车辆信息提取"""
    print("\n测试1: 多格式车辆信息提取")
    
    from generate_excel_report import extract_vehicle_info_value
    
    # 测试网页爬取格式（V0004使用的格式）
    vehicle_info = {
        '参数名称': 'iCAR V27 2026款',
        '长度(mm)': '5055',
        '厂商指导价(元)': '18.28万',
    }
    
    # 通过备用字段提取车型
    value = extract_vehicle_info_value(vehicle_info, ['车型'], ['参数名称'])
    assert value == 'iCAR V27 2026款', f"应该提取到'iCAR V27 2026款'，但得到'{value}'"
    print("  [OK] 网页格式字段提取正常")
    
    # 测试标准格式
    vehicle_info_std = {
        '车型': '坦克500',
        '车长mm': '5078',
    }
    value = extract_vehicle_info_value(vehicle_info_std, ['车型'], ['参数名称'])
    assert value == '坦克500', f"应该提取到'坦克500'，但得到'{value}'"
    print("  [OK] 标准格式字段提取正常")
    
    # 测试备用字段链
    vehicle_info_fallback = {
        '厂商指导价(元)': '18.28万',
    }
    value = extract_vehicle_info_value(
        vehicle_info_fallback, 
        ['指导价格（万元）', 'Price(10k CNY)'], 
        ['厂商指导价(元)']
    )
    assert value == '18.28万', f"应该提取到'18.28万'，但得到'{value}'"
    print("  [OK] 备用字段链正常工作")
    
    return True

def test_fuzzy_matching():
    """测试模糊匹配功能"""
    print("\n测试2: 模糊匹配功能")
    
    from core.condition_matcher import ConditionMatcher
    
    rules = {
        '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
        '26_停车D挡暖风': {'condition_name': '静止高温', 'soc_level': '≤40%'},
    }
    
    matcher = ConditionMatcher(rules)
    
    # 测试中文括号变体
    result = matcher.match('87_超车80-140（运动模式）')
    assert result is not None, "应该匹配中文括号变体"
    assert result.match_type == 'normalized', f"应该是normalized类型，但得到{result.match_type}"
    assert result.confidence >= 0.95, f"置信度应该>=0.95，但得到{result.confidence}"
    print("  [OK] 括号变体匹配正常 (confidence: {:.2f})".format(result.confidence))
    
    # 测试SOC不同但工况相同
    result = matcher.match('88_超车80-140(运动模式)')  # 88 vs 87
    assert result is not None, "应该匹配SOC不同的相似工况"
    assert result.condition_name == '超越加速', f"工况名应该是'超越加速'，但得到{result.condition_name}"
    print("  [OK] SOC差异匹配正常")
    
    return True

def test_excel_generation():
    """测试Excel生成（车辆信息不为空）"""
    print("\n测试3: Excel生成（车辆信息完整性）")
    
    import tempfile
    import pandas as pd
    from generate_excel_report import generate_excel_report
    
    # 构造测试数据（模拟V0004的网页格式）
    test_data = {
        'vehicle': {
            'vehicle_id': 'TEST01',
            'vehicle_info': {
                '参数名称': 'iCAR V27 2026款 200KM四驱猎鹰500',  # 网页格式
                '长度(mm)': '5055',
                '宽度(mm)': '1976',
                '厂商指导价(元)': '18.28万',
            }
        },
        'components': {
            'FM_V': {
                'component_name': 'Front Motor Voltage',
                'unit': 'V',
                'conditions': {
                    '87_test': {
                        'condition_name': 'Test',
                        'soc_level': '≥70%',
                        'time_domain': {'effective_value': 1.0, 'vpp': 0.5},
                        'frequency_domain': {
                            'peak_ranking': '1st',
                            'peak_frequency_khz': 10.0,
                            'peak_amplitude': 0.1,
                            'rms': 0.05
                        },
                        'image_path': '/path/to/image.png'
                    }
                }
            }
        },
        'metadata': {
            'total_components': 1,
            'total_conditions': 1,
            'warnings': []
        }
    }
    
    import os
    tmpdir = tempfile.mkdtemp()
    try:
        excel_path = Path(tmpdir) / "TEST01_RIPPLE_summary.xlsx"

        # 生成Excel
        try:
            generate_excel_report(test_data, str(excel_path))
            print("  [OK] Excel文件生成成功")
        except Exception as e:
            print(f"  [FAIL] Excel生成失败: {e}")
            return False

        # 验证文件存在
        assert excel_path.exists(), "Excel文件应该存在"
        print("  [OK] Excel文件存在")

        # 读取车辆信息表
        df = pd.read_excel(str(excel_path), sheet_name='Vehicle Information', header=None)

        # 验证Vehicle ID存在
        vehicle_id_rows = df[df[0] == 'Vehicle ID']
        assert not vehicle_id_rows.empty, "应该找到Vehicle ID行"
        assert vehicle_id_rows.iloc[0, 1] == 'TEST01', "Vehicle ID应该匹配"

        # 验证有数据行（不只是表头）
        assert len(df) > 3, "车辆信息表应该有数据行"

        print(f"  [OK] Excel车辆信息不为空，包含 {len(df)} 行数据")

        # 验证其他工作表
        xls = pd.ExcelFile(str(excel_path))
        expected_sheets = ['Vehicle Information', 'Component Summary', 'Detailed Results']
        for sheet in expected_sheets:
            assert sheet in xls.sheet_names, f"应该包含'{sheet}'工作表"
        print("  [OK] 所有工作表都存在")
    finally:
        # 手动清理临时目录
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    return True

def test_error_report_generation():
    """测试错误报告生成"""
    print("\n测试4: 错误报告生成")
    
    import tempfile
    from core.vehicle_processor import VehicleDataProcessor
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试目录结构
        parent_dir = Path(tmpdir) / "V9999"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V9999_RIPPLE"
        ripple_dir.mkdir()
        
        # 创建vehicle_info.md
        (parent_dir / "vehicle_info.md").write_text(
            "| 车型 | V9999 |\n|---|---|\n", encoding='utf-8'
        )
        
        # 创建组件文件夹
        (ripple_dir / "FM_V").mkdir()
        
        # 创建最小统计文件
        import pandas as pd
        df = pd.DataFrame({
            '数据名称': ['87_test'],
            '整段时域有效值': [1.0],
            '时域纹波Vpp值（V）': [0.5],
            '峰值排序': ['1st'],
            '频域最大峰值频率(KHZ)': [10.0],
            '频域最大峰值V/A': [0.1],
            '频域均方根值（rms）': [0.05]
        })
        df.to_excel(ripple_dir / "FM_V" / "statistics.xlsx", index=False)
        
        # 运行处理
        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()
        
        # 验证error_report.md生成
        report_path = processor.output_dir / "error_report.md"
        assert report_path.exists(), f"error_report.md应该生成"
        print("  [OK] error_report.md已生成")
        
        # 验证内容 (中文报告)
        content = report_path.read_text(encoding='utf-8')
        required_sections = [
            '## 处理摘要',
            '## 已完成的功能',
            '## 生成的文件',
        ]

        for section in required_sections:
            assert section in content, f"应该包含'{section}'"
        print("  [OK] 报告包含所有必要章节")
        
        # 验证生成的文件在列表中
        assert 'V9999_RIPPLE_data.json' in content, "JSON文件应该在生成的文件列表中"
        print("  [OK] 生成的文件在文件列表中")
    
    return True

def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("回归测试套件 - 验证关键修复")
    print("="*60)
    
    tests = [
        ("多格式车辆信息提取", test_multi_format_vehicle_info),
        ("模糊匹配功能", test_fuzzy_matching),
        ("Excel生成", test_excel_generation),
        ("错误报告生成", test_error_report_generation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"[FAIL] {name} 失败")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"测试结果: {passed}/{len(tests)} 通过")
    print("="*60)
    
    if failed == 0:
        print("[OK] 所有测试通过！关键修复已验证。")
        return 0
    else:
        print(f"[FAIL] {failed} 项测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
