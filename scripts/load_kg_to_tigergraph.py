#!/usr/bin/env python3
"""
Load the pre-built knowledge graph (data/knowledge_graph.json) directly into
TigerGraph. Entity/relationship extraction is ALREADY done, so this makes ZERO
LLM calls — it only upserts vertices + edges via the TigerGraph client.

This is the cheap, reproducible way to get the exact graph behind the benchmark
numbers into TigerGraph so GraphRAG answers come from a real traversal.

Usage:
    python -m scripts.load_kg_to_tigergraph
    python -m scripts.load_kg_to_tigergraph --kg data/knowledge_graph.json
"""

import sys
import json
import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.graph.tigergraph_client import TigerGraphClient

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_kg(kg_path: str):
    kg = json.load(open(kg_path, "r", encoding="utf-8"))
    entities = kg.get("entities", [])
    relationships = kg.get("relationships", [])
    logger.info(f"Loaded {len(entities)} entities, {len(relationships)} relationships from {kg_path}")

    tg = TigerGraphClient().connect()
    logger.info(f"[OK] Connected to TigerGraph: {tg.host}/{tg.graph}")

    known_ids = set()

    # 1. Upsert entity vertices (primary_id = the JSON 'id', matching query-time ids)
    n_ent = 0
    for e in entities:
        eid = e.get("id") or e.get("name", "").lower().replace(" ", "_")
        try:
            tg.upsert_entity(
                entity_id=eid,
                name=e.get("name", eid),
                entity_type=e.get("type", "UNKNOWN"),
                description=e.get("description", ""),
                embedding=[],
                doc_source="knowledge_graph.json",
            )
            known_ids.add(eid)
            n_ent += 1
        except Exception as ex:
            logger.warning(f"[BAD] entity '{eid}' failed: {ex}")
    logger.info(f"[OK] Upserted {n_ent}/{len(entities)} entities")

    # 2. Upsert relationship edges. Create any missing endpoint vertex first so
    #    the edge always has both ends (RELATED_TO requires two Entity vertices).
    n_rel = 0
    for r in relationships:
        frm, to = r.get("from_id"), r.get("to_id")
        if not frm or not to:
            continue
        for vid in (frm, to):
            if vid not in known_ids:
                try:
                    tg.upsert_entity(vid, vid.replace("_", " "), "UNKNOWN", "", [], "knowledge_graph.json")
                    known_ids.add(vid)
                except Exception:
                    pass
        try:
            tg.upsert_relationship(
                from_entity=frm,
                to_entity=to,
                relation_type=r.get("type") or r.get("relation", "RELATED_TO"),
                confidence=float(r.get("confidence", 0.8)),
                context=r.get("context", ""),
            )
            n_rel += 1
        except Exception as ex:
            logger.warning(f"[BAD] relationship {frm}->{to} failed: {ex}")
    logger.info(f"[OK] Upserted {n_rel}/{len(relationships)} relationships")

    try:
        logger.info(f"[STATS] Graph stats: {tg.get_stats()}")
    except Exception:
        pass
    logger.info("[DONE] knowledge_graph.json loaded into TigerGraph (0 LLM calls).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Load knowledge_graph.json into TigerGraph (no LLM cost)")
    ap.add_argument("--kg", default="data/knowledge_graph.json", help="Path to knowledge_graph.json")
    args = ap.parse_args()
    load_kg(args.kg)
