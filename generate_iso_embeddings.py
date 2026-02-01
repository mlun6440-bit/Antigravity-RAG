#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Embeddings for ISO Knowledge Base
One-time script to add vector embeddings to existing ISO chunks.
"""

import os
import sys
import json

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from iso_embedding_manager import ISOEmbeddingManager


def main():
    """Generate embeddings for ISO knowledge base."""
    print("\n" + "="*70)
    print("=== Generating Vector Embeddings for ISO Knowledge Base ===")
    print("="*70 + "\n")

    # Paths
    kb_file = 'data/.tmp/iso_knowledge_base.json'

    # Check if KB exists
    if not os.path.exists(kb_file):
        print(f"[ERROR] Knowledge base not found: {kb_file}")
        print("Please run setup first: py run_asset_specialist.py --setup")
        sys.exit(1)

    # Load existing knowledge base
    print(f"[INFO] Loading knowledge base from {kb_file}...")
    with open(kb_file, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    chunks = kb.get('all_chunks', [])
    print(f"[OK] Loaded {len(chunks)} chunks")

    if not chunks:
        print("[ERROR] No chunks found in knowledge base")
        sys.exit(1)

    # Check if embeddings already exist
    chunks_with_embeddings = sum(1 for chunk in chunks if 'embedding' in chunk)
    if chunks_with_embeddings > 0:
        print(f"[INFO] {chunks_with_embeddings}/{len(chunks)} chunks already have embeddings")

        response = input("Regenerate all embeddings? (y/N): ").strip().lower()
        force_regenerate = response == 'y'
    else:
        force_regenerate = False

    # Initialize embedding manager
    print("\n[INFO] Initializing embedding manager...")
    try:
        manager = ISOEmbeddingManager()
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    # Add embeddings to chunks
    print(f"\n[INFO] Generating embeddings for ISO chunks...")
    print(f"  Model: text-embedding-004 (768 dimensions)")
    print(f"  Estimated cost: ~$0.0015 (less than 1 penny)\n")

    updated_chunks = manager.add_embeddings_to_chunks(chunks, force_regenerate=force_regenerate)

    # Save updated knowledge base
    kb['all_chunks'] = updated_chunks

    # Update standards too
    for standard_name, standard_data in kb.get('standards', {}).items():
        standard_chunks = []
        for chunk in updated_chunks:
            if chunk.get('iso_standard') == standard_name:
                standard_chunks.append(chunk)
        standard_data['chunks'] = standard_chunks

    # Add embedding metadata
    kb['embedding_metadata'] = {
        'model': 'text-embedding-004',
        'dimension': 768,
        'total_chunks': len(updated_chunks),
        'chunks_with_embeddings': sum(1 for chunk in updated_chunks if 'embedding' in chunk)
    }

    # Save
    print(f"\n[INFO] Saving updated knowledge base...")
    with open(kb_file, 'w', encoding='utf-8') as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print("[OK] SUCCESS! Vector embeddings generated and saved")
    print("="*70)
    print(f"\nKnowledge base: {kb_file}")
    print(f"Total chunks: {len(updated_chunks)}")
    print(f"Chunks with embeddings: {kb['embedding_metadata']['chunks_with_embeddings']}")
    print("\nYour system is now ready for semantic search!")
    print("Restart the web server to use vector search for ISO queries.\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
