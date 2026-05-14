#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_excel_report.py 测试

测试内容:
- Excel报告生成
- 各工作表填充
- 命令行接口
"""

import unittest
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

# 添加 ripple-data 到路径
ripple_path = scripts_dir.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))

# Mock the config import before importing generate_excel_report
sys.modules['config'] = Mock()
sys.modules['config'].SlopeConfigManager = Mock
sys.modules['config'].get_slope_config_manager = Mock(return_value=Mock(load=lambda x: {}))

from generate_excel_report import generate_excel_report, main


class TestGenerateExcelReport(unittest.TestCase):
    """测试Excel报告生成功能"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_generate_without_config(self):
        """测试不使用配置生成（传统方式）"""
        test_data = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {'车型': '坦克500', '制造商': '长城'}
            },
            'components': {
                'FM_A': {
                    'component_name': '前端模块电流',
                    'unit': 'A',
                    'conditions_count': 2,
                    'conditions': {
                        '87_超车': {
                            'condition_name': '超车',
                            'soc_level': '高电量',
                            'slope': {
                                'max_value': 1.5,
                                'min_value': -0.5,
                                'max_abs_value': 1.5
                            },
                            'image_path': '/path/to/image.png'
                        }
                    }
                }
            }
        }
        output_path = str(Path(self.temp_dir) / 'test.xlsx')

        generate_excel_report(test_data, output_path, use_config=False)

        # 验证文件生成
        self.assertTrue(Path(output_path).exists())

        # 验证内容
        with pd.ExcelFile(output_path) as xls:
            self.assertIn('Vehicle Information', xls.sheet_names)
            self.assertIn('Component Summary', xls.sheet_names)
            self.assertIn('Detailed Results', xls.sheet_names)

    def test_generate_empty_data(self):
        """测试空数据生成"""
        test_data = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {}
            },
            'components': {}
        }
        output_path = str(Path(self.temp_dir) / 'empty.xlsx')

        generate_excel_report(test_data, output_path, use_config=False)
        self.assertTrue(Path(output_path).exists())


