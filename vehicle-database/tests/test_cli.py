"""
Tests for CLI commands (init, add, list, show, stats, export, update, remove).
Uses click.testing.CliRunner for isolated CLI testing.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli import cli


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_db_dir(temp_dir):
    """Create a temporary database directory."""
    db_dir = temp_dir / 'Vehicle_Database'
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def _create_vehicle_json(source_path, vehicle_id, model='Test Model'):
    """Helper to create a vehicle JSON file."""
    v_folder = source_path / vehicle_id
    v_folder.mkdir(exist_ok=True)
    data = {
        'vehicle': {
            'vehicle_id': vehicle_id,
            'vehicle_info': {
                '车型': model,
                '制造商': 'Test Manufacturer'
            }
        },
        'components': {
            'FM_V': {
                'component_name': 'Front Motor Voltage',
                'unit': 'V',
                'conditions': {
                    'cond1': {
                        'condition_name': 'Test Condition',
                        'soc_level': '≥70%',
                        'time_domain': {'effective_value': 400.0, 'vpp': 12.5},
                        'frequency_domain': {
                            'peak_frequency_khz': 5.2,
                            'peak_amplitude': 2.3,
                            'rms': 1.8
                        },
                        'image_path': '/path/to/image.png'
                    }
                }
            }
        }
    }
    json_path = v_folder / f'{vehicle_id}_RIPPLE_data.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return v_folder


class TestCliInit:
    """Test suite for init command."""

    def test_init_creates_dual_databases(self, runner, temp_dir):
        """Test init creates both Ripple.db and Slope.db."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        result = runner.invoke(cli, [
            '--source', str(source_path),
            'init', '-o', str(temp_dir)
        ])

        assert result.exit_code == 0
        db_dir = temp_dir / 'Vehicle_Database'
        assert (db_dir / 'Ripple.db').exists()
        assert (db_dir / 'Slope.db').exists()
        assert 'Ripple.db + Slope.db' in result.output

    def test_init_no_vehicles(self, runner, temp_dir):
        """Test init with empty source directory."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        assert result.exit_code == 0
        assert 'No vehicles found' in result.output

    def test_init_with_vehicle(self, runner, temp_dir):
        """Test init auto-imports vehicles from source."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        assert result.exit_code == 0
        assert 'Found 1 vehicle(s)' in result.output

    def test_init_creates_tables(self, runner, temp_dir):
        """Test init creates all required tables in both databases."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        runner.invoke(cli, [
            '--source', str(source_path),
            'init', '-o', str(temp_dir)
        ])

        db_dir = temp_dir / 'Vehicle_Database'

        # Ripple.db should have ripple_results but not slope_results
        conn = sqlite3.connect(str(db_dir / 'Ripple.db'))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert 'vehicles' in tables
        assert 'components' in tables
        assert 'test_conditions' in tables
        assert 'ripple_results' in tables
        assert 'slope_results' not in tables

        # Slope.db should have slope_results but not ripple_results
        conn = sqlite3.connect(str(db_dir / 'Slope.db'))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert 'vehicles' in tables
        assert 'components' in tables
        assert 'test_conditions' in tables
        assert 'slope_results' in tables
        assert 'ripple_results' not in tables


class TestCliAdd:
    """Test suite for add command."""

    def test_add_vehicle(self, runner, temp_dir):
        """Test adding a vehicle to database."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        # Init first
        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'add', 'V0001'
        ])

        assert result.exit_code == 0
        assert 'Adding 1 vehicle(s)' in result.output

    def test_add_no_database(self, runner, temp_dir):
        """Test add fails when database doesn't exist."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'add', 'V0001'
        ])

        assert result.exit_code == 1
        assert 'Database not found' in result.output

    def test_add_no_args(self, runner, temp_dir):
        """Test add fails without vehicle IDs or --all."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'add'
        ])

        assert result.exit_code == 1
        assert 'Specify vehicle IDs' in result.output


