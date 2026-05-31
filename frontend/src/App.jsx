import { useState, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend
} from "recharts";
import { Zap, Database, GitBranch, Search, TrendingDown, Award, Clock, DollarSign, CheckCircle, AlertCircle, Loader } from "lucide-react";

// Use VITE_API_URL if set, otherwise use current origin (HuggingFace Spaces) or localhost:8001 (dev)
const API_BASE = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' ? window.location.origin : "http://localhost:8001");

const PIPELINES = [
  { id: "llm_only",  label: "LLM Only",  icon: Zap,       color: "#ef4444", dimColor: "rgba(239,68,68,0.12)",    desc: "No retrieval · Parametric only" },
  { id: "basic_rag", label: "Basic RAG", icon: Database,   color: "#f97316", dimColor: "rgba(249,115,22,0.12)",   desc: "Vector search · Top-K chunks" },
  { id: "graph_rag", label: "GraphRAG",  icon: GitBranch,  color: "#22c55e", dimColor: "rgba(34,197,94,0.12)",    desc: "TigerGraph · Subgraph traversal" },
];

const SAMPLE_QUESTIONS = [
  "What is the relationship between transformer architecture and attention mechanisms?",
  "How does GraphRAG reduce token consumption compared to Basic RAG?",
  "What metrics are used to evaluate answer quality in RAG systems?",
  "How does TigerGraph support multi-hop reasoning in knowledge graphs?",
  "What are the cost implications of token reduction at production scale?",
];

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color = "#f97316", icon: Icon }) {
  return (
    <div style={{
      background: "var(--card)", border: "1px solid var(--border)",
      borderRadius: 14, padding: "1.1rem 1.3rem",
      borderTop: `2px solid ${color}`,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span style={{ fontSize: ".72rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: ".06em" }}>{label}</span>
        {Icon && <Icon size={15} color={color} />}
      </div>
      <div style={{ fontSize: "1.75rem", fontWeight: 800, color, marginTop: ".3rem", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: ".72rem", color: "var(--text-secondary)", marginTop: ".3rem" }}>{sub}</div>}
    </div>
  );
}

// ─── Pipeline Answer Card ────────────────────────────────────────────────────
function PipelineCard({ pipeline, data, loading }) {
  const { label, color, dimColor, desc, icon: Icon } = pipeline;
  return (
    <div style={{
      background: "var(--card)", border: `1px solid ${color}33`,
      borderRadius: 16, padding: "1.25rem", display: "flex", flexDirection: "column", gap: ".9rem",
      boxShadow: loading ? "none" : `0 0 20px ${color}18`,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: ".6rem" }}>
        <div style={{ background: dimColor, borderRadius: 8, padding: ".45rem", display: "flex" }}>
          <Icon size={18} color={color} />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: ".95rem", color }}>{label}</div>
          <div style={{ fontSize: ".72rem", color: "var(--text-muted)" }}>{desc}</div>
        </div>
      </div>

      {/* Metrics Row */}
      {data && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: ".6rem" }}>
          {[
            { icon: Database, label: "Tokens", val: data.total_tokens?.toLocaleString() },
            { icon: Clock, label: "Latency", val: `${data.latency_ms?.toFixed(0)}ms` },
            { icon: DollarSign, label: "Cost", val: `$${(data.cost_usd * 1000).toFixed(3)}/k` },
          ].map(({ icon: MIcon, label: ml, val }) => (
            <div key={ml} style={{
              background: "var(--surface)", borderRadius: 9, padding: ".55rem .65rem",
              border: "1px solid var(--border-light)",
            }}>
              <div style={{ fontSize: ".65rem", color: "var(--text-muted)", marginBottom: ".2rem" }}>{ml}</div>
              <div style={{ fontWeight: 700, fontSize: ".92rem", color: "var(--text)" }}>{val ?? "—"}</div>
            </div>
          ))}
        </div>
      )}

      {/* Answer */}
      <div style={{
        background: "var(--surface)", borderRadius: 10, padding: "1rem",
        border: "1px solid var(--border-light)", minHeight: 120, flex: 1,
        fontSize: ".85rem", lineHeight: 1.65, color: "var(--text-secondary)",
      }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: ".6rem", color: "var(--text-muted)" }}>
            <Loader size={14} className="spin" />
            <span>Running pipeline...</span>
          </div>
        ) : data ? (
          <span style={{ color: "var(--text)" }}>{data.answer}</span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>Answer will appear here after you submit a query.</span>
        )}
      </div>

      {/* Judge Score */}
      {data?.judge_score !== undefined && (
        <div style={{
          display: "flex", alignItems: "center", gap: ".5rem",
          fontSize: ".78rem", color: "var(--text-muted)",
        }}>
          <Award size={13} color={color} />
          <span>Judge Score: <strong style={{ color }}>{data.judge_score}/10</strong></span>
        </div>
      )}
    </div>
  );
}

