"""
Pytest configuration and shared fixtures for vehicle-database tests.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_dir(temp_dir):
    """Create a temporary database directory for dual-db tests."""
    db_dir = temp_dir / 'Vehicle_Database'
    db_dir.mkdir(parents=True, exist_ok=True)
    from src.cli.core import init_database
    init_database(db_dir)
    return db_dir


@pytest.fixture
def temp_db_path(temp_dir):
    """Create a temporary database path (backward compat)."""
    return temp_dir / 'test.db'


@pytest.fixture
def temp_db(temp_db_path):
    """Create a temporary database with ALL_SCHEMA (backward compat for single-db tests)."""
    from src.database.connection import DatabaseConnection
    from src.database.schema import ALL_SCHEMA

    db = DatabaseConnection(str(temp_db_path))
    conn = db.connect()

    for schema in ALL_SCHEMA:
        try:
            conn.executescript(schema)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                continue
            raise

    conn.commit()

    yield db

    db.close()


@pytest.fixture
def temp_ripple_db(temp_db_dir):
    """Create a connection to the temporary Ripple.db."""
    from src.database.connection import DatabaseConnection
    db = DatabaseConnection(str(temp_db_dir / 'Ripple.db'))
    db.connect()
    yield db
    db.close()


@pytest.fixture
def temp_slope_db(temp_db_dir):
    """Create a connection to the temporary Slope.db."""
    from src.database.connection import DatabaseConnection
    db = DatabaseConnection(str(temp_db_dir / 'Slope.db'))
    db.connect()
    yield db
    db.close()


@pytest.fixture
def sample_vehicle_data():
    """Return sample vehicle data for testing."""
    return {
        "vehicle": {
            "vehicle_id": "V0001",
            "vehicle_info": {
                "vehicle_model": "Test Model",
                "manufacturer": "Test Manufacturer",
                "级别": "A级",
                "能源类型": "纯电动",
                "length_mm": 4500,
                "width_mm": 1800,
                "height_mm": 1500,
                "轴距(mm)": 2700,
                "整备质量(kg)": 1500,
                "最大满载质量(kg)": 2000,
                "电池类型": "三元锂",
                "电池能量(kWh)": 60,
                "快充功率(kW)": 80
            }
        },
        "components": {
            "FM_V": {
                "component_name": "前电驱系统直流母线端电压(V)",
                "conditions": {
                    "快充_SOC_≥70%": {
                        "condition_name": "快充 SOC ≥70%",
                        "soc_level": "≥70%",
                        "time_domain": {
                            "effective_value": 400.5,
                            "vpp": 12.5
                        },
                        "frequency_domain": {
                            "peak_frequency_khz": 5.2,
                            "peak_amplitude": 2.3,
                            "rms": 1.8,
                            "peak_ranking": {"5.2kHz": 2.3, "10.4kHz": 1.2}
                        },
                        "image_path": "/path/to/image.png",
                        "match_confidence": 0.95,
                        "match_method": "exact"
                    }
                }
            }
        },
        "metadata": {
            "data_type": "ripple",
            "warnings": []
        }
    }


@pytest.fixture
def sample_slope_data():
    """Return sample slope data for testing."""
    return {
        "vehicle": {
            "vehicle_id": "V0001",
            "vehicle_info": {
                "vehicle_model": "Test Model"
            }
        },
        "components": {
            "FM_V": {
                "component_name": "前电驱系统直流母线端电压(V)",
                "conditions": {
                    "加速_SOC_40-70%": {
                        "condition_name": "加速 SOC 40-70%",
                        "soc_level": "40%-70%",
                        "slope": {
                            "max_value": 100.5,
                            "min_value": -80.2,
                            "max_abs_value": 100.5,
                            "unit": "V/s"
                        },
                        "image_path": "/path/to/slope.png",
                        "match_confidence": 0.92,
                        "match_method": "fuzzy"
                    }
                }
            }
        },
        "metadata": {
            "data_type": "slope",
            "warnings": ["Sample warning"]
        }
    }


@pytest.fixture
def sample_json_file(temp_dir, sample_vehicle_data):
    """Create a sample JSON file for testing."""
    json_path = temp_dir / 'V0001_RIPPLE_data.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(sample_vehicle_data, f, ensure_ascii=False, indent=2)
    return json_path


@pytest.fixture
def sample_slope_json_file(temp_dir, sample_slope_data):
    """Create a sample slope JSON file for testing."""
    json_path = temp_dir / 'V0001_SLOPE_data.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(sample_slope_data, f, ensure_ascii=False, indent=2)
    return json_path


@pytest.fixture
def populated_db(temp_db, sample_vehicle_data, sample_slope_data, temp_dir):
    """Create a database with sample data imported (single-db backward compat)."""
    from src.importers.json_importer import JsonImporter

    importer = JsonImporter()

    # Import ripple data
    ripple_path = temp_dir / 'V0001_RIPPLE_data.json'
    with open(ripple_path, 'w', encoding='utf-8') as f:
        json.dump(sample_vehicle_data, f, ensure_ascii=False, indent=2)
    importer.import_data(temp_db.get_connection(), 'V0001', ripple_path)

    # Import slope data
    slope_path = temp_dir / 'V0001_SLOPE_data.json'
    with open(slope_path, 'w', encoding='utf-8') as f:
        json.dump(sample_slope_data, f, ensure_ascii=False, indent=2)
    importer.import_data(temp_db.get_connection(), 'V0001', slope_path)

    return temp_db
