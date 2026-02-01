#!/usr/bin/env python3
# Demo of the system capabilities
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("\n" + "="*70)
print("=== ASSET REGISTER ISO 55000 SPECIALIST v2.0 - DEMO ===")
print("="*70)

print("\nSYSTEM STATUS:")
print("-" * 70)

# Check dependencies
try:
    import google.generativeai as genai
    print("✓ Google Generative AI: Installed")
except:
    print("✗ Google Generative AI: Not installed")

try:
    import pandas
    print("✓ Pandas: Installed")
except:
    print("✗ Pandas: Not installed")

try:
    import pdfplumber
    print("✓ PDFPlumber: Installed")
except:
    print("✗ PDFPlumber: Not installed")

# Check files
import os
files_to_check = {
    'credentials.json': 'OAuth Credentials',
    'token.pickle': 'OAuth Token (WRITE access)',
    'data/.tmp/iso_knowledge_base.json': 'ISO Knowledge Base',
    'data/.tmp/ASISO55000-20241.pdf': 'ISO 55000 PDF',
    'data/.tmp/ASISO55001-20241.pdf': 'ISO 55001 PDF',
    'data/.tmp/ASISO55002-20241.pdf': 'ISO 55002 PDF',
}

print("\nFILES:")
print("-" * 70)
for file, desc in files_to_check.items():
    if os.path.exists(file):
        size = os.path.getsize(file)
        if size > 1024*1024:
            size_str = f"{size/(1024*1024):.1f} MB"
        elif size > 1024:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size} bytes"
        print(f"✓ {desc}: {size_str}")
    else:
        print(f"✗ {desc}: Not found")

# Check tools
print("\nTOOLS:")
print("-" * 70)
import sys
sys.path.insert(0, 'tools')

tools = [
    'citation_formatter',
    'command_parser',
    'asset_updater',
    'gemini_query_engine',
    'iso_pdf_parser',
    'asset_data_indexer',
    'drive_reader',
    'question_suggester'
]

for tool in tools:
    try:
        __import__(tool)
        print(f"✓ {tool}.py")
    except Exception as e:
        print(f"✗ {tool}.py: {e}")

# Test command parser
print("\nCOMMAND PARSER TEST:")
print("-" * 70)
try:
    from command_parser import CommandParser
    parser = CommandParser()

    test_commands = [
        "How many assets do we have?",
        "update asset A-001 condition to Poor",
        "change all Fair to Poor",
        "add new asset: Pump 6, Building C",
        "delete asset A-999"
    ]

    for cmd in test_commands:
        intent, params = parser.detect_intent(cmd)
        print(f"'{cmd[:40]}...' -> {intent}")

    print("✓ Command parser working!")
except Exception as e:
    print(f"✗ Command parser error: {e}")

# Test ISO KB
print("\nISO KNOWLEDGE BASE:")
print("-" * 70)
try:
    import json
    with open('data/.tmp/iso_knowledge_base.json', 'r', encoding='utf-8') as f:
        kb = json.load(f)

    print(f"✓ ISO Standards: {len(kb.get('standards', {}))}")
    print(f"✓ Total Chunks: {len(kb.get('all_chunks', []))}")

    for std_name, std_data in kb.get('standards', {}).items():
        print(f"  - {std_name}: {std_data.get('chunk_count', 0)} chunks")
except Exception as e:
    print(f"✗ ISO KB error: {e}")

print("\n" + "="*70)
print("SYSTEM READY!")
print("="*70)

print("\nWHAT YOU CAN DO:")
print("1. Double-click: start.bat")
print("2. Or manually run: py run_asset_specialist.py --interactive")
print("\nThen ask:")
print("- 'What is ISO 55000?'")
print("- 'According to ISO 55001, how should I manage assets?'")
print("- 'update asset A-001 condition to Poor' (CRUD)")
print("- 'suggest' (for question ideas)")

print("\n" + "="*70)
print("Press any key to exit...")
input()
