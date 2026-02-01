#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Question Suggester Tool
Generates helpful question suggestions for users unfamiliar with asset management.
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
    """Suggests contextual questions based on asset data."""

    def __init__(self):
        """Initialize suggester with question templates."""
        self.question_templates = self._load_question_templates()

    def _load_question_templates(self) -> Dict[str, List[Dict[str, str]]]:
        """Load question templates organized by category."""
        return {
            "beginner": [
                {
                    "question": "How many total assets are in the register?",
                    "category": "Inventory",
                    "explanation": "Get an overview of your asset count"
                },
                {
                    "question": "What types of assets do we manage?",
                    "category": "Inventory",
                    "explanation": "Understand the diversity of your asset portfolio"
                },
                {
                    "question": "Which assets were added most recently?",
                    "category": "Inventory",
                    "explanation": "Track recent asset acquisitions"
                },
                {
                    "question": "Show me a summary of assets by location",
                    "category": "Inventory",
                    "explanation": "Understand geographical distribution"
                },
                {
                    "question": "What fields are tracked for each asset?",
                    "category": "Data Structure",
                    "explanation": "Learn what information is recorded"
                }
            ],
            "maintenance": [
                {
                    "question": "Which assets need maintenance this month?",
                    "category": "Maintenance",
                    "explanation": "Identify upcoming maintenance requirements"
                },
                {
                    "question": "Show me assets with overdue maintenance",
                    "category": "Maintenance",
                    "explanation": "Find maintenance backlogs"
                },
                {
                    "question": "What is the maintenance schedule for critical assets?",
                    "category": "Maintenance",
                    "explanation": "Plan preventive maintenance"
                },
                {
                    "question": "Which assets have the highest maintenance costs?",
                    "category": "Maintenance",
                    "explanation": "Identify maintenance cost drivers"
                }
            ],
            "compliance": [
                {
                    "question": "Are our asset records compliant with ISO 55000?",
                    "category": "Compliance",
                    "explanation": "Check ISO 55000 compliance status"
                },
                {
                    "question": "What asset data is missing for full ISO 55000 compliance?",
                    "category": "Compliance",
                    "explanation": "Identify compliance gaps"
                },
                {
                    "question": "How do we track asset lifecycle according to ISO 55000?",
                    "category": "Compliance",
                    "explanation": "Understand lifecycle management practices"
                },
                {
                    "question": "What ISO 55000 requirements apply to asset performance monitoring?",
                    "category": "Compliance",
                    "explanation": "Learn performance monitoring standards"
                }
            ],
            "financial": [
                {
                    "question": "What is the total value of all assets?",
                    "category": "Financial",
                    "explanation": "Calculate total asset value"
                },
                {
                    "question": "Show me the most expensive assets",
                    "category": "Financial",
                    "explanation": "Identify high-value assets"
                },
                {
                    "question": "What is the average asset age by category?",
                    "category": "Financial",
                    "explanation": "Assess asset aging and depreciation"
                },
                {
                    "question": "Which assets are approaching end of useful life?",
                    "category": "Financial",
                    "explanation": "Plan for asset replacement"
                }
            ],
            "risk": [
                {
                    "question": "Which assets have high risk ratings?",
                    "category": "Risk",
                    "explanation": "Identify high-risk assets"
                },
                {
                    "question": "What are the common risk factors across assets?",
                    "category": "Risk",
                    "explanation": "Understand risk patterns"
                },
                {
                    "question": "How does ISO 55000 recommend we assess asset risk?",
                    "category": "Risk",
                    "explanation": "Learn ISO risk assessment framework"
                },
                {
                    "question": "Which critical assets lack risk assessments?",
                    "category": "Risk",
                    "explanation": "Find risk assessment gaps"
                }
            ],
            "performance": [
                {
                    "question": "What are the key performance indicators for our assets?",
                    "category": "Performance",
                    "explanation": "Identify asset KPIs"
                },
                {
                    "question": "Which assets are underperforming?",
                    "category": "Performance",
                    "explanation": "Find performance issues"
                },
                {
                    "question": "How should we measure asset performance per ISO 55000?",
                    "category": "Performance",
                    "explanation": "Learn ISO performance standards"
                },
                {
                    "question": "Show me asset utilization rates",
                    "category": "Performance",
                    "explanation": "Assess asset utilization"
                }
            ],
            "advanced": [
                {
                    "question": "What is our asset lifecycle cost profile?",
                    "category": "Lifecycle",
                    "explanation": "Analyze total cost of ownership"
                },
                {
                    "question": "How can we optimize asset replacement strategies?",
                    "category": "Optimization",
                    "explanation": "Improve replacement planning"
                },
                {
                    "question": "What are the interdependencies between our critical assets?",
                    "category": "System Analysis",
                    "explanation": "Understand asset relationships"
                },
                {
                    "question": "How do our asset management practices align with organizational objectives per ISO 55000?",
                    "category": "Strategic",
                    "explanation": "Assess strategic alignment"
                }
            ]
        }

    def load_asset_index(self, index_file: str) -> Dict[str, Any]:
        """Load asset index to generate contextual suggestions."""
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def analyze_data_context(self, asset_index: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze asset data to provide context for suggestions.

        Args:
            asset_index: Asset index data

        Returns:
            Context information
        """
        stats = asset_index.get('statistics', {})
        schema = asset_index.get('schema', {})

        context = {
            'total_assets': stats.get('total_assets', 0),
            'available_fields': list(schema.get('fields', {}).keys()),
            'has_maintenance_data': any('maintenance' in f.lower() for f in schema.get('fields', {}).keys()),
            'has_financial_data': any('cost' in f.lower() or 'value' in f.lower() or 'price' in f.lower()
                                     for f in schema.get('fields', {}).keys()),
            'has_risk_data': any('risk' in f.lower() for f in schema.get('fields', {}).keys()),
            'has_location_data': any('location' in f.lower() for f in schema.get('fields', {}).keys()),
        }

        return context

    def filter_relevant_questions(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Filter questions based on available data.

        Args:
            context: Data context

        Returns:
            Relevant questions
        """
        all_questions = []

        # Always include beginner questions
        all_questions.extend(self.question_templates['beginner'])

        # Include category-specific questions if data exists
        if context.get('has_maintenance_data'):
            all_questions.extend(self.question_templates['maintenance'])

        if context.get('has_financial_data'):
            all_questions.extend(self.question_templates['financial'])

        if context.get('has_risk_data'):
            all_questions.extend(self.question_templates['risk'])

        # Always include compliance questions (ISO 55000 focus)
        all_questions.extend(self.question_templates['compliance'])

        # Include performance and advanced
        all_questions.extend(self.question_templates['performance'])
        all_questions.extend(self.question_templates['advanced'])

        return all_questions

    def suggest_questions(self, asset_index_file: str, num_suggestions: int = 10, difficulty: str = "all") -> List[Dict[str, str]]:
        """
        Generate question suggestions.

        Args:
            asset_index_file: Path to asset index
            num_suggestions: Number of suggestions to return
            difficulty: Question difficulty ("beginner", "advanced", "all")

        Returns:
            List of suggested questions
        """
        print("\n=== Generating Question Suggestions ===\n")

        # Load asset index
        asset_index = self.load_asset_index(asset_index_file)

        # Analyze context
        context = self.analyze_data_context(asset_index)

        print(f"Asset Register Context:")
        print(f"  Total Assets: {context['total_assets']}")
        print(f"  Available Fields: {len(context['available_fields'])}")
        print(f"  Has Maintenance Data: {context['has_maintenance_data']}")
        print(f"  Has Financial Data: {context['has_financial_data']}")
        print(f"  Has Risk Data: {context['has_risk_data']}")

        # Filter relevant questions
        relevant_questions = self.filter_relevant_questions(context)

        # Filter by difficulty
        if difficulty == "beginner":
            relevant_questions = [q for q in relevant_questions
                                 if q['category'] in ['Inventory', 'Data Structure', 'Maintenance']]
        elif difficulty == "advanced":
            relevant_questions = [q for q in relevant_questions
                                 if q['category'] in ['Lifecycle', 'Optimization', 'System Analysis', 'Strategic']]

        # Shuffle and select
        random.shuffle(relevant_questions)
        suggestions = relevant_questions[:num_suggestions]

        return suggestions

    def display_suggestions(self, suggestions: List[Dict[str, str]]):
        """
        Display suggestions in a user-friendly format.

        Args:
            suggestions: List of suggested questions
        """
        print("\n" + "="*60)
        print("SUGGESTED QUESTIONS")
        print("="*60)

        # Group by category
        by_category = {}
        for q in suggestions:
            category = q['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(q)

        for category, questions in by_category.items():
            print(f"\n[{category}]")
            for q in questions:
                print(f"  • {q['question']}")
                print(f"    → {q['explanation']}")

        print("\n" + "="*60)


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='Generate question suggestions for asset queries')
    parser.add_argument('--asset-index', default='data/.tmp/asset_index.json',
                       help='Path to asset index file')
    parser.add_argument('--num', type=int, default=10,
                       help='Number of suggestions')
    parser.add_argument('--difficulty', choices=['beginner', 'advanced', 'all'], default='all',
                       help='Question difficulty level')

    args = parser.parse_args()

    try:
        suggester = QuestionSuggester()
        suggestions = suggester.suggest_questions(
            asset_index_file=args.asset_index,
            num_suggestions=args.num,
            difficulty=args.difficulty
        )

        suggester.display_suggestions(suggestions)

        print(f"\n[OK] Generated {len(suggestions)} question suggestions")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
