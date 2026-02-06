#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consultant Analyzer - Asset Management Expert Analysis Layer
Applies ISO 55000 consultant frameworks to enhance RAG answers.
"""

import os
import re
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv


class ConsultantAnalyzer:
    """
    Applies asset management consultant frameworks to enhance answers.
    Based on .claude/Eraclaudskills/asset-management-consultant skill.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize consultant analyzer with Gemini API."""
        load_dotenv()

        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found")

        # Use Pro model for consultant-level analysis
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')

        print("[OK] Consultant Analyzer initialized")

    def detect_analysis_type(self, question: str, answer: str) -> str:
        """
        Detect what type of consultant analysis is most relevant.

        Returns:
            'risk' - Risk assessment (condition, failures, criticality)
            'lifecycle' - Lifecycle costing (replacement, maintenance, NPV)
            'strategic' - Strategic planning (portfolio, long-term)
            'compliance' - ISO 55000 compliance guidance
        """
        question_lower = question.lower()
        answer_lower = answer.lower()
        combined = question_lower + " " + answer_lower

        # Risk assessment keywords
        risk_keywords = ['condition', 'poor', 'fail', 'failure', 'risk', 'critical',
                        'urgent', 'emergency', 'breakdown', 'deteriorat']

        # Lifecycle costing keywords
        lifecycle_keywords = ['replace', 'replacement', 'cost', 'budget', 'npv',
                             'investment', 'capital', 'refurbish', 'renew']

        # Strategic planning keywords
        strategic_keywords = ['should', 'recommend', 'strategy', 'plan', 'priorit',
                             'portfolio', 'roadmap', 'program', 'which option']

        # Compliance keywords
        compliance_keywords = ['iso', '55000', '55001', '55002', 'standard',
                              'compliance', 'audit', 'framework']

        # Count keyword matches
        risk_score = sum(1 for kw in risk_keywords if kw in combined)
        lifecycle_score = sum(1 for kw in lifecycle_keywords if kw in combined)
        strategic_score = sum(1 for kw in strategic_keywords if kw in combined)
        compliance_score = sum(1 for kw in compliance_keywords if kw in combined)

        # Determine primary analysis type
        scores = {
            'risk': risk_score,
            'lifecycle': lifecycle_score,
            'strategic': strategic_score,
            'compliance': compliance_score
        }

        primary_type = max(scores, key=scores.get)

        # Default to strategic if no clear signal
        if scores[primary_type] == 0:
            primary_type = 'strategic'

        print(f"[Consultant] Analysis type detected: {primary_type} (scores: {scores})")
        return primary_type

    def create_consultant_prompt(self, analysis_type: str, question: str,
                                 answer: str, asset_summary: Dict[str, Any]) -> str:
        """
        Create consultant-specific system prompt based on analysis type.

        Args:
            analysis_type: Type of analysis ('risk', 'lifecycle', 'strategic', 'compliance')
            question: Original user question
            answer: Answer from RAG pipeline
            asset_summary: Summary statistics from retrieved data
        """

        base_prompt = """You are a senior ISO 55000 Asset Management Consultant providing expert analysis.

Your role is to ENHANCE the existing answer with consultant-level strategic insights, not repeat it.

CRITICAL INSTRUCTIONS:
- DO NOT repeat or summarize the existing answer
- ADD value through strategic frameworks and expert analysis
- Use markdown tables for structured data
- Provide actionable, quantified recommendations
- Reference ISO 55000 standards where relevant
"""

        if analysis_type == 'risk':
            framework_prompt = """
Apply RISK ASSESSMENT frameworks:

1. **Risk Matrix Analysis (5×5 Consequence × Likelihood)**
   - Assess portfolio risk exposure
   - Estimate financial impact ranges
   - Calculate criticality scores where possible
   - Apply risk treatment strategies (Transfer/Avoid/Reduce/Accept)

2. **Asset Criticality**
   - Identify mission-critical vs routine assets
   - Consider consequence of failure
   - Factor in redundancy and dependencies

