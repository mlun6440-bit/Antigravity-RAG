#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Embeddings Script
==========================
Generates embeddings for the dummy ISO knowledge base so RRF can work.
"""

import os
import json
import sys

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

from iso_embedding_manager import ISOEmbeddingManager

def main():
    kb_file = os.path.join(os.path.dirname(__file__), 'data', 'iso_knowledge_base.json')
    
    if not os.path.exists(kb_file):
        print(f"[ERROR] KB file not found: {kb_file}")
        return

    print(f"[INFO] Loading knowledge base from {kb_file}...")
    with open(kb_file, 'r', encoding='utf-8') as f:
        kb = json.load(f)
    
    chunks = kb.get('all_chunks', [])
    print(f"[INFO] Found {len(chunks)} chunks.")
    
    manager = ISOEmbeddingManager()
    
    print("[INFO] Generating embeddings...")
    updated_chunks = manager.add_embeddings_to_chunks(chunks)
    
    # Save back
    kb['all_chunks'] = updated_chunks
    with open(kb_file, 'w', encoding='utf-8') as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
        
    print(f"[SUCCESS] Saved {len(updated_chunks)} chunks with embeddings to {kb_file}")

if __name__ == "__main__":
    main()
