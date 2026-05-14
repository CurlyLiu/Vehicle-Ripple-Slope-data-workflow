#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆纹波数据增量处理与差异检测模块
实现智能增量更新，只处理变化的文件，提升重复处理效率

核心功能:
    1. SHA-256指纹缓存 - 检测文件变化
    2. 增量处理 - 只处理变化的组件
    3. 差异检测 - 对比前后两次处理结果
    4. 差异报告 - 生成详细的变更报告

使用方法:
    from incremental_processor import IncrementalProcessor

    processor = IncrementalProcessor("V0001")
    new, modified, deleted = processor.detect_changes()

    if processor.should_process_component("LV_V"):
        process_component("LV_V")

    processor.update_cache(processed_files)

    # 生成差异报告
    diff_report = processor.generate_diff_report(prev_data, curr_data)
    processor.save_diff_report(diff_report)
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

import pandas as pd


class IncrementalProcessor:
    """
    增量处理器

    通过SHA-256指纹缓存机制，实现:
    - 快速检测文件变化
    - 只处理变化的组件
    - 生成详细的差异报告
    """
    
    def __init__(self, vehicle_folder: str):
        """
        初始化增量处理器
        
        参数:
            vehicle_folder: 车辆文件夹路径
        """
        self.vehicle_folder = Path(vehicle_folder)
        # 提取vehicle_id用于构建缓存目录路径
        vehicle_id = self._extract_vehicle_id(self.vehicle_folder.name)
        output_folder_name = f"{vehicle_id}_RIPPLE_output"
        self.cache_dir = self.vehicle_folder / output_folder_name / ".cache"
        self.cache_file = self.cache_dir / "processing_cache.json"
        self.state_file = self.cache_dir / "last_state.json"
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 提取vehicle_id（支持{VehID}_RIPPLE和VehID格式）
        self.vehicle_id = self._extract_vehicle_id(self.vehicle_folder.name)
        
        # 加载缓存
        self.cache = self._load_cache()
        self.last_state = self._load_last_state()
        
        # 变化追踪
        self.changed_files: List[Path] = []
        self.changed_components: Set[str] = set()
        
    def _extract_vehicle_id(self, folder_name: str) -> str:
        """
        从文件夹名称提取车辆ID
        支持格式:
          - {VehicleID}_RIPPLE (推荐) → 返回 VehicleID
          - {VehicleID} (legacy) → 返回 VehicleID
        
        示例:
          - V0001_RIPPLE → V0001
          - V0002_RIPPLE → V0002
          - V0001 → V0001
        """
        if folder_name.endswith('_RIPPLE'):
            return folder_name[:-7]  # 去掉 '_RIPPLE' 后缀
        return folder_name
    
    def _load_cache(self) -> Dict:
        """加载SHA-256缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告: 无法加载缓存文件: {e}")
                return {}
        return {}
    
    def _load_last_state(self) -> Dict:
        """加载上次处理状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """保存SHA-256缓存 (v1.6 hotfix P1.3: 原子写 tmp+fsync+os.replace + .bak 备份)."""
        self._atomic_save_json(self.cache_file, self.cache)

    def _save_last_state(self, state: Dict) -> None:
        """保存处理状态 (v1.6 hotfix P1.3: 原子写)."""
        self._atomic_save_json(self.state_file, state)

    def _atomic_save_json(self, target_path: Path, data: Dict) -> None:
        """原子写 JSON (v1.6 hotfix P1.3): tmp + fsync + os.replace + .bak 备份 + Windows retry.

        断电/Ctrl+C 时:
        - target 保持原文件 (未污染)
        - 旧 .bak 可作为最后一次成功写入的恢复点
        """
        # 1. .bak 备份
        if target_path.exists():
            try:
                bak = target_path.with_suffix(target_path.suffix + '.bak')
                shutil.copy2(target_path, bak)
            except Exception:
                pass  # .bak 失败不阻塞主写入

        # 2. tmp + fsync + os.replace
        tmp_fd, tmp_str = tempfile.mkstemp(
            suffix='.tmp', prefix=target_path.name + '_', dir=str(target_path.parent)
        )
        tmp_path = Path(tmp_str)
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Windows 锁文件 (antivirus 等) retry
            for attempt in range(3):
                try:
                    os.replace(str(tmp_path), str(target_path))
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.1)
        except Exception as e:
            print(f"警告: 无法保存 {target_path.name}: {e}")
        finally:
            # 清理残留 tmp (os.replace 成功后 tmp_path 已不存在)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """
        计算文件SHA-256哈希值

        参数:
            file_path: 文件路径
        返回:
            SHA-256哈希字符串
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"警告: 无法计算 {file_path} 的SHA-256: {e}")
            return ""
    
    def detect_changes(self) -> Tuple[List[Path], List[Path], List[Path]]:
        """
        检测文件变化
        
        扫描所有相关文件，对比MD5哈希值，识别:
        - 新增文件
        - 修改文件  
        - 删除文件
        
        返回:
            (新增文件列表, 修改文件列表, 删除文件列表)
        """
        print("\n[增量更新] 检测文件变化...")
        
        new_files: List[Path] = []
        modified_files: List[Path] = []
        deleted_files: List[Path] = []
        
        current_files: Dict[str, str] = {}
        current_components: Set[str] = set()
        
        # 扫描所有相关文件
        file_patterns = [
            "vehicle_info.md",
            "vehicle_info.xlsx",
            "test_naming_rules.md",
            "test_naming_rules.xlsx",
            "sensor_naming_rules.md",
            "sensor_naming_rules.xlsx",
            "*/statistics.xlsx",
            "*/*.png",
            "*/*.jpg"
        ]
        
        for pattern in file_patterns:
            for file_path in self.vehicle_folder.rglob(pattern):
                # 跳过缓存目录
                if ".cache" in str(file_path) or "__pycache__" in str(file_path):
                    continue
                
                # 跳过输出目录 (e.g., V0001_RIPPLE_output)
                if "_RIPPLE_output" in str(file_path):
                    continue
                
                rel_path = str(file_path.relative_to(self.vehicle_folder))
                current_files[rel_path] = self._calculate_sha256(file_path)
                
                # 记录组件文件夹
                if file_path.parent != self.vehicle_folder:
                    comp_name = file_path.parent.name
                    current_components.add(comp_name)
        
        # 对比缓存，识别变化
        for rel_path, current_hash in current_files.items():
            if rel_path not in self.cache:
                # 新增文件
                new_files.append(self.vehicle_folder / rel_path)
            elif self.cache[rel_path] != current_hash:
                # 修改文件
                modified_files.append(self.vehicle_folder / rel_path)
        
        # 识别删除的文件
        for cached_path in self.cache:
            if cached_path.startswith("_"):  # 跳过元数据
                continue
            if cached_path not in current_files:
                deleted_files.append(self.vehicle_folder / cached_path)
        
        # 保存变化列表
        self.changed_files = new_files + modified_files
        
        # 识别受影响的组件
        for file_path in self.changed_files:
            if file_path.parent != self.vehicle_folder:
                self.changed_components.add(file_path.parent.name)
        
        # 打印统计
        print(f"  新增文件: {len(new_files)} 个")
        print(f"  修改文件: {len(modified_files)} 个")
        print(f"  删除文件: {len(deleted_files)} 个")
        print(f"  受影响组件: {len(self.changed_components)} 个")
        
        if self.changed_components:
            print(f"  组件列表: {', '.join(sorted(self.changed_components))}")
        
        return new_files, modified_files, deleted_files
    
    def should_process_component(self, component_name: str) -> bool:
        """
        判断组件是否需要重新处理
        
        参数:
            component_name: 组件名称（如"LV_V"）
        返回:
            是否需要处理
        """
        # 如果没有缓存，处理所有组件
        if not self.cache:
            return True
        
        # 如果该组件有文件变化，需要处理
        if component_name in self.changed_components:
            return True
        
        # 检查组件文件夹是否存在
        comp_folder = self.vehicle_folder / component_name
        if not comp_folder.exists():
            return False
        
        return False
    
    def get_components_to_process(self, all_components: List[str]) -> List[str]:
        """
        获取需要处理的组件列表
        
        参数:
            all_components: 所有可用组件列表
        返回:
            需要处理的组件列表
        """
        if not self.cache:
            # 首次处理，处理所有组件
            return all_components
        
        to_process = []
        for comp in all_components:
            if self.should_process_component(comp):
                to_process.append(comp)
        
        return to_process
    
    def update_cache(self, processed_files: Optional[List[Path]] = None) -> None:
        """
        更新已处理文件的缓存

        参数:
            processed_files: 已处理的文件列表（可选，默认扫描所有文件）
        """
        print("\n[增量更新] 更新缓存...")
        
        if processed_files is None:
            # 扫描所有文件
            processed_files = []
            for pattern in ["*/statistics.xlsx", "*/*.png", "*/*.jpg"]:
                processed_files.extend(self.vehicle_folder.rglob(pattern))
        
        # 更新缓存
        update_count = 0
        for file_path in processed_files:
            if ".cache" in str(file_path):
                continue

            rel_path = str(file_path.relative_to(self.vehicle_folder))
            self.cache[rel_path] = self._calculate_sha256(file_path)
            update_count += 1
        
        # 添加元数据 (v1.6 hotfix P3.3: 持久化时间戳带 UTC)
        self.cache["_last_processed"] = datetime.now(timezone.utc).isoformat()
        self.cache["_version"] = "1.0"
        
        # 保存缓存
        self._save_cache()
        print(f"  已更新 {update_count} 个文件的缓存")
    
    def save_processing_state(self, result_data: Dict) -> None:
        """
        保存处理状态用于下次差异对比

        参数:
            result_data: 处理结果数据（如JSON输出）
        """
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),  # v1.6 hotfix P3.3
            "vehicle_id": result_data.get("vehicle", {}).get("vehicle_id", ""),
            "total_components": len(result_data.get("components", {})),
            "total_conditions": sum(
                len(comp.get("conditions", {}))
                for comp in result_data.get("components", {}).values()
            ),
            "data_hash": hashlib.sha256(
                json.dumps(result_data, sort_keys=True).encode()
            ).hexdigest()[:16]
        }
        
        self._save_last_state(state)
    
    def generate_diff_report(self, previous_data: Dict, current_data: Dict) -> str:
        """
        生成详细的差异报告
        
        对比两次处理结果，识别所有变更:
        - 新增/删除的组件
        - 新增/删除的工况
        - 数值变化
        
        参数:
            previous_data: 上次处理的数据
            current_data: 本次处理的数据
        返回:
            Markdown格式的差异报告
        """
        lines = []
        lines.append("# 车辆数据差异报告")
        lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"\n---\n")
        
        # 车辆信息变更
        prev_vehicle = previous_data.get("vehicle", {})
        curr_vehicle = current_data.get("vehicle", {})
        
        if prev_vehicle != curr_vehicle:
            lines.append("\n## 车辆信息变更")
            prev_info = prev_vehicle.get("vehicle_info", {})
            curr_info = curr_vehicle.get("vehicle_info", {})
            
            all_keys = set(prev_info.keys()) | set(curr_info.keys())
            changes = []
            for key in sorted(all_keys):
                prev_val = prev_info.get(key)
                curr_val = curr_info.get(key)
                if prev_val != curr_val:
                    changes.append(f"- **{key}**: `{prev_val}` → `{curr_val}`")
            
            if changes:
                lines.extend(changes)
            else:
                lines.append("- 车辆信息无实质性变更")
        
        # 组件级别变更
        prev_components = previous_data.get("components", {})
        curr_components = current_data.get("components", {})
        
        # 新增组件
        new_components = set(curr_components.keys()) - set(prev_components.keys())
        if new_components:
            lines.append(f"\n## 新增组件 ({len(new_components)}个)")
            for comp in sorted(new_components):
                comp_data = curr_components[comp]
                cond_count = len(comp_data.get("conditions", {}))
                lines.append(f"- **{comp}**: {comp_data.get('component_name', '')} ({cond_count}个工况)")
        
        # 删除组件
        removed_components = set(prev_components.keys()) - set(curr_components.keys())
        if removed_components:
            lines.append(f"\n## 删除组件 ({len(removed_components)}个)")
            for comp in sorted(removed_components):
                lines.append(f"- **{comp}**")
        
        # 组件内部变更
        lines.append("\n## 组件数据变更")
        
        for comp_name in sorted(set(prev_components.keys()) & set(curr_components.keys())):
            prev_comp = prev_components[comp_name]
            curr_comp = curr_components[comp_name]
            
            prev_conditions = prev_comp.get("conditions", {})
            curr_conditions = curr_comp.get("conditions", {})
            
            comp_changes = []
            
            # 新增工况
            new_conditions = set(curr_conditions.keys()) - set(prev_conditions.keys())
            if new_conditions:
                comp_changes.append(f"- 新增工况: {len(new_conditions)}个")
                for cond in sorted(new_conditions)[:5]:
                    comp_changes.append(f"  - {cond}")
                if len(new_conditions) > 5:
                    comp_changes.append(f"  - ... 还有 {len(new_conditions)-5} 个")
            
            # 删除工况
            removed_conditions = set(prev_conditions.keys()) - set(curr_conditions.keys())
            if removed_conditions:
                comp_changes.append(f"- 删除工况: {len(removed_conditions)}个")
                for cond in sorted(removed_conditions)[:5]:
                    comp_changes.append(f"  - {cond}")
                if len(removed_conditions) > 5:
                    comp_changes.append(f"  - ... 还有 {len(removed_conditions)-5} 个")
            
            # 数值变化
            value_changes = []
            for cond_id in sorted(set(prev_conditions.keys()) & set(curr_conditions.keys())):
                prev_cond = prev_conditions[cond_id]
                curr_cond = curr_conditions[cond_id]
                
                # 对比关键数值
                prev_vpp = prev_cond.get("time_domain", {}).get("vpp")
                curr_vpp = curr_cond.get("time_domain", {}).get("vpp")
                
                if prev_vpp != curr_vpp and prev_vpp is not None and curr_vpp is not None:
                    change_pct = ((curr_vpp - prev_vpp) / prev_vpp * 100) if prev_vpp else 0
                    value_changes.append({
                        "condition": cond_id,
                        "field": "VPP",
                        "prev": prev_vpp,
                        "curr": curr_vpp,
                        "change_pct": change_pct
                    })
            
            if value_changes:
                # 按变化幅度排序，只显示前10个
                value_changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
                comp_changes.append(f"- 数值变化: {len(value_changes)}个工况")
                for item in value_changes[:10]:
                    comp_changes.append(
                        f"  - {item['condition']}: "
                        f"{item['field']} {item['prev']:.4f} → {item['curr']:.4f} "
                        f"({item['change_pct']:+.1f}%)"
                    )
                if len(value_changes) > 10:
                    comp_changes.append(f"  - ... 还有 {len(value_changes)-10} 个变化")
            
            if comp_changes:
                lines.append(f"\n### {comp_name}")
                lines.extend(comp_changes)
        
        # 统计摘要
        lines.append("\n---\n")
        lines.append("## 统计摘要")
        lines.append(f"- 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- 组件总数: {len(curr_components)} (上次: {len(prev_components)})")
        lines.append(f"- 新增组件: {len(new_components)}")
        lines.append(f"- 删除组件: {len(removed_components)}")
        
        total_curr_conditions = sum(
            len(comp.get("conditions", {}))
            for comp in curr_components.values()
        )
        total_prev_conditions = sum(
            len(comp.get("conditions", {}))
            for comp in prev_components.values()
        )
        lines.append(f"- 工况总数: {total_curr_conditions} (上次: {total_prev_conditions})")
        
        return "\n".join(lines)
    
    def save_diff_report(self, report: str, suffix: str = "") -> Path:
        """
        保存差异报告
        
        参数:
            report: 报告内容
            suffix: 文件名后缀（可选）
        返回:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            filename = f"diff_report_{suffix}_{timestamp}.md"
        else:
            filename = f"diff_report_{timestamp}.md"
        
        report_file = self.cache_dir.parent / filename
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report_file
    
    def get_processing_summary(self) -> Dict:
        """
        获取处理摘要信息
        
        返回:
            包含缓存状态、上次处理时间等信息的字典
        """
        last_processed = self.cache.get("_last_processed", "从未")
        
        return {
            "cache_exists": bool(self.cache),
            "last_processed": last_processed,
            "cached_files": len([k for k in self.cache.keys() if not k.startswith("_")]),
            "cache_version": self.cache.get("_version", "unknown"),
            "changed_components": list(self.changed_components),
            "changed_files_count": len(self.changed_files)
        }


# 便捷的函数接口
def process_with_incremental(vehicle_folder: str, force_full: bool = False) -> IncrementalProcessor:
    """
    增量处理便捷函数
    
    参数:
        vehicle_folder: 车辆文件夹路径
        force_full: 是否强制全量处理
    返回:
        IncrementalProcessor实例
    """
    processor = IncrementalProcessor(vehicle_folder)
    
    if force_full:
        print("\n[处理模式] 强制全量处理（忽略缓存）")
        processor.changed_components = set()  # 清空变化集合，处理所有
    else:
        new, modified, deleted = processor.detect_changes()
        
        if not new and not modified and not deleted and processor.cache:
            print("\n[OK] 没有检测到文件变化，跳过处理")
            return processor
    
    return processor


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python incremental_processor.py <vehicle_folder>")
        sys.exit(1)
    
    folder = sys.argv[1]
    processor = IncrementalProcessor(folder)
    
    # 检测变化
    new, modified, deleted = processor.detect_changes()
    
    # 打印摘要
    summary = processor.get_processing_summary()
    print("\n处理摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
