import asyncio
from backend.api.server import compare_pipelines, QueryRequest

print('VERIFYING FIX LOCALLY:')
print('=' * 70)

# Test with a domain question
req = QueryRequest(question='What is the transformer architecture and how does it work?', run_judge=False)
result = asyncio.run(compare_pipelines(req))

print(f'BasicRAG answer length: {len(result.basic_rag.answer)} chars')
print(f'GraphRAG answer length: {len(result.graph_rag.answer)} chars')
print()

if result.basic_rag.answer == result.graph_rag.answer:
    print('ERROR: Answers are still identical')
else:
    print('SUCCESS: Answers are DIFFERENT!')
    print()
    print('BasicRAG (first 100 chars):')
    print(result.basic_rag.answer[:100])
    print()
    print('GraphRAG (first 100 chars):')
    print(result.graph_rag.answer[:100])
    print()
    print('=' * 70)
    print('FIX CONFIRMED: Different prompts = Different answers')
