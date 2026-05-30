from backend.graph.tigergraph_client import TigerGraphClient

client=TigerGraphClient()
client.connect()

docs=client.conn.getVertices("Document")

entities=client.conn.getVertices("Entity",limit=500)

for d in docs:

    text=d["attributes"]["content"]
    doc_id=d["v_id"]

    for e in entities:

        name=e["attributes"]["name"]
        entity_id=e["v_id"]

        if name in text:

            client.conn.upsertEdge(
                "Entity",
                entity_id,
                "MENTIONED_IN",
                "Document",
                doc_id
            )

print("MENTIONED_IN edges created")