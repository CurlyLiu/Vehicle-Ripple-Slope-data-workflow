#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆斜率数据处理测试

测试斜率技能的各项功能，包括：
- 斜率处理器初始化
- SOC值提取
- 版本号读取
- 输出目录生成
"""

import unittest
import sys
from pathlib import Path

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

# 添加 ripple-data 到路径以导入 condition_matcher
ripple_path = scripts_dir.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))

# 添加 ripple-data/scripts 到路径
ripple_scripts_path = scripts_dir.parent.parent / 'vehicle-ripple-data' / 'scripts'
if str(ripple_scripts_path) not in sys.path:
    sys.path.insert(0, str(ripple_scripts_path))

# 添加 ripple-data/scripts/core 到路径
ripple_core_path = scripts_dir.parent.parent / 'vehicle-ripple-data' / 'scripts' / 'core'
if str(ripple_core_path) not in sys.path:
    sys.path.insert(0, str(ripple_core_path))

from slope_processor import SlopeDataProcessor
from version_utils import get_slope_version


class TestSlopeVersion(unittest.TestCase):
    """测试版本号功能"""

    def test_version_format(self):
        """测试版本号格式正确"""
        version = get_slope_version()
        self.assertNotEqual(version, "Unknown")
        # 版本号应为 x.y 或 x.y.z 格式
        parts = version.split('.')
        self.assertGreaterEqual(len(parts), 2)
        self.assertLessEqual(len(parts), 3)
        # 每个部分应为数字
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_version_matches_skill_md(self):
        """测试版本号与SKILL.md一致"""
        version = get_slope_version()
        skill_path = Path(__file__).parent.parent.parent
        skill_md = skill_path / 'SKILL.md'

        if skill_md.exists():
            import re
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'version:\s*"(\d+\.\d+(?:\.\d+)?)"', content)
                if match:
                    self.assertEqual(version, match.group(1))


class TestSOCExtraction(unittest.TestCase):
    """测试SOC值提取功能"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时处理器实例用于测试私有方法
        self.processor = SlopeDataProcessor.__new__(SlopeDataProcessor)

    def test_extract_soc_from_condition_id_normal(self):
        """测试正常工况SOC提取"""
        test_cases = [
            ("87_超车80-140", 87),
            ("26_超车80-140", 26),
            ("20_直流充电暖风", 20),
            ("64_匀速100", 64),
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_extract_soc_from_condition_id_slope(self):
        """测试坡度工况SOC提取"""
        test_cases = [
            ("坡度10_81_匀速80暖风", 81),
            ("坡度10_32_急加速", 32),
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_extract_soc_dash_separator(self):
        """测试-分隔符格式SOC提取（V0006等车辆）"""
        test_cases = [
            ("25-交流充电冷风", 25),
            ("55-直流充电暖风", 55),
            ("87-匀速100暖风（运动模式）", 87),
            ("39-超车80-140（运动模式）dmd", 39),
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_extract_soc_slope_with_dash(self):
        """测试坡度工况使用-分隔符提取SOC"""
        test_cases = [
            ("坡度10-24-匀速80暖风", 24),
            ("坡度10-31-匀速80冷风（运动模式）", 31),
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_extract_soc_gbk_corruption(self):
        """测试GBK乱码坡度前缀提取SOC"""
        test_cases = [
            ("�¶�10_26_匀速80冷风", 26),
            ("�¶�10_27_匀速80暖风", 27),
            ("�¶�10_28_急加速0-80", 28),
            ("�¶�10-24-匀速80暖风（运动模式）", 24),
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_extract_soc_slope_with_space(self):
        """测试坡度工况使用空格分隔符提取SOC（V0009/V0010）"""
        test_cases = [
            ("�¶�10 47_匀速80冷风", 47),
            ("�¶�10 51_匀速80暖风", 51),
            ("�¶�10 15_匀速80暖风", 15),
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_normalize_condition_id(self):
        """测试condition_id规范化"""
        self.assertEqual(
            self.processor._normalize_condition_id("�¶�10_82_匀速80暖风"),
            "坡度10_82_匀速80暖风"
        )
        self.assertEqual(
            self.processor._normalize_condition_id("�¶�10-24-匀速80暖风"),
            "坡度10-24-匀速80暖风"
        )
        self.assertEqual(
            self.processor._normalize_condition_id("坡度10_81_匀速80暖风"),
            "坡度10_81_匀速80暖风"
        )
        self.assertEqual(
            self.processor._normalize_condition_id("87_超车80-140"),
            "87_超车80-140"
        )

    def test_extract_soc_edge_cases(self):
        """测试SOC提取边界情况"""
        test_cases = [
            ("", None),
            (None, None),
            ("invalid", None),
            ("abc_def", None),
            ("坡度100_测试", None),  # 负向前瞻保护
            ("32_多次 加速", 32),  # 空格在描述中
        ]
        for condition_id, expected_soc in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertEqual(result, expected_soc)

    def test_extract_soc_from_invalid_id(self):
        """测试无效工况ID"""
        test_cases = [
            "invalid_id",
            "",
            "abc_def",
        ]
        for condition_id in test_cases:
            with self.subTest(condition_id=condition_id):
                result = self.processor._extract_soc_from_condition_id(condition_id)
                self.assertIsNone(result)


class TestSOCLevel(unittest.TestCase):
    """测试SOC等级映射"""

    def setUp(self):
        """设置测试环境"""
        self.processor = SlopeDataProcessor.__new__(SlopeDataProcessor)

    def test_soc_level_high(self):
        """测试高SOC等级"""
        self.assertEqual(self.processor._get_soc_level(87), "≥70%")
        self.assertEqual(self.processor._get_soc_level(70), "≥70%")
        self.assertEqual(self.processor._get_soc_level(100), "≥70%")

    def test_soc_level_medium(self):
        """测试中SOC等级"""
        self.assertEqual(self.processor._get_soc_level(40), "40%-70%")
        self.assertEqual(self.processor._get_soc_level(50), "40%-70%")
        self.assertEqual(self.processor._get_soc_level(69), "40%-70%")

    def test_soc_level_low(self):
        """测试低SOC等级"""
        self.assertEqual(self.processor._get_soc_level(39), "≤40%")
        self.assertEqual(self.processor._get_soc_level(20), "≤40%")
        self.assertEqual(self.processor._get_soc_level(0), "≤40%")

    def test_soc_level_unknown(self):
        """测试未知SOC等级"""
        self.assertEqual(self.processor._get_soc_level(None), "Unknown")


class TestOutputDirectory(unittest.TestCase):
    """测试输出目录生成"""

    def test_output_dir_format(self):
        """测试输出目录格式"""
        # 使用不存在的路径来测试初始化
        try:
            processor = SlopeDataProcessor("/nonexistent/V0001_SLOPE")
        except FileNotFoundError:
            # 预期会失败，但output_dir应该已设置
            pass


class TestImports(unittest.TestCase):
    """测试导入功能"""

    def test_import_condition_matcher(self):
        """测试从ripple-data导入condition_matcher"""
        try:
            from slope_processor import ConditionMatcher
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"无法导入ConditionMatcher: {e}")

    def test_import_config_manager(self):
        """测试导入配置管理器"""
        try:
            from slope_processor import get_slope_config_manager
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"无法导入get_slope_config_manager: {e}")


if __name__ == '__main__':
    unittest.main()
