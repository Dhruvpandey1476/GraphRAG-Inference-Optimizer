"""
Auto-generates a polished HTML benchmark report from JSON results.
"""

import json
from datetime import datetime


def generate_html_report(data: dict, output_path: str):
    summary = data["summary"]
    queries = data.get("per_query", [])

    token_reduction = summary["avg_token_reduction_pct"]
    cost_reduction = summary["avg_cost_reduction_pct"]
    latency_reduction = summary["avg_latency_reduction_pct"]
    judge_graph = summary["avg_judge_score_graph"]
    judge_basic = summary["avg_judge_score_basic"]
    bert_graph = summary["bert_score_graph_f1"]
    bert_basic = summary["bert_score_basic_f1"]
    pass_rate = summary["llm_judge_pass_rate_graph"]

    # Build query rows
    query_rows = ""
    for r in queries[:20]:  # cap at 20 for readability
        color = "#22c55e" if r["graph_wins_judge"] else "#f59e0b"
        query_rows += f"""
        <tr>
            <td class="q-col">{r["question"][:80]}...</td>
            <td>{r["basic_tokens"]}</td>
            <td>{r["graph_tokens"]}</td>
            <td style="color:{color};font-weight:bold">{r["token_reduction_pct"]}%</td>
            <td>{r["basic_judge_score"]:.1f}</td>
            <td>{r["graph_judge_score"]:.1f}</td>
            <td style="color:{color}">{"✅ Graph" if r["graph_wins_judge"] else "⚠️ Basic"}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GraphRAG Benchmark Report</title>
<style>
  :root {{
    --orange: #f97316;
    --dark: #0f172a;
    --card: #1e293b;
    --border: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --green: #22c55e;
    --blue: #38bdf8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--dark); color: var(--text); padding: 2rem; }}
  h1 {{ font-size: 2rem; color: var(--orange); margin-bottom: .25rem; }}
  .subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }}
  .card .label {{ font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: .5rem; }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: var(--orange); }}
  .card .sub {{ font-size: .8rem; color: var(--muted); margin-top: .25rem; }}
  h2 {{ font-size: 1.25rem; color: var(--text); margin: 2rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: .5rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
  th {{ background: var(--card); color: var(--muted); padding: .75rem; text-align: left; font-weight: 600; border-bottom: 1px solid var(--border); }}
  td {{ padding: .65rem .75rem; border-bottom: 1px solid #1e293b; }}
  tr:hover td {{ background: rgba(255,255,255,.03); }}
  .q-col {{ max-width: 300px; color: var(--muted); font-size: .8rem; }}
  .bar-row {{ display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; }}
  .bar-label {{ width: 120px; font-size: .85rem; color: var(--muted); }}
  .bar-track {{ flex: 1; background: var(--border); border-radius: 999px; height: 20px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 999px; display: flex; align-items: center; padding-left: .5rem; font-size: .75rem; font-weight: 700; color: white; }}
  .badge {{ display: inline-block; padding: .2rem .6rem; border-radius: 6px; font-size: .75rem; font-weight: 700; }}
  .badge-green {{ background: #16653a; color: #4ade80; }}
  .badge-orange {{ background: #7c3500; color: #fb923c; }}
  footer {{ margin-top: 3rem; color: var(--muted); font-size: .8rem; text-align: center; }}
</style>
</head>
<body>
<h1>🐯 GraphRAG Inference Benchmark Report</h1>
<p class="subtitle">Dataset: {summary["dataset"]} &nbsp;|&nbsp; {summary["total_queries"]} queries &nbsp;|&nbsp; {summary["timestamp"][:10]}</p>

<div class="grid">
  <div class="card">
    <div class="label">Token Reduction</div>
    <div class="value">{token_reduction:.1f}%</div>
    <div class="sub">GraphRAG vs Basic RAG</div>
  </div>
  <div class="card">
    <div class="label">Cost Reduction</div>
    <div class="value">{cost_reduction:.1f}%</div>
    <div class="sub">per query savings</div>
  </div>
  <div class="card">
    <div class="label">Latency Reduction</div>
    <div class="value">{latency_reduction:.1f}%</div>
    <div class="sub">ms per query</div>
  </div>
  <div class="card">
    <div class="label">Judge Score (Graph)</div>
    <div class="value">{judge_graph:.1f}<span style="font-size:1rem;color:var(--muted)">/10</span></div>
    <div class="sub">vs {judge_basic:.1f} Basic RAG</div>
  </div>
  <div class="card">
    <div class="label">BERTScore F1</div>
    <div class="value">{bert_graph:.3f}</div>
    <div class="sub">vs {bert_basic:.3f} Basic RAG</div>
  </div>
  <div class="card">
    <div class="label">Judge Pass Rate</div>
    <div class="value">{pass_rate:.1f}%</div>
    <div class="sub">scores ≥ 7/10</div>
  </div>
</div>

<h2>Pipeline Token Comparison</h2>
<div style="margin-bottom:2rem">
  <div class="bar-row">
    <span class="bar-label">LLM-Only</span>
    <div class="bar-track">
      <div class="bar-fill" style="width:100%;background:#ef4444">{summary["avg_tokens_llm"]:.0f} tokens</div>
    </div>
  </div>
  <div class="bar-row">
    <span class="bar-label">Basic RAG</span>
    <div class="bar-track">
      <div class="bar-fill" style="width:{min(100, summary["avg_tokens_basic"]/max(summary["avg_tokens_llm"],1)*100):.0f}%;background:#f97316">{summary["avg_tokens_basic"]:.0f} tokens</div>
    </div>
  </div>
  <div class="bar-row">
    <span class="bar-label">GraphRAG ✨</span>
    <div class="bar-track">
      <div class="bar-fill" style="width:{min(100, summary["avg_tokens_graph"]/max(summary["avg_tokens_llm"],1)*100):.0f}%;background:#22c55e">{summary["avg_tokens_graph"]:.0f} tokens</div>
    </div>
  </div>
</div>

<h2>Per-Query Results (first 20)</h2>
<table>
  <thead>
    <tr>
      <th>Question</th>
      <th>Basic Tokens</th>
      <th>Graph Tokens</th>
      <th>Reduction</th>
      <th>Basic Score</th>
      <th>Graph Score</th>
      <th>Winner</th>
    </tr>
  </thead>
  <tbody>{query_rows}</tbody>
</table>

<footer>Generated by GraphRAG Inference Hackathon benchmark runner &nbsp;|&nbsp; TigerGraph 2026</footer>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