class TestCliList:
    """Test suite for list command."""

    def test_list_empty_database(self, runner, temp_dir):
        """Test list with empty database."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'list'
        ])

        assert result.exit_code == 0
        assert 'No vehicles in database' in result.output

    def test_list_with_vehicles(self, runner, temp_dir):
        """Test list with vehicles in database."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'list'
        ])

        assert result.exit_code == 0
        assert 'V0001' in result.output

    def test_list_json_format(self, runner, temp_dir):
        """Test list with JSON output format."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'list', '--format', 'json'
        ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) >= 1
        assert data[0]['vehicle_id'] == 'V0001'

    def test_list_type_slope(self, runner, temp_dir):
        """Test list --type slope when Slope.db exists."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'list', '--type', 'slope'
        ])

        assert result.exit_code == 0


class TestCliShow:
    """Test suite for show command."""

    def test_show_vehicle(self, runner, temp_dir):
        """Test showing vehicle details."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'show', 'V0001'
        ])

        assert result.exit_code == 0
        assert 'Vehicle ID:' in result.output
        assert 'V0001' in result.output

    def test_show_not_found(self, runner, temp_dir):
        """Test show fails for nonexistent vehicle."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'show', 'NONEXISTENT'
        ])

        assert result.exit_code == 1
        assert 'not found' in result.output


class TestCliStats:
    """Test suite for stats command."""

    def test_stats_empty_database(self, runner, temp_dir):
        """Test stats on empty database."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'stats'
        ])

        assert result.exit_code == 0
        assert 'Vehicles:' in result.output

    def test_stats_with_data(self, runner, temp_dir):
        """Test stats with imported data."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'stats'
        ])

        assert result.exit_code == 0
        assert 'Vehicles:' in result.output
        assert 'Components:' in result.output


class TestCliExport:
    """Test suite for export command."""

    def test_export_vehicle_json(self, runner, temp_dir):
        """Test exporting a vehicle to JSON."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        output_path = temp_dir / 'V0001_export.json'
        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'export', 'V0001',
            '--json', '--output', str(output_path)
        ])

        assert result.exit_code == 0
        assert output_path.exists()

    def test_export_all(self, runner, temp_dir):
        """Test exporting all vehicles."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        output_dir = temp_dir / 'exports'
        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'export', '--all', '--json', '--output', str(output_dir)
        ])

        assert result.exit_code == 0
        assert 'Exporting' in result.output

    def test_export_no_database(self, runner, temp_dir):
        """Test export fails when database doesn't exist."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'export', 'V0001'
        ])

        assert result.exit_code == 1
        assert 'Database not found' in result.output


class TestCliUpdate:
    """Test suite for update command."""

    def test_update_vehicle(self, runner, temp_dir):
        """Test updating a vehicle."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'update', 'V0001'
        ])

        assert result.exit_code == 0
        assert 'Updating 1 vehicle(s)' in result.output

    def test_update_no_database(self, runner, temp_dir):
        """Test update fails when database doesn't exist."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'update', 'V0001'
        ])

        assert result.exit_code == 1
        assert 'Database not found' in result.output


class TestCliRemove:
    """Test suite for remove command."""

    def test_remove_vehicle(self, runner, temp_dir):
        """Test removing a vehicle from database."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()
        _create_vehicle_json(source_path, 'V0001')

        runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'init'
        ])

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'remove', 'V0001'
        ])

        assert result.exit_code == 0
        assert 'Removing 1 vehicle(s)' in result.output

    def test_remove_no_database(self, runner, temp_dir):
        """Test remove fails when database doesn't exist."""
        source_path = temp_dir / 'Vehicle_Date'
        source_path.mkdir()

        result = runner.invoke(cli, [
            '--database', str(temp_dir),
            '--source', str(source_path),
            'remove', 'V0001'
        ])

        assert result.exit_code == 1
        assert 'Database not found' in result.output


class TestCliMain:
    """Test suite for main CLI behavior."""

    def test_cli_help(self, runner):
        """Test CLI help output."""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert 'Vehicle Database CLI' in result.output

    def test_cli_no_command(self, runner):
        """Test CLI with no command shows help.

        Click returns exit_code 2 when no subcommand is provided.
        """
        result = runner.invoke(cli, [])

        assert result.exit_code == 2
        assert 'Vehicle Database CLI' in result.output

    def test_cli_invalid_command(self, runner):
        """Test CLI with invalid command."""
        result = runner.invoke(cli, ['nonexistent'])

        assert result.exit_code != 0
        assert 'No such command' in result.output
