# Architecture Deep Dive — GraphRAG Inference System

## System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         GraphRAG Inference System                          │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    React Dashboard (Port 5173)                       │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │  │
│  │  │  Query Input   │  │ Token BarChart  │  │   Accuracy RadarChart  │ │  │
│  │  │  Sample Q's    │  │ (Recharts)      │  │   (LLM-as-Judge)       │ │  │
│  │  └───────┬────────┘  └────────────────┘  └────────────────────────┘ │  │
│  │          │ POST /query/compare                                        │  │
│  └──────────┼───────────────────────────────────────────────────────────┘  │
│             │                                                              │
│  ┌──────────▼───────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Server (Port 8000)                         │  │
│  │                                                                      │  │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │  │
│  │  │  Pipeline 1  │  │   Pipeline 2      │  │     Pipeline 3       │  │  │
│  │  │  LLM Only    │  │   Basic RAG       │  │     GraphRAG         │  │  │
│  │  │              │  │                   │  │                      │  │  │
│  │  │  • sys prompt│  │  • embed query    │  │  • extract entities  │  │  │
│  │  │  • question  │  │  • FAISS search   │  │  • TG traversal      │  │  │
│  │  │  • LLM call  │  │  • top-K chunks   │  │  • serialize graph   │  │  │
│  │  │              │  │  • LLM call       │  │  • LLM call          │  │  │
│  │  └──────┬───────┘  └───────┬──────────┘  └──────────┬───────────┘  │  │
│  │         │                  │                          │              │  │
│  │         └──────────────────┴──────────────────────────┘              │  │
│  │                            │                                          │  │
│  │                   ┌────────▼────────┐                                │  │
│  │                   │  LLM-as-Judge   │                                │  │
│  │                   │  + Metrics Agg  │                                │  │
│  │                   └────────┬────────┘                                │  │
│  └────────────────────────────┼────────────────────────────────────────┘  │
│                               │                                            │
└───────────────────────────────┼────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
   ┌──────────▼──────────┐             ┌──────────▼──────────┐
   │   FAISS Vector DB   │             │   TigerGraph Savanna │
   │   (in-memory/pkl)   │             │   Knowledge Graph    │
   │                     │             │                      │
   │  chunks[]           │             │  Entity vertices     │
   │  embeddings[]       │             │  RELATED_TO edges    │
   │  IndexFlatIP        │             │  MENTIONED_IN edges  │
   └─────────────────────┘             └──────────────────────┘
                                                │
                                     ┌──────────▼──────────┐
                                     │   OpenAI API         │
                                     │   (LLM + Embeddings) │
                                     └─────────────────────┘
```

---

## Component Details

### 1. Ingestion Pipeline (`backend/graph/ingestion.py`)

Converts raw documents into the knowledge graph:

```
Raw Docs (.txt/.md)
    │
    ▼  chunk_text() — token-aware, 512 tokens + 64 overlap
Document Chunks
    │
    ▼  extract_entities_and_relations() — GPT-4o-mini JSON extraction
Entities + Relationships
    │
    ├─▶ get_embeddings_batch() — text-embedding-3-small
    │       │
    │       ▼
    │   Entity embeddings (for future vector-on-graph hybrid)
    │
    ├─▶ tg.upsert_entity() — Entity vertex in TigerGraph
    ├─▶ tg.upsert_document() — Document vertex in TigerGraph
    ├─▶ tg.upsert_relationship() — RELATED_TO edge
    └─▶ tg.link_entity_to_document() — MENTIONED_IN edge
```

Simultaneously, all raw chunks are added to FAISS for Pipeline 2.

### 2. Basic RAG Pipeline (`backend/rag/basic_rag.py`)

```
User Query
    │
    ▼  openai.embeddings.create() → 1536-dim vector
Query Vector
    │
    ▼  faiss.IndexFlatIP.search() — cosine similarity
Top-K Chunk Indices (K=5)
    │
    ▼  Concatenate chunk texts
Context String (~3,000 tokens)
    │
    ▼  openai.chat.completions.create()
Answer + Token Usage
```

Token overhead: system prompt (~50) + context (~3,000) + question (~50) = ~3,100 prompt tokens

### 3. GraphRAG Pipeline (`backend/rag/graph_rag.py`)

```
User Query
    │
    ▼  extract_query_entities() — LLM → ["Entity A", "Entity B"]
