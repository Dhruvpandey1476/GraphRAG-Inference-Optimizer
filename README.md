# 🐯 GraphRAG Inference Optimizer
### TigerGraph GraphRAG Inference Hackathon

> **91.5% token reduction with maintained answer quality, using TigerGraph 2-hop knowledge-graph retrieval + Gemini 2.5 Flash. 100% of GraphRAG answers are grounded in a real TigerGraph traversal.**

---

## 🎯 Benchmark Results (50 queries, live TigerGraph run)

| Metric | LLM-Only | Basic RAG | **GraphRAG** | **vs Basic RAG** |
|--------|----------|-----------|-------------|-----------------|
| **Avg Tokens** | 134 | 2,843 | **242** | **91.5% ↓** |
| **Judge Score** | 8.38/10 | 8.26/10 | **8.20/10** | Maintained (Δ0.06) |
| **BERTScore F1 (raw)** | 0.882 | 0.876 | **0.883** | **highest** |
| **Cost / 1k queries** | $0.057 | $0.472 | **$0.071** | **84.9% ↓** |
| **Latency** | 1,284ms | 1,881ms | 3,474ms | graph-traversal trade-off |
| **Pass Rate ≥7/10** | 98% | 94% | **96%** | ✅ |
| **TigerGraph-sourced** | — | — | **100% (50/50)** | provenance ✅ |

**Status:** Submission-ready. Fair baselines (all ≈8/10 — no handicapping). GraphRAG matches accuracy at a fraction of the tokens, with every answer provably from the graph. Annual savings: **≈$146,000 @ 1M queries/day** vs Basic RAG.

---

## 🚀 Quick Start

### Option A: Run with Docker
```bash
docker build -t graphrag .
docker run -p 7860:7860 --env-file .env graphrag
# Open http://localhost:7860
```

### Option B: Run Locally
```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Create .env file with credentials
cp .env.example .env
# Edit with your TigerGraph + Gemini API keys

# Start backend
uvicorn backend.api.server:app --host 0.0.0.0 --port 8000

# In new terminal: Start frontend
cd frontend
npm run dev
# Open http://localhost:5173
```

### Option C: Test Single Query
```python
from backend.rag.graph_rag import graph_rag

result = graph_rag("What is transformer architecture?")
print(f"Tokens: {result['total_tokens']}")      # Expected: ~242
print(f"Answer: {result['answer']}")
print(f"Judge Score: {result['judge_score']}")  # Expected: ~8.2
```

---

## 🏗️ Architecture

**Visual Architecture Diagram:**

<img src="docs/ARCHITECTURE_DIAGRAM.svg" alt="Architecture Diagram" width="900"/>

---

## 📁 Project Structure

```
graphrag-hackathon/
├── backend/                           # Core inference engine
│   ├── api/server.py                  # FastAPI server (port 7860/8000)
│   ├── rag/
│   │   ├── graph_rag.py              # Main GraphRAG pipeline
│   │   ├── basic_rag.py              # FAISS baseline
│   │   └── llm_only.py               # No-retrieval baseline
│   ├── graph/
│   │   ├── tigergraph_client.py      # TigerGraph connection
│   │   └── ingestion.py              # Document ingestion
│   └── llm/
│       ├── gemini_client.py          # Gemini API wrapper
│       └── judge.py                  # LLM-as-Judge evaluator
│
├── evaluation/                        # Benchmarking
│   ├── benchmark.py                  # Compare all 3 pipelines
│   ├── metrics.py                    # Token/cost/quality metrics
│   └── report_generator.py           # HTML report generation
│
├── frontend/                             # React + Vite dashboard
│   |── src/App.jsx                    # Live 3-pipeline comparison UI
│   ├── package.json
|   └── vite.config.js
|
├── scripts/                           # Setup utilities
│   ├── setup_tigergraph.py           # Initialize schema
│   └── ingest_documents.py           # Load documents
│   └── reingest_enhanced.py          # Re-ingest with improved entity extraction
| 
├── docs/                              # Documentation
│   ├── architecture.md               # System design
│   ├── blog_post.md                  # Technical blog
│   └── ARCHITECTURE_DIAGRAM.svg      # System diagram
│
├── data/
│   ├── eval_queries.json             # 50+ benchmark queries
│   └── sample_docs/ai_knowledge_base.md
|
├── results/                           # Evaluation Results
│   ├── benchmark_<timestamp>.json      # 50-query benchmark (91.5% token reduction)
│   └── report_<timestamp>.html         # HTML report generated per run
|
├── Dockerfile                         # Docker container config
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
└── .env.example                       # Environment template
```

