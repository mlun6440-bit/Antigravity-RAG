#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrator Agent — Deep Analysis Engine
==========================================
Combines all four analytical enhancements into one cohesive system:

1. **Chain-of-Thought (CoT)**: Step-by-step reasoning before answering
2. **Multi-hop Cross-Brain**: Chains outputs from one brain into another
3. **ReAct Agent Loop**: Observe → Think → Act → Repeat until satisfied
4. **Smart Widget Aggregation**: Intelligent widget decisions across all results

Architecture:
    User Question
        ↓
    [THINK] CoT Reasoning — break question into sub-tasks
        ↓
    [ACT]  Call Brain 1 (e.g., Knowledge Graph)
        ↓
    [OBSERVE] Evaluate result — enough info?
        ↓
    [ACT]  Call Brain 2 (e.g., Pandas Analyzer) with enriched context
        ↓
    [OBSERVE] Evaluate result — enough info?
        ↓
    [SYNTHESIZE] Combine all results → Final answer + widgets
"""

import os
import json
import time
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Optional imports ──────────────────────────────────────────────────────────
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
# Tool Definitions (for the ReAct loop)
# ─────────────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = """
Available tools for analysis:

1. TOOL: analyze_data
   Description: Run quantitative analysis on the asset database using Pandas code execution.
   Best for: Counts, percentages, breakdowns, aggregations, cost calculations, trend analysis, filtering assets by condition/category/building.
   Returns: Numerical answer with optional chart data.

2. TOOL: query_knowledge_graph
   Description: Query the relational knowledge graph to find relationships between entities.
   Best for: Compliance gaps, building clusters of poor condition, end-of-life risks, cross-entity relationships, dependency analysis, multi-hop relational queries.
   Returns: Relational analysis with entity connections.

3. TOOL: search_iso_standards
   Description: Search the ISO 55000/55001/55002 knowledge base using semantic retrieval.
   Best for: Standards compliance questions, best practices, definitions, ISO requirements, regulatory guidance, methodology questions.
   Returns: Cited passages from ISO standards with page references.