Seed Entities
    │
    ▼  tg.get_entity_subgraph() — GSQL multi-hop traversal
Subgraph {entities[], relationships[], documents[]}
    │
    ▼  serialize_subgraph() — compact structured text
Graph Context (~400-800 tokens)
    │
    ▼  openai.chat.completions.create()
Answer + Token Usage
```

Token overhead: system prompt (~60) + graph context (~600) + question (~50) = ~710 prompt tokens

**Token reduction: ~77%**

### 4. LLM-as-a-Judge (`backend/llm/judge.py`)

```
Question + Answer + Ground Truth
    │
    ▼  GPT-4o-mini with JSON response format
{
  "score": 8,
  "correctness": 9,
  "completeness": 7,
  "clarity": 8,
  "relevance": 8,
  "reasoning": "..."
}
```

Run for both Basic RAG and GraphRAG answers. Used for per-query comparison and aggregate pass rate.

### 5. BERTScore Evaluation (`evaluation/benchmark.py`)

```python
from bert_score import score as bert_score_fn
P, R, F1 = bert_score_fn(
    predictions=[graph_answers],
    references=[ground_truths],
    lang="en",
    model_type="distilbert-base-uncased"
)
```

Target: F1 rescaled ≥ 0.55 (raw ≥ 0.88) for bonus points.

---

## Knowledge Graph Schema

### Vertices

| Type | Key Attributes | Purpose |
|------|---------------|---------|
| Entity | name, entity_type, description, embedding | Core knowledge nodes |
| Document | title, content, chunk_index, token_count | Source text chunks |
| Concept | name, category, importance_score | High-level topics |

### Edges

| Type | Direction | Attributes | Purpose |
|------|-----------|-----------|---------|
| RELATED_TO | Entity ↔ Entity | relation_type, confidence, context | Core relationships |
| MENTIONED_IN | Entity → Document | frequency, relevance_score | Entity-source links |
| HAS_CONCEPT | Document → Concept | weight | Topic tagging |
| CO_OCCURS_WITH | Entity ↔ Entity | co_occurrence_count | Statistical co-occurrence |

---

## Subgraph Serialization Format

The key to token efficiency is our compact serialization format:

```
## ENTITIES
• [Entity Name] [TYPE]: description text

## RELATIONSHIPS
• Entity A —[RELATION_TYPE]→ Entity B (conf: 0.95) | context snippet

## SUPPORTING TEXT (top-1 doc, max 300 chars)
[Document Title]: first 300 characters of relevant chunk...
```

This format is:
- Hierarchically structured (LLM can parse with zero instruction)
- Non-redundant (each fact stated once)
- Confidence-weighted (LLM can trust high-confidence facts more)
- Bounded (caps prevent runaway token usage)

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Server health + TG connection status |
| POST | /query/compare | Run all 3 pipelines, return full metrics |
| GET | /stats/session | Cumulative session token savings |
| GET | /graph/stats | TigerGraph vertex/edge counts |
| POST | /ingest/text | Quick-ingest a document |

---

## Performance Characteristics

| Operation | Typical Latency |
|-----------|----------------|
| Query embedding (OpenAI) | 150–300ms |
| FAISS search (100K chunks) | <10ms |
| Entity extraction (LLM) | 300–600ms |
| TigerGraph GSQL traversal | 50–200ms |
| LLM generation (gpt-4o-mini) | 800–2000ms |
| LLM Judge evaluation | 300–600ms |
| **Total: Basic RAG** | **~1,500–2,500ms** |
| **Total: GraphRAG** | **~1,000–1,800ms** |

GraphRAG's latency advantage comes from:
1. No FAISS search needed (graph traversal replaces it)
2. Smaller context = faster LLM generation
3. No chunk deduplication step needed

---

## Scaling Considerations (Round 2)

For 50-100M token datasets:
- TigerGraph Savanna handles billions of edges natively — no schema changes needed
- FAISS upgrades to `IndexIVFFlat` or `HNSW` for ANN search at scale
- Ingestion parallelized with async batch processing
- Entity extraction cached — same entities aren't re-extracted across document runs
- Community detection (TigerGraph built-in) adds global context layer for broad queries
