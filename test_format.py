#!/usr/bin/env python3
"""Quick test of GraphRAG output format"""

from backend.rag.graph_rag import GraphRAG

rag = GraphRAG()
result = rag.query('What is a transformer?')
print('Answer:')
print(result['answer'])
print(f'\nTokens: {result["total_tokens"]}')
print(f'Bullet count: {result["answer"].count("•")}')
