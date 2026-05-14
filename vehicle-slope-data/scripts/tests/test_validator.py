#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_slope.py 测试

测试内容:
- SlopeValidator 初始化
- 各种验证方法
- 报告生成
- 主函数
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

from validate_slope import SlopeValidator, main


class TestSlopeValidatorInit(unittest.TestCase):
    """测试验证器初始化"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_init_with_slope_folder(self):
        """测试使用{SLOPE}文件夹初始化"""
        slope_folder = Path(self.temp_dir) / "V0001_SLOPE"
        slope_folder.mkdir()

        validator = SlopeValidator(str(slope_folder))
        self.assertEqual(validator.vehicle_id, "V0001")
        self.assertEqual(validator.vehicle_folder.name, "V0001_SLOPE")
        self.assertFalse(validator.verbose)

    def test_init_with_plain_folder(self):
        """测试使用普通文件夹初始化"""
        plain_folder = Path(self.temp_dir) / "V0002"
        plain_folder.mkdir()

        validator = SlopeValidator(str(plain_folder))
        self.assertEqual(validator.vehicle_id, "V0002")

    def test_init_with_verbose(self):
        """测试详细模式初始化"""
        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder), verbose=True)
        self.assertTrue(validator.verbose)


class TestVehicleIdExtraction(unittest.TestCase):
    """测试车辆ID提取"""

    def test_extract_from_slope_folder(self):
        """测试从{SLOPE}文件夹提取"""
        validator = SlopeValidator.__new__(SlopeValidator)
        self.assertEqual(validator._extract_vehicle_id("V0001_SLOPE"), "V0001")
        self.assertEqual(validator._extract_vehicle_id("Test_SLOPE"), "Test")

    def test_extract_from_plain_folder(self):
        """测试从普通文件夹提取"""
        validator = SlopeValidator.__new__(SlopeValidator)
        self.assertEqual(validator._extract_vehicle_id("V0001"), "V0001")
        self.assertEqual(validator._extract_vehicle_id("MyVehicle"), "MyVehicle")


class TestVehicleInfoValidation(unittest.TestCase):
    """测试车辆信息验证"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_validate_missing_vehicle_info(self):
        """测试缺少车辆信息文件"""
        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator._validate_vehicle_info()

        self.assertEqual(len(validator.issues), 1)
        self.assertEqual(validator.issues[0]['category'], 'vehicle_info')

    def test_validate_vehicle_info_md(self):
        """测试验证车辆信息MD文件"""
        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()

        md_file = folder / "vehicle_info.md"
        md_content = """| 参数名称 | 参数值 |
| --- | --- |
| 车辆ID | V0002 |
| 车型 | 测试车型 |
"""
        md_file.write_text(md_content, encoding='utf-8')

        validator = SlopeValidator(str(folder))
        validator._validate_vehicle_info()

        self.assertEqual(len(validator.issues), 0)

    def test_validate_vehicle_info_xlsx(self):
        """测试验证车辆信息Excel文件"""
        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()

        xlsx_file = folder / "vehicle_info.xlsx"
        df = pd.DataFrame({
            '车辆ID': ['V0003'],
            '车型': ['测试车型']
        })
        df.to_excel(xlsx_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_vehicle_info()

        self.assertEqual(len(validator.issues), 0)

    def test_validate_missing_required_fields(self):
        """测试缺少必需字段"""
        folder = Path(self.temp_dir) / "V0004_SLOPE"
        folder.mkdir()

        md_file = folder / "vehicle_info.md"
        md_content = """| 参数名称 | 参数值 |
| --- | --- |
| 其他字段 | 值 |
"""
        md_file.write_text(md_content, encoding='utf-8')

        validator = SlopeValidator(str(folder))
        validator._validate_vehicle_info()

        self.assertEqual(len(validator.issues), 1)
        self.assertIn('车辆ID', validator.issues[0]['message'])

    def test_validate_gbk_encoded_file(self):
        """测试GBK编码文件"""
        folder = Path(self.temp_dir) / "V0005_SLOPE"
        folder.mkdir()

        md_file = folder / "vehicle_info.md"
        md_content = """| 参数名称 | 参数值 |
| --- | --- |
| 车辆ID | V0005 |
| 车型 | 测试车型 |
"""
        md_file.write_text(md_content, encoding='gbk')

        validator = SlopeValidator(str(folder))
        validator._validate_vehicle_info()

        self.assertEqual(len(validator.issues), 0)
        self.assertEqual(len(validator.warnings), 1)
        self.assertEqual(validator.warnings[0]['category'], 'vehicle_info')

    def test_validate_empty_excel(self):
        """测试空Excel文件"""
        folder = Path(self.temp_dir) / "V0006_SLOPE"
        folder.mkdir()

        xlsx_file = folder / "vehicle_info.xlsx"
        df = pd.DataFrame()
        df.to_excel(xlsx_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_vehicle_info()

        self.assertEqual(len(validator.issues), 1)
        self.assertIn('为空', validator.issues[0]['message'])


class TestNamingRulesValidation(unittest.TestCase):
    """测试命名规则验证"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_validate_missing_rules(self):
        """测试缺少命名规则文件"""
        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator._validate_naming_rules()

        # 应该有2个info（测试规则和传感器规则各一个）
        self.assertEqual(len(validator.infos), 2)

    def test_validate_test_rules_md(self):
        """测试验证测试规则MD文件"""
        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()

        md_file = folder / "test_naming_rules.md"
        md_content = """| 电量状态 | 工况名称 | 数据命名举例 |
| --- | --- | --- |
| 高电量 | 超车 | 87_超车80-140 |
"""
        md_file.write_text(md_content, encoding='utf-8')

        validator = SlopeValidator(str(folder))
        validator._validate_naming_rules()

        self.assertEqual(len(validator.warnings), 0)

    def test_validate_test_rules_xlsx(self):
        """测试验证测试规则Excel文件"""
        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()

        xlsx_file = folder / "test_naming_rules.xlsx"
        df = pd.DataFrame({
            '电量状态': ['高电量'],
            '工况名称': ['超车'],
            '数据命名举例': ['87_超车80-140']
        })
        df.to_excel(xlsx_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_naming_rules()

        self.assertEqual(len(validator.warnings), 0)

    def test_validate_test_rules_missing_columns(self):
        """测试测试规则缺少必需列"""
        folder = Path(self.temp_dir) / "V0004_SLOPE"
        folder.mkdir()

        xlsx_file = folder / "test_naming_rules.xlsx"
        df = pd.DataFrame({
            '错误列名': ['值']
        })
        df.to_excel(xlsx_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_naming_rules()

        self.assertEqual(len(validator.warnings), 1)
        self.assertIn('缺少必需列', validator.warnings[0]['message'])


class TestComponentStructureValidation(unittest.TestCase):
    """测试组件结构验证"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_validate_no_components(self):
        """测试无组件文件夹"""
        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator._validate_component_structure()

        self.assertEqual(len(validator.issues), 1)
        self.assertEqual(validator.issues[0]['category'], 'component_structure')

    def test_validate_missing_statistics(self):
        """测试缺少statistics.xlsx"""
        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()
        component_folder = folder / "FM_A"
        component_folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator._validate_component_structure()

        self.assertEqual(len(validator.issues), 1)
        self.assertIn('statistics.xlsx', validator.issues[0]['message'])

    def test_validate_valid_component(self):
        """测试有效组件"""
        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()
        component_folder = folder / "FM_A"
        component_folder.mkdir()

        stats_file = component_folder / "statistics.xlsx"
        df = pd.DataFrame({
            '文件名': ['87_超车'],
            '斜率最大值(V/s)': [1.5],
            '斜率最小值(V/s)': [-0.5],
            '斜率绝对值最大值(V/s)': [1.5]
        })
        df.to_excel(stats_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_component_structure()

        self.assertEqual(len(validator.issues), 0)
        self.assertEqual(validator.stats['valid_components'], 1)

    def test_validate_wrong_column_count(self):
        """测试列数不正确"""
        folder = Path(self.temp_dir) / "V0004_SLOPE"
        folder.mkdir()
        component_folder = folder / "FM_A"
        component_folder.mkdir()

        stats_file = component_folder / "statistics.xlsx"
        df = pd.DataFrame({
            '文件名': ['87_超车'],
            '斜率最大值': [1.5]  # 缺少列
        })
        df.to_excel(stats_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_component_structure()

        self.assertEqual(len(validator.issues), 1)
        self.assertIn('列数不正确', validator.issues[0]['message'])

    def test_validate_missing_columns(self):
        """测试缺少必需列"""
        folder = Path(self.temp_dir) / "V0005_SLOPE"
        folder.mkdir()
        component_folder = folder / "FM_A"
        component_folder.mkdir()

        stats_file = component_folder / "statistics.xlsx"
        df = pd.DataFrame({
            '文件名': ['87_超车'],
            '错误列1': [1.5],
            '错误列2': [-0.5],
            '错误列3': [1.5]
        })
        df.to_excel(stats_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_component_structure()

        self.assertEqual(len(validator.issues), 1)
        self.assertIn('缺少必需列', validator.issues[0]['message'])

    def test_validate_non_numeric_data(self):
        """测试非数值数据"""
        folder = Path(self.temp_dir) / "V0006_SLOPE"
        folder.mkdir()
        component_folder = folder / "FM_A"
        component_folder.mkdir()

        stats_file = component_folder / "statistics.xlsx"
        df = pd.DataFrame({
            '文件名': ['87_超车'],
            '斜率最大值(V/s)': ['invalid'],
            '斜率最小值(V/s)': [-0.5],
            '斜率绝对值最大值(V/s)': [1.5]
        })
        df.to_excel(stats_file, index=False)

        validator = SlopeValidator(str(folder))
        validator._validate_component_structure()

        self.assertEqual(len(validator.warnings), 1)
        self.assertIn('非数值数据', validator.warnings[0]['message'])


class TestEncodingValidation(unittest.TestCase):
    """测试编码验证"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_validate_utf8_file(self):
        """测试UTF-8编码文件"""
        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        md_file = folder / "test.md"
        md_file.write_text("# UTF-8 Content", encoding='utf-8')

        validator = SlopeValidator(str(folder))
        validator._validate_encoding()

        self.assertEqual(len(validator.warnings), 0)

    def test_validate_gbk_file(self):
        """测试GBK编码文件"""
        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()

        md_file = folder / "test.md"
        md_file.write_text("中文内容", encoding='gbk')

        validator = SlopeValidator(str(folder))
        validator._validate_encoding()

        self.assertEqual(len(validator.warnings), 1)
        self.assertEqual(validator.warnings[0]['category'], 'file_encoding')


class TestReportGeneration(unittest.TestCase):
    """测试报告生成"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_generate_report(self):
        """测试生成报告"""
        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator.stats = {
            'total_components': 5,
            'valid_components': 4,
            'total_conditions': 100
        }
        validator.issues = [{'type': 'error', 'message': 'test'}]
        validator.warnings = [{'type': 'warning', 'message': 'test'}]
        validator.infos = [{'type': 'info', 'message': 'test'}]

        report_path = validator.generate_report()

        self.assertTrue(Path(report_path).exists())

        # 验证JSON内容
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        self.assertEqual(report['vehicle_id'], 'V0001')
        self.assertEqual(report['summary']['total_components'], 5)
        self.assertEqual(report['summary']['issues_count'], 1)
        self.assertEqual(report['summary']['warnings_count'], 1)
        self.assertFalse(report['summary']['passed'])

    def test_generate_report_with_custom_path(self):
        """测试自定义报告路径"""
        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()
        custom_path = Path(self.temp_dir) / "custom_report.json"

        validator = SlopeValidator(str(folder))
        report_path = validator.generate_report(str(custom_path))

        self.assertEqual(str(report_path), str(custom_path))
        self.assertTrue(custom_path.exists())

    def test_print_report_summary(self):
        """测试打印报告摘要"""
        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator.stats = {
            'total_components': 0,
            'valid_components': 0,
            'total_conditions': 0
        }

        # 应该返回True（无错误）
        result = validator.print_report()
        self.assertTrue(result)

    def test_print_report_with_issues(self):
        """测试打印带错误的报告"""
        folder = Path(self.temp_dir) / "V0004_SLOPE"
        folder.mkdir()

        validator = SlopeValidator(str(folder))
        validator.stats = {'total_components': 1, 'valid_components': 0, 'total_conditions': 0}
        validator.issues = [{
            'category': 'test',
            'message': 'Test error',
            'suggestion': 'Fix it'
        }]

        # 应该返回False（有错误）
        result = validator.print_report()
        self.assertFalse(result)


class TestValidateAll(unittest.TestCase):
    """测试完整验证流程"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_validate_all_pass(self):
        """测试完整验证通过"""
        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        # 创建车辆信息
        md_file = folder / "vehicle_info.md"
        md_file.write_text("""| 参数名称 | 参数值 |
| --- | --- |
| 车辆ID | V0001 |
| 车型 | 测试车型 |
""", encoding='utf-8')

        # 创建组件
        component_folder = folder / "FM_A"
        component_folder.mkdir()
        stats_file = component_folder / "statistics.xlsx"
        df = pd.DataFrame({
            '文件名': ['87_超车'],
            '斜率最大值(V/s)': [1.5],
            '斜率最小值(V/s)': [-0.5],
            '斜率绝对值最大值(V/s)': [1.5]
        })
        df.to_excel(stats_file, index=False)

        validator = SlopeValidator(str(folder))
        passed, issues, warnings, infos = validator.validate_all()

        self.assertTrue(passed)
        self.assertEqual(len(issues), 0)

    def test_validate_all_fail(self):
        """测试完整验证失败"""
        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()

        # 缺少车辆信息文件

        validator = SlopeValidator(str(folder))
        passed, issues, warnings, infos = validator.validate_all()

        self.assertFalse(passed)
        self.assertGreater(len(issues), 0)


class TestMainFunction(unittest.TestCase):
    """测试主函数"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    @patch('validate_slope.SlopeValidator')
    def test_main_success(self, mock_validator_class):
        """测试主函数成功"""
        mock_validator = Mock()
        mock_validator.validate_all.return_value = (True, [], [], [])
        mock_validator_class.return_value = mock_validator

        folder = Path(self.temp_dir) / "V0001_SLOPE"
        folder.mkdir()

        test_args = ['validate_slope.py', '--vehicle-folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    @patch('validate_slope.SlopeValidator')
    def test_main_failure(self, mock_validator_class):
        """测试主函数失败"""
        mock_validator = Mock()
        mock_validator.validate_all.return_value = (False, [{'message': 'error'}], [], [])
        mock_validator_class.return_value = mock_validator

        folder = Path(self.temp_dir) / "V0002_SLOPE"
        folder.mkdir()

        test_args = ['validate_slope.py', '--vehicle-folder', str(folder)]
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)

    @patch('validate_slope.SlopeValidator')
    def test_main_with_output_report(self, mock_validator_class):
        """测试生成输出报告"""
        mock_validator = Mock()
        mock_validator.validate_all.return_value = (True, [], [], [])
        mock_validator_class.return_value = mock_validator

        folder = Path(self.temp_dir) / "V0003_SLOPE"
        folder.mkdir()
        report_path = Path(self.temp_dir) / "report.json"

        test_args = [
            'validate_slope.py',
            '--vehicle-folder', str(folder),
            '--output-report', str(report_path)
        ]
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)


if __name__ == '__main__':
    unittest.main()
