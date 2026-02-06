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
            "data_quality": [
                {
                    "question": "Which critical assets lack risk assessments?",
                    "category": "Data Quality",
                    "explanation": "ISO 55000: Identify risk assessment gaps to improve register completeness"
                },
                {
                    "question": "Which assets have incomplete condition data?",
                    "category": "Data Quality",
                    "explanation": "ISO 55001: Find assets needing condition updates for better decision-making"
                },
                {
                    "question": "Which assets are missing installation dates?",
                    "category": "Data Quality",
                    "explanation": "ISO 55000: Complete lifecycle data for accurate age-based planning"
                },
                {
                    "question": "Which assets lack maintenance history?",
                    "category": "Data Quality",
                    "explanation": "ISO 55001: Build maintenance records for reliability analysis"
                },
                {
                    "question": "What asset data is missing for full ISO 55000 compliance?",
                    "category": "Data Quality",
                    "explanation": "ISO 55002: Systematic gap analysis to improve register maturity"
                }
            ],
            "beginner": [
                {
                    "question": "How many total assets are in the register?",
                    "category": "Portfolio Overview",
                    "explanation": "ISO 55000: Understand portfolio scope and scale"
                },
                {
                    "question": "What types of assets do we manage?",
                    "category": "Portfolio Overview",
                    "explanation": "ISO 55000: Map asset diversity for strategic planning"
                },
                {
                    "question": "How many poor condition fire systems do we have?",
                    "category": "Critical Assets",
                    "explanation": "ISO 55000: Prioritize life safety assets for immediate action"
                },
                {
                    "question": "Show me all R4-R5 rated assets requiring immediate action",
                    "category": "Critical Assets",
                    "explanation": "ISO 55001: Identify critical condition assets for intervention planning"
                }
            ],
            "maintenance": [
                {
                    "question": "Which electrical switchboards are over 20 years old?",
                    "category": "Lifecycle Planning",
                    "explanation": "ISO 55000: Age-based intervention planning for critical infrastructure"
                },
                {
                    "question": "Which assets need replacement in the next 2 years?",
                    "category": "Lifecycle Planning",
                    "explanation": "ISO 55001: Capital planning based on remaining useful life"
                },
                {
                    "question": "Show me assets approaching end-of-life with high criticality",
                    "category": "Lifecycle Planning",
                    "explanation": "ISO 55000: Prioritize replacement planning by risk and age"
                },
                {
                    "question": "What is the maintenance backlog for R4-R5 condition assets?",
                    "category": "Maintenance Optimization",
                    "explanation": "ISO 55001: Identify maintenance deferrals causing condition degradation"
                }
            ],
            "iso_learning": [
                {
                    "question": "What does ISO 55000 say about risk assessment?",
                    "category": "ISO 55000 Learning",
                    "explanation": "Learn ISO 55000 risk management framework principles"
                },
                {
                    "question": "How should we measure asset performance per ISO 55000?",
                    "category": "ISO 55000 Learning",
                    "explanation": "Understand ISO performance measurement requirements"
                },
                {
                    "question": "What are ISO 55001 requirements for lifecycle costing?",
                    "category": "ISO 55000 Learning",
                    "explanation": "Learn whole-of-life cost analysis methods"
                },
                {
                    "question": "How does ISO 55000 recommend prioritizing asset interventions?",
                    "category": "ISO 55000 Learning",
                    "explanation": "Learn risk-based decision-making frameworks"
                }
            ],
            "strategic_improvement": [
                {
                    "question": "What building services assets need replacement in next 2 years?",
                    "category": "Capital Planning",
                    "explanation": "ISO 55001: Long-term capital planning for building services portfolio"
                },
                {
                    "question": "Which asset categories have the most data quality issues?",
                    "category": "Register Improvement",
                    "explanation": "ISO 55000: Identify systematic data gaps for targeted improvement"
                },
                {
                    "question": "What is the average condition rating by asset type?",
                    "category": "Portfolio Health",
                    "explanation": "ISO 55000: Benchmark portfolio health to identify weak areas"
                },
                {
                    "question": "Which locations have the most critical condition assets?",
                    "category": "Portfolio Health",
                    "explanation": "ISO 55000: Geographic risk profiling for intervention prioritization"
                }
            ],
            "risk": [
                {
                    "question": "Show me high criticality assets with poor condition ratings",
                    "category": "Risk Assessment",
                    "explanation": "ISO 55000: Risk-based prioritization combining consequence and condition"
                },
                {
                    "question": "What are the interdependencies between our critical assets?",
                    "category": "System Risk",
                    "explanation": "ISO 55001: Understand cascading failure risks in asset systems"
                },
                {
                    "question": "Which life safety systems lack recent inspections?",
                    "category": "Risk Assessment",
                    "explanation": "ISO 55001: Identify compliance risks for critical safety assets"
                },
                {
                    "question": "What is our exposure to assets with unknown condition?",
                    "category": "Risk Assessment",
                    "explanation": "ISO 55000: Quantify uncertainty risk from incomplete data"
                }
            ],
            "continuous_improvement": [
                {
                    "question": "What patterns exist in our asset failures?",
                    "category": "Continuous Improvement",
                    "explanation": "ISO 55001: Learn from failures to improve preventive strategies"
                },
                {
                    "question": "Which asset types consistently degrade faster than expected?",
                    "category": "Continuous Improvement",
                    "explanation": "ISO 55000: Identify systematic issues for root cause analysis"
                },
                {
                    "question": "How accurate are our condition assessments compared to actual failures?",
                    "category": "Continuous Improvement",
                    "explanation": "ISO 55001: Validate and improve condition assessment methods"
                },
                {
                    "question": "What is the correlation between maintenance frequency and asset condition?",
                    "category": "Continuous Improvement",
                    "explanation": "ISO 55000: Optimize maintenance strategies based on evidence"
                }
            ],
            "advanced": [
                {
                    "question": "What is the lifecycle cost profile for building services vs infrastructure?",
                    "category": "Advanced Analysis",
                    "explanation": "ISO 55002: Compare total cost of ownership across asset categories"
                },
                {
                    "question": "How do our asset management practices align with organizational objectives per ISO 55000?",
                    "category": "Strategic Alignment",
                    "explanation": "ISO 55001: Connect asset decisions to organizational strategy"
                },
                {
                    "question": "What is the optimal renewal timing for assets approaching end-of-life?",
                    "category": "Advanced Analysis",
                    "explanation": "ISO 55000: Balance risk, cost, and performance for renewal decisions"
                },
                {
                    "question": "How can we improve asset data quality systematically?",
                    "category": "Register Maturity",
                    "explanation": "ISO 55001: Develop data quality improvement roadmap"
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

        # Priority 1: Data Quality Improvement (always show these)
        all_questions.extend(self.question_templates['data_quality'])

        # Priority 2: ISO 55000 Learning (always show these)
        all_questions.extend(self.question_templates['iso_learning'])

        # Priority 3: Basic queries for immediate action
        all_questions.extend(self.question_templates['beginner'])

        # Priority 4: Strategic improvement questions
        all_questions.extend(self.question_templates['strategic_improvement'])

        # Priority 5: Risk-based questions
        all_questions.extend(self.question_templates['risk'])

        # Priority 6: Lifecycle planning
        all_questions.extend(self.question_templates['maintenance'])

        # Priority 7: Continuous improvement
        all_questions.extend(self.question_templates['continuous_improvement'])

        # Priority 8: Advanced analysis
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
