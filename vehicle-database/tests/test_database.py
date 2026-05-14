"""
Tests for database connection and schema modules.
"""

import sqlite3
from pathlib import Path

import pytest

from src.database.connection import DatabaseConnection
from src.database.schema import ALL_SCHEMA


class TestDatabaseConnection:
    """Test suite for DatabaseConnection class."""

    def test_init(self, temp_db_path):
        """Test DatabaseConnection initialization."""
        db = DatabaseConnection(str(temp_db_path))
        assert db.db_path == temp_db_path
        assert db._connection is None

    def test_connect_creates_database(self, temp_db_path):
        """Test connect creates the database file."""
        db = DatabaseConnection(str(temp_db_path))
        conn = db.connect()

        assert temp_db_path.exists()
        assert isinstance(conn, sqlite3.Connection)

        db.close()

    def test_connect_creates_parent_directories(self, temp_dir):
        """Test connect creates parent directories if they don't exist."""
        nested_path = temp_dir / 'deep' / 'nested' / 'test.db'
        db = DatabaseConnection(str(nested_path))
        db.connect()

        assert nested_path.exists()
        db.close()

    def test_connect_sets_row_factory(self, temp_db_path):
        """Test connect sets sqlite3.Row row factory."""
        db = DatabaseConnection(str(temp_db_path))
        conn = db.connect()

        assert conn.row_factory == sqlite3.Row
        db.close()

    def test_close(self, temp_db_path):
        """Test close closes the connection."""
        db = DatabaseConnection(str(temp_db_path))
        db.connect()
        db.close()

        assert db._connection is None

    def test_close_without_connect(self, temp_db_path):
        """Test close when no connection exists."""
        db = DatabaseConnection(str(temp_db_path))
        # Should not raise
        db.close()

    def test_get_connection_creates_if_none(self, temp_db_path):
        """Test get_connection creates connection if none exists."""
        db = DatabaseConnection(str(temp_db_path))
        conn = db.get_connection()

        assert conn is not None
        assert db._connection is not None
        db.close()

    def test_get_connection_returns_existing(self, temp_db_path):
        """Test get_connection returns existing connection."""
        db = DatabaseConnection(str(temp_db_path))
        conn1 = db.connect()
        conn2 = db.get_connection()

        assert conn1 is conn2
        db.close()

    def test_execute(self, temp_db):
        """Test execute method."""
        cursor = temp_db.execute("SELECT 1 as test")
        result = cursor.fetchone()

        assert result['test'] == 1

    def test_executescript(self, temp_db):
        """Test executescript method."""
        temp_db.executescript("""
            CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO test_table (name) VALUES ('test');
        """)

        cursor = temp_db.execute("SELECT * FROM test_table")
        result = cursor.fetchone()

        assert result['name'] == 'test'

    def test_transaction_success(self, temp_db):
        """Test transaction context manager commits on success."""
        temp_db.executescript("""
            CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);
        """)

        with temp_db.transaction() as conn:
            conn.execute("INSERT INTO test_table (name) VALUES ('committed')")

        cursor = temp_db.execute("SELECT * FROM test_table")
        result = cursor.fetchone()

        assert result['name'] == 'committed'

    def test_transaction_rollback(self, temp_db):
        """Test transaction context manager rolls back on exception."""
        temp_db.executescript("""
            CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);
        """)

        with pytest.raises(ValueError):
            with temp_db.transaction() as conn:
                conn.execute("INSERT INTO test_table (name) VALUES ('should_rollback')")
                raise ValueError("Test error")

        cursor = temp_db.execute("SELECT * FROM test_table")
        result = cursor.fetchone()

        assert result is None

    def test_context_manager(self, temp_db_path):
        """Test DatabaseConnection as context manager."""
        with DatabaseConnection(str(temp_db_path)) as db:
            conn = db.connect()
            assert conn is not None

        assert db._connection is None


