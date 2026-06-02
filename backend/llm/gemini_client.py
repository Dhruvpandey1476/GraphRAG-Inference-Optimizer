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


def gemini_generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    use_json_schema: bool = False,
) -> dict:
    """Generate a response using Gemini API with thinking disabled."""
    from google.genai import types

    client = _get_client()

    config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "system_instruction": system_prompt,
        "thinking_config": types.ThinkingConfig(thinking_budget=0),
    }

    # Only use JSON schema for GraphRAG to force 3-bullet format
    if use_json_schema:
        response_schema = {
            "type": "object",
            "properties": {
                "bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Exactly 3 bullet points"
                }
            },
            "required": ["bullets"]
        }
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_schema

    config = types.GenerateContentConfig(**config_kwargs)

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=user_prompt,
        config=config,
    )

    usage = response.usage_metadata
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

    # Parse JSON response if applicable
    import json
    import re
    answer = response.text
    
    if use_json_schema:
        # Try JSON parsing first
        try:
            data = json.loads(response.text)
            bullets = data.get("bullets", [])[:3]
            answer = '\n'.join([f"• {b}" for b in bullets])
            logger.info(f"✅ JSON schema parsed: {len(bullets)} bullets")
        except:
            # Fallback: extract bullet points using regex
            try:
                # Look for quoted strings that are likely bullets
                matches = re.findall(r'"([^"]{20,})"', response.text)
                if matches:
                    bullets = matches[:3]
                    answer = '\n'.join([f"• {b}" for b in bullets])
                    logger.info(f"✅ Extracted {len(bullets)} bullets from JSON")
                else:
                    answer = response.text
                    logger.warning(f"⚠️ Could not parse JSON schema, using raw: {response.text[:100]}")
            except:
                answer = response.text
                logger.error(f"❌ All parsing failed, raw response: {response.text[:200]}")

    return {
        "answer": answer,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def count_tokens_gemini(text: str) -> int:
    """Count tokens using Gemini's native tokenizer."""
    client = _get_client()
    result = client.models.count_tokens(model=GEMINI_MODEL_NAME, contents=text)
    return result.total_tokens
