#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive Reader Tool
Reads asset register files (Google Sheets and Excel) from Google Drive.
"""

import os
import sys
import json
import argparse
import io
from typing import Dict, List, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import pickle
import pandas as pd
from dotenv import load_dotenv

# Python 3.13 handles UTF-8 natively on Windows

# Scopes required for Google Drive and Sheets access
# MINIMAL SCOPES: Only request what's actually needed (principle of least privilege)
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

class DriveReader:
    """Reads asset register data from Google Drive."""

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        """Initialize with OAuth credentials."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._authenticate()
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def _authenticate(self) -> Credentials:
        """Authenticate with Google OAuth."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired token...")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"credentials.json not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console."
                    )
                # CRITICAL FIX: Do not block for interactive auth in headless mode
                print("[INFO] Starting interactive authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        print("[OK] Authenticated with Google")
        return creds

    def list_folder_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        List all files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of file metadata dictionaries
        """
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()

            files = results.get('files', [])
            print(f"[OK] Found {len(files)} files in folder")
            return files

        except HttpError as error:
            print(f"[ERROR] Error listing folder files: {error}")
            raise

    def read_google_sheet(self, file_id: str, file_name: str) -> Dict[str, Any]:
        """
        Read data from a Google Sheets file.

        Args:
            file_id: Google Sheets file ID
            file_name: Name of the file (for logging)

        Returns:
            Dictionary with sheet data
        """
        try:
            print(f"Reading Google Sheet: {file_name}...")

            # Get spreadsheet metadata
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=file_id
            ).execute()

            sheets_data = {}
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]

            # Read each sheet
            for sheet_name in sheet_names:
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=file_id,
                    range=sheet_name
                ).execute()

                values = result.get('values', [])
                if values:
                    # SMART HEADER DETECTION
                    # Scan first 50 rows for a header-like row
                    header_index = 0
                    max_score = 0
                    
                    # Expanded keywords
                    keywords = {
                        'asset id', 'id', 'record id', 'asset name', 'description', 
                        'category', 'tag', 'serial number', 'functional location',
                        'equipment id', 'tag number', 'asset', 'model', 'manufacturer',
                        'location', 'site', 'status', 'condition', 'fulcrum id'
                    }
                    
                    print(f"  Scanning '{sheet_name}' for headers...")
                    
                    for i, row in enumerate(values[:50]):
                        # Normalize cell values for matching
                        row_text = set(str(cell).lower().strip().replace('_', ' ') for cell in row if cell)
                        # Check intersection
                        matches = row_text.intersection(keywords)
                        score = len(matches)
                        
                        if score > max_score:
                            max_score = score
                            header_index = i
                            # If we find a very strong match (>3 keywords), stop searching
                            if score >= 3:
                                break
                    
                    if max_score > 0:
                        print(f"    -> Found header at row {header_index+1} (Score: {max_score})")
                        print(f"       Headers: {values[header_index]}")
                    else:
                        print(f"    [WARN] No clear header found. Defaulting to row 1.")
                        print(f"    Row 1 Raw: {values[0] if values else 'Empty'}")
                        # Fallback: check if row 1 is metadata and skip it? 
                        # For now, just warn.
                    
                    # Slicing based on detected header
                    headers = values[header_index] if values else []
                    data_rows = values[header_index+1:]

                    # Handle column mismatch by padding shorter rows
                    max_cols = max(len(headers), max((len(row) for row in data_rows), default=0))

                    # Pad headers if needed
                    if len(headers) < max_cols:
                        headers.extend([f'Column_{i}' for i in range(len(headers), max_cols)])

                    # Remove newlines/spaces from headers
                    headers = [str(h).strip().replace('\n', ' ') for h in headers]

                    # Pad data rows if needed
                    padded_rows = []
                    for row in data_rows:
                        if len(row) < len(headers):
                            padded_row = row + [''] * (len(headers) - len(row))
                        else:
                            padded_row = row[:len(headers)]
                        padded_rows.append(padded_row)

                    df = pd.DataFrame(padded_rows, columns=headers)
                    sheets_data[sheet_name] = df.to_dict('records')
                    print(f"  [OK] Sheet '{sheet_name}': {len(df)} rows")

            return {
                'file_id': file_id,
                'file_name': file_name,
                'type': 'google_sheet',
                'sheets': sheets_data
            }

        except HttpError as error:
            print(f"[ERROR] Error reading Google Sheet {file_name}: {error}")
            raise

    def read_excel_file(self, file_id: str, file_name: str, output_dir: str = 'data/.tmp') -> Dict[str, Any]:
        """
        Download and read an Excel file from Google Drive.

        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            output_dir: Directory to save temporary file

        Returns:
            Dictionary with Excel data
        """
        try:
            print(f"Downloading Excel file: {file_name}...")

            # Download file
            request = self.drive_service.files().get_media(fileId=file_id)
            file_path = os.path.join(output_dir, file_name)

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"  Download {int(status.progress() * 100)}%")

            fh.close()
            print(f"  [OK] Downloaded to {file_path}")

            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheets_data[sheet_name] = df.to_dict('records')
                print(f"  [OK] Sheet '{sheet_name}': {len(df)} rows")

            return {
                'file_id': file_id,
                'file_name': file_name,
                'type': 'excel',
                'sheets': sheets_data,
                'local_path': file_path
            }

        except HttpError as error:
            print(f"[ERROR] Error downloading Excel file {file_name}: {error}")
            raise

    def download_pdf(self, file_id: str, file_name: str, output_dir: str = 'data/.tmp') -> str:
        """
        Download a PDF file from Google Drive.

        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            output_dir: Directory to save file

        Returns:
            Path to downloaded file
        """
        try:
            print(f"Downloading PDF: {file_name}...")

            request = self.drive_service.files().get_media(fileId=file_id)
            file_path = os.path.join(output_dir, file_name)

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"  Download {int(status.progress() * 100)}%")

            fh.close()
            print(f"  [OK] Downloaded to {file_path}")
            return file_path

        except HttpError as error:
            print(f"[ERROR] Error downloading PDF {file_name}: {error}")
            raise

    def fetch_all_asset_registers(self, folder_id: str, output_file: str = 'data/.tmp/asset_registers_combined.json') -> Dict[str, Any]:
        """
        Fetch all asset register files from Google Drive folder.

        Args:
            folder_id: Google Drive folder ID
            output_file: Path to save combined data

        Returns:
            Combined asset register data
        """
        print("\n=== Fetching Asset Registers from Google Drive ===\n")

        # List all files in folder
        files = self.list_folder_files(folder_id)

        asset_data = {
            'google_sheets': [],
            'excel_files': [],
            'pdf_files': [],
            'metadata': {
                'total_files': len(files),
                'folder_id': folder_id
            }
        }

        # Process each file
        for file_info in files:
            file_id = file_info['id']
            file_name = file_info['name']
            mime_type = file_info['mimeType']

            try:
                # Google Sheets
                if mime_type == 'application/vnd.google-apps.spreadsheet':
                    sheet_data = self.read_google_sheet(file_id, file_name)
                    asset_data['google_sheets'].append(sheet_data)

                # Excel files
                elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                  'application/vnd.ms-excel']:
                    excel_data = self.read_excel_file(file_id, file_name)
                    asset_data['excel_files'].append(excel_data)

                # PDF files
                elif mime_type == 'application/pdf':
                    pdf_path = self.download_pdf(file_id, file_name)
                    asset_data['pdf_files'].append({
                        'file_id': file_id,
                        'file_name': file_name,
                        'local_path': pdf_path
                    })

                else:
                    print(f"⊘ Skipping unsupported file type: {file_name} ({mime_type})")

            except Exception as e:
                print(f"[ERROR] Error processing {file_name}: {e}")
                continue

        # Save combined data
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asset_data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Combined data saved to: {output_file}")
        print(f"  - Google Sheets: {len(asset_data['google_sheets'])}")
        print(f"  - Excel files: {len(asset_data['excel_files'])}")
        print(f"  - PDF files: {len(asset_data['pdf_files'])}")

        return asset_data


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='Read asset registers from Google Drive')
    parser.add_argument('--folder-id', required=True, help='Google Drive folder ID')
    parser.add_argument('--output', default='data/.tmp/asset_registers_combined.json',
                       help='Output file path')
    parser.add_argument('--credentials', default='credentials.json',
                       help='Path to credentials.json')
    parser.add_argument('--token', default='token.pickle',
                       help='Path to token.pickle')

    args = parser.parse_args()

    try:
        reader = DriveReader(
            credentials_path=args.credentials,
            token_path=args.token
        )

        data = reader.fetch_all_asset_registers(
            folder_id=args.folder_id,
            output_file=args.output
        )

        print("\n[OK] Success! Asset register data fetched.")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
