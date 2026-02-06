#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migrate JSON Asset Index to SQLite Database
Converts data/.tmp/asset_index.json to data/assets.db for improved query accuracy.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from database_manager import DatabaseManager


class AssetMigrator:
    """
    Migrates asset data from JSON to SQLite.
    Maps JSON fields to normalized database schema.
    """

    def __init__(self, json_path: str = 'data/.tmp/asset_index.json',
                 db_path: str = 'data/assets.db'):
        """Initialize migrator."""
        self.json_path = Path(json_path)
        self.db_path = db_path

        if not self.json_path.exists():
            raise FileNotFoundError(f"Asset index not found: {self.json_path}")

        self.db = DatabaseManager(db_path)

        print(f"[OK] Migrator initialized")
        print(f"  Source: {self.json_path}")
        print(f"  Target: {self.db_path}")

    def normalize_asset_data(self, raw_asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize JSON asset data to database schema.
        Maps various field names to consistent schema.
        """

        # Extract UUID - try different field names
        asset_id = (
            raw_asset.get('') or  # Empty string key for UUID
            raw_asset.get('asset_id') or
            raw_asset.get('id') or
            raw_asset.get('record_id') or
            'unknown'
        )

        # Asset identification
        asset_name = (
            raw_asset.get('asset_description') or
            raw_asset.get('asset_description_2') or
            ''
        )

        asset_type = raw_asset.get('asset_description', '')
        category = raw_asset.get('asset_category', '')

        # Location fields
        location = raw_asset.get('alpha_name', '')
        building = raw_asset.get('site_no', '')
        floor = raw_asset.get('level', '')
        room = raw_asset.get('room_code', '') or raw_asset.get('level_other', '')

        # Condition mapping - status field contains condition like "R4 Good"
        status_raw = raw_asset.get('status', '')
        condition = self._extract_condition(status_raw)
        condition_score = self._condition_to_score(condition)

        # Status
        asset_status = raw_asset.get('asset_status', '')

        # Criticality - e.g. "4 High"
        criticality_raw = raw_asset.get('asset_criticality', '')
        criticality = self._extract_criticality(criticality_raw)

        # Dates
        install_date = raw_asset.get('date_installed') or raw_asset.get('date_in_service')
        last_maintenance_date = raw_asset.get('last_compliance_testinspection_date')
        next_maintenance_date = raw_asset.get('inspection_date_mandatory')
        replacement_due_date = raw_asset.get('client_agreed_replacement_year')

        # Financial
        try:
            replacement_cost = float(raw_asset.get('estimated_replacement_cost') or 0)
        except (ValueError, TypeError):
            replacement_cost = 0.0

        try:
            annual_maintenance_cost = float(raw_asset.get('maintenance_cost') or 0)
        except (ValueError, TypeError):
            annual_maintenance_cost = 0.0

        # Age calculations
        try:
            design_life = int(raw_asset.get('asset_design_life') or 0)
        except (ValueError, TypeError):
            design_life = 0

        # Try to calculate age if we have dates
        current_age = None
        if install_date:
            try:
                from datetime import datetime
                install_year = datetime.fromisoformat(install_date.replace('UTC', '').strip()).year
                current_age = 2026 - install_year  # Current year
            except:
                pass

        # If no age calculated, try to infer from design life and remaining life
        if current_age is None:
            try:
                remaining = raw_asset.get('remaining_useful_life_yrs')
                if remaining and design_life:
                    remaining_int = int(remaining)
                    current_age = design_life - remaining_int
            except (ValueError, TypeError):
                pass

        expected_life = design_life if design_life > 0 else None

        # Remaining life
        remaining_life = None
        try:
            remaining_life_str = raw_asset.get('remaining_useful_life_yrs')
            if remaining_life_str:
                remaining_life = int(remaining_life_str)
        except (ValueError, TypeError):
            # Calculate from replacement year if available
            if replacement_due_date:
                try:
                    remaining_life = int(replacement_due_date) - 2026
                except (ValueError, TypeError):
                    pass

        # Compliance
        compliance_standard = raw_asset.get('data_source', '')
        last_inspection_date = raw_asset.get('last_compliance_testinspection_date')
        next_inspection_date = raw_asset.get('inspection_date_mandatory')
        inspection_status = 'Compliant' if next_inspection_date else 'Unknown'

        # Metadata
        notes = raw_asset.get('condition_comments', '') or raw_asset.get('asset_notes', '')
        tags = category  # Use category as tags for now

        created_date = raw_asset.get('created_at', '')
        updated_date = raw_asset.get('updated_at', '')

        return {
            'asset_id': asset_id,
            'asset_name': asset_name,
            'asset_type': asset_type,
            'category': category,
            'location': location,
            'building': building,
            'floor': floor,
            'room': room,

            'condition': condition,
            'condition_score': condition_score,
            'status': asset_status,
            'criticality': criticality,

            'install_date': install_date,
            'last_maintenance_date': last_maintenance_date,
            'next_maintenance_date': next_maintenance_date,
            'replacement_due_date': replacement_due_date,

            'replacement_cost': replacement_cost,
            'annual_maintenance_cost': annual_maintenance_cost,
            'current_age': current_age,
            'expected_life': expected_life,
            'remaining_life': remaining_life,

            'compliance_standard': compliance_standard,
            'last_inspection_date': last_inspection_date,
            'next_inspection_date': next_inspection_date,
            'inspection_status': inspection_status,

            'notes': notes,
            'tags': tags,
            'created_date': created_date,
            'updated_date': updated_date
        }

    def _extract_condition(self, status_str: str) -> str:
        """Extract condition from status string like 'R4 Good'."""
        if not status_str:
            return 'Unknown'

        status_lower = status_str.lower()

        if 'very good' in status_lower or 'r5' in status_lower:
            return 'Very Good'
        elif 'good' in status_lower or 'r4' in status_lower:
            return 'Good'
        elif 'fair' in status_lower or 'r3' in status_lower:
            return 'Fair'
        elif 'poor' in status_lower or 'r2' in status_lower:
            return 'Poor'
        elif 'very poor' in status_lower or 'r1' in status_lower:
            return 'Very Poor'

        return 'Unknown'

    def _condition_to_score(self, condition: str) -> int:
        """Convert condition to numeric score (1-5)."""
        mapping = {
            'Very Poor': 1,
            'Poor': 2,
            'Fair': 3,
            'Good': 4,
            'Very Good': 5,
            'Unknown': 0
        }
        return mapping.get(condition, 0)

    def _extract_criticality(self, criticality_str: str) -> str:
        """Extract criticality from string like '4 High'."""
        if not criticality_str:
            return 'Unknown'

        crit_lower = criticality_str.lower()

        if 'critical' in crit_lower or '5' in crit_lower:
            return 'Critical'
        elif 'high' in crit_lower or '4' in crit_lower:
            return 'High'
        elif 'medium' in crit_lower or '3' in crit_lower:
            return 'Medium'
        elif 'low' in crit_lower or '2' in crit_lower or '1' in crit_lower:
            return 'Low'

        return 'Unknown'

    def load_json_data(self) -> list:
        """Load assets from JSON file."""
        print(f"\n[1/3] Loading JSON data from {self.json_path}...")

        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assets = data.get('assets', [])
        print(f"[OK] Loaded {len(assets):,} assets from JSON")

        return assets

    def migrate_assets(self, assets: list):
        """Migrate all assets to SQLite."""
        print(f"\n[2/3] Normalizing and migrating {len(assets):,} assets...")

        normalized_assets = []

        for i, raw_asset in enumerate(assets):
            try:
                normalized = self.normalize_asset_data(raw_asset)
                normalized_assets.append(normalized)

                if (i + 1) % 10000 == 0:
                    print(f"  Normalized {i + 1:,} / {len(assets):,} assets...")

            except Exception as e:
                print(f"[WARNING] Failed to normalize asset {i+1}: {e}")
                continue

        print(f"[OK] Normalized {len(normalized_assets):,} assets")

        # Batch insert
        print(f"\n[3/3] Inserting assets into database...")
        self.db.insert_assets_batch(normalized_assets, batch_size=1000)

    def verify_migration(self):
        """Verify migration completed successfully."""
        print(f"\n=== MIGRATION VERIFICATION ===\n")

        total_count = self.db.count_all_assets()
        print(f"Total assets in database: {total_count:,}")

        # Get summary
        summary = self.db.get_asset_summary()
        print(f"\nSummary Statistics:")
        print(f"  Asset types: {summary['asset_types']}")
        print(f"  Locations: {summary['locations']}")
        print(f"  Buildings: {summary['buildings']}")
        print(f"  Avg condition score: {summary['avg_condition_score']:.2f}")
        print(f"  Total replacement cost: ${summary['total_replacement_cost']:,.0f}")

        # Condition breakdown
        print(f"\nCondition Breakdown:")
        condition_counts = self.db.get_condition_breakdown()
        for condition, count in condition_counts.items():
            pct = (count / total_count * 100) if total_count > 0 else 0
            print(f"  {condition:15s}: {count:6,} ({pct:5.1f}%)")

        # Top asset types
        print(f"\nTop 10 Asset Types:")
        asset_types = self.db.get_asset_types()[:10]
        for asset_type, count in asset_types:
            pct = (count / total_count * 100) if total_count > 0 else 0
            print(f"  {asset_type[:40]:40s}: {count:6,} ({pct:5.1f}%)")

        print(f"\n{'='*60}")
        print(f"[OK] Migration complete and verified!")
        print(f"{'='*60}\n")

    def run(self):
        """Run the full migration process."""
        print(f"\n{'='*60}")
        print(f"=== Asset Data Migration: JSON to SQLite ===")
        print(f"{'='*60}\n")

        # Load JSON
        assets = self.load_json_data()

        # Migrate
        self.migrate_assets(assets)

        # Verify
        self.verify_migration()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate asset data from JSON to SQLite')
    parser.add_argument('--json', default='data/.tmp/asset_index.json',
                        help='Path to JSON asset index')
    parser.add_argument('--db', default='data/assets.db',
                        help='Path to SQLite database (will be created)')
    parser.add_argument('--skip-verify', action='store_true',
                        help='Skip verification step')

    args = parser.parse_args()

    try:
        migrator = AssetMigrator(json_path=args.json, db_path=args.db)
        migrator.run()

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print("\nPlease ensure the asset index JSON file exists.")
        print("You may need to run: python tools/asset_data_indexer.py first")
        exit(1)

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
