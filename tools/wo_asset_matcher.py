#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WO Asset Matcher - NLP-based matching of Work Orders to Asset Register entries.

Since WOs have no asset number, this module uses a 4-stage pipeline:
  Stage 1: SQL pre-filter by site_id + service_type → asset_type mapping
  Stage 2: Hybrid semantic search (0.7 cosine + 0.3 BM25) on WO description
  Stage 3: Cross-encoder reranking with ISO 55000 risk boosting
  Stage 4: Return top matches with confidence scores + ISO 55001 risk flags

ISO Risk Flags (ISO 55001):
  - Clause 8.1: RM on Critical/High asset in Poor/Very Poor condition
  - Clause 8.3: PM WO but asset is past next_maintenance_date
  - Clause 9.1: Asset already has 3+ open WOs (overloaded)
"""

import logging
import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service Type → Asset Type keyword mapping (pre-filter Stage 1)
# ---------------------------------------------------------------------------
SERVICE_TYPE_MAP = {
    "heating": ["HVAC", "Mechanical", "Air", "Chiller", "Boiler", "AHU"],
    "ventilation": ["HVAC", "Mechanical", "Air", "Fan", "AHU", "Duct"],
    "cooling": ["HVAC", "Chiller", "Cooling", "Air", "Mechanical"],
    "hvac": ["HVAC", "Mechanical", "Air", "Chiller"],
    "electrical": ["Electrical", "Power", "Switchboard", "Generator", "UPS"],
    "fire": ["Fire", "Sprinkler", "Detection", "Suppression", "Extinguisher"],
    "access control": ["Security", "Access", "CCTV", "Door", "Card"],
    "security": ["Security", "Access", "CCTV", "Surveillance"],
    "plumbing": ["Plumbing", "Hydraulic", "Water", "Pump", "Valve"],
    "hydraulic": ["Plumbing", "Hydraulic", "Water", "Pump"],
    "lift": ["Lift", "Elevator", "Escalator", "Vertical"],
    "elevator": ["Lift", "Elevator", "Vertical"],
    "building management": ["BMS", "Controls", "Automation", "Building"],
    "bms": ["BMS", "Controls", "Automation"],
    "structural": ["Structural", "Civil", "Facade", "Roof", "Concrete"],
    "civil": ["Structural", "Civil", "Pavement", "Drainage"],
    "grounds": ["Grounds", "Landscaping", "Garden", "External"],
    "cleaning": ["Cleaning", "Hygiene", "Amenity"],
    "pest": ["Pest", "Termite"],
    "waste": ["Waste", "Bin", "Refuse"],
    "painting": ["Paint", "Facade", "Finishes"],
    "glass": ["Glass", "Glazing", "Window", "Facade"],
    "door": ["Door", "Hardware", "Entrance", "Access"],
}

# ISO 55001 risk flag definitions
ISO_FLAGS = {
    "clause_8_1": "ISO 55001 Clause 8.1: Critical asset failure risk — reactive WO on critical/poor-condition asset",
    "clause_8_3": "ISO 55001 Clause 8.3: Overdue planned maintenance — PM WO but asset past next_maintenance_date",
    "clause_9_1": "ISO 55001 Clause 9.1: Asset under excessive reactive load — 3+ open WOs on same asset",
}


class WOAssetMatcher:
    """
    Matches Work Orders to assets using NLP + ISO 55000 risk analysis.

    Args:
        db_path: Path to assets.db SQLite database
        embedding_manager: EmbeddingManager instance (optional, for semantic search)
        bm25_scorer: BM25Scorer instance (optional)
        reranker: CrossEncoderReranker instance (optional)
    """

    def __init__(
        self,
        db_path: str = "data/assets.db",
        embedding_manager=None,
        bm25_scorer=None,
        reranker=None,
    ):
        from tools.database_manager import DatabaseManager
        self.db = DatabaseManager(db_path)
        self.embedding_manager = embedding_manager
        self.bm25_scorer = bm25_scorer
        self.reranker = reranker
        self._asset_embedding_cache: Dict[str, Any] = {}
        logger.info("[WOAssetMatcher] Initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match_wo(self, wo_row: dict, top_k: int = 5) -> List[dict]:
        """
        Match a single WO row to assets.

        Args:
            wo_row: Dict with keys: row_id, site_id, description, service_type, wo_type, status
            top_k: Number of top matches to return

        Returns:
            List of match dicts: {asset_id, asset_name, asset_type, location,
                                  condition, criticality, confidence, match_method,
                                  iso_risk_flags}
        """
        if not wo_row.get("description"):
            return []

        # Stage 1: SQL pre-filter
        candidates = self._stage1_filter(
            site_id=wo_row.get("site_id", ""),
            service_type=wo_row.get("service_type", ""),
        )

        if not candidates:
            logger.debug(f"WO {wo_row.get('row_id')}: No candidate assets after filter")
            return []

        # Stage 2: Hybrid search
        scored = self._stage2_hybrid_search(
            query=wo_row["description"],
            candidates=candidates,
        )

        # Stage 3: Rerank + ISO boost
        ranked = self._stage3_rerank(
            wo_row=wo_row,
            scored=scored,
            top_k=min(20, len(scored)),
        )

        # Stage 4: Build results with ISO flags
        results = []
        for asset, score in ranked[:top_k]:
            flags = self.get_iso_risk_flags(wo_row, asset)
            results.append({
                "asset_id": asset.get("asset_id"),
                "asset_name": asset.get("asset_name"),
                "asset_type": asset.get("asset_type"),
                "location": asset.get("location"),
                "building": asset.get("building"),
                "condition": asset.get("condition"),
                "criticality": asset.get("criticality"),
                "next_maintenance_date": asset.get("next_maintenance_date"),
                "confidence": round(score, 4),
                "match_method": "hybrid" if self.embedding_manager else "bm25",
                "iso_risk_flags": flags,
            })

        return results

    def match_all_unmatched(self, site_id: str = None, limit: int = None) -> dict:
        """
        Batch-match all unmatched WOs (where matched_asset_id IS NULL).

        Args:
            site_id: If provided, only match WOs for this site
            limit: Max WOs to process (for testing)

        Returns:
            Summary dict: {matched, unmatched, skipped, sites_processed}
        """
        # Query unmatched open WOs
        query = "SELECT * FROM work_orders WHERE matched_asset_id IS NULL AND status != 'Completed'"
        params = []
        if site_id:
            query += " AND site_id = ?"
            params.append(str(site_id))
        if limit:
            query += f" LIMIT {limit}"

        try:
            with self.db.get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                wo_list = [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Could not query work_orders: {e}")
            return {"matched": 0, "skipped": 0, "error": str(e)}

        logger.info(f"Processing {len(wo_list):,} unmatched WOs...")

        stats = {"matched": 0, "skipped": 0, "sites_processed": set()}

        for wo in wo_list:
            try:
                matches = self.match_wo(wo, top_k=1)
                if matches:
                    best = matches[0]
                    self.db.update_wo_match(
                        row_id=wo["row_id"],
                        asset_id=best["asset_id"],
                        confidence=best["confidence"],
                        method=best["match_method"],
                    )
                    stats["matched"] += 1
                    stats["sites_processed"].add(wo.get("site_id", ""))
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.warning(f"Error matching WO {wo.get('row_id')}: {e}")
                stats["skipped"] += 1

            if (stats["matched"] + stats["skipped"]) % 500 == 0:
                logger.info(f"  Matched: {stats['matched']:,} | Skipped: {stats['skipped']:,}")

        stats["sites_processed"] = list(stats["sites_processed"])
        logger.info(f"Batch complete — matched={stats['matched']:,} skipped={stats['skipped']:,}")
        return stats

    def get_iso_risk_flags(self, wo_row: dict, asset: dict) -> List[str]:
        """
        Return ISO 55001 risk flag strings for a WO-asset pair.

        Checks:
        - Clause 8.1: RM + critical/high asset in poor condition
        - Clause 8.3: PM + asset past next_maintenance_date
        - Clause 9.1: Asset has 3+ open WOs
        """
        flags = []
        wo_type = (wo_row.get("wo_type") or "").upper()
        condition = (asset.get("condition") or "").lower()
        criticality = (asset.get("criticality") or "").lower()

        # Clause 8.1 — Reactive WO on critical/poor asset
        if (wo_type == "RM"
                and condition in ("poor", "very poor")
                and criticality in ("critical", "high")):
            flags.append(ISO_FLAGS["clause_8_1"])

        # Clause 8.3 — PM overdue
        if wo_type == "PM":
            nmd = asset.get("next_maintenance_date")
            if nmd:
                try:
                    due = datetime.datetime.strptime(str(nmd)[:10], "%Y-%m-%d").date()
                    if due < datetime.date.today():
                        flags.append(ISO_FLAGS["clause_8_3"])
                except ValueError:
                    pass

        # Clause 9.1 — Asset overloaded with WOs
        asset_id = asset.get("asset_id")
        if asset_id:
            try:
                with self.db.get_connection() as conn:
                    row = conn.execute(
                        "SELECT COUNT(*) as cnt FROM work_orders WHERE matched_asset_id=? AND status!='Completed'",
                        (asset_id,)
                    ).fetchone()
                    if row and row["cnt"] >= 3:
                        flags.append(ISO_FLAGS["clause_9_1"])
            except Exception:
                pass

        return flags

    # ------------------------------------------------------------------
    # Internal pipeline stages
    # ------------------------------------------------------------------

    def _stage1_filter(self, site_id: str, service_type: str) -> List[dict]:
        """
        Stage 1: SQL filter — narrow assets by site_id and mapped asset_type keywords.
        Returns list of asset dicts.
        """
        filters = {}

        # Match site_id to asset building field
        if site_id:
            filters["building"] = str(site_id)

        assets, _ = self.db.query_assets(filters=filters, limit=5000)

        # Further narrow by service_type keyword mapping
        if service_type and assets:
            keywords = self._service_type_to_keywords(service_type)
            if keywords:
                filtered = []
                kw_lower = [k.lower() for k in keywords]
                for a in assets:
                    atype = (a.get("asset_type") or "").lower()
                    cat = (a.get("category") or "").lower()
                    if any(k in atype or k in cat for k in kw_lower):
                        filtered.append(a)
                if filtered:
                    assets = filtered

        return assets

    def _stage2_hybrid_search(self, query: str, candidates: List[dict]) -> List[tuple]:
        """
        Stage 2: Hybrid search combining semantic embeddings (0.7) + BM25 (0.3).
        Returns list of (asset, combined_score) tuples, sorted descending.
        """
        if not candidates:
            return []

        # --- BM25 scoring (always available, pure Python) ---
        bm25_scores = {}
        if self.bm25_scorer:
            try:
                corpus = [self._asset_to_text(a) for a in candidates]
                raw_scores = self.bm25_scorer.score(query, corpus)
                # Normalize 0-1
                max_s = max(raw_scores) if raw_scores else 1.0
                if max_s > 0:
                    bm25_scores = {i: s / max_s for i, s in enumerate(raw_scores)}
                else:
                    bm25_scores = {i: 0.0 for i in range(len(candidates))}
            except Exception as e:
                logger.debug(f"BM25 scoring failed: {e}")
                bm25_scores = {i: 0.0 for i in range(len(candidates))}
        else:
            # Fallback: simple keyword overlap score
            q_words = set(query.lower().split())
            for i, a in enumerate(candidates):
                text = self._asset_to_text(a).lower()
                overlap = sum(1 for w in q_words if w in text)
                bm25_scores[i] = min(overlap / max(len(q_words), 1), 1.0)

        # --- Semantic embedding scoring (optional) ---
        semantic_scores = {i: 0.0 for i in range(len(candidates))}
        if self.embedding_manager:
            try:
                query_emb = self.embedding_manager.generate_query_embedding(query)
                asset_texts = [self._asset_to_text(a) for a in candidates]
                # Use search_by_embedding if available
                if hasattr(self.embedding_manager, "search_by_embedding"):
                    # Build simple embedding list
                    asset_embs = []
                    for text in asset_texts:
                        try:
                            emb = self.embedding_manager.generate_embedding(text)
                            asset_embs.append(emb)
                        except Exception:
                            asset_embs.append(None)
                    results = self.embedding_manager.search_by_embedding(
                        query_emb, asset_embs, top_k=len(candidates)
                    )
                    # results: list of (index, score) or (asset, score)
                    for item in results:
                        if isinstance(item, (list, tuple)) and len(item) == 2:
                            idx, score = item
                            if isinstance(idx, int):
                                semantic_scores[idx] = float(score)
            except Exception as e:
                logger.debug(f"Semantic search failed, using BM25 only: {e}")

        # --- Combine scores ---
        combined = []
        for i, asset in enumerate(candidates):
            sem = semantic_scores.get(i, 0.0)
            bm25 = bm25_scores.get(i, 0.0)
            score = 0.7 * sem + 0.3 * bm25
            combined.append((asset, score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined

    def _stage3_rerank(
        self, wo_row: dict, scored: List[tuple], top_k: int = 20
    ) -> List[tuple]:
        """
        Stage 3: Rerank top candidates with cross-encoder + ISO condition boosting.
        """
        candidates = scored[:top_k]

        # Cross-encoder reranking (if available)
        if self.reranker and candidates:
            try:
                query = wo_row.get("description", "")
                pairs = [(query, self._asset_to_text(a)) for a, _ in candidates]
                ce_scores = self.reranker.rerank(pairs)
                # Blend cross-encoder with existing score
                candidates = [
                    (asset, 0.5 * base_score + 0.5 * float(ce_scores[i]))
                    for i, (asset, base_score) in enumerate(candidates)
                ]
            except Exception as e:
                logger.debug(f"Cross-encoder reranking failed: {e}")

        # ISO condition boost
        wo_type = (wo_row.get("wo_type") or "").upper()
        today = datetime.date.today()
        boosted = []
        for asset, score in candidates:
            boost = 0.0
            condition = (asset.get("condition") or "").lower()
            criticality = (asset.get("criticality") or "").lower()

            # RM WO: boost poor/critical assets (higher urgency match)
            if wo_type == "RM" and condition in ("poor", "very poor"):
                boost += 0.05
            if wo_type == "RM" and criticality in ("critical", "high"):
                boost += 0.05

            # PM WO: boost assets past maintenance date
            if wo_type == "PM":
                nmd = asset.get("next_maintenance_date")
                if nmd:
                    try:
                        due = datetime.datetime.strptime(str(nmd)[:10], "%Y-%m-%d").date()
                        if due < today:
                            boost += 0.08
                    except ValueError:
                        pass

            boosted.append((asset, min(score + boost, 1.0)))

        boosted.sort(key=lambda x: x[1], reverse=True)
        return boosted

    def _asset_to_text(self, asset: dict) -> str:
        """Convert asset dict to searchable text for BM25/embedding."""
        if self.embedding_manager and hasattr(self.embedding_manager, "asset_to_text"):
            try:
                return self.embedding_manager.asset_to_text(asset)
            except Exception:
                pass
        # Fallback: concatenate key fields
        parts = [
            asset.get("asset_name", ""),
            asset.get("asset_type", ""),
            asset.get("category", ""),
            asset.get("notes", ""),
            asset.get("tags", ""),
        ]
        return " | ".join(p for p in parts if p)

    def _service_type_to_keywords(self, service_type: str) -> List[str]:
        """Map a WO service_type string to asset type keywords."""
        service_lower = service_type.lower()
        keywords = []
        for key, kws in SERVICE_TYPE_MAP.items():
            if key in service_lower:
                keywords.extend(kws)
        return list(set(keywords))


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_matcher(db_path: str = "data/assets.db") -> WOAssetMatcher:
    """
    Create a WOAssetMatcher with all available NLP components.
    Components are loaded lazily — missing dependencies gracefully degrade.
    """
    embedding_manager = None
    bm25_scorer = None
    reranker = None

    try:
        from tools.embedding_manager import EmbeddingManager
        embedding_manager = EmbeddingManager()
        logger.info("[WOAssetMatcher] EmbeddingManager loaded")
    except Exception as e:
        logger.warning(f"EmbeddingManager not available: {e} — using BM25 only")

    try:
        from tools.bm25_scorer import BM25Scorer
        bm25_scorer = BM25Scorer()
        logger.info("[WOAssetMatcher] BM25Scorer loaded")
    except Exception as e:
        logger.warning(f"BM25Scorer not available: {e}")

    try:
        from tools.cross_encoder_reranker import CrossEncoderReranker
        reranker = CrossEncoderReranker()
        logger.info("[WOAssetMatcher] CrossEncoderReranker loaded")
    except Exception as e:
        logger.warning(f"CrossEncoderReranker not available: {e}")

    return WOAssetMatcher(
        db_path=db_path,
        embedding_manager=embedding_manager,
        bm25_scorer=bm25_scorer,
        reranker=reranker,
    )


if __name__ == "__main__":
    # Quick smoke test
    logging.basicConfig(level=logging.INFO)
    matcher = create_matcher()
    test_wo = {
        "row_id": 1,
        "site_id": "54500293",
        "site_name": "Test Site",
        "description": "Air handling unit filter replacement required — unit not performing",
        "service_type": "Heating, Ventilation & Cooling",
        "wo_type": "RM",
        "status": "Open",
    }
    results = matcher.match_wo(test_wo, top_k=3)
    print(f"\nMatched {len(results)} assets:")
    for r in results:
        print(f"  [{r['confidence']:.2f}] {r['asset_name']} ({r['asset_type']}) — {r['condition']}")
        for flag in r["iso_risk_flags"]:
            print(f"    ⚠ {flag}")
