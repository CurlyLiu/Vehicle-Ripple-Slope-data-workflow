#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试套件 - 防止已知问题再次发生

测试已修复的问题：
1. 父文件夹自动检测
2. 多格式车辆信息支持
3. 输出文件完整性（包括error_report.md）
4. Excel车辆信息表不为空

运行: pytest test_regression.py -v
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

import pytest

# 导入被测试模块
try:
    from core.vehicle_processor import VehicleDataProcessor
    from core.condition_matcher import ConditionMatcher
    from generate_excel_report import generate_excel_report, extract_vehicle_info_value
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"Python路径: {sys.path}")
    raise


class TestParentFolderAutoDetection:
    """回归测试: 父文件夹自动检测功能 (Issue: 传入父文件夹创建错误输出目录)"""
    
    def test_auto_detect_ripple_subfolder(self, tmp_path):
        """测试传入父文件夹时自动检测RIPPLE子文件夹"""
        # 创建测试目录结构
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        
        # 创建必需的vehicle_info.md
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')
        
        # 创建最小化的组件结构
        (ripple_dir / "FM_V").mkdir()
        (ripple_dir / "FM_V" / "statistics.xlsx").write_bytes(b'')  # 空文件
        
        # 测试：传入父文件夹
        processor = VehicleDataProcessor(str(parent_dir))
        
        # 验证：自动检测到RIPPLE子文件夹
        assert processor.vehicle_folder.name == "V0001_RIPPLE", \
            f"应该自动检测V0001_RIPPLE，但得到{processor.vehicle_folder.name}"
        assert processor.parent_folder.name == "V0001", \
            f"父文件夹应该是V0001，但得到{processor.parent_folder.name}"
        assert processor.vehicle_id == "V0001", \
            f"车辆ID应该是V0001，但得到{processor.vehicle_id}"
    
    def test_direct_ripple_folder(self, tmp_path):
        """测试直接传入RIPPLE文件夹仍然工作"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        
        # 创建必需的vehicle_info.md在父目录
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')
        
        processor = VehicleDataProcessor(str(ripple_dir))
        
        assert processor.vehicle_folder.name == "V0001_RIPPLE"
        assert processor.vehicle_id == "V0001"


class TestMultiFormatVehicleInfo:
    """回归测试: 多格式车辆信息支持 (Issue: Excel车辆信息表为空)"""
    
    def test_extract_standard_format(self):
        """测试标准格式字段提取"""
        vehicle_info = {
            '车型': '坦克500',
            '车长mm': '5078',
            '车宽mm': '1934',
        }
        
        # 标准字段
        value = extract_vehicle_info_value(vehicle_info, ['车型'], ['参数名称'])
        assert value == '坦克500', f"应该提取到'坦克500'，但得到'{value}'"
        
        # 数字字段
        value = extract_vehicle_info_value(vehicle_info, ['车长mm'], ['长度(mm)'])
        assert value == '5078', f"应该提取到'5078'，但得到'{value}'"
    
    def test_extract_car_home_format(self):
        """测试网页爬取格式字段提取 (Issue: V0004使用此格式)"""
        vehicle_info = {
            '参数名称': 'iCAR V27 2026款',
            '长度(mm)': '5055',
            '厂商指导价(元)': '18.28万',
        }
        
        # 备用字段提取
        value = extract_vehicle_info_value(vehicle_info, ['车型'], ['参数名称'])
        assert value == 'iCAR V27 2026款', \
            f"应该通过备用字段提取到'iCAR V27 2026款'，但得到'{value}'"
        
        value = extract_vehicle_info_value(vehicle_info, ['车长mm'], ['长度(mm)'])
        assert value == '5055', f"应该映射到'5055'，但得到'{value}'"
    
    def test_fallback_chain(self):
        """测试多层级备用字段链"""
        vehicle_info = {
            '厂商指导价(元)': '18.28万',
        }
        
        # 第三优先级提取
        value = extract_vehicle_info_value(
            vehicle_info, 
            ['指导价格（万元）', 'Price(10k CNY)'], 
            ['厂商指导价(元)']
        )
        assert value == '18.28万', f"应该提取到'18.28万'，但得到'{value}'"


class TestOutputCompleteness:
    """回归测试: 输出文件完整性 (Issue: 缺少error_report.md)"""
    
    def test_all_output_files_exist(self, tmp_path):
        """测试所有输出文件都生成"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # 构造测试数据
        test_data = {
            'vehicle': {
                'vehicle_id': 'TEST01',
                'vehicle_info': {'车型': 'Test Car'}
            },
            'components': {
                'FM_V': {
                    'component_name': 'Front Motor Voltage',
                    'unit': 'V',
                    'conditions': {
                        '87_test': {
                            'condition_name': 'Test Condition',
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
        
        # 生成Excel
        excel_path = output_dir / "TEST01_RIPPLE_summary.xlsx"
        generate_excel_report(test_data, str(excel_path))
        
        # 验证文件存在
        assert excel_path.exists(), "Excel文件应该生成"
        
        # 验证Excel包含所有工作表
        import pandas as pd
        xls = pd.ExcelFile(str(excel_path))
        expected_sheets = ['Vehicle Information', 'Component Summary', 'Detailed Results']
        for sheet in expected_sheets:
            assert sheet in xls.sheet_names, f"Excel应该包含'{sheet}'工作表"
    
    def test_excel_vehicle_info_not_empty(self, tmp_path):
        """测试Excel车辆信息表不为空"""
        test_data = {
            'vehicle': {
                'vehicle_id': 'TEST01',
                'vehicle_info': {
                    '车型': 'Test Car Model',  # 使用标准格式
                    '车长mm': '5000',
                }
            },
            'components': {},
            'metadata': {'total_components': 0, 'total_conditions': 0, 'warnings': []}
        }

        excel_path = tmp_path / "TEST01_RIPPLE_summary.xlsx"
        generate_excel_report(test_data, str(excel_path))

        # 读取车辆信息表
        import pandas as pd
        df = pd.read_excel(str(excel_path), sheet_name='Vehicle Information', header=None)

        # 验证Vehicle ID存在
        vehicle_id_row = df[df[0] == 'Vehicle ID']
        assert not vehicle_id_row.empty, "应该找到Vehicle ID行"
        assert vehicle_id_row.iloc[0, 1] == 'TEST01', "Vehicle ID应该匹配"

        # 验证有数据行（不只是表头）
        assert len(df) > 3, "车辆信息表应该有数据行"


class TestErrorReportGeneration:
    """回归测试: 错误报告生成功能"""
    
    def test_error_report_content(self, tmp_path):
        """测试错误报告包含必要章节"""
        from core.vehicle_processor import VehicleDataProcessor
        
        # 创建最小化测试环境
        parent_dir = tmp_path / "V9999"
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
        assert report_path.exists(), f"error_report.md应该生成在{report_path}"
        
        # 验证内容 (中文报告)
        content = report_path.read_text(encoding='utf-8')
        required_sections = [
            '## 处理摘要',
            '## 已完成的功能',
            '## 生成的文件',
        ]

        for section in required_sections:
            assert section in content, f"错误报告应该包含'{section}'"

        # error_report.md 本身不会出现在文件列表中，因为它是在生成文件列表之后创建的
        assert 'V9999_RIPPLE_data.json' in content


class TestFuzzyMatchingEdgeCases:
    """回归测试: 模糊匹配边界情况"""
    
    def test_bracket_variants(self):
        """测试括号变体匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
        }
        
        matcher = ConditionMatcher(rules)
        
        # 中文括号
        result = matcher.match('87_超车80-140（运动模式）')
        assert result is not None, "应该匹配中文括号变体"
        assert result.match_type == 'normalized', f"应该是normalized类型，但得到{result.match_type}"
        assert result.confidence >= 0.95, f"置信度应该>=0.95，但得到{result.confidence}"
    
    def test_typo_tolerance(self):
        """测试拼写容错"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
        }
        
        matcher = ConditionMatcher(rules)
        
        # 轻微拼写错误（一个字符差异）
        result = matcher.match('87_超车80-140(sprot)')  # sprot vs sport
        assert result is not None, "应该容忍轻微拼写错误"
        assert result.confidence >= 0.90, f"置信度应该>=0.90，但得到{result.confidence}"


class TestDataValidation:
    """回归测试: 数据验证"""
    
    def test_missing_vehicle_info(self, tmp_path):
        """测试缺少vehicle_info时抛出错误"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        
        processor = VehicleDataProcessor(str(ripple_dir))
        
        with pytest.raises(FileNotFoundError) as exc_info:
            processor.process()
        
        assert 'vehicle_info' in str(exc_info.value).lower() or '未找到' in str(exc_info.value), \
            f"错误信息应该提及vehicle_info，但得到: {exc_info.value}"


def run_quick_tests():
    """快速测试 - 验证核心功能"""
    print("\n" + "="*60)
    print("运行快速回归测试")
    print("="*60)
    
    # 测试1: 多格式字段提取
    print("\n测试1: 多格式字段提取")
    vehicle_info = {'参数名称': 'Test Car', '长度(mm)': '5000'}
    value = extract_vehicle_info_value(vehicle_info, ['车型'], ['参数名称'])
    assert value == 'Test Car', f"测试1失败: {value}"
    print("[OK] 通过")
    
    # 测试2: 括号变体匹配
    print("\n测试2: 括号变体匹配")
    rules = {'87_test(abc)': {'condition_name': 'Test'}}
    matcher = ConditionMatcher(rules)
    result = matcher.match('87_test（abc）')
    assert result is not None and result.match_type == 'normalized', "测试2失败"
    print("[OK] 通过")
    
    # 测试3: 备用字段链
    print("\n测试3: 备用字段链")
    vehicle_info = {'厂商指导价(元)': '18万'}
    value = extract_vehicle_info_value(
        vehicle_info, 
        ['指导价格（万元）'], 
        ['厂商指导价(元)']
    )
    assert value == '18万', f"测试3失败: {value}"
    print("[OK] 通过")
    
    print("\n" + "="*60)
    print("[OK] 所有快速测试通过！")
    print("="*60)
    return True


if __name__ == '__main__':
    # 可以独立运行快速测试
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        run_quick_tests()
    else:
        # 运行pytest
        pytest.main([__file__, '-v'])