class TestMainFunction(unittest.TestCase):
    """测试主函数"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    @patch('generate_excel_report.generate_excel_report')
    @patch('generate_excel_report.Path.exists')
    def test_main_with_input_json(self, mock_exists, mock_generate):
        """测试使用--input-json参数"""
        mock_exists.return_value = True
        mock_generate.return_value = None

        json_file = Path(self.temp_dir) / 'data.json'
        json_file.write_text(json.dumps({'test': 'data'}), encoding='utf-8')
        output_file = Path(self.temp_dir) / 'output.xlsx'

        test_args = [
            'generate_excel_report.py',
            '--input-json', str(json_file),
            '--output-excel', str(output_file)
        ]

        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)

    @patch('generate_excel_report.generate_excel_report')
    @patch('generate_excel_report.Path.exists')
    def test_main_with_vehicle_folder(self, mock_exists, mock_generate):
        """测试使用--vehicle-folder参数"""
        mock_exists.return_value = True
        mock_generate.return_value = None

        vehicle_folder = Path(self.temp_dir) / 'V0001_SLOPE'
        vehicle_folder.mkdir()
        output_folder = vehicle_folder / 'V0001_SLOPE_output'
        output_folder.mkdir()
        json_file = output_folder / 'V0001_SLOPE_data.json'
        json_file.write_text(json.dumps({'test': 'data'}), encoding='utf-8')
        output_file = Path(self.temp_dir) / 'output.xlsx'

        test_args = [
            'generate_excel_report.py',
            '--vehicle-folder', str(vehicle_folder),
            '--output-excel', str(output_file)
        ]

        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 0)

    def test_main_missing_arguments(self):
        """测试缺少必需参数"""
        test_args = ['generate_excel_report.py']

        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 2)

    def test_main_nonexistent_input(self):
        """测试输入文件不存在"""
        test_args = [
            'generate_excel_report.py',
            '--input-json', '/nonexistent/file.json',
            '--output-excel', '/nonexistent/output.xlsx'
        ]

        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 1)

    @patch('generate_excel_report.Path.exists')
    def test_main_invalid_json(self, mock_exists):
        """测试无效JSON文件"""
        mock_exists.return_value = True

        json_file = Path(self.temp_dir) / 'invalid.json'
        json_file.write_text('not valid json', encoding='utf-8')
        output_file = Path(self.temp_dir) / 'output.xlsx'

        test_args = [
            'generate_excel_report.py',
            '--input-json', str(json_file),
            '--output-excel', str(output_file)
        ]

        with patch.object(sys, 'argv', test_args):
            result = main()
            self.assertEqual(result, 1)


class TestExcelContentGeneration(unittest.TestCase):
    """测试Excel内容生成"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_vehicle_info_sheet_content(self):
        """测试车辆信息工作表内容"""
        test_data = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {
                    '车型': '坦克500',
                    '制造商': '长城汽车',
                    '车长mm': '5078'
                }
            },
            'components': {}
        }
        output_path = str(Path(self.temp_dir) / 'test.xlsx')

        generate_excel_report(test_data, output_path, use_config=False)

        # 读取并验证内容
        df = pd.read_excel(output_path, sheet_name='Vehicle Information')
        self.assertEqual(len(df), 3)  # 3个参数

    def test_component_summary_sheet_content(self):
        """测试组件摘要工作表内容"""
        test_data = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {}
            },
            'components': {
                'FM_A': {
                    'component_name': '前端模块电流',
                    'unit': 'A',
                    'conditions_count': 3,
                    'conditions': {
                        'cond1': {
                            'condition_name': '工况1',
                            'soc_level': '高电量',
                            'slope': {'max_value': 1.0, 'min_value': -0.5, 'max_abs_value': 1.0}
                        },
                        'cond2': {
                            'condition_name': '工况2',
                            'soc_level': '中电量',
                            'slope': {'max_value': 2.0, 'min_value': -1.0, 'max_abs_value': 2.0}
                        },
                        'cond3': {
                            'condition_name': '工况3',
                            'soc_level': '低电量',
                            'slope': {'max_value': 1.5, 'min_value': -0.8, 'max_abs_value': 1.5}
                        }
                    }
                }
            }
        }
        output_path = str(Path(self.temp_dir) / 'test.xlsx')

        generate_excel_report(test_data, output_path, use_config=False)

        # 读取并验证内容
        df = pd.read_excel(output_path, sheet_name='Component Summary')
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Component Code'], 'FM_A')
        self.assertEqual(df.iloc[0]['Component Name'], '前端模块电流')

    def test_detailed_results_sheet_content(self):
        """测试详细结果工作表内容"""
        test_data = {
            'vehicle': {
                'vehicle_id': 'V0001',
                'vehicle_info': {}
            },
            'components': {
                'FM_A': {
                    'component_name': '前端模块电流',
                    'unit': 'A',
                    'conditions_count': 2,
                    'conditions': {
                        '87_超车': {
                            'condition_name': '超车',
                            'soc_level': '高电量',
                            'slope': {
                                'max_value': 1.5,
                                'min_value': -0.5,
                                'max_abs_value': 1.5
                            },
                            'image_path': '/path/to/image.png'
                        },
                        '20_急加速': {
                            'condition_name': '急加速',
                            'soc_level': '低电量',
                            'slope': {
                                'max_value': 2.0,
                                'min_value': -1.0,
                                'max_abs_value': 2.0
                            },
                            'image_path': ''
                        }
                    }
                }
            }
        }
        output_path = str(Path(self.temp_dir) / 'test.xlsx')

        generate_excel_report(test_data, output_path, use_config=False)

        # 读取并验证内容
        df = pd.read_excel(output_path, sheet_name='Detailed Results')
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]['No.'], 1)
        self.assertEqual(df.iloc[0]['Component'], 'FM_A')


if __name__ == '__main__':
    unittest.main()
