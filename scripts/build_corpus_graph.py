#!/usr/bin/env python3
"""
Phase 1 — Build a knowledge graph FROM THE SAME CORPUS as Basic RAG, at $0.

Reuses the exact chunks in data/faiss_index.pkl (the arxiv corpus behind
Pipeline 2), so GraphRAG and Basic RAG are provably on the same dataset — the
fairness requirement the hackathon judges on.

Extraction is NON-LLM (zero API cost):
  - Entities: acronyms + curated ML/AI vocabulary + capitalized phrases, using
    the SAME normalization as the query-time extractor so seeds resolve.
  - Relationships: co-occurrence within a chunk (weighted by frequency).
  - MENTIONED_IN: each kept entity linked to a few source chunks (Document
    vertices), so GraphRAG can optionally return grounded snippets (Phase 3).

The full corpus is read (100% coverage), then pruned to the highest-signal
entities/edges so the graph loads into TigerGraph fast via batch upserts.

Usage:
    python -m scripts.build_corpus_graph                 # build + load to TigerGraph
    python -m scripts.build_corpus_graph --no-tigergraph # build JSON only (inspect first)
    python -m scripts.build_corpus_graph --limit 5000    # quick test on a subset
"""

import re
import sys
import json
import pickle
import argparse
import logging
from pathlib import Path
from collections import Counter, defaultdict

from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.graph.tigergraph_client import TigerGraphClient

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
FAISS_PKL = ROOT / "data" / "faiss_index.pkl"
OUT_JSON = ROOT / "data" / "knowledge_graph_corpus.json"

# ── Entity extraction (mirrors query-time extract_query_entities) ────────────
# Canonical ML/AI terms → matched case-insensitively, stored under canonical name
# so the same string appears whether it shows up in a chunk or a query.
CANON_TERMS = {
    "Transformer": r"\btransformers?\b",
    "Attention": r"\b(?:self[- ]|cross[- ]|multi[- ]head )?attention\b",
    "BERT": r"\bBERT\b", "RoBERTa": r"\bRoBERTa\b", "DistilBERT": r"\bDistilBERT\b",
    "GPT": r"\bGPT-?\d?\b", "T5": r"\bT5\b", "LLaMA": r"\bLLaMA\b",
    "LSTM": r"\bLSTM\b", "RNN": r"\bRNN\b", "CNN": r"\bCNN\b", "GRU": r"\bGRU\b",
    "Seq2Seq": r"\bseq2seq\b|\bsequence-to-sequence\b",
    "Encoder": r"\bencoder\b", "Decoder": r"\bdecoder\b",
    "Embedding": r"\bembeddings?\b", "Token": r"\btokens?\b",
    "Knowledge Graph": r"\bknowledge graphs?\b",
    "RAG": r"\bRAG\b|\bretrieval[- ]augmented generation\b", "GraphRAG": r"\bGraphRAG\b",
    "LLM": r"\bLLMs?\b|\blarge language models?\b",
    "FAISS": r"\bFAISS\b", "TigerGraph": r"\bTigerGraph\b",
    "Fine-tuning": r"\bfine[- ]tun\w*\b", "Pre-training": r"\bpre[- ]train\w*\b",
    "Instruction Tuning": r"\binstruction[- ]tun\w*\b",
    "Chain-of-Thought": r"\bchain[- ]of[- ]thought\b|\bCoT\b",
    "In-Context Learning": r"\bin[- ]context learning\b",
    "RLHF": r"\bRLHF\b|\breinforcement learning from human feedback\b",
    "Hallucination": r"\bhallucinat\w*\b", "Softmax": r"\bsoftmax\b",
    "Self-Attention": r"\bself[- ]attention\b", "Contrastive": r"\bcontrastive\b",
    "Vector Search": r"\bvector (?:search|similarity)\b", "Semantic": r"\bsemantic\b",
    "Retrieval": r"\bretrieval\b", "Reasoning": r"\breasoning\b",
    "Fine-tuning": r"\bfine[- ]tun\w*\b", "Prompt": r"\bprompt\w*\b",
}
_CANON_COMPILED = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in CANON_TERMS.items()]

_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,6}\b")
# Multi-word capitalized phrases ONLY (>=2 words) — single capitalized words are
# almost always sentence-starters ("Let", "Then") and pollute the graph.
_CAP_PHRASE = re.compile(r"\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+){1,3}\b")

