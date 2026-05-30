import re
from backend.graph.tigergraph_client import TigerGraphClient

client=TigerGraphClient()
client.connect()

docs=client.conn.getVertices("Document")

for d in docs:

    text=d["attributes"]["content"]

    entities=set(
        re.findall(
            r'\b[A-Z][A-Za-z0-9\-]{3,}\b',
            text
        )
    )

    for e in entities:
        client.conn.upsertVertex(
            "Entity",
            e,
            {
                "name":e,
                "entity_type":"CONCEPT",
                "description":e
            }
        )

print("Done")