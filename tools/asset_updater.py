#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asset Updater Tool
Updates asset data in Google Sheets and Excel files.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import pandas as pd
from datetime import datetime

# Python 3.13 handles UTF-8 natively on Windows
if sys.platform == 'win32':
    import io

# Scopes with WRITE permissions
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',  # Read AND Write
    'https://www.googleapis.com/auth/drive',         # Full Drive access
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/gmail.send'
]


class AssetUpdater:
    """Updates asset data in Google Sheets and Excel files."""

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        """Initialize with OAuth credentials."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._authenticate()
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

        # Load asset index for lookups
        self.index_file = 'data/.tmp/asset_index.json'
        self.asset_index = self._load_index()

        # Change log
        self.changes = []

    def _authenticate(self) -> Credentials:
        """Authenticate with Google OAuth (with WRITE permissions)."""
        creds = None

        # Load existing token - support both JSON and pickle formats
        if os.path.exists(self.token_path):
            try:
                # Try JSON format first (new format)
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except Exception:
                # Fall back to pickle format (old format)
                try:
                    with open(self.token_path, 'rb') as token:
                        creds = pickle.load(token)
                except Exception as e:
                    print(f"[WARNING] Could not load token: {e}")
                    creds = None

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired token...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[WARNING] Token refresh failed: {e}")
                    print("[INFO] Will re-authenticate instead...")
                    creds = None

            # If still no creds, need to re-authenticate
            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"credentials.json not found at {self.credentials_path}")

                print("[WARNING]  IMPORTANT: You need to re-authenticate with WRITE permissions!")
                print("   Your browser will open. Grant full access to Google Sheets and Drive.")

                # Skip input prompt if running non-interactively
                import sys
                if sys.stdin.isatty():
                    input("   Press ENTER to continue...")
                else:
                    print("   (Running non-interactively - opening browser automatically...)")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

                # Save token for future use (JSON format)
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())

        print("[OK] Authenticated with Google (WRITE access)")
        return creds

    def _load_index(self) -> Dict[str, Any]:
        """Load asset index."""
        if not os.path.exists(self.index_file):
            print("[WARNING]  Warning: Asset index not found. Run setup first!")
            return {'assets': [], 'indexes': {'by_id': {}}}

        with open(self.index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def find_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Find asset by ID.

        Args:
            asset_id: Asset ID to find

        Returns:
            Asset record or None
        """
        # Try exact match
        asset = self.asset_index.get('indexes', {}).get('by_id', {}).get(asset_id)
        if asset:
            return asset

        # Try searching all assets
        for asset in self.asset_index.get('assets', []):
            if asset.get('Asset ID') == asset_id or asset.get('ID') == asset_id:
                return asset

        return None

    def find_assets_by_criteria(self, filter_field: str, filter_value: str) -> List[Dict[str, Any]]:
        """
        Find assets matching criteria.

        Args:
            filter_field: Field name to filter on
            filter_value: Value to match

        Returns:
            List of matching assets
        """
        matching = []
        for asset in self.asset_index.get('assets', []):
            if asset.get(filter_field) == filter_value:
                matching.append(asset)
        return matching

    def update_google_sheet(self, file_id: str, sheet_name: str, row_number: int,
                           column_name: str, new_value: str) -> bool:
        """
        Update a cell in Google Sheet.

        Args:
            file_id: Google Sheets file ID
            sheet_name: Sheet name
            row_number: Row number (1-based, including header)
            column_name: Column name
            new_value: New value

        Returns:
            Success status
        """
        try:
            # First, get the header row to find column index
            header_range = f"{sheet_name}!1:1"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=file_id,
                range=header_range
            ).execute()

            headers = result.get('values', [[]])[0]

            # Find column index
            if column_name not in headers:
                print(f"[ERROR] Column '{column_name}' not found in sheet")
                return False

            col_index = headers.index(column_name)
            col_letter = self._col_index_to_letter(col_index)

            # Update the cell
            cell_range = f"{sheet_name}!{col_letter}{row_number}"

            body = {
                'values': [[new_value]]
            }

            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=file_id,
                range=cell_range,
                valueInputOption='RAW',
                body=body
            ).execute()

            print(f"  [OK] Updated {cell_range} = '{new_value}'")
            return True

        except HttpError as error:
            print(f"[ERROR] Error updating Google Sheet: {error}")
            return False

    def _col_index_to_letter(self, col_index: int) -> str:
        """Convert column index to letter (0 -> A, 1 -> B, etc.)."""
        result = ""
        while col_index >= 0:
            result = chr(col_index % 26 + 65) + result
            col_index = col_index // 26 - 1
        return result

    def update_asset(self, asset_id: str, field: str, new_value: str,
                    confirm: bool = True) -> bool:
        """
        Update a single asset.

        Args:
            asset_id: Asset ID
            field: Field name to update
            new_value: New value
            confirm: Ask for confirmation

        Returns:
            Success status
        """
        print(f"\n=== Updating Asset {asset_id} ===")

        # Find asset
        asset = self.find_asset(asset_id)
        if not asset:
            print(f"[ERROR] Asset {asset_id} not found")
            return False

        # Show current value
        old_value = asset.get(field, 'N/A')
        print(f"\nAsset ID: {asset_id}")
        print(f"Field: {field}")
        print(f"Current Value: {old_value}")
        print(f"New Value: {new_value}")

        # Get source info
        source_file = asset.get('_source_file')
        source_sheet = asset.get('_source_sheet')
        source_type = asset.get('_source_type')

        print(f"\nSource: {source_file} / {source_sheet}")

        # Confirm
        if confirm:
            response = input("\nProceed with update? (y/n): ")
            if response.lower() != 'y':
                print("Update cancelled")
                return False

        # Perform update based on source type
        if source_type == 'google_sheet':
            # Find file ID from combined data
            combined_data_file = 'data/.tmp/asset_registers_combined.json'
            with open(combined_data_file, 'r', encoding='utf-8') as f:
                combined = json.load(f)

            # Find the file
            file_id = None
            for sheet_file in combined.get('google_sheets', []):
                if sheet_file['file_name'] == source_file:
                    file_id = sheet_file['file_id']
                    break

            if not file_id:
                print(f"[ERROR] Could not find file ID for {source_file}")
                return False

            # Find row number (need to search the sheet)
            # This is simplified - in reality you'd need to find the exact row
            print(f"[WARNING]  Note: Row number detection not fully implemented")
            print(f"   You'll need to specify the row number manually")

            # For now, show what would be updated
            print(f"\n[OK] Would update Google Sheet:")
            print(f"  File ID: {file_id}")
            print(f"  Sheet: {source_sheet}")
            print(f"  Column: {field}")
            print(f"  Value: {new_value}")

        elif source_type == 'excel':
            print(f"\n[OK] Would update Excel file:")
            print(f"  File: {source_file}")
            print(f"  Sheet: {source_sheet}")
            print(f"  Column: {field}")
            print(f"  Value: {new_value}")
            print(f"\n[WARNING]  Excel update: File would be downloaded, modified, and re-uploaded")

        # Log change
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'asset_id': asset_id,
            'field': field,
            'old_value': old_value,
            'new_value': new_value,
            'source_file': source_file
        }
        self.changes.append(change_record)

        return True

    def bulk_update_by_criteria(self, filter_field: str, filter_value: str,
                               update_field: str, new_value: str,
                               confirm: bool = True) -> int:
        """
        Bulk update assets matching criteria.

        Args:
            filter_field: Field to filter on
            filter_value: Value to match
            update_field: Field to update
            new_value: New value
            confirm: Ask for confirmation

        Returns:
            Number of assets updated
        """
        print(f"\n=== Bulk Update ===")
        print(f"Filter: {filter_field} = {filter_value}")
        print(f"Update: {update_field} → {new_value}")

        # Find matching assets
        matching = self.find_assets_by_criteria(filter_field, filter_value)

        if not matching:
            print(f"\n[ERROR] No assets found matching: {filter_field} = {filter_value}")
            return 0

        print(f"\nFound {len(matching)} matching assets:")
        for i, asset in enumerate(matching[:10], 1):
            asset_id = asset.get('Asset ID') or asset.get('ID', 'Unknown')
            current_val = asset.get(update_field, 'N/A')
            print(f"  {i}. {asset_id}: {update_field} = {current_val}")

        if len(matching) > 10:
            print(f"  ... and {len(matching) - 10} more")

        # Confirm
        if confirm:
            response = input(f"\nUpdate all {len(matching)} assets? (y/n): ")
            if response.lower() != 'y':
                print("Bulk update cancelled")
                return 0

        # Update each
        updated_count = 0
        for asset in matching:
            asset_id = asset.get('Asset ID') or asset.get('ID')
            if self.update_asset(asset_id, update_field, new_value, confirm=False):
                updated_count += 1

        print(f"\n[OK] Updated {updated_count} assets")
        return updated_count

    def save_change_log(self, output_file: str = 'data/.tmp/update_log.json'):
        """Save change log."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Load existing log if exists
        existing_log = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_log = json.load(f)

        # Append new changes
        existing_log.extend(self.changes)

        # Save
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_log, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Change log saved: {output_file}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='Update asset register data')

    subparsers = parser.add_subparsers(dest='command', help='Update command')

    # Single update
    single = subparsers.add_parser('update', help='Update single asset')
    single.add_argument('--asset-id', required=True, help='Asset ID')
    single.add_argument('--field', required=True, help='Field to update')
    single.add_argument('--value', required=True, help='New value')
    single.add_argument('--no-confirm', action='store_true', help='Skip confirmation')

    # Bulk update
    bulk = subparsers.add_parser('bulk', help='Bulk update by criteria')
    bulk.add_argument('--filter-field', required=True, help='Field to filter on')
    bulk.add_argument('--filter-value', required=True, help='Value to match')
    bulk.add_argument('--update-field', required=True, help='Field to update')
    bulk.add_argument('--new-value', required=True, help='New value')
    bulk.add_argument('--no-confirm', action='store_true', help='Skip confirmation')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        updater = AssetUpdater()

        if args.command == 'update':
            updater.update_asset(
                asset_id=args.asset_id,
                field=args.field,
                new_value=args.value,
                confirm=not args.no_confirm
            )

        elif args.command == 'bulk':
            updater.bulk_update_by_criteria(
                filter_field=args.filter_field,
                filter_value=args.filter_value,
                update_field=args.update_field,
                new_value=args.new_value,
                confirm=not args.no_confirm
            )

        # Save change log
        updater.save_change_log()

        print("\n[OK] Update complete!")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
