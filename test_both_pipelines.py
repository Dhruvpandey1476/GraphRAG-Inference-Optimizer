from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.graph.tigergraph_client import TigerGraphClient

tg = TigerGraphClient().connect()
basic_rag = BasicRAG()
graph_rag = GraphRAG(tg)

question = "What is the relationship between transformer architecture?"

print("="*70)
print("TESTING BASIC RAG")
print("="*70)
result_basic = basic_rag.query(question)
print(f"\nANSWER (first 200 chars):\n{result_basic.answer[:200]}")
print(f"\nTOKENS: {result_basic.total_tokens}")

print("\n" + "="*70)
print("TESTING GRAPH RAG")
print("="*70)
result_graph = graph_rag.query(question)
print(f"\nANSWER (first 200 chars):\n{result_graph.answer[:200]}")
print(f"\nTOKENS: {result_graph.total_tokens}")

print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"SAME ANSWER? {result_basic.answer == result_graph.answer}")
print(f"BasicRAG len: {len(result_basic.answer)}, GraphRAG len: {len(result_graph.answer)}")
