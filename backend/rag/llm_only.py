"""
Pipeline 1: LLM-Only Baseline
Raw prompt → LLM. No retrieval. No context. Just the model.
This is the worst-case baseline — highest token cost, lowest accuracy.
"""

import os
import time
import logging
from pathlib import Path
from dataclasses import dataclass
import tiktoken
from groq import Groq
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

_groq_client = None
encoder = tiktoken.get_encoding("cl100k_base")


def _get_groq_client():
    """Lazily initialize Groq client to ensure .env is loaded."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment. Check your .env file.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


@dataclass
class LLMOnlyResult:
    answer: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    method: str = "llm_only"


class LLMOnly:
    """
    Pipeline 1: Raw LLM with no retrieval.
    
    Sends the bare question to the LLM.
    - No context injection
    - No retrieval step
    - Relies entirely on model's parametric knowledge
    - Hallucinates on domain-specific / recent data
    - Serves as worst-case cost/accuracy baseline
    """

    def query(self, question: str) -> LLMOnlyResult:
        t0 = time.time()

        system_prompt = (
            "You are a knowledgeable assistant. Answer the following question "
            "as accurately as possible using your training knowledge."
        )

        client = _get_groq_client()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
            max_tokens=512,
        )

        latency_ms = (time.time() - t0) * 1000
        usage = response.usage

        return LLMOnlyResult(
            answer=response.choices[0].message.content,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
        )
