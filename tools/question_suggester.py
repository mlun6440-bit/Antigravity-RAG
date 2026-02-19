#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Question Suggester Tool (Enhanced)
Generates smart, data-driven, and educational questions connecting Asset Register data to ISO 55000.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any
import random

# Python 3.13 handles UTF-8 natively on Windows
if sys.platform == 'win32':
    import io

class QuestionSuggester:
    """Suggests intelligent questions based on asset data quality and ISO 55000 principles."""

    def __init__(self):
        """Initialize suggester."""
        pass

    def load_asset_index(self, index_file: str) -> Dict[str, Any]:
        """Load asset index to generate contextual suggestions."""
        if not os.path.exists(index_file):
            return {"assets": [], "statistics": {}}
            
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def analyze_data_gaps(self, assets: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Analyze what percentage of data is missing for key ISO fields.
        Returns: Dict of field_name -> missing_percentage (0.0 to 1.0)
        """
        if not assets:
            return {}
            
        total = len(assets)
        missing_counts = {
            "date_installed": 0,
            "asset_criticality": 0,
            "status": 0, # Condition
            "estimated_replacement_cost": 0,
            "manufacturer": 0,
            "warranty_expiry": 0
        }
        
        for asset in assets:
            if not asset.get("date_installed"): missing_counts["date_installed"] += 1
            if not asset.get("asset_criticality"): missing_counts["asset_criticality"] += 1
            if not asset.get("status"): missing_counts["status"] += 1
            if not asset.get("estimated_replacement_cost"): missing_counts["estimated_replacement_cost"] += 1
            if not asset.get("manufacturer"): missing_counts["manufacturer"] += 1
            if not asset.get("date_warranty_expiry"): missing_counts["warranty_expiry"] += 1
            
        return {k: v / total for k, v in missing_counts.items()}

    def get_categories(self, assets: List[Dict[str, Any]]) -> List[str]:
        """Get top asset categories."""
        counts = {}
        for a in assets:
            cat = a.get("asset_category", "Unknown")
            if cat:
                # Handle comma separated lists
                parts = cat.split(',')
                primary = parts[0].strip()
                counts[primary] = counts.get(primary, 0) + 1
        
        # Return top 5
        sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [c[0] for c in sorted_cats[:5]]

    def generate_educational_question(self, topic: str) -> Dict[str, str]:
        """Generate a static educational question about ISO 55000."""
        iso_questions = [
            {
                "question": "What is the definition of an asset according to ISO 55000?",
                "category": "ISO Education",
                "explanation": "Learn the fundamental definition that scopes your entire management system."
            },
            {
                "question": "What are the requirements for a Strategic Asset Management Plan (SAMP)?",
                "category": "ISO Education",
                "explanation": "Understand the document connecting organizational objectives to asset decisions (ISO 55001 Cl 4.3)."
            },
            {
                "question": "How does ISO 55000 define 'Criticality'?",
                "category": "ISO Education",
                "explanation": "Learn how risk-based criticality drives maintenance priority."
            },
            {
                "question": "What is the role of Top Management in asset management?",
                "category": "ISO Education",
                "explanation": "ISO 55001 Clause 5.1 emphasizes leadership's role in resource allocation."
            },
            {
                "question": "What constitutes a 'nonconformity' in asset data?",
                "category": "ISO Education",
                "explanation": "Learn how data gaps can be classified as nonconformities under ISO 55001 Clause 10.2."
            }
        ]
        return random.choice(iso_questions)

    def suggest_questions(self, asset_index_file: str, num_suggestions: int = 10, difficulty: str = "all") -> List[Dict[str, str]]:
        """
        Generate smart questions based on actual data gaps and ISO principles.
        """
        print("\n=== Generating Smart Suggestions ===\n")

        data = self.load_asset_index(asset_index_file)
        assets = data.get("assets", [])
        
        if not assets:
            return [self.generate_educational_question("general") for _ in range(5)]

        gaps = self.analyze_data_gaps(assets)
        categories = self.get_categories(assets)
        top_cat = categories[0] if categories else "Assets"
        
        suggestions = []

        # --- 1. Gap Analysis Questions (Data Quality) ---
        # If > 30% missing installation date
        if gaps["date_installed"] > 0.3:
            suggestions.append({
                "question": "Which assets are missing installation dates?",
                "category": "Data Quality",
                "explanation": f"ISO 55000 requires lifecycle data. {int(gaps['date_installed']*100)}% of your assets lack this."
            })
            suggestions.append({
                "question": "How does missing installation date affect lifecycle modeling per ISO 55000?",
                "category": "ISO Learning",
                "explanation": "Without age data, you cannot predict End of Life accurately (ISO 55001 Cl 6.2.2)."
            })

        # If > 10% missing criticality
        if gaps["asset_criticality"] > 0.1:
            suggestions.append({
                "question": "Show me assets with missing criticality ratings",
                "category": "Risk Management",
                "explanation": f"Criticality is key to risk-based maintenance (ISO 55001 Cl 6.1). {int(gaps['asset_criticality']*100)}% unrated."
            })

        # If > 50% missing replacement cost
        if gaps["estimated_replacement_cost"] > 0.5:
            suggestions.append({
                "question": "Which asset categories define replacement costs?",
                "category": "Financial Planning",
                "explanation": "ISO 55000 links technical and financial decisions. Cost data is vital for valid SAMPs."
            })

        # --- 2. Strategic Insight Questions (Analysis) ---
        # Condition vs Criticality
        suggestions.append({
            "question": "Show me High Criticality assets in Poor condition",
            "category": "Risk Analysis",
            "explanation": "ISO 55001 demands prioritization of risks. These are your 'burning platform' assets."
        })
        
        # Category specific
        if top_cat:
            suggestions.append({
                "question": f"What is the condition profile of {top_cat}?",
                "category": "Portfolio Review",
                "explanation": "Understanding condition by class helps target renewal budgets."
            })

        # --- 3. Education Questions (ISO 55000) ---
        # Always mix in 2-3 pure learning questions
        suggestions.append(self.generate_educational_question("general"))
        suggestions.append(self.generate_educational_question("general"))
        
        # --- 4. "Actionable" Questions ---
        suggestions.append({
            "question": "Generate a summary of renewal costs for the next 5 years",
            "category": "Strategic Planning",
            "explanation": "Supports the 'Financial Plan' requirement of the SAMP (ISO 55001 Cl 2.5.3.4)."
        })

        # Shuffle and return requested amount
        random.shuffle(suggestions)
        
        # Ensure we don't have duplicates
        unique_suggestions = []
        seen = set()
        for s in suggestions:
            if s['question'] not in seen:
                unique_suggestions.append(s)
                seen.add(s['question'])
                
        return unique_suggestions[:num_suggestions]

    def display_suggestions(self, suggestions: List[Dict[str, str]]):
        """Display suggestions."""
        print("\n" + "="*60)
        print("SUGGESTED QUESTIONS (ISO 55000 ALIGNED)")
        print("="*60)

        by_category = {}
        for q in suggestions:
            cat = q['category']
            if cat not in by_category: by_category[cat] = []
            by_category[cat].append(q)

        for category, questions in by_category.items():
            print(f"\n[{category}]")
            for q in questions:
                print(f"  • {q['question']}")
                print(f"    → {q['explanation']}")
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset-index', default='data/.tmp/asset_index.json')
    parser.add_argument('--num', type=int, default=10)
    args = parser.parse_args()

    suggester = QuestionSuggester()
    suggestions = suggester.suggest_questions(args.asset_index, args.num)
    suggester.display_suggestions(suggestions)

if __name__ == '__main__':
    main()
