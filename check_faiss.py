import pickle
from pathlib import Path

faiss_path = Path("data/faiss_index.pkl")
if faiss_path.exists():
    with open(faiss_path, "rb") as f:
        data = pickle.load(f)
    print(f"Keys: {list(data.keys())}")
    print(f"Index total: {data['index'].ntotal}")
    print(f"Chunks count: {len(data['chunks'])}")
    if data['chunks']:
        print(f"Sample chunk: {data['chunks'][0][:150]}")
else:
    print(f"FAISS index not found at {faiss_path}")
