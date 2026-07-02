"""
Pipeline 1: LLM-Only Baseline
Raw prompt → LLM. No retrieval. No context. Just the model.
This is the worst-case baseline — highest token cost, lowest accuracy.
"""

import time
import logging
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

from ..llm.gemini_client import gemini_generate, MAX_OUTPUT_TOKENS, CONCISE_ANSWER_INSTRUCTION

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)


@dataclass
class LLMOnlyResult:
    answer: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    context_tokens: int = 0  # no retrieval → zero context
    method: str = "llm_only"


class LLMOnly:
    """
    Pipeline 1: Raw LLM with no retrieval.
    
    Sends the bare question to the LLM.
    - No context injection
    - No retrieval step
    - Relies entirely on model's parametric knowledge
    - Serves as worst-case cost/accuracy baseline
    """

    def query(self, question: str) -> LLMOnlyResult:
        t0 = time.time()

        system_prompt = (
            "You are a knowledgeable assistant. Answer the question using your "
            "training knowledge. " + CONCISE_ANSWER_INSTRUCTION
        )

        result = gemini_generate(
            system_prompt=system_prompt,
            user_prompt=question,
            temperature=0.1,
            max_tokens=MAX_OUTPUT_TOKENS,  # shared cap — equal across all 3 pipelines
        )

        latency_ms = (time.time() - t0) * 1000

        return LLMOnlyResult(
            answer=result["answer"],
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=result["total_tokens"],
            latency_ms=latency_ms,
            context_tokens=0,  # LLM-only feeds no retrieved context
        )