4. TOOL: synthesize_final_answer
   Description: Combine all gathered information into a final comprehensive answer.
   Use this ONLY after you have gathered enough information from other tools.
   Returns: Final answer ready for the user.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator Agent
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorAgent:
    """
    ReAct-style agent that orchestrates multiple analysis brains
    with Chain-of-Thought reasoning and multi-hop capabilities.
    """

    MAX_ITERATIONS = 3  # Maximum ReAct loop iterations

    def __init__(
        self,
        pandas_analyzer=None,
        knowledge_graph_engine=None,
        query_engine=None,
        model_name: str = "gemini-2.0-flash"
    ):
        self.pandas_analyzer = pandas_analyzer
        self.knowledge_graph_engine = knowledge_graph_engine
        self.query_engine = query_engine
        self.model_name = model_name

        # Initialize Gemini for reasoning
        self.llm = None
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                self.llm = genai.GenerativeModel(model_name)
                logger.info(f"OrchestratorAgent: Gemini reasoning enabled ({model_name})")
            except Exception as e:
                logger.warning(f"OrchestratorAgent: Gemini init failed ({e})")
        else:
            logger.warning("OrchestratorAgent: No LLM available, orchestration disabled")

        # Track available tools
        self.available_tools = []
        if self.pandas_analyzer:
            self.available_tools.append('analyze_data')
        if self.knowledge_graph_engine:
            self.available_tools.append('query_knowledge_graph')
        if self.query_engine:
            self.available_tools.append('search_iso_standards')

        logger.info(
            f"OrchestratorAgent initialized with tools: {self.available_tools}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def is_complex_query(self, question: str) -> bool:
        """
        Determine if a question benefits from multi-brain orchestration.
        Simple queries are faster on single-brain paths.
        """
        q_lower = question.lower()

        # Multi-part indicators
        multi_part_signals = [
            ' and ', ' also ', ' additionally ', ' furthermore ',
            ' as well as ', ' along with ', ' plus ',
            ' compare ', ' versus ', ' vs ',
            ' both ', ' between ',
        ]

        # Cross-domain indicators (touching multiple brains)
        cross_domain_signals = [
            # Data + ISO
            ('condition', 'iso'), ('condition', 'standard'), ('condition', 'compliance'),
            ('cost', 'iso'), ('cost', 'standard'), ('cost', 'compliance'),
            ('building', 'iso'), ('building', 'standard'),
            # Data + Relationships
            ('how many', 'relationship'), ('how many', 'connected'),
            ('count', 'cluster'), ('count', 'compliance gap'),
            # Analysis + Recommendations
            ('analyze', 'recommend'), ('breakdown', 'recommend'),
            ('trend', 'what should'), ('percentage', 'according to iso'),
        ]

        # Strategic / consultant-level questions
        strategic_signals = [
            'strategic', 'strategy', 'prioriti', 'roadmap',
            'action plan', 'investment', 'budget allocation',
            'risk assessment', 'risk profile', 'decision',
            'comprehensive', 'full analysis', 'deep dive',
            'overall', 'holistic', 'systematic',
            'what should', 'how should', 'recommend',
        ]

        # Check multi-part
        has_multi_part = any(sig in q_lower for sig in multi_part_signals)

        # Check cross-domain
        has_cross_domain = any(
            all(term in q_lower for term in pair)
            for pair in cross_domain_signals
        )

        # Check strategic
        has_strategic = any(sig in q_lower for sig in strategic_signals)

        # Question length (longer questions tend to be more complex)
        is_long = len(question.split()) > 15

        return has_multi_part or has_cross_domain or has_strategic or (is_long and has_multi_part)

    def orchestrate(
        self,
        question: str,
        context_prefix: str = "",
        asset_index_file: str = None,
        iso_kb_file: str = None,
    ) -> Dict[str, Any]:
        """
        Main entry point: Run the ReAct loop to answer a complex question.

        Returns:
            Dict with answer, widgets, reasoning_chain, tools_used, etc.
        """
        t0 = time.time()

        if not self.llm:
            return self._fallback_single_brain(question, context_prefix, asset_index_file, iso_kb_file)

        # ── Phase 1: PLAN (Chain-of-Thought) ──────────────────────────────────
        plan = self._plan(question)
        logger.info(f"[ORCHESTRATOR] Plan: {json.dumps(plan, indent=2)}")

        # ── Phase 2: EXECUTE (ReAct Loop) ─────────────────────────────────────
        reasoning_chain = []
        all_tool_results = {}
        all_widgets = []
        tools_used = []

        for iteration in range(self.MAX_ITERATIONS):
            step_num = iteration + 1

            # THINK: What tool should I call next?
            next_action = self._think(
                question, plan, reasoning_chain, all_tool_results
            )

            if not next_action or next_action.get('tool') == 'synthesize_final_answer':
                logger.info(f"[ORCHESTRATOR] Synthesis triggered at step {step_num}")
                reasoning_chain.append({
                    'step': step_num,
                    'phase': 'THINK',
                    'decision': 'Ready to synthesize final answer',
                    'reason': next_action.get('reason', 'Sufficient information gathered'),
                })
                break

            tool_name = next_action.get('tool', '')
            tool_question = next_action.get('question', question)
            reason = next_action.get('reason', '')

            reasoning_chain.append({
                'step': step_num,
                'phase': 'THINK',
                'decision': f'Call {tool_name}',
                'question': tool_question,
                'reason': reason,
            })

            # ACT: Call the tool
            logger.info(f"[ORCHESTRATOR] Step {step_num}: {tool_name}({tool_question[:60]}...)")
            tool_result = self._act(
                tool_name, tool_question, context_prefix,
                asset_index_file, iso_kb_file
            )

            all_tool_results[tool_name] = tool_result
            tools_used.append(tool_name)

            # Collect widgets from this tool
            if tool_result.get('widgets'):
                all_widgets.extend(tool_result['widgets'])

            # OBSERVE: Log what we got
            answer_preview = str(tool_result.get('answer', ''))[:200]
            reasoning_chain.append({
                'step': step_num,
                'phase': 'OBSERVE',
                'tool': tool_name,
                'result_preview': answer_preview,
                'has_data': bool(tool_result.get('answer')),
                'widget_count': len(tool_result.get('widgets', [])),
            })

        # ── Phase 3: SYNTHESIZE ───────────────────────────────────────────────
        final_answer = self._synthesize(question, plan, all_tool_results, reasoning_chain)

        # ── Phase 4: WIDGET AGGREGATION ───────────────────────────────────────
        final_widgets = self._aggregate_widgets(all_widgets, question)

        elapsed = time.time() - t0

        return {
            'status': 'success',
            'answer': final_answer,
            'route': 'orchestrated',
            'method': 'OrchestratorAgent (ReAct + CoT)',
            'tools_used': tools_used,
            'hop_count': len(tools_used),
            'reasoning_chain': reasoning_chain,
            'widgets': final_widgets,
            'elapsed_seconds': round(elapsed, 2),
            'model': f'Gemini ({self.model_name}) + Multi-Brain',
        }

    # ── Phase 1: PLAN ─────────────────────────────────────────────────────────

    def _plan(self, question: str) -> Dict[str, Any]:
        """
        Chain-of-Thought planning: Break the question into sub-tasks
        and decide which tools to use in what order.
        """
        prompt = f"""You are a strategic analysis planner for an ISO 55000 Asset Management system.

A user asked: "{question}"

You have these analysis tools available:
{TOOL_DEFINITIONS}

Think step-by-step:
1. What is the user really asking? (identify the core intent)
2. What types of information are needed to answer fully?
3. Which tools should be called, and in what order?
4. Should one tool's output feed into another? (multi-hop)

Output ONLY valid JSON:
{{
  "intent": "brief description of what user wants",
  "sub_tasks": [
    {{
      "tool": "tool_name",
      "question": "specific question for this tool",
      "reason": "why this tool is needed",
      "depends_on": null or "previous_tool_name"
    }}
  ],
  "synthesis_strategy": "how to combine results into final answer"
}}

Rules:
- Use 1-3 sub-tasks (no more than 3)
- Only use tools from the available list
- Order sub-tasks logically (dependencies first)
- If the question only needs one tool, that's fine — use just one
"""

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=500,
                )
            )
            text = response.text.strip()

            # Clean JSON from markdown fences
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

            plan = json.loads(text)
            return plan

        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Planning failed: {e}")
            # Fallback: simple plan
            return {
                'intent': question,
                'sub_tasks': [
                    {
                        'tool': 'analyze_data' if self.pandas_analyzer else 'search_iso_standards',
                        'question': question,
                        'reason': 'Primary analysis',
                        'depends_on': None,
                    }
                ],
                'synthesis_strategy': 'Direct answer from primary tool',
            }

    # ── Phase 2: THINK ────────────────────────────────────────────────────────

    def _think(
        self,
        question: str,
        plan: Dict,
        reasoning_chain: List[Dict],
        tool_results: Dict[str, Any],
    ) -> Optional[Dict]:
        """
        Decide what to do next based on the plan and results so far.
        Returns the next action, or None if ready to synthesize.
        """
        sub_tasks = plan.get('sub_tasks', [])
        completed_tools = set(tool_results.keys())
        completed_count = len(completed_tools)

        # Check if all planned sub-tasks are done
        remaining_tasks = [
            t for t in sub_tasks
            if t.get('tool') not in completed_tools
            and t.get('tool') in self.available_tools
        ]

        if not remaining_tasks:
            # All planned tasks done → synthesize
            return {'tool': 'synthesize_final_answer', 'reason': 'All planned analyses complete'}

        # Get next task
        next_task = remaining_tasks[0]
        tool_name = next_task['tool']
        tool_question = next_task.get('question', question)

        # Multi-hop enrichment: if this task depends on a previous result,
        # enhance the question with context from that result
        depends_on = next_task.get('depends_on')
        if depends_on and depends_on in tool_results:
            prev_answer = str(tool_results[depends_on].get('answer', ''))[:500]
            tool_question = (
                f"Based on this prior analysis:\n{prev_answer}\n\n"
                f"Now answer: {tool_question}"
            )

        return {
            'tool': tool_name,
            'question': tool_question,
            'reason': next_task.get('reason', 'Planned analysis step'),
        }

    # ── Phase 2: ACT ──────────────────────────────────────────────────────────

    def _act(
        self,
        tool_name: str,
        question: str,
        context_prefix: str = "",
        asset_index_file: str = None,
        iso_kb_file: str = None,
    ) -> Dict[str, Any]:
        """Execute a tool call and return its result."""

        contextual_q = context_prefix + question if context_prefix else question

        try:
            if tool_name == 'analyze_data' and self.pandas_analyzer:
                result = self.pandas_analyzer.analyze(question)
                return {
                    'answer': result.get('answer', 'No result'),
                    'code': result.get('code', ''),
                    'evidence': result.get('evidence', ''),
                    'widgets': result.get('widgets', []),
                    'source': 'PandasAnalyzer',
                }

            elif tool_name == 'query_knowledge_graph' and self.knowledge_graph_engine:
                result = self.knowledge_graph_engine.query(contextual_q)
                return {
                    'answer': result.get('answer', 'No result'),
                    'intent': result.get('intent', ''),
                    'raw_count': result.get('raw_count', 0),
                    'widgets': result.get('widgets', []),
                    'source': 'KnowledgeGraph',
                }

            elif tool_name == 'search_iso_standards' and self.query_engine:
                result = self.query_engine.query(
                    question=contextual_q,
                    asset_index_file=asset_index_file,
                    iso_kb_file=iso_kb_file,
                )
                return {
                    'answer': result.get('answer', 'No result'),
                    'citations': result.get('citations', []),
                    'widgets': result.get('widgets', []),
                    'source': 'RAG_ISO',
                }

            else:
                return {
                    'answer': f'Tool {tool_name} not available',
                    'widgets': [],
                    'source': 'error',
                }

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Tool {tool_name} failed: {e}")
            return {
                'answer': f'Tool error: {str(e)}',
                'widgets': [],
                'source': 'error',
            }

    # ── Phase 3: SYNTHESIZE ───────────────────────────────────────────────────

    def _synthesize(
        self,
        question: str,
        plan: Dict,
        tool_results: Dict[str, Any],
        reasoning_chain: List[Dict],
    ) -> str:
        """
        Combine all tool results into a single, coherent, consultant-quality answer.
        Uses Chain-of-Thought to reason across multiple data sources.
        """
        if not self.llm:
            return self._fallback_synthesis(tool_results)

        # Build results summary
        results_text = []
        for tool_name, result in tool_results.items():
            source = result.get('source', tool_name)
            answer = str(result.get('answer', 'No data'))[:800]
            results_text.append(f"=== {source} Analysis ===\n{answer}\n")

        combined_results = "\n".join(results_text)

        # Build reasoning summary
        thinking_steps = []
        for step in reasoning_chain:
            if step['phase'] == 'THINK':
                thinking_steps.append(f"- Step {step['step']}: {step.get('decision', '')} — {step.get('reason', '')}")

        reasoning_summary = "\n".join(thinking_steps) if thinking_steps else "Direct analysis"

        prompt = f"""You are a senior ISO 55000 Asset Management consultant delivering a comprehensive analysis.

USER QUESTION: "{question}"

ANALYSIS PLAN:
Intent: {plan.get('intent', question)}
Strategy: {plan.get('synthesis_strategy', 'Combine all findings')}

REASONING STEPS:
{reasoning_summary}

ANALYSIS RESULTS FROM MULTIPLE SOURCES:
{combined_results}

INSTRUCTIONS:
Write a comprehensive, professional answer that:
1. **Synthesizes** findings from ALL sources above into a unified narrative
2. **Quantifies** key findings (exact numbers, percentages)
3. **Cross-references** when one source enriches another (e.g., data confirms ISO requirements)
4. **Prioritizes** the most critical/actionable insights first
5. **Recommends** 2-3 specific next steps aligned with ISO 55001/55002
6. Uses **markdown formatting** (bold key numbers, headings, bullet points)
7. Adds a brief "**Analysis Method**" note at the end showing which brains contributed

Keep the answer focused and actionable (8-15 sentences maximum).
Do NOT repeat raw data verbatim — synthesize and interpret it.
Do NOT include preamble like "Based on the analysis..." — just answer directly.
"""

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1200,
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Synthesis failed: {e}")
            return self._fallback_synthesis(tool_results)

    def _fallback_synthesis(self, tool_results: Dict[str, Any]) -> str:
        """Combine results without Gemini."""
        parts = ["## Multi-Brain Analysis Results\n"]
        for tool_name, result in tool_results.items():
            source = result.get('source', tool_name)
            answer = str(result.get('answer', 'No data'))
            parts.append(f"### {source}\n{answer}\n")
        return "\n".join(parts)

    # ── Phase 4: WIDGET AGGREGATION ───────────────────────────────────────────

    def _aggregate_widgets(
        self,
        all_widgets: List[Dict],
        question: str,
    ) -> List[Dict]:
        """
        Intelligently aggregate and deduplicate widgets from multiple tools.
        Prioritize the most informative ones and limit to avoid UI clutter.
        """
        if not all_widgets:
            return []

        MAX_WIDGETS = 4

        # Deduplicate by title
        seen_titles = set()
        unique_widgets = []
        for w in all_widgets:
            title = w.get('title', '')
            if title not in seen_titles:
                seen_titles.add(title)
                unique_widgets.append(w)

        # Prioritize: stat_cards first, then charts
        stat_cards = [w for w in unique_widgets if w.get('type') == 'stat_card']
        charts = [w for w in unique_widgets if w.get('type') == 'chart']
        tables = [w for w in unique_widgets if w.get('type') == 'table']
        others = [w for w in unique_widgets if w.get('type') not in ('stat_card', 'chart', 'table')]

        # Compose: 1-2 stat cards + 1-2 charts + rest
        result = []
        result.extend(stat_cards[:2])
        result.extend(charts[:2])
        result.extend(tables[:1])
        result.extend(others[:1])

        return result[:MAX_WIDGETS]

    # ── Fallback (no LLM) ────────────────────────────────────────────────────

    def _fallback_single_brain(
        self,
        question: str,
        context_prefix: str,
        asset_index_file: str,
        iso_kb_file: str,
    ) -> Dict[str, Any]:
        """When orchestration LLM is unavailable, use single-brain path."""
        # Try pandas first, then knowledge graph, then RAG
        for tool_name in ['analyze_data', 'query_knowledge_graph', 'search_iso_standards']:
            result = self._act(tool_name, question, context_prefix, asset_index_file, iso_kb_file)
            if result.get('answer') and result.get('source') != 'error':
                return {
                    'status': 'success',
                    'answer': result['answer'],
                    'route': 'orchestrated',
                    'method': f'Fallback ({result["source"]})',
                    'tools_used': [tool_name],
                    'hop_count': 1,
                    'reasoning_chain': [],
                    'widgets': result.get('widgets', []),
                }

        return {
            'status': 'error',
            'answer': 'No analysis tools available.',
            'route': 'orchestrated',
        }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Quick integration test
    from pandas_analyzer import PandasAnalyzer
    from knowledge_graph import KnowledgeGraphEngine

    pa = PandasAnalyzer()
    kg = KnowledgeGraphEngine()
    kg.build_graph()

    agent = OrchestratorAgent(
        pandas_analyzer=pa,
        knowledge_graph_engine=kg,
    )

    test_questions = [
        "What are the critical compliance gaps and how much would it cost to fix them?",
        "Compare the condition distribution across buildings and recommend a prioritized maintenance strategy",
        "Which buildings have the worst asset conditions and what does ISO 55001 say about condition assessment?",
    ]

    for q in test_questions:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print(f"Complex? {agent.is_complex_query(q)}")
        result = agent.orchestrate(q)
        print(f"Tools: {result['tools_used']} | Hops: {result['hop_count']}")
        print(f"Answer: {result['answer'][:400]}...")
        print(f"Reasoning: {json.dumps(result['reasoning_chain'], indent=2)}")
