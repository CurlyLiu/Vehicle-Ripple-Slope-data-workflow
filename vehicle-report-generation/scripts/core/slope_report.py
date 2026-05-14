"""斜率报告生成器."""

from .report_generator import ReportGenerator
from ..utils.excel_reader import (
    filter_by_component,
    filter_by_soc,
    load_slope_data,
)


class SlopeReportGenerator(ReportGenerator):
    """斜率报告生成器."""

    report_type_label = "斜率"

    def __init__(self, template_path: str, base_dir: str, component_code: str, prune: bool = True):
        super().__init__(template_path, prune=prune)
        self.base_dir = base_dir
        self.component_code = component_code
        self._all_data = None

    def _is_current_channel(self) -> bool:
        """判断是否为电流通道（以 _A 结尾）."""
        return self.component_code.endswith("_A")

    def load_data(self, vehicle_id: str, component_code: str, soc_level: str) -> list[dict]:
        """加载斜率数据."""
        if self._all_data is None:
            self._all_data = load_slope_data(vehicle_id, self.base_dir)
        records = filter_by_component(self._all_data, component_code)
        records = filter_by_soc(records, soc_level)
        return records

    def build_result_text(self, item_index: int, matched_data: dict) -> str:
        """生成斜率检验结果文本 (NEW-5 v1.5 修订:加最大值绝对值措辞+末尾阈值断言)."""
        if not matched_data:
            return "未找到对应工况数据。"

        parts = []
        for label in ["工况一", "工况二", "工况三"]:
            rec = matched_data.get(label)
            if rec and rec.get("slope_max_abs") is not None:
                slope = rec["slope_max_abs"]
                if self._is_current_channel():
                    parts.append(f"{label}产生电流斜率最大值绝对值为{slope:.2f}A/s")
                else:
                    parts.append(f"{label}产生电压斜率最大值绝对值为{slope:.2f}V/s")

        if not parts:
            return "未找到对应工况数据。"

        if self._is_current_channel():
            text = "1#样车" + "，".join(parts) + "。电流斜率最大值绝对值不超过20000A/s。"
        else:
            text = "1#样车" + "，".join(parts) + "。电压斜率最大值绝对值不超过20000V/s。"
        return text

    def build_compliance(self, item_index: int, matched_data: dict) -> str:
        """斜率符合性判定:电压通道 ≤20000V/s,电流通道 ≤20000A/s (NEW-5 v1.5 修订).

        与 ripple_report.build_compliance 结构对称,仅阈值不同。
        阈值: 20000 (电压电流单位均为 V/s 或 A/s,由 _is_current_channel 区分)。
        """
        if not matched_data:
            return "—"

        threshold = 20000
        for rec in matched_data.values():
            slope = rec.get("slope_max_abs")
            if slope is not None and abs(slope) > threshold:
                return "不符合"
        return "符合"

    def adapt_standard_requirement(self, original_text: str) -> str:
        """斜率报告:把 ripple 阈值句替换为 slope 阈值句 (NEW-5 v1.5 修订, R6+ 修订).

        模板内容 (ripple 副本) 用全角逗号: "电压纹波，电压纹波峰峰值最大应不超过30Vpp。"
        R6+ 修订: 直接对 ripple 原文做整句替换 (而非先把电压换电流再替换 100App),
        避免"电流纹波,电流纹波峰峰值"残留。

        阈值: 电压 20000 V/s,电流 20000 A/s (用户 2026-05-12 提供)。
        """
        text = original_text
        if self._is_current_channel():
            # 电流通道: 直接从 ripple 模板原文 (电压纹波/30Vpp) 替换为电流斜率句
            # 半角逗号版本
            text = text.replace(
                "电压纹波,电压纹波峰峰值最大应不超过30Vpp",
                "电流斜率,电流斜率最大值绝对值不超过20000A/s"
            )
            # 全角逗号版本 (模板实际用此)
            text = text.replace(
                "电压纹波，电压纹波峰峰值最大应不超过30Vpp",
                "电流斜率,电流斜率最大值绝对值不超过20000A/s"
            )
            # "采集...电压纹波" → "采集...电流斜率"
            text = text.replace(
                "采集整车高压内网产生的电压纹波",
                "采集整车高压内网产生的电流斜率"
            )
            # 兜底:剩余 "电压纹波" / "电流纹波" 字面全部改为 "电流斜率"
            text = text.replace("电压纹波", "电流斜率")
            text = text.replace("电流纹波", "电流斜率")
            # 兜底数字单位
            text = text.replace("峰峰值", "最大值绝对值")
            text = text.replace("30Vpp", "20000A/s")
            text = text.replace("100App", "20000A/s")
        else:
            # 电压通道: ripple "电压纹波/30Vpp" → slope "电压斜率/20000V/s"
            text = text.replace(
                "电压纹波,电压纹波峰峰值最大应不超过30Vpp",
                "电压斜率,电压斜率最大值绝对值不超过20000V/s"
            )
            text = text.replace(
                "电压纹波，电压纹波峰峰值最大应不超过30Vpp",
                "电压斜率,电压斜率最大值绝对值不超过20000V/s"
            )
            text = text.replace(
                "采集整车高压内网产生的电压纹波",
                "采集整车高压内网产生的电压斜率"
            )
            # 兜底:剩余 "电压纹波" 字面全部改为 "电压斜率"
            text = text.replace("电压纹波", "电压斜率")
            # 兜底数字单位
            text = text.replace("峰峰值", "最大值绝对值")
            text = text.replace("30Vpp", "20000V/s")
        return text


def generate_slope_report(
    vehicle_id: str,
    component_code: str,
    base_dir: str,
    template_path: str,
    output_path: str,
    prune: bool = True,
) -> None:
    """生成斜率报告的便捷函数."""
    generator = SlopeReportGenerator(template_path, base_dir, component_code, prune=prune)
    generator.generate(vehicle_id, component_code, output_path)
