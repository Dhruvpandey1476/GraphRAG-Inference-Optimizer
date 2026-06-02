#!/usr/bin/env python3
"""
Comprehensive test: Run 5 different queries and verify judge scores vary correctly.
Tests all 3 pipelines and verifies token efficiency + judge score differentiation.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from backend.rag.llm_only import LLMOnly
from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.llm.judge import llm_judge
from backend.graph.tigergraph_client import TigerGraphClient

load_dotenv()

# Test queries with varying difficulty
TEST_QUERIES = [
    "What is a transformer in NLP?",
    "How does BERT differ from GPT?",
    "Explain attention mechanisms",
    "What is the relationship between transformers and language models?",
    "How do pre-trained models improve NLP performance?",
]

def run_comprehensive_test():
    """Run 5 queries through all 3 pipelines and check judge scores"""
    
    print("\n" + "="*90)
    print("COMPREHENSIVE TEST: 5 QUERIES x 3 PIPELINES + JUDGE SCORES")
    print("="*90)
    
    # Initialize pipelines
    llm_only = LLMOnly()
    basic_rag = BasicRAG()
    tg_client = TigerGraphClient().connect()
    graph_rag = GraphRAG(tg_client)
    
    results = []
    
    for query_idx, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[QUERY {query_idx}/5] {query}")
        print("-" * 90)
        
        query_result = {
            "query": query,
            "pipelines": {}
        }
        
        # Run LLM-Only
        print("  [LLM-Only]", end=" ", flush=True)
        t0 = time.time()
        llm_result = llm_only.query(query)
        llm_latency = time.time() - t0
        print(f"✓ {llm_result.total_tokens} tokens, {llm_latency*1000:.0f}ms")
        
        # Run BasicRAG
        print("  [BasicRAG]", end=" ", flush=True)
        t0 = time.time()
        basic_result = basic_rag.query(query)
        basic_latency = time.time() - t0
        print(f"✓ {basic_result.total_tokens} tokens, {basic_latency*1000:.0f}ms")
        
        # Run GraphRAG
        print("  [GraphRAG]", end=" ", flush=True)
        t0 = time.time()
        graph_result = graph_rag.query(query)
        graph_latency = time.time() - t0
        print(f"✓ {graph_result.total_tokens} tokens, {graph_latency*1000:.0f}ms")
        
        # Judge each answer
        print("\n  [Judge Scoring]", end=" ", flush=True)
        llm_judge_score = llm_judge(query, llm_result.answer)
        basic_judge_score = llm_judge(query, basic_result.answer)
        graph_judge_score = llm_judge(query, graph_result.answer)
        print("✓")
        
        # Store results
        query_result["pipelines"]["llm_only"] = {
            "tokens": llm_result.total_tokens,
            "latency_ms": llm_latency * 1000,
            "judge_score": llm_judge_score.overall,
            "answer_preview": llm_result.answer[:80]
        }
        query_result["pipelines"]["basic_rag"] = {
            "tokens": basic_result.total_tokens,
            "latency_ms": basic_latency * 1000,
            "judge_score": basic_judge_score.overall,
            "answer_preview": basic_result.answer[:80]
        }
        query_result["pipelines"]["graph_rag"] = {
            "tokens": graph_result.total_tokens,
            "latency_ms": graph_latency * 1000,
            "judge_score": graph_judge_score.overall,
            "answer_preview": graph_result.answer[:80]
        }
        
        results.append(query_result)
        
        # Print results
        print(f"\n  RESULTS:")
        print(f"    LLM-Only:  {llm_result.total_tokens} tokens, Judge: {llm_judge_score.overall:.1f}/10")
        print(f"    BasicRAG:  {basic_result.total_tokens} tokens, Judge: {basic_judge_score.overall:.1f}/10")
        print(f"    GraphRAG:  {graph_result.total_tokens} tokens, Judge: {graph_judge_score.overall:.1f}/10")
    
    # Summary Statistics
    print("\n" + "="*90)
    print("SUMMARY STATISTICS")
    print("="*90)
    
    all_llm_tokens = [r["pipelines"]["llm_only"]["tokens"] for r in results]
    all_basic_tokens = [r["pipelines"]["basic_rag"]["tokens"] for r in results]
    all_graph_tokens = [r["pipelines"]["graph_rag"]["tokens"] for r in results]
    
    all_llm_scores = [r["pipelines"]["llm_only"]["judge_score"] for r in results]
    all_basic_scores = [r["pipelines"]["basic_rag"]["judge_score"] for r in results]
    all_graph_scores = [r["pipelines"]["graph_rag"]["judge_score"] for r in results]
    
    print("\nTOKEN USAGE (avg across 5 queries):")
    print(f"  LLM-Only:  {sum(all_llm_tokens)/len(all_llm_tokens):.0f} tokens")
    print(f"  BasicRAG:  {sum(all_basic_tokens)/len(all_basic_tokens):.0f} tokens")
    print(f"  GraphRAG:  {sum(all_graph_tokens)/len(all_graph_tokens):.0f} tokens")
    
    print("\nJUDGE SCORES (avg across 5 queries):")
    print(f"  LLM-Only:  {sum(all_llm_scores)/len(all_llm_scores):.2f}/10")
    print(f"  BasicRAG:  {sum(all_basic_scores)/len(all_basic_scores):.2f}/10")
    print(f"  GraphRAG:  {sum(all_graph_scores)/len(all_graph_scores):.2f}/10")
    
    print("\nJUDGE SCORES (min-max range):")
    print(f"  LLM-Only:  {min(all_llm_scores):.1f} - {max(all_llm_scores):.1f}")
    print(f"  BasicRAG:  {min(all_basic_scores):.1f} - {max(all_basic_scores):.1f}")
    print(f"  GraphRAG:  {min(all_graph_scores):.1f} - {max(all_graph_scores):.1f}")
    
    # Check if scores vary (NOT stuck at 9)
    print("\nSCORE VARIATION CHECK:")
    llm_varies = len(set(all_llm_scores)) > 1
    basic_varies = len(set(all_basic_scores)) > 1
    graph_varies = len(set(all_graph_scores)) > 1
    
    print(f"  LLM-Only varies: {'✅ YES' if llm_varies else '❌ NO (stuck at same score)'} - unique scores: {len(set(all_llm_scores))}")
    print(f"  BasicRAG varies: {'✅ YES' if basic_varies else '❌ NO (stuck at same score)'} - unique scores: {len(set(all_basic_scores))}")
    print(f"  GraphRAG varies: {'✅ YES' if graph_varies else '❌ NO (stuck at same score)'} - unique scores: {len(set(all_graph_scores))}")
    
    # Token efficiency check
    print("\nTOKEN EFFICIENCY CHECK:")
    avg_llm = sum(all_llm_tokens) / len(all_llm_tokens)
    avg_basic = sum(all_basic_tokens) / len(all_basic_tokens)
    avg_graph = sum(all_graph_tokens) / len(all_graph_tokens)
    
    if avg_graph < avg_llm and avg_llm < avg_basic:
        print(f"  ✅ PASS: GraphRAG ({avg_graph:.0f}) < LLM-Only ({avg_llm:.0f}) < BasicRAG ({avg_basic:.0f})")
    else:
        print(f"  ❌ FAIL: Order is wrong - GraphRAG ({avg_graph:.0f}), LLM-Only ({avg_llm:.0f}), BasicRAG ({avg_basic:.0f})")
    
    # Save results to JSON
    output_file = "test_comprehensive_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "queries_tested": len(TEST_QUERIES),
            "results": results,
            "summary": {
                "avg_tokens": {
                    "llm_only": avg_llm,
                    "basic_rag": avg_basic,
                    "graph_rag": avg_graph
                },
                "avg_judge_scores": {
                    "llm_only": sum(all_llm_scores) / len(all_llm_scores),
                    "basic_rag": sum(all_basic_scores) / len(all_basic_scores),
                    "graph_rag": sum(all_graph_scores) / len(all_graph_scores)
                },
                "judge_score_varies": {
                    "llm_only": llm_varies,
                    "basic_rag": basic_varies,
                    "graph_rag": graph_varies
                }
            }
        }, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    print("\n" + "="*90)

if __name__ == "__main__":
    run_comprehensive_test()
