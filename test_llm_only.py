from backend.rag.llm_only import LLMOnly

llm = LLMOnly()
question = "What is TigerGraph?"

print("="*70)
print("TESTING LLM-ONLY PIPELINE")
print("="*70)
result = llm.query(question)
print(f"\nQUESTION: {question}")
print(f"\nANSWER:\n{result.answer}")
print(f"\n{'='*70}")
print(f"TOKENS: {result.total_tokens}")
print(f"LATENCY: {result.latency_ms:.0f}ms")
print(f"COMPLETION TOKENS: {result.completion_tokens}")
print(f"\nENDS WITH: ...{result.answer[-50:]}")