// ─── Token Bar Chart ─────────────────────────────────────────────────────────
function TokenChart({ results }) {
  if (!results) return null;
  const data = [
    { name: "LLM Only",  tokens: results.llm_only.total_tokens,  fill: "#ef4444" },
    { name: "Basic RAG", tokens: results.basic_rag.total_tokens, fill: "#f97316" },
    { name: "GraphRAG",  tokens: results.graph_rag.total_tokens, fill: "#22c55e" },
  ];
  return (
    <div style={{ background: "var(--card)", borderRadius: 14, padding: "1.25rem", border: "1px solid var(--border)" }}>
      <div style={{ fontWeight: 700, marginBottom: "1rem", fontSize: ".9rem" }}>Token Usage Comparison</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} barCategoryGap="35%">
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #1e3a5f", borderRadius: 8, fontSize: 13 }}
            cursor={{ fill: "rgba(255,255,255,.04)" }}
          />
          <Bar dataKey="tokens" radius={[6,6,0,0]}>
            {data.map((d, i) => <Cell key={i} fill={d.fill} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Accuracy Radar ───────────────────────────────────────────────────────────
function AccuracyRadar({ judgeScores }) {
  if (!judgeScores) return null;
  const { basic_rag_score: b, graph_rag_score: g } = judgeScores;
  const data = [
    { axis: "Correctness",  basic: b.correctness,  graph: g.correctness },
    { axis: "Completeness", basic: b.completeness, graph: g.completeness },
    { axis: "Clarity",      basic: b.clarity,      graph: g.clarity },
    { axis: "Relevance",    basic: b.relevance,    graph: g.relevance },
  ];
  return (
    <div style={{ background: "var(--card)", borderRadius: 14, padding: "1.25rem", border: "1px solid var(--border)" }}>
      <div style={{ fontWeight: 700, marginBottom: "1rem", fontSize: ".9rem" }}>Answer Quality (LLM-as-Judge)</div>
      <ResponsiveContainer width="100%" height={200}>
        <RadarChart data={data}>
          <PolarGrid stroke="#1e3a5f" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "#64748b", fontSize: 11 }} />
          <Radar name="Basic RAG" dataKey="basic" stroke="#f97316" fill="#f97316" fillOpacity={0.18} />
          <Radar name="GraphRAG"  dataKey="graph"  stroke="#22c55e" fill="#22c55e" fillOpacity={0.25} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1e3a5f", borderRadius: 8, fontSize: 12 }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Reduction Badge ─────────────────────────────────────────────────────────
function ReductionBadge({ label, pct, icon: Icon }) {
  const good = pct > 0;
  const color = good ? "#22c55e" : "#ef4444";
  return (
    <div style={{
      background: good ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
      border: `1px solid ${color}44`, borderRadius: 10,
      padding: ".75rem 1rem", display: "flex", flexDirection: "column", gap: ".25rem",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: ".4rem", fontSize: ".72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
        <Icon size={12} color={color} />{label}
      </div>
      <div style={{ fontWeight: 800, fontSize: "1.5rem", color }}>
        {good ? "↓" : "↑"}{Math.abs(pct).toFixed(1)}%
      </div>
      <div style={{ fontSize: ".7rem", color: "var(--text-muted)" }}>vs Basic RAG</div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [question, setQuestion] = useState("");
  const [groundTruth, setGroundTruth] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [sessionStats, setSessionStats] = useState(null);

  const fetchSessionStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/stats/session`);
      if (r.ok) setSessionStats(await r.json());
    } catch {}
  }, []);

  const handleQuery = useCallback(async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await fetch(`${API_BASE}/query/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), ground_truth: groundTruth, run_judge: true }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();

      // Attach judge scores to individual pipelines for display
      if (data.judge_scores) {
        const js = data.judge_scores;
        data.basic_rag.judge_score = js.basic_rag_score?.overall;
        data.graph_rag.judge_score = js.graph_rag_score?.overall;
      }
      setResults(data);
      fetchSessionStats();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [question, groundTruth, loading, fetchSessionStats]);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* Header */}
      <header style={{
        background: "var(--surface)", borderBottom: "1px solid var(--border)",
        padding: "1rem 2rem", display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, zIndex: 100, backdropFilter: "blur(10px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".75rem" }}>
          <span style={{ fontSize: "1.5rem" }}>🐯</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: "1.1rem", color: "var(--orange)" }}>GraphRAG Inference Dashboard</div>
            <div style={{ fontSize: ".72rem", color: "var(--text-muted)" }}>TigerGraph Hackathon · 3-Pipeline Comparison</div>
          </div>
        </div>
        {sessionStats && (
          <div style={{ display: "flex", gap: "1.5rem", fontSize: ".8rem" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: "var(--text-muted)", fontSize: ".68rem" }}>QUERIES RUN</div>
              <div style={{ fontWeight: 700, color: "var(--blue)" }}>{sessionStats.total_queries}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: "var(--text-muted)", fontSize: ".68rem" }}>TOKENS SAVED</div>
              <div style={{ fontWeight: 700, color: "var(--green)" }}>{sessionStats.total_tokens_saved?.toLocaleString()}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: "var(--text-muted)", fontSize: ".68rem" }}>AVG REDUCTION</div>
              <div style={{ fontWeight: 700, color: "var(--green)" }}>{sessionStats.avg_token_reduction_pct}%</div>
            </div>
          </div>
        )}
      </header>

      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "2rem" }}>

        {/* Query Input */}
        <div style={{
          background: "var(--card)", borderRadius: 16, padding: "1.5rem",
          border: "1px solid var(--border)", marginBottom: "1.5rem",
          boxShadow: "0 0 40px rgba(249,115,22,0.06)",
        }}>
          <div style={{ fontWeight: 700, marginBottom: "1rem", color: "var(--text)", display: "flex", alignItems: "center", gap: ".5rem" }}>
            <Search size={16} color="var(--orange)" /> Enter Your Query
          </div>

          {/* Sample questions */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: ".5rem", marginBottom: "1rem" }}>
            {SAMPLE_QUESTIONS.map((q, i) => (
              <button key={i} onClick={() => setQuestion(q)} style={{
                background: "var(--surface)", border: "1px solid var(--border-light)",
                borderRadius: 20, padding: ".3rem .8rem", fontSize: ".72rem",
                color: "var(--text-secondary)", cursor: "pointer",
                transition: "all .15s",
              }}
              onMouseEnter={e => e.target.style.borderColor = "var(--orange)"}
              onMouseLeave={e => e.target.style.borderColor = "var(--border-light)"}
              >{q.substring(0, 55)}…</button>
            ))}
          </div>

          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Ask a question across all three pipelines simultaneously…"
            rows={3}
            style={{
              width: "100%", background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 10, padding: ".9rem 1rem", color: "var(--text)", fontSize: ".9rem",
              resize: "vertical", lineHeight: 1.6, outline: "none", fontFamily: "inherit",
              marginBottom: ".75rem", transition: "border-color .15s",
            }}
            onFocus={e => e.target.style.borderColor = "var(--orange)"}
            onBlur={e => e.target.style.borderColor = "var(--border)"}
            onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleQuery()}
          />

          <input
            value={groundTruth}
            onChange={e => setGroundTruth(e.target.value)}
            placeholder="Ground truth answer (optional — for BERTScore & Judge evaluation)"
            style={{
              width: "100%", background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 10, padding: ".65rem 1rem", color: "var(--text)", fontSize: ".82rem",
              outline: "none", fontFamily: "inherit", marginBottom: "1rem", transition: "border-color .15s",
            }}
            onFocus={e => e.target.style.borderColor = "var(--blue)"}
            onBlur={e => e.target.style.borderColor = "var(--border)"}
          />

          <button
            onClick={handleQuery}
            disabled={!question.trim() || loading}
            style={{
              background: question.trim() && !loading ? "var(--orange)" : "var(--surface)",
              color: question.trim() && !loading ? "white" : "var(--text-muted)",
              border: "none", borderRadius: 10, padding: ".75rem 2rem",
              fontWeight: 700, fontSize: ".9rem", cursor: question.trim() && !loading ? "pointer" : "default",
              display: "flex", alignItems: "center", gap: ".5rem", transition: "all .2s",
            }}
          >
            {loading ? <><Loader size={16} /> Running all 3 pipelines…</> : <><Zap size={16} /> Run All Pipelines</>}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "rgba(239,68,68,0.1)", border: "1px solid #ef444444",
            borderRadius: 10, padding: "1rem", marginBottom: "1.5rem",
            color: "#f87171", display: "flex", alignItems: "center", gap: ".5rem",
          }}>
            <AlertCircle size={16} /> {error} — Is the backend running? (<code>uvicorn api.server:app --reload</code>)
          </div>
        )}

        {/* Results */}
        {results && (
          <>
            {/* Reduction Badges */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
              <ReductionBadge label="Token Reduction" pct={results.token_reduction_pct} icon={TrendingDown} />
              <ReductionBadge label="Cost Reduction" pct={results.cost_reduction_pct} icon={DollarSign} />
              <ReductionBadge label="Latency Reduction" pct={results.latency_reduction_pct} icon={Clock} />
            </div>

            {/* Charts Row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
              <TokenChart results={results} />
              <AccuracyRadar judgeScores={results.judge_scores} />
            </div>

            {/* Judge Winner Banner */}
            {results.judge_scores && (
              <div style={{
                background: results.judge_scores.winner === "graph_rag"
                  ? "rgba(34,197,94,0.1)" : results.judge_scores.winner === "tie"
                  ? "rgba(156,163,175,0.1)"
                  : "rgba(249,115,22,0.1)",
                border: `1px solid ${results.judge_scores.winner === "graph_rag" 
                  ? "#22c55e44" : results.judge_scores.winner === "tie"
                  ? "#9ca3af44"
                  : "#f9731644"}`,
                borderRadius: 12, padding: "1rem 1.25rem", marginBottom: "1.5rem",
                display: "flex", alignItems: "center", gap: ".75rem",
              }}>
                <CheckCircle size={18} color={results.judge_scores.winner === "graph_rag" 
                  ? "#22c55e" : results.judge_scores.winner === "tie"
                  ? "#9ca3af"
                  : "#f97316"} />
                <div>
                  <strong style={{ color: results.judge_scores.winner === "graph_rag" 
                    ? "#22c55e" : results.judge_scores.winner === "tie"
                    ? "#9ca3af"
                    : "#f97316" }}>
                    {results.judge_scores.winner === "graph_rag" 
                      ? "✨ GraphRAG wins" 
                      : results.judge_scores.winner === "tie"
                      ? "🤝 It's a tie"
                      : "📊 Basic RAG wins"} this query
                  </strong>
                  <span style={{ color: "var(--text-muted)", fontSize: ".82rem", marginLeft: ".5rem" }}>
                    (score improvement: {results.judge_scores.improvement > 0 ? "+" : ""}{results.judge_scores.improvement?.toFixed(1)} pts)
                  </span>
                </div>
              </div>
            )}
          </>
        )}

        {/* 3 Pipeline Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
          {PIPELINES.map(p => (
            <PipelineCard
              key={p.id}
              pipeline={p}
              data={results?.[p.id]}
              loading={loading}
            />
          ))}
        </div>

        {/* Metric Summary Table */}
        {results && (
          <div style={{ background: "var(--card)", borderRadius: 14, padding: "1.25rem", border: "1px solid var(--border)", marginBottom: "2rem" }}>
            <div style={{ fontWeight: 700, marginBottom: "1rem", fontSize: ".9rem" }}>📊 Full Metrics Table</div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".83rem" }}>
                <thead>
                  <tr>
                    {["Metric", "LLM Only", "Basic RAG", "GraphRAG", "Graph vs Basic"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: ".6rem .75rem", color: "var(--text-muted)", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: "Prompt Tokens",     llm: results.llm_only.prompt_tokens,     basic: results.basic_rag.prompt_tokens,     graph: results.graph_rag.prompt_tokens,     better: "lower" },
                    { label: "Completion Tokens",  llm: results.llm_only.completion_tokens,  basic: results.basic_rag.completion_tokens,  graph: results.graph_rag.completion_tokens,  better: "lower" },
                    { label: "Total Tokens",       llm: results.llm_only.total_tokens,       basic: results.basic_rag.total_tokens,       graph: results.graph_rag.total_tokens,       better: "lower" },
                    { label: "Latency (ms)",       llm: results.llm_only.latency_ms?.toFixed(0), basic: results.basic_rag.latency_ms?.toFixed(0), graph: results.graph_rag.latency_ms?.toFixed(0), better: "lower" },
                    { label: "Cost ($)",           llm: results.llm_only.cost_usd?.toFixed(5), basic: results.basic_rag.cost_usd?.toFixed(5), graph: results.graph_rag.cost_usd?.toFixed(5), better: "lower" },
                    { label: "Judge Score",        llm: "—",                                  basic: results.judge_scores?.basic_rag_score?.overall?.toFixed(1) ?? "—", graph: results.judge_scores?.graph_rag_score?.overall?.toFixed(1) ?? "—", better: "higher" },
                  ].map(row => {
                    const basicNum = parseFloat(row.basic);
                    const graphNum = parseFloat(row.graph);
                    const graphBetter = row.better === "lower" ? graphNum < basicNum : graphNum > basicNum;
                    const pctDiff = basicNum > 0 ? ((graphNum - basicNum) / basicNum * 100).toFixed(1) : null;
                    return (
                      <tr key={row.label} style={{ borderBottom: "1px solid var(--border-light)" }}>
                        <td style={{ padding: ".55rem .75rem", color: "var(--text-secondary)", fontWeight: 500 }}>{row.label}</td>
                        <td style={{ padding: ".55rem .75rem", color: "#ef4444" }}>{row.llm}</td>
                        <td style={{ padding: ".55rem .75rem", color: "#f97316" }}>{row.basic}</td>
                        <td style={{ padding: ".55rem .75rem", color: "#22c55e", fontWeight: 700 }}>{row.graph}</td>
                        <td style={{ padding: ".55rem .75rem" }}>
                          {pctDiff !== null && (
                            <span style={{
                              background: graphBetter ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                              color: graphBetter ? "#22c55e" : "#ef4444",
                              borderRadius: 6, padding: ".15rem .45rem", fontSize: ".75rem", fontWeight: 700,
                            }}>
                              {pctDiff > 0 ? "+" : ""}{pctDiff}%
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer style={{ textAlign: "center", color: "var(--text-muted)", fontSize: ".75rem", paddingTop: "1rem", borderTop: "1px solid var(--border)" }}>
          🐯 Built for the TigerGraph GraphRAG Inference Hackathon &nbsp;·&nbsp;
          GraphRAG = fewer tokens, better answers &nbsp;·&nbsp;
          <a href="https://github.com/tigergraph/graphrag" style={{ color: "var(--orange)", textDecoration: "none" }}>github.com/tigergraph/graphrag</a>
        </footer>
      </main>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
        button:hover:not(:disabled) { opacity: .88; transform: translateY(-1px); }
      `}</style>
    </div>
  );
}
