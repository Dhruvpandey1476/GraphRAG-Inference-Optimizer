# 🐯 GraphRAG Inference Optimizer
### TigerGraph GraphRAG Inference Hackathon — Round 2 Submission

> **Reducing LLM token consumption by 60–80% while maintaining answer quality using TigerGraph's graph-native retrieval.**

---

## 🚀 What We Built

A full **GraphRAG pipeline** that replaces Basic RAG's brute-force document chunking with intelligent, graph-traversal-based context retrieval. By retrieving only the *structurally relevant* subgraph — entities, relationships, and 2-hop neighbors — instead of top-K raw text chunks, we dramatically reduce token overhead while improving reasoning quality.

### Key Results

| Metric | Basic RAG | GraphRAG (Ours) | Improvement |
|--------|-----------|-----------------|-------------|
| Avg Tokens/Query | ~3,200 | ~780 | **75.6% reduction** |
| Cost/1000 Queries | ~$9.60 | ~$2.34 | **75.6% savings** |
| BERTScore F1 | 0.81 | 0.87 | **+7.4% improvement** |
| LLM-as-Judge Score | 6.8/10 | 8.4/10 | **+23.5% improvement** |
| Avg Latency | 2.1s | 1.4s | **33% faster** |

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌──────────────────────────────────────────────────────┐
│              GraphRAG Inference Pipeline              │
│                                                      │
│  Query → Entity Extraction → TigerGraph Traversal   │
│       → Subgraph Context → Prompt Assembly           │
│       → LLM Inference → Answer + Token Metrics      │
└──────────────────────────────────────────────────────┘
    │                           │
    ▼                           ▼
TigerGraph Savanna         OpenAI / Claude
(Knowledge Graph)          (LLM Backend)
```

### Components

1. **`backend/rag/basic_rag.py`** — Baseline: vector similarity top-K retrieval
2. **`backend/rag/graph_rag.py`** — GraphRAG: entity-anchored subgraph traversal
3. **`backend/rag/llm_only.py`** — No-retrieval baseline: pure LLM inference
4. **`backend/graph/tigergraph_client.py`** — TigerGraph connection + GSQL queries
5. **`backend/graph/ingestion.py`** — Document → Knowledge Graph pipeline
6. **`backend/llm/gemini_client.py`** — Google Gemini API wrapper
7. **`backend/llm/judge.py`** — LLM-as-Judge evaluation with realistic 1-10 scoring
8. **`backend/api/server.py`** — FastAPI server with /health and /query/compare endpoints
9. **`evaluation/benchmark.py`** — 50-query benchmark comparing all 3 pipelines
10. **`evaluation/metrics.py`** — BERTScore F1, token counting, cost calculations
11. **`evaluation/report_generator.py`** — Auto HTML report generation
12. **`frontend/`** — React + Vite dashboard with live query execution and metrics
13. **`docs/blog_post.md`** — Full technical blog post for publication
14. **`docs/architecture.md`** — System architecture deep-dive
15. **`docs/demo_video_script.md`** — 2-3 minute demo narration script

---

## ⚡ Quick Start

### 1. Prerequisites

```bash
python >= 3.10
node >= 18
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
cp .env.example .env
# Fill in your TigerGraph Savanna credentials + OpenAI key
```

### 3. Download ArXiv Dataset

The benchmark uses 17,317 arXiv papers (131.2M tokens) for evaluation. Download them:

```bash
python scripts/download_arxiv_bulk.py
# Downloads to data/arxiv_bulk/ (~3-4 GB)
# (Excluded from Git due to size)
```

### 4. Set Up TigerGraph Schema

```bash
python scripts/setup_tigergraph.py
```

### 5. Ingest Documents

```bash
python scripts/ingest_documents.py --data data/arxiv_bulk/
```

### 6. Run Backend API

```bash
# From the project root (graphrag-hackathon/):
uvicorn backend.api.server:app --reload --port 8000
```

### 7. Run Frontend Dashboard

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 8. Run Full Benchmark

```bash
python evaluation/benchmark.py --queries data/eval_queries.json --output results/
# Runs 50-query benchmark comparing all 3 RAG pipelines
# Generates report_FINAL.html with metrics
```

---

## 📁 File Structure

```
graphrag-hackathon/
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── .gitattributes                     # Line ending configuration
│
├── backend/                           # Core inference backend
│   ├── api/
│   │   └── server.py                  # FastAPI server (port 8000)
│   ├── rag/
│   │   ├── llm_only.py               # Baseline: pure LLM (no retrieval)
│   │   ├── basic_rag.py              # Baseline: vector similarity RAG
│   │   └── graph_rag.py              # GraphRAG: entity-anchored subgraph
│   ├── graph/
│   │   ├── tigergraph_client.py      # TigerGraph connection & GSQL
│   │   └── ingestion.py              # Document → KG pipeline
│   └── llm/
│       ├── gemini_client.py          # Google Gemini API wrapper
│       └── judge.py                  # LLM-as-Judge evaluator
│
├── evaluation/                        # Benchmark & metrics
│   ├── benchmark.py                  # 50-query benchmark runner
│   ├── metrics.py                    # BERTScore, token counting, costs
│   └── report_generator.py           # HTML report generation
│
├── frontend/                          # React dashboard
│   ├── src/
│   │   ├── App.jsx                   # Main dashboard component
│   │   ├── main.jsx                  # React entry point
│   │   └── index.css                 # Styles
│   ├── index.html                    # HTML entry point
│   ├── package.json                  # Node dependencies
│   ├── vite.config.js                # Vite build config
│   └── .env                          # Frontend API URL
│
├── scripts/                           # Setup & utility scripts
│   ├── setup_tigergraph.py           # Initialize TigerGraph schema
│   ├── ingest_documents.py           # Load documents into KG
│   ├── download_arxiv_bulk.py        # Download arXiv papers
│   ├── count_tokens_gemini.py        # Gemini token counting
│   └── verify_tokens_gemini.py       # Verify token counts
│
├── docs/                              # Documentation
│   ├── architecture.md               # System architecture
│   ├── blog_post.md                 # Technical blog post
│   ├── demo_video_script.md         # 2-3 min demo narration
│   └── ARCHITECTURE_DIAGRAM.svg      # Visual architecture
│
├── data/                              # Evaluation data (queries in Git, papers require download)
│   ├── eval_queries.json             # 50 benchmark queries with ground truth
│   ├── eval_queries_16.json          # 16 test queries for quick validation
│   ├── sample_docs/
│   │   └── ai_knowledge_base.md      # Sample knowledge base for testing
│   ├── arxiv_bulk/                   # 17,317 arXiv papers (NOT in Git - download via script)
│   │   └── hf_*.txt                  # Individual arXiv papers
│   └── arxiv_papers/                 # Additional papers (optional)
│
└── results/                           # Benchmark results
    ├── benchmark_20260530_115007.json # Latest benchmark data
    └── report_FINAL.html             # Latest HTML report
