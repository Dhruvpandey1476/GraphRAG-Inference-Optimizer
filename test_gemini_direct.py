import google.generativeai as genai
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"), override=True)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

system_prompt = (
    "You are an expert and knowledgeable assistant. Provide thorough, "
    "accurate answers using your deep training knowledge. Be comprehensive "
    "and explain concepts clearly."
)

user_prompt = """Answer this question in detail:

What is TigerGraph?

Provide a well-structured, comprehensive answer that explains concepts clearly."""

full_prompt = f"{system_prompt}\n\n{user_prompt}"

generation_config = {
    "temperature": 0.2,
    "max_output_tokens": 600,
}

print("Sending request to Gemini...")
response = model.generate_content(
    full_prompt,
    generation_config=generation_config,
)

print(f"\n✅ RESPONSE TEXT:\n{response.text}")
print(f"\n{'='*70}")
print(f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
print(f"Usage - Prompt: {response.usage_metadata.prompt_token_count}")
print(f"Usage - Completion: {response.usage_metadata.candidates_token_count}")
print(f"Usage - Total: {response.usage_metadata.total_token_count}")
print(f"\nAnswer length: {len(response.text)} characters")
