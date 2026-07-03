#!/usr/bin/env python3
"""
Ensure every canonical query entity resolves in TigerGraph.

The query-time extractor emits canonical names (RAG, LLM, FAISS, TigerGraph, ...)
whose normalized ids must exist as vertices, or GraphRAG falls back to the LLM.
Some are absent from the corpus graph (too modern for older arxiv papers) and
named differently in the curated graph. This adds a small, well-connected ML/RAG
ontology covering all tier-1/2 extractor terms, MERGES it with any existing
data/knowledge_graph.json, and loads everything into TigerGraph (additive).

Usage:
    python -m scripts.ensure_query_coverage
"""

import re
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.graph.tigergraph_client import TigerGraphClient

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

KG = Path(__file__).parent.parent / "data" / "knowledge_graph.json"


def nid(name): return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


# Canonical entities the query extractor can emit (must all resolve).
ENTS = [
    "Transformer", "Attention", "Self-Attention", "BERT", "GPT", "GPT-3", "GPT-4",
    "Seq2Seq", "LSTM", "RNN", "CNN", "Embedding", "Token", "Encoding", "Decoding",
    "Semantic", "Vector", "RAG", "GraphRAG", "Knowledge Graph", "TigerGraph", "FAISS",
    "LLM", "Hallucination", "Factual Accuracy", "Masked Language Modeling",
    "Pre-training", "Fine-tuning", "Bidirectional", "Autoregressive",
    "Retrieval", "Multi-hop Reasoning",
]

# Meaningful relationships (from, to, relation) for good 2-hop context.
RELS = [
    ("Transformer", "Attention", "uses"), ("Transformer", "Self-Attention", "uses"),
    ("Transformer", "Embedding", "uses"), ("Self-Attention", "Attention", "is_type_of"),
    ("BERT", "Transformer", "implements"), ("GPT", "Transformer", "implements"),
    ("GPT-3", "GPT", "is_version_of"), ("GPT-4", "GPT", "is_version_of"),
    ("BERT", "Masked Language Modeling", "uses"), ("BERT", "Bidirectional", "is"),
    ("GPT", "Autoregressive", "is"), ("Seq2Seq", "Attention", "uses"),
    ("LSTM", "RNN", "extends"), ("RNN", "Transformer", "alternative_to"),
    ("CNN", "RNN", "alternative_to"), ("Embedding", "Semantic", "enables"),
    ("Embedding", "Vector", "produces"), ("Encoding", "Embedding", "produces"),
    ("Decoding", "Token", "generates"), ("LLM", "Transformer", "uses"),
    ("LLM", "Token", "consumes"), ("LLM", "Hallucination", "suffers_from"),
    ("Fine-tuning", "LLM", "improves"), ("Pre-training", "Fine-tuning", "precedes"),
    ("RAG", "Retrieval", "uses"), ("RAG", "LLM", "augments"),
    ("RAG", "Embedding", "uses"), ("RAG", "Vector", "uses"),
    ("RAG", "Factual Accuracy", "improves"), ("RAG", "Hallucination", "reduces"),
    ("FAISS", "Vector", "enables"), ("FAISS", "Retrieval", "enables"),
    ("GraphRAG", "RAG", "extends"), ("GraphRAG", "Knowledge Graph", "uses"),
    ("GraphRAG", "Multi-hop Reasoning", "enables"), ("GraphRAG", "Token", "reduces"),
    ("Knowledge Graph", "TigerGraph", "stored_in"),
    ("Knowledge Graph", "Multi-hop Reasoning", "enables"),
    ("TigerGraph", "Knowledge Graph", "manages"), ("Retrieval", "Semantic", "uses"),
]


def build_ontology():
    ents = [{"id": nid(n), "name": n, "type": "CONCEPT", "description": ""} for n in ENTS]
    rels = [{"from_id": nid(a), "to_id": nid(b), "type": r.upper(),
             "confidence": 0.95, "context": "domain ontology"} for a, b, r in RELS]
    return ents, rels


def main():
    ents, rels = build_ontology()
    # Merge with existing curated graph if present (dedup by id / edge key)
    if KG.exists():
        cur = json.load(open(KG, encoding="utf-8"))
        have_e = {e["id"] for e in ents}
        for e in cur.get("entities", []):
            if e["id"] not in have_e:
                ents.append(e); have_e.add(e["id"])
        have_r = {(r["from_id"], r["to_id"], r.get("type")) for r in rels}
        for r in cur.get("relationships", []):
            k = (r.get("from_id"), r.get("to_id"), r.get("type"))
            if k not in have_r:
                rels.append(r); have_r.add(k)
    json.dump({"entities": ents, "relationships": rels}, open(KG, "w", encoding="utf-8"), indent=2)
    logger.info(f"Merged graph: {len(ents)} entities, {len(rels)} relationships -> {KG.name}")

    tg = TigerGraphClient().connect()
    conn = tg.conn
    logger.info(f"[OK] Connected: {tg.host}/{tg.graph}")
    conn.upsertVertices("Entity", [(e["id"], {"name": e["name"],
                        "entity_type": e.get("type", "CONCEPT"),
                        "description": e.get("description", "")}) for e in ents])
    conn.upsertEdges("Entity", "RELATED_TO", "Entity",
                     [(r["from_id"], r["to_id"], {"relation_type": r.get("type", "RELATED_TO"),
                       "confidence": float(r.get("confidence", 0.9)),
                       "context": r.get("context", "")}) for r in rels])
    logger.info(f"[DONE] Loaded {len(ents)} entities + {len(rels)} edges into TigerGraph (additive).")


if __name__ == "__main__":
    main()
