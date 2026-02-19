#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persistent Memory Manager
==========================
Two-layer memory system for the Asset Management RAG:

Layer 1 — Raw exchanges (SQLite)
    Every Q&A turn stored permanently.
    Queryable history: "what did I ask about last week?"

Layer 2 — Extracted insights (Gemini summary)
    After each session Gemini distils key facts:
      "User focused on Building A, HVAC compliance gaps, flagged 12 critical assets"
    Injected as a compact context block on next session startup.

Schema:
    sessions        — one row per browser session
    exchanges       — every Q&A turn, linked to a session
    memory_insights — Gemini-extracted facts, persisted across sessions
"""

import json
import os
import sqlite3
import time
import numpy as np
import logging
import warnings
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ── Gemini (optional — degrades gracefully) ───────────────────────────────────
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()

try:
    from tools.embedding_manager import EmbeddingManager
except ImportError:
    EmbeddingManager = None

# ─────────────────────────────────────────────────────────────────────────────

class MemoryManager:
    """
    Persistent conversation memory backed by a dedicated SQLite database.
    Completely separate from assets.db to avoid polluting asset data.
    """

    def __init__(self, db_path: str = None, model_name: str = "gemini-2.0-flash"):
        self.db_path = db_path or self._default_db_path()
        self.model_name = model_name
        self._init_db()

        # Initialize Embedding Manager for RAG
        self.embedding_manager = None
        if EmbeddingManager:
            try:
                self.embedding_manager = EmbeddingManager()
                logger.info("MemoryManager: Semantic Search (RAG) enabled")
            except Exception as e:
                logger.warning(f"MemoryManager: EmbeddingManager init failed: {e}")

        # Gemini for insight extraction
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.llm = None
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.llm = genai.GenerativeModel(model_name)
                logger.info("MemoryManager: Gemini insight extraction enabled")
            except Exception as e:
                logger.warning(f"MemoryManager: Gemini init failed ({e}); insights disabled")
        else:
            logger.info("MemoryManager: running without Gemini (raw storage only)")

        logger.info(f"MemoryManager initialized at {self.db_path}")

    # ── Helper: safe DB connection ────────────────────────────────────────────

    def _get_conn(self, row_factory: bool = False) -> sqlite3.Connection:
        """Create a new connection. Always use with `with` statement."""
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = sqlite3.Row
        return conn

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _default_db_path(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, 'data', 'memory.db')

    def _init_db(self):
        """Create tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id   TEXT PRIMARY KEY,
                    started_at   TEXT NOT NULL,
                    ended_at     TEXT,
                    turn_count   INTEGER DEFAULT 0,
                    summary      TEXT
                );

                CREATE TABLE IF NOT EXISTS exchanges (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id   TEXT NOT NULL,
                    turn_index   INTEGER NOT NULL,
                    timestamp    TEXT NOT NULL,
                    question     TEXT NOT NULL,
                    answer       TEXT NOT NULL,
                    route        TEXT,
                    intent       TEXT,
                    embedding    BLOB,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS memory_insights (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at   TEXT NOT NULL,
                    session_id   TEXT,
                    insight_type TEXT NOT NULL,
                    content      TEXT NOT NULL,
                    relevance    REAL DEFAULT 1.0
                );

                CREATE INDEX IF NOT EXISTS idx_exchanges_session
                    ON exchanges(session_id);
                CREATE INDEX IF NOT EXISTS idx_exchanges_timestamp
                    ON exchanges(timestamp);
                CREATE INDEX IF NOT EXISTS idx_insights_type
                    ON memory_insights(insight_type);
            """)
            
            # Check if embedding column exists (migration for existing DBs)
            try:
                conn.execute("SELECT embedding FROM exchanges LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("[MEMORY] Migrating DB: Adding 'embedding' column to exchanges")
                conn.execute("ALTER TABLE exchanges ADD COLUMN embedding BLOB")

    # ── Session management ────────────────────────────────────────────────────

    def start_session(self, session_id: str):
        """Register a new session (idempotent)."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO sessions (session_id, started_at)
                VALUES (?, ?)
            """, (session_id, datetime.utcnow().isoformat()))

    def end_session(self, session_id: str):
        """Mark session as ended and trigger insight extraction."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE sessions SET ended_at = ? WHERE session_id = ?
            """, (datetime.utcnow().isoformat(), session_id))
        # Extract insights in the background (non-blocking)
        self._extract_session_insights(session_id)

    # ── Exchange storage ──────────────────────────────────────────────────────

    def save_exchange(self, session_id: str, question: str, answer: str,
                      route: str = None, intent: str = None):
        """Save one Q&A turn."""
        
        # Generate embedding (if enabled)
        embedding_blob = None
        if self.embedding_manager:
            try:
                # Embed Q+A for better context retrieval
                text_to_embed = f"Q: {question}\nA: {answer}"
                vec = self.embedding_manager.generate_embedding(text_to_embed)
                if vec:
                    # Convert to numpy bytes for storage
                    embedding_blob = np.array(vec, dtype=np.float32).tobytes()
            except Exception as e:
                logger.warning(f"[MEMORY] Embedding generation failed: {e}")

        with self._get_conn() as conn:
            # Get current turn count
            row = conn.execute(
                "SELECT turn_count FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            turn_index = (row[0] if row else 0) + 1

            conn.execute("""
                INSERT INTO exchanges (session_id, turn_index, timestamp, question, answer, route, intent, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, turn_index,
                datetime.utcnow().isoformat(),
                question[:2000],
                answer[:4000],
                route or '',
                intent or '',
                embedding_blob
            ))
            conn.execute("""
                UPDATE sessions SET turn_count = ? WHERE session_id = ?
            """, (turn_index, session_id))
        logger.debug(f"[MEMORY] Saved turn {turn_index} for session {session_id[:8]}...")

    # ── Context retrieval ─────────────────────────────────────────────────────

    def get_context_for_session(self, session_id: str, question: str = None, max_recent: int = 6) -> str:
        """
        Build a compact context string to inject into the next query prompt.
        Combines:
          - Persistent insights from all past sessions
          - Relevant past exchanges (Semantic Search / RAG)
          - Recent exchanges from the current session
        """
        parts = []

        # 1. Persistent insights (from previous sessions)
        insights = self._get_recent_insights(limit=5)
        if insights:
            parts.append("PERSISTENT MEMORY (from previous sessions):")
            for ins in insights:
                parts.append(f"  - [{ins['insight_type']}] {ins['content']}")
            parts.append("")
            
        # 2. Semantic Recall (RAG over History)
        # Search for similar questions/answers from past sessions
        if question and self.embedding_manager:
            similar_exchanges = self.search_similar_exchanges(
                query=question, 
                limit=3, 
                exclude_session_id=session_id
            )
            if similar_exchanges:
                parts.append("RELEVANT PAST CONVERSATIONS (Semantic Search):")
                for item in similar_exchanges:
                    parts.append(f"  [Date: {item['date']}]")
                    parts.append(f"  Q: {item['question']}")
                    parts.append(f"  A: {item['answer'][:300]}...") # Truncate answer
                parts.append("")

        # 3. Recent exchanges from this session
        recent = self._get_recent_exchanges(session_id, limit=max_recent)
        if recent:
            parts.append("CURRENT SESSION CONTEXT:")
            for ex in recent:
                q = ex['question'][:200]
                a = ex['answer'][:300]
                parts.append(f"  [USER]: {q}")
                parts.append(f"  [ASSISTANT]: {a}")
            parts.append("")

        if not parts:
            return ""

        parts.append("END OF MEMORY CONTEXT")
        return "\n".join(parts) + "\n\n"

    def get_memory_summary(self) -> Dict[str, Any]:
        """Return stats and recent insights for the UI."""
        with self._get_conn(row_factory=True) as conn:
            total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            total_exchanges = conn.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0]
            total_insights = conn.execute("SELECT COUNT(*) FROM memory_insights").fetchone()[0]

            recent_questions = conn.execute("""
                SELECT question, timestamp, route FROM exchanges
                ORDER BY timestamp DESC LIMIT 10
            """).fetchall()

            insights = conn.execute("""
                SELECT insight_type, content, created_at FROM memory_insights
                ORDER BY created_at DESC LIMIT 8
            """).fetchall()

        return {
            'total_sessions': total_sessions,
            'total_exchanges': total_exchanges,
            'total_insights': total_insights,
            'recent_questions': [
                {
                    'question': r['question'][:100],
                    'timestamp': r['timestamp'],
                    'route': r['route'],
                }
                for r in recent_questions
            ],
            'insights': [
                {
                    'type': i['insight_type'],
                    'content': i['content'][:200],
                    'created_at': i['created_at'],
                }
                for i in insights
            ],
        }

    def get_history(self, limit: int = 50) -> List[Dict]:
        """Return full exchange history for the history panel."""
        with self._get_conn(row_factory=True) as conn:
            rows = conn.execute("""
                SELECT e.question, e.answer, e.route, e.intent, e.timestamp, e.session_id
                FROM exchanges e
                ORDER BY e.timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ── Insight extraction ────────────────────────────────────────────────────

    def _extract_session_insights(self, session_id: str):
        """Use Gemini to distil key facts from a session into persistent insights."""
        if not self.llm:
            return

        exchanges = self._get_recent_exchanges(session_id, limit=20)
        if not exchanges:
            return

        # Build exchange text
        exchange_text = "\n".join([
            f"Q: {ex['question'][:200]}\nA: {ex['answer'][:300]}"
            for ex in exchanges
        ])

        prompt = f"""You are summarising a conversation session about asset management.
Extract 2-4 concise, factual insights from these exchanges that would be useful to remember
for future sessions. Focus on:
- Specific assets, buildings, or categories the user was investigating
- Problems or gaps identified (e.g. compliance gaps, poor condition clusters)
- Preferences shown (e.g. preferred grouping, focus areas)
- Key numbers or findings worth remembering

Exchanges:
{exchange_text}

Output ONLY a JSON array of objects, each with:
  "type": one of "focus_area", "finding", "preference", "action_item"
  "content": a single concise sentence (max 120 chars)

Example:
[
  {{"type": "focus_area", "content": "User frequently investigates Building 54500233 HVAC compliance"}},
  {{"type": "finding", "content": "50 critical assets have no compliance standard documented"}}
]

Output only valid JSON, no preamble."""

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=400,
                )
            )
            text = response.text.strip()
            # Strip markdown fences if present
            if text.startswith('```'):
                parts = text.split('```')
                text = parts[1] if len(parts) > 1 else text
                if text.startswith('json'):
                    text = text[4:]
            insights = json.loads(text.strip())

            with self._get_conn() as conn:
                for ins in insights:
                    if isinstance(ins, dict) and 'content' in ins:
                        conn.execute("""
                            INSERT INTO memory_insights (created_at, session_id, insight_type, content)
                            VALUES (?, ?, ?, ?)
                        """, (
                            datetime.utcnow().isoformat(),
                            session_id,
                            ins.get('type', 'finding'),
                            ins['content'][:300],
                        ))
            logger.info(f"[MEMORY] Extracted {len(insights)} insights from session {session_id[:8]}...")

        except Exception as e:
            logger.warning(f"[MEMORY] Insight extraction failed: {e}")

    def _get_recent_exchanges(self, session_id: str, limit: int = 6) -> List[Dict]:
        with self._get_conn(row_factory=True) as conn:
            rows = conn.execute("""
                SELECT question, answer, route, intent, timestamp
                FROM exchanges
                WHERE session_id = ?
                ORDER BY turn_index DESC
                LIMIT ?
            """, (session_id, limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def _get_recent_insights(self, limit: int = 5) -> List[Dict]:
        with self._get_conn(row_factory=True) as conn:
            rows = conn.execute("""
                SELECT insight_type, content, created_at
                FROM memory_insights
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ── Semantic Search (Memory RAG) ──────────────────────────────────────────

    def search_similar_exchanges(self, query: str, limit: int = 3, exclude_session_id: str = None) -> List[Dict]:
        """
        Search past exchanges for semantic similarity to the current query.
        Returns relevant Q&A pairs from history.
        """
        if not self.embedding_manager:
            return []

        try:
            query_embedding = self.embedding_manager.generate_query_embedding(query)
            if not query_embedding:
                return []
            
            # Fetch all embeddings from DB (optimized for small history < 10k)
            # For larger history, we would use a vector DB or FAISS
            with self._get_conn(row_factory=True) as conn:
                # Only fetch rows that HAVE an embedding
                sql = "SELECT id, question, answer, embedding, session_id, timestamp FROM exchanges WHERE embedding IS NOT NULL"
                params = []
                if exclude_session_id:
                    sql += " AND session_id != ?"
                    params.append(exclude_session_id)
                
                rows = conn.execute(sql, params).fetchall()
            
            if not rows:
                return []

            # Calculate cosine similarity
            # Convert blobs back to numpy arrays
            import numpy as np
            
            scores = []
            for row in rows:
                try:
                    emb_bytes = row['embedding']
                    emb_vec = np.frombuffer(emb_bytes, dtype=np.float32)
                    
                    # Compute similarity
                    similarity = np.dot(query_embedding, emb_vec) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb_vec))
                    scores.append((similarity, row))
                except Exception:
                    continue
            
            # Sort by similarity desc
            scores.sort(key=lambda x: x[0], reverse=True)
            
            # Return top K results
            results = []
            for score, row in scores[:limit]:
                if score > 0.65:  # Similarity threshold
                    results.append({
                        'question': row['question'],
                        'answer': row['answer'],
                        'similarity': score,
                        'date': row['timestamp'].split('T')[0]
                    })
            
            return results

        except Exception as e:
            logger.error(f"[MEMORY] Semantic search failed: {e}")
            return []


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    mm = MemoryManager()
    sid = 'test-session-001'
    mm.start_session(sid)

    mm.save_exchange(sid,
        "Which critical assets lack ISO compliance documentation?",
        "Found 50 critical/high assets with no compliance standard. Building 54500233 has the most.",
        route='graph', intent='compliance_gaps')

    mm.save_exchange(sid,
        "How many HVAC assets are in poor condition?",
        "There are 342 HVAC assets in poor condition across 10 buildings.",
        route='analytical')

    ctx = mm.get_context_for_session(sid)
    print("=== CONTEXT BLOCK ===")
    print(ctx)

    mm.end_session(sid)

    summary = mm.get_memory_summary()
    print("\n=== MEMORY SUMMARY ===")
    print(json.dumps(summary, indent=2))
