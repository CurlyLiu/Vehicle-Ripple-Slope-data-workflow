#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆斜率数据处理 - 核心处理模块

主要功能:
1. 加载和验证车辆信息
2. 加载命名规则（支持合并策略）
3. 发现并验证组件文件夹
4. 处理斜率统计数据
5. 生成JSON、Excel、SQLite输出

示例用法:
    from scripts.slope_processor import SlopeDataProcessor
    
    processor = SlopeDataProcessor("V0001_SLOPE")
    result = processor.process()
    
    processor.generate_excel("V0001_summary.xlsx")
    processor.generate_sqlite("V0001.db")
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# 坡度前缀匹配正则（支持正常文本、GBK乱码、多种分隔符）
_SLOPE_PREFIX_PATTERN = re.compile(
    r'^(坡度|�¶�)\s*10(?![0-9])[_\-\s]*(\d+)[_\-\s]',
    re.IGNORECASE
)

# 普通工况SOC匹配正则（开头的数字 + 任意分隔符）
_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')

# Import condition matcher from ripple-data skill
try:
    from scripts.core.condition_matcher import ConditionMatcher, get_condition_name
except ImportError:
    import sys
    from pathlib import Path
    # Try multiple possible locations for ripple-data
    possible_paths = [
        Path(__file__).parent.parent.parent / 'vehicle-ripple-data',  # From slope scripts
        Path(__file__).parent.parent.parent.parent / 'vehicle-ripple-data',  # From tests
        Path.cwd().parent / 'vehicle-ripple-data',  # From slope root
        Path.cwd().parent.parent / 'vehicle-ripple-data',  # From tests
    ]
    for ripple_path in possible_paths:
        if ripple_path.exists():
            if str(ripple_path) not in sys.path:
                sys.path.insert(0, str(ripple_path))
            try:
                from scripts.core.condition_matcher import ConditionMatcher, get_condition_name
                break
            except ImportError:
                # Try importing from core directly
                core_path = ripple_path / 'scripts' / 'core'
                if str(core_path) not in sys.path:
                    sys.path.insert(0, str(core_path))
                try:
                    from condition_matcher import ConditionMatcher, get_condition_name
                    break
                except ImportError:
                    continue
    else:
        raise ImportError("Cannot find ConditionMatcher from vehicle-ripple-data")

# Import configuration manager
try:
    from config import get_config_manager as get_slope_config_manager
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import get_config_manager as get_slope_config_manager

# Import version utility
try:
    from version_utils import get_slope_version
except ImportError:
    get_slope_version = lambda: "1.2"  # Fallback version


