#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SlopeDataProcessor 核心处理器测试

测试内容:
- 初始化与配置
- 车辆ID提取
- SLOPE子文件夹检测
- 车辆信息解析
- 命名规则解析
- 组件发现与验证
- 斜率数据处理
- 输出文件生成
"""

import unittest
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

# 添加 ripple-data 到路径
ripple_path = scripts_dir.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))

from slope_processor import SlopeDataProcessor


class TestSlopeDataProcessorInit(unittest.TestCase):
    """测试处理器初始化"""

    def setUp(self):
        """创建临时测试目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_init_with_slope_folder(self):
        """测试使用{SLOPE}文件夹初始化"""
        slope_folder = Path(self.temp_dir) / "V0001_SLOPE"
        slope_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(slope_folder))
            self.assertEqual(processor.vehicle_id, "V0001")
            self.assertEqual(processor.folder_name, "V0001_SLOPE")

    def test_init_with_plain_folder(self):
        """测试使用普通文件夹初始化"""
        plain_folder = Path(self.temp_dir) / "V0002"
        plain_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(plain_folder))
            self.assertEqual(processor.vehicle_id, "V0002")

    def test_init_auto_detect_slope_subfolder(self):
        """测试自动检测SLOPE子文件夹"""
        parent_folder = Path(self.temp_dir) / "V0003"
        parent_folder.mkdir()
        slope_folder = parent_folder / "V0003_SLOPE"
        slope_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(parent_folder))
            self.assertEqual(processor.vehicle_id, "V0003")
            self.assertEqual(processor.vehicle_folder.name, "V0003_SLOPE")

    def test_init_custom_config(self):
        """测试自定义配置"""
        slope_folder = Path(self.temp_dir) / "V0001_SLOPE"
        slope_folder.mkdir()
        custom_output = Path(self.temp_dir) / "custom_output"

        config = {
            'generate_json': False,
            'generate_excel': True,
            'generate_sqlite': False,
            'output_dir': str(custom_output)
        }

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(slope_folder), config)
            self.assertFalse(processor.config['generate_json'])
            self.assertTrue(processor.config['generate_excel'])
            self.assertFalse(processor.config['generate_sqlite'])
            self.assertEqual(str(processor.output_dir), str(custom_output))

    def test_default_config(self):
        """测试默认配置"""
        slope_folder = Path(self.temp_dir) / "V0001_SLOPE"
        slope_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(slope_folder))
            self.assertTrue(processor.config['generate_json'])
            self.assertTrue(processor.config['generate_excel'])
            self.assertTrue(processor.config['generate_sqlite'])


class TestVehicleIdExtraction(unittest.TestCase):
    """测试车辆ID提取"""

    def test_extract_from_slope_folder(self):
        """测试从{SLOPE}文件夹提取"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            self.assertEqual(processor._extract_vehicle_id("V0001_SLOPE"), "V0001")
            self.assertEqual(processor._extract_vehicle_id("TestVehicle_SLOPE"), "TestVehicle")

    def test_extract_from_plain_folder(self):
        """测试从普通文件夹提取"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            self.assertEqual(processor._extract_vehicle_id("V0001"), "V0001")
            self.assertEqual(processor._extract_vehicle_id("MyVehicle"), "MyVehicle")

    def test_extract_edge_cases(self):
        """测试边界情况"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            self.assertEqual(processor._extract_vehicle_id(""), "")
            self.assertEqual(processor._extract_vehicle_id("_SLOPE"), "")
            self.assertEqual(processor._extract_vehicle_id("A_SLOPE_SLOPE"), "A_SLOPE")


class TestSlopeSubfolderDetection(unittest.TestCase):
    """测试SLOPE子文件夹检测"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_find_existing_slope_subfolder(self):
        """测试找到存在的SLOPE子文件夹"""
        parent = Path(self.temp_dir) / "parent"
        parent.mkdir()
        slope_folder = parent / "TEST_SLOPE"
        slope_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._find_slope_subfolder(parent)
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "TEST_SLOPE")

    def test_find_nonexistent_slope_subfolder(self):
        """测试找不到SLOPE子文件夹"""
        parent = Path(self.temp_dir) / "parent"
        parent.mkdir()
        regular_folder = parent / "regular_folder"
        regular_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._find_slope_subfolder(parent)
            self.assertIsNone(result)

    def test_find_with_non_dir_path(self):
        """测试非目录路径"""
        file_path = Path(self.temp_dir) / "not_a_dir.txt"
        file_path.write_text("test")

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._find_slope_subfolder(file_path)
            self.assertIsNone(result)


