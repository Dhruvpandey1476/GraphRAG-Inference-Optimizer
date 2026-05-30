from backend.graph.tigergraph_client import TigerGraphClient
import itertools

client=TigerGraphClient()
client.connect()

docs=client.conn.getVertices("Document")

for d in docs:

    text=d["attributes"]["content"]

    entities=[]

    for e in client.conn.getVertices("Entity",limit=500):
        name=e["attributes"]["name"]

        if name in text:
            entities.append(name)

    for a,b in itertools.combinations(set(entities),2):

        client.conn.upsertEdge(
            "Entity",
            a,
            "RELATIONSHIP",
            "Entity",
            b
        )

print("Relationships created")