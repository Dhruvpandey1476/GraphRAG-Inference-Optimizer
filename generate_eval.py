from groq import Groq
import json
import os
import re

# Use environment variable for API key (never hardcode secrets!)
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY environment variable not set")

client = Groq(api_key=api_key)

prompt = """
Generate 50 additional domain-specific evaluation questions and answers
for GraphRAG, LLMs, RAG, Knowledge Graphs, Transformers, Embeddings.

Return ONLY valid JSON:

[
 {
   "question":"...",
   "ground_truth":"..."
 }
]
"""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role":"user","content":prompt}],
    temperature=0.7
)

content = response.choices[0].message.content

# Remove ```json and ```
content = re.sub(r"```json|```", "", content).strip()

# Extract only the JSON array
match = re.search(r"\[.*\]", content, re.DOTALL)

if not match:
    print("LLM did not return valid JSON")
    print(content)
    exit()

new_questions = json.loads(match.group())

existing = []

if os.path.exists("data/eval_queries.json"):
    with open(
        "data/eval_queries.json",
        "r",
        encoding="utf-8"
    ) as f:
        existing = json.load(f)

existing_questions = {
    q["question"] for q in existing
}

for item in new_questions:
    if item["question"] not in existing_questions:
        existing.append(item)

with open(
    "data/eval_queries.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(existing, f, indent=2)

print(
    f"Added {len(existing)-len(existing_questions)} new questions"
)