class TestVehicleInfoParsing(unittest.TestCase):
    """测试车辆信息解析"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_parse_vehicle_info_md_standard_format(self):
        """测试标准纵向格式解析"""
        md_file = Path(self.temp_dir) / "vehicle_info.md"
        md_content = """| 参数名称 | 参数值 |
| --- | --- |
| 车型 | 坦克500 |
| 车辆ID | V0001 |
| 制造商 | 长城汽车 |
"""
        md_file.write_text(md_content, encoding='utf-8')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_vehicle_info_md(md_file)
            self.assertEqual(result.get('车型'), '坦克500')
            self.assertEqual(result.get('车辆ID'), 'V0001')
            self.assertEqual(result.get('制造商'), '长城汽车')

    def test_parse_vehicle_info_md_autohome_format(self):
        """测试汽车之家格式解析"""
        md_file = Path(self.temp_dir) / "vehicle_info.md"
        md_content = """| 参数名称 | 北京越野BJ60增程 2024款 |
| --- | --- |
| 厂商指导价(元) | 25.98万 |
| 车辆ID | V0002 |
"""
        md_file.write_text(md_content, encoding='utf-8')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_vehicle_info_md(md_file)
            self.assertEqual(result.get('参数名称'), '北京越野BJ60增程 2024款')
            self.assertEqual(result.get('厂商指导价(元)'), '25.98万')

    def test_parse_vehicle_info_md_horizontal_format(self):
        """测试横向表格格式"""
        md_file = Path(self.temp_dir) / "vehicle_info.md"
        md_content = """| 车型 | 车辆ID | 制造商 |
| --- | --- | --- |
| Model X | V0003 | Tesla |
"""
        md_file.write_text(md_content, encoding='utf-8')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_vehicle_info_md(md_file)
            self.assertEqual(result.get('车型'), 'Model X')
            self.assertEqual(result.get('车辆ID'), 'V0003')

    def test_parse_vehicle_info_md_gbk_encoding(self):
        """测试GBK编码文件"""
        md_file = Path(self.temp_dir) / "vehicle_info.md"
        md_content = """| 参数名称 | 参数值 |
| --- | --- |
| 车型 | 测试车型 |
"""
        md_file.write_text(md_content, encoding='gbk')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_vehicle_info_md(md_file)
            self.assertEqual(result.get('车型'), '测试车型')

    def test_parse_vehicle_info_xlsx(self):
        """测试Excel格式解析"""
        xlsx_file = Path(self.temp_dir) / "vehicle_info.xlsx"
        df = pd.DataFrame({
            '车型': ['坦克500'],
            '车辆ID': ['V0001'],
            '制造商': ['长城汽车']
        })
        df.to_excel(xlsx_file, index=False)

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_vehicle_info_xlsx(xlsx_file)
            self.assertEqual(result.get('车型'), '坦克500')
            self.assertEqual(result.get('车辆ID'), 'V0001')

    def test_parse_empty_file(self):
        """测试空文件"""
        md_file = Path(self.temp_dir) / "vehicle_info.md"
        md_file.write_text("", encoding='utf-8')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_vehicle_info_md(md_file)
            self.assertEqual(result, {})


class TestNamingRulesParsing(unittest.TestCase):
    """测试命名规则解析"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_parse_test_rules_md(self):
        """测试测试命名规则MD解析"""
        md_file = Path(self.temp_dir) / "test_naming_rules.md"
        md_content = """| 电量状态 | 工况名称 | 数据命名举例 |
| --- | --- | --- |
| 高电量 | 超车 | 87_超车80-140 |
| 低电量 | 急加速 | 20_急加速0-80 |
"""
        md_file.write_text(md_content, encoding='utf-8')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_test_rules_md(md_file)
            self.assertIn('87_超车80-140', result)
            self.assertEqual(result['87_超车80-140']['soc_level'], '高电量')
            self.assertEqual(result['87_超车80-140']['condition_name'], '超车')

    def test_parse_test_rules_xlsx(self):
        """测试测试命名规则Excel解析"""
        xlsx_file = Path(self.temp_dir) / "test_naming_rules.xlsx"
        df = pd.DataFrame({
            '电量状态': ['高电量', '低电量'],
            '工况名称': ['超车', '急加速'],
            '数据命名举例': ['87_超车80-140', '20_急加速0-80']
        })
        df.to_excel(xlsx_file, index=False)

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_test_rules_xlsx(xlsx_file)
            self.assertIn('87_超车80-140', result)
            self.assertEqual(result['87_超车80-140']['soc_level'], '高电量')

    def test_parse_sensor_rules_md(self):
        """测试传感器命名规则MD解析"""
        md_file = Path(self.temp_dir) / "sensor_naming_rules.md"
        md_content = """# 传感器命名规则
FM_A: 前端模块电流
LV_V: 低压系统电压
HV_V: 高压系统电压
"""
        md_file.write_text(md_content, encoding='utf-8')

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_sensor_rules_md(md_file)
            self.assertIn('FM_A', result)
            self.assertEqual(result['FM_A']['name'], '前端模块电流')
            self.assertEqual(result['FM_A']['unit'], 'A')
            self.assertEqual(result['LV_V']['unit'], 'V')

    def test_parse_sensor_rules_xlsx(self):
        """测试传感器命名规则Excel解析"""
        xlsx_file = Path(self.temp_dir) / "sensor_naming_rules.xlsx"
        df = pd.DataFrame({
            '通道代码': ['FM_A', 'LV_V'],
            '描述': ['前端模块电流', '低压系统电压']
        })
        df.to_excel(xlsx_file, index=False)

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            result = processor._parse_sensor_rules_xlsx(xlsx_file)
            self.assertIn('FM_A', result)
            self.assertEqual(result['FM_A']['name'], '前端模块电流')


