#!/usr/bin/env python3
# Quick test of ISO knowledge base
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from iso_pdf_parser import ISOPDFParser

print("Testing ISO Knowledge Base...")
print("=" * 70)

kb_file = 'data/.tmp/iso_knowledge_base.json'
if os.path.exists(kb_file):
    import json
    with open(kb_file, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    print(f"\nISO Knowledge Base Loaded Successfully!")
    print(f"Total standards: {len(kb.get('standards', {}))}")
    print(f"Total chunks: {len(kb.get('all_chunks', []))}")

    print("\nSample ISO content:")
    for i, chunk in enumerate(kb.get('all_chunks', [])[:3], 1):
        print(f"\n{i}. {chunk.get('iso_standard', '')} - Section {chunk.get('section_number', '')}")
        print(f"   Title: {chunk.get('section_title', '')}")
        print(f"   Pages: {chunk.get('page_range', '')}")
        print(f"   Preview: {chunk.get('content', '')[:150]}...")

    print("\n" + "=" * 70)
    print("System is ready! You can ask ISO 55000 questions.")
    print("\nTo start interactive mode, run: start.bat")
    print("Or manually: py run_asset_specialist.py --interactive")
else:
    print("Knowledge base not found. Run setup first.")