# Academic / math boilerplate + sentence-initial words + acronym junk.
_STOP = {
    "what", "how", "why", "when", "where", "which", "who", "the", "a", "an", "and",
    "or", "of", "in", "on", "at", "to", "from", "this", "that", "these", "those",
    "we", "our", "it", "is", "are", "was", "were", "figure", "table", "section",
    "abstract", "introduction", "conclusion", "however", "therefore", "using",
    "based", "results", "method", "methods", "model", "models", "paper", "approach",
    "for", "with", "can", "such", "also", "more", "than", "into", "each",
    # sentence-initial / connectives
    "let", "then", "if", "as", "since", "thus", "by", "here", "note", "given",
    "hence", "moreover", "furthermore", "first", "second", "third", "finally",
    "now", "suppose", "assume", "consider", "recall", "indeed", "so", "but", "we",
    "our", "their", "its", "there", "they", "he", "she", "one", "two", "next",
    # math/paper structure
    "lemma", "theorem", "proof", "corollary", "proposition", "remark", "example",
    "fact", "claim", "case", "step", "definition", "equation", "appendix",
    "eq", "fig", "algorithm", "problem", "observation", "assumption", "notation",
    # acronym junk
    "ii", "iii", "iv", "vi", "pdf", "url", "ok", "id", "eg", "ie", "et", "al",
    # citation / venue boilerplate
    "ieee", "acm", "usa", "conference", "journal", "proceedings", "university",
    "springer", "arxiv", "vol", "isbn", "doi", "international", "national",
    "technical", "report", "preprint", "workshop", "symposium", "press", "author",
}
_VAR_LABEL = re.compile(r"^[A-Z]{1,2}\d+$")  # A1, X1, S1 — equation/variable labels


