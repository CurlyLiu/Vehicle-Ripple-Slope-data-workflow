#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本工具模块 - 从SKILL.md读取版本号 (斜率技能)

引用vehicle-ripple-data的版本工具，保持单一来源。
"""

import sys
from pathlib import Path

# 添加ripple-data到路径
ripple_path = Path(__file__).parent.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))

# 从ripple-data导入版本工具
try:
    from scripts.version_utils import get_version_from_skill_md, get_ripple_version
except ImportError:
    # 如果无法导入，提供基本实现
    import re

    def get_version_from_skill_md(skill_path=None):
        """基本版本读取实现"""
        if skill_path is None:
            skill_path = Path(__file__).parent.parent

        skill_md = skill_path / 'SKILL.md'
        if not skill_md.exists():
            return "Unknown"

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'version' in line.lower():
                        match = re.search(r'[Vv]ersion\s*[:\s]\s*"?(\d+\.\d+(?:\.\d+)?)"?', line)
                        if match:
                            return match.group(1)
        except Exception:
            pass
        return "Unknown"

    def get_ripple_version():
        """获取ripple版本"""
        ripple_path = Path(__file__).parent.parent.parent / 'vehicle-ripple-data'
        return get_version_from_skill_md(ripple_path)


def get_slope_version() -> str:
    """获取vehicle-slope-data技能版本"""
    skill_path = Path(__file__).parent.parent
    return get_version_from_skill_md(skill_path)


if __name__ == '__main__':
    # 测试
    print(f"Ripple version: {get_ripple_version()}")
    print(f"Slope version: {get_slope_version()}")
