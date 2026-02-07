#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Citation Formatter
Formats citations in NotebookLM style for asset queries and ISO standards.
"""

from typing import Dict, List, Any
from tools.spreadsheet_config import get_spreadsheet_url, has_spreadsheet_url


class CitationFormatter:
    """Formats citations for answers."""

    def __init__(self):
        """Initialize formatter."""
        self.citation_counter = 0
        self.citations = []

    def reset(self):
        """Reset citation counter for new query."""
        self.citation_counter = 0
        self.citations = []

    def add_asset_citation(self, asset_ids: List[str], source_file: str,
                          sheet_name: str, field: str, filter_criteria: str,
                          count: int) -> int:
        """
        Add citation for asset data.

        Args:
            asset_ids: List of asset IDs referenced
            source_file: Source file name
            sheet_name: Sheet name
            field: Field name queried
            filter_criteria: Filter applied
            count: Number of matching records

        Returns:
            Citation number
        """
        self.citation_counter += 1

        # Get Google Sheets URL if available
        spreadsheet_url = get_spreadsheet_url(sheet_name)

        self.citations.append({
            'number': self.citation_counter,
            'type': 'asset_data',
            'source_file': source_file,
            'sheet_name': sheet_name,
            'field': field,
            'filter': filter_criteria,
            'count': count,
            'asset_ids': asset_ids[:10],  # Show first 10 IDs
            'spreadsheet_url': spreadsheet_url  # NEW: Add Google Sheets URL
        })

        return self.citation_counter

    def add_iso_citation(self, iso_standard: str, section_number: str,
                        section_title: str, page_range: str,
                        quote: str) -> int:
        """
        Add citation for ISO standard.

        Args:
            iso_standard: ISO standard name (e.g., "ISO 55001")
            section_number: Clause/section number
            section_title: Section title
            page_range: Page number or range
            quote: Excerpt from standard

        Returns:
            Citation number
        """
        self.citation_counter += 1

        print(f"[ISO CITATION ADDED] #{self.citation_counter}: {iso_standard} {section_number} - {section_title[:50]}")

        self.citations.append({
            'number': self.citation_counter,
            'type': 'iso_standard',
            'standard': iso_standard,
            'section': section_number,
            'title': section_title,
            'pages': page_range,
            'quote': quote
        })

        return self.citation_counter

    def add_calculation_citation(self, description: str, formula: str,
                                 data_sources: List[str]) -> int:
        """
        Add citation for calculations.

        Args:
            description: What was calculated
            formula: The formula used
            data_sources: List of data sources

        Returns:
            Citation number
        """
        self.citation_counter += 1

        self.citations.append({
            'number': self.citation_counter,
            'type': 'calculation',
            'description': description,
            'formula': formula,
            'sources': data_sources
        })

        return self.citation_counter

    def format_references(self) -> str:
        """
        Format all citations as reference section.

        Returns:
            Formatted reference text
        """
        if not self.citations:
            return ""

        lines = []
        lines.append("\n" + "━" * 70)
        lines.append("REFERENCES")
        lines.append("━" * 70)
        lines.append("")

        for citation in self.citations:
            if citation['type'] == 'asset_data':
                lines.append(self._format_asset_citation(citation))
            elif citation['type'] == 'iso_standard':
                lines.append(self._format_iso_citation(citation))
            elif citation['type'] == 'calculation':
                lines.append(self._format_calculation_citation(citation))

            lines.append("")  # Blank line between citations

        lines.append("━" * 70)

        return "\n".join(lines)

    def _format_asset_citation(self, citation: Dict[str, Any]) -> str:
        """Format asset data citation."""
        lines = []
        lines.append(f"[{citation['number']}] Asset Data - {citation['filter']}")
        lines.append(f"    Source: {citation['source_file']}")
        lines.append(f"    Sheet: {citation['sheet_name']}")
        lines.append(f"    Field: {citation['field']}")
        lines.append(f"    Matching records: {citation['count']}")

        if citation['asset_ids']:
            ids_str = ", ".join(citation['asset_ids'])
            if citation['count'] > 10:
                ids_str += f", ... and {citation['count'] - 10} more"
            lines.append(f"    Asset IDs: {ids_str}")

        return "\n".join(lines)

    def _format_iso_citation(self, citation: Dict[str, Any]) -> str:
        """Format ISO standard citation."""
        lines = []
        lines.append(f"[{citation['number']}] {citation['standard']} - {citation['title']}")
        lines.append(f"    Section: {citation['section']}")
        lines.append(f"    Pages: {citation['pages']}")
        lines.append(f"    Excerpt: \"{citation['quote']}\"")

        return "\n".join(lines)

    def _format_calculation_citation(self, citation: Dict[str, Any]) -> str:
        """Format calculation citation."""
        lines = []
        lines.append(f"[{citation['number']}] Calculation - {citation['description']}")
        lines.append(f"    Formula: {citation['formula']}")
        lines.append(f"    Data sources:")
        for source in citation['sources']:
            lines.append(f"      • {source}")

        return "\n".join(lines)

    def get_inline_citation(self, citation_number: int) -> str:
        """
        Get inline citation marker.

        Args:
            citation_number: Citation number

        Returns:
            Formatted inline citation (e.g., "[1]")
        """
        return f"[{citation_number}]"

    def get_citations_as_json(self) -> List[Dict[str, Any]]:
        """
        Get all citations as structured JSON for frontend popups.

        Returns:
            List of citation dictionaries
        """
        return self.citations


def example_usage():
    """Example of how to use the citation formatter."""
    formatter = CitationFormatter()

    # Add some example citations
    cit1 = formatter.add_asset_citation(
        asset_ids=["A-001", "A-002", "A-003"],
        source_file="Asset register Part 1",
        sheet_name="Sheet1",
        field="Condition",
        filter_criteria="Condition = 'Poor'",
        count=312
    )

    cit2 = formatter.add_iso_citation(
        iso_standard="ISO 55001:2014",
        section_number="8.3",
        section_title="Management of change",
        page_range="24-26",
        quote="The organization shall establish, implement and maintain process(es)..."
    )

    cit3 = formatter.add_calculation_citation(
        description="Asset portfolio percentage",
        formula="312 poor assets ÷ 1,853 total assets = 16.8%",
        data_sources=["Asset index statistics", "All 9 asset register files"]
    )

    # Create answer with inline citations
    answer = f"""Your asset register shows 312 assets in poor condition {formatter.get_inline_citation(cit1)}.

According to ISO 55001, these require immediate assessment {formatter.get_inline_citation(cit2)}.

This represents 16.8% of your total asset portfolio {formatter.get_inline_citation(cit3)},
which is above recommended thresholds for infrastructure management.
"""

    # Add references
    answer += formatter.format_references()

    print(answer)


if __name__ == '__main__':
    example_usage()
