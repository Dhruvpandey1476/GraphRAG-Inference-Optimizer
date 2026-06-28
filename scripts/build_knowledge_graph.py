#!/usr/bin/env python3
"""
Build the pre-computed knowledge graph JSON consumed by LocalKnowledgeGraph.

This is the offline counterpart to the TigerGraph ingestion pipeline. It reads
the source documents in ``data/sample_docs/``, extracts entities and
relationships, enriches them with synthetic co-occurrence edges, and writes a
single ``data/knowledge_graph.json`` file in the schema expected by
``backend/graph/local_graph.py``:

    {
      "entities":      [{"id", "name", "type", "description"}],
      "relationships": [{"from_id", "to_id", "type", "confidence", "context"}],
      "metadata":      {...}
    }

That JSON powers GraphRAG locally (and as the production fallback when
TigerGraph is unavailable), giving the benchmark a fast, deterministic graph
with real multi-hop BFS traversal.

The script degrades gracefully:
  * With ``GROQ_API_KEY`` set, it runs LLM entity/relationship extraction over
    the documents (same extractor used for TigerGraph ingestion).
  * Without an API key (or with ``--no-llm``), it falls back to the curated
    ML/AI knowledge base baked into ``local_knowledge_graph.py`` so the graph is
    always non-trivial and reproducible.

Usage:
    python scripts/build_knowledge_graph.py
    python scripts/build_knowledge_graph.py --data data/sample_docs/ --output data/knowledge_graph.json
    python scripts/build_knowledge_graph.py --no-llm        # offline / deterministic
    python scripts/build_knowledge_graph.py --no-synthetic  # only extracted edges
"""

