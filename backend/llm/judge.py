"""
LLM-as-a-Judge Evaluation
Scores answers on correctness, completeness, and relevance.
Also computes BERTScore F1.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from groq import Groq
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

_groq_client = None
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


def _get_groq_client():
    """Lazily initialize Groq client to ensure .env is loaded."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment. Check your .env file.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client

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
{answer}
"""


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
    Use LLM to score an answer on multiple dimensions.
    Returns structured scores.
    """
    prompt = JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth or "Not provided",
        answer=answer,
    )
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an impartial judge. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        data = json.loads(response.choices[0].message.content)
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


def compute_bert_score(predictions: list[str], references: list[str]) -> dict:
    """
    Compute BERTScore F1 between predicted answers and ground truths.
    Returns precision, recall, f1 (averaged).
    """
    try:
        from bert_score import score as bert_score_fn
        P, R, F1 = bert_score_fn(
            predictions,
            references,
            lang="en",
            model_type="distilbert-base-uncased",
            verbose=False,
        )
        return {
            "precision": float(P.mean()),
            "recall": float(R.mean()),
            "f1": float(F1.mean()),
        }
    except ImportError:
        logger.warning("bert-score not installed. Skipping BERTScore computation.")
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    except Exception as e:
        logger.error(f"BERTScore computation failed: {e}")
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}


def compare_answers(question: str, basic_rag_answer: str, graph_rag_answer: str,
                    ground_truth: str = "") -> dict:
    """
    Side-by-side LLM judge comparison of Basic RAG vs GraphRAG answers.
    """
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
