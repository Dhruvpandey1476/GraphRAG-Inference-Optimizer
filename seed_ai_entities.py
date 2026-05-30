from backend.graph.tigergraph_client import TigerGraphClient

client=TigerGraphClient()
client.connect()

concepts = [
    "Transformer",
    "Attention",
    "SelfAttention",
    "Query",
    "Key",
    "Value",
    "Embedding",
    "RAG",
    "LargeLanguageModel"
]

for c in concepts:

    client.conn.upsertVertex(
        "Entity",
        c,
        {
            "name": c,
            "entity_type":"CONCEPT",
            "description": c
        }
    )

relations=[
("Transformer","Attention"),
("Attention","SelfAttention"),
("SelfAttention","Query"),
("SelfAttention","Key"),
("SelfAttention","Value")
]

for a,b in relations:
    client.conn.upsertEdge(
        "Entity",
        a,
        "RELATIONSHIP",
        "Entity",
        b
    )

print("AI entities seeded")