class SlopeDataProcessor:
    """车辆斜率数据处理器"""
    
    def __init__(self, vehicle_folder: str, config: Optional[Dict] = None):
        """
        初始化斜率数据处理器

        参数:
            vehicle_folder: 车辆文件夹路径（支持 {VehID}_SLOPE 或 {VehID} 格式）
                支持传入父文件夹，会自动查找 {VehicleID}_SLOPE 子文件夹
            config: 配置选项
                - generate_json: 是否生成JSON (默认 True)
                - generate_excel: 是否生成Excel (默认 True)
                - generate_sqlite: 是否生成SQLite (默认 True)
                - output_dir: 输出目录（默认: vehicle_folder/SKILL_output）
        """
        input_path = Path(vehicle_folder)
        self.config = {
            'generate_json': True,
            'generate_excel': True,
            'generate_sqlite': True,
            'output_dir': None
        }
        if config:
            self.config.update(config)

        # 自动检测 SLOPE 子文件夹
        if input_path.name.endswith('_SLOPE'):
            # 输入已经是 SLOPE 文件夹
            self.vehicle_folder = input_path
            self.vehicle_id = self._extract_vehicle_id(input_path.name)
        else:
            # 输入可能是父文件夹，尝试查找 SLOPE 子文件夹
            slope_folder = self._find_slope_subfolder(input_path)
            if slope_folder:
                self.vehicle_folder = slope_folder
                self.vehicle_id = self._extract_vehicle_id(slope_folder.name)
                print(f"[信息] 自动检测到 SLOPE 子文件夹: {slope_folder.name}")
            else:
                # 未找到 SLOPE 子文件夹，将输入视为车辆文件夹本身
                self.vehicle_folder = input_path
                self.vehicle_id = self._extract_vehicle_id(input_path.name)

        self.folder_name = self.vehicle_folder.name

        # 设置输出目录: {VehicleID}_SLOPE_output
        if self.config['output_dir']:
            self.output_dir = Path(self.config['output_dir'])
        else:
            self.output_dir = self.vehicle_folder / f"{self.vehicle_id}_SLOPE_output"

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储
        self.vehicle_info: Dict = {}
        self.test_rules: Dict = {}
        self.sensor_rules: Dict = {}
        self.components: Dict = {}
        self.warnings: List[str] = []
        self.errors: List[str] = []
        
        # 配置驱动初始化
        self._init_config_manager()
        
    def _init_config_manager(self) -> None:
        """Initialize configuration manager"""
        try:
            self.config_mgr = get_slope_config_manager(hot_reload=True)
            
            # Load shared configurations from ripple-data
            self.field_config = self.config_mgr.load('common/vehicle_fields')
            self.matching_config = self.config_mgr.load('common/matching_rules')
            
            print("[INFO] Configuration loaded successfully")
            
        except Exception as e:
            print(f"[WARNING] Failed to load configuration: {e}")
            self.config_mgr = None
            self.field_config = None
            self.matching_config = None
    
    def _extract_vehicle_info_with_config(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized vehicle info using configuration
        
        Args:
            raw_data: Raw data parsed from vehicle_info file
            
        Returns:
            Standardized vehicle info dictionary
        """
        standardized = {}
        
        # If config is not available, use raw data as-is
        if not self.field_config:
            return raw_data
        
        # Extract each defined field
        for field_key in self.field_config.get('field_mappings', {}).keys():
            value = self._extract_field_with_config(raw_data, field_key)
            if value is not None:
                standardized[field_key] = value
        
        # Also keep original fields for backward compatibility
        for key, value in raw_data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized
    
    def _extract_field_with_config(self, raw_data: Dict, field_key: str) -> Any:
        """
        Extract field value using configuration
        
        Args:
            raw_data: Raw vehicle info data
            field_key: Target field key (e.g., 'vehicle_model')
            
        Returns:
            Extracted value or default
        """
        if not self.field_config or field_key not in self.field_config.get('field_mappings', {}):
            # Fallback to hardcoded extraction
            return self._extract_field_fallback(raw_data, field_key)
        
        field_def = self.field_config['field_mappings'][field_key]
        extraction = self.field_config.get('extraction', {})
        
        value = None
        
        # Try different source formats in priority order
        for source_type in extraction.get('priority_order', ['standard_format']):
            if source_type not in field_def.get('sources', {}):
                continue
            
            possible_names = field_def['sources'][source_type]
            if isinstance(possible_names, dict):
                # Handle nested sources
                possible_names = [item for sublist in possible_names.values() for item in sublist]
            
            # Try each possible field name
            for name in possible_names:
                # Apply case sensitivity setting
                if not extraction.get('strategy', {}).get('case_sensitive', True):
                    name_lower = name.lower()
                    raw_keys_lower = {k.lower(): v for k, v in raw_data.items()}
                    if name_lower in raw_keys_lower:
                        value = raw_keys_lower[name_lower]
                        break
                else:
                    if name in raw_data:
                        value = raw_data[name]
                        break
            
            if value is not None:
                break
        
        # Post-processing
        if value is not None:
            if extraction.get('post_process', {}).get('strip_whitespace', True):
                value = str(value).strip()
            
            if extraction.get('post_process', {}).get('remove_empty', True) and value == '':
                value = None
        
        # Use default if still None
        if value is None:
            value = field_def.get('default_value')
        
        return value
    
    def _extract_field_fallback(self, raw_data: Dict, field_key: str) -> Any:
        """Fallback field extraction (hardcoded mappings for common vehicle fields)"""
        fallback_mappings = {
            'vehicle_model': ['车型', '参数名称', '车辆型号', 'Model', 'model'],
            'manufacturer': ['制造商', '厂商', '品牌', 'Manufacturer'],
            'length_mm': ['长度(mm)', '车长', '长度', 'Length'],
            'width_mm': ['宽度(mm)', '车宽', '宽度', 'Width'],
            'height_mm': ['高度(mm)', '车高', '高度', 'Height'],
            'wheelbase_mm': ['轴距(mm)', '轴距', 'Wheelbase'],
            'curb_weight_kg': ['整备质量(kg)', '整备质量', 'Curb Weight'],
            'max_speed_kmh': ['最高车速(km/h)', '最高车速', 'Max Speed'],
            'acceleration_0_100': ['0-100加速时间(s)', '0-100加速', 'Acceleration'],
            'motor_power_kw': ['电机功率(kW)', '电机功率', '最大功率', 'Power'],
            'motor_torque_nm': ['电机扭矩(N·m)', '电机扭矩', '最大扭矩', 'Torque'],
            'battery_capacity_kwh': ['电池容量(kWh)', '电池容量', 'Capacity'],
            'battery_type': ['电池类型', '电池'],
            'drive_type': ['驱动方式', '驱动'],
            'front_tire': ['前轮胎规格', '前轮胎', '前轮'],
            'rear_tire': ['后轮胎规格', '后轮胎', '后轮'],
            'vehicle_platform': ['整车平台', '平台', 'Platform'],
        }

        possible_names = fallback_mappings.get(field_key, [field_key])

        for name in possible_names:
            if name in raw_data:
                return raw_data[name]

        return None
        
    def _find_slope_subfolder(self, parent_path: Path) -> Optional[Path]:
        """
        自动检测 SLOPE 子文件夹

        查找符合 {VehicleID}_SLOPE 模式的文件夹

        参数:
            parent_path: 父文件夹路径

        返回:
            SLOPE 子文件夹路径（如果找到），否则返回 None
        """
        if not parent_path.is_dir():
            return None

        # 查找以 _SLOPE 结尾的文件夹
        for item in parent_path.iterdir():
            if item.is_dir() and item.name.endswith('_SLOPE'):
                return item

        return None

    def _extract_vehicle_id(self, folder_name: str) -> str:
        """
        从文件夹名称提取车辆ID

        支持格式:
          - {VehicleID}_SLOPE (推荐) → 返回 VehicleID
          - {VehicleID} (legacy) → 返回 VehicleID

        示例:
          - V0001_SLOPE → V0001
          - V0002_SLOPE → V0002
          - V0001 → V0001
        """
        if folder_name.endswith('_SLOPE'):
            return folder_name[:-6]  # 去掉 '_SLOPE' 后缀
        return folder_name
    
    def process(self) -> Dict:
        """
        主处理流程
        
        返回:
            处理结果字典，包含车辆信息、组件数据、元数据
        """
        version = get_slope_version()
        print(f"\n{'='*80}")
        print(f"车辆电压斜率数据处理工具 v{version}")
        print(f"{'='*80}")
        print(f"车辆文件夹: {self.vehicle_folder.absolute()}")
        print(f"车辆ID: {self.vehicle_id}")
        print(f"输出目录: {self.output_dir.absolute()}\n")
        
        try:
            # 步骤1: 验证车辆文件夹
            print("[步骤1/6] 验证车辆文件夹...")
            self._validate_vehicle_folder()
            print(f"[OK] 文件夹验证通过\n")
            
            # 步骤2: 加载命名规则
            print("[步骤2/6] 加载命名规则...")
            self._load_naming_rules()
            print(f"[OK] 测试规则: {len(self.test_rules)} 个工况")
            print(f"[OK] 传感器规则: {len(self.sensor_rules)} 个通道\n")
            
            # 步骤3: 加载车辆信息
            print("[步骤3/6] 加载车辆信息...")
            self._load_vehicle_info()
            vehicle_model = self.vehicle_info.get('车型') or self.vehicle_info.get('vehicle_model', 'Unknown')
            print(f"[OK] 车辆信息加载完成: {vehicle_model}\n")
            
            # 步骤4: 发现并验证组件
            print("[步骤4/6] 发现并验证组件...")
            component_folders = self._discover_components()
            print(f"[OK] 发现 {len(component_folders)} 个组件文件夹\n")
            
            # 步骤5: 处理组件数据
            print("[步骤5/6] 处理组件数据...")
            self._process_components(component_folders)
            total_conditions = sum(len(comp['conditions']) for comp in self.components.values())
            print(f"[OK] 处理完成: {len(self.components)} 个组件, {total_conditions} 个工况\n")
            
            # 步骤6: 生成输出
            print("[步骤6/6] 生成输出文件...")
            self._generate_outputs()
            print(f"[OK] 输出文件生成完成\n")
            
            # 构建结果
            result = {
                'vehicle': {
                    'vehicle_id': self.vehicle_id,
                    'vehicle_info': self.vehicle_info
                },
                'components': self.components,
                'metadata': {
                    'processing_date': datetime.now(timezone.utc).isoformat(),
                    'total_components': len(self.components),
                    'total_conditions': total_conditions,
                    'data_type': 'slope',
                    'test_naming_rules_source': 'merged',
                    'sensor_naming_rules_source': 'merged',
                    'warnings': self.warnings,
                    'errors': self.errors
                }
            }
            
            print(f"{'='*80}")
            print(f"[DONE] 处理完成!")
            print(f"{'='*80}")
            print(f"车辆ID: {self.vehicle_id}")
            vehicle_model = self.vehicle_info.get('车型') or self.vehicle_info.get('vehicle_model', 'Unknown')
            print(f"车型: {vehicle_model}")
            print(f"组件数: {len(self.components)}")
            print(f"工况数: {total_conditions}")
            
            if self.warnings:
                print(f"\n[WARN] 警告 ({len(self.warnings)}):")
                for warning in self.warnings[:5]:
                    print(f"  - {warning}")
                if len(self.warnings) > 5:
                    print(f"  ... 还有 {len(self.warnings)-5} 个")
            
            return result
            
        except Exception as e:
            self.errors.append(str(e))
            raise
    
    def _validate_vehicle_folder(self) -> None:
        """验证车辆文件夹
        
        检查vehicle_info文件，优先在当前文件夹查找，
        如果找不到，则在父文件夹中查找（适用于{VehID}_SLOPE子文件夹结构）
        """
        if not self.vehicle_folder.exists():
            raise FileNotFoundError(f"车辆文件夹不存在: {self.vehicle_folder}")
        
        # 检查vehicle_info文件（当前文件夹或父文件夹）
        search_paths = [self.vehicle_folder, self.vehicle_folder.parent]
        
        for path in search_paths:
            md_file = path / "vehicle_info.md"
            xlsx_file = path / "vehicle_info.xlsx"
            if md_file.exists() or xlsx_file.exists():
                self.vehicle_info_path = path
                return
        
        raise FileNotFoundError(
            f"缺少vehicle_info文件（需要.md或.xlsx）: {self.vehicle_folder} 或其父文件夹"
        )
    
    def _load_naming_rules(self) -> None:
        """加载命名规则（使用合并策略）"""
        # 首先加载默认规则
        self._load_default_rules()
        
        # 然后加载车辆文件夹中的自定义规则并合并
        self._load_vehicle_rules()
    
    def _load_default_rules(self) -> None:
        """加载默认命名规则"""
        # 获取技能根目录
        skill_root = Path(__file__).parent.parent
        refs_dir = skill_root / "references"
        
        # 加载默认测试命名规则
        test_md = refs_dir / "test_naming_rules.md"
        test_xlsx = refs_dir / "test_naming_rules.xlsx"
        
        if test_md.exists():
            self.test_rules = self._parse_test_rules_md(test_md)
        elif test_xlsx.exists():
            self.test_rules = self._parse_test_rules_xlsx(test_xlsx)
        
        # 加载默认传感器命名规则
        sensor_md = refs_dir / "sensor_naming_rules.md"
        sensor_xlsx = refs_dir / "sensor_naming_rules.xlsx"
        
        if sensor_md.exists():
            self.sensor_rules = self._parse_sensor_rules_md(sensor_md)
        elif sensor_xlsx.exists():
            self.sensor_rules = self._parse_sensor_rules_xlsx(sensor_xlsx)
    
    def _load_vehicle_rules(self) -> None:
        """加载车辆文件夹中的自定义规则并合并

        优先在当前文件夹查找，如找不到则在父文件夹中查找
        """
        # 确定搜索路径（优先当前文件夹，然后是父文件夹）
        search_paths = [self.vehicle_folder, self.vehicle_folder.parent]
        
        # 加载自定义测试命名规则
        vehicle_test_rules = {}
        for path in search_paths:
            test_md = path / "test_naming_rules.md"
            test_xlsx = path / "test_naming_rules.xlsx"
            if test_md.exists():
                vehicle_test_rules = self._parse_test_rules_md(test_md)
                break
            elif test_xlsx.exists():
                vehicle_test_rules = self._parse_test_rules_xlsx(test_xlsx)
                break
        
        # 合并规则（车辆规则优先）
        if vehicle_test_rules:
            self.test_rules.update(vehicle_test_rules)
            self.warnings.append({
                'type': '信息',
                'message': '使用了车辆文件夹中的自定义测试命名规则',
                'component': ''
            })
        
        # 加载自定义传感器命名规则
        vehicle_sensor_rules = {}
        for path in search_paths:
            sensor_md = path / "sensor_naming_rules.md"
            sensor_xlsx = path / "sensor_naming_rules.xlsx"
            if sensor_md.exists():
                vehicle_sensor_rules = self._parse_sensor_rules_md(sensor_md)
                break
            elif sensor_xlsx.exists():
                vehicle_sensor_rules = self._parse_sensor_rules_xlsx(sensor_xlsx)
                break
        
        # 合并规则（车辆规则优先）
        if vehicle_sensor_rules:
            self.sensor_rules.update(vehicle_sensor_rules)
            self.warnings.append({
                'type': '信息',
                'message': '使用了车辆文件夹中的自定义传感器命名规则',
                'component': ''
            })
    
    def _parse_test_rules_md(self, file_path: Path) -> Dict:
        """解析测试命名规则markdown文件"""
        rules = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # 简单解析markdown表格
        lines = content.split('\n')
        in_table = False
        headers = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('|'):
                if not in_table:
                    # 表头行
                    headers = [h.strip() for h in line.split('|')[1:-1]]
                    in_table = True
                elif line.replace('|', '').replace('-', '').replace(':', '').strip():
                    # 数据行
                    values = [v.strip() for v in line.split('|')[1:-1]]
                    if len(values) >= 3 and headers:
                        row = dict(zip(headers, values))
                        condition_id = row.get('数据命名举例', '')
                        if condition_id:
                            rules[condition_id] = {
                                'soc_level': row.get('电量状态', ''),
                                'condition_name': row.get('工况名称', '')
                            }
        
        return rules
    
    def _parse_test_rules_xlsx(self, file_path: Path) -> Dict:
        """解析测试命名规则Excel文件"""
        rules = {}
        try:
            df = pd.read_excel(file_path)
            for _, row in df.iterrows():
                condition_id = row.get('数据命名举例', '')
                if condition_id and pd.notna(condition_id):
                    rules[str(condition_id)] = {
                        'soc_level': str(row.get('电量状态', '')),
                        'condition_name': str(row.get('工况名称', ''))
                    }
        except Exception as e:
            self.warnings.append({
                'type': '错误',
                'message': f'解析测试命名规则Excel失败: {e}',
                'component': ''
            })
        
        return rules
    
    def _parse_sensor_rules_md(self, file_path: Path) -> Dict:
        """解析传感器命名规则markdown文件"""
        rules = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # 解析 "CODE: Description" 格式
        for line in content.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                parts = line.split(':', 1)
                code = parts[0].strip()
                desc = parts[1].strip()
                # 确定单位
                unit = 'A' if code.endswith('_A') else 'V' if code.endswith('_V') else ''
                rules[code] = {
                    'name': desc,
                    'unit': unit
                }
        
        return rules
    
    def _parse_sensor_rules_xlsx(self, file_path: Path) -> Dict:
        """解析传感器命名规则Excel文件"""
        rules = {}
        try:
            df = pd.read_excel(file_path)
            for _, row in df.iterrows():
                code = row.get('通道代码', '')
                if code and pd.notna(code):
                    unit = 'A' if str(code).endswith('_A') else 'V' if str(code).endswith('_V') else ''
                    rules[str(code)] = {
                        'name': str(row.get('描述', '')),
                        'unit': unit
                    }
        except Exception as e:
            self.warnings.append({
                'type': '错误',
                'message': f'解析传感器命名规则Excel失败: {e}',
                'component': ''
            })
        
        return rules
    
    def _load_vehicle_info(self) -> None:
        """加载车辆信息 - 使用配置驱动提取
        
        从 _validate_vehicle_folder 设置的 vehicle_info_path 中加载
        """
        # 使用之前验证时找到的路径
        search_path = getattr(self, 'vehicle_info_path', self.vehicle_folder)
        
        md_file = search_path / "vehicle_info.md"
        xlsx_file = search_path / "vehicle_info.xlsx"
        
        if md_file.exists():
            raw_data = self._parse_vehicle_info_md(md_file)
        elif xlsx_file.exists():
            raw_data = self._parse_vehicle_info_xlsx(xlsx_file)
        else:
            raw_data = {}
        
        # 使用配置驱动提取标准化字段
        self.vehicle_info = self._extract_vehicle_info_with_config(raw_data)
    
    def _parse_vehicle_info_md(self, file_path: Path) -> Dict:
        """解析车辆信息markdown文件
        
        支持格式:
        1. 标准纵向格式:
        | 参数名称 | 参数值 |
        | --- | --- |
        | 车型 | 坦克500 |
        | 车长mm | 5078 |
        
        2. 汽车之家格式（第一行包含车型）:
        | 参数名称 | 北京越野BJ60增程 2024款... |
        | --- | --- |
        | 厂商指导价(元) | 25.98万 |
        ...
        
        3. 横向表格格式（第一行表头，第二行数据）
        """
        info = {}
        
        # 尝试多种编码（优先UTF-8，失败则回退到GBK系列）
        content = None
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                # 成功读取即停止，不再通过内容特征判断（避免GBK文件被误判）
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            # 如果都失败了，使用utf-8并忽略错误
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        # 解析markdown表格
        lines = content.split('\n')
        in_table = False
        headers = []
        data_rows = []
        
        for line in lines:
            line = line.strip()
            if not line.startswith('|'):
                continue
            
            # 跳过分隔行 |---|---|
            if line.replace('|', '').replace('-', '').replace(':', '').replace(' ', '').strip() == '':
                continue
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            if not in_table:
                # 第一行是表头
                headers = cells
                in_table = True
            else:
                # 数据行
                if len(cells) == len(headers):
                    data_rows.append(cells)
        
        # 判断表格格式
        if len(data_rows) == 0:
            return info
        
        # 检查是否是汽车之家格式（第一行第二列包含车型）
        # 例如：| 参数名称 | 北京越野BJ60增程 2024款... |
        # 注意：某些文件有额外的空列，所以用 >= 2 而不是 == 2
        if len(headers) >= 2 and headers[0] == "参数名称" and headers[1] and headers[1] != "参数值":
            # 汽车之家格式：第一行第二列就是车型
            info[headers[0]] = headers[1]
            # 继续解析其他数据行
            for row in data_rows:
                key = row[0]
                value = row[1] if len(row) > 1 else ""
                if key and value:
                    info[key] = value
        elif len(headers) == 2:
            # 标准纵向格式：每行是 |参数名|参数值|
            for row in data_rows:
                key = row[0]
                value = row[1] if len(row) > 1 else ""
                if key and value:
                    info[key] = value
        else:
            # 横向格式：第一行表头，第二行是数据值
            for col_idx, header in enumerate(headers):
                if col_idx < len(data_rows[0]):
                    info[header] = data_rows[0][col_idx]
        
        return info
    
    def _parse_vehicle_info_xlsx(self, file_path: Path) -> Dict:
        """解析车辆信息Excel文件"""
        try:
            df = pd.read_excel(file_path)
            if len(df) > 0:
                return df.iloc[0].to_dict()
        except Exception as e:
            self.warnings.append({
                'type': '错误',
                'message': f'解析车辆信息Excel失败: {e}',
                'component': ''
            })
        
        return {}
    
    def _discover_components(self) -> List[Path]:
        """发现并验证组件文件夹

        v1.6 hotfix P2.2: 同步 NEW-7 (与 vehicle_processor 一致),
        对非组件可疑文件 (.zip/.rar/.docx/.png 等) 也发出警告,避免静默丢弃数据。
        """
        component_folders = []
        invalid_folders = []
        suspicious_files = []
        suspicious_exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.docx', '.png', '.jpg', '.jpeg'}

        # 需要跳过的系统文件夹
        skip_folders = {f'{self.vehicle_id}_SLOPE_output'}

        for item in self.vehicle_folder.iterdir():
            if item.name.startswith('.'):
                continue  # 跳过隐藏文件
            if item.is_dir() and item.name not in skip_folders and not item.name.endswith('_output'):
                # 检查是否为有效组件
                if item.name in self.sensor_rules:
                    component_folders.append(item)
                else:
                    invalid_folders.append(item.name)
            elif item.is_file():
                # v1.6 hotfix P2.2: NEW-7 同步 - 警告可疑非组件文件
                if item.suffix.lower() in suspicious_exts:
                    suspicious_files.append(item.name)

        # 记录无效文件夹为警告，不阻止处理
        for invalid_folder in invalid_folders:
            self.warnings.append({
                'type': '警告',
                'message': f'组件文件夹 {invalid_folder} 未在sensor_naming_rules中定义，已跳过',
                'component': invalid_folder
            })

        # v1.6 hotfix P2.2: 记录可疑文件为警告
        for fname in suspicious_files:
            self.warnings.append({
                'type': '警告',
                'message': f'忽略非组件文件: {fname} (位置可能错误，应在父目录)',
                'component': None
            })

        if not component_folders:
            raise ValueError("未找到有效的组件文件夹")

        return component_folders
    
    def _process_components(self, component_folders: List[Path]) -> None:
        """处理组件数据"""
        for folder in component_folders:
            comp_code = folder.name
            comp_info = self.sensor_rules.get(comp_code, {})
            
            # 检查statistics.xlsx
            stats_file = folder / "statistics.xlsx"
            if not stats_file.exists():
                self.warnings.append({
                    'type': '警告',
                    'message': f'组件 {comp_code} 缺少 statistics.xlsx，已跳过',
                    'component': comp_code
                })
                continue
            
            try:
                # 读取斜率统计数据
                df = pd.read_excel(stats_file)
                
                # 验证列名
                expected_cols = ['文件名', '斜率最大值(V/s)', '斜率最小值(V/s)', '斜率绝对值最大值(V/s)']
                actual_cols = list(df.columns)
                
                if len(actual_cols) != 4:
                    self.warnings.append({
                        'type': '警告',
                        'message': f'组件 {comp_code} 的 statistics.xlsx 列数不正确 (期望4列，实际{len(actual_cols)}列)',
                        'component': comp_code
                    })
                
                # 扫描图片文件
                image_files = list(folder.glob('*.png')) + list(folder.glob('*.jpg'))
                image_map = {}
                for img_file in image_files:
                    # Sensor channel is determined by the FOLDER name (comp_code), NOT parsed from filename
                    # The channel code in filename should match the folder name, but we use folder name as source of truth
                    # Format: {condition_id}_{channel_code}.png where channel_code should match comp_code
                    img_stem = img_file.stem.strip()  # 去掉首尾空格，避免末尾空格导致匹配失败

                    # Try to find comp_code as suffix in filename
                    suffix = f'_{comp_code}'
                    if img_stem.endswith(suffix):
                        img_condition_id = img_stem[:-len(suffix)]
                        image_map[img_condition_id] = str(img_file.absolute())
                    else:
                        # Fallback: try case-insensitive match
                        suffix_lower = f'_{comp_code}'.lower()
                        if img_stem.lower().endswith(suffix_lower):
                            img_condition_id = img_stem[:-len(comp_code) - 1]
                            image_map[img_condition_id] = str(img_file.absolute())
                        else:
                            # Last resort: try to find any known sensor code suffix
                            # This maintains backward compatibility
                            found = False
                            sensor_codes = sorted(self.sensor_rules.keys(), key=len, reverse=True)
                            for code in sensor_codes:
                                test_suffix = f'_{code}'
                                if img_stem.endswith(test_suffix):
                                    img_condition_id = img_stem[:-len(test_suffix)]
                                    image_map[img_condition_id] = str(img_file.absolute())
                                    found = True
                                    # Warn if the code in filename doesn't match folder name
                                    if code != comp_code:
                                        self.warnings.append({
                                            'type': '警告',
                                            'message': f'图片 {img_file.name} 中的通道代码 ({code}) 与文件夹名称 ({comp_code}) 不匹配',
                                            'component': comp_code
                                        })
                                    break
                            if not found:
                                self.warnings.append({
                                    'type': '警告',
                                    'message': f'无法解析图片文件名: {img_file.name} (未找到匹配的通道代码)',
                                    'component': comp_code
                                })
                
                # 处理每个工况
                conditions = {}
                for _, row in df.iterrows():
                    condition_id = str(row.get('文件名', ''))
                    if not condition_id or pd.isna(condition_id):
                        continue

                    # 规范化 condition_id（处理 GBK 乱码坡度前缀）
                    condition_id = self._normalize_condition_id(condition_id)

                    # 提取SOC值和等级
                    soc_value = self._extract_soc_from_condition_id(condition_id)
                    soc_level = self._get_soc_level(soc_value)
                    
                    # 获取工况名称
                    # C2 v1.6 hotfix: 同时取 match_method + match_confidence,
                    # 持久化到 JSON 让下游能读到匹配质量
                    condition_name, match_method, match_confidence = self._get_match_info(condition_id)

                    # 提取斜率值
                    slope_max = self._safe_float(row.get('斜率最大值(V/s)'))
                    slope_min = self._safe_float(row.get('斜率最小值(V/s)'))
                    slope_max_abs = self._safe_float(row.get('斜率绝对值最大值(V/s)'))

                    # 获取图片路径 (绝对路径)
                    image_path = image_map.get(condition_id, '')

                    # 根据组件代码后缀判断斜率单位
                    slope_unit = 'A/s' if comp_code.endswith('_A') else 'V/s'

                    conditions[condition_id] = {
                        'condition_name': condition_name,
                        'soc_level': soc_level,
                        'slope': {
                            'max_value': slope_max,
                            'min_value': slope_min,
                            'max_abs_value': slope_max_abs,
                            'unit': slope_unit
                        },
                        'image_path': image_path,
                        # C2 v1.6 hotfix: 匹配元数据持久化
                        'match_method': match_method,
                        'match_confidence': match_confidence,
                    }
                
                self.components[comp_code] = {
                    'component_name': comp_info.get('name', comp_code),
                    'channel_code': comp_code,
                    'unit': comp_info.get('unit', ''),
                    'statistics_file': str(stats_file.relative_to(self.vehicle_folder)),
                    'conditions_count': len(conditions),
                    'conditions': conditions
                }
                
            except Exception as e:
                self.warnings.append({
                    'type': '错误',
                    'message': f'处理组件 {comp_code} 时出错: {e}',
                    'component': comp_code
                })
    
    def _normalize_condition_id(self, condition_id: str) -> str:
        """规范化 condition_id，处理 GBK 乱码坡度前缀"""
        return re.sub(r'^�¶�\s*10(?![0-9])', '坡度10', condition_id)

    def _extract_soc_from_condition_id(self, condition_id: str) -> Optional[int]:
        """从 condition_id 提取 SOC 值

        支持格式:
          - 普通: 87_超车80-140, 25-交流充电冷风, 33 直流充电
          - 坡度: 坡度10_24_xxx, 坡度10-24-xxx, 坡度10 24 xxx
          - GBK乱码: �¶�10_24_xxx, �¶�10-24-xxx, �¶�10 24 xxx
        """
        if not condition_id:
            return None

        # 坡度工况（支持GBK乱码和多种分隔符）
        slope_match = _SLOPE_PREFIX_PATTERN.match(condition_id)
        if slope_match:
            return int(slope_match.group(2))

        # 普通工况（开头的数字 + 任意分隔符）
        normal_match = _SOC_PATTERN.match(condition_id)
        if normal_match:
            return int(normal_match.group(1))

        return None
    
    def _get_soc_level(self, soc_value: Optional[int]) -> str:
        """将SOC值映射到SOC等级"""
        if soc_value is None:
            return "Unknown"
        elif soc_value >= 70:
            return "≥70%"
        elif soc_value >= 40:
            return "40%-70%"
        else:
            return "≤40%"
    
    def _get_condition_name(self, condition_id: str) -> str:
        """获取工况名称 - 向后兼容封装(只返回名字)。

        新代码应优先用 _get_match_info(),它返回完整匹配信息以便持久化(C2 fix)。
        """
        name, _method, _conf = self._get_match_info(condition_id)
        return name

    def _get_match_info(self, condition_id: str):
        """
        获取工况名称 + 匹配元数据 (C2 v1.6 hotfix).

        匹配策略（按优先级）：
        1. 精确匹配 (confidence=1.0)
        2. 规范化匹配 (~0.95)
        3. 模糊匹配 (0.7-0.95)
        4. 特征匹配 (0.75-0.90)
        5. 回退:从condition_id提取描述 (confidence=0.5)

        Args:
            condition_id: 条件ID

        Returns:
            (condition_name, match_method, match_confidence) 三元组
        """
        # 使用ConditionMatcher进行多级匹配
        matcher = ConditionMatcher(self.test_rules)
        result = matcher.match(condition_id)

        if result:
            # 记录非精确匹配以便调试
            if result.match_type != 'exact':
                self.warnings.append({
                    'type': '警告',
                    'message': f"模糊匹配: '{condition_id}' → '{result.matched_id}' (类型: {result.match_type}, 置信度: {result.confidence:.2f})",
                    'component': ''
                })
            return result.condition_name, result.match_type, float(result.confidence)

        # 回退：从condition_id提取描述部分
        parts = condition_id.split('_')
        if len(parts) >= 2:
            return '_'.join(parts[1:]), 'fallback_extract', 0.5

        return condition_id, 'no_match', 0.0

    def _safe_float(self, value) -> Optional[float]:
        """安全地转换为float"""
        try:
            if pd.isna(value):
                return None
            return float(value)
        except Exception:
            return None
    
    def _generate_outputs(self) -> None:
        """生成输出文件"""
        # 构建结果数据
        total_conditions = sum(len(comp['conditions']) for comp in self.components.values())
        
        result = {
            'vehicle': {
                'vehicle_id': self.vehicle_id,
                'vehicle_info': self.vehicle_info
            },
            'components': self.components,
            'metadata': {
                'processing_date': datetime.now().isoformat(),
                'total_components': len(self.components),
                'total_conditions': total_conditions,
                'data_type': 'slope',
                'test_naming_rules_source': 'merged',
                'sensor_naming_rules_source': 'merged',
                'warnings': self.warnings,
                'errors': self.errors
            }
        }
        
        # 生成JSON
        if self.config['generate_json']:
            json_path = self.output_dir / f"{self.vehicle_id}_SLOPE_data.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  [OK] JSON: {json_path.name}")
        
        # 生成Excel
        if self.config['generate_excel']:
            excel_path = self.output_dir / f"{self.vehicle_id}_SLOPE_summary.xlsx"
            self._generate_excel(result, excel_path)
            print(f"  [OK] Excel: {excel_path.name}")
        
        # 生成SQLite
        if self.config['generate_sqlite']:
            sqlite_path = self.output_dir / f"{self.vehicle_id}_SLOPE.db"
            self._generate_sqlite(result, sqlite_path)
            print(f"  [OK] SQLite: {sqlite_path.name}")
        
        # 生成中文错误报告
        self._generate_error_report(result)
    
    def _generate_excel(self, data: Dict, output_path: Path) -> None:
        """生成Excel报告 - Unified format with ripple-data skill"""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 工作表1: 车辆信息 (统一格式)
            # Build unified vehicle info data (same as ripple-data)
            vehicle = data['vehicle']
            vehicle_info = vehicle['vehicle_info']

            # Standard fields first (same order as ripple-data)
            vehicle_data = [
                {'Parameter': 'Vehicle ID', 'Value': vehicle.get('vehicle_id', 'Unknown')},
                {'Parameter': 'Vehicle Model', 'Value': vehicle_info.get('vehicle_model', 'Unknown')},
                {'Parameter': 'Manufacturer', 'Value': vehicle_info.get('manufacturer', 'Unknown')},
                {'Parameter': 'Length (mm)', 'Value': vehicle_info.get('length_mm', '')},
                {'Parameter': 'Width (mm)', 'Value': vehicle_info.get('width_mm', '')},
                {'Parameter': 'Height (mm)', 'Value': vehicle_info.get('height_mm', '')},
            ]

            # Add extra fields (same exclusions as ripple-data)
            excluded_keys = {
                'vehicle_id', 'vehicle_model', 'manufacturer',
                'length_mm', 'width_mm', 'height_mm',
            }

            for key, value in vehicle_info.items():
                if key not in excluded_keys and value and str(value).strip():
                    # Convert display name
                    if '_' in key and not any(c in key for c in '()（）'):
                        display_key = key.replace('_', ' ').title()
                    else:
                        display_key = key
                    vehicle_data.append({'Parameter': display_key, 'Value': value})

            vehicle_df = pd.DataFrame(vehicle_data)
            vehicle_df.to_excel(writer, sheet_name='Vehicle Information', index=False)
            
            # 工作表2: 组件摘要
            summary_data = []
            for comp_code, comp_data in data['components'].items():
                # 计算斜率统计
                slopes = [cond['slope'] for cond in comp_data['conditions'].values()]
                max_vals = [s['max_value'] for s in slopes if s['max_value'] is not None]
                min_vals = [s['min_value'] for s in slopes if s['min_value'] is not None]
                
                summary_data.append({
                    'Component Code': comp_code,
                    'Component Name': comp_data['component_name'],
                    'Unit': comp_data['unit'],
                    'Conditions Count': comp_data['conditions_count'],
                    'Max Slope (V/s)': max(max_vals) if max_vals else None,
                    'Min Slope (V/s)': min(min_vals) if min_vals else None
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Component Summary', index=False)
            
            # 工作表3: 详细结果
            results_data = []
            seq_num = 1
            for comp_code, comp_data in data['components'].items():
                unit = comp_data['unit']
                for cond_id, cond_data in comp_data['conditions'].items():
                    results_data.append({
                        'No.': seq_num,
                        'Component': comp_code,
                        'Unit': unit,
                        'Condition ID': cond_id,
                        'Condition Name': cond_data['condition_name'],
                        'SOC Level': cond_data['soc_level'],
                        'Slope Max (V/s)': cond_data['slope']['max_value'],
                        'Slope Min (V/s)': cond_data['slope']['min_value'],
                        'Slope Max Abs (V/s)': cond_data['slope']['max_abs_value'],
                        'Image Path': cond_data.get('image_path', '')
                    })
                    seq_num += 1
            
            results_df = pd.DataFrame(results_data)
            results_df.to_excel(writer, sheet_name='Detailed Results', index=False)
    
    def _generate_sqlite(self, data: Dict, output_path: Path) -> None:
        """生成SQLite数据库"""
        # 删除旧数据库以确保表结构最新
        if output_path.exists():
            output_path.unlink()

        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()
        
        # 创建vehicles表 (存储完整车辆信息JSON)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id TEXT PRIMARY KEY,
                vehicle_model TEXT,
                vehicle_info_json TEXT
            )
        ''')
        
        # 创建components表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components (
                component_code TEXT PRIMARY KEY,
                component_name TEXT,
                unit TEXT
            )
        ''')
        
        # 创建conditions表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conditions (
                condition_id TEXT PRIMARY KEY,
                condition_name TEXT,
                soc_level TEXT
            )
        ''')
        
        # 创建slope_results表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS slope_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                component_code TEXT,
                condition_id TEXT,
                slope_max REAL,
                slope_min REAL,
                slope_max_abs REAL,
                unit TEXT,
                image_path TEXT,
                match_confidence REAL,
                match_method TEXT
            )
        ''')

        # C2 v1.6 hotfix: 向后兼容旧 DB - 显式 ALTER 添加列(若已存在会抛错,忽略)
        for col_def in (
            "ALTER TABLE slope_results ADD COLUMN match_confidence REAL",
            "ALTER TABLE slope_results ADD COLUMN match_method TEXT",
        ):
            try:
                cursor.execute(col_def)
            except sqlite3.OperationalError:
                pass
        
        # 插入车辆信息 (包含完整JSON)
        vehicle_id = data['vehicle']['vehicle_id']
        vehicle_info = data['vehicle']['vehicle_info']
        vehicle_model = vehicle_info.get('vehicle_model') or vehicle_info.get('车型', '')
        vehicle_info_json = json.dumps(vehicle_info, ensure_ascii=False)
        cursor.execute(
            'INSERT OR REPLACE INTO vehicles VALUES (?, ?, ?)',
            (vehicle_id, vehicle_model, vehicle_info_json)
        )
        
        # 插入组件和结果
        for comp_code, comp_data in data['components'].items():
            cursor.execute(
                'INSERT OR REPLACE INTO components VALUES (?, ?, ?)',
                (comp_code, comp_data['component_name'], comp_data['unit'])
            )
            
            for cond_id, cond_data in comp_data['conditions'].items():
                cursor.execute(
                    'INSERT OR REPLACE INTO conditions VALUES (?, ?, ?)',
                    (cond_id, cond_data['condition_name'], cond_data['soc_level'])
                )
                
                cursor.execute('''
                    INSERT INTO slope_results
                    (vehicle_id, component_code, condition_id, slope_max, slope_min, slope_max_abs,
                     unit, image_path, match_confidence, match_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    vehicle_id,
                    comp_code,
                    cond_id,
                    cond_data['slope']['max_value'],
                    cond_data['slope']['min_value'],
                    cond_data['slope']['max_abs_value'],
                    cond_data['slope']['unit'],
                    cond_data.get('image_path', ''),
                    cond_data.get('match_confidence'),  # C2 v1.6 hotfix
                    cond_data.get('match_method'),
                ))
        
        conn.commit()
        conn.close()
    
    def _build_result_data(self, include_debug: bool = False) -> Dict:
        """构建统一的结果数据结构

        Args:
            include_debug: 是否包含警告和错误信息
        """
        total_conditions = sum(len(comp['conditions']) for comp in self.components.values())

        result = {
            'vehicle': {
                'vehicle_id': self.vehicle_id,
                'vehicle_info': self.vehicle_info
            },
            'components': self.components,
            'metadata': {
                'processing_date': datetime.now().isoformat(),
                'total_components': len(self.components),
                'total_conditions': total_conditions,
                'data_type': 'slope',
                'test_naming_rules_source': 'merged',
                'sensor_naming_rules_source': 'merged',
            }
        }

        if include_debug:
            result['metadata']['warnings'] = self.warnings
            result['metadata']['errors'] = self.errors

        return result

    def generate_json(self, output_path: str):
        """单独生成JSON文件（供外部调用）"""
        result = self._build_result_data(include_debug=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def generate_excel(self, output_path: str):
        """单独生成Excel文件（供外部调用）"""
        result = self._build_result_data(include_debug=False)
        self._generate_excel(result, Path(output_path))
    
    def generate_sqlite(self, output_path: str):
        """单独生成SQLite文件（供外部调用）"""
        result = self._build_result_data(include_debug=False)
        self._generate_sqlite(result, Path(output_path))
    
    def _generate_error_report(self, data: Dict) -> None:
        """生成中文错误报告"""
        try:
            # Ensure we import from vehicle-slope-data, not vehicle-ripple-data
            import sys
            slope_scripts = str(Path(__file__).parent)
            if slope_scripts in sys.path:
                sys.path.remove(slope_scripts)
            sys.path.insert(0, slope_scripts)
            from generate_error_report_cn import generate_error_report_cn
            
            # 准备已完成的功能列表
            total_conds = data["metadata"]["total_conditions"]
            completed_functions = [
                {'name': '车辆信息加载', 'success': True, 'details': f'{len(self.vehicle_info)}个参数'},
                {'name': '测试命名规则加载', 'success': True, 'details': f'{len(self.test_rules)}个工况'},
                {'name': '传感器命名规则加载', 'success': True, 'details': f'{len(self.sensor_rules)}个通道'},
                {'name': '组件文件夹验证', 'success': True, 'details': f'{len(self.components)}个组件'},
                {'name': '斜率统计数据处理', 'success': True, 'details': f'{total_conds}个工况'},
                {'name': 'JSON文件生成', 'success': self.config.get('generate_json', True), 'details': f'{self.vehicle_id}_SLOPE_data.json'},
                {'name': 'Excel报告生成', 'success': self.config.get('generate_excel', True), 'details': f'{self.vehicle_id}_SLOPE_summary.xlsx'},
                {'name': 'SQLite数据库生成', 'success': self.config.get('generate_sqlite', True), 'details': f'{self.vehicle_id}_SLOPE.db'},
            ]
            
            # 准备生成的文件列表
            generated_files = []
            if self.config.get('generate_json', True):
                generated_files.append({
                    'name': f'{self.vehicle_id}_SLOPE_data.json',
                    'type': 'JSON',
                    'description': '结构化数据导出，包含车辆信息、组件数据和元数据'
                })
            if self.config.get('generate_excel', True):
                generated_files.append({
                    'name': f'{self.vehicle_id}_SLOPE_summary.xlsx',
                    'type': 'Excel',
                    'description': 'V1.0格式报告，包含3个工作表(车辆信息、组件摘要、详细结果)'
                })
            if self.config.get('generate_sqlite', True):
                generated_files.append({
                    'name': f'{self.vehicle_id}_SLOPE.db',
                    'type': 'SQLite',
                    'description': '数据库，包含4个表(vehicles, components, conditions, slope_results)'
                })
            
            # 转换警告和错误格式 (self.warnings/self.errors 中已包含字典)
            warning_list = []
            for w in self.warnings:
                if isinstance(w, dict):
                    warning_list.append(w)
                else:
                    warning_list.append({'type': '警告', 'message': str(w), 'component': ''})
            error_list = []
            for e in self.errors:
                if isinstance(e, dict):
                    error_list.append(e)
                else:
                    error_list.append({'type': '错误', 'message': str(e), 'component': ''})
            
            # 生成报告
            report_path = generate_error_report_cn(
                vehicle_folder=str(self.vehicle_folder),
                vehicle_id=self.vehicle_id,
                vehicle_model=self.vehicle_info.get('车型') or self.vehicle_info.get('vehicle_model', 'Unknown'),
                processing_status=len(self.errors) == 0,
                completed_functions=completed_functions,
                generated_files=generated_files,
                errors=error_list,
                warnings=warning_list,
                processing_stats={
                    'total_components': len(self.components),
                    'processed_components': len(self.components),
                    'total_conditions': data['metadata']['total_conditions']
                },
                output_folder=str(self.output_dir)  # 使用output_dir作为报告输出位置
            )
            
            print(f"  [OK] Error Report: error_report.md")
            
        except Exception as e:
            print(f"  [WARN] 生成错误报告失败: {e}")


if __name__ == '__main__':
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python slope_processor.py <vehicle_folder>")
        sys.exit(1)
    
    vehicle_folder = sys.argv[1]
    processor = SlopeDataProcessor(vehicle_folder)
    result = processor.process()
    
    print("\n处理完成!")
    print(f"结果已保存到: {processor.output_dir}")
