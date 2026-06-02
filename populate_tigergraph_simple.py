#!/usr/bin/env python3
"""
Simple TigerGraph Bulk Loader - Directly inserts entities and relationships.
Bypasses complex DocumentIngestionPipeline that has schema issues.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from backend.graph.tigergraph_client import TigerGraphClient

load_dotenv()

def populate_sample_entities(tg: TigerGraphClient):
    """Manually insert entities that match knowledge base topics"""
    
    # Sample entities from AI knowledge base
    entities = [
        {"id": "transformer_001", "name": "Transformer", "type": "CONCEPT", "desc": "Neural network architecture using self-attention"},
        {"id": "bert_001", "name": "BERT", "type": "MODEL", "desc": "Bidirectional Encoder Representations from Transformers"},
        {"id": "gpt_001", "name": "GPT", "type": "MODEL", "desc": "Generative Pre-trained Transformer"},
        {"id": "attention_001", "name": "Attention Mechanism", "type": "CONCEPT", "desc": "Key mechanism in Transformers allowing focus on relevant parts"},
        {"id": "encoder_001", "name": "Encoder", "type": "COMPONENT", "desc": "Part of Transformer that processes input sequences"},
        {"id": "decoder_001", "name": "Decoder", "type": "COMPONENT", "desc": "Part of Transformer that generates output sequences"},
        {"id": "nlp_001", "name": "Natural Language Processing", "type": "DOMAIN", "desc": "Field of AI focused on human language"},
        {"id": "pretraining_001", "name": "Pre-training", "type": "TECHNIQUE", "desc": "Initial training on large corpus before fine-tuning"},
        {"id": "embedding_001", "name": "Embedding", "type": "CONCEPT", "desc": "Dense vector representation of tokens/words"},
        {"id": "mlm_001", "name": "Masked Language Model", "type": "TECHNIQUE", "desc": "Pre-training objective used by BERT"},
    ]
    
    print(f"[TigerGraph] Inserting {len(entities)} entities...")
    for e in entities:
        try:
            tg.conn.upsertVertex(
                vertexType="Entity",
                vertexId=e["id"],
                attributes={
                    "entity_id": e["id"],
                    "name": e["name"],
                    "entity_type": e["type"],
                    "description": e["desc"],
                }
            )
        except Exception as ex:
            print(f"  Warning: {e['name']} - {ex}")
    
    print(f"✅ {len(entities)} entities inserted")
    return entities


def populate_sample_relationships(tg: TigerGraphClient, entities: list):
    """Manually insert relationships between entities"""
    
    relationships = [
        ("transformer_001", "USED_BY", "bert_001", "BERT is built on Transformer architecture"),
        ("transformer_001", "USED_BY", "gpt_001", "GPT uses Transformer decoder architecture"),
        ("bert_001", "HAS_COMPONENT", "encoder_001", "BERT uses Transformer encoder"),
        ("gpt_001", "HAS_COMPONENT", "decoder_001", "GPT uses Transformer decoder"),
        ("encoder_001", "USES", "attention_001", "Encoder implements attention mechanisms"),
        ("decoder_001", "USES", "attention_001", "Decoder implements attention mechanisms"),
        ("attention_001", "PART_OF", "transformer_001", "Attention is core to Transformers"),
        ("bert_001", "APPLIES_TO", "nlp_001", "BERT is used in NLP tasks"),
        ("gpt_001", "APPLIES_TO", "nlp_001", "GPT is used in NLP tasks"),
        ("bert_001", "TRAINED_WITH", "mlm_001", "BERT uses Masked Language Model training"),
        ("bert_001", "USES", "embedding_001", "BERT generates token embeddings"),
        ("pretraining_001", "PRECEDES", "encoder_001", "Pre-training happens before encoding"),
    ]
    
    print(f"[TigerGraph] Inserting {len(relationships)} relationships...")
    for from_id, rel_type, to_id, context in relationships:
        try:
            tg.conn.upsertEdge(
                sourceVertexType="Entity",
                sourceVertexId=from_id,
                edgeType=rel_type,
                targetVertexType="Entity",
                targetVertexId=to_id,
                attributes={
                    "context": context,
                    "confidence": 0.9,
                }
            )
        except Exception as ex:
            print(f"  Warning: {from_id} -> {to_id} - {ex}")
    
    print(f"✅ {len(relationships)} relationships inserted")


def main():
    print("\n" + "="*60)
    print("POPULATE TIGERGRAPH WITH SAMPLE DATA")
    print("="*60)
    
    tg = TigerGraphClient()
    tg.connect()
    
    # Insert entities
    entities = populate_sample_entities(tg)
    
    # Insert relationships
    populate_sample_relationships(tg, entities)
    
    print("\n✅ TigerGraph populated with sample entities and relationships")
    print("   Now test with: python test_comprehensive_5queries.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
