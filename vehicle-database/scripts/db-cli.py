#!/usr/bin/env python3
"""
Vehicle Database CLI 入口脚本
"""

import sys
from pathlib import Path

# 添加src到Python路径
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from cli import cli

if __name__ == '__main__':
    cli()
