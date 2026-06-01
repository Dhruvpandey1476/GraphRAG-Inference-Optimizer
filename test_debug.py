from backend.rag.graph_rag import extract_query_entities
from backend.graph.tigergraph_client import TigerGraphClient

tg = TigerGraphClient().connect()

question = 'What is transformer architecture?'
entities = extract_query_entities(question)
print(f'EXTRACTED ENTITIES: {entities}')

subgraph = tg.get_entity_subgraph(entity_names=entities, max_hops=2, max_neighbors=10)
print(f'SUBGRAPH STATS:')
print(f'  Entities: {len(subgraph.get("entities", []))}')
print(f'  Relationships: {len(subgraph.get("relationships", []))}')
print(f'  Documents: {len(subgraph.get("documents", []))}')

if subgraph.get("entities"):
    print(f'ENTITY DETAILS:')
    for e in subgraph["entities"][:3]:
        print(f'  {e}')
