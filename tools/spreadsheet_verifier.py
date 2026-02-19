#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spreadsheet Verifier Tool
=========================
Provides direct access to raw asset data for side-by-side verification.
Acts as the "Data Lawyer" - proving the AI's claims with raw evidence.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class SpreadsheetVerifier:
    """
    Bridge between the Chat UI and the Raw Data.
    Allows fetching specific rows to show in the "Spreadsheet Panel".
    """

    def __init__(self, json_path: str = 'data/.tmp/asset_index.json'):
        self.json_path = json_path
        self._assets_by_id: Dict[str, Dict] = {}
        self._assets_list: List[Dict] = []
        self._loaded = False
        
        # Load lazily
        # self.load_data() 

    def load_data(self):
        """Load and index the asset data from JSON."""
        if self._loaded:
            return

        try:
            if not os.path.exists(self.json_path):
                logger.error(f"Asset index not found at {self.json_path}")
                return

            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures (list vs dict)
            if isinstance(data, list):
                self._assets_list = data
            elif isinstance(data, dict):
                self._assets_list = data.get('assets', [])
            
            # Index by multiple ID fields for robustness
            count = 0
            for asset in self._assets_list:
                # Try standard ID fields
                aid = str(asset.get('asset_id') or asset.get('fulcrum_id') or asset.get('id') or asset.get('record_id') or '').strip()
                if aid:
                    self._assets_by_id[aid.lower()] = asset
                
                # Also verify explicitly by fulcrum_id if present (as dual key)
                fid = str(asset.get('fulcrum_id') or '').strip()
                if fid:
                    self._assets_by_id[fid.lower()] = asset
                
                # Also try name/description as fallback key if unique? 
                # Better not to pollute index with non-unique names.
                count += 1
                
            self._loaded = True
            logger.info(f"SpreadsheetVerifier loaded {count} assets from {self.json_path}")

        except Exception as e:
            logger.error(f"Failed to load asset index: {e}")

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single asset record by ID (case-insensitive)."""
        if not self._loaded:
            self.load_data()
            
        return self._assets_by_id.get(str(asset_id).strip().lower())

    def search_assets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Simple text search for assets (ID, Name, Category).
        Used for the sidebar "Quick Find".
        """
        if not self._loaded:
            self.load_data()
            
        q = query.lower().strip()
        results = []
        
        for asset in self._assets_list:
            # Check ID
            # Check ID
            aid = str(asset.get('asset_id', '')).lower()
            fid = str(asset.get('fulcrum_id', '')).lower()
            if q in aid or q in fid:
                results.append(asset)
                continue
                
            # Check Name
            name = str(asset.get('asset_description', '') or asset.get('asset_name', '')).lower()
            if q in name:
                results.append(asset)
                continue

            # Check Category
            cat = str(asset.get('asset_category', '') or asset.get('category', '')).lower()
            if q in cat:
                results.append(asset)
        
        return results[:limit]

    def verify_value(self, asset_id: str, field: str, expected_value: Any) -> Dict[str, Any]:
        """
        Verify if a specific field matches an expected value.
        Returns: {match: bool, actual: Any, source: str}
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return {'error': 'Asset not found'}
            
        actual = asset.get(field)
        
        # Loose comparison (stringified)
        match = str(actual).strip().lower() == str(expected_value).strip().lower()
        
        return {
            'match': match,
            'actual_value': actual,
            'field': field,
            'source_file': asset.get('_source_file', 'Unknown'),
            'source_sheet': asset.get('_source_sheet', 'Unknown')
        }

    def generate_html_view(self, asset_id: str) -> str:
        """
        Generate a "Spreadsheet Row" HTML view for the frontend.
        Includes source metadata styling.
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return "<div class='error'>Asset not found</div>"
            
        # Determine Source
        source = f"{asset.get('_source_file', 'Unknown')} ({asset.get('_source_sheet', '')})"
        
        # Build Table
        html = f"""
        <div class="spreadsheet-row-container">
            <div class="spreadsheet-meta">
                <span class="meta-label">SOURCE:</span> 
                <span class="meta-value">{source}</span>
            </div>
            <table class="spreadsheet-table">
                <thead>
                    <tr>
                        <th>Field</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Prioritize key fields
        priority_fields = [
            'asset_id', 'fulcrum_id', 'asset_description', 'asset_category', 
            'site_no', 'room_code', 'status', 'asset_criticality',
            'date_installed', 'estimated_replacement_cost'
        ]
        
        # Add Priority Rows
        for field in priority_fields:
            if field in asset:
                html += f"""
                    <tr class="priority-row">
                        <td class="field-name">{field}</td>
                        <td class="field-value">{asset[field]}</td>
                    </tr>
                """
        
        # Add Other Rows (sorted)
        for field, value in sorted(asset.items()):
            if field in priority_fields or field.startswith('_'):
                continue
            # Skip empty? No, show empty to prove it's empty
            html += f"""
                <tr>
                    <td class="field-name">{field}</td>
                    <td class="field-value">{value}</td>
                </tr>
            """
            
        html += """
                </tbody>
            </table>
        </div>
        """
        return html

if __name__ == "__main__":
    # verification test
    verifier = SpreadsheetVerifier()
    verifier.load_data()
    print(f"Loaded {len(verifier._assets_list)} assets")
    
    # Test search
    results = verifier.search_assets("pump", limit=1)
    if results:
        print("Found pump:", results[0].get('asset_id'))
        print(verifier.generate_html_view(results[0].get('asset_id')))
