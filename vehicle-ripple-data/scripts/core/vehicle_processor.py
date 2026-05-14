#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vehicle Data Processor - Core Processing Logic
Handles vehicle ripple test data processing from folder structure to structured output

This module provides the main VehicleDataProcessor class that:
1. Loads and validates vehicle information
2. Loads naming rules (test and sensor)
3. Discovers and processes component folders
4. Matches conditions between statistics and images
5. Generates JSON, SQLite, and Excel outputs
"""

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

# Import condition matcher for fuzzy matching
try:
    from .condition_matcher import ConditionMatcher, get_condition_name
except ImportError:
    from condition_matcher import ConditionMatcher, get_condition_name

# Import config manager for configuration-driven processing
try:
    from ...config import ConfigManager
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config import ConfigManager


# 坡度前缀匹配正则（支持正常文本、GBK乱码、多种分隔符）
_SLOPE_PREFIX_PATTERN = re.compile(
    r'^(坡度|�¶�)\s*10(?![0-9])[_\-\s]*(\d+)[_\-\s]',
    re.IGNORECASE
)

# 普通工况SOC匹配正则（开头的数字 + 任意分隔符）
_SOC_PATTERN = re.compile(r'^(\d+)[_\-\s]')

# REPORT-H2 v1.4: ripple marker 正则锚定,避免 'in' 子串匹配的 false positive
# 匹配格式: <数字>{Ipp|Vpp|Xpp} (大小写不敏感),如 '8.39Vpp' / '0.70xpp' / '29.21IPP'
# 锚定 ^...$ 防止 'IPPC' / 'VPPT' 等工况名片段被误识别
_RIPPLE_MARKER_PATTERN = re.compile(r'^\d+(?:\.\d+)?[IVXivx]pp$', re.IGNORECASE)


class VehicleDataProcessor:
    """
    Main processor for vehicle ripple test data
    
    Usage:
        processor = VehicleDataProcessor("/path/to/V0001_RIPPLE", config)
        result = processor.process()
    """
    
    def __init__(self, vehicle_folder: str, config: Optional[Dict] = None):
        """
        Initialize the processor
        
        Args:
            vehicle_folder: Path to vehicle folder (e.g., V0001_RIPPLE)
                Can also be parent folder, and the skill will auto-detect RIPPLE subfolder
            config: Processing configuration dict
                - generate_json: bool (default True)
                - generate_excel: bool (default True)
                - generate_sqlite: bool (default True)
                - output_dir: str (optional custom output directory)
        """
        input_path = Path(vehicle_folder)
        self.config = config or {}
        
        # Auto-detect RIPPLE subfolder if input is parent folder
        if input_path.name.endswith('_RIPPLE'):
            # Input is already the RIPPLE folder
            self.vehicle_folder = input_path
            self.parent_folder = input_path.parent
            self.vehicle_id = self._extract_vehicle_id(input_path.name)
        else:
            # Input might be parent folder, try to find RIPPLE subfolder
            ripple_folder = self._find_ripple_subfolder(input_path)
            if ripple_folder:
                self.vehicle_folder = ripple_folder
                self.parent_folder = input_path
                self.vehicle_id = self._extract_vehicle_id(ripple_folder.name)
            else:
                # No RIPPLE subfolder found, treat input as vehicle folder itself
                self.vehicle_folder = input_path
                self.parent_folder = input_path
                self.vehicle_id = self._extract_vehicle_id(input_path.name)
        
        # Output directory
        self.output_dir = self._get_output_dir()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.vehicle_info: Dict[str, Any] = {}
        self.test_rules: Dict[str, Dict] = {}
        self.sensor_rules: Dict[str, Dict] = {}
        self.components: Dict[str, Dict] = {}
        self.warnings: List[str] = []
        self.errors: List[str] = []
        
        # Configuration-driven setup
        self._init_config_manager()
        
    def _init_config_manager(self):
        """Initialize configuration manager"""
        try:
            # Get skill root directory
            skill_root = Path(__file__).parent.parent.parent
            
            # Initialize config manager with hot reload enabled
            self.config_mgr = ConfigManager(skill_root, hot_reload=True)
            
            # Load configurations
            self.field_config = self.config_mgr.load('common/vehicle_fields')
            self.matching_config = self.config_mgr.load('common/matching_rules')
            
        except Exception as e:
            # Fallback: if config loading fails, processor still works with hardcoded defaults
            print(f"[警告] 配置加载失败，使用默认设置: {e}")
            self.config_mgr = None
            self.field_config = None
            self.matching_config = None
    
    def _extract_with_config(self, raw_data: Dict, field_key: str) -> Any:
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
        """Fallback field extraction (hardcoded mappings)"""
        fallback_mappings = {
            'vehicle_model': ['车型', '参数名称', '车辆型号', 'Model'],
            'manufacturer': ['制造商', '厂商', '品牌'],
            'length_mm': ['长度(mm)', '车长', '长度'],
        }
        
        possible_names = fallback_mappings.get(field_key, [field_key])
        
        for name in possible_names:
            if name in raw_data:
                return raw_data[name]
        
        return None
    
    def _find_ripple_subfolder(self, parent_path: Path) -> Optional[Path]:
        """
        Auto-detect RIPPLE subfolder in parent directory
        
        Looks for folder matching pattern: {VehicleID}_RIPPLE
        
        Args:
            parent_path: Path to parent folder
            
        Returns:
            Path to RIPPLE subfolder if found, None otherwise
        """
        if not parent_path.is_dir():
            return None
        
        # Look for folders ending with _RIPPLE
        for item in parent_path.iterdir():
            if item.is_dir() and item.name.endswith('_RIPPLE'):
                return item
        
        return None
    
    def _extract_vehicle_id(self, folder_name: str) -> str:
        """Extract vehicle ID from folder name"""
        if folder_name.endswith('_RIPPLE'):
            return folder_name[:-7]
        return folder_name
    
    def _get_output_dir(self) -> Path:
        """Determine output directory"""
        if self.config.get('output_dir'):
            return Path(self.config['output_dir'])
        return self.vehicle_folder / f"{self.vehicle_id}_RIPPLE_output"
    
    def process(self) -> Dict[str, Any]:
        """
        Main processing pipeline
        
        Returns:
            Dict containing:
                - vehicle: vehicle info
                - components: processed component data
                - metadata: processing metadata
        """
        print(f"[处理] 开始处理车辆 {self.vehicle_id}")
        
        # Step 1: Load vehicle info
        self._load_vehicle_info()
        
        # Step 2: Load naming rules
        self._load_test_naming_rules()
        self._load_sensor_naming_rules()
        
        # Step 3: Discover and validate components
        component_folders = self._discover_components()
        
        # Step 4: Process each component
        for comp_folder in component_folders:
            self._process_component(comp_folder)
        
        # Step 5: Build result structure
        result = {
            'vehicle': {
                'vehicle_id': self.vehicle_id,
                'vehicle_info': self.vehicle_info
            },
            'components': self.components,
            'metadata': {
                'total_components': len(self.components),
                'total_conditions': sum(
                    len(comp.get('conditions', {})) 
                    for comp in self.components.values()
                ),
                'warnings': self.warnings
            }
        }
        
        # Step 6: Generate outputs
        if self.config.get('generate_json', True):
            self._generate_json(result)
        
        if self.config.get('generate_sqlite', True):
            self._generate_sqlite(result)
        
        if self.config.get('generate_excel', True):
            self._generate_excel(result)
        
        # Step 7: Generate error report
        self._generate_error_report(result)
        
        print(f"[完成] 处理完成: {len(self.components)} 个组件, {result['metadata']['total_conditions']} 个工况")
        
        return result
    
    def _load_vehicle_info(self):
        """Load vehicle information from parent folder using configuration-driven extraction"""
        # Try .md first, then .xlsx
        md_path = self.parent_folder / 'vehicle_info.md'
        xlsx_path = self.parent_folder / 'vehicle_info.xlsx'
        
        if md_path.exists():
            raw_data = self._parse_vehicle_info_md(md_path)
        elif xlsx_path.exists():
            raw_data = self._parse_vehicle_info_xlsx(xlsx_path)
        else:
            raise FileNotFoundError(f"未找到vehicle_info.md或vehicle_info.xlsx在 {self.parent_folder}")
        
        # Configuration-driven field extraction
        self.vehicle_info = self._extract_vehicle_info_with_config(raw_data)
    
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
            value = self._extract_with_config(raw_data, field_key)
            if value is not None:
                standardized[field_key] = value
        
        # Also keep original fields for backward compatibility
        for key, value in raw_data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized
    
    def _parse_vehicle_info_md(self, file_path: Path) -> Dict[str, Any]:
        """Parse vehicle info from markdown file"""
        info = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # Parse markdown table
        lines = content.split('\n')
        for line in lines:
            if '|' in line and not line.startswith('|---'):
                parts = line.split('|')
                if len(parts) >= 3:
                    key = parts[1].strip()
                    value = parts[2].strip()
                    # Skip separator rows and header names
                    if key and key not in ['Parameter', '参数', '---', '']:
                        info[key] = value
        
        return info
    
    def _parse_vehicle_info_xlsx(self, file_path: Path) -> Dict[str, Any]:
        """Parse vehicle info from Excel file"""
        df = pd.read_excel(file_path)
        info = {}
        
        # Assume first column is key, second is value
        for _, row in df.iterrows():
            if len(row) >= 2:
                key = str(row.iloc[0]).strip()
                value = str(row.iloc[1]).strip()
                if key:
                    info[key] = value
        
        return info
    
    def _load_test_naming_rules(self):
        """Load test naming rules with merge strategy"""
        # Load default rules first
        skill_dir = Path(__file__).parent.parent.parent
        default_rules_path = skill_dir / 'references' / 'test_naming_rules.md'
        
        if default_rules_path.exists():
            self.test_rules = self._parse_test_rules(default_rules_path)
        
        # Merge with parent folder rules if exists
        parent_rules_md = self.parent_folder / 'test_naming_rules.md'
        parent_rules_xlsx = self.parent_folder / 'test_naming_rules.xlsx'
        
        if parent_rules_md.exists():
            parent_rules = self._parse_test_rules(parent_rules_md)
            self.test_rules.update(parent_rules)
        elif parent_rules_xlsx.exists():
            parent_rules = self._parse_test_rules_xlsx(parent_rules_xlsx)
            self.test_rules.update(parent_rules)
    
    def _load_sensor_naming_rules(self):
        """Load sensor naming rules with merge strategy"""
        skill_dir = Path(__file__).parent.parent.parent
        default_rules_path = skill_dir / 'references' / 'sensor_naming_rules.md'
        
        if default_rules_path.exists():
            self.sensor_rules = self._parse_sensor_rules(default_rules_path)
        
        # Merge with parent folder rules
        parent_rules_md = self.parent_folder / 'sensor_naming_rules.md'
        parent_rules_xlsx = self.parent_folder / 'sensor_naming_rules.xlsx'
        
        if parent_rules_md.exists():
            parent_rules = self._parse_sensor_rules(parent_rules_md)
            self.sensor_rules.update(parent_rules)
        elif parent_rules_xlsx.exists():
            parent_rules = self._parse_sensor_rules_xlsx(parent_rules_xlsx)
            self.sensor_rules.update(parent_rules)
    
    def _parse_test_rules(self, file_path: Path) -> Dict[str, Dict]:
        """Parse test naming rules from markdown"""
        rules = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        lines = content.split('\n')
        for line in lines:
            if '|' in line and not line.startswith('|---'):
                parts = line.split('|')
                if len(parts) >= 4:
                    soc_level = parts[1].strip()
                    condition_name = parts[2].strip()
                    example_naming = parts[3].strip()
                    # Skip header row - check if any column contains header text
                    if soc_level and soc_level not in ['电量状态'] and condition_name not in ['工况名称']:
                        # Use example_naming as the key for matching
                        # Extract base pattern by removing _001 suffix if present
                        condition_id = example_naming
                        if condition_id:
                            rules[condition_id] = {
                                'condition_name': condition_name
                            }
        
        return rules
    
    def _parse_test_rules_xlsx(self, file_path: Path) -> Dict[str, Dict]:
        """Parse test naming rules from Excel"""
        df = pd.read_excel(file_path)
        rules = {}
        
        for _, row in df.iterrows():
            if len(row) >= 2:
                condition_id = str(row.iloc[0]).strip()
                condition_name = str(row.iloc[1]).strip()
                if condition_id:
                    rules[condition_id] = {'condition_name': condition_name}
        
        return rules
    
    def _parse_sensor_rules(self, file_path: Path) -> Dict[str, Dict]:
        """Parse sensor naming rules from markdown (supports both table and colon formats)"""
        rules = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        lines = content.split('\n')
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or line.startswith('#') or line.startswith('---'):
                continue
            
            # Try colon format first: "FM_V: 前电驱系统直流母线端电压(V)"
            if ':' in line and '|' not in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    channel_code = parts[0].strip()
                    component_name = parts[1].strip()
                    # Validate channel code format
                    if channel_code and ('_' in channel_code) and not channel_code.startswith('Channel'):
                        unit = 'A' if channel_code.endswith('_A') else 'V'
                        rules[channel_code] = {
                            'component_name': component_name,
                            'unit': unit
                        }
            # Try table format: "| FM_V | 前电驱系统直流母线端电压(V) |"
            elif '|' in line and not line.startswith('|---'):
                parts = line.split('|')
                if len(parts) >= 3:
                    channel_code = parts[1].strip()
                    component_name = parts[2].strip()
                    if channel_code and channel_code not in ['Channel', '通道']:
                        unit = 'A' if channel_code.endswith('_A') else 'V'
                        rules[channel_code] = {
                            'component_name': component_name,
                            'unit': unit
                        }
        
        return rules
    
    def _parse_sensor_rules_xlsx(self, file_path: Path) -> Dict[str, Dict]:
        """Parse sensor naming rules from Excel"""
        df = pd.read_excel(file_path)
        rules = {}
        
        for _, row in df.iterrows():
            if len(row) >= 2:
                channel_code = str(row.iloc[0]).strip()
                component_name = str(row.iloc[1]).strip()
                if channel_code:
                    unit = 'A' if channel_code.endswith('_A') else 'V'
                    rules[channel_code] = {
                        'component_name': component_name,
                        'unit': unit
                    }
        
        return rules
    
    def _discover_components(self) -> List[Path]:
        """Discover and validate component folders"""
        component_folders = []
        # NEW-7 v1.4: 非目录工件 (zip/rar/.docx 等) 静默丢弃会造成数据遗漏感
        # 检测到可疑文件给出警告,但不阻断
        suspicious_exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.docx', '.pdf'}

        for item in self.vehicle_folder.iterdir():
            if item.name.startswith('.') or item.name.endswith('_output'):
                continue  # 隐藏目录/输出目录,合理跳过

            if item.is_dir():
                # Check if folder name matches sensor rules
                if item.name in self.sensor_rules:
                    component_folders.append(item)
                else:
                    self.warnings.append(f"组件文件夹 {item.name} 未在sensor_naming_rules中定义")
            elif item.is_file():
                # NEW-7 v1.4: 可疑文件 (压缩包/文档等) 警告,提醒用户检查位置
                if item.suffix.lower() in suspicious_exts:
                    self.warnings.append(
                        f"忽略非组件文件: {item.name} (可能位置错误,应在父目录或为外部文件)"
                    )

        return component_folders
    
    def _process_component(self, comp_folder: Path):
        """Process a single component folder"""
        comp_code = comp_folder.name
        comp_info = self.sensor_rules.get(comp_code, {})
        
        print(f"  [组件] 处理 {comp_code}")
        
        # Load statistics
        stats_path = comp_folder / 'statistics.xlsx'
        if not stats_path.exists():
            self.warnings.append(f"组件 {comp_code} 缺少statistics.xlsx")
            return
        
        try:
            stats_df = pd.read_excel(stats_path)
        except Exception as e:
            self.warnings.append(f"无法读取 {comp_code}/statistics.xlsx: {e}")
            return
        
        # Scan images
        images = list(comp_folder.glob('*.png')) + list(comp_folder.glob('*.jpg'))
        image_map = self._parse_image_filenames(images, comp_code)
        
        # Process conditions
        conditions = {}
        for _, row in stats_df.iterrows():
            condition_data = self._process_condition_row(row, comp_folder, image_map)
            if condition_data:
                conditions[condition_data['condition_id']] = condition_data
        
        # Store component data
        self.components[comp_code] = {
            'component_name': comp_info.get('component_name', comp_code),
            'unit': comp_info.get('unit', ''),
            'conditions': conditions
        }
    
    def _parse_image_filenames(self, image_files: List[Path], comp_code: str) -> Dict[str, Dict]:
        """Parse image filenames to extract metadata

        Filename format: {condition_id}_{channel}_{vpp}Ipp_{freq}kHz_{amplitude}A.png
        Example: 20_直流充电暖风_PTC_A_29.21Ipp_0.02kHz_5.923A.png

        Note: Sensor channel is determined by the FOLDER name (comp_code), NOT parsed from filename.
        The channel code in filename should match the folder name, but we use folder name as source of truth.
        """
        image_map = {}

        for img_file in image_files:
            img_stem = img_file.stem.strip()  # 去掉首尾空格，避免末尾空格导致匹配失败
            parts = img_stem.split('_')

            # Find the Ipp/Vpp part (contains the ripple amplitude value)
            # 支持标准标记(Ipp/Vpp/ipp/vpp)、非标准标记(xpp/Xpp)、全大写(IPP/VPP/XPP)
            # REPORT-H2 v1.4: 改用正则锚定数值前缀,避免 'in' 子串匹配的 false positive
            # 例如 'IPPC' / 'VPPT' 等工况名片段不会被误识别为 ripple marker
            # 正则匹配格式: <数字>{Ipp|Vpp|Xpp} (大小写不敏感),如 '8.39Vpp' / '0.70xpp' / '29.21IPP'
            ipp_idx = None
            for i, part in enumerate(parts):
                if _RIPPLE_MARKER_PATTERN.search(part):
                    ipp_idx = i
                    break

            if ipp_idx is None or ipp_idx < 1:
                self.warnings.append(f"无法解析图片文件名: {img_file.name} (未找到Vpp/Ipp标记)")
                continue

            # The channel code (comp_code) may contain underscore (e.g., 'PTC_A')
            # When split by '_', it becomes multiple parts
            # We need to find where comp_code ends by checking parts before ipp_idx

            # Strategy: Try to match comp_code by joining parts
            # comp_code 'PTC_A' could be split into ['PTC', 'A']
            # We need to find how many parts make up the channel code

            condition_id = None
            matched_channel = None
            comp_code_parts = comp_code.split('_')  # e.g., ['PTC', 'A']
            num_comp_parts = len(comp_code_parts)

            # Check if the channel code matches comp_code by joining parts
            # The channel should be immediately before the Ipp/Vpp part
            if ipp_idx >= num_comp_parts:
                # Try to match comp_code_parts backwards from ipp_idx-1
                potential_channel = '_'.join(parts[ipp_idx - num_comp_parts:ipp_idx])
                if potential_channel == comp_code or potential_channel.upper() == comp_code.upper():
                    # Matched! Condition ID is everything before the channel
                    condition_parts = parts[:ipp_idx - num_comp_parts]
                    condition_id = '_'.join(condition_parts)
                    matched_channel = potential_channel

            # Fallback: try other matching strategies if exact match fails
            if condition_id is None:
                # Try to find comp_code by checking any consecutive parts
                for num_parts in range(1, min(ipp_idx, 4) + 1):  # Check 1-4 parts
                    for start_idx in range(ipp_idx - num_parts, max(-1, ipp_idx - 4), -1):
                        if start_idx < 0:
                            continue
                        potential_channel = '_'.join(parts[start_idx:start_idx + num_parts])
                        if potential_channel == comp_code or potential_channel.upper() == comp_code.upper():
                            condition_id = '_'.join(parts[:start_idx])
                            matched_channel = potential_channel
                            break
                    if condition_id:
                        break

            # Fallback 2: Try to match ANY known sensor channel from sensor_rules
            # This handles cases where image filename uses a different channel code than the folder
            if condition_id is None and self.sensor_rules:
                # Get all sensor codes sorted by length (longest first to avoid partial matches)
                all_sensor_codes = sorted(self.sensor_rules.keys(), key=len, reverse=True)
                for sensor_code in all_sensor_codes:
                    sensor_parts = sensor_code.split('_')
                    num_sensor_parts = len(sensor_parts)
                    if ipp_idx >= num_sensor_parts:
                        potential_channel = '_'.join(parts[ipp_idx - num_sensor_parts:ipp_idx])
                        if potential_channel == sensor_code or potential_channel.upper() == sensor_code.upper():
                            condition_parts = parts[:ipp_idx - num_sensor_parts]
                            condition_id = '_'.join(condition_parts)
                            matched_channel = potential_channel
                            # Warn about channel mismatch
                            if sensor_code != comp_code:
                                self.warnings.append(
                                    f"图片 {img_file.name} 中的通道代码 ({sensor_code}) "
                                    f"与文件夹名称 ({comp_code}) 不匹配，但已匹配到已知通道"
                                )
                            break
                    if condition_id:
                        break

            # Last resort: use everything before the part immediately before Ipp
            if condition_id is None:
                condition_parts = parts[:ipp_idx - 1]
                condition_id = '_'.join(condition_parts)

            if not condition_id:
                self.warnings.append(f"无法从图片文件名解析condition_id: {img_file.name}")
                continue

            # Store with ABSOLUTE path
            image_map[condition_id] = {
                'path': str(img_file.absolute()),
                'filename': img_file.name
            }

        return image_map
    
    def _process_condition_row(self, row: pd.Series, comp_folder: Path, image_map: Dict) -> Optional[Dict]:
        """Process a single condition row from statistics"""
        # Use column indices (iloc) to handle encoding issues
        try:
            condition_id = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            if not condition_id:
                return None

            # 规范化 condition_id（处理 GBK 乱码坡度前缀）
            condition_id = self._normalize_condition_id(condition_id)

            # Extract SOC from condition_id
            soc_value = self._extract_soc(condition_id)
            soc_level = self._get_soc_level(soc_value)

            # Get condition name from rules
            # C2 v1.6 hotfix: 同时拿到 match_method + match_confidence,
            # 持久化到 JSON,让 validate_cross_format 和 unified DB importer
            # 都能读到真实的匹配质量
            condition_name, match_method, match_confidence = self._get_match_info(condition_id)

            # Extract statistics using column indices
            # Handle variable column counts (6 or 7+ columns)
            num_cols = len(row)
            time_effective_value = float(row.iloc[1]) if num_cols > 1 and pd.notna(row.iloc[1]) else None
            time_vpp = float(row.iloc[2]) if num_cols > 2 and pd.notna(row.iloc[2]) else None

            if num_cols >= 7:
                # Standard format: 7+ columns with peak_ranking
                peak_ranking = str(row.iloc[3]) if pd.notna(row.iloc[3]) else None
                freq_peak_khz = float(row.iloc[4]) if pd.notna(row.iloc[4]) else None
                freq_peak_amplitude = float(row.iloc[5]) if pd.notna(row.iloc[5]) else None
                freq_rms = float(row.iloc[6]) if pd.notna(row.iloc[6]) else None
            else:
                # Compact format: 6 columns without peak_ranking
                peak_ranking = None
                freq_peak_khz = float(row.iloc[3]) if num_cols > 3 and pd.notna(row.iloc[3]) else None
                freq_peak_amplitude = float(row.iloc[4]) if num_cols > 4 and pd.notna(row.iloc[4]) else None
                freq_rms = float(row.iloc[5]) if num_cols > 5 and pd.notna(row.iloc[5]) else None
            
            # Get image path (ABSOLUTE)
            image_info = image_map.get(condition_id, {})
            image_path = image_info.get('path', '')
            
            return {
                'condition_id': condition_id,
                'condition_name': condition_name,
                'soc_level': soc_level,
                'time_domain': {
                    'effective_value': time_effective_value,
                    'vpp': time_vpp
                },
                'frequency_domain': {
                    'peak_ranking': peak_ranking,
                    'peak_frequency_khz': freq_peak_khz,
                    'peak_amplitude': freq_peak_amplitude,
                    'rms': freq_rms
                },
                'image_path': image_path,
                # C2 v1.6 hotfix: 匹配元数据持久化(原先只在 metadata.warnings 中以文本存在)
                'match_method': match_method,
                'match_confidence': match_confidence
            }
            
        except Exception as e:
            self.warnings.append(f"处理工况行失败: {e}")
            return None
    
    def _normalize_condition_id(self, condition_id: str) -> str:
        """规范化 condition_id，处理 GBK 乱码坡度前缀"""
        return re.sub(r'^�¶�\s*10(?![0-9])', '坡度10', condition_id)

    def _extract_soc(self, condition_id: str) -> Optional[int]:
        """从 condition_id 提取 SOC 值"""
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
        """Map SOC value to SOC level"""
        # MED-5 v1.4: \u6539\u5b57\u9762 ≥/≤ (\u539f ≥/≤ escape \u8ba9 grep '≥70%' \u6f0f\u5339\u914d)
        if soc_value is None:
            return "Unknown"
        elif soc_value >= 70:
            return "≥70%"
        elif soc_value >= 40:
            return "40%-70%"
        else:
            return "≤40%"
    
    def _get_condition_name(self, condition_id: str) -> str:
        """Backward-compatible wrapper: get condition name only.

        New code should prefer :meth:`_get_match_info` which returns the full
        match metadata (name, type, confidence) so callers can persist
        :code:`match_confidence` / :code:`match_method` to JSON/DB (C2 fix).
        """
        name, _method, _conf = self._get_match_info(condition_id)
        return name

    def _get_match_info(self, condition_id: str) -> Tuple[str, str, float]:
        """
        Get condition name + match metadata using intelligent fuzzy matching.

        C2 v1.6 hotfix: 返回完整的匹配信息(name, method, confidence),
        让 _process_condition_row 可以将 match_confidence 持久化到 JSON 和 SQLite。
        旧版只返回 name,导致下游(unified DB / validate_cross_format)
        无法读取置信度,引发 C5 (校验失效) 和 M6 (报告不标注).

        Uses multi-level matching strategy:
          1. Exact match (confidence=1.0)
          2. Normalized match (bracket variations, ~0.95)
          3. Fuzzy match (edit distance, 0.7-0.95)
          4. Feature match (handles encoding issues, 0.75-0.90)

        Args:
            condition_id: Condition identifier from statistics or image filename

        Returns:
            (condition_name, match_method, match_confidence) 三元组
              - match_method: 'exact'/'normalized'/'fuzzy'/'feature'/'fallback_extract'/'no_match'
              - match_confidence: 0.0-1.0
        """
        # Initialize matcher with current rules
        matcher = ConditionMatcher(self.test_rules)

        # Attempt multi-level matching
        result = matcher.match(condition_id)

        if result:
            # Log non-exact matches for debugging
            if result.match_type != 'exact':
                self.warnings.append(
                    f"模糊匹配: '{condition_id}' → '{result.matched_id}' "
                    f"(类型: {result.match_type}, 置信度: {result.confidence:.2f})"
                )
            return result.condition_name, result.match_type, float(result.confidence)

        # Fallback: extract from condition_id (匹配失败,confidence=0.5 表示低质量推断)
        parts = condition_id.split('_', 1)
        if len(parts) > 1:
            return parts[1], 'fallback_extract', 0.5
        return condition_id, 'no_match', 0.0
    
    def _generate_json(self, result: Dict):
        """Generate JSON output"""
        output_path = self.output_dir / f"{self.vehicle_id}_RIPPLE_data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  [输出] JSON: {output_path}")
    
    def _generate_sqlite(self, result: Dict):
        """Generate SQLite database"""
        output_path = self.output_dir / f"{self.vehicle_id}_RIPPLE.db"
        
        conn = sqlite3.connect(str(output_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id TEXT PRIMARY KEY,
                vehicle_model TEXT,
                vehicle_info TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components (
                component_code TEXT PRIMARY KEY,
                component_name TEXT,
                unit TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conditions (
                condition_id TEXT PRIMARY KEY,
                condition_name TEXT,
                soc_level TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                component_code TEXT,
                condition_id TEXT,
                time_effective_value REAL,
                time_vpp REAL,
                freq_peak_frequency_khz REAL,
                freq_peak_amplitude REAL,
                freq_rms REAL,
                image_path TEXT,
                match_confidence REAL,
                match_method TEXT
            )
        ''')

        # C2 v1.6 hotfix: 向后兼容旧 DB - 旧表无 match_confidence/match_method 列,
        # 显式 ALTER TABLE ADD COLUMN(若已存在会抛 sqlite3.OperationalError,忽略即可)
        for col_def in (
            "ALTER TABLE test_results ADD COLUMN match_confidence REAL",
            "ALTER TABLE test_results ADD COLUMN match_method TEXT",
        ):
            try:
                cursor.execute(col_def)
            except sqlite3.OperationalError:
                pass  # 列已存在

        # Clear old test results for this vehicle to avoid duplicates on re-runs
        cursor.execute('DELETE FROM test_results WHERE vehicle_id = ?', (self.vehicle_id,))

        # Insert vehicle
        cursor.execute('''
            INSERT OR REPLACE INTO vehicles (vehicle_id, vehicle_model, vehicle_info)
            VALUES (?, ?, ?)
        ''', (
            self.vehicle_id,
            result['vehicle']['vehicle_info'].get('车型', ''),
            json.dumps(result['vehicle']['vehicle_info'], ensure_ascii=False)
        ))

        # Insert components and test results
        for comp_code, comp_data in result['components'].items():
            cursor.execute('''
                INSERT OR REPLACE INTO components (component_code, component_name, unit)
                VALUES (?, ?, ?)
            ''', (comp_code, comp_data['component_name'], comp_data['unit']))
            
            for cond_id, cond_data in comp_data['conditions'].items():
                cursor.execute('''
                    INSERT OR REPLACE INTO conditions (condition_id, condition_name, soc_level)
                    VALUES (?, ?, ?)
                ''', (cond_id, cond_data['condition_name'], cond_data['soc_level']))
                
                # Safely extract values with defaults
                time_domain = cond_data.get('time_domain', {})
                freq_domain = cond_data.get('frequency_domain', {})
                
                cursor.execute('''
                    INSERT INTO test_results
                    (vehicle_id, component_code, condition_id, time_effective_value, time_vpp,
                     freq_peak_frequency_khz, freq_peak_amplitude, freq_rms, image_path,
                     match_confidence, match_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.vehicle_id,
                    comp_code,
                    cond_id,
                    time_domain.get('effective_value'),
                    time_domain.get('vpp'),
                    freq_domain.get('peak_frequency_khz'),
                    freq_domain.get('peak_amplitude'),
                    freq_domain.get('rms'),
                    cond_data.get('image_path', ''),
                    cond_data.get('match_confidence'),  # C2 v1.6 hotfix
                    cond_data.get('match_method'),
                ))
        
        conn.commit()
        conn.close()
        print(f"  [输出] SQLite: {output_path}")
    
    def _generate_excel(self, result: Dict):
        """Generate Excel report with 3 sheets"""
        # Import here to avoid dependency issues
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from generate_excel_report import generate_excel_report
        
        output_path = self.output_dir / f"{self.vehicle_id}_RIPPLE_summary.xlsx"
        generate_excel_report(result, str(output_path))
        print(f"  [输出] Excel: {output_path}")
    
    def _generate_error_report(self, result: Dict):
        """Generate error report using external report generator (unified with slope-data)"""
        try:
            # Import error report generator
            from generate_error_report_cn import generate_error_report_cn
            
            # Prepare completed functions list
            completed_functions = [
                {'name': '车辆信息加载', 'success': True, 'details': f'{len(self.vehicle_info)}个参数'},
                {'name': '测试命名规则加载', 'success': True, 'details': f'{len(self.test_rules)}个工况'},
                {'name': '传感器命名规则加载', 'success': True, 'details': f'{len(self.sensor_rules)}个通道'},
                {'name': '组件文件夹验证', 'success': True, 'details': f'{len(self.components)}个组件'},
                {'name': '纹波统计数据处理', 'success': True, 'details': f"{result['metadata']['total_conditions']}个工况"},
                {'name': 'JSON文件生成', 'success': True, 'details': f'{self.vehicle_id}_RIPPLE_data.json'},
                {'name': 'Excel报告生成', 'success': True, 'details': f'{self.vehicle_id}_RIPPLE_summary.xlsx'},
                {'name': 'SQLite数据库生成', 'success': True, 'details': f'{self.vehicle_id}_RIPPLE.db'},
            ]
            
            # Prepare generated files list
            generated_files = [
                {
                    'name': f'{self.vehicle_id}_RIPPLE_data.json',
                    'type': 'JSON',
                    'description': '结构化数据导出，包含车辆信息、组件数据和元数据'
                },
                {
                    'name': f'{self.vehicle_id}_RIPPLE_summary.xlsx',
                    'type': 'Excel',
                    'description': 'V4.0格式报告，包含3个工作表(车辆信息、组件摘要、详细结果)'
                },
                {
                    'name': f'{self.vehicle_id}_RIPPLE.db',
                    'type': 'SQLite',
                    'description': '数据库，包含4个表(vehicles, components, conditions, test_results)'
                },
            ]
            
            # Convert warnings and errors to unified format
            warning_list = [{'type': '警告', 'message': w, 'component': ''} for w in self.warnings]
            error_list = [{'type': '错误', 'message': e, 'component': ''} for e in self.errors]
            
            # Generate report using external generator
            vehicle_model = result['vehicle']['vehicle_info'].get('车型', 
                               result['vehicle']['vehicle_info'].get('参数名称', 'Unknown'))
            
            report_path = generate_error_report_cn(
                ripple_folder=str(self.vehicle_folder),
                vehicle_id=self.vehicle_id,
                vehicle_model=vehicle_model,
                processing_status=len(self.errors) == 0,
                completed_functions=completed_functions,
                generated_files=generated_files,
                errors=error_list,
                warnings=warning_list,
                processing_stats={
                    'total_components': result['metadata']['total_components'],
                    'processed_components': result['metadata']['total_components'],
                    'total_conditions': result['metadata']['total_conditions']
                }
            )
            
            print(f"  [输出] Error Report: {report_path}")
            
        except Exception as e:
            print(f"  [WARN] 生成错误报告失败: {e}")


if __name__ == '__main__':
    # Test code
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python vehicle_processor.py <vehicle_folder>")
        sys.exit(1)
    
    folder = sys.argv[1]
    processor = VehicleDataProcessor(folder)
    result = processor.process()
    
    print(f"\n处理完成!")
    print(f"车辆ID: {result['vehicle']['vehicle_id']}")
    print(f"组件数: {len(result['components'])}")
    print(f"总工况数: {result['metadata']['total_conditions']}")
