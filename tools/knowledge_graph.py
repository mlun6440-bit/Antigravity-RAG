#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Graph Engine — Third Brain
=====================================
Builds and queries a NetworkX-based knowledge graph from the asset SQLite database.
Sits alongside PandasAnalyzer (Brain 1) and GeminiQueryEngine (Brain 2).

Designed for relational reasoning queries like:
  - "Which critical assets lack ISO compliance documentation?"
  - "What are the dependencies between HVAC and fire safety assets?"
  - "Show me the relationship between asset age and condition across buildings"
  - "Which buildings have clusters of poor-condition assets?"
  - "What compliance gaps exist for assets nearing end-of-life?"

Architecture:
    SQLite DB → NetworkX Graph → Graph Traversal → Gemini Synthesis → Answer

Node Types:
    - Asset       (id=asset_id)
    - Building    (id=building name)
    - Category    (id=category name)
    - Condition   (id=condition level)
    - Compliance  (id=compliance standard)
    - Criticality (id=criticality level)

Edge Types:
    - LOCATED_IN    (Asset → Building)
    - BELONGS_TO    (Asset → Category)
    - HAS_CONDITION (Asset → Condition)
    - HAS_CRITICALITY (Asset → Criticality)
    - HAS_COMPLIANCE  (Asset → Compliance)
    - SAME_BUILDING   (Building → Building, for adjacency reasoning)
    - COMPLIANCE_GAP  (Asset → Compliance, weight=1 when non-compliant)
