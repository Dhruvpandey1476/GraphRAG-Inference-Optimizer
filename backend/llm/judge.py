"""
LLM-as-a-Judge Evaluation (1-10 Scale)
Uses Gemini for structured grading + BERTScore F1 with rescaling.
Meets TigerGraph Hackathon Round 2 requirements.
"""

import os
import re
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)


# ─── Shared Gemini for judge ─────────────────────────────────────────────────

def _judge_gemini_call(prompt: str) -> str:
    """Call Gemini for judge evaluation."""
    from .gemini_client import gemini_generate
    result = gemini_generate(
        system_prompt="You are an impartial AI judge. Return only valid JSON.",
        user_prompt=prompt,
        temperature=0,
        max_tokens=500,
    )
    return result["answer"]


# ─── 1-10 Scale Judge ────────────────────────────────────────────────────────

JUDGE_PROMPT = """You are an impartial AI judge evaluating the quality of an answer to a question.

Score the answer on a scale of 1-10 based on:
- Correctness (is the information accurate and factually sound?)
- Completeness (does it fully answer the question without gaps?)
- Clarity (is it well-structured, concise, and easy to understand?)
- Relevance (does it stay on topic and avoid irrelevant information?)

Be strict and differentiate between good and poor answers. Use the full 1-10 scale:
- 1-3: Poor, inaccurate, incomplete, or irrelevant
- 4-6: Acceptable, some issues but generally on track  
- 7-8: Good, mostly accurate and complete with minor issues
- 9-10: Excellent, accurate, comprehensive, and well-structured

Return ONLY a JSON object with this exact format:
{{
  "score": <integer 1-10>,
  "correctness": <integer 1-10>,
  "completeness": <integer 1-10>,
  "clarity": <integer 1-10>,
  "relevance": <integer 1-10>,
  "reasoning": "<one sentence explanation>"
}}

Question: {question}

Ground Truth (if available): {ground_truth}

Answer to evaluate:
{answer}"""


@dataclass
class JudgeScore:
    overall: float
    correctness: float
    completeness: float
    clarity: float
    relevance: float
    reasoning: str


def llm_judge(question: str, answer: str, ground_truth: str = "") -> JudgeScore:
    """
    Use LLM to score an answer on multiple dimensions (1-10).
    Returns structured scores.
    """
    prompt = JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth or "Not provided",
        answer=answer,
    )
    try:
        raw = _judge_gemini_call(prompt)
        # Clean markdown wrappers
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)
        return JudgeScore(
            overall=float(data.get("score", 5)),
            correctness=float(data.get("correctness", 5)),
            completeness=float(data.get("completeness", 5)),
            clarity=float(data.get("clarity", 5)),
            relevance=float(data.get("relevance", 5)),
            reasoning=data.get("reasoning", ""),
        )
    except Exception as e:
        logger.error(f"LLM Judge failed: {e}")
        return JudgeScore(5.0, 5.0, 5.0, 5.0, 5.0, f"Evaluation failed: {e}")


# ─── BERTScore ───────────────────────────────────────────────────────────────

def compute_bert_score(predictions: list[str], references: list[str]) -> dict:
    """
    Compute BERTScore F1 between predicted answers and ground truths.
    Uses roberta-large with rescale_with_baseline=True as required.
    Returns both rescaled and raw F1 scores.
    """
    try:
        import evaluate
        bertscore = evaluate.load("bertscore")

        model_type = "roberta-large"

        # Compute raw first (no rescaling)
        results_raw = bertscore.compute(
            predictions=predictions,
            references=references,
            lang="en",
            model_type=model_type,
        )
        raw_f1 = sum(results_raw["f1"]) / len(results_raw["f1"])

        # Compute with rescaling
        results = bertscore.compute(
            predictions=predictions,
            references=references,
            lang="en",
            model_type=model_type,
            rescale_with_baseline=True,
        )

        f1_scores = results["f1"]
        precision_scores = results["precision"]
        recall_scores = results["recall"]

        avg_f1 = sum(f1_scores) / len(f1_scores)
        avg_precision = sum(precision_scores) / len(precision_scores)
        avg_recall = sum(recall_scores) / len(recall_scores)

        return {
            "precision": round(float(avg_precision), 4),
            "recall": round(float(avg_recall), 4),
            "f1": round(float(avg_f1), 4),        # rescaled
            "f1_raw": round(float(raw_f1), 4),     # raw
        }
    except ImportError:
        logger.warning("evaluate/bert-score not installed. Skipping BERTScore.")
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "f1_raw": 0.0}
    except Exception as e:
        logger.error(f"BERTScore computation failed: {e}")
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "f1_raw": 0.0}


# ─── Side-by-side Comparison ─────────────────────────────────────────────────

def compare_answers(question: str, basic_rag_answer: str, graph_rag_answer: str,
                    ground_truth: str = "") -> dict:
    """Side-by-side LLM judge comparison of Basic RAG vs GraphRAG answers."""
    basic_score = llm_judge(question, basic_rag_answer, ground_truth)
    graph_score = llm_judge(question, graph_rag_answer, ground_truth)

    return {
        "question": question,
        "basic_rag_score": {
            "overall": basic_score.overall,
            "correctness": basic_score.correctness,
            "completeness": basic_score.completeness,
            "clarity": basic_score.clarity,
            "relevance": basic_score.relevance,
            "reasoning": basic_score.reasoning,
        },
        "graph_rag_score": {
            "overall": graph_score.overall,
            "correctness": graph_score.correctness,
            "completeness": graph_score.completeness,
            "clarity": graph_score.clarity,
            "relevance": graph_score.relevance,
            "reasoning": graph_score.reasoning,
        },
        "winner": "graph_rag" if graph_score.overall > basic_score.overall else
                  "basic_rag" if basic_score.overall > graph_score.overall else "tie",
        "improvement": graph_score.overall - basic_score.overall,
    }
