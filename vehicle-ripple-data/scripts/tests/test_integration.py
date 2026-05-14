#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试 - 完整流程测试

测试内容:
1. 完整处理流程
2. 多组件处理
3. 实际文件系统操作
4. 端到端数据处理
"""

import sys
import json
import sqlite3
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from core.vehicle_processor import VehicleDataProcessor
from generate_excel_report import generate_excel_report
from generate_error_report_cn import generate_error_report_cn


class TestFullProcessingWorkflow:
    """测试完整处理流程"""

    def test_process_single_component(self, tmp_path):
        """测试处理单个组件"""
        # 创建测试目录结构
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()

        # 创建vehicle_info.md
        vehicle_info_content = """| 参数 | 值 |
|---|---|
| 车型 | 坦克500 |
| 制造商 | 长城汽车 |
| 车长mm | 5078 |
"""
        (parent_dir / "vehicle_info.md").write_text(vehicle_info_content, encoding='utf-8')

        # 创建传感器命名规则
        sensor_rules = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(sensor_rules, encoding='utf-8')

        # 创建测试命名规则
        test_rules = """| 电量状态 | 工况名称 | 命名示例 |
|---|---|---|
| ≥70% | 超越加速 | 87_超车80-140(运动模式) |
"""
        (parent_dir / "test_naming_rules.md").write_text(test_rules, encoding='utf-8')

        # 创建统计数据
        stats_df = pd.DataFrame({
            '数据名称': ['87_超车80-140(运动模式)'],
            '整段时域有效值': [400.5],
            '时域纹波Vpp值（V）': [5.2],
            '峰值排序': ['1st'],
            '频域最大峰值频率(KHZ)': [10.5],
            '频域最大峰值V/A': [2.1],
            '频域均方根值（rms）': [1.5]
        })
        stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

        # 创建图片文件
        (comp_dir / "87_超车80-140_FM_V_5.2Ipp_10.5kHz_2.1V.png").write_text("fake image")

        # 运行处理
        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()

        # 验证结果
        assert result['vehicle']['vehicle_id'] == 'V0001'
        assert result['vehicle']['vehicle_info']['车型'] == '坦克500'
        assert len(result['components']) == 1
        assert 'FM_V' in result['components']

        # 验证输出文件
        output_dir = ripple_dir / "V0001_RIPPLE_output"
        assert (output_dir / "V0001_RIPPLE_data.json").exists()
        assert (output_dir / "V0001_RIPPLE.db").exists()
        assert (output_dir / "V0001_RIPPLE_summary.xlsx").exists()
        assert (output_dir / "error_report.md").exists()

    def test_process_multiple_components(self, tmp_path):
        """测试处理多个组件"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()

        # 创建多个组件
        for comp in ['FM_V', 'FM_A', 'RM_V']:
            comp_dir = ripple_dir / comp
            comp_dir.mkdir()

            stats_df = pd.DataFrame({
                '数据名称': ['87_test', '20_test'],
                '整段时域有效值': [400.5, 200.3],
                '时域纹波Vpp值（V）': [5.2, 3.1],
                '峰值排序': ['1st', '2nd'],
                '频域最大峰值频率(KHZ)': [10.5, 8.2],
                '频域最大峰值V/A': [2.1, 1.5],
                '频域均方根值（rms）': [1.5, 1.0]
            })
            stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

            (comp_dir / f"87_test_{comp}_5.2Ipp_10.5kHz_2.1V.png").write_text("fake")
            (comp_dir / f"20_test_{comp}_3.1Ipp_8.2kHz_1.5V.png").write_text("fake")

        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        sensor_rules = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
