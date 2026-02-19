#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Parser
Detects and parses natural language CRUD commands.
"""

import re
from typing import Dict, Any, Optional, Tuple


class CommandParser:
    """Parses natural language commands for CRUD operations."""

    def __init__(self):
        """Initialize parser with keyword patterns."""
        self.update_keywords = ['update', 'change', 'modify', 'set', 'fix']
        self.create_keywords = ['add', 'create', 'insert', 'new']
        self.delete_keywords = ['delete', 'remove', 'drop']

    def detect_intent(self, query: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Detect command intent.

        Args:
            query: User query

        Returns:
            Tuple of (intent, params) where intent is READ/UPDATE/CREATE/DELETE
        """
        query_lower = query.lower()

        # Check for UPDATE
        for keyword in self.update_keywords:
            if keyword in query_lower:
                params = self.parse_update(query)
                if params:
                    return 'UPDATE', params

        # Check for CREATE
        for keyword in self.create_keywords:
            if keyword in query_lower:
                params = self.parse_create(query)
                if params:
                    return 'CREATE', params

        # Check for DELETE
        for keyword in self.delete_keywords:
            if keyword in query_lower:
                params = self.parse_delete(query)
                if params:
                    return 'DELETE', params

        # Default to READ
        return 'READ', None

    def parse_update(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Parse UPDATE command.

        Patterns:
        - "update asset A-001 condition to Poor"
        - "change asset A-123 location to Building C"
        - "set A-456 status to Critical"
        - "update all Fair assets to Poor"

        Args:
            query: User query

        Returns:
            Dict with update parameters or None
        """
        query_lower = query.lower()

        # Pattern 1: update asset <ID> <field> to <value>
        pattern1 = r'(?:update|change|set|modify)\s+(?:asset\s+)?([A-Za-z0-9-]+)\s+(\w+)\s+to\s+(.+?)(?:\s|$)'
        match = re.search(pattern1, query_lower, re.IGNORECASE)

        if match:
            return {
                'type': 'single',
                'asset_id': match.group(1).upper(),
                'field': match.group(2).capitalize(),
                'value': match.group(3).strip()
            }

        # Pattern 2: update all <condition> assets to <value>
        # "update all Fair to Poor"
        pattern2 = r'(?:update|change)\s+all\s+(\w+)\s+(?:assets?\s+)?to\s+(\w+)'
        match = re.search(pattern2, query_lower, re.IGNORECASE)

        if match:
            return {
                'type': 'bulk',
                'filter_value': match.group(1).capitalize(),
                'filter_field': 'Condition',  # Assume condition
                'new_value': match.group(2).capitalize()
            }

        # Pattern 3: change all <field> = <value> to <new_value>
        pattern3 = r'(?:change|update)\s+all\s+(?:assets?\s+where\s+)?(\w+)\s*=?\s*(\w+)\s+to\s+(\w+)'
        match = re.search(pattern3, query_lower, re.IGNORECASE)

        if match:
            return {
                'type': 'bulk',
                'filter_field': match.group(1).capitalize(),
                'filter_value': match.group(2).capitalize(),
                'new_value': match.group(3).capitalize()
            }

        return None

    def parse_create(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Parse CREATE command.

        Patterns:
        - "add new asset: Pump 5, Building C, Good condition"
        - "create asset with name Pump 5, location Building C"

        Args:
            query: User query

        Returns:
            Dict with create parameters or None
        """
        query_lower = query.lower()

        # Pattern: add/create [new] asset [with] <details>
        pattern = r'(?:add|create)\s+(?:new\s+)?asset[:\s]+(.+)'
        match = re.search(pattern, query_lower, re.IGNORECASE)

        if match:
            details = match.group(1).strip()

            # Try to parse comma-separated values
            parts = [p.strip() for p in details.split(',')]

            # Try to extract key-value pairs
            asset_data = {}
            for part in parts:
                # Look for "field: value" or "field = value"
                kv_match = re.match(r'(\w+)\s*[=:]\s*(.+)', part)
                if kv_match:
                    asset_data[kv_match.group(1).capitalize()] = kv_match.group(2).strip()
                else:
                    # If no key, assume it's a name
                    if 'Name' not in asset_data:
                        asset_data['Name'] = part

            return {
                'type': 'create',
                'asset_data': asset_data
            }

        return None

    def parse_delete(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Parse DELETE command.

        Patterns:
        - "delete asset A-001"
        - "remove asset A-123"
        - "delete all decommissioned assets"

        Args:
            query: User query

        Returns:
            Dict with delete parameters or None
        """
        query_lower = query.lower()

        # Pattern 1: delete asset <ID>
        pattern1 = r'(?:delete|remove)\s+(?:asset\s+)?([A-Za-z0-9-]+)'
        match = re.search(pattern1, query_lower, re.IGNORECASE)

        if match and not 'all' in query_lower:
            return {
                'type': 'single',
                'asset_id': match.group(1).upper()
            }

        # Pattern 2: delete all <condition> assets
        pattern2 = r'(?:delete|remove)\s+all\s+(\w+)\s+assets?'
        match = re.search(pattern2, query_lower, re.IGNORECASE)

        if match:
            return {
                'type': 'bulk',
                'filter_field': 'Status',  # Assume status
                'filter_value': match.group(1).capitalize()
            }

        return None

    def needs_confirmation(self, intent: str, params: Dict[str, Any]) -> bool:
        """
        Check if command needs user confirmation.

        Args:
            intent: Command intent
            params: Command parameters

        Returns:
            True if confirmation needed
        """
        # All DELETE commands need confirmation
        if intent == 'DELETE':
            return True

        # Bulk UPDATE needs confirmation
        if intent == 'UPDATE' and params and params.get('type') == 'bulk':
            return True

        # Single updates don't need confirmation
        return False


# Example usage
if __name__ == '__main__':
    parser = CommandParser()

    test_queries = [
        "update asset A-001 condition to Poor",
        "change all Fair assets to Poor",
        "add new asset: Pump 5, Building C, Good condition",
        "delete asset A-999",
        "how many assets do we have?",
        "set A-123 status to Critical"
    ]

    for query in test_queries:
        intent, params = parser.detect_intent(query)
        needs_conf = parser.needs_confirmation(intent, params) if params else False

        print(f"\nQuery: {query}")
        print(f"Intent: {intent}")
        print(f"Params: {params}")
        print(f"Needs Confirmation: {needs_conf}")
