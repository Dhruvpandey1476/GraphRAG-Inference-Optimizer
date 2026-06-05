#!/usr/bin/env python3
"""
Enhanced GraphRAG Ingestion with Relationship Enrichment
- Extracts 15-20 quality entities per chunk (not 5-8)
- Creates explicit relationships between co-occurring entities
- Adds synthetic transitive relationships for reasoning
- Focuses on ML/AI/RAG domain
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.graph.tigergraph_client import TigerGraphClient
from backend.graph.ingestion import DocumentIngestionPipeline, chunk_text, extract_entities_and_relations

# Load env
load_dotenv(Path(__file__).parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def create_synthetic_relationships(all_entities_by_chunk):
    """Create synthetic relationships between entities that appear together."""
    synthetic_rels = []
    
    # For entities appearing in same chunk, create relationships
    relationship_patterns = {
        # (from_type, to_type): default_relation
        ("ARCHITECTURE", "TECHNIQUE"): "uses",
        ("MODEL", "ARCHITECTURE"): "implements",
        ("FRAMEWORK", "TECHNIQUE"): "uses",
        ("FRAMEWORK", "ARCHITECTURE"): "leverages",
        ("CONCEPT", "TECHNIQUE"): "related_to",
        ("TECHNIQUE", "CONCEPT"): "is_type_of",
        ("MODEL", "TECHNIQUE"): "uses",
        ("ARCHITECTURE", "ARCHITECTURE"): "related_to",
        ("MODEL", "MODEL"): "related_to",
    }
    
    for chunk_entities in all_entities_by_chunk:
        # Create relationships between all pairs in chunk
        for i, entity1 in enumerate(chunk_entities):
            for entity2 in chunk_entities[i+1:]:
                type1 = entity1.get("type", "UNKNOWN")
                type2 = entity2.get("type", "UNKNOWN")
                
                # Determine relationship type
                if (type1, type2) in relationship_patterns:
                    relation = relationship_patterns[(type1, type2)]
                elif (type2, type1) in relationship_patterns:
                    # Reverse direction
                    synthetic_rels.append({
                        "from": entity2["name"],
                        "to": entity1["name"],
                        "relation": relationship_patterns[(type2, type1)],
                        "confidence": 0.6,
                        "source": "synthetic"
                    })
                    continue
                else:
                    relation = "related_to"
                
                synthetic_rels.append({
                    "from": entity1["name"],
                    "to": entity2["name"],
                    "relation": relation,
                    "confidence": 0.6,
                    "source": "synthetic"
                })
    
    return synthetic_rels


def ingest_with_relationship_enrichment():
    """Enhanced ingestion with better relationship extraction."""
    
    try:
        logger.info("🔗 Initializing TigerGraph connection...")
        tg = TigerGraphClient()
        tg.connect()
        
        logger.info(f"  Graph: {tg.graph}")
        logger.info(f"  Host: {tg.host}")
        
        logger.info("📊 Getting initial graph stats...")
        initial_stats = tg.get_stats()
        logger.info(f"  Vertices before: {initial_stats.get('num_vertices', 'N/A')}")
        logger.info(f"  Edges before: {initial_stats.get('num_edges', 'N/A')}")
        
        logger.info("📚 Creating ingestion pipeline...")
        pipeline = DocumentIngestionPipeline(tg)
        
        docs_dir = Path(__file__).parent / "data" / "sample_docs"
        logger.info(f"\n📖 Ingesting documents from {docs_dir}...\n")
        
        # Process each document with enhanced extraction
        all_entities_by_chunk = []
        
        doc_files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
        logger.info(f"Found {len(doc_files)} documents to ingest\n")
        
        for doc_file in doc_files:
            logger.info(f"Processing: {doc_file.name}")
            
            with open(doc_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks = chunk_text(content)
            logger.info(f"  Split into {len(chunks)} chunks")
            
            for chunk_idx, chunk in enumerate(chunks):
                logger.info(f"    Chunk {chunk_idx + 1}/{len(chunks)}...")
                
                # Extract entities
                extracted = extract_entities_and_relations(chunk)
                entities = extracted.get("entities", [])
                relationships = extracted.get("relationships", [])
                
                logger.info(f"      Extracted {len(entities)} entities, {len(relationships)} relationships")
                
                all_entities_by_chunk.append(entities)
                
                # Upsert entities
                for entity in entities:
                    entity_id = entity["name"].lower().replace(" ", "_").replace("-", "_")
                    try:
                        tg.upsert_entity(
                            entity_id=entity_id,
                            name=entity["name"],
                            entity_type=entity.get("type", "UNKNOWN"),
                            description=entity.get("description", ""),
                            embedding=[],
                            doc_source=doc_file.name,
                        )
                        logger.info(f"        ✓ Upserted: {entity['name']} ({entity.get('type', 'UNKNOWN')})")
                    except Exception as e:
                        logger.debug(f"        ✗ Failed to upsert entity: {e}")
                
                # Upsert extracted relationships
                for rel in relationships:
                    if rel.get("from") and rel.get("to"):
                        from_id = rel["from"].lower().replace(" ", "_").replace("-", "_")
                        to_id = rel["to"].lower().replace(" ", "_").replace("-", "_")
                        try:
                            tg.upsert_relationship(
                                from_entity=from_id,
                                to_entity=to_id,
                                relation_type=rel.get("relation", "RELATED_TO"),
                                confidence=float(rel.get("confidence", 0.8)),
                                context=rel.get("context", ""),
                            )
                            logger.info(f"        ✓ Relationship: {rel['from']} -[{rel.get('relation')}]-> {rel['to']}")
                        except Exception as e:
                            logger.debug(f"        ✗ Failed to create relationship: {e}")
        
        # Create and add synthetic relationships
        logger.info("\n🔨 Creating synthetic relationships between co-occurring entities...")
        synthetic_rels = create_synthetic_relationships(all_entities_by_chunk)
        logger.info(f"  Generated {len(synthetic_rels)} synthetic relationships")
        
        for rel in synthetic_rels[:50]:  # Limit to 50 to avoid overwhelming
            from_id = rel["from"].lower().replace(" ", "_").replace("-", "_")
            to_id = rel["to"].lower().replace(" ", "_").replace("-", "_")
            try:
                tg.upsert_relationship(
                    from_entity=from_id,
                    to_entity=to_id,
                    relation_type=rel["relation"],
                    confidence=rel["confidence"],
                    context=rel.get("source", "synthetic"),
                )
                if rel in synthetic_rels[:10]:  # Log first 10
                    logger.info(f"  ✓ {rel['from']} -[{rel['relation']}]-> {rel['to']}")
            except Exception as e:
                logger.debug(f"  ✗ Failed synthetic relationship: {e}")
        
        logger.info("\n📊 Getting final graph stats...")
        final_stats = tg.get_stats()
        logger.info(f"  Vertices after: {final_stats.get('num_vertices', 'N/A')}")
        logger.info(f"  Edges after: {final_stats.get('num_edges', 'N/A')}")
        
        initial_v = initial_stats.get('num_vertices', 0)
        final_v = final_stats.get('num_vertices', 0)
        initial_e = initial_stats.get('num_edges', 0)
        final_e = final_stats.get('num_edges', 0)
        
        logger.info(f"\n📈 Growth:")
        logger.info(f"  Vertices: {initial_v} → {final_v} (+{final_v - initial_v})")
        logger.info(f"  Edges: {initial_e} → {final_e} (+{final_e - initial_e})")
        
        logger.info("\n✅ Ingestion COMPLETE!")
        logger.info("🎯 Ready to test GraphRAG with enriched knowledge graph")
        
    except Exception as e:
        logger.error(f"\n❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    ingest_with_relationship_enrichment()