class TestSafeFloatConversion(unittest.TestCase):
    """测试安全浮点数转换"""

    def test_valid_numbers(self):
        """测试有效数字"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            self.assertEqual(processor._safe_float(3.14), 3.14)
            self.assertEqual(processor._safe_float("2.5"), 2.5)
            self.assertEqual(processor._safe_float(42), 42.0)

    def test_nan_values(self):
        """测试NaN值"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            self.assertIsNone(processor._safe_float(float('nan')))
            self.assertIsNone(processor._safe_float(pd.NA))

    def test_invalid_values(self):
        """测试无效值"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            self.assertIsNone(processor._safe_float("invalid"))
            self.assertIsNone(processor._safe_float(None))
            self.assertIsNone(processor._safe_float([1, 2, 3]))


class TestResultDataBuilding(unittest.TestCase):
    """测试结果数据构建"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_build_result_data_basic(self):
        """测试基本结果数据构建"""
        slope_folder = Path(self.temp_dir) / "V0001_SLOPE"
        slope_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(slope_folder))
            processor.vehicle_info = {'车型': 'Test'}
            processor.components = {
                'FM_A': {
                    'conditions': {'cond1': {}, 'cond2': {}}
                }
            }

            result = processor._build_result_data(include_debug=False)
            self.assertEqual(result['vehicle']['vehicle_id'], 'V0001')
            self.assertEqual(result['vehicle']['vehicle_info']['车型'], 'Test')
            self.assertEqual(result['metadata']['total_components'], 1)
            self.assertEqual(result['metadata']['total_conditions'], 2)
            self.assertNotIn('warnings', result['metadata'])

    def test_build_result_data_with_debug(self):
        """测试带调试信息的结果数据构建"""
        slope_folder = Path(self.temp_dir) / "V0001_SLOPE"
        slope_folder.mkdir()

        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor(str(slope_folder))
            processor.vehicle_info = {}
            processor.components = {}
            processor.warnings = ['warning1', 'warning2']
            processor.errors = ['error1']

            result = processor._build_result_data(include_debug=True)
            self.assertIn('warnings', result['metadata'])
            self.assertIn('errors', result['metadata'])
            self.assertEqual(len(result['metadata']['warnings']), 2)
            self.assertEqual(len(result['metadata']['errors']), 1)


class TestConfigDrivenExtraction(unittest.TestCase):
    """测试配置驱动字段提取"""

    def test_extract_field_fallback(self):
        """测试回退字段提取"""
        with patch.object(SlopeDataProcessor, '_init_config_manager'):
            processor = SlopeDataProcessor.__new__(SlopeDataProcessor)
            raw_data = {'车型': '坦克500', '制造商': '长城'}
            self.assertEqual(processor._extract_field_fallback(raw_data, 'vehicle_model'), '坦克500')
            self.assertEqual(processor._extract_field_fallback(raw_data, 'manufacturer'), '长城')
            self.assertIsNone(processor._extract_field_fallback(raw_data, 'unknown_field'))


if __name__ == '__main__':
    unittest.main()
