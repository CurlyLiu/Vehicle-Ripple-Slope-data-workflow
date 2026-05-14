"""JSON exporter for vehicle data."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from .base import BaseExporter, ExportResult


class JsonExporter(BaseExporter):
    """Export vehicle data to JSON format matching the import format."""

    def __init__(self, data_type='ripple'):
        self.data_type = data_type
        self.table_name = 'ripple_results' if data_type == 'ripple' else 'slope_results'
        self.other_table = 'slope_results' if data_type == 'ripple' else 'ripple_results'

    def export_vehicle(self, conn: sqlite3.Connection, vehicle_id: str, output_path: Path) -> ExportResult:
        """Export a single vehicle to JSON."""
        errors = []

        try:
            result = self._build_vehicle_json(conn, vehicle_id)

            if not result:
                return ExportResult(
                    success=False,
                    errors=[f"Vehicle {vehicle_id} not found"]
                )

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            records = sum(
                len(comp.get("conditions", {}))
                for comp in result.get("components", {}).values()
            )

            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=records
            )

        except (OSError, ValueError, TypeError) as e:
            errors.append(str(e))
            return ExportResult(success=False, errors=errors)

    def export_all(self, conn: sqlite3.Connection, output_path: Path) -> ExportResult:
        """Export all vehicles to a single JSON file."""
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

            all_vehicles = []
            total_records = 0

            for vid in vehicle_ids:
                vehicle_data = self._build_vehicle_json(conn, vid)
                if vehicle_data:
                    all_vehicles.append(vehicle_data)
                    total_records += sum(
                        len(comp.get("conditions", {}))
                        for comp in vehicle_data.get("components", {}).values()
                    )

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({
                    "vehicles": all_vehicles,
                    "metadata": {
                        "total_vehicles": len(all_vehicles),
                        "total_records": total_records
                    }
                }, f, ensure_ascii=False, indent=2)

            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=total_records
            )

        except (OSError, ValueError, TypeError) as e:
            errors.append(str(e))
            return ExportResult(success=False, errors=errors)

    def _build_vehicle_json(self, conn: sqlite3.Connection, vehicle_id: str) -> dict[str, Any] | None:
        """Build the JSON structure for a single vehicle."""
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        row = cursor.fetchone()

        if not row:
            return None

        columns = [desc[0] for desc in cursor.description]
        vehicle_data = dict(zip(columns, row))

        vehicle_info = {
            k: v for k, v in vehicle_data.items()
            if k != "vehicle_id" and v is not None
        }

        result = {
            "vehicle": {
                "vehicle_id": vehicle_id,
                "vehicle_info": vehicle_info
            },
            "components": {}
        }

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='components'")
        has_components_table = cursor.fetchone() is not None

        if has_components_table:
            cursor.execute(f"""
                SELECT c.channel_code, c.component_name, c.unit
                FROM components c
                JOIN {self.table_name} r ON c.channel_code = r.component_code
                WHERE r.vehicle_id = ?
                GROUP BY c.channel_code
            """, (vehicle_id,))
        else:
            cursor.execute(f"""
                SELECT component_code, component_code as component_name, '' as unit
                FROM {self.table_name}
                WHERE vehicle_id = ?
                GROUP BY component_code
            """, (vehicle_id,))

        components = cursor.fetchall()

        for comp_row in components:
            comp_code, comp_name, unit = comp_row

            result["components"][comp_code] = {
                "component_name": comp_name or comp_code,
                "unit": unit or "",
                "conditions": {}
            }

            if self.data_type == 'ripple':
                cursor.execute("""
                    SELECT condition_id, vpp_value, peak_frequency_khz,
                           peak_amplitude, frequency_rms, image_path
                    FROM ripple_results
                    WHERE vehicle_id = ? AND component_code = ?
                """, (vehicle_id, comp_code))

                for r_row in cursor.fetchall():
                    cond_id = r_row[0]
                    result["components"][comp_code]["conditions"][cond_id] = {
                        "time_domain": {
                            "vpp": r_row[1]
                        },
                        "frequency_domain": {
                            "peak_frequency_khz": r_row[2],
                            "peak_amplitude": r_row[3],
                            "rms": r_row[4]
                        },
                        "image_path": r_row[5] or ""
                    }

                # Optionally merge slope data if present (backward compat for single-db)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slope_results'")
                has_slope = cursor.fetchone() is not None

                if has_slope:
                    cursor.execute("""
                        SELECT condition_id, slope_max, slope_min,
                               slope_max_abs, slope_unit, image_path
                        FROM slope_results
                        WHERE vehicle_id = ? AND component_code = ?
                    """, (vehicle_id, comp_code))

                    for s_row in cursor.fetchall():
                        cond_id = s_row[0]
                        if cond_id in result["components"][comp_code]["conditions"]:
                            result["components"][comp_code]["conditions"][cond_id]["slope"] = {
                                "slope_max": s_row[1],
                                "slope_min": s_row[2],
                                "slope_max_abs": s_row[3],
                                "slope_unit": s_row[4] or "V/s"
                            }
                            if s_row[5] and not result["components"][comp_code]["conditions"][cond_id].get("image_path"):
                                result["components"][comp_code]["conditions"][cond_id]["image_path"] = s_row[5]
            else:
                # slope data type
                cursor.execute("""
                    SELECT condition_id, slope_max, slope_min,
                           slope_max_abs, slope_unit, image_path
                    FROM slope_results
                    WHERE vehicle_id = ? AND component_code = ?
                """, (vehicle_id, comp_code))

                for s_row in cursor.fetchall():
                    cond_id = s_row[0]
                    result["components"][comp_code]["conditions"][cond_id] = {
                        "slope": {
                            "slope_max": s_row[1],
                            "slope_min": s_row[2],
                            "slope_max_abs": s_row[3],
                            "slope_unit": s_row[4] or "V/s"
                        },
                        "image_path": s_row[5] or ""
                    }

                # Optionally merge ripple data if present (backward compat for single-db)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ripple_results'")
                has_ripple = cursor.fetchone() is not None

                if has_ripple:
                    cursor.execute("""
                        SELECT condition_id, vpp_value, peak_frequency_khz,
                               peak_amplitude, frequency_rms, image_path
                        FROM ripple_results
                        WHERE vehicle_id = ? AND component_code = ?
                    """, (vehicle_id, comp_code))

                    for r_row in cursor.fetchall():
                        cond_id = r_row[0]
                        if cond_id in result["components"][comp_code]["conditions"]:
                            result["components"][comp_code]["conditions"][cond_id]["time_domain"] = {
                                "vpp": r_row[1]
                            }
                            result["components"][comp_code]["conditions"][cond_id]["frequency_domain"] = {
                                "peak_frequency_khz": r_row[2],
                                "peak_amplitude": r_row[3],
                                "rms": r_row[4]
                            }
                            if r_row[5] and not result["components"][comp_code]["conditions"][cond_id].get("image_path"):
                                result["components"][comp_code]["conditions"][cond_id]["image_path"] = r_row[5]

        cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE vehicle_id = ?", (vehicle_id,))
        total_conditions = cursor.fetchone()[0]

        result["metadata"] = {
            "total_components": len(result["components"]),
            "total_conditions": total_conditions
        }

        return result
