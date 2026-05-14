# -*- coding: utf-8 -*-
"""
车辆斜率数据处理测试套件

引用 vehicle-ripple-data 的测试基础设施，
确保双子星技能的测试一致性。
"""

import sys
from pathlib import Path

# 添加 ripple-data 到路径以共享测试基础设施
ripple_path = Path(__file__).parent.parent.parent.parent / 'vehicle-ripple-data'
if str(ripple_path) not in sys.path:
    sys.path.insert(0, str(ripple_path))
