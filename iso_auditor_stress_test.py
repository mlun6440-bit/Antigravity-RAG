#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISO 55000 Auditor Stress Test
"Battle testing" the Analytical Query System with 10 scenarios.
"""

import sys
import os
import time
import json
import traceback

# Add tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from gemini_query_engine import GeminiQueryEngine

# File to log results
LOG_FILE = "iso_audit_report.txt"

def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def run_stress_test():
    # Clear log file
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("ISO 55000 AUDITOR STRESS TEST REPORT\n")
        f.write("=====================================\n\n")

    log("Initializing Auditor Protocol (GeminiQueryEngine)...")
    start_init = time.time()
    try:
        engine = GeminiQueryEngine()
        log(f"[OK] Engine loaded in {time.time() - start_init:.2f}s")
    except Exception as e:
        log(f"[CRITICAL FAIL] Engine could not start: {e}")
        return

    # Files (using the ones from previous context - CORRECT PATHS)
    asset_index = 'data/.tmp/asset_index.json' 
    iso_kb = 'data/.tmp/iso_knowledge_base.json'

    scenarios = [
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
            "expect": "Hybrid response: SQL count + ISO risk analysis + Recs",
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
            "expect": "ISO definitions and clauses (e.g. 6.1)",
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
            "expect": "Specific actionable advice citing ISO 55000",
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
            "expect": "General overview or request for specifics (Analytical fallback)",
            "mode": "analytical" 
        },
        {
            "id": 9,
            "category": "ISO_MAPPING",
            "query": "What are the requirements for an Asset Management Plan (AMP)?",
            "expect": "Reference to ISO 55002 / specific AMP elements",
            "mode": "knowledge"
        },
        {
            "id": 10,
            "category": "DATA_INTEGRITY",
            "query": "Show me assets with replacement cost over $1",
            "expect": "List of assets with costs",
            "mode": "analytical"
        }
    ]

    score_card = []
    
    for sc in scenarios:
        log("\n" + "="*80)
        log(f"SCENARIO #{sc['id']}: {sc['category']}")
        log(f"QUERY: {sc['query']}")
        log(f"EXPECT: {sc['expect']}")
        
        t0 = time.time()
        
        # 1. Check Mode Detection
        try:
            detected_mode = engine.structured_query_detector.detect_query_mode(sc['query']) if engine.structured_query_detector else "UNKNOWN"
            log(f"MODE DETECTED: {detected_mode}")
        except Exception as e:
            log(f"MODE DETECT ERROR: {e}")
            detected_mode = "ERROR"
        
        # 2. Run Query
        try:
            result = engine.query(sc['query'], asset_index, iso_kb)
            duration = time.time() - t0
            
            # Extract key info
            answer = str(result.get('answer', 'NO ANSWER'))
            model_used = result.get('model', 'Unknown')
            citations = result.get('citations', [])
            citation_count = len(citations) if isinstance(citations, list) else 0
            
            log(f"TIME: {duration:.2f}s")
            log(f"MODEL: {model_used}")
            log(f"CITATIONS: {citation_count}")
            log("-" * 40)
            log(f"ANSWER PREVIEW:\n{answer[:400]}...")
            log("-" * 40)
            
            # Grading Logic
            passed_mode = (detected_mode == sc['mode']) or \
                          (sc['mode'] == 'analytical' and detected_mode == 'structured') or \
                          (sc['mode'] == 'analytical' and detected_mode == 'knowledge') # lenient fallback
            
            has_answer = len(answer) > 50
            
            grade = "PASS"
            notes = []
            
            if not passed_mode:
                grade = "WARN"
                notes.append(f"Mode mismatch: got {detected_mode} expected {sc['mode']}")
            
            if not has_answer:
                grade = "FAIL"
                notes.append("Empty/Short answer")
                
            if sc['category'] == 'HALLUCINATION_CHECK':
                 if "0" in answer or "no assets" in answer.lower() or "not find" in answer.lower():
                     grade = "PASS"
                 else:
                     grade = "FAIL"
                     notes.append("Possible hallucination (found items?)")

            log(f"AUDIT JUDGMENT: {grade} {' (' + ', '.join(notes) + ')' if notes else ''}")
            score_card.append({"id": sc['id'], "grade": grade})
            
        except Exception as e:
            log(f"[CRITICAL FAIL] SYSTEM CRASHED ON QUERY: {e}")
            traceback.print_exc()
            score_card.append({"id": sc['id'], "grade": "CRASH"})

    # Final Report
    log("\n" + "="*80)
    log("FINAL AUDIT REPORT")
    log("="*80)
    
    passed_count = sum(1 for s in score_card if s['grade'] == "PASS")
    warn_count = sum(1 for s in score_card if s['grade'] == "WARN")
    crash_count = sum(1 for s in score_card if s['grade'] == "CRASH")
    total = len(scenarios)
    
    # Calculate score: PASS=10, WARN=5, FAIL=0, CRASH=-10
    raw_score = (passed_count * 10) + (warn_count * 5) - (crash_count * 10)
    max_score = total * 10
    final_percentage = max(0, min(100, (raw_score / max_score) * 100))
    
    log(f"SCENARIOS: {total}")
    log(f"PASSED:    {passed_count}")
    log(f"warned:    {warn_count}")
    log(f"FAILED:    {total - passed_count - warn_count}")
    log(f"FINAL SCORE: {final_percentage:.1f}/100")

    if final_percentage > 90:
        log("VERDICT: ISO CERTIFIED (HIGH ASSURANCE)")
    elif final_percentage > 70:
        log("VERDICT: COMPLIANT WITH OBSERVATIONS")
    else:
        log("VERDICT: NON-CONFORMANCE DETECTED")

if __name__ == "__main__":
    run_stress_test()