class TestDatabaseSchema:
    """Test suite for database schema definitions."""

    def test_all_schema_is_list(self):
        """Test ALL_SCHEMA is a list."""
        assert isinstance(ALL_SCHEMA, list)
        assert len(ALL_SCHEMA) > 0

    def test_schema_creates_tables(self, temp_db):
        """Test schema creates all expected tables."""
        cursor = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row['name'] for row in cursor.fetchall()]

        expected_tables = [
            'components',
            'data_batches',
            'matching_logs',
            'ripple_results',
            'slope_results',
            'test_conditions',
            'vehicles',
        ]

        for table in expected_tables:
            assert table in tables

    def test_schema_creates_indexes(self, temp_db):
        """Test schema creates expected indexes."""
        cursor = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = [row['name'] for row in cursor.fetchall()]

        expected_indexes = [
            'idx_conditions_category',
            'idx_conditions_soc',
            'idx_ripple_component',
            'idx_ripple_condition',
            'idx_ripple_vpp',
            'idx_ripple_vehicle',
            'idx_slope_component',
            'idx_slope_condition',
            'idx_slope_max_abs',
            'idx_slope_vehicle',
        ]

        for idx in expected_indexes:
            assert idx in indexes

    def test_vehicles_table_structure(self, temp_db):
        """Test vehicles table has correct columns."""
        cursor = temp_db.execute("PRAGMA table_info(vehicles)")
        columns = {row['name'] for row in cursor.fetchall()}

        expected_columns = {
            'vehicle_id', 'vehicle_model', 'manufacturer', 'level',
            'energy_type', 'length_mm', 'width_mm', 'height_mm',
            'wheelbase_mm', 'curb_weight_kg', 'max_weight_kg',
            'battery_type', 'battery_capacity_kwh', 'fast_charge_power_kw',
            'vehicle_info_json', 'created_at', 'updated_at'
        }

        for col in expected_columns:
            assert col in columns

    def test_ripple_results_table_structure(self, temp_db):
        """Test ripple_results table has correct columns."""
        cursor = temp_db.execute("PRAGMA table_info(ripple_results)")
        columns = {row['name'] for row in cursor.fetchall()}

        expected_columns = {
            'id', 'vehicle_id', 'component_code', 'condition_id',
            'time_domain_effective_value', 'vpp_value', 'peak_ranking_json',
            'peak_frequency_khz', 'peak_amplitude', 'frequency_rms',
            'image_path', 'match_confidence', 'match_method',
            'raw_data_json', 'created_at'
        }

        for col in expected_columns:
            assert col in columns

    def test_slope_results_table_structure(self, temp_db):
        """Test slope_results table has correct columns."""
        cursor = temp_db.execute("PRAGMA table_info(slope_results)")
        columns = {row['name'] for row in cursor.fetchall()}

        expected_columns = {
            'id', 'vehicle_id', 'component_code', 'condition_id',
            'slope_max', 'slope_min', 'slope_max_abs', 'slope_unit',
            'image_path', 'match_confidence', 'match_method',
            'raw_data_json', 'created_at'
        }

        for col in expected_columns:
            assert col in columns

    def test_unique_constraint_ripple(self, temp_db):
        """Test ripple_results has unique constraint on (vehicle_id, component_code, condition_id)."""
        cursor = temp_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ripple_results'"
        )
        schema = cursor.fetchone()[0]

        assert 'UNIQUE(vehicle_id, component_code, condition_id)' in schema

    def test_unique_constraint_slope(self, temp_db):
        """Test slope_results has unique constraint on (vehicle_id, component_code, condition_id)."""
        cursor = temp_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='slope_results'"
        )
        schema = cursor.fetchone()[0]

        assert 'UNIQUE(vehicle_id, component_code, condition_id)' in schema

    def test_foreign_keys(self, temp_db):
        """Test foreign key constraints exist."""
        cursor = temp_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ripple_results'"
        )
        schema = cursor.fetchone()[0]

        assert 'FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)' in schema
        assert 'FOREIGN KEY (component_code) REFERENCES components(channel_code)' in schema
        assert 'FOREIGN KEY (condition_id) REFERENCES test_conditions(condition_id)' in schema

    def test_insert_and_query_vehicle(self, temp_db):
        """Test inserting and querying a vehicle."""
        temp_db.execute("""
            INSERT INTO vehicles (vehicle_id, vehicle_model, manufacturer)
            VALUES (?, ?, ?)
        """, ('V0001', 'Test Model', 'Test Manufacturer'))

        cursor = temp_db.execute(
            "SELECT * FROM vehicles WHERE vehicle_id = ?", ('V0001',)
        )
        row = cursor.fetchone()

        assert row['vehicle_id'] == 'V0001'
        assert row['vehicle_model'] == 'Test Model'
        assert row['manufacturer'] == 'Test Manufacturer'

    def test_insert_duplicate_vehicle(self, temp_db):
        """Test inserting duplicate vehicle raises error."""
        temp_db.execute("""
            INSERT INTO vehicles (vehicle_id, vehicle_model)
            VALUES (?, ?)
        """, ('V0001', 'Model A'))

        with pytest.raises(sqlite3.IntegrityError):
            temp_db.execute("""
                INSERT INTO vehicles (vehicle_id, vehicle_model)
                VALUES (?, ?)
            """, ('V0001', 'Model B'))

    def test_insert_ripple_result(self, temp_db):
        """Test inserting a ripple result."""
        # Insert prerequisite data
        temp_db.execute("""
            INSERT INTO vehicles (vehicle_id, vehicle_model) VALUES (?, ?)
        """, ('V0001', 'Test Model'))
        temp_db.execute("""
            INSERT INTO components (channel_code, component_name, unit)
            VALUES (?, ?, ?)
        """, ('FM_V', 'Front Motor Voltage', 'V'))
        temp_db.execute("""
            INSERT INTO test_conditions (condition_id, condition_name, soc_level)
            VALUES (?, ?, ?)
        """, ('test_cond', 'Test Condition', '≥70%'))

        # Insert ripple result
        temp_db.execute("""
            INSERT INTO ripple_results
            (vehicle_id, component_code, condition_id, vpp_value, peak_frequency_khz)
            VALUES (?, ?, ?, ?, ?)
        """, ('V0001', 'FM_V', 'test_cond', 12.5, 5.2))

        cursor = temp_db.execute(
            "SELECT * FROM ripple_results WHERE vehicle_id = ?", ('V0001',)
        )
        row = cursor.fetchone()

        assert row['vpp_value'] == 12.5
        assert row['peak_frequency_khz'] == 5.2
