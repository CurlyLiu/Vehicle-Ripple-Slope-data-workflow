#!/usr/bin/env python3
"""Vehicle Database CLI - Main Entry Point.

车辆数据库命令行工具 - 主入口点

Usage:
    python vehicle_database.py init -o OUTPUT_DIR
    python vehicle_database.py add V0001 [V0002...] [--source PATH]
    python vehicle_database.py add --all [--source PATH]
    python vehicle_database.py update V0001 [V0002...]
    python vehicle_database.py update --all
    python vehicle_database.py remove V0001 [V0002...]
    python vehicle_database.py remove --all
    python vehicle_database.py list [--format table|json|--ids]
    python vehicle_database.py show V0001
    python vehicle_database.py stats
    python vehicle_database.py export V0001 [--excel|--json|--sqlite] [-o OUTPUT]
    python vehicle_database.py export --all [--excel|--json|--sqlite] [-o OUTPUT]
"""

import sys
from pathlib import Path

# Add project root to Python path so 'src' is recognized as a package
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run CLI from the new package (not the legacy cli.py module)
from src.cli import cli

if __name__ == "__main__":
    cli()
