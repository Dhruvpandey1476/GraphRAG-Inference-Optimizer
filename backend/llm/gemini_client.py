"""
Shared Gemini Client — Used by all 3 pipelines + judge.
Provides a unified interface for LLM calls via Google Gemini API.
"""

import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

_gemini_model = None
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _get_gemini_model():
    """Lazily initialize Gemini model."""
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. "
                "DM Devanshu on WhatsApp to get your $50 Gemini API key."
            )
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info(f"✅ Gemini model initialized: {GEMINI_MODEL_NAME}")
    return _gemini_model


def gemini_generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 512,
) -> dict:
    """
    Generate a response using Gemini API.
    
    Returns dict with:
        - answer: str
        - prompt_tokens: int
        - completion_tokens: int
        - total_tokens: int
    """
    model = _get_gemini_model()
    
    # Gemini uses a combined prompt approach
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    
    response = model.generate_content(
        full_prompt,
        generation_config=generation_config,
    )
    
    # Extract token counts from usage metadata
    usage = response.usage_metadata
    prompt_tokens = getattr(usage, "prompt_token_count", 0)
    completion_tokens = getattr(usage, "candidates_token_count", 0)
    total_tokens = getattr(usage, "total_token_count", prompt_tokens + completion_tokens)
    
    return {
        "answer": response.text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def count_tokens_gemini(text: str) -> int:
    """Count tokens using Gemini's native tokenizer."""
    model = _get_gemini_model()
    result = model.count_tokens(text)
    return result.total_tokens
