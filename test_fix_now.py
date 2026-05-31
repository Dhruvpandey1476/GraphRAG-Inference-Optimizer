#!/usr/bin/env python3
"""Quick test of the GraphRAG fix"""
import asyncio
import sys
sys.path.insert(0, '.')

from backend.api.server import compare_pipelines, QueryRequest

async def test():
    print("Testing GraphRAG fallback prompt fix...")
    print("=" * 70)
    
    req = QueryRequest(question="What is attention?", run_judge=False)
    result = await compare_pipelines(req)
    
    b_len = len(result.basic_rag.answer)
    g_len = len(result.graph_rag.answer)
    
    print(f"BasicRAG answer length: {b_len} chars")
    print(f"GraphRAG answer length: {g_len} chars")
    print()
    print(f"BasicRAG (first 100 chars):")
    print(f"  {result.basic_rag.answer[:100]}")
    print()
    print(f"GraphRAG (first 100 chars):")
    print(f"  {result.graph_rag.answer[:100]}")
    print()
    print("=" * 70)
    
    if result.basic_rag.answer == result.graph_rag.answer:
        print("ERROR: Answers are IDENTICAL - FIX NOT WORKING")
        return False
    else:
        print("SUCCESS: Answers are DIFFERENT - FIX DEPLOYED!")
        print(f"Length difference: {abs(b_len - g_len)} chars")
        return True

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)
