"""
数据库连接管理
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional


class DatabaseConnection:
    """数据库连接管理器"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """建立数据库连接"""
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def get_connection(self) -> sqlite3.Connection:
        """获取当前连接，如不存在则创建"""
        if self._connection is None:
            return self.connect()
        return self._connection

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        """执行SQL"""
        return self.get_connection().execute(sql, parameters)

    def executescript(self, sql: str) -> sqlite3.Cursor:
        """执行SQL脚本"""
        return self.get_connection().executescript(sql)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
