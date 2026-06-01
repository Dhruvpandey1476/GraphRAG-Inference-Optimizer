from backend.rag.llm_only import LLMOnly
from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.graph.tigergraph_client import TigerGraphClient

tg = TigerGraphClient().connect()
llm = LLMOnly()
basic = BasicRAG()
graph = GraphRAG(tg)

question = "What is the relationship between transformer architecture and attention?"

print("="*70)
print("TESTING 3 DISTINCT PROMPT STYLES")
print("="*70)

print("\n1️⃣ LLM-ONLY (BULLET POINTS FORMAT)")
llm_result = llm.query(question)
print(f"Answer:\n{llm_result.answer[:200]}...")
print(f"Tokens: {llm_result.total_tokens}")

print("\n2️⃣ BASIC-RAG (CONTEXT-BASED WITH CITATIONS)")
basic_result = basic.query(question)
print(f"Answer:\n{basic_result.answer[:200]}...")
print(f"Tokens: {basic_result.total_tokens}")

print("\n3️⃣ GRAPH-RAG (ENTITY-RELATIONSHIP STRUCTURED)")
graph_result = graph.query(question)
print(f"Answer:\n{graph_result.answer[:200]}...")
print(f"Tokens: {graph_result.total_tokens}")

print("\n" + "="*70)
print("VERIFICATION")
print("="*70)
print(f"All different starts? {len(set([llm_result.answer[:50], basic_result.answer[:50], graph_result.answer[:50]])) == 3}")
print(f"Token order (should be ~800, ~1500, ~1200): GraphRAG={graph_result.total_tokens}, BasicRAG={basic_result.total_tokens}, LLMOnly={llm_result.total_tokens}")
