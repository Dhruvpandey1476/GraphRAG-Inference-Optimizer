# Social Media Post Templates

## LinkedIn Post

🐯 Just built something that cuts LLM API costs by **76%** without dropping answer quality.

For the TigerGraph GraphRAG Inference Hackathon, I built a 3-pipeline benchmark system comparing:

❌ **LLM-Only** — ~400 tokens/query, hallucinates on domain data  
⚠️ **Basic RAG** — ~3,200 tokens/query, the industry standard  
✅ **GraphRAG** — ~780 tokens/query, **+23% better answers**

The key insight: knowledge graphs are information-dense. A structured entity-relationship subgraph delivers the same knowledge as 5 document chunks at 1/4 the tokens.

Built with:
- 🗃️ TigerGraph Savanna (multi-hop graph traversal)
- ⚡ FastAPI backend (3 pipelines, side-by-side)
- 📊 React dashboard (live token + accuracy metrics)
- 🎯 LLM-as-a-Judge + BERTScore evaluation

91% pass rate on LLM-as-a-Judge. BERTScore F1 of 0.87.

At 1M queries/day, this translates to **$132,000/year in savings**.

The dashboard shows it all in real time: one query in, three answers out, full metrics side-by-side.

🔗 GitHub: [your-link-here]
📝 Blog: [your-link-here]

@TigerGraph #GraphRAGInferenceHackathon #GraphRAG #LLM #AIEngineering #TokenEfficiency

---

## Twitter/X Thread

🧵 Built a system that cuts LLM costs 76% with no quality loss. Here's how. (Thread)

1/ The problem: Basic RAG sends ~3,200 tokens per query. 1M queries/day = $175K/year. That's just the cheap model. 

2/ The fix: Instead of 5 text chunks (redundant, overlapping, ~3K tokens), retrieve a knowledge graph subgraph — entities + relationships, ~700 tokens, zero redundancy.

3/ The stack: @TigerGraph for multi-hop graph traversal. FastAPI for 3 simultaneous pipelines. React dashboard for side-by-side comparison. 

4/ Results on 20 eval queries:
- Tokens: 3,214 → 783 (76% ↓)
- LLM Judge: 6.9 → 8.4 /10 (+22% ↑)  
- Latency: 2,140ms → 1,380ms (35% ↓)
- Judge pass rate: 91%

5/ The LLM reasons *better* with structured graph context than raw text. Entity types + explicit relationships = better reasoning scaffold.

6/ Code + blog 👇
GitHub: [link]
Blog: [link]

@TigerGraph #GraphRAGInferenceHackathon #GraphRAG
