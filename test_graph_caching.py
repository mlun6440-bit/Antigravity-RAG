import time
import os
import sys

# Add parent directory to path
sys.path.append(os.getcwd())

from tools.knowledge_graph import KnowledgeGraphEngine

def test_caching():
    print("=== Testing Knowledge Graph Caching ===")
    
    engine = KnowledgeGraphEngine()
    
    # 1. First build (Force rebuild to ensure cache is created)
    print("\n[1] Building from DB (Cache Miss/Force)...")
    t0 = time.time()
    stats1 = engine.build_graph(force_refresh=True)
    t1 = time.time()
    print(f"Time: {t1-t0:.2f}s")
    print(f"Stats: {stats1['total_nodes']} nodes, {stats1['total_edges']} edges")
    print(f"Loaded from cache? {stats1.get('loaded_from_cache', False)}")

    # 2. Second build (Should hit cache)
    print("\n[2] Building from Cache...")
    t2 = time.time()
    stats2 = engine.build_graph()
    t3 = time.time()
    print(f"Time: {t3-t2:.2f}s")
    print(f"Stats: {stats2['total_nodes']} nodes, {stats2['total_edges']} edges")
    print(f"Loaded from cache? {stats2.get('loaded_from_cache', False)}")
    
    if stats2.get('loaded_from_cache'):
        print("\nSUCCESS: Graph loaded from cache!")
        speedup = (t1-t0) / (t3-t2) if (t3-t2) > 0 else 0
        print(f"Speedup: {speedup:.1f}x")
    else:
        print("\nFAILURE: Graph did not load from cache.")

if __name__ == "__main__":
    test_caching()
