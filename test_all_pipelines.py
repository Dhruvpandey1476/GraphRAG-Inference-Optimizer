from backend.rag.llm_only import LLMOnly
from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.graph.tigergraph_client import TigerGraphClient

tg = TigerGraphClient().connect()
llm = LLMOnly()
basic = BasicRAG()
graph = GraphRAG(tg)

question = "What is TigerGraph?"

print("="*70)
print("ALL 3 PIPELINES COMPARISON")
print("="*70)

print("\n1️⃣ LLM-ONLY")
llm_result = llm.query(question)
print(f"   Answer preview: {llm_result.answer[:100]}...")
print(f"   Tokens: {llm_result.total_tokens}")
print(f"   Length: {len(llm_result.answer)} chars")

print("\n2️⃣ BASIC-RAG (Vector Search)")
basic_result = basic.query(question)
print(f"   Answer preview: {basic_result.answer[:100]}...")
print(f"   Tokens: {basic_result.total_tokens}")
print(f"   Length: {len(basic_result.answer)} chars")

print("\n3️⃣ GRAPH-RAG (Knowledge Graph)")
graph_result = graph.query(question)
print(f"   Answer preview: {graph_result.answer[:100]}...")
print(f"   Tokens: {graph_result.total_tokens}")
print(f"   Length: {len(graph_result.answer)} chars")

print("\n" + "="*70)
print("VERIFICATION")
print("="*70)
print(f"All different? {llm_result.answer != basic_result.answer and basic_result.answer != graph_result.answer}")
print(f"All complete? {all(len(a.answer) > 200 for a in [llm_result, basic_result, graph_result])}")