import os
import re
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Make the project root importable when run as `python scripts/build_knowledge_graph.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env before importing modules that read environment variables (Groq, etc.)
load_dotenv(PROJECT_ROOT / ".env", override=True)

from backend.graph.local_knowledge_graph import LOCAL_ENTITIES, LOCAL_RELATIONSHIPS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "sample_docs"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "knowledge_graph.json"

# Synthetic relationship types inferred from entity-type pairs that co-occur in a
# chunk. Mirrors scripts/reingest_enhanced.py so the local graph matches the
# TigerGraph-ingested graph.
TYPE_PAIR_RELATIONS = {
    ("ARCHITECTURE", "TECHNIQUE"): "USES",
    ("MODEL", "ARCHITECTURE"): "IMPLEMENTS",
    ("FRAMEWORK", "TECHNIQUE"): "USES",
    ("FRAMEWORK", "ARCHITECTURE"): "LEVERAGES",
    ("CONCEPT", "TECHNIQUE"): "RELATED_TO",
    ("TECHNIQUE", "CONCEPT"): "IS_TYPE_OF",
    ("MODEL", "TECHNIQUE"): "USES",
    ("ARCHITECTURE", "ARCHITECTURE"): "RELATED_TO",
    ("MODEL", "MODEL"): "RELATED_TO",
}


def normalize_id(name: str) -> str:
    """Normalize an entity name to a stable id.

    Identical to ``DocumentIngestionPipeline._make_entity_id`` so ids line up
    with the TigerGraph-ingested graph and the curated local graph.
    """
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


# ─── Curated baseline ─────────────────────────────────────────────────────────

def seed_from_curated() -> tuple[dict, dict]:
    """Seed entities/relationships from the curated ML/AI knowledge base.

    Guarantees the core entities the query extractor looks for (BERT, GPT,
    Transformer, Attention, RAG, ...) are always present, so GraphRAG works even
    with no documents and no API key.

    Returns:
        (entities_by_id, relationships_by_key)
    """
    entities = {}
    for eid, data in LOCAL_ENTITIES.items():
        entities[eid] = {
            "id": eid,
            "name": data["name"],
            "type": data["type"],
            "description": data["description"],
        }

    relationships = {}
    for (from_id, to_id), data in LOCAL_RELATIONSHIPS.items():
        key = (from_id, to_id, data["type"])
        relationships[key] = {
            "from_id": from_id,
            "to_id": to_id,
            "type": data["type"],
            "confidence": 0.95,  # curated, stated facts
            "context": data.get("context", ""),
        }

    logger.info(
        f"🌱 Seeded {len(entities)} curated entities, {len(relationships)} curated relationships"
    )
    return entities, relationships


# ─── LLM extraction from documents ────────────────────────────────────────────

def extract_from_documents(data_dir: Path) -> tuple[dict, dict, list]:
    """Extract entities/relationships from documents via the LLM pipeline.

    Returns:
        (entities_by_id, relationships_by_key, entities_per_chunk)
        ``entities_per_chunk`` feeds synthetic co-occurrence enrichment.
        Returns empty structures if extraction is unavailable (e.g. no API key).
    """
    entities: dict = {}
    relationships: dict = {}
    entities_per_chunk: list = []

    files = sorted(list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt")))
    if not files:
        logger.warning(f"No .md/.txt documents found in {data_dir}")
        return entities, relationships, entities_per_chunk

    # Import lazily so --no-llm / offline runs don't require Groq/tiktoken.
    try:
        from backend.graph.ingestion import chunk_text, extract_entities_and_relations
    except Exception as e:
        logger.warning(f"Ingestion pipeline unavailable ({e}); skipping LLM extraction")
        return entities, relationships, entities_per_chunk

    if not os.getenv("GROQ_API_KEY"):
        logger.warning("GROQ_API_KEY not set; skipping LLM extraction (using curated baseline only)")
        return entities, relationships, entities_per_chunk

    logger.info(f"📖 Extracting from {len(files)} document(s) in {data_dir}")

    for doc in files:
        content = doc.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(content)
        logger.info(f"  {doc.name}: {len(chunks)} chunks")

        for idx, chunk in enumerate(chunks):
            extracted = extract_entities_and_relations(chunk)
            chunk_entities = extracted.get("entities", [])
            chunk_rels = extracted.get("relationships", [])
            entities_per_chunk.append(chunk_entities)

            for ent in chunk_entities:
                name = (ent.get("name") or "").strip()
                if not name:
                    continue
                eid = normalize_id(name)
                # First write wins for name/type; backfill missing descriptions.
                existing = entities.get(eid)
                if existing is None:
                    entities[eid] = {
                        "id": eid,
                        "name": name,
                        "type": ent.get("type", "CONCEPT"),
                        "description": ent.get("description", ""),
                    }
                elif not existing.get("description") and ent.get("description"):
                    existing["description"] = ent["description"]

            for rel in chunk_rels:
                frm = (rel.get("from") or "").strip()
                to = (rel.get("to") or "").strip()
                if not frm or not to:
                    continue
                from_id, to_id = normalize_id(frm), normalize_id(to)
                rel_type = (rel.get("relation") or "RELATED_TO").upper().replace(" ", "_")
                key = (from_id, to_id, rel_type)
                conf = float(rel.get("confidence", 0.8))
                prev = relationships.get(key)
                if prev is None or conf > prev["confidence"]:
                    relationships[key] = {
                        "from_id": from_id,
                        "to_id": to_id,
                        "type": rel_type,
                        "confidence": conf,
                        "context": rel.get("context", ""),
                    }

    logger.info(
        f"🧠 LLM extraction: {len(entities)} entities, {len(relationships)} relationships "
        f"over {len(entities_per_chunk)} chunks"
    )
    return entities, relationships, entities_per_chunk


# ─── Synthetic enrichment ─────────────────────────────────────────────────────

def build_synthetic_relationships(entities_per_chunk: list) -> dict:
    """Create co-occurrence edges between entities appearing in the same chunk.

    Densifies the graph for richer multi-hop traversal, matching the enrichment
    step used during TigerGraph ingestion.
    """
    relationships: dict = {}

    for chunk_entities in entities_per_chunk:
        for i, e1 in enumerate(chunk_entities):
            name1 = (e1.get("name") or "").strip()
            if not name1:
                continue
            for e2 in chunk_entities[i + 1:]:
                name2 = (e2.get("name") or "").strip()
                if not name2 or name1 == name2:
                    continue

                t1 = e1.get("type", "UNKNOWN")
                t2 = e2.get("type", "UNKNOWN")

                if (t1, t2) in TYPE_PAIR_RELATIONS:
                    from_name, to_name, rel = name1, name2, TYPE_PAIR_RELATIONS[(t1, t2)]
                elif (t2, t1) in TYPE_PAIR_RELATIONS:
                    from_name, to_name, rel = name2, name1, TYPE_PAIR_RELATIONS[(t2, t1)]
                else:
                    from_name, to_name, rel = name1, name2, "RELATED_TO"

                from_id, to_id = normalize_id(from_name), normalize_id(to_name)
                key = (from_id, to_id, rel)
                if key not in relationships:
                    relationships[key] = {
                        "from_id": from_id,
                        "to_id": to_id,
                        "type": rel,
                        "confidence": 0.6,  # inferred / synthetic
                        "context": "co-occurrence (synthetic)",
                    }

    logger.info(f"🔗 Synthetic enrichment: {len(relationships)} co-occurrence relationships")
    return relationships


# ─── Assembly ─────────────────────────────────────────────────────────────────

def merge_relationships(*relationship_dicts: dict) -> dict:
    """Merge relationship dicts keyed by (from_id, to_id, type), highest confidence wins."""
    merged: dict = {}
    for rels in relationship_dicts:
        for key, rel in rels.items():
            prev = merged.get(key)
            if prev is None or rel["confidence"] > prev["confidence"]:
                merged[key] = rel
    return merged


def ensure_endpoint_entities(entities: dict, relationships: dict) -> None:
    """Create minimal stub entities for any relationship endpoint without a vertex.

    Keeps the graph connected so BFS traversal never dead-ends on a dangling edge.
    """
    added = 0
    for rel in relationships.values():
        for eid in (rel["from_id"], rel["to_id"]):
            if eid not in entities:
                # Recover a human-readable name from the normalized id.
                name = eid.replace("_", " ").title()
                entities[eid] = {
                    "id": eid,
                    "name": name,
                    "type": "CONCEPT",
                    "description": "",
                }
                added += 1
    if added:
        logger.info(f"➕ Added {added} stub entities for dangling relationship endpoints")


def build_graph(data_dir: Path, use_llm: bool, use_synthetic: bool) -> dict:
    """Build the full knowledge graph dict ready to serialize."""
    # 1. Curated baseline (always present, guarantees core ML entities).
    entities, curated_rels = seed_from_curated()

    # 2. LLM extraction over documents (optional).
    llm_entities, llm_rels, entities_per_chunk = ({}, {}, [])
    if use_llm:
        llm_entities, llm_rels, entities_per_chunk = extract_from_documents(data_dir)

        # Guard: if LLM extraction was requested AND the API key is present, but
        # extraction returned nothing, every chunk silently failed (bad JSON,
        # rate limit, etc.). Don't quietly emit the 18/21 curated baseline and
        # pretend the documents were used — fail loudly so it gets fixed.
        if os.getenv("GROQ_API_KEY") and not llm_entities:
            raise SystemExit(
                "❌ LLM extraction returned 0 entities despite GROQ_API_KEY being set.\n"
                "   Every chunk failed in extract_entities_and_relations() (non-JSON "
                "response, rate limit, or bad model name).\n"
                "   The graph would collapse to the curated baseline. Re-run with "
                "logging at DEBUG to see the underlying error, or pass --no-llm to "
                "intentionally build the baseline-only graph."
            )

        for eid, ent in llm_entities.items():
            if eid not in entities:
                entities[eid] = ent
            elif not entities[eid].get("description") and ent.get("description"):
                entities[eid]["description"] = ent["description"]

    # 3. Synthetic co-occurrence enrichment (optional, needs extracted chunks).
    synthetic_rels = {}
    if use_synthetic and entities_per_chunk:
        synthetic_rels = build_synthetic_relationships(entities_per_chunk)

    # 4. Merge all relationship sources.
    relationships = merge_relationships(curated_rels, llm_rels, synthetic_rels)

    # 5. Patch up any dangling edges.
    ensure_endpoint_entities(entities, relationships)

    entity_list = list(entities.values())
    relationship_list = list(relationships.values())

    return {
        "entities": entity_list,
        "relationships": relationship_list,
        "metadata": {
            "built_at": datetime.now().isoformat(),
            "source_dir": str(data_dir.relative_to(PROJECT_ROOT)) if data_dir.is_relative_to(PROJECT_ROOT) else str(data_dir),
            "entity_count": len(entity_list),
            "relationship_count": len(relationship_list),
            "used_llm_extraction": bool(llm_entities),
            "llm_entity_count": len(llm_entities),
            "llm_relationship_count": len(llm_rels),
            "synthetic_relationship_count": len(synthetic_rels),
            "used_synthetic_relationships": bool(synthetic_rels),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Build data/knowledge_graph.json for LocalKnowledgeGraph")
    parser.add_argument("--data", default=str(DEFAULT_DATA_DIR),
                        help="Directory with source .md/.txt documents")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT),
                        help="Output JSON path")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM extraction; build from curated baseline only (deterministic, offline)")
    parser.add_argument("--no-synthetic", action="store_true",
                        help="Skip synthetic co-occurrence relationships")
    args = parser.parse_args()

    data_dir = Path(args.data)
    output_path = Path(args.output)

    logger.info("=" * 60)
    logger.info("  Building knowledge graph")
    logger.info("=" * 60)

    graph = build_graph(
        data_dir=data_dir,
        use_llm=not args.no_llm,
        use_synthetic=not args.no_synthetic,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    logger.info("=" * 60)
    logger.info(f"✅ Wrote {output_path}")
    logger.info(f"   Entities:      {graph['metadata']['entity_count']}")
    logger.info(f"   Relationships: {graph['metadata']['relationship_count']}")
    logger.info("=" * 60)
    logger.info("Next: GraphRAG / benchmark will load this via LocalKnowledgeGraph.load_from_json()")


if __name__ == "__main__":
    main()
