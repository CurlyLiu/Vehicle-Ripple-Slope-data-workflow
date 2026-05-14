#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本工具模块 - 从SKILL.md读取版本号

提供统一的版本读取功能，避免在多个文件中硬编码版本号。
"""

import re
from pathlib import Path
from typing import Optional


def get_version_from_skill_md(skill_path: Optional[Path] = None) -> str:
    """
    从SKILL.md文件读取版本号

    Args:
        skill_path: Skill根目录路径，默认为当前文件所在目录的父目录

    Returns:
        版本号字符串（如 "4.2"），如果读取失败返回 "Unknown"
    """
    if skill_path is None:
        skill_path = Path(__file__).parent.parent

    skill_md = skill_path / 'SKILL.md'

    if not skill_md.exists():
        return "Unknown"

    try:
        with open(skill_md, 'r', encoding='utf-8') as f:
            for line in f:
                # 匹配 frontmatter 格式: version: "x.y.z"
                if 'version' in line.lower():
                    match = re.search(r'[Vv]ersion\s*[:\s]\s*"?(\d+\.\d+(?:\.\d+)?)"?', line)
                    if match:
                        return match.group(1)
    except Exception:
        pass

    return "Unknown"


def get_ripple_version() -> str:
    """获取vehicle-ripple-data技能版本"""
    skill_path = Path(__file__).parent.parent
    return get_version_from_skill_md(skill_path)


def get_slope_version() -> str:
    """获取vehicle-slope-data技能版本"""
    ripple_path = Path(__file__).parent.parent
    slope_path = ripple_path.parent / 'vehicle-slope-data'
    return get_version_from_skill_md(slope_path)


if __name__ == '__main__':
    # 测试
    print(f"Ripple version: {get_ripple_version()}")
    print(f"Slope version: {get_slope_version()}")