3. **Risk Mitigation Hierarchy**
   - Prioritized intervention recommendations
   - Timeline and budget estimates
   - ISO 55001 Clause 6.1 alignment

Present findings in structured format with tables and clear priority rankings.
"""

        elif analysis_type == 'lifecycle':
            framework_prompt = """
Apply LIFECYCLE COSTING frameworks:

1. **Total Cost of Ownership (TCO)**
   - Compare options (repair vs replace vs refurbish)
   - Consider: Acquisition + Operating + Maintenance + Disposal
   - Typical split: 15-25% capital, 40-50% operating, 25-35% maintenance

2. **Net Present Value (NPV)**
   - Use 5% discount rate for government, 7-10% for commercial
   - Calculate payback periods
   - Estimate benefit-cost ratios

3. **Economic Recommendations**
   - Rank options by NPV
   - Identify break-even points
   - Consider non-financial factors (risk, service quality)

Present analysis with comparison tables and financial recommendations.
"""

        elif analysis_type == 'strategic':
            framework_prompt = """
Apply STRATEGIC PLANNING frameworks:

1. **Portfolio Analysis**
   - Asset class prioritization
   - Resource allocation optimization
   - Long-term capital planning (5-10 year horizon)

2. **Value Optimization**
   - Align with ISO 55000 value principles
   - Balance cost, risk, and performance
   - Identify quick wins vs long-term investments

3. **Implementation Roadmap**
   - Phased approach with milestones
   - Budget profiling over time
   - Governance and decision points

Present as executive-ready strategic recommendations with clear action items.
"""

        elif analysis_type == 'compliance':
            framework_prompt = """
Apply ISO 55000 COMPLIANCE frameworks:

1. **Standards Alignment**
   - Map to ISO 55000 (principles), 55001 (requirements), 55002 (guidance)
   - Identify relevant clauses
   - Assess maturity level (Aware → Developing → Competent → Optimizing → Excellent)

2. **Gap Analysis**
   - Current state vs ISO requirements
   - Priority compliance gaps
   - Improvement recommendations

3. **Best Practice Guidance**
   - Australian Standards integration (AS 1670, 1851, 2118, 2419, 2444)
   - Industry benchmarks
   - Implementation considerations

Present with standards cross-references and maturity assessment.
"""

        else:
            framework_prompt = "Apply general asset management best practices and ISO 55000 principles."

        # Build full prompt
        full_prompt = f"""{base_prompt}

{framework_prompt}

=== CONTEXT ===

**Original Question:**
{question}

**Existing Answer (DO NOT REPEAT):**
{answer}

**Asset Data Summary:**
{self._format_asset_summary(asset_summary)}

=== YOUR TASK ===

Provide ENHANCED EXPERT ANALYSIS that ADDS strategic value beyond the existing answer.

Structure your response as:

## Expert Analysis

[Your consultant-level insights using the frameworks above]

### Key Findings
[Bullet points with quantified assessments]

### Recommended Actions
[Prioritized, actionable steps with timelines and budget estimates]

### ISO 55000 Alignment
[Relevant standards and compliance notes]