"""

import os
import time
import logging
import sqlite3
import pickle
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Optional imports (graceful degradation) ──────────────────────────────────
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("networkx not installed. Run: pip install networkx")

try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Graph Engine
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeGraphEngine:
    """
    NetworkX-based Knowledge Graph over asset data.
    Provides relational reasoning capabilities not available via SQL or RAG.
    """

    def __init__(self, db_path: str = None, model_name: str = "gemini-2.0-flash"):
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx is required. Run: pip install networkx")

        self.db_path = db_path or self._find_db()
        self.model_name = model_name
        self.graph: Optional[nx.MultiDiGraph] = None
        self.graph_stats: Dict[str, Any] = {}
        self._built = False

        # Gemini for answer synthesis
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.llm = genai.GenerativeModel(model_name)
                logger.info(f"KnowledgeGraphEngine: Gemini synthesis enabled ({model_name})")
            except Exception as e:
                self.llm = None
                logger.warning(f"KnowledgeGraphEngine: Gemini init failed ({e}); raw results only.")
        elif not GENAI_AVAILABLE:
            self.llm = None
            logger.warning("KnowledgeGraphEngine: google-generativeai not installed; raw results only.")
        else:
            self.llm = None
            logger.warning("KnowledgeGraphEngine: GEMINI_API_KEY not set; raw results only.")

        logger.info(f"KnowledgeGraphEngine initialized (db={self.db_path})")

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _find_db(self) -> str:
        """Locate the SQLite database relative to this file."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(base, 'data', 'assets.db')
        if os.path.exists(candidate):
            return candidate
        raise FileNotFoundError(f"assets.db not found at {candidate}")

    def build_graph(self, sample_size: int = None, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Build the knowledge graph from SQLite.
        Uses disk caching to speed up subsequent loads (10x-50x faster).

        Args:
            sample_size: If set, only load this many assets (for testing).
            force_refresh: If True, ignore cache and rebuild from DB.

        Returns:
            Stats dict about the built graph.
        """
        t0 = time.time()
        cache_path = os.path.join(os.path.dirname(self.db_path), 'knowledge_graph.pkl')

        # ── 1. Try Cache Load ────────────────────────────────────────────────
        if not sample_size and not force_refresh and os.path.exists(cache_path):
            try:
                db_mtime = os.path.getmtime(self.db_path)
                cache_mtime = os.path.getmtime(cache_path)
                
                if cache_mtime > db_mtime:
                    logger.info("Loading Knowledge Graph from disk cache...")
                    with open(cache_path, 'rb') as f:
                        data = pickle.load(f)
                        self.graph = data['graph']
                        self.graph_stats = data['stats']
                        self.graph_stats['loaded_from_cache'] = True
                    
                    elapsed = time.time() - t0
                    self._built = True
                    logger.info(f"Graph loaded in {elapsed:.2f}s (cached)")
                    return self.graph_stats
                else:
                    logger.info("Graph cache stale; rebuilding...")
            except Exception as e:
                logger.warning(f"Cache load failed ({e}); rebuilding...")

        # ── 2. Build from SQL ────────────────────────────────────────────────
        logger.info("Building knowledge graph from SQLite…")

        self.graph = nx.MultiDiGraph()

        # Use context manager to prevent resource leaks
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load assets (parameterized LIMIT to prevent SQL injection)
            if sample_size:
                sample_size = int(sample_size)  # Validate as integer
                cursor.execute("""
                    SELECT
                        asset_id, asset_name, asset_type, category,
                        building, floor, location,
                        condition, condition_score, status, criticality,
                        compliance_standard, inspection_status,
                        install_date, replacement_due_date, remaining_life,
                        replacement_cost, annual_maintenance_cost
                    FROM assets
                    LIMIT ?
                """, (sample_size,))
            else:
                cursor.execute("""
                    SELECT
                        asset_id, asset_name, asset_type, category,
                        building, floor, location,
                        condition, condition_score, status, criticality,
                        compliance_standard, inspection_status,
                        install_date, replacement_due_date, remaining_life,
                        replacement_cost, annual_maintenance_cost
                    FROM assets
                """)
            rows = cursor.fetchall()

        # ── Build graph ───────────────────────────────────────────────────────
        category_nodes: set = set()
        building_nodes: set = set()
        condition_nodes: set = set()
        criticality_nodes: set = set()
        compliance_nodes: set = set()

        for row in rows:
            aid = str(row['asset_id'])

            # Asset node
            self.graph.add_node(
                f"asset:{aid}",
                node_type='asset',
                asset_id=aid,
                name=row['asset_name'] or aid,
                asset_type=row['asset_type'] or 'Unknown',
                category=row['category'] or 'Unknown',
                building=row['building'] or 'Unknown',
                floor=row['floor'] or 'Unknown',
                location=row['location'] or 'Unknown',
                condition=row['condition'] or 'Unknown',
                condition_score=row['condition_score'] or 0,
                status=row['status'] or 'Unknown',
                criticality=row['criticality'] or 'Unknown',
                compliance_standard=row['compliance_standard'] or 'None',
                inspection_status=row['inspection_status'] or 'Unknown',
                remaining_life=row['remaining_life'] or 0,
                replacement_cost=row['replacement_cost'] or 0,
                annual_maintenance_cost=row['annual_maintenance_cost'] or 0,
            )

            # ── Category node + edge ──────────────────────────────────────────
            cat = row['category'] or 'Unknown'
            cat_id = f"category:{cat}"
            if cat_id not in category_nodes:
                self.graph.add_node(cat_id, node_type='category', name=cat)
                category_nodes.add(cat_id)
            self.graph.add_edge(f"asset:{aid}", cat_id, edge_type='BELONGS_TO')

            # ── Building node + edge ──────────────────────────────────────────
            bldg = row['building'] or 'Unknown'
            bldg_id = f"building:{bldg}"
            if bldg_id not in building_nodes:
                self.graph.add_node(bldg_id, node_type='building', name=bldg)
                building_nodes.add(bldg_id)
            self.graph.add_edge(f"asset:{aid}", bldg_id, edge_type='LOCATED_IN')

            # ── Condition node + edge ─────────────────────────────────────────
            cond = row['condition'] or 'Unknown'
            cond_id = f"condition:{cond}"
            if cond_id not in condition_nodes:
                self.graph.add_node(cond_id, node_type='condition', name=cond)
                condition_nodes.add(cond_id)
            self.graph.add_edge(f"asset:{aid}", cond_id, edge_type='HAS_CONDITION')

            # ── Criticality node + edge ───────────────────────────────────────
            crit = row['criticality'] or 'Unknown'
            crit_id = f"criticality:{crit}"
            if crit_id not in criticality_nodes:
                self.graph.add_node(crit_id, node_type='criticality', name=crit)
                criticality_nodes.add(crit_id)
            self.graph.add_edge(f"asset:{aid}", crit_id, edge_type='HAS_CRITICALITY')

            # ── Compliance node + edge ────────────────────────────────────────
            comp = row['compliance_standard'] or 'None'
            comp_id = f"compliance:{comp}"
            if comp_id not in compliance_nodes:
                self.graph.add_node(comp_id, node_type='compliance', name=comp)
                compliance_nodes.add(comp_id)
            self.graph.add_edge(f"asset:{aid}", comp_id, edge_type='HAS_COMPLIANCE')

            # ── Compliance gap edge (for ISO-compliance-gap queries) ──────────
            # An asset is a "gap" if it's critical/poor condition but has no standard
            is_gap = (
                crit in ('Critical', 'High') and
                cond in ('Poor',) and
                comp in ('None', '', 'Unknown')
            )
            if is_gap:
                self.graph.add_edge(
                    f"asset:{aid}", comp_id,
                    edge_type='COMPLIANCE_GAP',
                    severity='high'
                )

        elapsed = time.time() - t0
        self.graph_stats = {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'asset_nodes': len([n for n in self.graph.nodes if n.startswith('asset:')]),
            'building_nodes': len(building_nodes),
            'category_nodes': len(category_nodes),
            'condition_nodes': len(condition_nodes),
            'criticality_nodes': len(criticality_nodes),
            'compliance_nodes': len(compliance_nodes),
            'build_time_seconds': round(elapsed, 2),
            'loaded_from_cache': False
        }
        self._built = True

        # ── 3. Save to Cache ─────────────────────────────────────────────────
        if not sample_size:
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump({
                        'graph': self.graph,
                        'stats': self.graph_stats
                    }, f)
                logger.info(f"Graph cached to {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to cache graph: {e}")

        logger.info(
            f"Graph built in {elapsed:.1f}s — "
            f"{self.graph_stats['total_nodes']} nodes, "
            f"{self.graph_stats['total_edges']} edges"
        )
        return self.graph_stats

    # ── Core Graph Queries ────────────────────────────────────────────────────

    def get_critical_assets_without_compliance(self, limit: int = 50) -> List[Dict]:
        """Return critical/high assets with no compliance standard documented."""
        if not self._built:
            self.build_graph()

        results = []
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') != 'asset':
                continue
            if data.get('criticality') in ('Critical', 'High'):
                comp = data.get('compliance_standard', 'None')
                if not comp or comp in ('None', 'Unknown', ''):
                    results.append({
                        'asset_id': data.get('asset_id'),
                        'name': data.get('name'),
                        'category': data.get('category'),
                        'building': data.get('building'),
                        'condition': data.get('condition'),
                        'criticality': data.get('criticality'),
                        'compliance_standard': comp,
                    })
        results.sort(key=lambda x: (
            0 if x['criticality'] == 'Critical' else 1,
            0 if x['condition'] == 'Poor' else 1
        ))
        return results[:limit]

    def get_poor_condition_clusters_by_building(self) -> List[Dict]:
        """Find buildings with the highest concentration of poor-condition assets."""
        if not self._built:
            self.build_graph()

        building_stats: Dict[str, Dict] = {}
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') != 'asset':
                continue
            bldg = data.get('building', 'Unknown')
            if bldg not in building_stats:
                building_stats[bldg] = {'total': 0, 'poor': 0, 'critical_poor': 0}
            building_stats[bldg]['total'] += 1
            if data.get('condition') == 'Poor':
                building_stats[bldg]['poor'] += 1
                if data.get('criticality') in ('Critical', 'High'):
                    building_stats[bldg]['critical_poor'] += 1

        results = []
        for bldg, stats in building_stats.items():
            if stats['total'] > 0:
                poor_pct = round(100 * stats['poor'] / stats['total'], 1)
                results.append({
                    'building': bldg,
                    'total_assets': stats['total'],
                    'poor_condition': stats['poor'],
                    'critical_and_poor': stats['critical_poor'],
                    'poor_percentage': poor_pct,
                })
        results.sort(key=lambda x: (-x['critical_and_poor'], -x['poor_percentage']))
        return results

    def get_end_of_life_compliance_gaps(self, remaining_life_threshold: int = 3) -> List[Dict]:
        """Assets nearing end-of-life that lack compliance documentation."""
        if not self._built:
            self.build_graph()

        results = []
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') != 'asset':
                continue
            rl = data.get('remaining_life', 0) or 0
            comp = data.get('compliance_standard', 'None')
            if rl <= remaining_life_threshold and (not comp or comp in ('None', 'Unknown', '')):
                results.append({
                    'asset_id': data.get('asset_id'),
                    'name': data.get('name'),
                    'category': data.get('category'),
                    'building': data.get('building'),
                    'criticality': data.get('criticality'),
                    'remaining_life': rl,
                    'replacement_cost': data.get('replacement_cost', 0),
                    'compliance_standard': comp,
                })
        results.sort(key=lambda x: x['remaining_life'])
        return results[:50]

    def get_category_condition_distribution(self) -> List[Dict]:
        """Cross-category condition distribution — useful for portfolio view."""
        if not self._built:
            self.build_graph()

        cat_cond: Dict[str, Dict] = {}
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') != 'asset':
                continue
            cat = data.get('category', 'Unknown')
            cond = data.get('condition', 'Unknown')
            if cat not in cat_cond:
                cat_cond[cat] = {}
            cat_cond[cat][cond] = cat_cond[cat].get(cond, 0) + 1

        results = []
        for cat, conds in cat_cond.items():
            total = sum(conds.values())
            poor = conds.get('Poor', 0)
            results.append({
                'category': cat,
                'total': total,
                'poor': poor,
                'fair': conds.get('Fair', 0),
                'good': conds.get('Good', 0),
                'very_good': conds.get('Very Good', 0),
                'unknown': conds.get('Unknown', 0),
                'poor_percentage': round(100 * poor / total, 1) if total else 0,
            })
        results.sort(key=lambda x: -x['poor_percentage'])
        return results

    def get_connected_assets(self, asset_id: str, depth: int = 2) -> Dict[str, Any]:
        """
        Return ego-graph around an asset — its neighbours and their attributes.
        Useful for understanding asset context (same building, same category, etc.)
        """
        if not self._built:
            self.build_graph()

        node_id = f"asset:{asset_id}"
        if node_id not in self.graph:
            return {'error': f'Asset {asset_id} not found in graph'}

        # BFS up to depth
        ego = nx.ego_graph(self.graph, node_id, radius=depth, undirected=True)
        nodes_out = []
        for n, d in ego.nodes(data=True):
            nodes_out.append({'id': n, **{k: v for k, v in d.items()}})
        edges_out = [
            {'from': u, 'to': v, 'type': d.get('edge_type', '')}
            for u, v, d in ego.edges(data=True)
        ]
        return {
            'center': node_id,
            'depth': depth,
            'node_count': ego.number_of_nodes(),
            'edge_count': ego.number_of_edges(),
            'nodes': nodes_out,
            'edges': edges_out,
        }

    def get_high_cost_poor_condition(self, top_n: int = 20) -> List[Dict]:
        """Assets with highest replacement cost that are in poor condition."""
        if not self._built:
            self.build_graph()

        results = []
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') != 'asset':
                continue
            if data.get('condition') == 'Poor':
                results.append({
                    'asset_id': data.get('asset_id'),
                    'name': data.get('name'),
                    'category': data.get('category'),
                    'building': data.get('building'),
                    'criticality': data.get('criticality'),
                    'condition': data.get('condition'),
                    'replacement_cost': data.get('replacement_cost', 0),
                    'annual_maintenance_cost': data.get('annual_maintenance_cost', 0),
                })
        results.sort(key=lambda x: -(x['replacement_cost'] or 0))
        return results[:top_n]

    # ── Intent Dispatcher ─────────────────────────────────────────────────────

    def query(self, question: str) -> Dict[str, Any]:
        """
        Main entry point: detect intent from question and run the appropriate
        graph traversal, then synthesize an answer via Gemini.
        """
        if not self._built:
            try:
                self.build_graph()
            except Exception as e:
                return {
                    'status': 'error',
                    'answer': f'Knowledge Graph not available: {e}',
                    'route': 'graph'
                }

        t0 = time.time()
        q_lower = question.lower()

        # ── Intent detection ──────────────────────────────────────────────────
        raw_data: Any = None
        intent_label: str = "general"

        if any(p in q_lower for p in [
            'critical', 'compliance', 'iso', 'documentation', 'standard', 'lack', 'missing', 'gap'
        ]):
            raw_data = self.get_critical_assets_without_compliance()
            intent_label = "compliance_gaps"

        elif any(p in q_lower for p in [
            'cluster', 'building', 'concentration', 'hotspot', 'worst building', 'buildings with'
        ]):
            raw_data = self.get_poor_condition_clusters_by_building()
            intent_label = "building_clusters"

        elif any(p in q_lower for p in [
            'end of life', 'end-of-life', 'remaining life', 'nearing', 'replacement', 'eol'
        ]):
            raw_data = self.get_end_of_life_compliance_gaps()
            intent_label = "eol_gaps"

        elif any(p in q_lower for p in [
            'category', 'distribution', 'portfolio', 'breakdown by category', 'per category'
        ]):
            raw_data = self.get_category_condition_distribution()
            intent_label = "category_distribution"

        elif any(p in q_lower for p in [
            'cost', 'expensive', 'highest cost', 'replacement cost', 'high cost'
        ]):
            raw_data = self.get_high_cost_poor_condition()
            intent_label = "high_cost_poor"

        else:
            # Generic: compliance gaps as default graph query
            raw_data = self.get_critical_assets_without_compliance()
            intent_label = "compliance_gaps"

        elapsed = (time.time() - t0) * 1000

        # ── Synthesize answer ─────────────────────────────────────────────────
        answer = self._synthesize(question, intent_label, raw_data)

        # ── Produce widgets ───────────────────────────────────────────────────
        widgets = self._generate_widgets(intent_label, raw_data)

        return {
            'status': 'success',
            'answer': answer,
            'route': 'graph',
            'intent': intent_label,
            'raw_count': len(raw_data) if isinstance(raw_data, list) else 0,
            'graph_stats': self.graph_stats,
            'widgets': widgets,
            'elapsed_ms': round(elapsed, 1),
        }

    # ── Synthesis ─────────────────────────────────────────────────────────────

    def _synthesize(self, question: str, intent: str, data: Any) -> str:
        """Use Gemini Flash to synthesize a consultant-style answer from raw graph data."""
        if not self.llm:
            return self._fallback_answer(intent, data)

        # Build a compact data summary (avoid huge prompts)
        data_summary = self._summarize_data(intent, data)

        prompt = f"""You are an ISO 55000 Asset Management consultant.
A user asked: "{question}"

The Knowledge Graph traversal identified the following (intent: {intent}):

{data_summary}

Write a concise, professional answer (3-6 sentences) that:
1. Directly answers the question using the data above
2. Quantifies the findings (numbers, percentages)
3. Highlights the most critical items
4. Suggests one actionable next step aligned with ISO 55001
5. Uses markdown formatting (bold key numbers, bullet points if helpful)

Do NOT include preamble like "Based on the graph..." — just answer directly.
"""
        try:
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=600
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini synthesis failed: {e}")
            return self._fallback_answer(intent, data)

    def _summarize_data(self, intent: str, data: Any) -> str:
        """Create a compact text summary of graph query results for the LLM."""
        if not data:
            return "No results found."

        if intent == "compliance_gaps":
            top = data[:10]
            lines = [f"Found {len(data)} critical/high-criticality assets with no compliance standard:"]
            for item in top:
                lines.append(
                    f"  • {item['asset_id']} — {item['name']} | "
                    f"Cat: {item['category']} | Bldg: {item['building']} | "
                    f"Cond: {item['condition']} | Crit: {item['criticality']}"
                )
            if len(data) > 10:
                lines.append(f"  … and {len(data) - 10} more")
            return "\n".join(lines)

        elif intent == "building_clusters":
            lines = [f"Building condition analysis ({len(data)} buildings):"]
            for item in data[:8]:
                lines.append(
                    f"  • {item['building']}: {item['poor_condition']}/{item['total_assets']} poor "
                    f"({item['poor_percentage']}%), {item['critical_and_poor']} critical+poor"
                )
            return "\n".join(lines)

        elif intent == "eol_gaps":
            lines = [f"Found {len(data)} assets nearing end-of-life with no compliance standard:"]
            for item in data[:10]:
                cost = f"${item['replacement_cost']:,.0f}" if item['replacement_cost'] else "N/A"
                lines.append(
                    f"  • {item['asset_id']} — {item['name']} | "
                    f"Remaining life: {item['remaining_life']}yr | "
                    f"Replacement: {cost} | Crit: {item['criticality']}"
                )
            return "\n".join(lines)

        elif intent == "category_distribution":
            lines = [f"Category condition distribution ({len(data)} categories):"]
            for item in data[:10]:
                lines.append(
                    f"  • {item['category']}: {item['total']} assets, "
                    f"{item['poor']} poor ({item['poor_percentage']}%)"
                )
            return "\n".join(lines)

        elif intent == "high_cost_poor":
            total_cost = sum(i.get('replacement_cost', 0) or 0 for i in data)
            lines = [f"Top {len(data)} high-cost poor-condition assets (total replacement: ${total_cost:,.0f}):"]
            for item in data[:10]:
                cost = f"${item['replacement_cost']:,.0f}" if item['replacement_cost'] else "N/A"
                lines.append(
                    f"  • {item['name']} | {item['category']} | "
                    f"Bldg: {item['building']} | Cost: {cost} | Crit: {item['criticality']}"
                )
            return "\n".join(lines)

        else:
            return str(data)[:1000]

    def _fallback_answer(self, intent: str, data: Any) -> str:
        """Plain-text answer when Gemini is unavailable."""
        if not data:
            return "No results found for this graph query."
        summary = self._summarize_data(intent, data)
        return f"**Knowledge Graph Result ({intent}):**\n\n{summary}"

    # ── Widget Generation ─────────────────────────────────────────────────────

    def _generate_widgets(self, intent: str, data: Any) -> List[Dict]:
        """Generate frontend widgets from graph query results."""
        if not data:
            return []

        widgets = []

        if intent == "compliance_gaps":
            critical = sum(1 for i in data if i.get('criticality') == 'Critical')
            high = sum(1 for i in data if i.get('criticality') == 'High')
            widgets.append({
                'type': 'stat_card',
                'title': 'Assets Missing Compliance Docs',
                'value': str(len(data)),
                'subtitle': f'{critical} Critical, {high} High criticality',
                'status': 'danger' if critical > 0 else 'warning',
            })
            # Category breakdown bar chart
            cat_counts: Dict[str, int] = {}
            for item in data:
                cat = item.get('category', 'Unknown')
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            if cat_counts:
                widgets.append({
                    'type': 'chart',
                    'chart_type': 'bar',
                    'title': 'Compliance Gaps by Category',
                    'data': [{'label': k, 'value': v} for k, v in
                             sorted(cat_counts.items(), key=lambda x: -x[1])[:10]],
                })

        elif intent == "building_clusters":
            worst = data[0] if data else {}
            widgets.append({
                'type': 'stat_card',
                'title': 'Buildings with Poor Condition Assets',
                'value': str(len([b for b in data if b.get('poor', 0) > 0 or b.get('poor_condition', 0) > 0])),
                'subtitle': f"Worst: {worst.get('building', 'N/A')} "
                            f"({worst.get('poor_percentage', 0)}% poor)",
                'status': 'warning',
            })
            top_buildings = data[:8]
            if top_buildings:
                widgets.append({
                    'type': 'chart',
                    'chart_type': 'bar',
                    'title': 'Poor-Condition Assets by Building (Top 8)',
                    'data': [
                        {
                            'label': b.get('building', 'Unknown'),
                            'value': b.get('poor_condition', 0),
                        }
                        for b in top_buildings
                    ],
                })

        elif intent == "eol_gaps":
            total_cost = sum(i.get('replacement_cost', 0) or 0 for i in data)
            widgets.append({
                'type': 'stat_card',
                'title': 'End-of-Life Assets Without Compliance',
                'value': str(len(data)),
                'subtitle': f'Est. replacement cost: ${total_cost:,.0f}',
                'status': 'danger' if len(data) > 20 else 'warning',
            })

        elif intent == "category_distribution":
            worst_cat = data[0] if data else {}
            widgets.append({
                'type': 'stat_card',
                'title': 'Categories Analysed',
                'value': str(len(data)),
                'subtitle': f"Worst: {worst_cat.get('category', 'N/A')} "
                            f"({worst_cat.get('poor_percentage', 0)}% poor)",
                'status': 'info',
            })
            widgets.append({
                'type': 'chart',
                'chart_type': 'bar',
                'title': 'Poor Condition % by Category (Top 10)',
                'data': [
                    {'label': i['category'], 'value': i['poor_percentage']}
                    for i in data[:10]
                ],
            })

        elif intent == "high_cost_poor":
            total = sum(i.get('replacement_cost', 0) or 0 for i in data)
            widgets.append({
                'type': 'stat_card',
                'title': 'Poor-Condition High-Cost Assets',
                'value': str(len(data)),
                'subtitle': f'Total replacement value: ${total:,.0f}',
                'status': 'danger',
            })
            widgets.append({
                'type': 'chart',
                'chart_type': 'bar',
                'title': 'Replacement Cost (Top Poor-Condition Assets)',
                'data': [
                    {
                        'label': i.get('name', i.get('asset_id', '?'))[:25],
                        'value': i.get('replacement_cost', 0) or 0,
                    }
                    for i in data[:10]
                ],
            })

        return widgets

    # ── Stats / Health ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return graph statistics."""
        return {
            'built': self._built,
            'stats': self.graph_stats,
            'networkx_version': nx.__version__ if NETWORKX_AVAILABLE else 'not installed',
        }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import json
    logging.basicConfig(level=logging.INFO)

    engine = KnowledgeGraphEngine()
    stats = engine.build_graph()
    print(f"\nGraph stats: {json.dumps(stats, indent=2)}")

    test_queries = [
        "Which critical assets lack ISO compliance documentation?",
        "Which buildings have clusters of poor-condition assets?",
        "What assets are nearing end-of-life without compliance standards?",
        "Show me the category distribution of poor condition assets",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"Q: {q}")
        result = engine.query(q)
        print(f"Route: {result['route']} | Intent: {result['intent']} | Count: {result['raw_count']}")
        print(f"Answer: {result['answer'][:300]}…")
