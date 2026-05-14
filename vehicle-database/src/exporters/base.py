"""Base exporter interface for vehicle data export."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import sqlite3


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    file_path: Optional[Path] = None
    records_exported: int = 0
    errors: list = field(default_factory=list)


class BaseExporter(ABC):
    """Abstract base class for vehicle data exporters."""

    @abstractmethod
    def export_vehicle(self, conn: sqlite3.Connection, vehicle_id: str, output_path: Path) -> ExportResult:
        """Export a single vehicle's data.
        
        Args:
            conn: SQLite database connection
            vehicle_id: ID of the vehicle to export
            output_path: Path where the export file should be saved
            
        Returns:
            ExportResult with success status and metadata
        """
        pass

    @abstractmethod
    def export_all(self, conn: sqlite3.Connection, output_path: Path) -> ExportResult:
        """Export all vehicles' data.
        
        Args:
            conn: SQLite database connection
            output_path: Path where the export file should be saved
            
        Returns:
            ExportResult with success status and metadata
        """
        pass
