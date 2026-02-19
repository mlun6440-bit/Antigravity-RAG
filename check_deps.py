try:
    import faiss
    print("FAISS available")
except ImportError:
    print("FAISS missing")

try:
    import rank_bm25
    print("rank_bm25 available")
except ImportError:
    print("rank_bm25 missing")
