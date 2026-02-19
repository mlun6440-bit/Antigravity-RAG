#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Evaluation Tool
===================
Evaluates the retrieval quality of the RAG system using a set of test cases.
Metrics:
1. Precision@K: Is the relevant ISO section returned in the top K results?
2. Keyword Recall: Are expected keywords present in the retrieved content?
3. Faithfulness (LLM-as-a-judge): Does the context support the answer?
"""

import os
import json
import logging
import argparse
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import tools
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tools.gemini_query_engine import GeminiQueryEngine
    from tools.iso_embedding_manager import ISOEmbeddingManager
except ImportError:
    # Try importing directly if running from tools/
    try:
        from gemini_query_engine import GeminiQueryEngine
        from iso_embedding_manager import ISOEmbeddingManager
    except ImportError:
        logger.error("Could not import required modules. Run from project root.")
        sys.exit(1)

load_dotenv()

class RAGEvaluator:
    def __init__(self, test_cases_file: str = "data/test_cases.json"):
        self.test_cases_file = test_cases_file
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=self.api_key)
        self.judge_model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Initialize Query Engine (using mock DB paths or relying on defaults)
        self.engine = GeminiQueryEngine()
        
        # Load ISO KB manually to ensure we have chunks
        kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "iso_knowledge_base.json")
        if os.path.exists(kb_path):
            self.iso_kb = self.engine.load_iso_knowledge(kb_path)
            logger.info(f"Loaded ISO KB with {len(self.iso_kb.get('all_chunks', []))} chunks")
            # Initialize embedding manager manually if needed
            if not self.engine.iso_embedding_manager:
                 self.engine.iso_embedding_manager = ISOEmbeddingManager()
        else:
            logger.warning("ISO Knowledge Base not found. Evaluation results will be skewed.")
            self.iso_kb = {}

    def load_test_cases(self) -> List[Dict]:
        if not os.path.exists(self.test_cases_file):
            logger.error(f"Test cases file not found: {self.test_cases_file}")
            return []
        
        with open(self.test_cases_file, 'r') as f:
            return json.load(f)

    def evaluate_retrieval(self, question: str, expected_section: str, 
                           expected_keywords: List[str] = None, top_k: int = 5) -> Dict[str, Any]:
        """Check retrieval quality using section matching AND keyword recall."""
        
        # Perform retrieval using the engine's logic (Hybrid RRF)
        retrieved_chunks = self.engine.search_relevant_iso_content(question, self.iso_kb, max_chunks=top_k)
        
        found = False
        rank = -1
        retrieved_sections = []
        
        # Combine all retrieved text for keyword analysis
        all_retrieved_text = ""
        
        for i, chunk in enumerate(retrieved_chunks):
            sec_num = chunk.get('section', chunk.get('section_number', ''))
            title = chunk.get('title', chunk.get('section_title', ''))
            text = chunk.get('text', chunk.get('content', ''))
            
            retrieved_sections.append(f"{sec_num} ({title})")
            all_retrieved_text += " " + text.lower()
            
            # Check section number OR if expected section string appears in text
            if expected_section and not found:
                if (str(expected_section) in str(sec_num) or 
                    str(expected_section) in str(title) or
                    str(expected_section) in text):
                    found = True
                    rank = i + 1
        
        # Keyword recall
        keyword_recall = 0.0
        keywords_found = []
        keywords_missing = []
        if expected_keywords:
            for kw in expected_keywords:
                if kw.lower() in all_retrieved_text:
                    keywords_found.append(kw)
                else:
                    keywords_missing.append(kw)
            keyword_recall = len(keywords_found) / len(expected_keywords) if expected_keywords else 0
        
        return {
            'found': found,
            'rank': rank,
            'retrieved_sections': retrieved_sections,
            'retrieved_chunks': retrieved_chunks,
            'keyword_recall': keyword_recall,
            'keywords_found': keywords_found,
            'keywords_missing': keywords_missing
        }

    def evaluate_faithfulness(self, question: str, retrieved_chunks: List[Dict]) -> Dict[str, Any]:
        """Ask LLM judge if the retrieved context is sufficient to answer the question."""
        
        context_text = "\n\n".join([
            f"Section {c.get('section', 'N/A')}: {c.get('text', c.get('content', ''))}" 
            for c in retrieved_chunks
        ])
        
        prompt = f"""You are an unbiased evaluator for a RAG system.
        
        Question: {question}
        
        Retrieved Context:
        {context_text}
        
        Task: Determine if the retrieved context contains sufficient information to answer the question accurately.
        
        Output JSON only:
        {{
            "sufficient": boolean,
            "reason": "explanation",
            "score": float (0.0 to 1.0)
        }}
        """
        
        try:
            response = self.judge_model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Faithfulness check failed: {e}")
            return {"sufficient": False, "reason": "Error", "score": 0.0}

    def run_eval(self, top_k: int = 5):
        test_cases = self.load_test_cases()
        if not test_cases:
            return
        
        results = []
        logger.info(f"Starting evaluation on {len(test_cases)} test cases...")
        
        total_precision = 0
        total_faithfulness = 0
        total_keyword_recall = 0
        
        print(f"\n{'='*90}")
        print(f"{'QUESTION':<40} | {'FOUND':<6} | {'KW-RCL':<6} | {'FAITHFUL':<8} | {'SCORE':<5}")
        print(f"{'-'*90}")
        
        for case in test_cases:
            q = case['question']
            expected = case.get('expected_citation_iso')
            expected_kw = case.get('expected_keywords', [])
            
            # 1. Evaluate Retrieval (with keywords)
            retrieval_res = self.evaluate_retrieval(q, expected, expected_kw, top_k)
            
            # 2. Evaluate Faithfulness
            faithfulness_res = self.evaluate_faithfulness(q, retrieval_res['retrieved_chunks'])
            
            # Aggregates
            total_precision += 1 if retrieval_res['found'] else 0
            total_faithfulness += faithfulness_res['score']
            total_keyword_recall += retrieval_res.get('keyword_recall', 0)
            
            # Print row
            found_mark = "✅" if retrieval_res['found'] else "❌"
            kw_recall = retrieval_res.get('keyword_recall', 0)
            faith_mark = "✅" if faithfulness_res['sufficient'] else "❌"
            
            print(f"{q[:38]:<40} | {found_mark:<6} | {kw_recall:.0%}   | {faith_mark:<8} | {faithfulness_res['score']:.2f}")
            
            results.append({
                'question': q,
                'retrieval': retrieval_res,
                'faithfulness': faithfulness_res
            })
            
        # Summary
        n = len(test_cases)
        avg_precision = total_precision / n if n else 0
        avg_faithfulness = total_faithfulness / n if n else 0
        avg_keyword_recall = total_keyword_recall / n if n else 0
        
        print(f"{'='*90}")
        print(f"RESULTS SUMMARY:")
        print(f"  Total Cases:             {n}")
        print(f"  Retrieval Precision@{top_k}:  {avg_precision:.2%}")
        print(f"  Avg Keyword Recall:      {avg_keyword_recall:.2%}")
        print(f"  Avg Faithfulness Score:   {avg_faithfulness:.2f}/1.00")
        print(f"{'='*90}")
        
        # Save detailed report (strip embeddings to keep file small)
        for r in results:
            for chunk in r.get('retrieval', {}).get('retrieved_chunks', []):
                chunk.pop('embedding', None)
        
        with open('data/eval_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'precision_at_k': avg_precision,
                    'avg_keyword_recall': avg_keyword_recall,
                    'avg_faithfulness': avg_faithfulness,
                    'k': top_k
                },
                'details': results
            }, f, indent=2)
            logger.info("Detailed report saved to data/eval_report.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top_k", type=int, default=5, help="Number of chunks to retrieve")
    args = parser.parse_args()
    
    evaluator = RAGEvaluator()
    evaluator.run_eval(top_k=args.top_k)
