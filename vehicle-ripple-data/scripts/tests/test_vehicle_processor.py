#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vehicle Processor 单元测试

测试内容:
1. 初始化与配置
2. 车辆信息解析 (MD/XLSX)
3. 命名规则解析
4. 组件发现与处理
5. 工况数据处理
6. 输出生成 (JSON/SQLite/Excel)
"""

import sys
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import pandas as pd

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from core.vehicle_processor import VehicleDataProcessor


class TestVehicleProcessorInit:
    """测试处理器初始化"""

    def test_init_with_ripple_folder(self, tmp_path):
        """测试直接传入RIPPLE文件夹"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor.vehicle_folder.name == "V0001_RIPPLE"
        assert processor.parent_folder == tmp_path
        assert processor.vehicle_id == "V0001"

    def test_init_with_parent_folder_auto_detect(self, tmp_path):
        """测试传入父文件夹自动检测RIPPLE子文件夹"""
        parent_dir = tmp_path / "V0001"
        parent_dir.mkdir()
        ripple_dir = parent_dir / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(parent_dir))

        assert processor.vehicle_folder.name == "V0001_RIPPLE"
        assert processor.parent_folder == parent_dir
        assert processor.vehicle_id == "V0001"

    def test_init_without_ripple_subfolder(self, tmp_path):
        """测试没有RIPPLE子文件夹时使用输入作为车辆文件夹"""
        vehicle_dir = tmp_path / "V0002"
        vehicle_dir.mkdir()
        (vehicle_dir / "vehicle_info.md").write_text("| 车型 | V0002 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(vehicle_dir))

        assert processor.vehicle_folder.name == "V0002"
        assert processor.vehicle_id == "V0002"

    def test_custom_output_dir(self, tmp_path):
        """测试自定义输出目录"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        custom_output = tmp_path / "custom_output"
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir), config={'output_dir': str(custom_output)})

        assert processor.output_dir == custom_output

    def test_extract_vehicle_id_from_folder(self, tmp_path):
        """测试从文件夹名提取车辆ID"""
        ripple_dir = tmp_path / "TEST123_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | TEST123 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor.vehicle_id == "TEST123"


class TestVehicleInfoParsing:
    """测试车辆信息解析"""

    def test_parse_vehicle_info_md(self, tmp_path):
        """测试解析Markdown格式的vehicle_info"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path

        md_content = """| 参数 | 值 |
|---|---|
| 车型 | 坦克500 |
| 车长mm | 5078 |
| 车宽mm | 1934 |
| 制造商 | 长城汽车 |
"""
        (parent_dir / "vehicle_info.md").write_text(md_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_vehicle_info()

        assert processor.vehicle_info['车型'] == '坦克500'
        assert processor.vehicle_info['车长mm'] == '5078'
        assert processor.vehicle_info['制造商'] == '长城汽车'

    def test_parse_vehicle_info_md_with_encoding_fallback(self, tmp_path):
        """测试MD文件编码回退 (UTF-8失败时使用GBK)"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path

        # 使用GBK编码写入
        md_content = "| 车型 | 测试车 |\n|---|---|\n"
        (parent_dir / "vehicle_info.md").write_text(md_content, encoding='gbk')

        processor = VehicleDataProcessor(str(ripple_dir))
        # 不应抛出异常
        processor._load_vehicle_info()

        assert '车型' in processor.vehicle_info

    def test_parse_vehicle_info_xlsx(self, tmp_path):
        """测试解析Excel格式的vehicle_info"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path

        # 创建Excel文件
        df = pd.DataFrame({
            '参数': ['车型', '车长mm', '制造商'],
            '值': ['坦克300', '4760', '长城汽车']
        })
        df.to_excel(parent_dir / "vehicle_info.xlsx", index=False)

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_vehicle_info()

        assert processor.vehicle_info['车型'] == '坦克300'

    def test_missing_vehicle_info_raises_error(self, tmp_path):
        """测试缺少vehicle_info时抛出错误"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()

        processor = VehicleDataProcessor(str(ripple_dir))

        with pytest.raises(FileNotFoundError):
            processor._load_vehicle_info()


class TestNamingRulesParsing:
    """测试命名规则解析"""

    def test_parse_test_rules_md(self, tmp_path):
        """测试解析测试命名规则MD文件"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        # 创建测试规则文件
        rules_content = """| 电量状态 | 工况名称 | 命名示例 |
|---|---|---|
| ≥70% | 超越加速 | 87_超车80-140(运动模式) |
| ≤40% | 直流充电暖风 | 20_直流充电暖风 |
"""
        (parent_dir / "test_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_test_naming_rules()

        assert '87_超车80-140(运动模式)' in processor.test_rules
        assert processor.test_rules['87_超车80-140(运动模式)']['condition_name'] == '超越加速'

    def test_parse_sensor_rules_md_table_format(self, tmp_path):
        """测试解析传感器命名规则MD文件 (表格格式)"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        rules_content = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
| FM_A | 前电机电流 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()

        assert 'FM_V' in processor.sensor_rules
        assert processor.sensor_rules['FM_V']['component_name'] == '前电机电压'
        assert processor.sensor_rules['FM_V']['unit'] == 'V'
        assert processor.sensor_rules['FM_A']['unit'] == 'A'

    def test_parse_sensor_rules_md_colon_format(self, tmp_path):
        """测试解析传感器命名规则MD文件 (冒号格式)"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        rules_content = """FM_V: 前电机电压(V)
FM_A: 前电机电流(A)
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()

        assert 'FM_V' in processor.sensor_rules
        assert processor.sensor_rules['FM_V']['component_name'] == '前电机电压(V)'


class TestComponentDiscovery:
    """测试组件发现"""

    def test_discover_components(self, tmp_path):
        """测试发现组件文件夹"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        # 创建组件文件夹
        (ripple_dir / "FM_V").mkdir()
        (ripple_dir / "FM_A").mkdir()
        (ripple_dir / "RM_V").mkdir()

        # 创建传感器规则
        rules_content = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
| FM_A | 前电机电流 |
| RM_V | 后电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()
        component_folders = processor._discover_components()

        assert len(component_folders) == 3
        folder_names = [f.name for f in component_folders]
        assert 'FM_V' in folder_names
        assert 'FM_A' in folder_names
        assert 'RM_V' in folder_names

    def test_skip_undefined_components(self, tmp_path):
        """测试跳过未定义的组件文件夹"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        # 创建组件文件夹
        (ripple_dir / "FM_V").mkdir()  # 已定义
        (ripple_dir / "UNKNOWN").mkdir()  # 未定义

        rules_content = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()
        component_folders = processor._discover_components()

        assert len(component_folders) == 1
        assert component_folders[0].name == 'FM_V'
        assert len(processor.warnings) == 1
        assert 'UNKNOWN' in processor.warnings[0]

    def test_skip_output_folders(self, tmp_path):
        """测试跳过输出文件夹"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        parent_dir = tmp_path
        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        # 创建组件文件夹和输出文件夹
        (ripple_dir / "FM_V").mkdir()
        (ripple_dir / "V0001_RIPPLE_output").mkdir()

        rules_content = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()
        component_folders = processor._discover_components()

        assert len(component_folders) == 1
        assert component_folders[0].name == 'FM_V'


class TestConditionProcessing:
    """测试工况数据处理"""

    def test_extract_soc_standard_format(self, tmp_path):
        """测试从标准格式提取SOC"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("87_超车80-140(运动模式)") == 87
        assert processor._extract_soc("20_直流充电暖风") == 20
        assert processor._extract_soc("40_匀速80") == 40

    def test_extract_soc_slope_format(self, tmp_path):
        """测试从坡度格式提取SOC"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("坡度10_81_匀速80暖风") == 81
        assert processor._extract_soc("坡度10_32_急加速") == 32

    def test_extract_soc_dash_separator(self, tmp_path):
        """测试从-分隔符格式提取SOC（V0006等车辆）"""
        ripple_dir = tmp_path / "V0006_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0006 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("25-交流充电冷风") == 25
        assert processor._extract_soc("55-直流充电暖风") == 55
        assert processor._extract_soc("87-匀速100暖风（运动模式）") == 87
        assert processor._extract_soc("39-超车80-140（运动模式）dmd") == 39

    def test_extract_soc_slope_with_dash_separator(self, tmp_path):
        """测试坡度工况使用-分隔符提取SOC（V0006等车辆）"""
        ripple_dir = tmp_path / "V0006_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0006 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("坡度10-24-匀速80暖风（运动模式）") == 24
        assert processor._extract_soc("坡度10-31-匀速80冷风（运动模式）") == 31

    def test_extract_soc_gbk_corruption(self, tmp_path):
        """测试从GBK乱码工况名提取SOC"""
        ripple_dir = tmp_path / "V0017_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0017 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        # GBK乱码坡度前缀 + _ 分隔符
        assert processor._extract_soc("�¶�10_26_匀速80冷风") == 26
        assert processor._extract_soc("�¶�10_27_匀速80暖风") == 27
        assert processor._extract_soc("�¶�10_28_急加速0-80") == 28

    def test_extract_soc_slope_with_space_separator(self, tmp_path):
        """测试坡度工况使用空格分隔符提取SOC（V0009/V0010等车辆）"""
        ripple_dir = tmp_path / "V0009_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0009 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("�¶�10 47_匀速80冷风") == 47
        assert processor._extract_soc("�¶�10 51_匀速80暖风") == 51
        assert processor._extract_soc("�¶�10 15_匀速80暖风") == 15

    def test_extract_soc_mixed_separators(self, tmp_path):
        """测试混用分隔符格式提取SOC"""
        ripple_dir = tmp_path / "V0009_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0009 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("�¶�10-24-匀速80暖风（运动模式）") == 24
        assert processor._extract_soc("32_多次 加速") == 32  # 空格在描述中

    def test_normalize_condition_id(self, tmp_path):
        """测试condition_id规范化"""
        ripple_dir = tmp_path / "V0017_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0017 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._normalize_condition_id("�¶�10_82_匀速80暖风") == "坡度10_82_匀速80暖风"
        assert processor._normalize_condition_id("�¶�10-24-匀速80暖风") == "坡度10-24-匀速80暖风"
        assert processor._normalize_condition_id("坡度10_81_匀速80暖风") == "坡度10_81_匀速80暖风"  # 正常情况不变
        assert processor._normalize_condition_id("87_超车80-140") == "87_超车80-140"  # 普通工况不变

    def test_extract_soc_edge_cases(self, tmp_path):
        """测试SOC提取边界情况"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._extract_soc("") is None
        assert processor._extract_soc(None) is None
        assert processor._extract_soc("invalid") is None
        assert processor._extract_soc("abc_测试") is None
        assert processor._extract_soc("坡度100_测试") is None  # 负向前瞻保护

    def test_get_soc_level(self, tmp_path):
        """测试SOC等级映射"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        assert processor._get_soc_level(87) == "≥70%"
        assert processor._get_soc_level(70) == "≥70%"
        assert processor._get_soc_level(50) == "40%-70%"
        assert processor._get_soc_level(40) == "40%-70%"
        assert processor._get_soc_level(20) == "≤40%"
        assert processor._get_soc_level(None) == "Unknown"

    def test_parse_image_filenames(self, tmp_path):
        """测试解析图片文件名"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        # 创建测试图片文件
        (comp_dir / "87_超车80-140_FM_V_10.5Ipp_6.84kHz_4.195V.png").write_text("fake")
        (comp_dir / "20_直流充电_FM_V_5.2Ipp_3.42kHz_2.1V.png").write_text("fake")

        processor = VehicleDataProcessor(str(ripple_dir))
        images = list(comp_dir.glob("*.png"))
        image_map = processor._parse_image_filenames(images, "FM_V")

        assert "87_超车80-140" in image_map
        assert "20_直流充电" in image_map
        assert image_map["87_超车80-140"]["filename"].endswith(".png")


class TestOutputGeneration:
    """测试输出生成"""

    def test_generate_json_output(self, tmp_path):
        """测试生成JSON输出"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor.vehicle_info = {"车型": "测试车"}
        processor.components = {}

        result = {
            'vehicle': {'vehicle_id': 'V0001', 'vehicle_info': processor.vehicle_info},
            'components': {},
            'metadata': {'total_components': 0, 'total_conditions': 0, 'warnings': []}
        }

        processor._generate_json(result)

        json_path = processor.output_dir / "V0001_RIPPLE_data.json"
        assert json_path.exists()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['vehicle']['vehicle_id'] == 'V0001'

    def test_generate_sqlite_output(self, tmp_path):
        """测试生成SQLite输出"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor.vehicle_info = {"车型": "测试车"}

        result = {
            'vehicle': {'vehicle_id': 'V0001', 'vehicle_info': processor.vehicle_info},
            'components': {
                'FM_V': {
                    'component_name': '前电机电压',
                    'unit': 'V',
                    'conditions': {
                        '87_test': {
                            'condition_name': '测试工况',
                            'soc_level': '≥70%',
                            'time_domain': {'effective_value': 1.0, 'vpp': 0.5},
                            'frequency_domain': {
                                'peak_ranking': '1st',
                                'peak_frequency_khz': 10.0,
                                'peak_amplitude': 0.1,
                                'rms': 0.05
                            },
                            'image_path': '/path/to/image.png'
                        }
                    }
                }
            },
            'metadata': {'total_components': 1, 'total_conditions': 1, 'warnings': []}
        }

        processor._generate_sqlite(result)

        db_path = processor.output_dir / "V0001_RIPPLE.db"
        assert db_path.exists()

        # 验证数据库内容
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM vehicles")
        vehicles = cursor.fetchall()
        assert len(vehicles) == 1
        assert vehicles[0][0] == 'V0001'

        cursor.execute("SELECT * FROM components")
        components = cursor.fetchall()
        assert len(components) == 1
        assert components[0][0] == 'FM_V'

        cursor.execute("SELECT * FROM test_results")
        results = cursor.fetchall()
        assert len(results) == 1

        conn.close()


class TestConfigurationDriven:
    """测试配置驱动功能"""

    def test_init_config_manager(self, tmp_path):
        """测试配置管理器初始化"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        # 配置管理器应该被初始化 (可能为None如果配置加载失败)
        assert hasattr(processor, 'config_mgr')

    def test_extract_field_fallback(self, tmp_path):
        """测试字段提取回退机制"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor.field_config = None  # 模拟配置加载失败

        raw_data = {'车型': '坦克500', '制造商': '长城'}

        result = processor._extract_field_fallback(raw_data, 'vehicle_model')
        assert result == '坦克500'

        result = processor._extract_field_fallback(raw_data, 'manufacturer')
        assert result == '长城'


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_statistics_file(self, tmp_path):
        """测试处理空统计文件"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()
        parent_dir = tmp_path

        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        # 创建空的statistics.xlsx
        df = pd.DataFrame()
        df.to_excel(comp_dir / "statistics.xlsx", index=False)

        rules_content = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()

        # 处理组件不应抛出异常
        processor._process_component(comp_dir)

    def test_missing_statistics_file(self, tmp_path):
        """测试缺少统计文件时发出警告"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        comp_dir = ripple_dir / "FM_V"
        comp_dir.mkdir()
        parent_dir = tmp_path

        (parent_dir / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        rules_content = """| Channel | 描述 |
|---|---|
| FM_V | 前电机电压 |
"""
        (parent_dir / "sensor_naming_rules.md").write_text(rules_content, encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))
        processor._load_sensor_naming_rules()
        processor._process_component(comp_dir)

        assert len(processor.warnings) == 1
        assert 'statistics.xlsx' in processor.warnings[0]

    def test_invalid_condition_row(self, tmp_path):
        """测试处理无效工况行"""
        ripple_dir = tmp_path / "V0001_RIPPLE"
        ripple_dir.mkdir()
        (tmp_path / "vehicle_info.md").write_text("| 车型 | V0001 |\n|---|---|\n", encoding='utf-8')

        processor = VehicleDataProcessor(str(ripple_dir))

        # 创建包含NaN的Series
        row = pd.Series([None, None, None])
        result = processor._process_condition_row(row, ripple_dir, {})

        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
