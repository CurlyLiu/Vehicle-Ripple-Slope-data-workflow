"""Excel exporter for vehicle data."""

import sqlite3
from pathlib import Path

import pandas as pd

from .base import BaseExporter, ExportResult


class ExcelExporter(BaseExporter):
    """Export vehicle data to Excel format using pandas."""

    def __init__(self, data_type: str = 'ripple'):
        """Initialize exporter with data type filter.

        Args:
            data_type: 'ripple' (queries ripple_results) or 'slope' (queries slope_results).
                       Default 'ripple' preserves backward compatibility.
        """
        if data_type not in ('ripple', 'slope'):
            raise ValueError(f"data_type must be 'ripple' or 'slope', got {data_type!r}")
        self.data_type = data_type

    def export_vehicle(self, conn: sqlite3.Connection, vehicle_id: str, output_path: Path) -> ExportResult:
        """Export a single vehicle to Excel with multiple sheets."""
        errors = []
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                records = self._write_vehicle_sheets(conn, vehicle_id, writer)
            
            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=records
            )
            
        except (OSError, ValueError, ImportError) as e:
            errors.append(str(e))
            return ExportResult(success=False, errors=errors)

    def export_all(self, conn: sqlite3.Connection, output_path: Path) -> ExportResult:
        """Export all vehicles to a single Excel file."""
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
            
            total_records = 0
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                all_results = []
                for vid in vehicle_ids:
                    results = self._get_detailed_results(conn, vid)
                    all_results.extend(results)
                
                if all_results:
                    df_results = pd.DataFrame(all_results)
                    df_results.to_excel(writer, sheet_name='Detailed Results', index=False)
                    self._auto_adjust_columns(writer.sheets['Detailed Results'])
                    total_records = len(all_results)
            
            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=total_records
            )
            
        except (OSError, ValueError, ImportError) as e:
            errors.append(str(e))
            return ExportResult(success=False, errors=errors)

    def _write_vehicle_sheets(self, conn: sqlite3.Connection, vehicle_id: str, writer: pd.ExcelWriter) -> int:
        """Write all sheets for a single vehicle. Returns record count."""
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            vehicle_data = dict(zip(columns, row))
            info_data = [{'Parameter': k, 'Value': v} for k, v in vehicle_data.items()]
            df_info = pd.DataFrame(info_data)
            df_info.to_excel(writer, sheet_name='Vehicle Information', index=False)
        
        results = self._get_detailed_results(conn, vehicle_id)
        if results:
            df_results = pd.DataFrame(results)
            df_results.to_excel(writer, sheet_name='Detailed Results', index=False)
            return len(results)
        
        return 0

    def _get_detailed_results(self, conn: sqlite3.Connection, vehicle_id: str) -> list[dict]:
        """Get detailed test results for a vehicle, filtered by data_type."""
        cursor = conn.cursor()
        results = []

        if self.data_type == 'ripple':
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ripple_results'")
            has_ripple = cursor.fetchone() is not None

            if has_ripple:
                cursor.execute("""
                    SELECT component_code, condition_id, vpp_value,
                           peak_frequency_khz, peak_amplitude, frequency_rms, image_path
                    FROM ripple_results
                    WHERE vehicle_id = ?
                    ORDER BY component_code, condition_id
                """, (vehicle_id,))

                for row in cursor.fetchall():
                    results.append({
                        'vehicle_id': vehicle_id,
                        'component_code': row[0],
                        'condition_id': row[1],
                        'vpp': row[2],
                        'peak_frequency_khz': row[3],
                        'peak_amplitude': row[4],
                        'rms': row[5],
                        'image_path': row[6],
                        'test_type': 'ripple'
                    })

        if self.data_type == 'slope':
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slope_results'")
            has_slope = cursor.fetchone() is not None

            if has_slope:
                cursor.execute("""
                    SELECT component_code, condition_id, slope_max,
                           slope_min, slope_max_abs, slope_unit, image_path
                    FROM slope_results
                    WHERE vehicle_id = ?
                    ORDER BY component_code, condition_id
                """, (vehicle_id,))

                for row in cursor.fetchall():
                    results.append({
                        'vehicle_id': vehicle_id,
                        'component_code': row[0],
                        'condition_id': row[1],
                        'slope_max': row[2],
                        'slope_min': row[3],
                        'slope_max_abs': row[4],
                        'slope_unit': row[5],
                        'image_path': row[6],
                        'test_type': 'slope'
                    })

        return results

    def _auto_adjust_columns(self, worksheet):
        """Auto-adjust column widths for better readability."""
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
