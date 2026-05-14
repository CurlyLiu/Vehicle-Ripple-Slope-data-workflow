"""SQLite exporter for vehicle data."""

import re
import sqlite3
from pathlib import Path

from .base import BaseExporter, ExportResult

# Allowed table names for security
ALLOWED_TABLES = {
    'vehicles', 'components', 'test_conditions',
    'ripple_results', 'slope_results', 'data_batches'
}


def _validate_table_name(table: str) -> bool:
    """Validate table name to prevent SQL injection."""
    if table in ALLOWED_TABLES:
        return True
    # Additional validation for standard naming
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table))


class SqliteExporter(BaseExporter):
    """Export vehicle data to a separate SQLite database."""

    def export_vehicle(self, conn: sqlite3.Connection, vehicle_id: str, output_path: Path) -> ExportResult:
        """Export a single vehicle to a new SQLite database."""
        errors = []
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing file if present
            if output_path.exists():
                output_path.unlink()
            
            # Create new database
            new_conn = sqlite3.connect(output_path)
            new_cursor = new_conn.cursor()
            
            # Create schema and copy data
            records = self._copy_vehicle_data(conn, new_conn, vehicle_id)
            
            new_conn.commit()
            new_conn.close()
            
            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=records
            )
            
        except (OSError, sqlite3.Error, ValueError) as e:
            errors.append(str(e))
            return ExportResult(success=False, errors=errors)

    def export_all(self, conn: sqlite3.Connection, output_path: Path) -> ExportResult:
        """Export all vehicles to a new SQLite database."""
        errors = []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT vehicle_id FROM vehicles")
            vehicle_ids = [row[0] for row in cursor.fetchall()]
            
            if not vehicle_ids:
                return ExportResult(
                    success=False,
                    errors=["No vehicles found in database"]
                )
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing file if present
            if output_path.exists():
                output_path.unlink()
            
            # Create new database
            new_conn = sqlite3.connect(output_path)
            
            # Copy schema and all data
            total_records = 0
            for vid in vehicle_ids:
                total_records += self._copy_vehicle_data(conn, new_conn, vid)
            
            new_conn.commit()
            new_conn.close()
            
            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=total_records
            )
            
        except (OSError, sqlite3.Error, ValueError) as e:
            errors.append(str(e))
            return ExportResult(success=False, errors=errors)

    def _copy_vehicle_data(self, source_conn: sqlite3.Connection, 
                          target_conn: sqlite3.Connection, vehicle_id: str) -> int:
        """Copy a vehicle's data to the target database. Returns record count."""
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        records = 0
        
        # Get table schema from source
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in source_cursor.fetchall()]
        
        for table in tables:
            if table.startswith('sqlite_'):
                continue

            # Validate table name to prevent SQL injection
            if not _validate_table_name(table):
                continue

            # Get schema using parameterized query (table name validated above)
            source_cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            schema_row = source_cursor.fetchone()

            if schema_row and schema_row[0]:
                # Create table in target
                target_cursor.execute(schema_row[0])

            # Get columns - PRAGMA doesn't support parameterized table names
            # but table name is validated above
            source_cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in source_cursor.fetchall()]

            if not columns:
                continue

            # Validate column names
            valid_columns = [col for col in columns if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col)]
            if not valid_columns:
                continue

            # Copy data based on table type
            if table == 'vehicles':
                source_cursor.execute(
                    f"SELECT {','.join(valid_columns)} FROM {table} WHERE vehicle_id = ?",
                    (vehicle_id,)
                )
            elif table in ('ripple_results', 'slope_results', 'test_results'):
                source_cursor.execute(
                    f"SELECT {','.join(valid_columns)} FROM {table} WHERE vehicle_id = ?",
                    (vehicle_id,)
                )
            else:
                # For other tables, copy all data (components, conditions, etc.)
                source_cursor.execute(f"SELECT {','.join(valid_columns)} FROM {table}")

            rows = source_cursor.fetchall()

            if rows:
                placeholders = ','.join(['?' for _ in valid_columns])
                target_cursor.executemany(
                    f"INSERT INTO {table} ({','.join(valid_columns)}) VALUES ({placeholders})",
                    rows
                )
                records += len(rows)
        
        return records
