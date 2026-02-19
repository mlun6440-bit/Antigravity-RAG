#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISO 55000 Auditor Stress Test v2 - EXPANDED
15 scenarios covering edge cases
"""

import sys
import os
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from gemini_query_engine import GeminiQueryEngine

LOG_FILE = "iso_audit_report_v2.txt"

def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def run_stress_test():
    # Clear log file
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("ISO 55000 AUDITOR STRESS TEST v2 - EXPANDED\n")
        f.write("=" * 60 + "\n\n")

    log("Initializing GeminiQueryEngine...")
    start_init = time.time()
    try:
        engine = GeminiQueryEngine()
        log(f"[OK] Engine loaded in {time.time() - start_init:.2f}s\n")
    except Exception as e:
        log(f"[FAIL] Engine could not start: {e}")
        return

    asset_index = 'data/.tmp/asset_index.json' 
    iso_kb = 'data/.tmp/iso_knowledge_base.json'

    scenarios = [
        # Original 10
        {
            "id": 1,
            "category": "ACCURACY",
            "query": "How many Precise Air assets are there?",
            "expect": "Exact count (4473)",
            "mode": "structured"
        },
        {
            "id": 2,
            "category": "COMPLEXITY",
            "query": "Analyze my poor condition electrical assets per ISO 55001",
            "expect": "Hybrid response: SQL count + ISO risk analysis",
            "mode": "analytical"
        },
        {
            "id": 3,
            "category": "SEGMENTATION",
            "query": "Count assets by criticality",
            "expect": "Table breakdown of Critical, High, Medium, Low",
            "mode": "structured"
        },
        {
            "id": 4,
            "category": "KNOWLEDGE",
            "query": "What does ISO 55001 say about risk management?",
            "expect": "ISO definitions and clauses",
            "mode": "knowledge"
        },
        {
            "id": 5,
            "category": "HALLUCINATION_CHECK",
            "query": "How many flux capacitors in the database?",
            "expect": "Zero / No results found",
            "mode": "structured"
        },
        {
            "id": 6,
            "category": "STRATEGY",
            "query": "Recommend a maintenance strategy for High Criticality assets in Poor condition",
            "expect": "Specific actionable advice citing ISO",
            "mode": "analytical"
        },
        {
            "id": 7,
            "category": "FILTERING",
            "query": "List all Fire assets created by 'Precise Fire'",
            "expect": "List of assets filtered by category and source",
            "mode": "structured"
        },
        {
            "id": 8,
            "category": "AMBIGUITY",
            "query": "Assess the state of our infrastructure",
            "expect": "General overview or clarification request",
            "mode": "analytical" 
        },
        {
            "id": 9,
            "category": "ISO_MAPPING",
            "query": "What are the requirements for an Asset Management Plan?",
            "expect": "Reference to ISO 55002 / AMP elements",
            "mode": "knowledge"
        },
        {
            "id": 10,
            "category": "DATA_INTEGRITY",
            "query": "Show me assets with replacement cost over $1",
            "expect": "List of assets with costs",
            "mode": "analytical"
        },
        # NEW: 5 Edge Cases
        {
            "id": 11,
            "category": "DATE_RANGE",
            "query": "How many assets are over 20 years old?",
            "expect": "Count of aged assets",
            "mode": "analytical"
        },
        {
            "id": 12,
            "category": "NEGATION",
            "query": "List assets that are not in Critical condition",
            "expect": "Assets excluding Critical",
            "mode": "structured"
        },
        {
            "id": 13,
            "category": "MULTI_FILTER",
            "query": "Count High criticality electrical assets in Poor condition",
            "expect": "Combined filters: criticality + category + condition",
            "mode": "analytical"
        },
        {
            "id": 14,
            "category": "AGGREGATION",
            "query": "What is the average age of HVAC assets?",
            "expect": "Statistical aggregation",
            "mode": "analytical"
        },
        {
            "id": 15,
            "category": "LOCATION_HIERARCHY",
            "query": "How many assets are in Building A?",
            "expect": "Location-based count",
            "mode": "structured"
        }
    ]

    score_card = []
    
    for sc in scenarios:
        log("\n" + "="*80)
        log(f"SCENARIO #{sc['id']}: {sc['category']}")
        log(f"QUERY: {sc['query']}")
        log(f"EXPECT: {sc['expect']}")
        
        t0 = time.time()
        
        # Check Mode Detection
        try:
            detected_mode = engine.structured_query_detector.detect_query_mode(sc['query']) if engine.structured_query_detector else "UNKNOWN"
            log(f"MODE DETECTED: {detected_mode}")
        except Exception as e:
            log(f"MODE DETECT ERROR: {e}")
            detected_mode = "ERROR"
        
        # Run Query
        try:
            result = engine.query(sc['query'], asset_index, iso_kb)
            duration = time.time() - t0
            
            answer = str(result.get('answer', 'NO ANSWER'))
            model_used = result.get('model', 'Unknown')
            citations = result.get('citations', [])
            citation_count = len(citations) if isinstance(citations, list) else 0
            
            log(f"TIME: {duration:.2f}s")
            log(f"MODEL: {model_used}")
            log(f"CITATIONS: {citation_count}")
            log("-" * 40)
            log(f"ANSWER PREVIEW:\n{answer[:300]}...")
            log("-" * 40)
            
            # Grading
            passed_mode = (detected_mode == sc['mode']) or \
                          (sc['mode'] == 'analytical' and detected_mode in ['structured', 'knowledge'])
            
            has_answer = len(answer) > 10
            
            grade = "PASS"
            notes = []
            
            if not passed_mode:
                grade = "WARN"
                notes.append(f"Mode mismatch: {detected_mode} vs {sc['mode']}")
            
            if not has_answer:
                grade = "FAIL"
                notes.append("Empty answer")
                
            if sc['category'] == 'HALLUCINATION_CHECK':
                 if "0" in answer or "no assets" in answer.lower() or "not find" in answer.lower() or "couldn't find" in answer.lower():
                     grade = "PASS"
                 else:
                     grade = "FAIL"
                     notes.append("Hallucination detected")

            log(f"JUDGMENT: {grade} {' (' + ', '.join(notes) + ')' if notes else ''}")
            score_card.append({"id": sc['id'], "grade": grade})
            
        except Exception as e:
            log(f"[CRASH] {e}")
            traceback.print_exc()
            score_card.append({"id": sc['id'], "grade": "CRASH"})

    # Final Report
    log("\n" + "="*80)
    log("FINAL AUDIT REPORT")
    log("="*80)
    
    passed = sum(1 for s in score_card if s['grade'] == "PASS")
    warned = sum(1 for s in score_card if s['grade'] == "WARN")
    crashed = sum(1 for s in score_card if s['grade'] == "CRASH")
    total = len(scenarios)
    
    # Scoring: PASS=10, WARN=5, FAIL=0, CRASH=-10
    raw = (passed * 10) + (warned * 5) - (crashed * 10)
    max_score = total * 10
    final = max(0, min(100, (raw / max_score) * 100))
    
    log(f"SCENARIOS: {total}")
    log(f"PASSED:    {passed}")
    log(f"WARNED:    {warned}")
    log(f"FAILED:    {total - passed - warned - crashed}")
    log(f"CRASHED:   {crashed}")
    log(f"\nFINAL SCORE: {final:.1f}/100")

    if final >= 95:
        log("VERDICT: ISO CERTIFIED (EXCELLENT)")
    elif final >= 90:
        log("VERDICT: ISO CERTIFIED (HIGH ASSURANCE)")
    elif final >= 70:
        log("VERDICT: COMPLIANT WITH OBSERVATIONS")
    else:
        log("VERDICT: NON-CONFORMANCE DETECTED")

if __name__ == "__main__":
    run_stress_test()
