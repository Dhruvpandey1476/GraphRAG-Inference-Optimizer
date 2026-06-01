from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.graph.tigergraph_client import TigerGraphClient

tg = TigerGraphClient().connect()
basic = BasicRAG()
graph = GraphRAG(tg)

question = "What is the relationship between transformer architecture and BERT?"

print("="*70)
print("NEW FIX TEST: GraphRAG vs BasicRAG")
print("="*70)

print("\n1️⃣ BASIC-RAG (Vector Search)")
basic_result = basic.query(question)
print(f"Answer: {basic_result.answer[:150]}...")
print(f"Tokens: {basic_result.total_tokens}")

print("\n2️⃣ GRAPH-RAG (Entity-Relationship CoT)")
graph_result = graph.query(question)
print(f"Answer: {graph_result.answer[:150]}...")
print(f"Tokens: {graph_result.total_tokens}")

print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"Token efficiency: GraphRAG={graph_result.total_tokens}, BasicRAG={basic_result.total_tokens}")
print(f"Different answers? {basic_result.answer[:100] != graph_result.answer[:100]}")
print(f"Graph more efficient? {graph_result.total_tokens < basic_result.total_tokens}")