---

## 🔌 API Endpoints

### POST `/query/compare`
Compare all 3 pipelines on a single query.

**Request:**
```json
{
  "query": "What is transformer architecture?"
}
```

**Response:**
```json
{
  "llm_only": {
    "answer": "Transformers are neural network architectures...",
    "tokens": 134,
    "latency_ms": 1284,
    "judge_score": 8.4
  },
  "basic_rag": {
    "answer": "Transformers introduced the self-attention mechanism...",
    "tokens": 2843,
    "latency_ms": 1881,
    "judge_score": 8.3
  },
  "graph_rag": {
    "answer": "Transformers use multi-head self-attention for parallel sequence processing; the architecture underpins BERT and GPT.",
    "tokens": 242,
    "latency_ms": 3474,
    "judge_score": 8.2
  }
}
```

### GET `/health`
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

## ⚙️ Configuration

Create `.env` from `.env.example`:

```bash
# TigerGraph Savanna
TIGERGRAPH_HOST=tg-xxxxxx.tgcloud.io
TIGERGRAPH_GRAPH=TigerGraph
TIGERGRAPH_USERNAME=your-username
TIGERGRAPH_PASSWORD=your-password
TIGERGRAPH_SECRET=your-secret

# Google Gemini
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash

# App Config
APP_ENV=production
LOG_LEVEL=INFO
MAX_HOPS_GRAPH_RAG=2
MAX_NEIGHBORS=5
MAX_FRONTIER=6
```

---

## 💡 Key Optimizations

### 1. **Graph-Native Retrieval**
- 2-hop TigerGraph traversal from query entities instead of top-K text chunks
- Compact entity + relationship *triples* as context, not raw prose
- Result: **91.5% fewer tokens** than Basic RAG, 100% graph-sourced

### 2. **Dense Subgraph Serialization**
- Top entities + highest-confidence relationships, deduplicated
- ≈70 context tokens vs ≈2,800 for concatenated document chunks

### 3. **Fair, Consistent Prompting**
- All three pipelines share the same model, temperature (0.1), output cap, and conciseness instruction
- Retrieved context used as support with fallback to the model's own expertise — no pipeline handicapped
- Result: **all pipelines ≈8.2–8.4/10** — the gain is efficiency, not quality loss

---

## 🧪 Run Benchmark

```bash

# Full benchmark (50+ queries, ~15 min)
python -m evaluation.benchmark --queries data/eval_queries.json

# Output: results/report_YYYY_MMDD_HHMMSS.html
```

---

## 🎯 Why GraphRAG Wins

1. **Radical Token Efficiency** — Graph-native retrieval vs vector brute-force
2. **Maintained Quality** — ≈8.2/10 judge score, matching Basic RAG and the raw LLM, with the highest BERTScore of the three
3. **Engineering Excellence** — Clean modular code, live dashboard, reproducible benchmarks
4. **Cost-Effective** — ≈85% cheaper than Basic RAG on cloud APIs

---

## 📝 License

MIT License — Built for TigerGraph GraphRAG Inference Hackathon 2026

---

**For details:** See [docs/architecture.md](docs/architecture.md), [docs/blog_post.md](docs/blog_post.md)

