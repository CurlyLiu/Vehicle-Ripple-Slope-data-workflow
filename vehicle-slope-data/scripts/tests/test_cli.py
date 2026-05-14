#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli/process_slope.py 测试

测试内容:
- 参数解析
- 主函数流程
- 各种选项组合
- 错误处理
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

# 添加 cli 到路径
sys.path.insert(0, str(scripts_dir / 'cli'))

from process_slope import create_parser, main


class TestCreateParser(unittest.TestCase):
    """测试参数解析器创建"""

    def test_parser_creation(self):
        """测试解析器创建"""
        parser = create_parser()
        self.assertIsNotNone(parser)
        self.assertEqual(parser.prog, 'vehicle-slope')

    def test_required_arguments(self):
        """测试必需参数"""
        parser = create_parser()

        # 缺少 --folder 应该失败
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_folder_argument(self):
        """测试 --folder 参数"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path/to/V0001_SLOPE'])
        self.assertEqual(args.folder, '/path/to/V0001_SLOPE')

    def test_short_folder_argument(self):
        """测试 -f 短参数"""
        parser = create_parser()
        args = parser.parse_args(['-f', '/path/to/V0001_SLOPE'])
        self.assertEqual(args.folder, '/path/to/V0001_SLOPE')

    def test_validate_first_argument(self):
        """测试 --validate-first 参数"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path', '--validate-first'])
        self.assertTrue(args.validate_first)

    def test_short_validate_first_argument(self):
        """测试 -v 短参数"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path', '-v'])
        self.assertTrue(args.validate_first)

    def test_format_argument(self):
        """测试 --format 参数"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path', '--format', 'json,excel'])
        self.assertEqual(args.format, 'json,excel')

    def test_default_format(self):
        """测试默认格式"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path'])
        self.assertEqual(args.format, 'all')

    def test_output_dir_argument(self):
        """测试 --output-dir 参数"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path', '--output-dir', '/custom/output'])
        self.assertEqual(args.output_dir, '/custom/output')

    def test_verbose_argument(self):
        """测试 --verbose 参数"""
        parser = create_parser()
        args = parser.parse_args(['--folder', '/path', '--verbose'])
        self.assertTrue(args.verbose)

    def test_version_argument(self):
        """测试 --version 参数"""
        parser = create_parser()

        with self.assertRaises(SystemExit) as cm:
            parser.parse_args(['--version'])
        self.assertEqual(cm.exception.code, 0)


