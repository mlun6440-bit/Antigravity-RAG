#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asset Data Indexer Tool
Processes and indexes asset register data for efficient querying.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from collections import defaultdict
import pandas as pd

# Python 3.13 handles UTF-8 natively on Windows
if sys.platform == 'win32':
    import io


class AssetDataIndexer:
    """Indexes and structures asset register data."""

    def __init__(self):
        """Initialize indexer."""
        pass

    def load_combined_data(self, data_file: str) -> Dict[str, Any]:
        """
        Load combined asset register data.

        Args:
            data_file: Path to combined JSON file

        Returns:
            Combined data dictionary
        """
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def extract_all_assets(self, combined_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all asset records from all files.

        Args:
            combined_data: Combined asset register data

        Returns:
            List of all asset records
        """
        print("\n=== Extracting Asset Records ===\n")

        all_assets = []

        # Process Google Sheets
        for sheet_file in combined_data.get('google_sheets', []):
            file_name = sheet_file['file_name']
            print(f"Processing: {file_name}")

            for sheet_name, records in sheet_file['sheets'].items():
                for record in records:
                    # Add source metadata
                    asset = record.copy()
                    asset['_source_file'] = file_name
                    asset['_source_sheet'] = sheet_name
                    asset['_source_type'] = 'google_sheet'
                    all_assets.append(asset)

                print(f"  [OK] Sheet '{sheet_name}': {len(records)} records")

        # Process Excel files
        for excel_file in combined_data.get('excel_files', []):
            file_name = excel_file['file_name']
            print(f"Processing: {file_name}")

            for sheet_name, records in excel_file['sheets'].items():
                for record in records:
                    # Add source metadata
                    asset = record.copy()
                    asset['_source_file'] = file_name
                    asset['_source_sheet'] = sheet_name
                    asset['_source_type'] = 'excel'
                    all_assets.append(asset)

                print(f"  [OK] Sheet '{sheet_name}': {len(records)} records")

        print(f"\n[OK] Total assets extracted: {len(all_assets)}")
        return all_assets

    def analyze_schema(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze asset data schema.

        Args:
            assets: List of asset records

        Returns:
            Schema analysis
        """
        print("\n=== Analyzing Schema ===\n")

        # Collect all field names
        all_fields = set()
        field_counts = defaultdict(int)
        field_types = defaultdict(set)
        field_samples = defaultdict(list)

        for asset in assets:
            for field, value in asset.items():
                if not field.startswith('_'):  # Skip metadata fields
                    all_fields.add(field)
                    field_counts[field] += 1

                    # Track value types
                    if value:
                        field_types[field].add(type(value).__name__)
                        # Store sample values (up to 5)
                        if len(field_samples[field]) < 5:
                            field_samples[field].append(str(value)[:100])

        # Create schema summary
        schema = {
            'total_fields': len(all_fields),
            'total_records': len(assets),
            'fields': {}
        }

        for field in sorted(all_fields):
            schema['fields'][field] = {
                'count': field_counts[field],
                'coverage': round(field_counts[field] / len(assets) * 100, 2),
                'types': list(field_types[field]),
                'samples': field_samples[field]
            }

        # Print summary
        print(f"Total fields found: {schema['total_fields']}")
        print(f"Total records: {schema['total_records']}")
        print("\nField Coverage:")
        for field, info in sorted(schema['fields'].items(), key=lambda x: x[1]['coverage'], reverse=True)[:10]:
            print(f"  {field}: {info['coverage']}% ({info['count']} records)")

        return schema

    def create_indexes(self, assets: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create searchable indexes.

        Args:
            assets: List of asset records
            schema: Schema analysis

        Returns:
            Indexes dictionary
        """
        print("\n=== Creating Indexes ===\n")

        indexes = {
            'by_id': {},
            'by_field': defaultdict(lambda: defaultdict(list)),
            'statistics': {}
        }

        # Index by ID (if ID field exists)
        id_fields = [f for f in schema['fields'].keys() if 'id' in f.lower() or 'asset' in f.lower()]
        if id_fields:
            primary_id = id_fields[0]
            print(f"Using primary ID field: {primary_id}")

            for idx, asset in enumerate(assets):
                asset_id = asset.get(primary_id, f"unknown_{idx}")
                indexes['by_id'][str(asset_id)] = asset

        # Index by common fields
        important_fields = [
            'category', 'type', 'status', 'location', 'department',
            'condition', 'risk', 'owner', 'manufacturer'
        ]

        for field in schema['fields'].keys():
            # Index fields that look like categories
            if any(keyword in field.lower() for keyword in important_fields):
                print(f"Indexing field: {field}")

                for asset in assets:
                    value = asset.get(field)
                    if value:
                        indexes['by_field'][field][str(value)].append(asset)

        # Calculate statistics
        for field, values in indexes['by_field'].items():
            indexes['statistics'][field] = {
                'unique_values': len(values),
                'value_counts': {k: len(v) for k, v in sorted(values.items(), key=lambda x: len(x[1]), reverse=True)[:10]}
            }

        print(f"\n[OK] Created indexes for {len(indexes['by_field'])} fields")
        return indexes

    def create_summary_statistics(self, assets: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics.

        Args:
            assets: List of asset records
            schema: Schema analysis

        Returns:
            Statistics dictionary
        """
        print("\n=== Generating Statistics ===\n")

        stats = {
            'total_assets': len(assets),
            'total_fields': schema['total_fields'],
            'source_distribution': defaultdict(int),
            'field_analysis': {}
        }

        # Source distribution
        for asset in assets:
            source = asset.get('_source_file', 'unknown')
            stats['source_distribution'][source] += 1

        print("Assets by source:")
        for source, count in sorted(stats['source_distribution'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count} assets")

        return stats

    def process_and_index(self, input_file: str, output_file: str = 'data/.tmp/asset_index.json') -> Dict[str, Any]:
        """
        Process combined asset data and create searchable index.

        Args:
            input_file: Path to combined asset data
            output_file: Path to save index

        Returns:
            Complete index with metadata
        """
        print("\n=== Asset Data Indexing ===\n")

        # Load data
        print(f"Loading data from: {input_file}")
        combined_data = self.load_combined_data(input_file)

        # Extract all assets
        all_assets = self.extract_all_assets(combined_data)

        if not all_assets:
            print("[ERROR] No assets found!")
            return {}

        # Analyze schema
        schema = self.analyze_schema(all_assets)

        # Create indexes
        indexes = self.create_indexes(all_assets, schema)

        # Generate statistics
        statistics = self.create_summary_statistics(all_assets, schema)

        # Combine everything
        result = {
            'assets': all_assets,
            'schema': schema,
            'indexes': {
                'by_id': indexes['by_id'],
                'by_field': {k: {fv: len(assets) for fv, assets in v.items()}
                           for k, v in indexes['by_field'].items()},
                'statistics': indexes['statistics']
            },
            'statistics': statistics
        }

        # Save index
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Index saved to: {output_file}")
        print(f"  - Total assets: {len(all_assets)}")
        print(f"  - Total fields: {schema['total_fields']}")
        print(f"  - Indexed fields: {len(indexes['by_field'])}")

        return result


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='Index asset register data')
    parser.add_argument('--input', default='data/.tmp/asset_registers_combined.json',
                       help='Input combined data file')
    parser.add_argument('--output', default='data/.tmp/asset_index.json',
                       help='Output index file')

    args = parser.parse_args()

    try:
        indexer = AssetDataIndexer()
        index = indexer.process_and_index(
            input_file=args.input,
            output_file=args.output
        )

        print("\n[OK] Success! Asset data indexed.")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
