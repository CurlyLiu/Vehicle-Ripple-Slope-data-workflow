"""
JSON数据导入器
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .base import BaseImporter, ImportResult


class JsonImporter(BaseImporter):
    """JSON格式数据导入器"""

    def can_import(self, file_path: Path) -> bool:
        """检查是否为JSON文件"""
        return file_path.suffix.lower() == '.json'

    def import_data(self, conn: sqlite3.Connection, vehicle_id: str, file_path: Path) -> ImportResult:
        """从JSON文件导入数据"""
        result = ImportResult(vehicle_id=vehicle_id, data_type='unknown')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 确定数据类型
            metadata = data.get('metadata', {})
            data_type = metadata.get('data_type', self.detect_data_type(Path(file_path)))
            result.data_type = data_type or 'unknown'

            # 导入车辆信息
            self._import_vehicle(conn, data)

            # 导入部件和测试结果
            components = data.get('components', {})
            for comp_code, comp_data in components.items():
                self._import_component(conn, comp_code, comp_data)

                conditions = comp_data.get('conditions', {})
                for cond_id, cond_data in conditions.items():
                    self._import_condition(conn, cond_id, cond_data)

                    if data_type == 'ripple':
                        self._import_ripple_result(
                            conn, vehicle_id, comp_code, cond_id, cond_data
                        )
                    elif data_type == 'slope':
                        self._import_slope_result(
                            conn, vehicle_id, comp_code, cond_id, cond_data
                        )

                    result.conditions_imported += 1

                result.components_imported += 1

            # 导入批次记录
            self._import_batch(conn, vehicle_id, result.data_type, file_path, metadata, result)

            # NEW-1 v1.4: 不在 importer 内部 commit,由外层 with DatabaseConnection 控制
            # 这确保 _delete_vehicle + import 等多步操作的原子性 (避免 update.py 半成功)

        except (KeyboardInterrupt, SystemExit):
            # VDB-C1 v1.4 修订: 不调用 conn.rollback() (会破坏外层事务边界)
            # 让异常向上传播,由外层 with DatabaseConnection.__exit__ 统一 rollback
            raise
        except (json.JSONDecodeError, KeyError, sqlite3.Error, OSError, ValueError,
                AttributeError, TypeError, UnicodeDecodeError, IndexError) as e:
            # VDB-C1 v1.4 修订: 记录错误后必须 raise,避免 with __exit__ 看到正常退出而 commit
            # 之前: result.errors.append + return → with 不知道失败 → commit DELETE → 数据丢失
            result.errors.append(f"Import failed ({type(e).__name__}): {str(e)}")
            raise
        except Exception as e:
            # NEW-2 v1.4: 兜底 - 任何其他异常也记录 + raise
            result.errors.append(f"Unexpected import error ({type(e).__name__}): {str(e)}")
            raise

        return result

    def _import_vehicle(self, conn: sqlite3.Connection, data: dict) -> None:
        """导入车辆信息"""
        vehicle = data.get('vehicle', {})
        vehicle_id = vehicle.get('vehicle_id')
        vehicle_info = vehicle.get('vehicle_info', {})

        if not vehicle_id:
            return

        conn.execute("""
            INSERT OR REPLACE INTO vehicles (
                vehicle_id, vehicle_model, manufacturer, level, energy_type,
                length_mm, width_mm, height_mm, wheelbase_mm,
                curb_weight_kg, max_weight_kg,
                battery_type, battery_capacity_kwh, fast_charge_power_kw,
                vehicle_info_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            vehicle_info.get('vehicle_model') or vehicle_info.get('车型') or vehicle_id,
            vehicle_info.get('manufacturer') or vehicle_info.get('制造商'),
            vehicle_info.get('级别'),
            vehicle_info.get('能源类型'),
            vehicle_info.get('length_mm'),
            vehicle_info.get('width_mm'),
            vehicle_info.get('height_mm'),
            vehicle_info.get('轴距(mm)'),
            vehicle_info.get('整备质量(kg)'),
            vehicle_info.get('最大满载质量(kg)'),
            vehicle_info.get('电池类型'),
            vehicle_info.get('电池能量(kWh)'),
            vehicle_info.get('快充功率(kW)'),
            json.dumps(vehicle_info, ensure_ascii=False)
        ))

    def _import_component(self, conn: sqlite3.Connection, comp_code: str, comp_data: dict) -> None:
        """导入部件定义"""
        component_type = 'voltage' if comp_code.endswith('_V') else 'current'
        unit = 'V' if comp_code.endswith('_V') else 'A'

        conn.execute("""
            INSERT OR IGNORE INTO components (channel_code, component_name, component_type, unit)
            VALUES (?, ?, ?, ?)
        """, (
            comp_code,
            comp_data.get('component_name', ''),
            component_type,
            unit
        ))

    def _import_condition(self, conn: sqlite3.Connection, cond_id: str, cond_data: dict) -> None:
        """导入工况定义"""
        conn.execute("""
            INSERT OR IGNORE INTO test_conditions (condition_id, condition_name, soc_level, category)
            VALUES (?, ?, ?, ?)
        """, (
            cond_id,
            cond_data.get('condition_name', ''),
            cond_data.get('soc_level', ''),
            self._infer_category(cond_id)
        ))

    def _import_ripple_result(self, conn: sqlite3.Connection, vehicle_id: str,
                              comp_code: str, cond_id: str, cond_data: dict) -> None:
        """导入纹波结果"""
        time_domain = cond_data.get('time_domain', {})
        freq_domain = cond_data.get('frequency_domain', {})

        conn.execute("""
            INSERT OR REPLACE INTO ripple_results (
                vehicle_id, component_code, condition_id,
                time_domain_effective_value, vpp_value,
                peak_ranking_json, peak_frequency_khz, peak_amplitude, frequency_rms,
                image_path, match_confidence, match_method, raw_data_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id, comp_code, cond_id,
            time_domain.get('effective_value'),
            time_domain.get('vpp'),
            json.dumps(freq_domain.get('peak_ranking', {}), ensure_ascii=False) if freq_domain.get('peak_ranking') else None,
            freq_domain.get('peak_frequency_khz'),
            freq_domain.get('peak_amplitude'),
            freq_domain.get('rms'),
            cond_data.get('image_path'),
            cond_data.get('match_confidence'),
            cond_data.get('match_method'),
            json.dumps(cond_data, ensure_ascii=False)
        ))

    def _import_slope_result(self, conn: sqlite3.Connection, vehicle_id: str,
                             comp_code: str, cond_id: str, cond_data: dict) -> None:
        """导入斜率结果"""
        slope = cond_data.get('slope', {})

        conn.execute("""
            INSERT OR REPLACE INTO slope_results (
                vehicle_id, component_code, condition_id,
                slope_max, slope_min, slope_max_abs, slope_unit,
                image_path, match_confidence, match_method, raw_data_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id, comp_code, cond_id,
            slope.get('max_value'),
            slope.get('min_value'),
            slope.get('max_abs_value'),
            slope.get('unit', 'V/s'),
            cond_data.get('image_path'),
            cond_data.get('match_confidence'),
            cond_data.get('match_method'),
            json.dumps(cond_data, ensure_ascii=False)
        ))

    def _import_batch(self, conn: sqlite3.Connection, vehicle_id: str,
                      data_type: str, file_path, metadata: dict,
                      result: ImportResult) -> None:
        """导入批次记录"""
        conn.execute("""
            INSERT INTO data_batches (
                vehicle_id, data_type, source_file, source_folder,
                total_components, total_conditions, warnings_count, errors_count,
                status, warnings_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id, data_type, str(file_path), str(Path(file_path).parent),
            result.components_imported, result.conditions_imported,
            len(metadata.get('warnings', [])),
            len(result.errors),
            'completed' if result.success else 'failed',
            json.dumps(metadata.get('warnings', []), ensure_ascii=False)
        ))

    @staticmethod
    def _infer_category(condition_id: str) -> Optional[str]:
        """从工况ID推断类别"""
        if '充电' in condition_id:
            return '充电'
        elif '刹车' in condition_id or '制动' in condition_id:
            return '制动'
        elif '加速' in condition_id or '超车' in condition_id:
            return '加速'
        elif '暖风' in condition_id or '冷风' in condition_id or '空调' in condition_id:
            return '气候'
        elif '爬坡' in condition_id or '坡度' in condition_id:
            return '爬坡'
        elif '滑行' in condition_id or '匀速' in condition_id:
            return '巡航'
        return '其他'
