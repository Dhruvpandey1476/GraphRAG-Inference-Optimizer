"""
Verify actual token count using Gemini's count_tokens API.
This is the OFFICIAL method required by the hackathon.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

def count_dataset_tokens():
    """Count total tokens in dataset using Gemini API."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in .env")
        return None
    
    genai.configure(api_key=api_key)
    
    data_dir = Path(__file__).parent.parent / "data" / "arxiv_bulk"
    files = sorted(data_dir.glob("*.txt"))
    
    logger.info(f"Found {len(files)} files to process")
    
    total_tokens = 0
    batch_size = 100
    
    for i, batch_start in enumerate(range(0, len(files), batch_size)):
        batch_end = min(batch_start + batch_size, len(files))
        batch_files = files[batch_start:batch_end]
        
        # Concatenate batch content
        batch_text = ""
        for file_path in batch_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    batch_text += f"\n\n---\n\n{content}"
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        # Count tokens using Gemini API
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.count_tokens(batch_text)
            batch_tokens = response.total_tokens
            total_tokens += batch_tokens
            
            pct = (batch_end / len(files)) * 100
            logger.info(
                f"Batch {i+1}: {batch_end}/{len(files)} files | "
                f"Batch tokens: {batch_tokens:,} | "
                f"Running total: {total_tokens:,} | "
                f"Progress: {pct:.1f}%"
            )
        except Exception as e:
            logger.error(f"Failed to count tokens for batch: {e}")
            return None
    
    logger.info(f"\n{'='*70}")
    logger.info(f"FINAL TOKEN COUNT (via Gemini API): {total_tokens:,}")
    logger.info(f"{'='*70}\n")
    
    # Save result
    result = {
        "total_files": len(files),
        "total_tokens_gemini": total_tokens,
        "verification_method": "Gemini count_tokens API",
        "model": "gemini-2.0-flash"
    }
    
    result_file = data_dir / "_token_verification.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Verification saved to {result_file}")
    
    return total_tokens

if __name__ == "__main__":
    total = count_dataset_tokens()
    if total:
        if total >= 100_000_000:
            print(f"\n✅ SUCCESS: {total:,} tokens (exceeds 100M requirement)")
        else:
            print(f"\n⚠️  WARNING: {total:,} tokens (below 100M requirement)")
