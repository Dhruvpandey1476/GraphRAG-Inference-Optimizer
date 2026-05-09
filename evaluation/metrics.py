"""
Metrics helpers — token counting, cost calculation, BERTScore wrappers.
"""

import os
import tiktoken
from dotenv import load_dotenv

load_dotenv()

encoder = tiktoken.get_encoding("cl100k_base")

# GPT-4o-mini pricing ($ per 1K tokens)
INPUT_COST_PER_1K  = float(os.getenv("INPUT_COST_PER_1K",  "0.00015"))
OUTPUT_COST_PER_1K = float(os.getenv("OUTPUT_COST_PER_1K", "0.0006"))


def count_tokens(text: str) -> int:
    """Count tokens in a string using cl100k_base encoding."""
    return len(encoder.encode(text))


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD for a single LLM call."""
    return (
        prompt_tokens / 1000 * INPUT_COST_PER_1K +
        completion_tokens / 1000 * OUTPUT_COST_PER_1K
    )


def token_reduction_pct(baseline_tokens: int, optimized_tokens: int) -> float:
    """Compute percentage reduction in tokens."""
    if baseline_tokens == 0:
        return 0.0
    return (baseline_tokens - optimized_tokens) / baseline_tokens * 100


def cost_per_1000_queries(avg_cost_per_query: float) -> float:
    return avg_cost_per_query * 1000


def annual_cost(daily_queries: int, avg_cost_per_query: float) -> float:
    return daily_queries * avg_cost_per_query * 365


def compute_bert_score_batch(predictions: list[str], references: list[str]) -> dict:
    """
    Compute BERTScore for a list of prediction/reference pairs.
    Returns {"precision": float, "recall": float, "f1": float}
    
    Target for bonus points:
    - Raw F1 >= 0.88
    - Rescaled F1 >= 0.55
    """
    try:
        from bert_score import score
        P, R, F1 = score(
            predictions,
            references,
            lang="en",
            model_type="distilbert-base-uncased",
            verbose=False,
            batch_size=8,
        )
        raw_f1 = float(F1.mean())
        # Rescale: F1_rescaled = (F1 - baseline) / (1 - baseline), baseline ~0.85
        baseline = 0.85
        rescaled_f1 = max(0.0, (raw_f1 - baseline) / (1 - baseline))
        return {
            "precision": float(P.mean()),
            "recall": float(R.mean()),
            "f1": raw_f1,
            "f1_rescaled": round(rescaled_f1, 4),
            "passes_threshold": raw_f1 >= 0.88 or rescaled_f1 >= 0.55,
        }
    except ImportError:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "f1_rescaled": 0.0, "passes_threshold": False}
