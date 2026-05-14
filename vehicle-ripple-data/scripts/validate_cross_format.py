"""
跨阶段数据一致性校验器
在阶段2输出完成后、阶段3导入前自动执行
支持纹波(ripple)和斜率(slope)两种数据类型
"""

import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class ValidationResult:
    """单条校验结果"""
    name: str
    level: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class CrossFormatReport:
    """完整校验报告"""
    vehicle_id: str
    timestamp: str
    results: List[ValidationResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(r.level == 'error' and not r.passed for r in self.results)

    @property
    def has_warnings(self) -> bool:
        return any(r.level == 'warning' and not r.passed for r in self.results)


class CrossFormatValidator:
    """
    跨格式数据一致性校验器

    同时支持纹波(ripple)和斜率(slope)两种数据类型的校验。
    校验 JSON / SQLite / Excel 三份输出的一致性。
    """

    def __init__(self, vehicle_id: str, output_dir: Path, data_type: str = "ripple"):
        self.vehicle_id = vehicle_id
        self.output_dir = Path(output_dir)
        self.data_type = data_type.lower()
        self.results: List[ValidationResult] = []

        type_upper = self.data_type.upper()

        self.json_path = self.output_dir / f"{vehicle_id}_{type_upper}_data.json"
        self.db_path = self.output_dir / f"{vehicle_id}_{type_upper}.db"
        self.excel_path = self.output_dir / f"{vehicle_id}_{type_upper}_summary.xlsx"

        self._config = {
            "ripple": {
                "db_table": "test_results",
                "db_fields": ["vehicle_id", "component_code", "condition_id",
                              "time_vpp", "freq_peak_frequency_khz", "image_path"],
                "db_count_key": "test_results_count",
                "db_rows_key": "test_results",
                "json_value_path": ("time_domain", "vpp"),
                "excel_value_col": "Time VPP",
                "image_required": True,
                "image_coverage_threshold": 0.9,
                "label": "纹波",
            },
            "slope": {
                "db_table": "slope_results",
                "db_fields": ["vehicle_id", "component_code", "condition_id",
                              "slope_max", "slope_min", "slope_max_abs", "image_path"],
                "db_count_key": "slope_results_count",
                "db_rows_key": "slope_results",
                "json_value_path": ("slope", "max_abs_value"),
                "excel_value_col": "Slope Max Abs (V/s)",
                "image_required": False,
                "image_coverage_threshold": 0.3,
                "label": "斜率",
            },
        }[self.data_type]

    def validate(self) -> CrossFormatReport:
        """执行全量校验，返回报告"""
        from datetime import datetime

        self._validate_file_existence()

        if self._has_file_errors():
            return CrossFormatReport(
                vehicle_id=self.vehicle_id,
                timestamp=datetime.now().isoformat(),
                results=self.results
            )

        json_data = self._load_json()
        sqlite_data = self._load_sqlite()
        excel_data = self._load_excel()

        self._validate_record_count(json_data, sqlite_data, excel_data)
        self._validate_component_count(json_data, sqlite_data, excel_data)
        self._validate_vehicle_info(json_data, sqlite_data, excel_data)
        self._validate_condition_coverage(json_data, sqlite_data, excel_data)

        self._validate_image_path_coverage(json_data, sqlite_data)
        self._validate_numeric_precision(json_data, excel_data)
        self._validate_soc_distribution(json_data)
        self._validate_condition_match_confidence(json_data)

        return CrossFormatReport(
            vehicle_id=self.vehicle_id,
            timestamp=datetime.now().isoformat(),
            results=self.results
        )

    def validate_and_report(self) -> bool:
        """
        执行校验并插入 error_report.md 首行

        采用兼容策略: 校验失败不阻断后续阶段，仅将错误报告
        插入到 error_report.md 的最顶部作为醒目标识。

        返回: True=通过, False=有错误 (但调用方不阻断)
        """
        report = self.validate()
        self._insert_at_top_of_error_report(report)

        errors = [r for r in report.results if r.level == 'error' and not r.passed]
        if errors:
            label = self._config['label']
            print(f"  [WARN] {self.vehicle_id} {label}跨阶段校验发现 {len(errors)} 项问题，已写入 error_report.md 首行")

        return not report.has_errors

    def _validate_file_existence(self):
        files = {
            "JSON": self.json_path,
            "SQLite": self.db_path,
            "Excel": self.excel_path,
        }

        for name, path in files.items():
            exists = path.exists()
            size = path.stat().st_size if exists else 0

            self.results.append(ValidationResult(
                name=f"{name}文件存在性",
                level="error",
                passed=exists and size > 0,
                details={"path": str(path), "exists": exists, "size_bytes": size},
                message=f"{name}文件{'缺失' if not exists else '为空' if size == 0 else '正常'}: {path.name}"
            ))

    def _has_file_errors(self) -> bool:
        return any(
            r.name.endswith("文件存在性") and not r.passed
            for r in self.results
        )

    def _load_json(self) -> Dict:
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_sqlite(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        data = {}
        cfg = self._config
        table = cfg["db_table"]
        fields = cfg["db_fields"]

        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        data[cfg["db_count_key"]] = cursor.fetchone()[0]

        cursor.execute(f"SELECT {', '.join(fields)} FROM {table}")
        rows = cursor.fetchall()

        row_dicts = []
        for r in rows:
            d = {}
            for i, field in enumerate(fields):
                d[field] = r[i]
            row_dicts.append(d)
        data[cfg["db_rows_key"]] = row_dicts

        cursor.execute("SELECT vehicle_id, vehicle_model FROM vehicles")
        row = cursor.fetchone()
        data["vehicle"] = {"vehicle_id": row[0], "vehicle_model": row[1]} if row else {}

        conn.close()
        return data

    def _load_excel(self) -> Dict:
        if not PANDAS_AVAILABLE:
            return {"sheets": [], "error": "pandas not available"}

        xls = pd.ExcelFile(self.excel_path)
        data = {"sheets": xls.sheet_names}

        if "Vehicle Information" in xls.sheet_names:
            df = pd.read_excel(xls, "Vehicle Information")
            data["vehicle_info"] = df.to_dict()

        if "Component Summary" in xls.sheet_names:
            df = pd.read_excel(xls, "Component Summary")
            data["component_summary"] = df
            data["component_count"] = len(df)

        if "Detailed Results" in xls.sheet_names:
            df = pd.read_excel(xls, "Detailed Results")
            data["detailed_results"] = df
            data["record_count"] = len(df)

        return data

    def _validate_record_count(self, json_data, sqlite_data, excel_data):
        json_count = sum(
            len(comp.get("conditions", {}))
            for comp in json_data.get("components", {}).values()
        )

        sqlite_count = sqlite_data.get(self._config["db_count_key"], 0)

        # pandas 不可用时跳过 Excel 校验
        if "error" in excel_data:
            excel_count = json_count  # 视为一致，跳过比较
        else:
            excel_count = excel_data.get("record_count", 0)

        counts = {"json": json_count, "sqlite": sqlite_count, "excel": excel_count}
        unique_counts = set(v for v in counts.values() if v > 0)
        passed = len(unique_counts) <= 1

        self.results.append(ValidationResult(
            name="记录总数一致性",
            level="error",
            passed=passed,
            details=counts,
            message=f"记录数: JSON={json_count}, SQLite={sqlite_count}, Excel={excel_count}"
                    + (" [OK]" if passed else " [FAIL] 不一致!")
        ))

    def _validate_component_count(self, json_data, sqlite_data, excel_data):
        json_components = set(json_data.get("components", {}).keys())

        sqlite_components = set(
            r["component_code"] for r in sqlite_data.get(self._config["db_rows_key"], [])
        )

        excel_components = set()
        if "error" not in excel_data and "component_summary" in excel_data:
            df = excel_data["component_summary"]
            if "Component Code" in df.columns:
                excel_components = set(df["Component Code"].unique())

        # pandas 不可用时仅比较 JSON 和 SQLite
        if "error" in excel_data:
            passed = json_components == sqlite_components
        else:
            passed = json_components == sqlite_components == excel_components

        self.results.append(ValidationResult(
            name="组件数量一致性",
            level="error",
            passed=passed,
            details={
                "json_count": len(json_components),
                "sqlite_count": len(sqlite_components),
                "excel_count": len(excel_components),
                "json_only": list(json_components - sqlite_components - excel_components),
                "sqlite_only": list(sqlite_components - json_components - excel_components),
                "excel_only": list(excel_components - json_components - sqlite_components),
            },
            message=f"组件数: JSON={len(json_components)}, SQLite={len(sqlite_components)}, Excel={len(excel_components)}"
                    + (" (Excel不可用，仅对比JSON/SQLite)" if "error" in excel_data else "")
        ))

    def _validate_vehicle_info(self, json_data, sqlite_data, excel_data):
        json_id = json_data.get("vehicle", {}).get("vehicle_id")
        sqlite_id = sqlite_data.get("vehicle", {}).get("vehicle_id")

        passed = (json_id == sqlite_id == self.vehicle_id)

        self.results.append(ValidationResult(
            name="车辆ID一致性",
            level="error",
            passed=passed,
            details={"json": json_id, "sqlite": sqlite_id, "expected": self.vehicle_id},
            message=f"车辆ID: JSON={json_id}, SQLite={sqlite_id}, 期望={self.vehicle_id}"
        ))

    def _validate_condition_coverage(self, json_data, sqlite_data, excel_data):
        json_conditions = set()
        for comp_code, comp in json_data.get("components", {}).items():
            for cond_id in comp.get("conditions", {}).keys():
                json_conditions.add((comp_code, cond_id))

        excel_conditions = set()
        if "error" not in excel_data and "detailed_results" in excel_data:
            df = excel_data["detailed_results"]
            for _, row in df.iterrows():
                excel_conditions.add((row.get("Component"), row.get("Condition ID")))

        # pandas 不可用时跳过 Excel 比较
        if "error" in excel_data:
            passed = True
            missing_in_excel = []
            extra_in_excel = []
        else:
            missing_in_excel = json_conditions - excel_conditions
            extra_in_excel = excel_conditions - json_conditions
            passed = len(missing_in_excel) == 0 and len(extra_in_excel) == 0

        self.results.append(ValidationResult(
            name="工况覆盖一致性",
            level="error",
            passed=passed,
            details={
                "json_total": len(json_conditions),
                "excel_total": len(excel_conditions),
                "missing_in_excel": list(missing_in_excel)[:10],
                "extra_in_excel": list(extra_in_excel)[:10],
            },
            message=f"工况覆盖: JSON={len(json_conditions)}, Excel={len(excel_conditions)}"
                    + (f", Excel缺失{len(missing_in_excel)}条" if missing_in_excel else "")
                    + (" (Excel不可用，跳过对比)" if "error" in excel_data else "")
        ))

    def _validate_image_path_coverage(self, json_data, sqlite_data):
        cfg = self._config
        rows_key = cfg["db_rows_key"]

        json_conditions = []
        for comp in json_data.get("components", {}).values():
            for cond_id, cond in comp.get("conditions", {}).items():
                json_conditions.append(cond.get("image_path"))

        sqlite_paths = [r.get("image_path") for r in sqlite_data.get(rows_key, [])]

        json_with_image = sum(1 for p in json_conditions if p) / max(len(json_conditions), 1)
        sqlite_with_image = sum(1 for p in sqlite_paths if p) / max(len(sqlite_paths), 1)

        threshold = cfg["image_coverage_threshold"]
        passed = json_with_image >= threshold and sqlite_with_image >= threshold

        msg_suffix = f" (低于{threshold:.0%}需关注)" if json_with_image < threshold else ""
        if not cfg["image_required"] and json_with_image == 0:
            msg_suffix = " (斜率图片为可选，无图片属正常)"
            passed = True

        self.results.append(ValidationResult(
            name="图片路径覆盖率",
            level="warning",
            passed=passed,
            details={
                "json_coverage": f"{json_with_image:.1%}",
                "sqlite_coverage": f"{sqlite_with_image:.1%}",
                "threshold": f"{threshold:.0%}",
                "image_required": cfg["image_required"],
            },
            message=f"图片覆盖率: JSON={json_with_image:.1%}, SQLite={sqlite_with_image:.1%}{msg_suffix}"
        ))

    def _validate_numeric_precision(self, json_data, excel_data):
        if "error" in excel_data or "detailed_results" not in excel_data:
            return

        df = excel_data["detailed_results"]
        cfg = self._config
        json_path = cfg["json_value_path"]
        excel_col = cfg["excel_value_col"]
        label = cfg["label"]

        sample_issues = []
        sample_count = 0

        for comp_code, comp in list(json_data.get("components", {}).items())[:5]:
            for cond_id, cond in list(comp.get("conditions", {}).items())[:3]:
                sample_count += 1

                match = df[(df["Component"] == comp_code) &
                           (df["Condition ID"] == cond_id)]

                if match.empty:
                    continue

                excel_row = match.iloc[0]

                json_val = cond
                for key in json_path:
                    json_val = json_val.get(key) if isinstance(json_val, dict) else None

                excel_val = excel_row.get(excel_col)

                if json_val is not None and excel_val is not None:
                    try:
                        diff = abs(float(json_val) - float(excel_val))
                        if diff > 0.01:
                            sample_issues.append({
                                "component": comp_code,
                                "condition": cond_id,
                                "json": json_val,
                                "excel": excel_val,
                                "diff": diff
                            })
                    except (ValueError, TypeError):
                        pass

        self.results.append(ValidationResult(
            name="数值精度一致性",
            level="warning",
            passed=len(sample_issues) == 0,
            details={
                "sampled": sample_count,
                "issues_found": len(sample_issues),
                "issue_examples": sample_issues[:3],
            },
            message=f"{label}数值精度: 抽样{sample_count}条"
                    + (f", 发现{len(sample_issues)}条差异>0.01" if sample_issues else ", 无差异")
        ))

    def _validate_soc_distribution(self, json_data):
        soc_levels = {"≥70%": 0, "40%-70%": 0, "≤40%": 0, "Unknown": 0}

        for comp in json_data.get("components", {}).values():
            for cond in comp.get("conditions", {}).values():
                level = cond.get("soc_level", "Unknown")
                soc_levels[level] = soc_levels.get(level, 0) + 1

        total = sum(soc_levels.values())
        max_ratio = max(soc_levels.values()) / max(total, 1)

        self.results.append(ValidationResult(
            name="SOC分级分布",
            level="warning",
            passed=max_ratio < 0.9,
            details={k: f"{v} ({v/max(total,1):.1%})" for k, v in soc_levels.items()},
            message=f"SOC分布: {soc_levels}"
                    + (" (分布不均，建议检查)" if max_ratio >= 0.9 else "")
        ))

    def _validate_condition_match_confidence(self, json_data):
        low_confidence = []

        for comp_code, comp in json_data.get("components", {}).items():
            for cond_id, cond in comp.get("conditions", {}).items():
                confidence = cond.get("match_confidence", 1.0)
                if confidence < 0.8:
                    low_confidence.append({
                        "condition_id": cond_id,
                        "condition_name": cond.get("condition_name", "N/A"),
                        "confidence": confidence
                    })

        total_conditions = sum(
            len(comp.get("conditions", {}))
            for comp in json_data.get("components", {}).values()
        )

        self.results.append(ValidationResult(
            name="工况匹配置信度",
            level="warning",
            passed=len(low_confidence) / max(total_conditions, 1) < 0.1,
            details={
                "total": total_conditions,
                "low_confidence_count": len(low_confidence),
                "examples": low_confidence[:5],
            },
            message=f"工况匹配: 共{total_conditions}条, 低置信度(<0.8){len(low_confidence)}条"
        ))

    def _insert_at_top_of_error_report(self, report: CrossFormatReport):
        """写入校验块到 error_report.md 首部 (sentinel upsert,避免重复累积)。

        使用 HTML 注释 sentinel 包裹本块:
          <!-- cross-format-validation:start -->
          ...校验内容...
          <!-- cross-format-validation:end -->

        若文件已存在该 sentinel 块,替换整段;否则 prepend。
        """
        error_report_path = self.output_dir / "error_report.md"
        label = self._config['label']

        sentinel_start = "<!-- cross-format-validation:start -->\n"
        sentinel_end = "<!-- cross-format-validation:end -->\n"

        lines = [sentinel_start]
        lines.append(f"# {label}跨阶段数据一致性校验报告\n\n")
        lines.append(f"**校验时间**: {report.timestamp}\n\n")
        lines.append(f"**校验结果**: {'全部通过' if not report.has_errors else '发现问题 (见下方详情)'}\n\n")
        lines.append("> **注意**: 本校验仅用于提示，不阻断后续阶段执行。如发现问题，请自行判断是否修复后重跑阶段2。\n\n")

        errors = [r for r in report.results if r.level == 'error' and not r.passed]
        if errors:
            lines.append("### 错误项\n\n")
            for r in errors:
                lines.append(f"- **{r.name}**: {r.message}\n")
            lines.append("\n")

        warnings = [r for r in report.results if r.level == 'warning' and not r.passed]
        if warnings:
            lines.append("### 警告项\n\n")
            for r in warnings:
                lines.append(f"- **{r.name}**: {r.message}\n")
            lines.append("\n")

        passed_items = [r for r in report.results if r.passed]
        if passed_items:
            lines.append("### 通过的校验项\n\n")
            for r in passed_items:
                lines.append(f"- {r.name}: {r.message}\n")
            lines.append("\n")

        lines.append("---\n\n")
        lines.append(sentinel_end)
        new_block = "".join(lines)

        existing_content = ""
        if error_report_path.exists():
            with open(error_report_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        # Sentinel upsert: 若已存在校验块,替换整段;否则 prepend
        if sentinel_start in existing_content and sentinel_end in existing_content:
            start_idx = existing_content.find(sentinel_start)
            end_idx = existing_content.find(sentinel_end) + len(sentinel_end)
            updated_content = (
                existing_content[:start_idx]
                + new_block
                + existing_content[end_idx:]
            )
        else:
            updated_content = new_block + existing_content

        with open(error_report_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="跨阶段数据一致性校验器 (支持纹波/斜率)")
    parser.add_argument("--vehicle-id", required=True, help="车辆ID")
    parser.add_argument("--output-dir", required=True, help="阶段2输出目录")
    parser.add_argument("--type", choices=["ripple", "slope"], default="ripple",
                        help="数据类型 (默认: ripple)")
    parser.add_argument("--strict", action="store_true",
                        help="严格模式: 警告也视为失败")

    args = parser.parse_args()

    validator = CrossFormatValidator(args.vehicle_id, Path(args.output_dir), args.type)

    passed = validator.validate_and_report()

    errors = [r for r in validator.results if r.level == 'error' and not r.passed]
    warnings = [r for r in validator.results if r.level == 'warning' and not r.passed]
    passed_items = [r for r in validator.results if r.passed]

    label = "纹波" if args.type == "ripple" else "斜率"
    print(f"\n{'='*60}")
    print(f"车辆 {args.vehicle_id} {label}跨阶段一致性校验结果")
    print(f"{'='*60}")
    print(f"错误: {len(errors)} 项")
    print(f"警告: {len(warnings)} 项")
    print(f"通过: {len(passed_items)} 项")
    print(f"{'='*60}")

    if errors:
        print("\n发现错误 (已写入 error_report.md 首行):")
        for e in errors:
            print(f"  - {e.name}: {e.message}")
        print("\n采用兼容策略，流程继续执行。请人工确认是否修复后重跑阶段2。")

    if warnings and not errors:
        print("\n有警告，但可继续:")
        for w in warnings:
            print(f"  - {w.name}: {w.message}")

    if not errors and not warnings:
        print("\n全部通过，可以安全进入阶段3")

    if args.strict and warnings:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
