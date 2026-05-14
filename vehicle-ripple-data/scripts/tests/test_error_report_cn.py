#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Report CN 单元测试

测试内容:
1. 错误报告生成
2. 文件移动功能
3. 处理统计信息
4. 错误和警告格式化
5. 示例报告生成
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_error_report_cn import (
    generate_error_report_cn,
    move_files_to_output,
    create_sample_error_report_cn
)


class TestGenerateErrorReport:
    """测试错误报告生成"""

    def test_generate_basic_report(self, tmp_path):
        """测试生成基本报告"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[
                {'name': '车辆信息加载', 'success': True, 'details': '27个参数'},
            ],
            generated_files=[
                {'name': 'V0001_RIPPLE_summary.xlsx', 'type': 'Excel', 'description': 'Excel报告'},
            ],
            errors=[],
            warnings=[],
            processing_stats={
                'total_components': 10,
                'processed_components': 10,
                'total_conditions': 390
            }
        )

        assert Path(report_path).exists()

        # 验证报告内容
        content = Path(report_path).read_text(encoding='utf-8')
        assert '车辆纹波数据处理报告' in content
        assert 'V0001' in content
        assert '坦克500' in content
        assert '成功完成' in content

    def test_generate_report_with_errors(self, tmp_path):
        """测试生成包含错误的报告"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        errors = [
            {
                'type': '文件缺失',
                'message': '未找到vehicle_info.md',
                'component': '全局',
                'fatal': True,
                'recommendation': '请添加vehicle_info.md文件'
            }
        ]

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=False,
            completed_functions=[],
            generated_files=[],
            errors=errors,
            warnings=[],
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        assert '致命错误' in content
        assert '文件缺失' in content
        assert '未找到vehicle_info.md' in content
        assert '失败' in content

    def test_generate_report_with_warnings(self, tmp_path):
        """测试生成包含警告的报告"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        warnings = [
            {
                'type': '列不匹配',
                'message': 'Excel文件有6列而不是预期的7列',
                'component': 'DCC_A',
                'details': '缺失列: 峰值排序',
                'impact': '缺失数据已用null值填充',
                'recommendation': '检查statistics.xlsx'
            }
        ]

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[
                {'name': '车辆信息加载', 'success': True, 'details': '27个参数'},
            ],
            generated_files=[],
            errors=[],
            warnings=warnings,
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        assert '警告' in content
        assert '列不匹配' in content
        assert 'DCC_A' in content

    def test_generate_report_with_processing_stats(self, tmp_path):
        """测试生成包含处理统计的报告"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        processing_stats = {
            'total_components': 10,
            'processed_components': 10,
            'components_with_warnings': 1,
            'total_conditions': 390,
            'matched_conditions': 385,
            'match_rate': 0.987,
            'total_images': 390,
            'data_quality_issues': 2
        }

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats=processing_stats
        )

        content = Path(report_path).read_text(encoding='utf-8')
        assert '处理统计' in content
        assert '组件总数' in content
        assert '10' in content
        assert '390' in content

    def test_report_output_location(self, tmp_path):
        """测试报告输出位置"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats={}
        )

        expected_path = ripple_folder / "V0001_RIPPLE_output" / "error_report.md"
        assert Path(report_path) == expected_path
        assert expected_path.exists()


class TestMoveFilesToOutput:
    """测试文件移动功能"""

    def test_move_files_success(self, tmp_path):
        """测试成功移动文件"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        # 创建测试文件
        (ripple_folder / "V0001_RIPPLE_summary.xlsx").write_text("fake excel")
        (ripple_folder / "V0001_RIPPLE.db").write_text("fake db")
        (ripple_folder / "V0001_RIPPLE_data.json").write_text("fake json")
        (ripple_folder / "README.md").write_text("fake readme")

        moved_files = move_files_to_output(str(ripple_folder), 'V0001')

        output_folder = ripple_folder / "V0001_RIPPLE_output"
        assert output_folder.exists()
        assert (output_folder / "V0001_RIPPLE_summary.xlsx").exists()
        assert (output_folder / "V0001_RIPPLE.db").exists()
        assert (output_folder / "V0001_RIPPLE_data.json").exists()
        assert (output_folder / "README.md").exists()

        assert 'V0001_RIPPLE_summary.xlsx' in moved_files
        assert 'V0001_RIPPLE.db' in moved_files

    def test_move_files_partial(self, tmp_path):
        """测试部分文件移动"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        # 只创建部分文件
        (ripple_folder / "V0001_RIPPLE_summary.xlsx").write_text("fake excel")
        # 不创建其他文件

        moved_files = move_files_to_output(str(ripple_folder), 'V0001')

        assert len(moved_files) == 1
        assert 'V0001_RIPPLE_summary.xlsx' in moved_files

    def test_move_files_none_exist(self, tmp_path):
        """测试没有文件可移动"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        moved_files = move_files_to_output(str(ripple_folder), 'V0001')

        assert len(moved_files) == 0
        assert (ripple_folder / "V0001_RIPPLE_output").exists()


class TestSampleReportGeneration:
    """测试示例报告生成"""

    def test_create_sample_report(self, tmp_path):
        """测试创建示例报告"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        report_path = create_sample_error_report_cn(str(ripple_folder))

        assert Path(report_path).exists()

        content = Path(report_path).read_text(encoding='utf-8')
        assert 'V0001' in content
        assert '坦克500 Hi4-Z' in content
        assert '车辆信息已加载' in content
        assert 'V0001_RIPPLE_summary.xlsx' in content

    def test_sample_report_structure(self, tmp_path):
        """测试示例报告结构"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        report_path = create_sample_error_report_cn(str(ripple_folder))
        content = Path(report_path).read_text(encoding='utf-8')

        # 验证所有必要章节
        assert '处理摘要' in content
        assert '已完成的功能' in content
        assert '生成的文件' in content
        assert '处理统计' in content


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_lists(self, tmp_path):
        """测试空列表处理"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=None,
            warnings=None,
            processing_stats=None
        )

        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding='utf-8')
        assert '未完成任何功能' in content or '生成的文件' in content

    def test_long_strings(self, tmp_path):
        """测试长字符串处理"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        long_function = {
            'name': '测试功能' * 50,
            'success': True,
            'details': '详情' * 100
        }

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[long_function],
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats={}
        )

        assert Path(report_path).exists()

    def test_special_characters(self, tmp_path):
        """测试特殊字符处理"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        special_warning = {
            'type': '特殊<字符>测试',
            'message': '消息|包含|管道符',
            'component': '组件&名称'
        }

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=[special_warning],
            processing_stats={}
        )

        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding='utf-8')
        assert '特殊' in content

    def test_non_fatal_errors(self, tmp_path):
        """测试非致命错误"""
        ripple_folder = tmp_path / "V0001_RIPPLE"
        ripple_folder.mkdir()

        non_fatal_errors = [
            {
                'type': '非致命错误',
                'message': '这是一个非致命错误',
                'component': '测试组件',
                'fatal': False
            }
        ]

        report_path = generate_error_report_cn(
            ripple_folder=str(ripple_folder),
            vehicle_id='V0001',
            vehicle_model='坦克500',
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=non_fatal_errors,
            warnings=[],
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        # 非致命错误不应该出现在致命错误章节
        assert '致命错误' not in content or '非致命错误' not in content.split('致命错误')[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
