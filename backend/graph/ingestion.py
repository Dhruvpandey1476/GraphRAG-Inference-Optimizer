"""
Document Ingestion Pipeline
Converts raw documents → chunks → entities → relationships → TigerGraph KG
"""

import os
import re
import json
import uuid
import logging
from pathlib import Path
from typing import Iterator
import tiktoken
from groq import Groq
from tqdm import tqdm
from dotenv import load_dotenv

from .tigergraph_client import TigerGraphClient

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 64))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

_groq_client = None
_sentence_transformer = None
encoder = tiktoken.get_encoding("cl100k_base")


def _get_groq_client():
    """Lazily initialize Groq client to ensure .env is loaded."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment. Check your .env file.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_sentence_transformer():
    """Lazily load sentence-transformer for local embeddings."""
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Loaded sentence-transformers for local embeddings (384 dims)")
        except ImportError:
            logger.warning("sentence-transformers not installed")
            _sentence_transformer = False
    return _sentence_transformer if _sentence_transformer else None


# ─── Text Chunking ────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Token-aware text chunking with overlap."""
    tokens = encoder.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(encoder.decode(chunk_tokens))
        start += chunk_size - overlap
    return chunks


def count_tokens(text: str) -> int:
    return len(encoder.encode(text))


# ─── Entity Extraction ────────────────────────────────────────────────────────

ENTITY_EXTRACTION_PROMPT = """Extract ALL key entities and their relationships from this Machine Learning / AI / RAG text.

FOCUS ON: 
- ML architectures: Transformer, LSTM, RNN, CNN, Seq2Seq, GRU, Attention, etc.
- Techniques: Attention Mechanism, Self-Attention, Multi-Head Attention, Embeddings, Pooling, etc.
- Models: BERT, GPT, GPT-2, GPT-3, GPT-4, Claude, LLaMA, RoBERTa, DistilBERT, ALBERT, T5, etc.
- Frameworks: RAG, GraphRAG, Knowledge Graphs, TigerGraph, Neo4j, FAISS, Pinecone, etc.
- Concepts: Token, Embedding, Encoder, Decoder, Context Window, Query, Key, Value, Softmax, etc.
- People: Vaswani, Devlin, Radford, Hinton, LeCun, Bengio, etc.
- Organizations: OpenAI, Google, Meta, DeepMind, Hugging Face, etc.

EXCLUDE: Generic words (what, when, where, how, why, which, who, it, is, the, a, provides, etc.)

Return ONLY valid JSON (no markdown, no code blocks):
{
  "entities": [
    {"name": "Specific Entity", "type": "ARCHITECTURE|TECHNIQUE|MODEL|FRAMEWORK|CONCEPT|PERSON|ORGANIZATION", "description": "Concise description of what it is"}
  ],
  "relationships": [
    {"from": "Entity A", "to": "Entity B", "relation": "uses|implements|extends|improves_over|enables|related_to|combines|alternative_to|requires|known_for|developed_by", "confidence": 0.9}
  ]
}

REQUIREMENTS:
- Extract 15-20 specific entities per chunk (be generous, capture everything relevant)
- Extract 10-15 relationships showing HOW entities connect
- Relationship confidence: 1.0 for stated facts, 0.8 for obvious inferences, 0.6 for logical deductions
- Include BOTH entity-type relationships AND more specific connection types
- Every entity should appear in at least one relationship

Text:
"""


def _filter_generic_entity(name: str) -> bool:
    """Filter out generic, low-value entities that pollute the graph.
    More permissive to capture more domain-specific entities."""
    # Ultra-generic words that are never entities
    ultra_generic = {
        "what", "when", "where", "how", "why", "which", "who", "it", "is", "the", "a", "an",
        "and", "or", "but", "for", "of", "in", "on", "at", "to", "from", "about", "by",
        "text", "document", "provides", "includes", "using", "used", "used", "various",
        "multiple", "other", "different", "time", "set", "type", "part", "feature", "method",
        "way", "example", "shown", "case", "number", "result", "form", "based", "becoming",
    }
    
    name_lower = name.lower().strip()
    
    # Reject if it's pure ultra-generic
    if name_lower in ultra_generic:
        return False
    
    # Reject if very short (< 2 chars)
    if len(name_lower) < 2:
        return False
    
    # Reject single generic words longer than 2 chars but still generic
    single_word_reject = {
        "system", "answer", "explanation", "information", "process", "step", "example",
        "allows", "enables", "makes", "shows", "learning", "training", "evaluation", "user",
        "question", "expert", "however", "different", "better", "good", "bad", "right", "wrong",
    }
    if name_lower in single_word_reject:
        return False
    
    return True


def extract_entities_and_relations(chunk: str) -> dict:
    """Use LLM to extract domain-specific entities and relationships from a text chunk."""
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a Machine Learning knowledge graph extraction engine. Extract ONLY domain-specific entities. Output only valid JSON, no markdown, no code blocks."},
                {"role": "user", "content": ENTITY_EXTRACTION_PROMPT + chunk}
            ],
            temperature=0,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()
        
        # Clean markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        
        result = json.loads(raw)
        
        # Filter out generic entities
        filtered_entities = [e for e in result.get("entities", []) if _filter_generic_entity(e.get("name", ""))]
        
        logger.debug(f"Extracted {len(filtered_entities)} quality entities (filtered from {len(result.get('entities', []))})")
        
        return {
            "entities": filtered_entities,
            "relationships": result.get("relationships", [])
        }
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {e}")
        return {"entities": [], "relationships": []}
    except Exception as e:
        logger.warning(f"Entity extraction failed: {e}")
        return {"entities": [], "relationships": []}


