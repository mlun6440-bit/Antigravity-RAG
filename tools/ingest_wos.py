#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WO Ingest Script - Load WOs.xlsx into the work_orders SQLite table.

Reads ~1M Work Order rows from the WOs.xlsx file, maps columns to the
work_orders schema, and batch-inserts them into assets.db.

Run:
    python tools/ingest_wos.py
    python tools/ingest_wos.py --db data/assets.db
    python tools/ingest_wos.py --wo-file "path/to/WOs.xlsx"
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from collections import defaultdict

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Default WO file location (parent of project dir)
DEFAULT_WO_FILE = str(Path(__file__).parent.parent.parent / "WOs.xlsx")
DEFAULT_DB = "data/assets.db"

# Column name mapping: WOs.xlsx header → DB field
COLUMN_MAP = {
    "Property[Property Id]": "site_id",
    "Property[Property Name]": "site_name",
    "Combined Work Orders[Request Description]": "description",
    "Combined Work Orders[Service Type]": "service_type",
    "Combined Work Orders[Table_Source]": "wo_type",
    "Combined Work Orders[Request Status Group]": "status",
    "Property[Facilities Manager]": "manager",
    "Property[Tenure]": "tenure",
    "[SumProperty_NLA_sqm]": "nla_sqm",
}


def _safe_float(val):
    """Convert to float safely, return 0.0 on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _safe_str(val):
    """Convert to string, strip whitespace, return '' on None."""
    if val is None:
        return ""
    return str(val).strip()


def ingest_wo_file(wo_file: str, db_path: str, batch_size: int = 10000) -> dict:
    """
    Read WOs.xlsx and insert all rows into work_orders table.

    Returns summary dict: {rows_read, rows_inserted, rows_skipped,
                           rm_count, pm_count, open_count, completed_count}
    """
    try:
        import openpyxl
    except ImportError:
        logger.error("openpyxl not installed. Run: pip install openpyxl")
        sys.exit(1)

    from tools.database_manager import DatabaseManager

    wo_path = Path(wo_file)
    if not wo_path.exists():
        logger.error(f"WO file not found: {wo_path}")
        logger.info(f"Expected location: {wo_path.resolve()}")
        sys.exit(1)

    logger.info(f"Loading WOs from: {wo_path}")
    logger.info(f"Target database: {db_path}")

    # Open workbook in read-only mode for memory efficiency
    wb = openpyxl.load_workbook(wo_path, read_only=True, data_only=True)
    ws = wb.active
    logger.info(f"Sheet: {ws.title}")

    # Read header row to build column index map
    rows_iter = ws.iter_rows(values_only=True)
    header = next(rows_iter)
    col_index = {}
    for i, cell in enumerate(header):
        col_name = _safe_str(cell)
        if col_name in COLUMN_MAP:
            col_index[COLUMN_MAP[col_name]] = i

    logger.info(f"Mapped columns: {list(col_index.keys())}")
    missing = [v for k, v in COLUMN_MAP.items() if v not in col_index]
    if missing:
        logger.warning(f"Missing expected columns (will default to ''): {missing}")

    # Ensure table exists
    db = DatabaseManager(db_path)
    db.create_work_orders_table()

    # Track stats
    stats = defaultdict(int)
    batch = []

    def _flush(batch):
        if batch:
            db.insert_work_orders_batch(batch, batch_size=len(batch))
            stats["rows_inserted"] += len(batch)

    for raw_row in rows_iter:
        stats["rows_read"] += 1

        try:
            def get(field):
                idx = col_index.get(field)
                return raw_row[idx] if idx is not None and idx < len(raw_row) else None

            wo = {
                "site_id": _safe_str(get("site_id")),
                "site_name": _safe_str(get("site_name")),
                "description": _safe_str(get("description")),
                "service_type": _safe_str(get("service_type")),
                "wo_type": _safe_str(get("wo_type")),
                "status": _safe_str(get("status")),
                "manager": _safe_str(get("manager")),
                "tenure": _safe_str(get("tenure")),
                "nla_sqm": _safe_float(get("nla_sqm")),
            }

            # Track RM/PM and open/completed counts
            wt = wo["wo_type"].upper()
            if wt == "RM":
                stats["rm_count"] += 1
            elif wt == "PM":
                stats["pm_count"] += 1

            st = wo["status"].lower()
            if "complet" in st:
                stats["completed_count"] += 1
            else:
                stats["open_count"] += 1

            batch.append(wo)

            if len(batch) >= batch_size:
                _flush(batch)
                batch = []
                logger.info(
                    f"  Progress: {stats['rows_read']:,} rows read, "
                    f"{stats['rows_inserted']:,} inserted, "
                    f"RM={stats['rm_count']:,} PM={stats['pm_count']:,}"
                )

        except Exception as e:
            stats["rows_skipped"] += 1
            if stats["rows_skipped"] <= 10:
                logger.warning(f"Skipped row {stats['rows_read']}: {e}")

    # Flush remainder
    _flush(batch)
    wb.close()

    logger.info("=" * 60)
    logger.info("WO Ingest Complete")
    logger.info(f"  Rows read:      {stats['rows_read']:,}")
    logger.info(f"  Rows inserted:  {stats['rows_inserted']:,}")
    logger.info(f"  Rows skipped:   {stats['rows_skipped']:,}")
    logger.info(f"  RM (Reactive):  {stats['rm_count']:,}")
    logger.info(f"  PM (Planned):   {stats['pm_count']:,}")
    logger.info(f"  Open WOs:       {stats['open_count']:,}")
    logger.info(f"  Completed WOs:  {stats['completed_count']:,}")
    logger.info("=" * 60)

    return dict(stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest WOs.xlsx into assets.db work_orders table")
    parser.add_argument("--wo-file", default=DEFAULT_WO_FILE, help="Path to WOs.xlsx")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to assets.db")
    parser.add_argument("--batch-size", type=int, default=10000, help="Batch size for inserts")
    args = parser.parse_args()

    result = ingest_wo_file(args.wo_file, args.db, args.batch_size)
    sys.exit(0)
