"""
Quick ingestion script — populates TigerGraph with knowledge from the
sample documents so GraphRAG has real data to traverse.
"""

import os
import re
import json
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env", override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.graph.tigergraph_client import TigerGraphClient
from groq import Groq

LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

ENTITY_EXTRACTION_PROMPT = """Extract all named entities and their relationships from the following text.

Return ONLY valid JSON in this exact format:
{
  "entities": [
    {"name": "Entity Name", "type": "PERSON|ORG|CONCEPT|TECHNOLOGY|METHOD", "description": "brief description"}
  ],
  "relationships": [
    {"from": "Entity A", "to": "Entity B", "relation": "relation type"}
  ]
}

Text:
"""

def make_entity_id(name: str) -> str:
    """Normalize entity name to a stable ID."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


def extract_entities_and_relations(chunk: str, groq_client: Groq) -> dict:
    """Use LLM to extract structured entities and relationships from a text chunk."""
    try:
        response = groq_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a knowledge graph extraction engine. Output only valid JSON."},
                {"role": "user", "content": ENTITY_EXTRACTION_PROMPT + chunk}
            ],
            temperature=0,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content
        # Clean markdown code fences if present
        raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Entity extraction failed: {e}")
        return {"entities": [], "relationships": []}


def chunk_text(text: str, chunk_size: int = 1500) -> list[str]:
    """Simple character-based chunking."""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def main():
    # Connect to TigerGraph
    print("🔌 Connecting to TigerGraph...")
    client = TigerGraphClient()
    client.connect()
    
    # Show current state
    try:
        stats = client.get_stats()
        print(f"📊 Current graph stats: {stats}")
    except:
        pass

    # Initialize Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set")
        sys.exit(1)
    groq_client = Groq(api_key=api_key)
    
    # Load sample documents
    docs_dir = Path(__file__).parent / "data" / "sample_docs"
    files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
    
    if not files:
        print("⚠️  No documents found in data/sample_docs/. Creating inline knowledge...")
    
    all_entities = {}  # name -> {type, description}
    all_relationships = []
    doc_links = []  # (entity_id, doc_id)
    
    for file_path in files:
        print(f"\n📄 Processing: {file_path.name}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        chunks = chunk_text(content)
        print(f"   → {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            doc_id = f"{file_path.stem}_chunk_{i}"
            title = f"{file_path.stem} [chunk {i}]"
            
            # Upsert document
            print(f"   📝 Upserting document: {doc_id}")
            client.upsert_document(
                doc_id=doc_id,
                title=title,
                content=chunk[:500],  # Truncate for storage
            )
            
            # Extract entities
            print(f"   🧠 Extracting entities from chunk {i}...")
            import time
            time.sleep(1)  # Rate limit for Groq
            extracted = extract_entities_and_relations(chunk, groq_client)
            
            entities = extracted.get("entities", [])
            relationships = extracted.get("relationships", [])
            
            print(f"   → Found {len(entities)} entities, {len(relationships)} relationships")
            
            for entity in entities:
                eid = make_entity_id(entity["name"])
                all_entities[entity["name"]] = {
                    "id": eid,
                    "type": entity.get("type", "CONCEPT"),
                    "description": entity.get("description", ""),
                }
                
                # Upsert entity
                client.upsert_entity(
                    entity_id=eid,
                    name=entity["name"],
                    entity_type=entity.get("type", "CONCEPT"),
                    description=entity.get("description", ""),
                )
                
                # Link to document
                client.link_entity_to_document(entity_id=eid, doc_id=doc_id)
                doc_links.append((eid, doc_id))
            
            for rel in relationships:
                from_name = rel.get("from", "")
                to_name = rel.get("to", "")
                if from_name and to_name:
                    from_id = make_entity_id(from_name)
                    to_id = make_entity_id(to_name)
                    
                    # Make sure both entities exist
                    if from_name not in all_entities:
                        client.upsert_entity(from_id, from_name, "CONCEPT", "")
                        all_entities[from_name] = {"id": from_id, "type": "CONCEPT", "description": ""}
                    if to_name not in all_entities:
                        client.upsert_entity(to_id, to_name, "CONCEPT", "")
                        all_entities[to_name] = {"id": to_id, "type": "CONCEPT", "description": ""}
                    
                    client.upsert_relationship(
                        from_entity=from_id,
                        to_entity=to_id,
                        relation_type=rel.get("relation", "RELATED_TO"),
                    )
                    all_relationships.append(rel)
    
    # Final stats
    print("\n" + "=" * 60)
    print("✅ INGESTION COMPLETE")
    print(f"   Entities:      {len(all_entities)}")
    print(f"   Relationships: {len(all_relationships)}")
    print(f"   Doc links:     {len(doc_links)}")
    
    try:
        stats = client.get_stats()
        print(f"\n📊 Graph stats: {json.dumps(stats, indent=2)}")
    except Exception as e:
        print(f"   Stats fetch error: {e}")


if __name__ == "__main__":
    main()
