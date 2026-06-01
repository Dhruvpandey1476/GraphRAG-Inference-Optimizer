import google.generativeai as genai
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"), override=True)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# Test with simple prompt first
print("TEST 1: Simple short question")
response1 = model.generate_content(
    "What is TigerGraph?",
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 200,
    }
)
print(f"Answer: {response1.text[:100]}")
print(f"Finish reason: {response1.candidates[0].finish_reason if response1.candidates else 'N/A'}")
print(f"Tokens: {response1.usage_metadata.candidates_token_count}")

print("\n" + "="*70)
print("TEST 2: Longer prompt with guidance")
response2 = model.generate_content(
    """You are a helpful assistant. Answer comprehensively.

What is TigerGraph and what are its main features?""",
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 800,
    }
)
print(f"Answer: {response2.text[:150]}")
print(f"Finish reason: {response2.candidates[0].finish_reason if response2.candidates else 'N/A'}")
print(f"Tokens: {response2.usage_metadata.candidates_token_count}")
