#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Manager - SQLite interface for asset data
Provides structured queries for improved accuracy over JSON.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager


class DatabaseManager:
    """
    Manages SQLite database for asset register data.
    Provides ACID-compliant structured queries for high accuracy.
    """

    def __init__(self, db_path: str = "data/assets.db"):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create tables if they don't exist
        self._initialize_schema()

        print(f"[OK] Database Manager initialized: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _initialize_schema(self):
        """Create database schema if it doesn't exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            asset_name TEXT,
            asset_type TEXT,
            category TEXT,
            location TEXT,
            building TEXT,
            floor TEXT,
            room TEXT,

            -- Condition & Status
            condition TEXT,
            condition_score INTEGER,
            status TEXT,
            criticality TEXT,

            -- Dates
            install_date TEXT,
            last_maintenance_date TEXT,
            next_maintenance_date TEXT,
            replacement_due_date TEXT,

            -- Financial
            replacement_cost REAL,
            annual_maintenance_cost REAL,
            current_age INTEGER,
            expected_life INTEGER,
            remaining_life INTEGER,

            -- Compliance
            compliance_standard TEXT,
            last_inspection_date TEXT,
            next_inspection_date TEXT,
            inspection_status TEXT,

            -- Metadata
            notes TEXT,
            tags TEXT,
            data_source TEXT,
            created_date TEXT,
            updated_date TEXT
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_condition ON assets(condition);
        CREATE INDEX IF NOT EXISTS idx_asset_type ON assets(asset_type);
        CREATE INDEX IF NOT EXISTS idx_category ON assets(category);
        CREATE INDEX IF NOT EXISTS idx_location ON assets(location);
        CREATE INDEX IF NOT EXISTS idx_building ON assets(building);
        CREATE INDEX IF NOT EXISTS idx_status ON assets(status);
        CREATE INDEX IF NOT EXISTS idx_criticality ON assets(criticality);
        CREATE INDEX IF NOT EXISTS idx_remaining_life ON assets(remaining_life);

        -- Composite indexes for common multi-field queries
        CREATE INDEX IF NOT EXISTS idx_condition_type ON assets(condition, asset_type);
        CREATE INDEX IF NOT EXISTS idx_location_condition ON assets(location, condition);
        CREATE INDEX IF NOT EXISTS idx_building_type ON assets(building, asset_type);
        """

        with self.get_connection() as conn:
            conn.executescript(schema_sql)

    def query_assets(self, filters: Dict[str, Any] = None,
                     limit: int = None, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Query assets with filters.

        Args:
            filters: Dictionary of field: value pairs
                     Supports operators in field names:
                     - 'field': exact match
                     - 'field__gt': greater than
                     - 'field__lt': less than
                     - 'field__gte': greater than or equal
                     - 'field__lte': less than or equal
                     - 'field__like': pattern match (use % wildcards)
                     - 'field__in': value in list
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (results list, total count)
        """
        where_clauses = []
        params = []

        if filters:
            for key, value in filters.items():
                if '__' in key:
                    field, operator = key.rsplit('__', 1)

                    if operator == 'gt':
                        where_clauses.append(f"{field} > ?")
                        params.append(value)
                    elif operator == 'lt':
                        where_clauses.append(f"{field} < ?")
                        params.append(value)
                    elif operator == 'gte':
                        where_clauses.append(f"{field} >= ?")
                        params.append(value)
                    elif operator == 'lte':
                        where_clauses.append(f"{field} <= ?")
                        params.append(value)
                    elif operator == 'like':
                        where_clauses.append(f"{field} LIKE ?")
                        params.append(value)
                    elif operator == 'in':
                        placeholders = ','.join(['?'] * len(value))
                        where_clauses.append(f"{field} IN ({placeholders})")
                        params.extend(value)
                else:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Count total matching records
        count_sql = f"SELECT COUNT(*) as count FROM assets {where_sql}"

        # Get paginated results
        query_sql = f"SELECT * FROM assets {where_sql}"

        if limit:
            query_sql += f" LIMIT {limit}"
        if offset:
            query_sql += f" OFFSET {offset}"

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get total count
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()['count']

            # Get results
            cursor.execute(query_sql, params)
            results = [dict(row) for row in cursor.fetchall()]

        return results, total_count

    def get_asset_summary(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get summary statistics for assets matching filters.

        Returns:
            Dictionary with aggregated statistics
        """
        where_clauses = []
        params = []

        if filters:
            for key, value in filters.items():
                if '__' not in key:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        summary_sql = f"""
        SELECT
            COUNT(*) as total_assets,
            COUNT(DISTINCT asset_type) as asset_types,
            COUNT(DISTINCT location) as locations,
            COUNT(DISTINCT building) as buildings,
            AVG(condition_score) as avg_condition_score,
            SUM(replacement_cost) as total_replacement_cost,
            SUM(annual_maintenance_cost) as total_annual_maintenance,
            AVG(current_age) as avg_age,
            AVG(remaining_life) as avg_remaining_life,

            -- Condition breakdown
            SUM(CASE WHEN condition = 'Very Good' THEN 1 ELSE 0 END) as very_good_count,
            SUM(CASE WHEN condition = 'Good' THEN 1 ELSE 0 END) as good_count,
            SUM(CASE WHEN condition = 'Fair' THEN 1 ELSE 0 END) as fair_count,
            SUM(CASE WHEN condition = 'Poor' THEN 1 ELSE 0 END) as poor_count,
            SUM(CASE WHEN condition = 'Very Poor' THEN 1 ELSE 0 END) as very_poor_count,

            -- Criticality breakdown
            SUM(CASE WHEN criticality = 'Critical' THEN 1 ELSE 0 END) as critical_count,
            SUM(CASE WHEN criticality = 'High' THEN 1 ELSE 0 END) as high_criticality_count,
            SUM(CASE WHEN criticality = 'Medium' THEN 1 ELSE 0 END) as medium_criticality_count,
            SUM(CASE WHEN criticality = 'Low' THEN 1 ELSE 0 END) as low_criticality_count

        FROM assets {where_sql}
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(summary_sql, params)
            result = dict(cursor.fetchone())

        # Convert None values to 0
        for key in result:
            if result[key] is None:
                result[key] = 0

        return result

    def get_condition_breakdown(self, filters: Dict[str, Any] = None) -> Dict[str, int]:
        """Get count of assets by condition."""
        where_clauses = []
        params = []

        if filters:
            for key, value in filters.items():
                if '__' not in key:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
        SELECT condition, COUNT(*) as count
        FROM assets {where_sql}
        GROUP BY condition
        ORDER BY
            CASE condition
                WHEN 'Very Good' THEN 1
                WHEN 'Good' THEN 2
                WHEN 'Fair' THEN 3
                WHEN 'Poor' THEN 4
                WHEN 'Very Poor' THEN 5
                ELSE 6
            END
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = {row['condition']: row['count'] for row in cursor.fetchall()}

        return results

    def get_asset_types(self, filters: Dict[str, Any] = None) -> List[Tuple[str, int]]:
        """Get list of asset types with counts."""
        where_clauses = []
        params = []

        if filters:
            for key, value in filters.items():
                if '__' not in key:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
        SELECT asset_type, COUNT(*) as count
        FROM assets {where_sql}
        GROUP BY asset_type
        ORDER BY count DESC
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = [(row['asset_type'], row['count']) for row in cursor.fetchall()]

        return results

    def insert_asset(self, asset_data: Dict[str, Any]):
        """Insert a single asset."""
        columns = ', '.join(asset_data.keys())
        placeholders = ', '.join(['?'] * len(asset_data))
        sql = f"INSERT OR REPLACE INTO assets ({columns}) VALUES ({placeholders})"

        with self.get_connection() as conn:
            conn.execute(sql, list(asset_data.values()))

    def insert_assets_batch(self, assets: List[Dict[str, Any]], batch_size: int = 1000):
        """Insert multiple assets efficiently."""
        if not assets:
            return

        # Get all column names from first asset
        columns = list(assets[0].keys())
        columns_sql = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        sql = f"INSERT OR REPLACE INTO assets ({columns_sql}) VALUES ({placeholders})"

        total_inserted = 0

        with self.get_connection() as conn:
            for i in range(0, len(assets), batch_size):
                batch = assets[i:i + batch_size]
                values = [tuple(asset.get(col) for col in columns) for asset in batch]
                conn.executemany(sql, values)
                total_inserted += len(batch)

                if total_inserted % 10000 == 0:
                    print(f"  Inserted {total_inserted:,} / {len(assets):,} assets...")

        print(f"[OK] Inserted {total_inserted:,} assets total")

    def count_all_assets(self) -> int:
        """Get total count of all assets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM assets")
            return cursor.fetchone()['count']


# Test function
if __name__ == '__main__':
    print("Testing Database Manager...")

    # Create test database
    db = DatabaseManager("data/test_assets.db")

    # Insert test data
    test_assets = [
        {
            'asset_id': 'TEST-001',
            'asset_name': 'Chiller CH-01',
            'asset_type': 'Chiller',
            'category': 'HVAC',
            'location': 'Sydney CBD',
            'building': 'Building A',
            'condition': 'Poor',
            'condition_score': 2,
            'status': 'Active',
            'criticality': 'Critical',
            'replacement_cost': 250000.0,
            'current_age': 18,
            'expected_life': 20,
            'remaining_life': 2
        },
        {
            'asset_id': 'TEST-002',
            'asset_name': 'Fire Panel FP-02',
            'asset_type': 'Fire Panel',
            'category': 'Fire',
            'location': 'Sydney CBD',
            'building': 'Building B',
            'condition': 'Good',
            'condition_score': 4,
            'status': 'Active',
            'criticality': 'Critical',
            'replacement_cost': 45000.0,
            'current_age': 5,
            'expected_life': 15,
            'remaining_life': 10
        }
    ]

    print("\nInserting test assets...")
    db.insert_assets_batch(test_assets)

    print("\nQuerying poor condition assets...")
    results, count = db.query_assets({'condition': 'Poor'})
    print(f"Found {count} poor condition assets")
    for asset in results:
        print(f"  - {asset['asset_name']}: {asset['asset_type']}")

    print("\nGetting summary statistics...")
    summary = db.get_asset_summary()
    print(f"Total assets: {summary['total_assets']}")
    print(f"Average condition score: {summary['avg_condition_score']:.2f}")
    print(f"Total replacement cost: ${summary['total_replacement_cost']:,.0f}")

    print("\nCondition breakdown:")
    condition_counts = db.get_condition_breakdown()
    for condition, count in condition_counts.items():
        print(f"  {condition}: {count}")

    print("\nTest complete!")