```

---

## 📊 Evaluation Data

### Query Files
- **`eval_queries.json`** — 50 expert-crafted questions covering:
  - Transformer architectures & attention mechanisms
  - BERT vs GPT differences
  - LLM hallucinations & factual accuracy
  - Knowledge graphs & graph-based retrieval
  - RAG system evaluation & metrics
  
  Each query includes a ground-truth answer for evaluation.

- **`eval_queries_16.json`** — Quick validation set (16 queries, ~2 min runtime)

### Dataset
- **`data/arxiv_bulk/`** — 17,317 arXiv papers in Computer Science (2018-2024)
  - **131.2M tokens** (verified by Gemini API)
  - Exceeds 100M token requirement by 31%
  - Excluded from Git (3-4 GB) — download via `python scripts/download_arxiv_bulk.py`

### Why Separate Query & Data Files
1. **eval_queries.json** = Standardized benchmark (runs against any data source)
2. **arxiv_bulk/** = Large external knowledge base (for information retrieval)
3. **Separation** = Allows comparing GraphRAG vs Basic RAG vs LLM-Only on the same queries

---

1. **Token Reduction (30% weight)**: We show concrete, reproducible 75%+ token savings via graph-native retrieval — the graph gives us *exactly* what's needed, not a pile of potentially-relevant chunks.

2. **Answer Quality (30% weight)**: Multi-hop graph traversal lets the LLM reason across relationships, not just semantic similarity — answering questions that Basic RAG gets wrong.

3. **Performance (20% weight)**: Graph queries resolve in <200ms. Total pipeline latency is 33% lower than Basic RAG.

4. **Engineering & Storytelling (20% weight)**: Live dashboard, reproducible benchmarks, comprehensive blog post, clean modular architecture.

---

## 📊 How the Evaluation Works

```
For each test query:
  1. Run Basic RAG → log tokens, answer, latency
  2. Run GraphRAG → log tokens, answer, latency  
  3. Score both answers with LLM-as-Judge (1-10)
  4. Compute BERTScore F1 vs ground truth
  5. Record all metrics to results/benchmark_results.json
  6. Generate HTML report automatically
```

---

## 🔑 Environment Variables

```
TIGERGRAPH_HOST=your-savanna-host.tgcloud.io
TIGERGRAPH_GRAPH=GraphRAGDemo
TIGERGRAPH_USERNAME=tigergraph
TIGERGRAPH_PASSWORD=your-password
TIGERGRAPH_SECRET=your-secret

OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

EMBEDDING_MODEL=text-embedding-3-small
```

---

## 📝 License

MIT — Built for the TigerGraph GraphRAG Inference Hackathon 2026.

