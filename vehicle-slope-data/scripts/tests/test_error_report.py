#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_error_report_cn.py 测试

测试内容:
- 错误报告生成
- 各种输入参数处理
- 文件输出验证
- 边界情况处理
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

from generate_error_report_cn import generate_error_report_cn


class TestGenerateErrorReport(unittest.TestCase):
    """测试错误报告生成"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_generate_success_report(self):
        """测试生成成功报告"""
        vehicle_folder = str(Path(self.temp_dir) / "V0001_SLOPE")
        Path(vehicle_folder).mkdir()

        completed_functions = [
            {'name': '车辆信息加载', 'success': True, 'details': '27个参数'},
            {'name': '组件数据处理', 'success': True, 'details': '10个组件'},
        ]
        generated_files = [
            {'name': 'V0001_SLOPE_data.json', 'type': 'JSON', 'description': '结构化数据'},
        ]
        processing_stats = {
            'total_components': 10,
            'processed_components': 10,
            'total_conditions': 100
        }

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0001",
            vehicle_model="坦克500 Hi4-Z",
            processing_status=True,
            completed_functions=completed_functions,
            generated_files=generated_files,
            errors=[],
            warnings=[],
            processing_stats=processing_stats
        )

        # 验证文件生成
        self.assertTrue(Path(report_path).exists())

        # 验证内容
        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("车辆电压斜率数据处理报告", content)
        self.assertIn("V0001", content)
        self.assertIn("坦克500 Hi4-Z", content)
        self.assertIn("[OK] 成功完成", content)

    def test_generate_failure_report(self):
        """测试生成失败报告"""
        vehicle_folder = str(Path(self.temp_dir) / "V0002_SLOPE")
        Path(vehicle_folder).mkdir()

        errors = [
            {'type': '文件缺失', 'message': '缺少statistics.xlsx', 'component': 'FM_A'},
        ]
        warnings = [
            {'type': '编码警告', 'message': '文件使用GBK编码', 'component': ''},
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0002",
            vehicle_model="测试车型",
            processing_status=False,
            completed_functions=[],
            generated_files=[],
            errors=errors,
            warnings=warnings,
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("[FAIL] 失败", content)
        self.assertIn("文件缺失", content)
        self.assertIn("编码警告", content)

    def test_generate_with_empty_lists(self):
        """测试空列表参数"""
        vehicle_folder = str(Path(self.temp_dir) / "V0003_SLOPE")
        Path(vehicle_folder).mkdir()

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0003",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=None,
            warnings=None,
            processing_stats=None
        )

        self.assertTrue(Path(report_path).exists())
        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("V0003", content)

    def test_generate_with_custom_output_folder(self):
        """测试自定义输出文件夹"""
        vehicle_folder = str(Path(self.temp_dir) / "V0004_SLOPE")
        Path(vehicle_folder).mkdir()
        custom_output = str(Path(self.temp_dir) / "custom_output")

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0004",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats={},
            output_folder=custom_output
        )

        self.assertTrue(Path(report_path).exists())
        self.assertIn("custom_output", report_path)

    def test_generate_creates_output_directory(self):
        """测试自动创建输出目录"""
        vehicle_folder = str(Path(self.temp_dir) / "V0005_SLOPE")
        Path(vehicle_folder).mkdir()
        nonexistent_output = str(Path(self.temp_dir) / "nonexistent" / "output")

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0005",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats={},
            output_folder=nonexistent_output
        )

        self.assertTrue(Path(nonexistent_output).exists())
        self.assertTrue(Path(report_path).exists())

    def test_report_content_structure(self):
        """测试报告内容结构"""
        vehicle_folder = str(Path(self.temp_dir) / "V0006_SLOPE")
        Path(vehicle_folder).mkdir()

        completed_functions = [
            {'name': '功能1', 'success': True, 'details': '详情1'},
            {'name': '功能2', 'success': False, 'details': ''},
        ]
        generated_files = [
            {'name': 'file1.json', 'type': 'JSON', 'description': '描述1'},
            {'name': 'file2.xlsx', 'type': 'Excel', 'description': '描述2'},
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0006",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=completed_functions,
            generated_files=generated_files,
            errors=[],
            warnings=[],
            processing_stats={
                'total_components': 5,
                'processed_components': 5,
                'total_conditions': 50
            }
        )

        content = Path(report_path).read_text(encoding='utf-8')

        # 验证各节存在
        self.assertIn("## 处理摘要", content)
        self.assertIn("## 已完成的功能", content)
        self.assertIn("## 生成的文件", content)
        self.assertIn("## 处理统计", content)

        # 验证表格格式
        self.assertIn("| 文件名 | 类型 | 说明 |", content)
        self.assertIn("| 指标 | 值 |", content)

    def test_report_with_only_warnings(self):
        """测试仅有警告的报告"""
        vehicle_folder = str(Path(self.temp_dir) / "V0007_SLOPE")
        Path(vehicle_folder).mkdir()

        warnings = [
            {'type': '警告1', 'message': '消息1', 'component': 'Comp1'},
            {'type': '警告2', 'message': '消息2', 'component': ''},
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0007",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=warnings,
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("### ⚠️ 警告", content)
        self.assertNotIn("### [FAIL] 错误", content)

    def test_report_with_only_errors(self):
        """测试仅有错误的报告"""
        vehicle_folder = str(Path(self.temp_dir) / "V0008_SLOPE")
        Path(vehicle_folder).mkdir()

        errors = [
            {'type': '错误1', 'message': '消息1', 'component': 'Comp1'},
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0008",
            vehicle_model="测试车型",
            processing_status=False,
            completed_functions=[],
            generated_files=[],
            errors=errors,
            warnings=[],
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("### [FAIL] 错误", content)
        self.assertNotIn("### ⚠️ 警告", content)

    def test_report_timestamp_format(self):
        """测试时间戳格式"""
        vehicle_folder = str(Path(self.temp_dir) / "V0009_SLOPE")
        Path(vehicle_folder).mkdir()

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0009",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=[],
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        # 验证时间戳格式 YYYY-MM-DD HH:MM:SS
        import re
        timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        self.assertRegex(content, timestamp_pattern)


class TestErrorReportEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_function_without_details(self):
        """测试无详情的功能项"""
        vehicle_folder = str(Path(self.temp_dir) / "V0010_SLOPE")
        Path(vehicle_folder).mkdir()

        completed_functions = [
            {'name': '功能名', 'success': True},  # 无details
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0010",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=completed_functions,
            generated_files=[],
            errors=[],
            warnings=[],
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("功能名", content)

    def test_file_without_description(self):
        """测试无描述的文件项"""
        vehicle_folder = str(Path(self.temp_dir) / "V0011_SLOPE")
        Path(vehicle_folder).mkdir()

        generated_files = [
            {'name': 'file.json', 'type': 'JSON'},  # 无description
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0011",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=[],
            generated_files=generated_files,
            errors=[],
            warnings=[],
            processing_stats={}
        )

        self.assertTrue(Path(report_path).exists())

    def test_error_without_component(self):
        """测试无组件的错误项"""
        vehicle_folder = str(Path(self.temp_dir) / "V0012_SLOPE")
        Path(vehicle_folder).mkdir()

        errors = [
            {'type': '错误类型', 'message': '错误消息'},  # 无component
        ]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0012",
            vehicle_model="测试车型",
            processing_status=False,
            completed_functions=[],
            generated_files=[],
            errors=errors,
            warnings=[],
            processing_stats={}
        )

        content = Path(report_path).read_text(encoding='utf-8')
        self.assertIn("错误类型", content)
        self.assertIn("错误消息", content)

    def test_missing_dict_keys(self):
        """测试缺失字典键"""
        vehicle_folder = str(Path(self.temp_dir) / "V0013_SLOPE")
        Path(vehicle_folder).mkdir()

        # 使用几乎为空的字典
        completed_functions = [{}]
        generated_files = [{}]
        errors = [{}]
        warnings = [{}]

        report_path = generate_error_report_cn(
            vehicle_folder=vehicle_folder,
            vehicle_id="V0013",
            vehicle_model="测试车型",
            processing_status=True,
            completed_functions=completed_functions,
            generated_files=generated_files,
            errors=errors,
            warnings=warnings,
            processing_stats={}
        )

        self.assertTrue(Path(report_path).exists())


if __name__ == '__main__':
    unittest.main()
