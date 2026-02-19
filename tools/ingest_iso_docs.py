#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISO Document Ingestion Script v2
=================================
Parses ISO PDFs, chunks by ~800 chars with overlap,
detects section headers, generates embeddings, and saves KB.
"""

import os
import sys
import glob
import json
import re
import time
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        print("[ERROR] pypdf missing. Run: pip install pypdf")
        sys.exit(1)

try:
    from tools.iso_embedding_manager import ISOEmbeddingManager
except ImportError:
    from iso_embedding_manager import ISOEmbeddingManager

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
DOCS_DIR = os.path.join(DATA_DIR, 'iso_docs')
KB_FILE = os.path.join(DATA_DIR, 'iso_knowledge_base.json')

CHUNK_SIZE = 800  # chars per chunk
CHUNK_OVERLAP = 150  # overlap between chunks
MAX_EMBED_TEXT = 2000  # max chars sent to embedding API


def clean_text(text: str) -> str:
    """Remove noise from extracted text."""
    # Remove page numbers / headers (e.g. "vii", "7", "Page 1 of 5")
    text = re.sub(r'Page \d+\s*(of\s*\d+)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE) # Standalone page numbers
    text = re.sub(r'^[ivx]+\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE) # Roman numerals
    
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove copyright lines and footer noise
    text = re.sub(r'©\s*Standards Australia.*?(?:\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'AS\s*ISO\s*55\d{3}:\d{4}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Australian Standard®', '', text)
    
    return text.strip()


def detect_section(text: str, prev_section: str, prev_title: str):
    """Try to find a section header like '4.1 Understanding...' or '3.2.1 Asset'."""
    # 1. Look for standard section headers: "4.1 Title"
    match = re.search(r'(?:^|\n)\s*(\d+(?:\.\d+)+)\s+([A-Z][A-Za-z\s,\-\(\)]+)(?:\n|$)', text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
        
    # 2. Look for standalone section numbers like "3.2.1" (common in definitions)
    # followed typically by the term name on the next line
    match_num = re.search(r'(?:^|\n)\s*(\d+(?:\.\d+)+)\s*(?:\n|$)', text)
    if match_num:
        # Try to find the title on the next non-empty line
        sec_num = match_num.group(1).strip()
        # Find where this match ends
        end_pos = match_num.end()
        remaining = text[end_pos:]
        # Find next line
        title_match = re.search(r'^\s*([A-Z][a-zA-Z\s\-\(\)]+)', remaining, re.MULTILINE)
        if title_match:
            return sec_num, title_match.group(1).strip()
        return sec_num, "Definition" # Fallback title
        
    return prev_section, prev_title


def chunk_text(full_text: str, filename: str) -> List[Dict[str, Any]]:
    """Split text into overlapping chunks with section detection."""
    chunks = []
    current_section = "0"
    current_title = "General"

    # Split into paragraphs/blocks
    # ISO standards often have double newlines between clauses
    paragraphs = re.split(r'\n\s*\n', full_text)

    buffer = ""
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 5: # Skip tiny noise
            continue

        # Detect section headers
        sec, title = detect_section(para, current_section, current_title)
        
        # If section changed, we might want to start a new chunk to alignment
        if sec != current_section:
            # Check depth change (e.g. 4.1 -> 4.2 is big, 4.1 -> 4.1.1 is small)
            # For now, just flush if buffer is substantial
            if len(buffer) > 200:
                chunks.append({
                    "chunk_id": f"{filename}_c{chunk_idx}",
                    "iso_standard": filename.replace('.pdf', ''),
                    "section_number": current_section,
                    "section_title": current_title,
                    "title": current_title,
                    "text": buffer.strip()[:MAX_EMBED_TEXT],
                    "page_range": "N/A",
                    "source_file": filename
                })
                chunk_idx += 1
                buffer = buffer[-CHUNK_OVERLAP:] if len(buffer) > CHUNK_OVERLAP else ""
            
            current_section = sec
            current_title = title

        buffer += "\n\n" + para

        # If buffer exceeds chunk size, flush
        if len(buffer) >= CHUNK_SIZE:
             # Try to find a natural break point (end of sentence)
            break_point = buffer.rfind('.', 0, CHUNK_SIZE)
            if break_point == -1 or break_point < CHUNK_SIZE * 0.5:
                break_point = CHUNK_SIZE
            else:
                break_point += 1 # Include the dot
                
            chunk_text = buffer[:break_point].strip()
            
            chunks.append({
                "chunk_id": f"{filename}_c{chunk_idx}",
                "iso_standard": filename.replace('.pdf', ''),
                "section_number": current_section,
                "section_title": current_title,
                "title": current_title,
                "text": chunk_text[:MAX_EMBED_TEXT],
                "page_range": "N/A",
                "source_file": filename
            })
            chunk_idx += 1
            # Keep overlap
            buffer = buffer[break_point - CHUNK_OVERLAP:] if break_point > CHUNK_OVERLAP else ""

    # Flush remaining
    if buffer.strip() and len(buffer.strip()) > 50:
        chunks.append({
            "chunk_id": f"{filename}_c{chunk_idx}",
            "iso_standard": filename.replace('.pdf', ''),
            "section_number": current_section,
            "section_title": current_title,
            "title": current_title,
            "text": buffer.strip()[:MAX_EMBED_TEXT],
            "page_range": "N/A",
            "source_file": filename
        })

    return chunks


def extract_all_text(filepath: str) -> str:
    """Extract all text from a PDF."""
    reader = PdfReader(filepath)
    all_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            all_text.append(clean_text(text))
    return "\n\n".join(all_text)


def main():
    print("=" * 60)
    print("ISO Document Ingestion v2")
    print("=" * 60)
    print(f"Looking for PDFs in: {DOCS_DIR}")

    os.makedirs(DOCS_DIR, exist_ok=True)

    pdf_files = sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf")))

    if not pdf_files:
        print(f"\n[WARNING] No PDF files found in {DOCS_DIR}")
        return

    print(f"[INFO] Found {len(pdf_files)} PDFs")

    all_chunks = []
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"\n[INFO] Processing {filename}...")

        full_text = extract_all_text(pdf_path)
        if len(full_text) < 100:
            print(f"  [WARN] Very little text extracted ({len(full_text)} chars). Scanned PDF?")
            continue

        print(f"  [OK] Extracted {len(full_text)} chars")

        chunks = chunk_text(full_text, filename)
        print(f"  [OK] Created {len(chunks)} chunks")

        # Show section distribution
        sections = set(c['section_number'] for c in chunks)
        print(f"  [OK] Sections found: {sorted(sections)}")

        all_chunks.extend(chunks)

    if not all_chunks:
        print("[ERROR] No chunks created.")
        return

    print(f"\n[INFO] Total chunks: {len(all_chunks)}")
    print("[INFO] Generating embeddings (this takes ~1 min)...")

    try:
        manager = ISOEmbeddingManager()

        # Generate embeddings with rate limiting
        success_count = 0
        fail_count = 0
        for i, chunk in enumerate(all_chunks):
            text_to_embed = f"{chunk['title']}\n{chunk['text']}"
            text_to_embed = text_to_embed[:MAX_EMBED_TEXT]

            try:
                embedding = manager.generate_embedding(text_to_embed, task_type="retrieval_document")
                non_zero = sum(1 for x in embedding if x != 0.0)
                if non_zero > 0:
                    chunk['embedding'] = embedding.tolist()
                    success_count += 1
                else:
                    chunk['embedding'] = []
                    fail_count += 1
                    print(f"  [WARN] Zero embedding for chunk {i}")
            except Exception as e:
                chunk['embedding'] = []
                fail_count += 1
                print(f"  [ERROR] Embedding failed for chunk {i}: {e}")

            # Rate limiting: ~1 request per 0.2s to stay under API limits
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(all_chunks)}] embeddings generated...")
                time.sleep(0.5)

        print(f"\n[RESULTS] Embeddings: {success_count} success, {fail_count} failed")

        # Save
        kb = {
            "all_chunks": all_chunks,
            "embedding_metadata": {
                "model": manager.embedding_model,
                "version": manager.embedding_version,
                "dimension": manager.embedding_dimension,
                "total_chunks": len(all_chunks),
                "successful_embeddings": success_count,
                "failed_embeddings": fail_count
            }
        }

        with open(KB_FILE, 'w', encoding='utf-8') as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)

        print(f"\n[SUCCESS] Knowledge Base saved to: {KB_FILE}")
        print(f"  Chunks: {len(all_chunks)}")
        print(f"  Embeddings: {success_count}/{len(all_chunks)}")
        print(f"\nRun 'python tools/eval_rag.py' to benchmark retrieval.")

    except Exception as e:
        print(f"[ERROR] {e}")
        # Save without embeddings as backup
        with open(KB_FILE, 'w', encoding='utf-8') as f:
            json.dump({"all_chunks": all_chunks}, f, indent=2)
        print(f"[INFO] Saved raw chunks (no embeddings) to {KB_FILE}")


if __name__ == "__main__":
    main()
