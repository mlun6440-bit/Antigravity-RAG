#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Query Router
Uses Gemini Flash to intelligently classify user queries into:
- structured:  SQL queries for counting, filtering, listing database records
- analytical:  Complex analysis combining data + knowledge
- knowledge:   Pure conceptual/procedural questions from ISO standards
- graph:       Relational reasoning across asset relationships
               (e.g. "which critical assets lack ISO compliance documentation?")
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMQueryRouter:
    """Intelligent query router using LLM classification."""

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the query router.
        
        Args:
            model_name: Gemini model to use (default: Flash for speed)
        """
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not found")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"LLMQueryRouter initialized with model: {model_name}")

    def classify_query(self, query: str) -> str:
        """
        Classify a user query into one of three modes.

        Args:
            query: User's question

        Returns:
            One of: 'structured', 'analytical', 'knowledge'
        """
        start_time = time.time()
        
        prompt = f"""
        You are an expert query classifier for an Asset Management RAG system.
        Classify the following user query into exactly one of these categories:

        1. STRUCTURED
           - Intent: Counting, listing, filtering, or retrieving specific asset records from a database.
           - Keywords: How many, count, list, show, which assets, filter by, where is, status of.
           - DOMAIN ASSETS: Mentions of Electrical (Switchboard, DB, GPO), Mechanical (Chiller, AHU, Fan), Fire (Detector, Sprinkler), Hydraulics (Pump, Valve), Lifts, Security (CCTV), or Building Fabric (Roof, Door).
           - Examples:
             * "How many assets are in poor condition?"
             * "List all HVAC assets in Building A"
             * "Show me critical assets created last year"

        2. ANALYTICAL
           - Intent: Complex analysis requiring both data aggregation AND knowledge/reasoning.
           - Keywords: Analyze, compare, trend, why, impact, optimize, summary.
           - Examples:
             * "Analyze the failure rate of HVAC systems compared to industry standards"
             * "Why are critical assets failing in Sector B?"
             * "Summarize the condition of our fire safety equipment"

        3. KNOWLEDGE
           - Intent: Conceptual, procedural, or regulatory questions (ISO 55000) unrelated to specific asset records.
           - Keywords: How to, what is, explain, define, procedure, best practice, ISO clause.
           - Examples:
             * "How do I perform a risk assessment?"
             * "What does ISO 55000 say about lifecycle costing?"
             * "Explain the difference between corrective and preventive maintenance"

        4. GRAPH
           - Intent: Relational reasoning across multiple asset attributes, cross-referencing entities
             (buildings, categories, compliance standards, criticality, condition) to find patterns,
             clusters, or gaps that require traversing relationships rather than counting rows.
           - Keywords: relationship, dependency, linked, cluster, gap, lack, missing, cross, connect,
             without, no compliance, critical AND poor, buildings with, nearing end-of-life, compliance gap.
           - Examples:
             * "Which critical assets lack ISO compliance documentation?"
             * "Which buildings have clusters of poor-condition assets?"
             * "What assets are nearing end-of-life and have no compliance standard?"
             * "Show me the relationship between asset age and condition across buildings"
             * "Find high-cost assets in poor condition with no compliance docs"

        Query: "{query}"

        Instructions:
        - Output ONLY the category name: STRUCTURED, ANALYTICAL, KNOWLEDGE, or GRAPH.
        - Do not output any explanation or extra text.
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=10
                )
            )
            
            category = response.text.strip().upper()
            
            # Map to internal mode names
            mode_map = {
                'STRUCTURED': 'structured',
                'ANALYTICAL': 'analytical',
                'KNOWLEDGE': 'knowledge',
                'GRAPH': 'graph',
            }

            result = mode_map.get(category, 'knowledge')  # Default to knowledge if unsure
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Query classified as '{result}' in {elapsed:.1f}ms: {query}")
            
            return result

        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            # Fallback heuristic
            return self._heuristic_fallback(query)

    def _heuristic_fallback(self, query: str) -> str:
        """Simple keyword fallback if LLM fails."""
        q_lower = query.lower()

        # Graph reasoning patterns (check first — higher specificity)
        graph_keywords = [
            'lack', 'lacking', 'missing', 'without', 'no compliance', 'compliance gap',
            'cluster', 'relationship', 'linked', 'dependency', 'nearing end',
            'end-of-life', 'end of life', 'critical and poor', 'cross-reference',
            'buildings with', 'compliance documentation',
        ]
        analytical_keywords = ['analyze', 'compare', 'trend', 'summary', 'report', 'why']
        structured_keywords = ['how many', 'count', 'list', 'show', 'which', 'where', 'total']

        for kw in graph_keywords:
            if kw in q_lower:
                return 'graph'

        for kw in analytical_keywords:
            if kw in q_lower:
                return 'analytical'

        for kw in structured_keywords:
            if kw in q_lower:
                return 'structured'

        return 'knowledge'

if __name__ == "__main__":
    # Test the router
    try:
        router = LLMQueryRouter()
        test_queries = [
            "How many assets are in poor condition?",
            "What is the ISO standard for risk management?",
            "Analyze the performance of our cooling towers",
            "Count distinct asset types in the database",
            "Which critical assets lack ISO compliance documentation?",
            "Which buildings have clusters of poor-condition assets?",
        ]
        
        print("Testing LLM Query Router...")
        for q in test_queries:
            mode = router.classify_query(q)
            print(f"Query: '{q}' -> Mode: {mode}")
            
    except Exception as e:
        print(f"Test failed: {e}")
