#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
version_utils.py 测试

测试内容:
- 版本号读取
- SKILL.md解析
- 回退机制
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

# 添加 ripple-data 到路径
ripple_path = scripts_dir.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))

from version_utils import get_slope_version


class TestGetSlopeVersion(unittest.TestCase):
    """测试获取斜率技能版本"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    @patch('version_utils.get_version_from_skill_md')
    def test_get_slope_version(self, mock_get_version):
        """测试获取斜率版本"""
        mock_get_version.return_value = "1.2.3"

        version = get_slope_version()
        self.assertEqual(version, "1.2.3")

    @patch('version_utils.get_version_from_skill_md')
    def test_get_slope_version_unknown(self, mock_get_version):
        """测试获取未知版本"""
        mock_get_version.return_value = "Unknown"

        version = get_slope_version()
        self.assertEqual(version, "Unknown")

    def test_get_slope_version_integration(self):
        """测试集成版本获取（实际SKILL.md）"""
        # 这个测试使用实际的SKILL.md文件
        version = get_slope_version()
        # 验证版本格式 x.y 或 x.y.z
        self.assertNotEqual(version, "Unknown")
        parts = version.split('.')
        self.assertGreaterEqual(len(parts), 2)
        self.assertLessEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())


class TestVersionFromSkillMd(unittest.TestCase):
    """测试从SKILL.md解析版本"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_parse_version_from_yaml_frontmatter(self):
        """测试从YAML frontmatter解析版本"""
        # 导入基本实现进行测试
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        content = """---
name: vehicle-slope-data
version: "1.2.3"
description: Test skill
---

# Content
"""
        skill_md.write_text(content, encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "1.2.3")

    def test_parse_version_from_inline(self):
        """测试从行内版本声明解析"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        content = """# Vehicle Slope Data Skill

Version: 2.0

Some content here.
"""
        skill_md.write_text(content, encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "2.0")

    def test_parse_version_with_quotes(self):
        """测试带引号的版本号"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        content = """---
version: "3.1.4"
---
"""
        skill_md.write_text(content, encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "3.1.4")

    def test_parse_version_without_quotes(self):
        """测试不带引号的版本号"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        content = """---
version: 1.5
---
"""
        skill_md.write_text(content, encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "1.5")

    def test_missing_skill_md(self):
        """测试缺少SKILL.md文件"""
        from version_utils import get_version_from_skill_md

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "Unknown")

    def test_no_version_in_skill_md(self):
        """测试SKILL.md中没有版本号"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        content = """# No Version Here

Some content without version.
"""
        skill_md.write_text(content, encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "Unknown")

    def test_empty_skill_md(self):
        """测试空的SKILL.md文件"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        skill_md.write_text("", encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "Unknown")

    def test_multiple_version_lines(self):
        """测试多行版本声明"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        content = """---
version: "1.0.0"
---

# Header

Version: 2.0.0
"""
        skill_md.write_text(content, encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        # 应该返回第一个匹配的版本
        self.assertEqual(version, "1.0.0")


class TestVersionFormatValidation(unittest.TestCase):
    """测试版本格式验证"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_two_part_version(self):
        """测试两部分版本号"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        skill_md.write_text('version: "1.2"', encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "1.2")

    def test_three_part_version(self):
        """测试三部分版本号"""
        from version_utils import get_version_from_skill_md

        skill_md = Path(self.temp_dir) / "SKILL.md"
        skill_md.write_text('version: "1.2.3"', encoding='utf-8')

        version = get_version_from_skill_md(Path(self.temp_dir))
        self.assertEqual(version, "1.2.3")


if __name__ == '__main__':
    unittest.main()
