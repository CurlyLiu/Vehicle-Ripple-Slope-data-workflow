"""
工况规则版本管理系统

功能:
1. 版本化规则加载 (支持 @import 指令)
2. 批量规则升级/回滚
3. 规则版本审计
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RuleVersion:
    """规则版本信息"""
    name: str
    version: str
    file_path: Path
    date: str
    count: int
    changelog: str


class VersionedRuleLoader:
    """
    版本化规则加载器

    支持两种规则文件格式:
    1. @import 指令: 引用标准规则并本地覆盖
    2. 完整规则: 传统模式，文件内容为全部规则

    加载优先级:
    1. 本地覆盖规则 (车辆文件夹)
    2. 引用的标准规则指定版本
    3. 默认最新标准规则
    """

    def __init__(self, skills_dir: str = "C:/Users/31915/.claude/skills"):
        self.skills_dir = Path(skills_dir)
        self.ripple_refs = self.skills_dir / "vehicle-ripple-data" / "references"
        self.versions = self._load_versions()

    def _load_versions(self) -> Dict:
        """加载版本元数据"""
        versions_path = self.ripple_refs / "versions.json"
        if versions_path.exists():
            with open(versions_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_rules(self, rule_name: str, vehicle_folder: str) -> Tuple[Dict, Dict]:
        """
        加载规则（兼容三种格式）

        格式识别优先级:
        1. @import 指令 -> 加载指定版本标准规则 + 本地覆盖
        2. YAML frontmatter -> 加载指定版本标准规则 + 本地覆盖
        3. 传统完整规则 -> 文件内容即全部规则（完全兼容现有文件）

        Returns:
            (rules_dict, metadata)
        """
        vehicle_folder = Path(vehicle_folder)
        local_rule = vehicle_folder / f"{rule_name}.md"

        metadata = {
            "rule_name": rule_name,
            "vehicle_folder": str(vehicle_folder),
        }

        if not local_rule.exists():
            rules = self._load_default_rules(rule_name)
            metadata.update({
                "source": "default_latest",
                "version": self.versions.get(rule_name, {}).get("current", "unknown"),
                "local_overrides": 0,
            })
            return rules, metadata

        content = self._read_file(local_rule)

        import_match = re.match(
            r'^\s*@import\s+(\S+):(\S+)(?:@([\d.]+))?\s*(?:\n|$)',
            content, re.MULTILINE
        )

        if import_match:
            skill_name, rule_ref, version = import_match.groups()
            version = version or self.versions.get(rule_name, {}).get("current")

            base_rules = self._load_rules_by_version(rule_name, version)
            local_content = content[import_match.end():]
            local_overrides = self._parse_rules(rule_name, local_content)

            rules = {**base_rules, **local_overrides}

            metadata.update({
                "source": f"imported@{version}",
                "version": version,
                "local_overrides": len(local_overrides),
            })
            return rules, metadata

        frontmatter_match = re.match(
            r'^---\s*\n(.*?)\n---\s*\n',
            content, re.DOTALL
        )

        if frontmatter_match:
            try:
                import yaml
                fm = yaml.safe_load(frontmatter_match.group(1))
                version = fm.get("version")
                extends = fm.get("extends", True)

                if extends and version:
                    base_rules = self._load_rules_by_version(rule_name, version)
                    local_content = content[frontmatter_match.end():]
                    local_overrides = self._parse_rules(rule_name, local_content)
                    rules = {**base_rules, **local_overrides}
                    metadata.update({
                        "source": f"frontmatter@{version}",
                        "version": version,
                        "local_overrides": len(local_overrides),
                    })
                    return rules, metadata
            except ImportError:
                pass

        rules = self._parse_rules(rule_name, content)
        metadata.update({
            "source": "local_full",
            "version": "local",
            "local_overrides": len(rules),
        })
        return rules, metadata

    def _read_file(self, path: Path) -> str:
        """读取文件，支持 UTF-8 / GBK 编码"""
        for encoding in ['utf-8', 'gbk']:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法解码文件: {path}")

    def _load_default_rules(self, rule_name: str) -> Dict:
        """加载最新默认规则"""
        default_path = self.ripple_refs / f"{rule_name}.md"
        return self._parse_rules(rule_name, self._read_file(default_path))

    def _load_rules_by_version(self, rule_name: str, version: str) -> Dict:
        """按版本加载规则"""
        version_info = self.versions.get(rule_name, {}).get("versions", {}).get(version)

        if version_info:
            rule_path = self.ripple_refs / version_info["file"]
        else:
            rule_path = self.ripple_refs / f"{rule_name}.md"

        return self._parse_rules(rule_name, self._read_file(rule_path))

    def _parse_rules(self, rule_name: str, content: str) -> Dict:
        """解析规则文件内容为字典"""
        if rule_name == "test_naming_rules":
            return self._parse_test_rules(content)
        elif rule_name == "sensor_naming_rules":
            return self._parse_sensor_rules(content)
        else:
            return {}

    def _parse_test_rules(self, content: str) -> Dict[str, Dict]:
        """解析 test_naming_rules 的 Markdown 表格格式"""
        rules = {}
        lines = content.split('\n')
        for line in lines:
            if '|' in line and not line.startswith('|---') and not line.startswith('|:--'):
                parts = line.split('|')
                if len(parts) >= 4:
                    soc_level = parts[1].strip()
                    condition_name = parts[2].strip()
                    example_naming = parts[3].strip()
                    if (soc_level and soc_level not in ['电量状态', 'SOC Level'] and
                        condition_name not in ['工况名称', 'Condition Name']):
                        condition_id = example_naming
                        if condition_id:
                            rules[condition_id] = {
                                'condition_name': condition_name,
                                'soc_level': soc_level,
                            }
        return rules

    def _parse_sensor_rules(self, content: str) -> Dict[str, Dict]:
        """解析 sensor_naming_rules 的 Markdown 格式（支持冒号和表格两种）"""
        rules = {}
        lines = content.split('\n')
        for line in lines:
            if not line.strip() or line.startswith('#') or line.startswith('---'):
                continue

            if ':' in line and '|' not in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    channel_code = parts[0].strip()
                    component_name = parts[1].strip()
                    if (channel_code and '_' in channel_code and
                        not channel_code.startswith('Channel') and
                        not channel_code.startswith('通道')):
                        unit = 'A' if channel_code.endswith('_A') else 'V'
                        rules[channel_code] = {
                            'component_name': component_name,
                            'unit': unit
                        }
            elif '|' in line and not line.startswith('|---') and not line.startswith('|:--'):
                parts = line.split('|')
                if len(parts) >= 3:
                    channel_code = parts[1].strip()
                    component_name = parts[2].strip()
                    if (channel_code and channel_code not in ['Channel', '通道'] and
                        '_' in channel_code):
                        unit = 'A' if channel_code.endswith('_A') else 'V'
                        rules[channel_code] = {
                            'component_name': component_name,
                            'unit': unit
                        }
        return rules

    def list_versions(self, rule_name: str) -> List[RuleVersion]:
        """列出某规则的所有可用版本"""
        versions = []
        for ver_str, info in self.versions.get(rule_name, {}).get("versions", {}).items():
            versions.append(RuleVersion(
                name=rule_name,
                version=ver_str,
                file_path=self.ripple_refs / info["file"],
                date=info.get("date", "unknown"),
                count=info.get("conditions_count", info.get("channels", 0)),
                changelog=info.get("changelog", "")
            ))
        return sorted(versions, key=lambda v: v.version)

    def get_current_version(self, rule_name: str) -> str:
        """获取当前最新版本号"""
        return self.versions.get(rule_name, {}).get("current", "unknown")


class RuleManager:
    """
    规则管理器
    提供批量升级、回滚、审计功能
    """

    def __init__(self, skills_dir: str = "C:/Users/31915/.claude/skills"):
        self.loader = VersionedRuleLoader(skills_dir)
        self.ripple_refs = Path(skills_dir) / "vehicle-ripple-data" / "references"

    def upgrade_vehicle(self, vehicle_folder: str, rule_name: str,
                        target_version: Optional[str] = None) -> Dict:
        """
        升级单个车辆的规则到指定版本
        """
        vehicle_folder = Path(vehicle_folder)
        target_version = target_version or self.loader.get_current_version(rule_name)

        current_rules, current_meta = self.loader.load_rules(rule_name, str(vehicle_folder))
        current_version = current_meta.get("version", "unknown")
        current_source = current_meta.get("source", "unknown")

        if current_source == "local_full":
            return {
                "status": "unchanged",
                "vehicle_id": vehicle_folder.name,
                "rule_name": rule_name,
                "version": current_version,
                "reason": "传统格式(local_full)不自动升级，请手动改为@import格式后重试",
            }

        if current_version == target_version:
            return {
                "status": "unchanged",
                "vehicle_id": vehicle_folder.name,
                "rule_name": rule_name,
                "version": current_version,
            }

        new_content = f"@import vehicle-ripple-data:{rule_name}@{target_version}\n\n"

        local_overrides = current_meta.get("local_overrides", 0)
        if local_overrides > 0:
            new_content += "# 本地自定义规则 (继承自旧版本)\n"
            new_content += "# TODO: 请审核以下规则是否仍然适用\n\n"

        rule_path = vehicle_folder / f"{rule_name}.md"
        with open(rule_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return {
            "status": "upgraded",
            "vehicle_id": vehicle_folder.name,
            "rule_name": rule_name,
            "from_version": current_version,
            "to_version": target_version,
        }

    def batch_upgrade(self, base_dir: str, rule_name: str,
                      target_version: Optional[str] = None) -> List[Dict]:
        """批量升级某目录下所有车辆的规则"""
        base_dir = Path(base_dir)
        if not base_dir.exists():
            return [{"status": "error", "reason": f"目录不存在: {base_dir}"}]

        results = []

        for vehicle_dir in base_dir.iterdir():
            if not vehicle_dir.is_dir():
                continue

            has_vehicle = (
                (vehicle_dir / f"{vehicle_dir.name}_RIPPLE").exists() or
                (vehicle_dir / "vehicle_info.md").exists()
            )

            if has_vehicle:
                result = self.upgrade_vehicle(str(vehicle_dir), rule_name, target_version)
                results.append(result)

        return results

    def audit(self, base_dir: str) -> List[Dict]:
        """审计所有车辆的规则版本"""
        base_dir = Path(base_dir)
        if not base_dir.exists():
            return [{"vehicle_id": "N/A", "error": f"目录不存在: {base_dir}"}]

        results = []

        for vehicle_dir in base_dir.iterdir():
            if not vehicle_dir.is_dir():
                continue

            has_vehicle = (
                (vehicle_dir / f"{vehicle_dir.name}_RIPPLE").exists() or
                (vehicle_dir / "vehicle_info.md").exists()
            )

            if not has_vehicle:
                continue

            vehicle_result = {
                "vehicle_id": vehicle_dir.name,
                "rules": {}
            }

            for rule_name in ["test_naming_rules", "sensor_naming_rules"]:
                try:
                    _, meta = self.loader.load_rules(rule_name, str(vehicle_dir))
                    vehicle_result["rules"][rule_name] = {
                        "version": meta.get("version", "unknown"),
                        "source": meta.get("source", "unknown"),
                        "current": meta.get("version") == self.loader.get_current_version(rule_name),
                    }
                except Exception as e:
                    vehicle_result["rules"][rule_name] = {
                        "version": "error",
                        "error": str(e),
                    }

            results.append(vehicle_result)

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="工况规则版本管理器")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    list_parser = subparsers.add_parser("list-versions", help="列出可用版本")
    list_parser.add_argument("rule_name", choices=["test_naming_rules", "sensor_naming_rules"])

    upgrade_parser = subparsers.add_parser("upgrade", help="升级车辆规则")
    upgrade_parser.add_argument("vehicle_folder", help="车辆文件夹路径")
    upgrade_parser.add_argument("--rule", required=True,
                                choices=["test_naming_rules", "sensor_naming_rules"])
    upgrade_parser.add_argument("--to", help="目标版本 (默认最新)")

    batch_parser = subparsers.add_parser("batch-upgrade", help="批量升级")
    batch_parser.add_argument("--scan", required=True, help="扫描目录")
    batch_parser.add_argument("--rule", required=True,
                              choices=["test_naming_rules", "sensor_naming_rules"])
    batch_parser.add_argument("--to", help="目标版本 (默认最新)")

    audit_parser = subparsers.add_parser("audit", help="审计规则版本")
    audit_parser.add_argument("--scan", required=True, help="扫描目录")

    args = parser.parse_args()

    manager = RuleManager()

    if args.command == "list-versions":
        versions = manager.loader.list_versions(args.rule_name)
        current = manager.loader.get_current_version(args.rule_name)
        print(f"\n{args.rule_name} 可用版本:")
        print(f"{'='*60}")
        for v in versions:
            marker = " <- 当前最新" if v.version == current else ""
            print(f"v{v.version}{marker}")
            print(f"  日期: {v.date}")
            print(f"  数量: {v.count}")
            print(f"  变更: {v.changelog}")
            print()

    elif args.command == "upgrade":
        result = manager.upgrade_vehicle(args.vehicle_folder, args.rule, args.to)
        print(f"\n升级结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "batch-upgrade":
        results = manager.batch_upgrade(args.scan, args.rule, args.to)

        upgraded = [r for r in results if r["status"] == "upgraded"]
        unchanged = [r for r in results if r["status"] == "unchanged"]
        failed = [r for r in results if r["status"] == "failed"]

        print(f"\n批量升级完成:")
        print(f"  已升级: {len(upgraded)} 辆车")
        print(f"  无需升级: {len(unchanged)} 辆车")
        print(f"  失败: {len(failed)} 辆车")

        if upgraded:
            print(f"\n已升级的车辆:")
            for r in upgraded:
                print(f"  {r['vehicle_id']}: {r['from_version']} -> {r['to_version']}")

    elif args.command == "audit":
        results = manager.audit(args.scan)

        # 检查是否有目录不存在等全局错误
        if results and "error" in results[0]:
            print(f"[ERROR] {results[0]['error']}")
            sys.exit(1)

        print(f"\n{'='*80}")
        print(f"{'车辆ID':<10} {'test_naming':<15} {'sensor_naming':<15} {'状态':<10}")
        print(f"{'='*80}")

        for r in results:
            vid = r["vehicle_id"]

            tn = r["rules"].get("test_naming_rules", {})
            tn_ver = tn.get("version", "N/A")
            tn_current = "Y" if tn.get("current") else "N"

            sn = r["rules"].get("sensor_naming_rules", {})
            sn_ver = sn.get("version", "N/A")
            sn_current = "Y" if sn.get("current") else "N"

            status = "正常" if tn.get("current") and sn.get("current") else "需升级"

            print(f"{vid:<10} {tn_ver+tn_current:<15} {sn_ver+sn_current:<15} {status:<10}")

        print(f"{'='*80}")


if __name__ == "__main__":
    main()
