import google.generativeai as genai
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"), override=True)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# Try without setting max_output_tokens (use default)
print("TEST: No max_output_tokens limit specified")
response = model.generate_content(
    """You are a helpful assistant. Answer comprehensively.

What is TigerGraph and what are its main features?""",
    generation_config={
        "temperature": 0.2,
    }
)
print(f"Answer:\n{response.text}")
print(f"\nFinish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
print(f"Completion tokens: {response.usage_metadata.candidates_token_count}")
print(f"Answer length: {len(response.text)} chars")