# ─── Embeddings ───────────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """Generate embedding for a text string using OpenAI (Groq doesn't support embeddings)."""
    try:
        from openai import OpenAI
        openai_client = OpenAI()
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:8191],  # API limit
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding failed: {e}. Using zero vector.")
        return [0.0] * 1536


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts using OpenAI, then sentence-transformers, then zeros."""
    # Try OpenAI first
    try:
        from openai import OpenAI
        openai_client = OpenAI()
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[t[:8191] for t in texts],
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.debug(f"OpenAI batch embedding failed: {e}")
    
    # Try sentence-transformers
    try:
        model = _get_sentence_transformer()
        if model:
            embeddings = model.encode([t[:8191] for t in texts])
            return embeddings.tolist()
    except Exception as e:
        logger.debug(f"Sentence-transformers batch embedding failed: {e}")
    
    # Fallback to zeros (384 dim for sentence-transformers)
    logger.warning(f"Batch embedding failed. Using zero vectors (384 dims).")
    return [[0.0] * 384 for _ in texts]


# ─── Main Ingestion ───────────────────────────────────────────────────────────

class DocumentIngestionPipeline:
    """
    Full document → Knowledge Graph ingestion pipeline.
    
    Steps:
    1. Load documents from file/directory
    2. Chunk into token-bounded segments
    3. Extract entities + relationships via LLM
    4. Generate embeddings
    5. Upsert everything into TigerGraph
    """

    def __init__(self, tg_client: TigerGraphClient):
        self.tg = tg_client
        self.stats = {
            "docs_processed": 0,
            "chunks_created": 0,
            "entities_extracted": 0,
            "relationships_extracted": 0,
            "tokens_used_for_ingestion": 0,
        }

    def ingest_directory(self, directory: str):
        """Ingest all .txt and .md files from a directory."""
        path = Path(directory)
        files = list(path.glob("*.txt")) + list(path.glob("*.md"))
        logger.info(f"Found {len(files)} documents to ingest")

        for file_path in tqdm(files, desc="Ingesting documents"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.ingest_document(
                doc_id=str(uuid.uuid4()),
                title=file_path.stem,
                content=content,
                source_url=str(file_path),
            )

    def ingest_document(self, doc_id: str, title: str, content: str, source_url: str = ""):
        """Process a single document through the full pipeline."""
        chunks = chunk_text(content)
        logger.info(f"  Doc '{title}': {len(chunks)} chunks")

        all_entity_names = set()

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            token_count = count_tokens(chunk)

            # Try to store document chunk, but don't fail if it doesn't work
            try:
                self.tg.upsert_document(
                    doc_id=chunk_id,
                    title=f"{title} [chunk {i}]",
                    content=chunk,
                    chunk_index=i,
                    token_count=token_count,
                    source_url=source_url,
                )
            except Exception as e:
                logger.debug(f"Could not store document chunk (this is OK): {e}")

            # Extract entities and relationships
            extracted = extract_entities_and_relations(chunk)
            entities = extracted.get("entities", [])
            relationships = extracted.get("relationships", [])

            self.stats["tokens_used_for_ingestion"] += count_tokens(ENTITY_EXTRACTION_PROMPT + chunk)

            # Batch embed entity descriptions
            if entities:
                descriptions = [e.get("description", e["name"]) for e in entities]
                # Skip embeddings if schema doesn't support them
                embeddings = None
                try:
                    embeddings = get_embeddings_batch(descriptions)
                except Exception as e:
                    logger.debug(f"Skipping embeddings (schema may not support): {e}")

                for entity, embedding in zip(entities, embeddings or [None]*len(entities)):
                    entity_id = self._make_entity_id(entity["name"])
                    all_entity_names.add(entity["name"])

                    try:
                        self.tg.upsert_entity(
                            entity_id=entity_id,
                            name=entity["name"],
                            entity_type=entity.get("type", "UNKNOWN"),
                            description=entity.get("description", ""),
                            embedding=embedding or [],  # Pass empty list if no embeddings
                            doc_source=source_url,
                        )
                        self.stats["entities_extracted"] += 1
                        
                        # Try to link to document
                        try:
                            self.tg.link_entity_to_document(
                                entity_id=entity_id,
                                doc_id=chunk_id,
                                frequency=1,
                                relevance_score=0.8,
                            )
                        except Exception as e:
                            logger.debug(f"Could not link entity to document: {e}")
                    except Exception as e:
                        logger.warning(f"Could not upsert entity '{entity['name']}': {e}")

            # Upsert relationships
            for rel in relationships:
                if rel.get("from") and rel.get("to"):
                    try:
                        self.tg.upsert_relationship(
                            from_entity=self._make_entity_id(rel["from"]),
                            to_entity=self._make_entity_id(rel["to"]),
                            relation_type=rel.get("relation", "RELATED_TO"),
                            confidence=float(rel.get("confidence", 0.8)),
                            context=rel.get("context", ""),
                        )
                        self.stats["relationships_extracted"] += 1
                    except Exception as e:
                        logger.debug(f"Could not create relationship: {e}")

            self.stats["chunks_created"] += 1

        self.stats["docs_processed"] += 1
        logger.info(f"  ✅ Ingested '{title}' — {len(all_entity_names)} unique entities")

    def _make_entity_id(self, name: str) -> str:
        """Normalize entity name to a stable ID."""
        return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())

    def get_stats(self) -> dict:
        return self.stats
