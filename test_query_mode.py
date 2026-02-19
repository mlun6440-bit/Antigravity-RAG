#!/usr/bin/env python3
"""Test query mode detection"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from structured_query_detector import StructuredQueryDetector

def test_query_mode_detection():
    """Test the 3-way query mode detection."""
    detector = StructuredQueryDetector()
    
    test_cases = [
        # Structured queries (count/list only)
        ("How many Precise Air assets", "structured"),
        ("Count assets by category", "structured"),
        ("Total number of fire systems", "structured"),
        ("List all electrical equipment", "structured"),
        
        # Analytical queries (analysis + data)
        ("Analyze my poor condition electrical assets per ISO 55001", "analytical"),
        ("Assess critical fire systems for AS 1851 compliance", "analytical"),
        ("Evaluate assets over 20 years old for replacement priority", "analytical"),
        ("Review high risk HVAC systems according to ISO 55000", "analytical"),
        ("What should I prioritize for poor condition assets", "analytical"),
        
        # Knowledge queries (no data filter)
        ("What is ISO 55001", "knowledge"),
        ("Explain asset management best practices", "knowledge"),
        ("Define preventive maintenance", "knowledge"),
        ("How does ISO 55000 framework work", "knowledge"),
        ("What are the ISO 55001 requirements", "knowledge"),
    ]
    
    print("="*70)
    print("QUERY MODE DETECTION TEST")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for query, expected_mode in test_cases:
        detected_mode = detector.detect_query_mode(query)
        status = "✓ PASS" if detected_mode == expected_mode else "✗ FAIL"
        
        if detected_mode == expected_mode:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"  Query: {query}")
        print(f"  Expected: {expected_mode}")
        print(f"  Got: {detected_mode}")
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*70)
    
    return failed == 0

if __name__ == "__main__":
    success = test_query_mode_detection()
    sys.exit(0 if success else 1)
