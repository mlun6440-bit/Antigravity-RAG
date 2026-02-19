import sys
import os
import logging
import sqlite3
import numpy as np

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.memory_manager import MemoryManager
from tools.embedding_manager import EmbeddingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_and_backfill():
    print("=== Fixing Memory Schema and Backfilling Embeddings ===")
    
    # 1. Initialize MemoryManager (triggers schema migration)
    try:
        mm = MemoryManager()
        print("[OK] MemoryManager initialized (schema check complete)")
    except Exception as e:
        print(f"[ERROR] Failed to initialize MemoryManager: {e}")
        return

    # 2. Check if EmbeddingManager is available
    if not mm.embedding_manager:
        print("[ERROR] EmbeddingManager not available. Cannot backfill.")
        try:
             mm.embedding_manager = EmbeddingManager()
             print("[OK] EmbeddingManager manually initialized")
        except Exception as e:
             print(f"[ERROR] Could not initialize EmbeddingManager: {e}")
             return

    # 3. Backfill missing embeddings
    db_path = mm.db_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get rows needing embeddings
    try:
        cursor.execute("SELECT id, question, answer FROM exchanges WHERE embedding IS NULL")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"[ERROR] Could not select from exchanges: {e}")
        conn.close()
        return

    print(f"Found {len(rows)} exchanges missing embeddings.")
    
    count = 0
    for row_id, question, answer in rows:
        try:
            text_to_embed = f"Q: {question}\nA: {answer}"
            vec = mm.embedding_manager.generate_embedding(text_to_embed)
            
            if vec:
                # Convert to blob
                blob = np.array(vec, dtype=np.float32).tobytes()
                
                cursor.execute(
                    "UPDATE exchanges SET embedding = ? WHERE id = ?",
                    (blob, row_id)
                )
                count += 1
                if count % 5 == 0:
                    print(f"Backfilled {count}/{len(rows)}...")
        except Exception as e:
            print(f"[WARN] Failed to embed row {row_id}: {e}")

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Backfilled {count} embeddings.")

if __name__ == "__main__":
    fix_and_backfill()
