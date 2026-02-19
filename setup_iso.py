#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
from iso_pdf_parser import ISOPDFParser

def main():
    print("=== Setting up ISO 55000 Knowledge Base ===")
    
    # Paths
    data_dir = 'data/.tmp'
    iso_kb_file = os.path.join(data_dir, 'iso_knowledge_base.json')
    
    # Define PDF files
    request_pdfs = [
        {'path': os.path.join(data_dir, 'ASISO55000-20241.pdf'), 'standard': 'ISO 55000'},
        {'path': os.path.join(data_dir, 'ASISO55001-20241.pdf'), 'standard': 'ISO 55001'},
        {'path': os.path.join(data_dir, 'ASISO55002-20241.pdf'), 'standard': 'ISO 55002'}
    ]
    
    # Verify files exist
    valid_pdfs = []
    for pdf in request_pdfs:
        if os.path.exists(pdf['path']):
            print(f"[OK] Found {pdf['standard']}: {pdf['path']}")
            valid_pdfs.append(pdf)
        else:
            print(f"[WARN] Missing {pdf['standard']}: {pdf['path']}")
            
    if not valid_pdfs:
        print("[ERROR] No ISO PDFs found!")
        return

    # Parse
    print("\nParsing PDFs...")
    try:
        parser = ISOPDFParser()
        parser.create_knowledge_base(
            pdf_files=valid_pdfs,
            output_file=iso_kb_file
        )
        print(f"\n[OK] ISO Knowledge Base created at: {iso_kb_file}")
            
    except Exception as e:
        print(f"\n[ERROR] Failed to parse ISO PDFs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