Use markdown tables for structured data. Be concise but comprehensive. Focus on strategic value.
"""

        return full_prompt

    def _format_asset_summary(self, asset_summary: Dict[str, Any]) -> str:
        """Format asset summary for prompt context."""
        if not asset_summary:
            return "No asset data available"

        lines = []

        if 'total_assets' in asset_summary:
            lines.append(f"Total Assets: {asset_summary['total_assets']:,}")

        if 'condition_breakdown' in asset_summary:
            lines.append("\nCondition Breakdown:")
            for condition, count in asset_summary['condition_breakdown'].items():
                lines.append(f"  - {condition}: {count:,} assets")

        if 'age_profile' in asset_summary:
            lines.append("\nAge Profile:")
            for age_range, count in asset_summary['age_profile'].items():
                lines.append(f"  - {age_range}: {count:,} assets")

        if 'value_exposure' in asset_summary:
            lines.append(f"\nEstimated Value Exposure: ${asset_summary['value_exposure']:,.0f}")

        return "\n".join(lines) if lines else "Limited asset data available"

    def analyze(self, question: str, answer: str, citations: List[Dict],
                asset_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform consultant-level analysis on the answer.

        Args:
            question: Original user question
            answer: Answer from RAG pipeline
            citations: Citation data from the query
            asset_summary: Optional summary statistics about retrieved assets

        Returns:
            Dict with analysis, type, and metadata
        """
        print(f"\n[Consultant] Starting expert analysis...")

        try:
            # Detect analysis type
            analysis_type = self.detect_analysis_type(question, answer)

            # Create consultant prompt
            prompt = self.create_consultant_prompt(
                analysis_type=analysis_type,
                question=question,
                answer=answer,
                asset_summary=asset_summary or {}
            )

            # Query Gemini with consultant prompt
            print(f"[Consultant] Applying {analysis_type} frameworks...")
            response = self.model.generate_content(prompt)

            # Extract citation numbers from analysis
            import re
            citation_pattern = r'\[(\d+)\]'
            cited_numbers = set(re.findall(citation_pattern, response.text))

            # Filter to only referenced citations
            referenced_citations = [
                cit for cit in citations
                if str(cit['number']) in cited_numbers
            ]

            result = {
                'analysis': response.text,
                'analysis_type': analysis_type,
                'frameworks_applied': self._get_frameworks_for_type(analysis_type),
                'citations': referenced_citations,
                'status': 'success'
            }

            print(f"[OK] Consultant analysis complete ({analysis_type}, {len(referenced_citations)} citations)")
            return result

        except Exception as e:
            print(f"[ERROR] Consultant analysis failed: {e}")
            return {
                'analysis': None,
                'error': str(e),
                'status': 'error'
            }

    def _get_frameworks_for_type(self, analysis_type: str) -> List[str]:
        """Get list of frameworks applied for display."""
        frameworks = {
            'risk': [
                'Risk Matrix (5×5 Consequence × Likelihood)',
                'Asset Criticality Assessment',
                'Risk Treatment Hierarchy (TARA)',
                'ISO 55001 Clause 6.1 - Risk Management'
            ],
            'lifecycle': [
                'Total Cost of Ownership (TCO)',
                'Net Present Value (NPV) Analysis',
                'Benefit-Cost Ratio (BCR)',
                'ISO 55002 Section 8.2 - Economic Analysis'
            ],
            'strategic': [
                'Portfolio Optimization',
                'Value-Based Decision Making',
                'Implementation Roadmapping',
                'ISO 55000 Core Principles'
            ],
            'compliance': [
                'ISO 55000/55001/55002 Mapping',
                'Maturity Assessment',
                'Gap Analysis',
                'Australian Standards Integration'
            ]
        }

        return frameworks.get(analysis_type, ['General Asset Management Best Practices'])


# Test function
if __name__ == '__main__':
    print("Testing Consultant Analyzer...")

    try:
        analyzer = ConsultantAnalyzer()

        # Test query
        test_question = "How many poor condition assets do we have?"
        test_answer = "There are 856 assets in poor condition [1]. This represents approximately 12% of the total portfolio."
        test_citations = [{'number': 1, 'type': 'asset_data', 'count': 856}]
        test_summary = {
            'total_assets': 7142,
            'condition_breakdown': {
                'Poor': 856,
                'Fair': 1234,
                'Good': 3052,
                'Very Good': 2000
            }
        }

        result = analyzer.analyze(
            question=test_question,
            answer=test_answer,
            citations=test_citations,
            asset_summary=test_summary
        )

        if result['status'] == 'success':
            print("\n" + "="*60)
            print("CONSULTANT ANALYSIS:")
            print("="*60)
            print(result['analysis'])
            print("\nFrameworks Applied:")
            for fw in result['frameworks_applied']:
                print(f"  - {fw}")
        else:
            print(f"Error: {result['error']}")

    except Exception as e:
        print(f"Test failed: {e}")
