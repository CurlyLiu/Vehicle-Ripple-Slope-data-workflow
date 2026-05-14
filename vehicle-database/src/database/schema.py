"""
数据库表结构定义
"""

# 车辆信息表
CREATE_VEHICLES_TABLE = """
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id TEXT PRIMARY KEY,
    vehicle_model TEXT NOT NULL,
    manufacturer TEXT,
    level TEXT,
    energy_type TEXT,
    length_mm INTEGER,
    width_mm INTEGER,
    height_mm INTEGER,
    wheelbase_mm INTEGER,
    front_track_mm INTEGER,
    rear_track_mm INTEGER,
    min_ground_clearance_mm INTEGER,
    curb_weight_kg REAL,
    max_weight_kg REAL,
    front_motor_max_power_kw REAL,
    rear_motor_max_power_kw REAL,
    front_motor_max_torque_nm REAL,
    rear_motor_max_torque_nm REAL,
    system_total_power_kw REAL,
    high_voltage_architecture TEXT,
    battery_type TEXT,
    battery_capacity_kwh REAL,
    fast_charge_power_kw REAL,
    front_suspension TEXT,
    rear_suspension TEXT,
    engine_model TEXT,
    transmission_type TEXT,
    displacement_l REAL,
    engine_max_power_kw TEXT,
    engine_max_torque_nm TEXT,
    price_wan REAL,
    vehicle_info_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 部件定义表
CREATE_COMPONENTS_TABLE = """
CREATE TABLE IF NOT EXISTS components (
    channel_code TEXT PRIMARY KEY,
    component_name TEXT NOT NULL,
    component_type TEXT,
    unit TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 测试工况表
CREATE_TEST_CONDITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS test_conditions (
    condition_id TEXT PRIMARY KEY,
    condition_name TEXT NOT NULL,
    soc_level TEXT NOT NULL,
    category TEXT,
    description TEXT,
    standard_condition_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 纹波测试结果表
CREATE_RIPPLE_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS ripple_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT NOT NULL,
    component_code TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    time_domain_effective_value REAL,
    vpp_value REAL,
    peak_ranking_json TEXT,
    peak_frequency_khz REAL,
    peak_amplitude REAL,
    frequency_rms REAL,
    image_path TEXT,
    match_confidence REAL,
    match_method TEXT,
    raw_data_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (component_code) REFERENCES components(channel_code),
    FOREIGN KEY (condition_id) REFERENCES test_conditions(condition_id),
    UNIQUE(vehicle_id, component_code, condition_id)
);
"""

# 斜率测试结果表
CREATE_SLOPE_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS slope_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT NOT NULL,
    component_code TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    slope_max REAL,
    slope_min REAL,
    slope_max_abs REAL,
    slope_unit TEXT DEFAULT 'V/s',
    image_path TEXT,
    match_confidence REAL,
    match_method TEXT,
    raw_data_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (component_code) REFERENCES components(channel_code),
    FOREIGN KEY (condition_id) REFERENCES test_conditions(condition_id),
    UNIQUE(vehicle_id, component_code, condition_id)
);
"""

# 数据批次表
CREATE_DATA_BATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS data_batches (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_folder TEXT NOT NULL,
    processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_components INTEGER,
    total_conditions INTEGER,
    warnings_count INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    warnings_json TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);
"""

# 模糊匹配日志表
CREATE_MATCHING_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS matching_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT NOT NULL,
    condition_id TEXT,
    matched_condition_name TEXT,
    match_confidence REAL,
    match_method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 创建索引
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ripple_vehicle ON ripple_results(vehicle_id);",
    "CREATE INDEX IF NOT EXISTS idx_ripple_component ON ripple_results(component_code);",
    "CREATE INDEX IF NOT EXISTS idx_ripple_condition ON ripple_results(condition_id);",
    "CREATE INDEX IF NOT EXISTS idx_ripple_vpp ON ripple_results(vpp_value);",
    "CREATE INDEX IF NOT EXISTS idx_slope_vehicle ON slope_results(vehicle_id);",
    "CREATE INDEX IF NOT EXISTS idx_slope_component ON slope_results(component_code);",
    "CREATE INDEX IF NOT EXISTS idx_slope_condition ON slope_results(condition_id);",
    "CREATE INDEX IF NOT EXISTS idx_slope_max_abs ON slope_results(slope_max_abs);",
    "CREATE INDEX IF NOT EXISTS idx_conditions_soc ON test_conditions(soc_level);",
    "CREATE INDEX IF NOT EXISTS idx_conditions_category ON test_conditions(category);",
]

# 兼容性修复：为旧数据库添加可能缺失的列
MIGRATE_SCHEMA = [
    """ALTER TABLE test_conditions ADD COLUMN category TEXT;""",
]

# 所有创建语句（向后兼容：单库包含所有表）
ALL_SCHEMA = [
    CREATE_VEHICLES_TABLE,
    CREATE_COMPONENTS_TABLE,
    CREATE_TEST_CONDITIONS_TABLE,
    CREATE_RIPPLE_RESULTS_TABLE,
    CREATE_SLOPE_RESULTS_TABLE,
    CREATE_DATA_BATCHES_TABLE,
    CREATE_MATCHING_LOGS_TABLE,
] + MIGRATE_SCHEMA + CREATE_INDEXES

# 纹波数据库 Schema（不含 slope_results）
RIPPLE_SCHEMA = [
    CREATE_VEHICLES_TABLE,
    CREATE_COMPONENTS_TABLE,
    CREATE_TEST_CONDITIONS_TABLE,
    CREATE_RIPPLE_RESULTS_TABLE,
    CREATE_DATA_BATCHES_TABLE,
    CREATE_MATCHING_LOGS_TABLE,
] + [idx for idx in CREATE_INDEXES if 'ripple' in idx or 'conditions' in idx]

# 斜率数据库 Schema（不含 ripple_results）
SLOPE_SCHEMA = [
    CREATE_VEHICLES_TABLE,
    CREATE_COMPONENTS_TABLE,
    CREATE_TEST_CONDITIONS_TABLE,
    CREATE_SLOPE_RESULTS_TABLE,
    CREATE_DATA_BATCHES_TABLE,
    CREATE_MATCHING_LOGS_TABLE,
] + [idx for idx in CREATE_INDEXES if 'slope' in idx or 'conditions' in idx]
