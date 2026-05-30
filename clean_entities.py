from backend.graph.tigergraph_client import TigerGraphClient

client = TigerGraphClient()
client.connect()

print("Deleting noisy RELATIONSHIP edges...")

# Get all entity vertices
entities = client.conn.getVertices("Entity", limit=1000)

deleted = 0

for e in entities:
    try:
        # Delete all outgoing RELATIONSHIP edges
        client.conn.delEdges(
            sourceVertexType="Entity",
            sourceVertexId=e["v_id"],
            edgeType="RELATIONSHIP"
        )

        deleted += 1

    except Exception:
        pass

print("Deleted RELATIONSHIP sets from:", deleted)

print("Adding meaningful relationships...")

relations = [
    ("Transformer","Attention"),
    ("Attention","SelfAttention"),
    ("SelfAttention","Query"),
    ("SelfAttention","Key"),
    ("SelfAttention","Value"),
    ("RAG","Retrieval"),
    ("RAG","KnowledgeGraph"),
    ("LLM","Transformer"),
    ("Embedding","Vector"),
    ("BERT","Transformer"),
    ("GPT","Transformer"),
    ("LLM","Attention")
]

for a,b in relations:

    try:
        client.conn.upsertEdge(
            "Entity",
            a,
            "RELATIONSHIP",
            "Entity",
            b
        )
    except Exception as e:
        print(f"Skipping {a}->{b}: {e}")

print("Done")