"""
Excel数据导入器
支持从Excel汇总文件导入数据
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from .base import BaseImporter, ImportResult


# Cache for config.yaml import settings
_IMPORT_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _load_import_config() -> Dict[str, Any]:
    """Load import configuration from project-level config.yaml."""
    global _IMPORT_CONFIG_CACHE
    if _IMPORT_CONFIG_CACHE is not None:
        return _IMPORT_CONFIG_CACHE
    try:
        import yaml
    except ImportError:
        _IMPORT_CONFIG_CACHE = {}
        return _IMPORT_CONFIG_CACHE
    config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f) or {}
                _IMPORT_CONFIG_CACHE = full_config.get("import", {})
                return _IMPORT_CONFIG_CACHE
        except (OSError, yaml.YAMLError):
            pass
    _IMPORT_CONFIG_CACHE = {}
    return _IMPORT_CONFIG_CACHE


class ExcelImporter(BaseImporter):
    """Excel格式数据导入器"""

    def can_import(self, file_path: Path) -> bool:
        """检查是否为Excel文件"""
        if not EXCEL_AVAILABLE:
            return False
        return file_path.suffix.lower() in ['.xlsx', '.xls']

    def import_data(self, conn: sqlite3.Connection, vehicle_id: str, file_path: Path) -> ImportResult:
        """从Excel文件导入数据"""
        if not EXCEL_AVAILABLE:
            return ImportResult(
                vehicle_id=vehicle_id,
                data_type='unknown',
                errors=["pandas not installed. Run: pip install pandas openpyxl"]
            )

        result = ImportResult(vehicle_id=vehicle_id, data_type='unknown')

        try:
            # 确定数据类型
            data_type = self.detect_data_type(file_path)
            result.data_type = data_type or 'unknown'

            # 读取所有sheet
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names

            # 查找Detailed Results sheet
            detailed_sheet = None
            for name in sheet_names:
                if 'detailed' in name.lower() or '详细' in name:
                    detailed_sheet = name
                    break

            if not detailed_sheet and len(sheet_names) >= 3:
                # 通常第三个sheet是Detailed Results
                detailed_sheet = sheet_names[2]

            if detailed_sheet:
                df = pd.read_excel(file_path, sheet_name=detailed_sheet)
                self._import_from_dataframe(conn, vehicle_id, data_type, df, result)

            # 导入批次记录
            self._import_batch(conn, vehicle_id, result.data_type, file_path, result)

            # NEW-1 v1.4: 不在 importer 内部 commit,由外层 with DatabaseConnection 控制

        except (KeyboardInterrupt, SystemExit):
            # VDB-C1 v1.4 修订: 不 rollback,让外层 with 处理
            raise
        except (OSError, sqlite3.Error, ValueError, KeyError, AttributeError,
                TypeError, UnicodeDecodeError, IndexError) as e:
            # VDB-C1 v1.4 修订: 记录错误后必须 raise,否则 with 会 commit DELETE
            result.errors.append(f"Import failed ({type(e).__name__}): {str(e)}")
            raise
        except Exception as e:
            # NEW-2 v1.4: pandas.errors.* 等 (ParserError/EmptyDataError) 不是 OSError 子类
            result.errors.append(f"Unexpected import error ({type(e).__name__}): {str(e)}")
            raise

        return result

    def _import_from_dataframe(self, conn: sqlite3.Connection, vehicle_id: str,
                               data_type: str, df: pd.DataFrame, result: ImportResult) -> None:
        """从DataFrame导入数据"""

        # 标准化列名
        df.columns = [str(col).strip() for col in df.columns]

        # 映射列名
        column_mapping = self._detect_column_mapping(df.columns)

        if not column_mapping:
            result.errors.append("Could not detect column mapping")
            return

        # 获取或创建车辆信息
        self._ensure_vehicle_exists(conn, vehicle_id)

        # 遍历每一行导入
        for _, row in df.iterrows():
            try:
                component_code = self._get_value(row, column_mapping.get('component', 'Component'))
                condition_name = self._get_value(row, column_mapping.get('condition', 'Condition Name'))

                if not component_code or not condition_name:
                    continue

                # 标准化组件代码
                component_code = str(component_code).strip()

                # 插入部件定义
                self._import_component_from_row(conn, component_code)

                # C3 v1.6 hotfix: 优先使用Excel中已存在的condition_id列(与JSON/SQLite一致),
                # 避免从condition_name重新生成导致 `-` `（` `）` 被规范化为 `_`,
                # 与 JSON 导入的原始 ID 形成重复记录。
                # 旧版本 _generate_condition_id 会把 "28_滑行120-40" 转成 "28_滑行120_40"
                excel_cond_id = self._get_value(row, column_mapping.get('condition_id'))
                if excel_cond_id is not None:
                    condition_id = str(excel_cond_id).strip()
                else:
                    # 仅当 Excel 中不存在 condition_id 列时,才从 condition_name 生成
                    # (保留以兼容老版本汇总文件)
                    condition_id = self._generate_condition_id(condition_name)

                # 插入工况定义
                self._import_condition_from_row(conn, condition_id, condition_name, row, column_mapping)

                # 根据数据类型导入结果
                if data_type == 'ripple':
                    self._import_ripple_from_row(conn, vehicle_id, component_code, condition_id, row, column_mapping)
                elif data_type == 'slope':
                    self._import_slope_from_row(conn, vehicle_id, component_code, condition_id, row, column_mapping)

                result.conditions_imported += 1

            except (ValueError, TypeError) as e:
                result.warnings.append(f"Row import warning: {e}")
                continue

        # 统计组件数量
        if 'component' in column_mapping:
            components = df[column_mapping['component']].unique()
            result.components_imported = len([c for c in components if pd.notna(c)])

    def _detect_column_mapping(self, columns: list) -> Dict[str, str]:
        """Detect column mapping using config.yaml variants with built-in defaults."""
        mapping = {}
        config = _load_import_config()
        column_variants = config.get("column_variants", {
            'component': ['Component', '部件', 'component_code', 'Channel', '通道'],
            'condition': ['Condition Name', '工况名称', 'Condition', 'condition_name'],
            'condition_id': ['Condition ID', '工况ID', 'condition_id'],
            # C10/C11 v1.6 hotfix: 增加 SOC Level 列识别,
            # 优先从 Excel 现有列读取(已由 vehicle-ripple-data 正确计算),
            # 避免再走 _infer_soc_level 的关键词匹配(命中率低,导致 70% 行为"未知")
            'soc_level': ['SOC Level', 'SOC 等级', 'soc_level', 'SOC'],
            'vpp': ['Vpp', 'Vpp(V)', '峰峰值', 'Vpp Value'],
            'frequency': ['Freq(kHz)', 'Frequency', '频率', 'Peak Freq'],
            'amplitude': ['Amplitude', '幅值', 'Peak Amp'],
            'slope_max': ['Slope Max', '斜率最大', 'Max Slope'],
            'slope_min': ['Slope Min', '斜率最小', 'Min Slope'],
            'slope_max_abs': ['Slope Max Abs', '斜率绝对值最大', 'Max Abs Slope'],
        })

        for standard_name, variants in column_variants.items():
            best_match_col = None
            best_match_len = 0
            for col in columns:
                col_str = str(col).strip()
                col_lower = col_str.lower()
                for variant in variants:
                    v_lower = variant.lower()
                    if v_lower in col_lower and len(v_lower) > best_match_len:
                        best_match_col = col_str
                        best_match_len = len(v_lower)
            if best_match_col:
                mapping[standard_name] = best_match_col

        return mapping

    def _get_value(self, row: pd.Series, column_name: Optional[str], default=None):
        """安全获取值"""
        if not column_name or column_name not in row.index:
            return default
        value = row[column_name]
        if pd.isna(value):
            return default
        return value

    def _import_component_from_row(self, conn: sqlite3.Connection, component_code: str) -> None:
        """从行数据导入部件"""
        component_type = 'voltage' if component_code.endswith('_V') else 'current'
        unit = 'V' if component_code.endswith('_V') else 'A'

        # 尝试从命名规则推断部件名称
        component_name = self._infer_component_name(component_code)

        conn.execute("""
            INSERT OR IGNORE INTO components (channel_code, component_name, component_type, unit)
            VALUES (?, ?, ?, ?)
        """, (component_code, component_name, component_type, unit))

    def _infer_component_name(self, component_code: str) -> str:
        """Infer component display name from config.yaml or fallback to code itself."""
        config = _load_import_config()
        name_map = config.get("component_names", {})
        return name_map.get(component_code, component_code)

    def _generate_condition_id(self, condition_name: str) -> str:
        """Generate a safe condition ID from the condition name.

        C3 v1.6 hotfix: \u4ec5\u5728 Excel \u4e0d\u5b58\u5728 condition_id \u5217\u65f6\u4f7f\u7528(\u5411\u540e\u517c\u5bb9).
        \u65b0\u6d41\u7a0b\u901a\u8fc7 column_mapping['condition_id'] \u76f4\u63a5\u8bfb\u53d6\u539f\u59cb ID,\u907f\u514d\u89c4\u8303\u5316\u53d8\u4f53.
        """
        clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', str(condition_name))
        return clean_name[:50]

    def _import_condition_from_row(self, conn: sqlite3.Connection, condition_id: str,
                                   condition_name: str, row: pd.Series, mapping: Dict) -> None:
        """Import condition definition with inferred SOC level and category.

        C10/C11 v1.6 hotfix: SOC 级别提取按以下优先级:
          1. Excel 中的 SOC Level 列(若存在,且为标准格式 ≥70%/40%-70%/≤40%)
          2. 从 condition_id 提取 SOC 数字(支持 `_`, `-`, ` ` 分隔符 + 坡度前缀)
          3. fallback 到关键词匹配(_infer_soc_level)
        旧逻辑直接 fallback 到关键词匹配,导致 70% 工况 SOC 为"未知"。
        """
        # 1. 优先读 Excel 的 SOC Level 列
        excel_soc = self._get_value(row, mapping.get('soc_level'))
        if excel_soc is not None:
            soc_level = self._normalize_soc_label(str(excel_soc).strip())
        else:
            # 2. 从 condition_id 提取 SOC
            soc_level = self._extract_soc_from_id(condition_id)
            # 3. fallback
            if soc_level == "未知":
                soc_level = self._infer_soc_level(condition_name)

        category = self._infer_category(condition_name)

        conn.execute("""
            INSERT OR IGNORE INTO test_conditions (condition_id, condition_name, soc_level, category)
            VALUES (?, ?, ?, ?)
        """, (condition_id, condition_name, soc_level, category))

        # 智能更新：新名称有意义且比现有值更好时覆盖
        if condition_name and condition_name != condition_id:
            conn.execute("""
                UPDATE test_conditions
                SET condition_name = ?
                WHERE condition_id = ? AND (condition_name = '' OR condition_name = condition_id)
            """, (condition_name, condition_id))

    @staticmethod
    def _normalize_soc_label(label: str) -> str:
        """规范化 SOC 标签为标准全角形式(§13.6 P1.1 MED-5 规范).

        映射规则:
          ">=70%", "≥70%", ">=70" → "≥70%"
          "<=40%", "≤40%", "<=40" → "≤40%"
          "40-70%", "40%-70%", "40%~70%" → "40%-70%"
          其他 → 原值(可能是 "未知" / "Unknown")
        """
        if not label:
            return "未知"
        s = label.replace(" ", "")
        # 高 SOC
        if "≥70" in s or ">=70" in s or ">70" in s:
            return "≥70%"
        # 低 SOC
        if "≤40" in s or "<=40" in s or "<40" in s:
            return "≤40%"
        # 中 SOC: 包含 40 和 70 (顺序不严)
        if "40" in s and "70" in s and ("-" in s or "~" in s or "至" in s):
            return "40%-70%"
        # 已经是标准格式
        if s in ("≥70%", "40%-70%", "≤40%"):
            return s
        # 未识别
        return label if label else "未知"

    @staticmethod
    def _extract_soc_from_id(condition_id: str) -> str:
        """从 condition_id 提取 SOC 等级 (与 vehicle_processor._extract_soc 逻辑一致).

        支持格式:
          坡度10_82_匀速80暖风 → SOC=82 → "≥70%"
          坡度10 26_匀速80冷风 → SOC=26 → "≤40%"
          15_交流充电冷风 → SOC=15 → "≤40%"
          55_停车D档暖风 → SOC=55 → "40%-70%"
        """
        if not condition_id:
            return "未知"
        # 坡度前缀(支持标准/GBK乱码,容忍多种分隔符)
        slope_pat = re.compile(r'^(坡度|�¶�)\s*10(?![0-9])[_\-\s]*(\d+)[_\-\s]', re.IGNORECASE)
        m = slope_pat.match(condition_id)
        if m:
            soc = int(m.group(2))
        else:
            # 普通工况
            m = re.match(r'^(\d+)[_\-\s]', condition_id)
            if not m:
                return "未知"
            soc = int(m.group(1))
        if soc >= 70:
            return "≥70%"
        elif soc >= 40:
            return "40%-70%"
        else:
            return "≤40%"

    def _infer_soc_level(self, condition_name: str) -> str:
        """Infer SOC level from condition name using config.yaml rules.

        注意: 这是最后的 fallback,实际优先级在 _import_condition_from_row:
          1. Excel 的 SOC Level 列 (_normalize_soc_label)
          2. condition_id 的数字前缀 (_extract_soc_from_id)
          3. 当前函数 (关键词匹配,命中率极低)
        """
        config = _load_import_config()
        rules = config.get("soc_levels", [
            {"keywords": ["≥70", ">=70", "高电量"], "label": "≥70%"},
            {"keywords": ["≤40", "<=40", "低电量"], "label": "≤40%"},
            {"keywords": ["40-70", "中电量"], "label": "40%-70%"},
        ])
        name = str(condition_name)
        for rule in rules:
            if any(kw in name for kw in rule.get("keywords", [])):
                return rule.get("label", "未知")
        return "未知"

    def _infer_category(self, condition_name: str) -> str:
        """Infer condition category from condition name using config.yaml rules."""
        config = _load_import_config()
        categories = config.get("categories", {
            "充电": ["充电", "快充", "慢充"],
            "制动": ["刹车", "制动"],
            "加速": ["加速", "超车"],
            "气候": ["暖风", "冷风", "空调"],
            "爬坡": ["爬坡", "坡度"],
            "巡航": ["滑行", "匀速", "巡航"],
        })
        name = str(condition_name)
        for category, keywords in categories.items():
            if any(kw in name for kw in keywords):
                return category
        return "其他"

    def _import_ripple_from_row(self, conn: sqlite3.Connection, vehicle_id: str,
                                component_code: str, condition_id: str,
                                row: pd.Series, mapping: Dict) -> None:
        """导入纹波结果"""
        vpp = self._get_value(row, mapping.get('vpp'))
        freq = self._get_value(row, mapping.get('frequency'))
        amp = self._get_value(row, mapping.get('amplitude'))

        conn.execute("""
            INSERT OR REPLACE INTO ripple_results
            (vehicle_id, component_code, condition_id, vpp_value, peak_frequency_khz,
             peak_amplitude, raw_data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id, component_code, condition_id,
            float(vpp) if vpp is not None else None,
            float(freq) if freq is not None else None,
            float(amp) if amp is not None else None,
            json.dumps(row.to_dict(), ensure_ascii=False)
        ))

    def _import_slope_from_row(self, conn: sqlite3.Connection, vehicle_id: str,
                               component_code: str, condition_id: str,
                               row: pd.Series, mapping: Dict) -> None:
        """导入斜率结果"""
        slope_max = self._get_value(row, mapping.get('slope_max'))
        slope_min = self._get_value(row, mapping.get('slope_min'))
        slope_max_abs = self._get_value(row, mapping.get('slope_max_abs'))

        # 如果没有max_abs，计算它
        if slope_max_abs is None and slope_max is not None and slope_min is not None:
            slope_max_abs = max(abs(float(slope_max)), abs(float(slope_min)))

        conn.execute("""
            INSERT OR REPLACE INTO slope_results
            (vehicle_id, component_code, condition_id, slope_max, slope_min,
             slope_max_abs, slope_unit, raw_data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id, component_code, condition_id,
            float(slope_max) if slope_max is not None else None,
            float(slope_min) if slope_min is not None else None,
            float(slope_max_abs) if slope_max_abs is not None else None,
            'V/s',
            json.dumps(row.to_dict(), ensure_ascii=False)
        ))

    def _ensure_vehicle_exists(self, conn: sqlite3.Connection, vehicle_id: str) -> None:
        """确保车辆记录存在"""
        conn.execute("""
            INSERT OR IGNORE INTO vehicles (vehicle_id, vehicle_model)
            VALUES (?, ?)
        """, (vehicle_id, f"Vehicle {vehicle_id}"))

    def _import_batch(self, conn: sqlite3.Connection, vehicle_id: str,
                      data_type: str, file_path: Path, result: ImportResult) -> None:
        """导入批次记录"""
        conn.execute("""
            INSERT INTO data_batches
            (vehicle_id, data_type, source_file, source_folder,
             total_components, total_conditions, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id, data_type, str(file_path), str(file_path.parent),
            result.components_imported, result.conditions_imported,
            'completed' if result.success else 'failed'
        ))
