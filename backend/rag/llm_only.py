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
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

LLM_MODEL = "gemini-2.0-flash"

_genai_client = None
encoder = tiktoken.get_encoding("cl100k_base")


def _get_genai_client():
    """Lazily initialize Gemini client to ensure .env is loaded."""
    global _genai_client
    if _genai_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment. Check your .env file.")
        genai.configure(api_key=api_key)
        _genai_client = genai.GenerativeModel(LLM_MODEL)
    return _genai_client


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

        client = _get_genai_client()
        full_prompt = f"{system_prompt}\n\n{question}"
        response = client.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
            )
        )

        latency_ms = (time.time() - t0) * 1000
        
        # Estimate token counts since Gemini doesn't return exact counts in response
        prompt_tokens = len(encoder.encode(full_prompt))
        completion_tokens = len(encoder.encode(response.text))

        return LLMOnlyResult(
            answer=response.text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
        )