class TestMainFunction(unittest.TestCase):
    """测试主函数"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    @patch('process_slope.SlopeDataProcessor')
    @patch('process_slope.generate_error_report_cn')
    def test_main_success(self, mock_generate_report, mock_processor_class):
        """测试主函数成功"""
        # 模拟处理器
        mock_processor = Mock()
        mock_processor.output_dir = Path(self.temp_dir)
        mock_processor.test_rules = {'rule1': {}}
        mock_processor.sensor_rules = {'sensor1': {}}
        mock_processor.process.return_value = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {'车型': '坦克500'}
            },
            'components': {'comp1': {}},
            'metadata': {
                'total_conditions': 10,
                'warnings': []
            }
        }
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)

    def test_main_nonexistent_folder(self):
        """测试文件夹不存在"""
        test_args = ['process_slope.py', '--folder', '/nonexistent/V0001_SLOPE']
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 1)

    @patch('process_slope.SlopeValidator')
    @patch('process_slope.SlopeDataProcessor')
    @patch('process_slope.generate_error_report_cn')
    def test_main_with_validation(self, mock_generate_report, mock_processor_class, mock_validator_class):
        """测试带验证的处理"""
        # 模拟验证器
        mock_validator = Mock()
        mock_validator.validate_all.return_value = (True, [], [], [])
        mock_validator_class.return_value = mock_validator

        # 模拟处理器
        mock_processor = Mock()
        mock_processor.output_dir = Path(self.temp_dir)
        mock_processor.test_rules = {}
        mock_processor.sensor_rules = {}
        mock_processor.process.return_value = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {'车型': '坦克500'}
            },
            'components': {},
            'metadata': {'total_conditions': 0, 'warnings': []}
        }
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder), '--validate-first']
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)

    @patch('process_slope.SlopeValidator')
    def test_main_validation_failure(self, mock_validator_class):
        """测试验证失败"""
        # 模拟验证器失败
        mock_validator = Mock()
        mock_validator.validate_all.return_value = (
            False,
            [{'message': 'Test error'}],
            [],
            []
        )
        mock_validator_class.return_value = mock_validator

        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder), '--validate-first']
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 1)

    @patch('process_slope.SlopeDataProcessor')
    @patch('process_slope.generate_error_report_cn')
    def test_main_with_warnings(self, mock_generate_report, mock_processor_class):
        """测试带警告的处理"""
        mock_processor = Mock()
        mock_processor.output_dir = Path(self.temp_dir)
        mock_processor.test_rules = {}
        mock_processor.sensor_rules = {}
        mock_processor.process.return_value = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {'车型': '坦克500'}
            },
            'components': {},
            'metadata': {
                'total_conditions': 0,
                'warnings': ['Warning 1', 'Warning 2', 'Warning 3', 'Warning 4', 'Warning 5', 'Warning 6']
            }
        }
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0004_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)

    @patch('process_slope.SlopeDataProcessor')
    def test_main_processing_exception(self, mock_processor_class):
        """测试处理异常"""
        mock_processor = Mock()
        mock_processor.process.side_effect = Exception("Processing error")
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0005_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 1)

    @patch('process_slope.SlopeDataProcessor')
    def test_main_keyboard_interrupt(self, mock_processor_class):
        """测试键盘中断"""
        mock_processor = Mock()
        mock_processor.process.side_effect = KeyboardInterrupt()
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0006_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 130)

    @patch('process_slope.SlopeDataProcessor')
    @patch('process_slope.generate_error_report_cn')
    def test_main_specific_formats(self, mock_generate_report, mock_processor_class):
        """测试特定格式输出"""
        mock_processor = Mock()
        mock_processor.output_dir = Path(self.temp_dir)
        mock_processor.test_rules = {}
        mock_processor.sensor_rules = {}
        mock_processor.process.return_value = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {'车型': '坦克500'}
            },
            'components': {},
            'metadata': {'total_conditions': 0, 'warnings': []}
        }
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0007_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder), '--format', 'json,excel']
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)
            # 验证配置正确传递
            call_args = mock_processor_class.call_args
            config = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('config', {})
            # 检查是否传递了generate_json和generate_excel


class TestVehicleIdExtraction(unittest.TestCase):
    """测试车辆ID提取"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    @patch('process_slope.SlopeDataProcessor')
    @patch('process_slope.generate_error_report_cn')
    def test_extract_from_slope_folder(self, mock_generate_report, mock_processor_class):
        """测试从{SLOPE}文件夹提取ID"""
        mock_processor = Mock()
        mock_processor.output_dir = Path(self.temp_dir)
        mock_processor.test_rules = {}
        mock_processor.sensor_rules = {}
        mock_processor.process.return_value = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {'车型': '坦克500'}
            },
            'components': {},
            'metadata': {'total_conditions': 0, 'warnings': []}
        }
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)
            # 验证使用了正确的vehicle_id
            call_args = mock_processor_class.call_args
            self.assertIn(str(folder), str(call_args[0][0]))

    @patch('process_slope.SlopeDataProcessor')
    @patch('process_slope.generate_error_report_cn')
    def test_extract_from_plain_folder(self, mock_generate_report, mock_processor_class):
        """测试从普通文件夹提取ID"""
        mock_processor = Mock()
        mock_processor.output_dir = Path(self.temp_dir)
        mock_processor.test_rules = {}
        mock_processor.sensor_rules = {}
        mock_processor.process.return_value = {
            'vehicle': {
                'vehicle_id': 'V0002',
                'vehicle_info': {'车型': '坦克500'}
            },
            'components': {},
            'metadata': {'total_conditions': 0, 'warnings': []}
        }
        mock_processor_class.return_value = mock_processor

        folder = Path(self.temp_dir) / "V0002"
        folder.mkdir()

        test_args = ['process_slope.py', '--folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
