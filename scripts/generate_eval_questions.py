#!/usr/bin/env python3
"""
Phase 4 — Generate corpus-grounded eval questions (cheap, ~$5-10).

Samples ML-rich chunks from the SAME corpus (faiss_index.pkl) and has Gemini
write, for each, a specific question + gold answer that can only be answered
from that passage. This makes retrieval genuinely matter: LLM-only can no longer
answer from parametric memory, so GraphRAG's grounded answers can win on both
tokens and accuracy — the story the hackathon rewards.

Output: data/eval_corpus_queries.json  ([{question, ground_truth}, ...])

Usage:
    python -m scripts.generate_eval_questions --num 50
"""

import re
import sys
import json
import time
import pickle
import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.llm.gemini_client import gemini_generate
from scripts.build_corpus_graph import _CANON_COMPILED  # reuse the ML vocabulary

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
FAISS_PKL = ROOT / "data" / "faiss_index.pkl"
OUT = ROOT / "data" / "eval_corpus_queries.json"

PROMPT = (
    "You are creating an evaluation question from a research-paper passage.\n"
    "Write ONE specific question that can be answered ONLY using facts stated in "
    "the passage (not general knowledge), plus a concise 2-3 sentence gold answer "
    "grounded in the passage. The question must name concrete entities/methods so "
    "it is retrievable. Return ONLY JSON: {\"question\": \"...\", \"answer\": \"...\"}\n\n"
    "Passage:\n"
)


def canon_count(text: str) -> int:
    return sum(1 for _, rx in _CANON_COMPILED if rx.search(text))


def main(num: int, min_canon: int, delay: float):
    data = pickle.load(open(FAISS_PKL, "rb"))
    chunks = data["chunks"]
    logger.info(f"Loaded {len(chunks)} chunks")

    # Candidate chunks: ML-rich (>= min_canon canonical terms) and substantial.
    candidates = [i for i, c in enumerate(chunks)
                  if len(c) > 400 and canon_count(c) >= min_canon]
    logger.info(f"{len(candidates)} ML-rich candidate chunks")
    if not candidates:
        logger.error("No candidates found; lower --min-canon.")
        return

    # Evenly spaced sample across the corpus (reproducible, no RNG).
    step = max(1, len(candidates) // num)
    picks = candidates[::step][:num]

    out = []
    for i in tqdm(picks, desc="Generating Q/A"):
        try:
            resp = gemini_generate(
                system_prompt="Return only valid JSON. No markdown.",
                user_prompt=PROMPT + chunks[i][:2500],
                temperature=0.3, max_tokens=400,
            )
            txt = resp["answer"].strip()
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt)
            obj = json.loads(txt)
            q, a = obj.get("question", "").strip(), obj.get("answer", "").strip()
            if q and a:
                out.append({"question": q, "ground_truth": a, "source_chunk": i})
        except Exception as e:
            logger.warning(f"chunk {i} failed: {e}")
        if delay:
            time.sleep(delay)

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    logger.info(f"[OK] Wrote {len(out)} corpus-grounded questions -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate corpus-grounded eval questions (Phase 4)")
    ap.add_argument("--num", type=int, default=50)
    ap.add_argument("--min-canon", type=int, default=3, help="Min ML terms per source chunk")
    ap.add_argument("--delay", type=float, default=0.0, help="Seconds between calls (free-tier throttle)")
    args = ap.parse_args()
    main(args.num, args.min_canon, args.delay)
