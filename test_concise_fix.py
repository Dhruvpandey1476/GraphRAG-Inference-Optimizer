from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.graph.tigergraph_client import TigerGraphClient

tg = TigerGraphClient().connect()
basic = BasicRAG()
graph = GraphRAG(tg)

question = "What is BERT vs GPT?"

print("="*70)
print("TESTING CONCISE FIX")
print("="*70)

print("\n1️⃣ BASIC-RAG")
basic_result = basic.query(question)
print(f"Tokens: {basic_result.total_tokens}")
print(f"Preview: {basic_result.answer[:80]}...\n")

print("2️⃣ GRAPH-RAG (now ultra-concise)")
graph_result = graph.query(question)
print(f"Tokens: {graph_result.total_tokens}")
print(f"Preview: {graph_result.answer[:80]}...\n")

print("="*70)
print(f"GraphRAG is {((basic_result.total_tokens - graph_result.total_tokens) / basic_result.total_tokens * 100):.1f}% SMALLER than BasicRAG")
