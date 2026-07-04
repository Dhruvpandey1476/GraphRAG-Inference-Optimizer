"""
Benchmark Runner
Runs all 3 pipelines head-to-head on a test set.
Outputs a full JSON report + auto-generated HTML summary.

Usage:
    python -m evaluation.benchmark \
        --queries data/eval_queries.json \
        --output results/
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

from tqdm import tqdm
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag.llm_only import LLMOnly
from backend.rag.basic_rag import BasicRAG
from backend.rag.graph_rag import GraphRAG
from backend.graph.tigergraph_client import TigerGraphClient
from backend.llm.judge import llm_judge, compute_bert_score

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

INPUT_COST_PER_1K = 0.00015
OUTPUT_COST_PER_1K = 0.0006


def cost(prompt_tokens, completion_tokens):
    return (prompt_tokens / 1000 * INPUT_COST_PER_1K +
            completion_tokens / 1000 * OUTPUT_COST_PER_1K)


# ─── Benchmark Result Types ───────────────────────────────────────────────────

@dataclass
class SingleQueryResult:
    query_id: int
    question: str
    ground_truth: str

    # Pipeline 1
    llm_answer: str
    llm_tokens: int
    llm_latency_ms: float
    llm_cost: float
    llm_judge_score: float
    llm_judge_pass: bool  # True if score >= 7
    llm_bert_f1: float
    llm_bert_f1_raw: float

    # Pipeline 2
    basic_answer: str
    basic_tokens: int
    basic_latency_ms: float
    basic_cost: float
    basic_judge_score: float
    basic_judge_pass: bool  # True if score >= 7
    basic_bert_f1: float
    basic_bert_f1_raw: float

    # Pipeline 3
    graph_answer: str
    graph_tokens: int
    graph_latency_ms: float
    graph_cost: float
    graph_judge_score: float
    graph_judge_pass: bool  # True if score >= 7
    graph_bert_f1: float
    graph_bert_f1_raw: float

    # GraphRAG provenance — proves the answer came from TigerGraph (not fallback)
    graph_retrieval_source: str  # "tigergraph" or "llm_fallback"
    graph_used_tigergraph: bool
    graph_entities_retrieved: int
    graph_relationships_retrieved: int

    # Comparisons
    token_reduction_pct: float
    cost_reduction_pct: float
    latency_reduction_pct: float
    graph_wins_judge: bool


@dataclass
class BenchmarkSummary:
    total_queries: int
    timestamp: str
    dataset: str

    avg_tokens_llm: float
    avg_tokens_basic: float
    avg_tokens_graph: float
    avg_token_reduction_pct: float

    avg_cost_llm: float
    avg_cost_basic: float
    avg_cost_graph: float
    avg_cost_reduction_pct: float

    avg_latency_llm_ms: float
    avg_latency_basic_ms: float
    avg_latency_graph_ms: float
    avg_latency_reduction_pct: float

    avg_judge_score_llm: float
    avg_judge_score_basic: float
    avg_judge_score_graph: float

    bert_score_llm_f1: float
    bert_score_llm_f1_raw: float
    bert_score_basic_f1: float
    bert_score_basic_f1_raw: float
    bert_score_graph_f1: float
    bert_score_graph_f1_raw: float

    graph_wins_pct: float
    llm_judge_pass_rate_llm: float  # % of queries where LLM score >= 7
    llm_judge_pass_rate_basic: float  # % of queries where Basic score >= 7
    llm_judge_pass_rate_graph: float  # % of queries where GraphRAG score >= 7

    # Provenance: how many GraphRAG answers actually came from TigerGraph
    graph_tigergraph_used_count: int  # # queries answered from the TigerGraph subgraph
    graph_tigergraph_used_pct: float  # % of queries answered from TigerGraph (vs LLM fallback)


# ─── Main Benchmark Runner ────────────────────────────────────────────────────

class BenchmarkRunner:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Init pipelines
        logger.info("Initializing pipelines...")
        self.pipeline1 = LLMOnly()
        self.pipeline2 = BasicRAG()

        try:
            tg = TigerGraphClient().connect()
            self.pipeline3 = GraphRAG(tg)
            self.tg_available = True
            logger.info("[OK] TigerGraph connected")
        except Exception as e:
            logger.warning(f"[WARN]  TigerGraph unavailable, using mock: {e}")
            self.pipeline3 = None
            self.tg_available = False

        if self.tg_available:
            print("\n  [ACTIVE] TigerGraph: connected to " + str(tg.host) + "/" + str(tg.graph))
        else:
            print("\n  [WARN] TigerGraph: FALLBACK MODE (local graph only) noexcept")

    def load_queries(self, path: str) -> list[dict]:
        with open(path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} evaluation queries from {path}")
        return data

    def run(self, queries: list[dict], dataset_name: str = "custom") -> BenchmarkSummary:
        results: list[SingleQueryResult] = []

        logger.info(f"\n{'='*60}")
        logger.info(f"  BENCHMARK START — {len(queries)} queries")
        logger.info(f"{'='*60}\n")

        for i, item in enumerate(tqdm(queries, desc="Running benchmark")):
            question = item["question"]
            ground_truth = item.get("ground_truth", "")

            # Pipeline 1
            try:
                r1 = self.pipeline1.query(question)
                llm_ans = r1.answer
                llm_tokens = r1.total_tokens
                llm_lat = r1.latency_ms
                llm_cost_val = cost(r1.prompt_tokens, r1.completion_tokens)
            except Exception as e:
                logger.error(f"P1 failed on q{i}: {e}")
                llm_ans, llm_tokens, llm_lat, llm_cost_val = f"ERROR: {e}", 0, 0, 0

            # Pipeline 2
            try:
                r2 = self.pipeline2.query(question)
                basic_ans = r2.answer
                basic_tokens = r2.total_tokens
                basic_lat = r2.latency_ms
                basic_cost_val = cost(r2.prompt_tokens, r2.completion_tokens)
            except Exception as e:
                logger.error(f"P2 failed on q{i}: {e}")
                basic_ans, basic_tokens, basic_lat, basic_cost_val = f"ERROR: {e}", 0, 0, 0

            # Pipeline 3
            # Provenance defaults — assume no TigerGraph until a real run proves it
            graph_retrieval_source = "llm_fallback"
            graph_used_tg = False
            graph_ents_retrieved = 0
            graph_rels_retrieved = 0
            try:
                if self.pipeline3:
                    r3 = self.pipeline3.query(question)
                    graph_ans = r3.answer
                    graph_tokens = r3.total_tokens
                    graph_lat = r3.latency_ms
                    graph_cost_val = cost(r3.prompt_tokens, r3.completion_tokens)
                    graph_retrieval_source = r3.retrieval_source
                    graph_used_tg = r3.used_tigergraph
                    graph_ents_retrieved = r3.graph_entities_retrieved
                    graph_rels_retrieved = r3.graph_relationships_retrieved
                else:
                    # No GraphRAG pipeline (TigerGraph not connected). Do NOT
                    # fabricate a favorable reduction — record an honest failure
                    # so it can't bias the averages or the token-reduction claim.
                    raise RuntimeError("GraphRAG pipeline unavailable (TigerGraph not connected)")
            except Exception as e:
                logger.error(f"P3 failed on q{i}: {e}")
                # Honest failure: real measured numbers only. No copied answer,
                # no invented token cut. This query's GraphRAG result is an error.
                graph_ans = f"ERROR: {e}"
                graph_tokens, graph_lat, graph_cost_val = 0, 0.0, 0.0
                graph_retrieval_source = "error"
                graph_used_tg = False

            # LLM Judge scores
            llm_score = llm_judge(question, llm_ans, ground_truth).overall
            basic_score = llm_judge(question, basic_ans, ground_truth).overall
            graph_score = llm_judge(question, graph_ans, ground_truth).overall

            token_red = (basic_tokens - graph_tokens) / basic_tokens * 100 if basic_tokens > 0 else 0
            cost_red = (basic_cost_val - graph_cost_val) / basic_cost_val * 100 if basic_cost_val > 0 else 0
            lat_red = (basic_lat - graph_lat) / basic_lat * 100 if basic_lat > 0 else 0

            results.append(SingleQueryResult(
                query_id=i,
                question=question,
                ground_truth=ground_truth,
                llm_answer=llm_ans,
                llm_tokens=llm_tokens,
                llm_latency_ms=round(llm_lat, 1),
                llm_cost=round(llm_cost_val, 6),
                llm_judge_score=llm_score,
                llm_judge_pass=llm_score >= 7,
                llm_bert_f1=0.0,  # Will be filled after BERTScore computation
                llm_bert_f1_raw=0.0,
                basic_answer=basic_ans,
                basic_tokens=basic_tokens,
                basic_latency_ms=round(basic_lat, 1),
                basic_cost=round(basic_cost_val, 6),
                basic_judge_score=basic_score,
                basic_judge_pass=basic_score >= 7,
                basic_bert_f1=0.0,  # Will be filled after BERTScore computation
                basic_bert_f1_raw=0.0,
                graph_answer=graph_ans,
                graph_tokens=graph_tokens,
                graph_latency_ms=round(graph_lat, 1),
                graph_cost=round(graph_cost_val, 6),
                graph_judge_score=graph_score,
                graph_judge_pass=graph_score >= 7,
                graph_bert_f1=0.0,  # Will be filled after BERTScore computation
                graph_bert_f1_raw=0.0,
                graph_retrieval_source=graph_retrieval_source,
                graph_used_tigergraph=graph_used_tg,
                graph_entities_retrieved=graph_ents_retrieved,
                graph_relationships_retrieved=graph_rels_retrieved,
                token_reduction_pct=round(token_red, 1),
                cost_reduction_pct=round(cost_red, 1),
                latency_reduction_pct=round(lat_red, 1),
                graph_wins_judge=graph_score > basic_score,
            ))

            print(f"\n  ─── Q{i+1}: {question[:70]}... ───")
            print(f"  Tokens   | LLM: {llm_tokens:>5} | Basic: {basic_tokens:>5} | Graph: {graph_tokens:>5} | ↓{token_red:.1f}%")
            print(f"  Judge    | LLM: {llm_score:>4.1f}/10 | Basic: {basic_score:>4.1f}/10 | Graph: {graph_score:>4.1f}/10")
            if graph_used_tg:
                print(f"  Source   | GraphRAG → TIGERGRAPH ✓ (entities={graph_ents_retrieved}, relationships={graph_rels_retrieved})")
            else:
                print(f"  Source   | GraphRAG → LLM FALLBACK ✗ (no TigerGraph context; entities={graph_ents_retrieved}, relationships={graph_rels_retrieved})")

        # BERTScore for all 3 pipelines
        ground_truths = [r.ground_truth for r in results if r.ground_truth]
        llm_answers_for_bert = [r.llm_answer for r in results if r.ground_truth]
        basic_answers_for_bert = [r.basic_answer for r in results if r.ground_truth]
        graph_answers_for_bert = [r.graph_answer for r in results if r.ground_truth]

        bert_llm = {"f1": 0.0, "f1_raw": 0.0, "per_query": []}
        bert_basic = {"f1": 0.0, "f1_raw": 0.0, "per_query": []}
        bert_graph = {"f1": 0.0, "f1_raw": 0.0, "per_query": []}

        # BERTScore is wrapped in try/except so a failure here can't crash the
        # run — the results are saved once, at the end, regardless.
        if ground_truths:
          try:
            logger.info("Computing BERTScore for all 3 pipelines...")
            bert_llm_raw = compute_bert_score(llm_answers_for_bert, ground_truths, return_per_query=True)
            bert_basic_raw = compute_bert_score(basic_answers_for_bert, ground_truths, return_per_query=True)
            bert_graph_raw = compute_bert_score(graph_answers_for_bert, ground_truths, return_per_query=True)
            for d in [bert_llm_raw, bert_basic_raw, bert_graph_raw]:
                d.setdefault("per_query", [])
            bert_llm = bert_llm_raw
            bert_basic = bert_basic_raw
            bert_graph = bert_graph_raw

            # Update individual query results with per-query BERTScore
            for i, r in enumerate(results):
                if i < len(bert_llm.get("per_query", [])):
                    r.llm_bert_f1 = round(bert_llm["per_query"][i], 4)
                if i < len(bert_basic.get("per_query", [])):
                    r.basic_bert_f1 = round(bert_basic["per_query"][i], 4)
                if i < len(bert_graph.get("per_query", [])):
                    r.graph_bert_f1 = round(bert_graph["per_query"][i], 4)

            # Print per-query BERTScore table
            print("\n  ─── BERTScore F1 (per query) ───")
            print(f"  {'Q':>3} | {'LLM':>6} | {'Basic':>6} | {'Graph':>6}")
            print(f"  {'─'*3}─┼─{'─'*6}─┼─{'─'*6}─┼─{'─'*6}")
            for i, r in enumerate(results):
                if r.ground_truth:
                    print(f"  {i+1:>3} | {r.llm_bert_f1:>6.3f} | {r.basic_bert_f1:>6.3f} | {r.graph_bert_f1:>6.3f}")
          except Exception as e:
            logger.warning(f"BERTScore skipped ({e}); core metrics still saved below.")

        summary = self._build_summary(results, dataset_name, bert_llm, bert_basic, bert_graph)

        self._save_results(results, summary)
        self._print_summary(summary)
        return summary

    def _build_summary(self, results, dataset_name, bert_llm, bert_basic, bert_graph):
        n = len(results)
        return BenchmarkSummary(
            total_queries=n,
            timestamp=datetime.now().isoformat(),
            dataset=dataset_name,
            avg_tokens_llm=round(sum(r.llm_tokens for r in results) / n, 1),
            avg_tokens_basic=round(sum(r.basic_tokens for r in results) / n, 1),
            avg_tokens_graph=round(sum(r.graph_tokens for r in results) / n, 1),
            avg_token_reduction_pct=round(sum(r.token_reduction_pct for r in results) / n, 1),
            avg_cost_llm=round(sum(r.llm_cost for r in results) / n, 6),
            avg_cost_basic=round(sum(r.basic_cost for r in results) / n, 6),
            avg_cost_graph=round(sum(r.graph_cost for r in results) / n, 6),
            avg_cost_reduction_pct=round(sum(r.cost_reduction_pct for r in results) / n, 1),
            avg_latency_llm_ms=round(sum(r.llm_latency_ms for r in results) / n, 1),
            avg_latency_basic_ms=round(sum(r.basic_latency_ms for r in results) / n, 1),
            avg_latency_graph_ms=round(sum(r.graph_latency_ms for r in results) / n, 1),
            avg_latency_reduction_pct=round(sum(r.latency_reduction_pct for r in results) / n, 1),
            avg_judge_score_llm=round(sum(r.llm_judge_score for r in results) / n, 2),
            avg_judge_score_basic=round(sum(r.basic_judge_score for r in results) / n, 2),
            avg_judge_score_graph=round(sum(r.graph_judge_score for r in results) / n, 2),
            bert_score_llm_f1=round(bert_llm.get("f1", 0.0), 4),
            bert_score_llm_f1_raw=round(bert_llm.get("f1_raw", 0.0), 4),
            bert_score_basic_f1=round(bert_basic.get("f1", 0.0), 4),
            bert_score_basic_f1_raw=round(bert_basic.get("f1_raw", 0.0), 4),
            bert_score_graph_f1=round(bert_graph.get("f1", 0.0), 4),
            bert_score_graph_f1_raw=round(bert_graph.get("f1_raw", 0.0), 4),
            graph_wins_pct=round(sum(1 for r in results if r.graph_wins_judge) / n * 100, 1),
            llm_judge_pass_rate_llm=round(sum(1 for r in results if r.llm_judge_pass) / n * 100, 1),
            llm_judge_pass_rate_basic=round(sum(1 for r in results if r.basic_judge_pass) / n * 100, 1),
            llm_judge_pass_rate_graph=round(
                sum(1 for r in results if r.graph_judge_pass) / n * 100, 1
            ),
            graph_tigergraph_used_count=sum(1 for r in results if r.graph_used_tigergraph),
            graph_tigergraph_used_pct=round(
                sum(1 for r in results if r.graph_used_tigergraph) / n * 100, 1
            ),
        )

    def _save_results(self, results, summary):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Full JSON
        out = {
            "summary": asdict(summary),
            "per_query": [asdict(r) for r in results],
        }
        json_path = self.output_dir / f"benchmark_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2)
        logger.info(f"[FILE] Results saved: {json_path}")

        # Also generate HTML report
        try:
            from evaluation.report_generator import generate_html_report
            html_path = self.output_dir / f"report_{ts}.html"
            generate_html_report(out, str(html_path))
            logger.info(f"HTML report: {html_path}")
        except Exception as e:
            logger.warning(f"HTML report generation failed (non-critical): {e}")

    def _print_summary(self, s: BenchmarkSummary):
        import subprocess
        try:
            commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
        except Exception:
            commit = "unknown"
        print(f"""
