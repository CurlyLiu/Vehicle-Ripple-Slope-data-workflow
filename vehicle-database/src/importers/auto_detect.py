"""
自动检测数据源格式
"""

import sqlite3
from pathlib import Path
from typing import List, Optional

from .base import DataSource


class DataFormatDetector:
    """数据格式检测器 - 同时支持JSON、SQLite、Excel三种格式"""

    @classmethod
    def detect(cls, folder_path: Path) -> List[DataSource]:
        """
        检测文件夹中的所有数据源
        不区分优先级，返回所有找到的数据源

        Args:
            folder_path: 文件夹路径

        Returns:
            数据源列表（无优先级排序，全部返回）
        """
        sources = []
        folder = Path(folder_path)

        if not folder.exists():
            return sources

        # 1. 检查JSON文件
        for pattern in ['*_RIPPLE_data.json', '*_SLOPE_data.json']:
            for json_file in folder.rglob(pattern):
                data_type = 'ripple' if 'RIPPLE' in json_file.name else 'slope'
                sources.append(DataSource(
                    path=json_file,
                    format='json',
                    priority=0,  # 无优先级
                    data_type=data_type
                ))

        # 2. 检查SQLite数据库
        for db_file in folder.rglob('*.db'):
            # 跳过输出目录中的db文件（避免重复）
            if '_output' in str(db_file):
                continue
            data_type = cls._detect_sqlite_type(db_file)
            if data_type:
                sources.append(DataSource(
                    path=db_file,
                    format='sqlite',
                    priority=0,  # 无优先级
                    data_type=data_type
                ))

        # 3. 检查Excel文件
        for pattern in ['*_summary.xlsx', '*.xlsx']:
            for excel_file in folder.rglob(pattern):
                data_type = 'ripple' if 'RIPPLE' in excel_file.name else 'slope' if 'SLOPE' in excel_file.name else 'unknown'
                sources.append(DataSource(
                    path=excel_file,
                    format='excel',
                    priority=0,  # 无优先级
                    data_type=data_type
                ))

        # 只按数据类型排序，不区分格式优先级
        return sorted(sources, key=lambda x: (x.data_type, x.format))

    @classmethod
    def _detect_sqlite_type(cls, db_path: Path) -> Optional[str]:
        """检测SQLite数据库的数据类型"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 检查表名来判断类型
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            conn.close()

            # 根据表名判断类型
            if 'test_results' in tables or 'ripple_results' in tables:
                return 'ripple'
            elif 'slope_results' in tables:
                return 'slope'

            # 根据文件名判断
            name = db_path.name.upper()
            if 'RIPPLE' in name:
                return 'ripple'
            elif 'SLOPE' in name:
                return 'slope'

        except (OSError, sqlite3.Error):
            pass

        return None

    @classmethod
    def find_vehicle_folders(cls, base_path: Path) -> List[Path]:
        """
        在基础路径下查找所有车辆文件夹

        Args:
            base_path: 基础路径（如 F:/Vehicle_Date）

        Returns:
            车辆文件夹列表
        """
        base = Path(base_path)
        if not base.exists():
            return []

        vehicle_folders = []

        for item in base.iterdir():
            if not item.is_dir():
                continue

            # 检查是否为车辆文件夹（包含RIPPLE或SLOPE子文件夹）
            has_ripple = any(item.glob('*_RIPPLE'))
            has_slope = any(item.glob('*_SLOPE'))

            if has_ripple or has_slope:
                vehicle_folders.append(item)

        return sorted(vehicle_folders)
