"""
导入器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from datetime import datetime


@dataclass
class DataSource:
    """数据源描述"""
    path: Path
    format: str
    priority: int
    data_type: str


@dataclass
class ImportResult:
    """导入结果"""
    vehicle_id: str
    data_type: str
    components_imported: int = 0
    conditions_imported: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        """是否成功（无错误）"""
        return len(self.errors) == 0


class BaseImporter(ABC):
    """导入器基类"""

    @abstractmethod
    def can_import(self, file_path: Path) -> bool:
        """
        检查是否可以导入该文件

        Args:
            file_path: 文件路径

        Returns:
            是否可以导入
        """
        pass

    @abstractmethod
    def import_data(self, conn, vehicle_id: str, file_path: Path) -> ImportResult:
        """
        导入数据

        Args:
            conn: 数据库连接
            vehicle_id: 车辆ID
            file_path: 文件路径

        Returns:
            导入结果
        """
        pass

    def detect_data_type(self, file_path: Path) -> Optional[str]:
        """
        检测数据类型（ripple/slope）

        Args:
            file_path: 文件路径

        Returns:
            数据类型或None
        """
        name = file_path.name.upper()
        if 'RIPPLE' in name:
            return 'ripple'
        elif 'SLOPE' in name:
            return 'slope'
        return None