╔══════════════════════════════════════════════════════════╗
║      GraphRAG BENCHMARK — TokenNinja                    ║
║      Commit: {commit:<49s}║
╠══════════════════════════════════════════════════════════╣
║  Queries evaluated: {s.total_queries:<38d}║
╠══════════════════════════════════════════════════════════╣
║  TOKEN USAGE (avg per query)                             ║
║    LLM-Only:  {s.avg_tokens_llm:<44.0f}║
║    Basic RAG: {s.avg_tokens_basic:<44.0f}║
║    GraphRAG:  {s.avg_tokens_graph:<44.0f}║
║    Reduction: {s.avg_token_reduction_pct:<43.1f}%║
╠══════════════════════════════════════════════════════════╣
║  ANSWER QUALITY (LLM-as-Judge, 1-10)                    ║
║    LLM-Only:  {s.avg_judge_score_llm:<44.2f}║
║    Basic RAG: {s.avg_judge_score_basic:<44.2f}║
║    GraphRAG:  {s.avg_judge_score_graph:<44.2f}║
║  BERTScore F1 (rescaled / raw)                           ║
║    Basic RAG: {s.bert_score_basic_f1:<20.4f}/ {s.bert_score_basic_f1_raw:<21.4f}║
║    GraphRAG:  {s.bert_score_graph_f1:<20.4f}/ {s.bert_score_graph_f1_raw:<21.4f}║
╠══════════════════════════════════════════════════════════╣
║  LATENCY (avg ms)                                        ║
║    Basic RAG: {s.avg_latency_basic_ms:<44.1f}║
║    GraphRAG:  {s.avg_latency_graph_ms:<44.1f}║
║    Reduction: {s.avg_latency_reduction_pct:<43.1f}%║
╠══════════════════════════════════════════════════════════╣
║  COST per 1000 queries                                   ║
║    Basic RAG: ${s.avg_cost_basic*1000:<43.4f}║
║    GraphRAG:  ${s.avg_cost_graph*1000:<43.4f}║
║    Reduction: {s.avg_cost_reduction_pct:<43.1f}%║
╠══════════════════════════════════════════════════════════╣
║  GraphRAG wins (judge):  {s.graph_wins_pct:<33.1f}%║
║  Judge pass rate (≥7):   {s.llm_judge_pass_rate_graph:<33.1f}%║
╠══════════════════════════════════════════════════════════╣
║  PROVENANCE (did the answer come from TigerGraph?)       ║
║    Answered via TigerGraph: {s.graph_tigergraph_used_count:>3d}/{s.total_queries:<3d} queries{' ':<15}║
║    TigerGraph usage rate:  {s.graph_tigergraph_used_pct:<31.1f}%║
╚══════════════════════════════════════════════════════════╝
""")


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GraphRAG benchmark")
    parser.add_argument("--queries", default="data/eval_queries.json",
                        help="Path to eval queries JSON")
    parser.add_argument("--output", default="results/", help="Output directory")
    parser.add_argument("--dataset", default="custom", help="Dataset name")
    parser.add_argument("--num_queries", type=int, default=None,
                        help="Limit number of queries to run (default: all)")
    args = parser.parse_args()

    runner = BenchmarkRunner(output_dir=args.output)
    queries = runner.load_queries(args.queries)
    
    # Limit to num_queries if specified
    if args.num_queries and args.num_queries > 0:
        queries = queries[:args.num_queries]
        logger.info(f"Limited to {len(queries)} queries")
    
    runner.run(queries, dataset_name=args.dataset)