| FM_A | 前电机电流 |
| RM_V | 后电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(sensor_rules, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()

        assert len(result['components']) == 3
        assert result['metadata']['total_conditions'] == 6

    def test_process_with_slope_conditions(self, tmp_path):
        """测试处理坡度工况"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()

        # 创建包含坡度工况的统计数据
        stats_df = pd.DataFrame({
            '数据名称': ['坡度10_81_匀速80暖风', '坡度10_32_急加速'],
            '整段时域有效值': [400.5, 350.2],
            '时域纹波Vpp值（V）': [5.2, 4.8],
            '峰值排序': ['1st', '2nd'],
            '频域最大峰值频率(KHZ)': [10.5, 9.8],
            '频域最大峰值V/A': [2.1, 1.9],
            '频域均方根值（rms）': [1.5, 1.4]
        })
        stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

        (comp_dir / "坡度10_81_匀速80暖风_FM_V_5.2Ipp_10.5kHz_2.1V.png").write_text("fake")
        (comp_dir / "坡度10_32_急加速_FM_V_4.8Ipp_9.8kHz_1.9V.png").write_text("fake")

        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')
        (parent_dir / "sensor_naming_rules.md").write_text("| Channel | 描述 |\n|---|---|\n| FM_V | 前电机电压 |\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()

        # 验证SOC正确提取
        fm_v_conditions = result['components']['FM_V']['conditions']
        assert len(fm_v_conditions) == 2

        # 检查SOC等级
        for cond_id, cond_data in fm_v_conditions.items():
            if '81' in cond_id:
                assert cond_data['soc_level'] == '≥70%'
            elif '32' in cond_id:
                assert cond_data['soc_level'] == '≤40%'


class TestExcelReportIntegration:
    """测试Excel报告集成"""

    def test_excel_report_from_processor_output(self, tmp_path):
        """测试从处理器输出生成Excel报告"""
        # 创建模拟处理器输出
        test_data = {
            'vehicle': {
                'vehicle_id': 'TEST01',
                'vehicle_info': {
                    '车型': '测试车',
                    '制造商': '测试厂商',
                    '车长mm': '5000'
                }
            },
            'components': {
                'FM_V': {
                    'component_name': '前电机电压',
                    'unit': 'V',
                    'conditions': {
                        '87_超车80-140(运动模式)': {
                            'condition_name': '超越加速',
                            'soc_level': '≥70%',
                            'time_domain': {
                                'effective_value': 400.5,
                                'vpp': 5.2
                            },
                            'frequency_domain': {
                                'peak_ranking': '1st (10.5kHz)',
                                'peak_frequency_khz': 10.5,
                                'peak_amplitude': 2.1,
                                'rms': 1.5
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

        output_path = tmp_path / "TEST01_RIPPLE_summary.xlsx"
        generate_excel_report(test_data, str(output_path))

        # 验证Excel内容
        import pandas as pd
        xls = pd.ExcelFile(str(output_path))

        # 验证车辆信息表
        vehicle_df = pd.read_excel(xls, 'Vehicle Information', header=None)
        assert 'Vehicle ID' in str(vehicle_df.values)

        # 验证组件汇总表
        summary_df = pd.read_excel(xls, 'Component Summary')
        assert 'FM_V' in summary_df['Component Code'].values

        # 验证详细结果表
        details_df = pd.read_excel(xls, 'Detailed Results')
        assert len(details_df) == 1
        assert details_df.iloc[0]['Component'] == 'FM_V'


class TestErrorReportIntegration:
    """测试错误报告集成"""

    def test_error_report_from_processor(self, tmp_path):
        """测试从处理器生成错误报告"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        completed_functions = [
            {'name': '车辆信息加载', 'success': True, 'details': '27个参数'},
            {'name': '测试命名规则加载', 'success': True, 'details': '42个工况'},
            {'name': '组件处理', 'success': True, 'details': '10个组件'},
        ]

        generated_files = [
            {'name': 'V0001_RIPPLE_summary.xlsx', 'type': 'Excel', 'description': 'Excel报告'},
            {'name': 'V0001_RIPPLE.db', 'type': 'SQLite', 'description': '数据库'},
        ]

        warnings = [
            {'type': '列不匹配', 'message': 'Excel文件有6列', 'component': 'DCC_A'}
        ]

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=completed_functions,
            generated_files=generated_files,
            errors=[],
            warnings=warnings,
            processing_stats={
                'total_components': 10,
                'processed_components': 10,
                'total_conditions': 390,
                'matched_conditions': 385
            }
        )

        content = Path(report_path).read_text(encoding='utf-8')

        # 验证报告包含所有信息
        assert '车辆信息加载' in content
        assert 'V0001_RIPPLE_summary.xlsx' in content
        assert '列不匹配' in content
        assert '组件总数' in content


