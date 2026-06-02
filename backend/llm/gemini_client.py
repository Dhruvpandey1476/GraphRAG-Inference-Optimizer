"""
Shared Gemini Client — Used by all 3 pipelines + judge.
Uses google.genai SDK with thinking disabled for token efficiency.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

_client = None
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _get_client():
    """Lazily initialize Genai client."""
    global _client
    if _client is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        _client = genai.Client(api_key=api_key)
        logger.info(f"Gemini client initialized: {GEMINI_MODEL_NAME}")
    return _client


def _make_thinking_config():
    """Create thinking config to disable thinking, handling SDK version differences."""
    try:
        from google.genai import types
        # Try thinking_budget (newer SDK)
        return types.ThinkingConfig(thinking_budget=0)
    except Exception:
        pass
    try:
        from google.genai import types
        # Try mode-based disable (older SDK)
        return types.ThinkingConfig(mode="off")
    except Exception:
        pass
    return None


def gemini_generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> dict:
    """Generate a response using Gemini API with thinking disabled."""
    from google.genai import types

    client = _get_client()
    thinking = _make_thinking_config()

    try:
        config_kwargs = dict(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )
        if thinking is not None:
            config_kwargs["thinking_config"] = thinking

        config = types.GenerateContentConfig(**config_kwargs)
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=user_prompt,
            config=config,
        )
    except Exception as e:
        # If thinking config fails, retry without it
        logger.warning(f"Retrying without thinking config: {e}")
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=user_prompt,
            config=config,
        )

    usage = response.usage_metadata
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
    total_tokens = prompt_tokens + completion_tokens

    return {
        "answer": response.text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def count_tokens_gemini(text: str) -> int:
    """Count tokens using Gemini's native tokenizer."""
    client = _get_client()
    result = client.models.count_tokens(model=GEMINI_MODEL_NAME, contents=text)
    return result.total_tokens