def _norm_id(name: str) -> str:
    """Vertex primary_id — MUST match TigerGraphClient._normalize_entity_id."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


def extract_entities(text: str, cap: int = 15) -> list[str]:
    """Return up to `cap` canonical entity display-names found in `text`."""
    found, seen = [], set()

    def add(name):
        key = name.lower()
        if key in seen or key in _STOP or len(name) < 2:
            return
        seen.add(key)
        found.append(name)

    for name, rx in _CANON_COMPILED:      # curated ML/AI vocab (highest signal)
        if rx.search(text):
            add(name)
    for m in _ACRONYM.findall(text):      # acronyms (BERT-style already covered, catch rest)
        if not _VAR_LABEL.match(m):
            add(m)
    for m in _CAP_PHRASE.findall(text):   # multi-word capitalized phrases
        if m.split()[0].lower() not in _STOP:  # reject "By Lemma", "In Section", ...
            add(m)
        if len(found) >= cap:
            break
    return found[:cap]


def build(limit=None, min_freq=3, top_entities=5000, min_edge=2, top_edges=40000,
          docs_per_entity=3):
    data = pickle.load(open(FAISS_PKL, "rb"))
    chunks, meta = data["chunks"], data.get("metadata", [])
    if limit:
        chunks, meta = chunks[:limit], meta[:limit]
    logger.info(f"Loaded {len(chunks)} chunks from {FAISS_PKL.name}")

    # Pass 1: per-chunk entities + global frequency
    ent_freq = Counter()
    chunk_ents = []  # list of (list[name]) per chunk
    for txt in tqdm(chunks, desc="Pass 1: extract"):
        ents = extract_entities(txt)
        chunk_ents.append(ents)
        ent_freq.update(ents)

    # Prune to high-signal entities
    kept = {n for n, c in ent_freq.items() if c >= min_freq}
    kept = set(sorted(kept, key=lambda n: -ent_freq[n])[:top_entities])
    logger.info(f"Kept {len(kept)} entities (freq>={min_freq}, top {top_entities})")

    # Pass 2: co-occurrence edges + document links (only among kept entities)
    edge_w = Counter()
    ent_docs = defaultdict(list)
    for i, ents in enumerate(tqdm(chunk_ents, desc="Pass 2: edges")):
        ke = [e for e in ents if e in kept]
        doc_id = (meta[i].get("file", f"chunk_{i}") if i < len(meta) else f"chunk_{i}") + f"__{i}"
        for a in ke:
            if len(ent_docs[a]) < docs_per_entity:
                ent_docs[a].append((doc_id, i))
        for x in range(len(ke)):
            for y in range(x + 1, len(ke)):
                edge_w[tuple(sorted((ke[x], ke[y])))] += 1

    edges = [(a, b, w) for (a, b), w in edge_w.items() if w >= min_edge]
    edges.sort(key=lambda e: -e[2])
    edges = edges[:top_edges]
    logger.info(f"Kept {len(edges)} co-occurrence edges (weight>={min_edge}, top {top_edges})")

    # Assemble JSON view
    max_w = max((w for _, _, w in edges), default=1)
    entities = [{"id": _norm_id(n), "name": n, "type": "CONCEPT",
                 "description": "", "freq": ent_freq[n]} for n in kept]
    relationships = [{"from_id": _norm_id(a), "to_id": _norm_id(b),
                      "type": "RELATED_TO", "confidence": round(0.5 + 0.5 * w / max_w, 3),
                      "context": f"co-occurs in {w} chunks"} for a, b, w in edges]
    OUT_JSON.write_text(json.dumps(
        {"entities": entities, "relationships": relationships,
         "metadata": {"source": "arxiv_bulk corpus (same as faiss_index.pkl)",
                      "chunks_scanned": len(chunks), "extraction": "non-LLM co-occurrence"}},
        indent=2), encoding="utf-8")
    logger.info(f"[OK] Wrote graph JSON: {OUT_JSON} ({len(entities)} entities, {len(relationships)} rels)")

    return chunks, meta, entities, relationships, ent_docs


def load_to_tigergraph(entities, relationships, ent_docs, chunks, batch=1000):
    tg = TigerGraphClient().connect()
    conn = tg.conn
    logger.info(f"[OK] Connected: {tg.host}/{tg.graph}")

    def batched(seq):
        for i in range(0, len(seq), batch):
            yield seq[i:i + batch]

    # Entity vertices
    verts = [(e["id"], {"name": e["name"], "entity_type": e["type"],
                        "description": e["description"]}) for e in entities]
    n = 0
    for b in tqdm(list(batched(verts)), desc="Upsert entities"):
        try:
            conn.upsertVertices("Entity", b); n += len(b)
        except Exception as ex:
            logger.warning(f"entity batch failed: {ex}")
    logger.info(f"[OK] Upserted ~{n} Entity vertices")

    # RELATED_TO edges
    eb = [(r["from_id"], r["to_id"], {"relation_type": r["type"],
           "confidence": r["confidence"], "context": r["context"]}) for r in relationships]
    n = 0
    for b in tqdm(list(batched(eb)), desc="Upsert RELATED_TO"):
        try:
            conn.upsertEdges("Entity", "RELATED_TO", "Entity", b); n += len(b)
        except Exception as ex:
            logger.warning(f"edge batch failed: {ex}")
    logger.info(f"[OK] Upserted ~{n} RELATED_TO edges")

    # Document vertices + MENTIONED_IN (for Phase 3 grounded snippets)
    docs, mentioned = {}, []
    for name, refs in ent_docs.items():
        eid = _norm_id(name)
        for doc_id, ci in refs:
            if doc_id not in docs and ci < len(chunks):
                docs[doc_id] = chunks[ci][:1500]
            mentioned.append((eid, doc_id, {"frequency": 1, "relevance_score": 1.0}))
    dv = [(d, {"title": d, "content": c, "chunk_index": 0, "token_count": 0}) for d, c in docs.items()]
    for b in tqdm(list(batched(dv)), desc="Upsert documents"):
        try:
            conn.upsertVertices("Document", b)
        except Exception as ex:
            logger.warning(f"doc batch failed: {ex}")
    for b in tqdm(list(batched(mentioned)), desc="Upsert MENTIONED_IN"):
        try:
            conn.upsertEdges("Entity", "MENTIONED_IN", "Document", b)
        except Exception as ex:
            logger.warning(f"mentioned batch failed: {ex}")
    logger.info(f"[OK] Upserted {len(dv)} Document vertices + {len(mentioned)} MENTIONED_IN edges")
    try:
        logger.info(f"[STATS] {tg.get_stats()}")
    except Exception:
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build corpus-derived KG (Phase 1, $0)")
    ap.add_argument("--limit", type=int, default=None, help="Only scan first N chunks (testing)")
    ap.add_argument("--min-freq", type=int, default=3)
    ap.add_argument("--top-entities", type=int, default=5000)
    ap.add_argument("--min-edge", type=int, default=2)
    ap.add_argument("--top-edges", type=int, default=40000)
    ap.add_argument("--docs-per-entity", type=int, default=3)
    ap.add_argument("--no-tigergraph", action="store_true", help="Build JSON only, skip TG load")
    args = ap.parse_args()

    chunks, meta, entities, relationships, ent_docs = build(
        limit=args.limit, min_freq=args.min_freq, top_entities=args.top_entities,
        min_edge=args.min_edge, top_edges=args.top_edges, docs_per_entity=args.docs_per_entity)

    if args.no_tigergraph:
        logger.info("Skipping TigerGraph load (--no-tigergraph). Inspect the JSON, then re-run without the flag.")
    else:
        load_to_tigergraph(entities, relationships, ent_docs, chunks)
        logger.info("[DONE] Corpus-derived graph loaded into TigerGraph (Phase 1, $0).")