class TestDatabaseIntegration:
    """测试数据库集成"""

    def test_sqlite_output_content(self, tmp_path):
        """测试SQLite输出内容"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()

        stats_df = pd.DataFrame({
            '数据名称': ['87_test'],
            '整段时域有效值': [400.5],
            '时域纹波Vpp值（V）': [5.2],
            '峰值排序': ['1st'],
            '频域最大峰值频率(KHZ)': [10.5],
            '频域最大峰值V/A': [2.1],
            '频域均方根值（rms）': [1.5]
        })
        stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

        (comp_dir / "87_test_FM_V_5.2Ipp_10.5kHz_2.1V.png").write_text("fake")
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')
        (parent_dir / "sensor_naming_rules.md").write_text("| Channel | 描述 |\n|---|---|\n| FM_V | 前电机电压 |\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()

        # 验证数据库内容
        db_path = ripple_dir / "V0001_RIPPLE_output" / "V0001_RIPPLE.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM vehicles")
        vehicles = cursor.fetchall()
        assert len(vehicles) == 1
        assert vehicles[0][0] == 'V0001'

        cursor.execute("SELECT * FROM test_results")
        test_results = cursor.fetchall()
        assert len(test_results) == 1
        # 列顺序: id(0), vehicle_id(1), component_code(2), condition_id(3), time_effective_value(4), ...
        assert test_results[0][4] == 400.5  # time_effective_value

        conn.close()


class TestEdgeCasesIntegration:
    """测试边界情况集成"""

    def test_process_with_missing_images(self, tmp_path):
        """测试处理缺少图片的情况"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()

        stats_df = pd.DataFrame({
            '数据名称': ['87_test'],
            '整段时域有效值': [400.5],
            '时域纹波Vpp值（V）': [5.2],
            '峰值排序': ['1st'],
            '频域最大峰值频率(KHZ)': [10.5],
            '频域最大峰值V/A': [2.1],
            '频域均方根值（rms）': [1.5]
        })
        stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

        # 不创建图片文件
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')
        (parent_dir / "sensor_naming_rules.md").write_text("| Channel | 描述 |\n|---|---|\n| FM_V | 前电机电压 |\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()

        # 应该成功处理，但image_path为空
        assert 'FM_V' in result['components']
        condition = result['components']['FM_V']['conditions']['87_test']
        assert condition['image_path'] == ''

    def test_process_with_empty_statistics(self, tmp_path):
        """测试处理空统计数据"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()

        # 创建空的统计数据
        stats_df = pd.DataFrame()
        stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')
        (parent_dir / "sensor_naming_rules.md").write_text("| Channel | 描述 |\n|---|---|\n| FM_V | 前电机电压 |\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        # 不应该抛出异常
        result = processor.process()
        assert 'FM_V' in result['components']
        assert len(result['components']['FM_V']['conditions']) == 0

    def test_process_with_gbk_encoding(self, tmp_path):
        """测试处理GBK编码文件"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()

        # 使用GBK编码创建vehicle_info.md
        vehicle_info = "| 车型 | 测试车 |\n|---|---|\n"
        (parent_dir / "vehicle_info.md").write_text(vehicle_info, encoding='gbk')

        stats_df = pd.DataFrame({
            '数据名称': ['87_test'],
            '整段时域有效值': [400.5],
            '时域纹波Vpp值（V）': [5.2],
            '峰值排序': ['1st'],
            '频域最大峰值频率(KHZ)': [10.5],
            '频域最大峰值V/A': [2.1],
            '频域均方根值（rms）': [1.5]
        })
        stats_df.to_excel(comp_dir / "statistics.xlsx", index=False)

        (comp_dir / "87_test_FM_V_5.2Ipp_10.5kHz_2.1V.png").write_text("fake")
        (parent_dir / "sensor_naming_rules.md").write_text("| Channel | 描述 |\n|---|---|\n| FM_V | 前电机电压 |\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        result = processor.process()

        # 应该成功处理
        assert result['vehicle']['vehicle_id'] == 'V0001'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
