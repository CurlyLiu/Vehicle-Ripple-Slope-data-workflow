"""纹波报告生成器."""

import os

from .report_generator import ReportGenerator
from ..utils.excel_reader import (
    filter_by_component,
    filter_by_soc,
    load_ripple_data,
)


class RippleReportGenerator(ReportGenerator):
    """纹波报告生成器."""

    report_type_label = "纹波"

    def __init__(self, template_path: str, base_dir: str, component_code: str, prune: bool = True):
        super().__init__(template_path, prune=prune)
        self.base_dir = base_dir
        self.component_code = component_code
        self._all_data = None

    def _is_current_channel(self) -> bool:
        """判断是否为电流通道（以 _A 结尾）."""
        return self.component_code.endswith("_A")

    def load_data(self, vehicle_id: str, component_code: str, soc_level: str) -> list[dict]:
        """加载纹波数据."""
        if self._all_data is None:
            self._all_data = load_ripple_data(vehicle_id, self.base_dir)
        records = filter_by_component(self._all_data, component_code)
        records = filter_by_soc(records, soc_level)
        return records

    def adapt_standard_requirement(self, original_text: str) -> str:
        """电流通道：修改标准要求列文本中的单位和描述."""
        if self._is_current_channel():
            text = original_text.replace("电压纹波", "电流纹波")
            text = text.replace("30Vpp", "100App")
            return text
        return original_text

    def build_result_text(self, item_index: int, matched_data: dict) -> str:
        """生成纹波检验结果文本."""
        if not matched_data:
            return "未找到对应工况数据。"

        parts = []
        for label in ["工况一", "工况二", "工况三"]:
            rec = matched_data.get(label)
            if rec and rec.get("time_vpp") is not None:
                vpp = rec["time_vpp"]
                if self._is_current_channel():
                    parts.append(f"{label}产生电流纹波为{vpp:.2f}App")
                else:
                    parts.append(f"{label}产生电压纹波为{vpp:.2f}Vpp")

        if not parts:
            return "未找到对应工况数据。"

        if self._is_current_channel():
            text = "1#样车" + "，".join(parts) + "。电流纹波峰峰值最大不超过100App。"
        else:
            text = "1#样车" + "，".join(parts) + "。电压纹波峰峰值最大不超过30Vpp。"
        return text

    def build_compliance(self, item_index: int, matched_data: dict) -> str:
        """纹波符合性判定：电压通道 <= 30Vpp，电流通道 <= 100App."""
        if not matched_data:
            return "—"

        threshold = 100 if self._is_current_channel() else 30
        for rec in matched_data.values():
            vpp = rec.get("time_vpp")
            if vpp is not None and vpp > threshold:
                return "不符合"
        return "符合"


def generate_ripple_report(
    vehicle_id: str,
    component_code: str,
    base_dir: str,
    template_path: str,
    output_path: str,
    prune: bool = True,
) -> None:
    """生成纹波报告的便捷函数."""
    generator = RippleReportGenerator(template_path, base_dir, component_code, prune=prune)
    generator.generate(vehicle_id, component_code, output_path)
