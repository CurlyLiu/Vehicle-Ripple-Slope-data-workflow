"""
SQLite数据库导入器
支持从已有的SQLite数据库导入纹波和斜率测试数据
"""

import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

from .base import BaseImporter, ImportResult, DataSource


# Allowed table and column name patterns for security
ALLOWED_TABLES = {'ripple_results', 'slope_results', 'test_results', 'vehicles', 'components', 'test_conditions', 'data_batches'}
VALID_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str) -> bool:
    """Validate SQL identifier to prevent injection."""
    return bool(VALID_IDENTIFIER_PATTERN.match(name))


def _validate_table_name(name: str) -> bool:
    """Validate table name against allowed list or pattern."""
    if name in ALLOWED_TABLES:
        return True
    return _validate_identifier(name)


class SqliteImporter(BaseImporter):
    """SQLite数据库导入器"""

    def import_data(self, db_connection: sqlite3.Connection,
                    vehicle_id: str, file_path: Path) -> ImportResult:
        """
        从SQLite数据库导入数据

        Args:
            db_connection: 目标数据库连接
            vehicle_id: 车辆ID
            file_path: SQLite数据库文件路径

        Returns:
            ImportResult: 导入结果
        """
        warnings = []
        errors = []
        components_imported = 0
        conditions_imported = 0

        try:
            # 连接源SQLite数据库
            source_conn = sqlite3.connect(str(file_path))
            source_conn.row_factory = sqlite3.Row
            cursor = source_conn.cursor()

            # 检测数据类型
            data_type = self._detect_data_type(file_path, cursor)

            if data_type == 'ripple':
                result = self._import_ripple_data(
                    db_connection, source_conn, vehicle_id, file_path
                )
            elif data_type == 'slope':
                result = self._import_slope_data(
                    db_connection, source_conn, vehicle_id, file_path
                )
            else:
                source_conn.close()
                # v1.6 hotfix P2.1: 改为 raise (与 json/excel importer 一致),
                # 让上层 `with DatabaseConnection` 回滚事务
                raise ValueError(f"无法识别的数据类型: {file_path}")

            source_conn.close()
            return result

        except (KeyboardInterrupt, SystemExit):
            if 'source_conn' in locals():
                source_conn.close()
            raise
        except (sqlite3.Error, OSError, json.JSONDecodeError, ValueError):
            # v1.6 hotfix P2.1: 改 return False 为 raise (NEW-1 原子性一致性)
            if 'source_conn' in locals():
                source_conn.close()
            raise

    def _detect_data_type(self, file_path: Path, cursor: sqlite3.Cursor) -> Optional[str]:
        """检测SQLite数据库的数据类型"""
        # 1. 根据文件名判断
        name = file_path.name.upper()
        if 'RIPPLE' in name:
            return 'ripple'
        elif 'SLOPE' in name:
            return 'slope'

        # 2. 根据表结构判断
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            if 'ripple_results' in tables or 'test_results' in tables:
                # 进一步检查表结构
                if 'test_results' in tables:
                    cursor.execute("PRAGMA table_info(test_results)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if any('vpp' in col.lower() or 'peak' in col.lower() for col in columns):
                        return 'ripple'
                    elif any('slope' in col.lower() for col in columns):
                        return 'slope'
                return 'ripple'
            elif 'slope_results' in tables:
                return 'slope'
        except (sqlite3.Error, IndexError):
            pass

        return None

    def _import_ripple_data(self, target_conn: sqlite3.Connection,
                           source_conn: sqlite3.Connection,
                           vehicle_id: str, file_path: Path) -> ImportResult:
        """导入纹波数据"""
        warnings = []
        errors = []
        components_imported = set()
        conditions_imported = set()

        cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # 首先插入车辆信息（如果不存在），传入源连接以读取完整 vehicle_info
        self._ensure_vehicle_exists(target_cursor, vehicle_id, source_conn)

        # 查询源数据库的表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # 确定主数据表
        data_table = None
        if 'ripple_results' in tables:
            data_table = 'ripple_results'
        elif 'test_results' in tables:
            data_table = 'test_results'

        if not data_table:
            errors.append("未找到纹波数据表")
            return ImportResult(
                success=False,
                components_imported=0,
                conditions_imported=0,
                warnings=warnings,
                errors=errors
            )

        # 获取表结构 (validate table name first)
        if not _validate_table_name(data_table):
            errors.append(f"Invalid table name: {data_table}")
            return ImportResult(
                success=False, components_imported=0, conditions_imported=0,
                warnings=warnings, errors=errors
            )
        cursor.execute(f"PRAGMA table_info({data_table})")
        columns = {row[1].lower(): row[1] for row in cursor.fetchall()}

        # 构建查询语句（适配不同的列名）
        select_cols = []
        col_mapping = {}

        # 组件相关
        if 'component_code' in columns:
            select_cols.append(columns['component_code'])
            col_mapping['component_code'] = columns['component_code']
        elif 'channel_code' in columns:
            select_cols.append(columns['channel_code'])
            col_mapping['component_code'] = columns['channel_code']

        # 工况相关
        if 'condition_id' in columns:
            select_cols.append(columns['condition_id'])
            col_mapping['condition_id'] = columns['condition_id']
        elif 'condition_name' in columns:
            select_cols.append(columns['condition_name'])
            col_mapping['condition_name'] = columns['condition_name']

        # Vpp值
        if 'vpp_value' in columns:
            select_cols.append(columns['vpp_value'])
            col_mapping['vpp_value'] = columns['vpp_value']
        elif 'vpp' in columns:
            select_cols.append(columns['vpp'])
            col_mapping['vpp_value'] = columns['vpp']

        # 频率
        if 'peak_frequency_khz' in columns:
            select_cols.append(columns['peak_frequency_khz'])
            col_mapping['peak_frequency_khz'] = columns['peak_frequency_khz']
        elif 'peak_frequency' in columns:
            select_cols.append(columns['peak_frequency'])
            col_mapping['peak_frequency_khz'] = columns['peak_frequency']

        # 幅值
        if 'peak_amplitude' in columns:
            select_cols.append(columns['peak_amplitude'])
            col_mapping['peak_amplitude'] = columns['peak_amplitude']

        # 时域有效值
        if 'time_domain_effective_value' in columns:
            select_cols.append(columns['time_domain_effective_value'])
            col_mapping['time_domain_effective_value'] = columns['time_domain_effective_value']

        # 频域数据
        if 'peak_ranking' in columns:
            select_cols.append(columns['peak_ranking'])
            col_mapping['peak_ranking'] = columns['peak_ranking']

        # 图片路径
        if 'image_path' in columns:
            select_cols.append(columns['image_path'])
            col_mapping['image_path'] = columns['image_path']

        # 验证所有列名
        valid_select_cols = [col for col in select_cols if _validate_identifier(col)]
        if not valid_select_cols:
            errors.append("No valid columns to select")
            return ImportResult(
                success=False, components_imported=0, conditions_imported=0,
                warnings=warnings, errors=errors
            )

        # 执行查询 (table name validated above, column names validated here)
        query = f"SELECT {', '.join(valid_select_cols)} FROM {data_table}"
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            errors.append(f"查询数据失败: {e}")
            return ImportResult(
                success=False,
                components_imported=0,
                conditions_imported=0,
                warnings=warnings,
                errors=errors
            )

        # 插入数据到目标数据库
        for row in cursor.execute(query):
            row_data = dict(zip([col_mapping.get(c, c) for c in valid_select_cols], row))

            component_code = row_data.get('component_code', 'UNKNOWN')
            condition_id = row_data.get('condition_id', row_data.get('condition_name', 'UNKNOWN'))

            # 确保部件存在
            self._ensure_component_exists(
                target_cursor, component_code,
                row_data.get('component_name', component_code),
                row_data.get('unit', 'V')
            )
            components_imported.add(component_code)

            # 确保工况存在
            self._ensure_condition_exists(
                target_cursor, condition_id,
                row_data.get('condition_name', condition_id),
                row_data.get('soc_level', 'UNKNOWN')
            )
            conditions_imported.add(condition_id)

            # 插入纹波结果
            try:
                target_cursor.execute("""
                    INSERT OR REPLACE INTO ripple_results (
                        vehicle_id, component_code, condition_id,
                        time_domain_effective_value, vpp_value,
                        peak_frequency_khz, peak_amplitude, frequency_rms,
                        peak_ranking, image_path, match_confidence, match_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vehicle_id, component_code, condition_id,
                    row_data.get('time_domain_effective_value'),
                    row_data.get('vpp_value'),
                    row_data.get('peak_frequency_khz'),
                    row_data.get('peak_amplitude'),
                    row_data.get('frequency_rms'),
                    json.dumps(row_data.get('peak_ranking')) if isinstance(row_data.get('peak_ranking'), (list, dict)) else row_data.get('peak_ranking'),
                    row_data.get('image_path'),
                    row_data.get('match_confidence', 1.0),
                    row_data.get('match_method', 'sqlite_import')
                ))
            except (sqlite3.Error, ValueError) as e:
                warnings.append(f"插入记录失败 ({component_code}, {condition_id}): {e}")

        # NEW-1 v1.4: ripple_results - 不在 importer 内部 commit,由外层 with 控制

        return ImportResult(
            success=len(errors) == 0,
            components_imported=len(components_imported),
            conditions_imported=len(conditions_imported),
            warnings=warnings,
            errors=errors
        )

    def _import_slope_data(self, target_conn: sqlite3.Connection,
                          source_conn: sqlite3.Connection,
                          vehicle_id: str, file_path: Path) -> ImportResult:
        """导入斜率数据"""
        warnings = []
        errors = []
        components_imported = set()
        conditions_imported = set()

        cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # 首先插入车辆信息（如果不存在），传入源连接以读取完整 vehicle_info
        self._ensure_vehicle_exists(target_cursor, vehicle_id, source_conn)

        # 查询源数据库的表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # 确定主数据表
        data_table = None
        if 'slope_results' in tables:
            data_table = 'slope_results'
        elif 'test_results' in tables:
            data_table = 'test_results'

        if not data_table:
            errors.append("未找到斜率数据表")
            return ImportResult(
                success=False,
                components_imported=0,
                conditions_imported=0,
                warnings=warnings,
                errors=errors
            )

        # 获取表结构 (validate table name first)
        if not _validate_table_name(data_table):
            errors.append(f"Invalid table name: {data_table}")
            return ImportResult(
                success=False, components_imported=0, conditions_imported=0,
                warnings=warnings, errors=errors
            )
        cursor.execute(f"PRAGMA table_info({data_table})")
        columns = {row[1].lower(): row[1] for row in cursor.fetchall()}

        # 构建查询语句
        select_cols = []
        col_mapping = {}

        # 组件相关
        if 'component_code' in columns:
            select_cols.append(columns['component_code'])
            col_mapping['component_code'] = columns['component_code']
        elif 'channel_code' in columns:
            select_cols.append(columns['channel_code'])
            col_mapping['component_code'] = columns['channel_code']

        # 工况相关
        if 'condition_id' in columns:
            select_cols.append(columns['condition_id'])
            col_mapping['condition_id'] = columns['condition_id']
        elif 'condition_name' in columns:
            select_cols.append(columns['condition_name'])
            col_mapping['condition_name'] = columns['condition_name']

        # 斜率值
        for col in ['slope_max', 'slope_min', 'slope_max_abs', 'slope']:
            if col in columns:
                select_cols.append(columns[col])
                col_mapping[col] = columns[col]

        # 图片路径
        if 'image_path' in columns:
            select_cols.append(columns['image_path'])
            col_mapping['image_path'] = columns['image_path']

        # 验证所有列名
        valid_select_cols = [col for col in select_cols if _validate_identifier(col)]
        if not valid_select_cols:
            errors.append("No valid columns to select")
            return ImportResult(
                success=False, components_imported=0, conditions_imported=0,
                warnings=warnings, errors=errors
            )

        # 执行查询 (table name validated above, column names validated here)
        query = f"SELECT {', '.join(valid_select_cols)} FROM {data_table}"
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            errors.append(f"查询数据失败: {e}")
            return ImportResult(
                success=False,
                components_imported=0,
                conditions_imported=0,
                warnings=warnings,
                errors=errors
            )

        # 插入数据到目标数据库
        for row in cursor.execute(query):
            row_data = dict(zip([col_mapping.get(c, c) for c in valid_select_cols], row))

            component_code = row_data.get('component_code', 'UNKNOWN')
            condition_id = row_data.get('condition_id', row_data.get('condition_name', 'UNKNOWN'))

            # 确保部件存在
            self._ensure_component_exists(
                target_cursor, component_code,
                row_data.get('component_name', component_code),
                row_data.get('unit', 'V/s')
            )
            components_imported.add(component_code)

            # 确保工况存在
            self._ensure_condition_exists(
                target_cursor, condition_id,
                row_data.get('condition_name', condition_id),
                row_data.get('soc_level', 'UNKNOWN')
            )
            conditions_imported.add(condition_id)

            # 插入斜率结果
            try:
                target_cursor.execute("""
                    INSERT OR REPLACE INTO slope_results (
                        vehicle_id, component_code, condition_id,
                        slope_max, slope_min, slope_max_abs, slope_unit,
                        image_path, match_confidence, match_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vehicle_id, component_code, condition_id,
                    row_data.get('slope_max'),
                    row_data.get('slope_min'),
                    row_data.get('slope_max_abs'),
                    row_data.get('slope_unit', 'V/s'),
                    row_data.get('image_path'),
                    row_data.get('match_confidence', 1.0),
                    row_data.get('match_method', 'sqlite_import')
                ))
            except (sqlite3.Error, ValueError) as e:
                warnings.append(f"插入记录失败 ({component_code}, {condition_id}): {e}")

        # NEW-1 v1.4: 不在 importer 内部 commit,由外层 with DatabaseConnection 控制

        return ImportResult(
            success=len(errors) == 0,
            components_imported=len(components_imported),
            conditions_imported=len(conditions_imported),
            warnings=warnings,
            errors=errors
        )

    def _ensure_vehicle_exists(self, cursor: sqlite3.Cursor, vehicle_id: str,
                               source_conn: Optional[sqlite3.Connection] = None):
        """确保车辆信息存在，如有源数据库则读取完整信息"""
        if source_conn is not None:
            try:
                source_cursor = source_conn.cursor()
                source_cursor.execute(
                    "SELECT vehicle_info FROM vehicles WHERE vehicle_id = ?",
                    (vehicle_id,)
                )
                row = source_cursor.fetchone()
                if row and row[0]:
                    vehicle_info = json.loads(row[0])

                    def _getv(*keys):
                        for k in keys:
                            v = vehicle_info.get(k)
                            if v is not None and str(v).strip():
                                return v
                        return None

                    columns = ['vehicle_id', 'vehicle_model']
                    values = [vehicle_id, _getv('vehicle_model', '车型', '参数名称') or vehicle_id]

                    field_map = {
                        'manufacturer': ('manufacturer', '制造商', '厂商', '品牌'),
                        'level': ('level', '级别'),
                        'energy_type': ('energy_type', '能源类型'),
                        'length_mm': ('length_mm', '长度(mm)', '车长mm', '车长'),
                        'width_mm': ('width_mm', '宽度(mm)', '车宽mm', '车宽'),
                        'height_mm': ('height_mm', '高度(mm)', '车高mm', '车高'),
                        'wheelbase_mm': ('wheelbase_mm', '轴距(mm)'),
                        'front_track_mm': ('front_track_mm', '前轮距(mm)'),
                        'rear_track_mm': ('rear_track_mm', '后轮距(mm)'),
                        'min_ground_clearance_mm': ('min_ground_clearance_mm', '最小离地间隙(mm)'),
                        'curb_weight_kg': ('curb_weight_kg', '整备质量(kg)'),
                        'max_weight_kg': ('max_weight_kg', '最大满载质量(kg)'),
                        'front_motor_max_power_kw': ('front_motor_max_power_kw', '前电机最大功率(kW)', '前电动机最大功率(kW)'),
                        'rear_motor_max_power_kw': ('rear_motor_max_power_kw', '后电机最大功率(kW)', '后电动机最大功率(kW)'),
                        'front_motor_max_torque_nm': ('front_motor_max_torque_nm', '前电机最大扭矩(N·m)', '电动机总扭矩(N·m)'),
                        'rear_motor_max_torque_nm': ('rear_motor_max_torque_nm', '后电机最大扭矩(N·m)'),
                        'system_total_power_kw': ('system_total_power_kw', '系统综合功率(kW)'),
                        'high_voltage_architecture': ('high_voltage_architecture', '高压架构'),
                        'battery_type': ('battery_type', '电池类型'),
                        'battery_capacity_kwh': ('battery_capacity_kwh', '电池能量(kWh)'),
                        'fast_charge_power_kw': ('fast_charge_power_kw', '快充功率(kW)'),
                        'front_suspension': ('front_suspension', '前悬类型', '前悬挂类型'),
                        'rear_suspension': ('rear_suspension', '后悬类型', '后悬挂类型'),
                        'engine_model': ('engine_model', '发动机型号'),
                        'transmission_type': ('transmission_type', '变速箱类型'),
                        'displacement_l': ('displacement_l', '排量(L)'),
                        'engine_max_power_kw': ('engine_max_power_kw', '发动机最大净功率(kW/rpm)'),
                        'engine_max_torque_nm': ('engine_max_torque_nm', '发动机最大净扭矩(N·m/rpm)'),
                        'price_wan': ('price_wan', '指导价格（万元）', '厂商指导价(元)', '经销商报价'),
                    }

                    for col, keys in field_map.items():
                        val = _getv(*keys)
                        if val is not None:
                            columns.append(col)
                            values.append(val)

                    columns.append('vehicle_info_json')
                    values.append(json.dumps(vehicle_info, ensure_ascii=False))

                    placeholders = ', '.join('?' for _ in values)
                    cursor.execute(
                        f"INSERT OR REPLACE INTO vehicles ({', '.join(columns)}) VALUES ({placeholders})",
                        values
                    )
                    return
            except Exception:
                pass  # 回退到基本插入

        cursor.execute(
            "INSERT OR IGNORE INTO vehicles (vehicle_id, vehicle_model) VALUES (?, ?)",
            (vehicle_id, vehicle_id)
        )

    def _ensure_component_exists(self, cursor: sqlite3.Cursor,
                                 channel_code: str, component_name: str, unit: str):
        """确保部件信息存在"""
        cursor.execute(
            """INSERT OR IGNORE INTO components
               (channel_code, component_name, unit) VALUES (?, ?, ?)""",
            (channel_code, component_name, unit)
        )

    def _ensure_condition_exists(self, cursor: sqlite3.Cursor,
                                 condition_id: str, condition_name: str, soc_level: str):
        """确保工况信息存在"""
        effective_name = condition_name or condition_id
        cursor.execute(
            """INSERT OR IGNORE INTO test_conditions
               (condition_id, condition_name, soc_level) VALUES (?, ?, ?)""",
            (condition_id, effective_name, soc_level or 'UNKNOWN')
        )

        # 智能更新：新名称有意义且比现有值更好时覆盖
        if condition_name and condition_name != condition_id:
            cursor.execute("""
                UPDATE test_conditions
                SET condition_name = ?
                WHERE condition_id = ? AND (condition_name = '' OR condition_name = condition_id)
            """, (condition_name, condition_id))
