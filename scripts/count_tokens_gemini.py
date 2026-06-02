"""
Token Counter using Gemini's count_tokens API
Required by Round 2 to document dataset size.

Usage:
    python scripts/count_tokens_gemini.py --data-dir data/arxiv_bulk/
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def count_tokens_in_directory(data_dir: Path, sample_size: int = 100) -> dict:
    """
    Count tokens in all text files using Gemini's count_tokens API.
    Uses sampling for large datasets to avoid excessive API calls.
    """
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "PASTE_YOUR_GEMINI_KEY_HERE":
        logger.error("GEMINI_API_KEY not set. Update your .env file.")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Get all text files
    text_files = sorted(data_dir.glob("*.txt"))
    total_files = len(text_files)
    
    if total_files == 0:
        logger.error(f"No .txt files found in {data_dir}")
        return {"total_tokens": 0, "total_files": 0}
    
    logger.info(f"Found {total_files:,} text files in {data_dir}")
    
    # Sample files for token counting (to avoid excessive API calls)
    if total_files > sample_size:
        import random
        random.seed(42)
        sample_files = random.sample(text_files, sample_size)
        logger.info(f"Sampling {sample_size} files for token estimation...")
    else:
        sample_files = text_files
    
    sample_tokens = 0
    sample_chars = 0
    
    for i, fpath in enumerate(sample_files):
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            result = model.count_tokens(text)
            sample_tokens += result.total_tokens
            sample_chars += len(text)
            
            if (i + 1) % 10 == 0:
                logger.info(f"  Counted {i+1}/{len(sample_files)} sample files...")
        except Exception as e:
            logger.warning(f"  Error counting tokens for {fpath.name}: {e}")
    
    # Calculate tokens-per-char ratio from sample
    if sample_chars > 0:
        ratio = sample_tokens / sample_chars
    else:
        ratio = 0.25  # fallback
    
    # Count total characters across ALL files
    total_chars = 0
    for fpath in text_files:
        try:
            total_chars += fpath.stat().st_size  # approximate via file size
        except:
            pass
    
    # Estimate total tokens
    estimated_total_tokens = int(total_chars * ratio)
    
    result = {
        "total_files": total_files,
        "total_chars_approx": total_chars,
        "sample_size": len(sample_files),
        "sample_tokens": sample_tokens,
        "sample_chars": sample_chars,
        "tokens_per_char_ratio": round(ratio, 4),
        "estimated_total_tokens": estimated_total_tokens,
        "measurement_method": "Gemini count_tokens API with sampling",
        "model": "gemini-2.0-flash",
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"  DATASET TOKEN COUNT (Gemini API)")
    logger.info(f"  Total files:           {total_files:,}")
    logger.info(f"  Sample measured:       {len(sample_files)} files")
    logger.info(f"  Sample tokens:         {sample_tokens:,}")
    logger.info(f"  Tokens/char ratio:     {ratio:.4f}")
    logger.info(f"  Total chars (approx):  {total_chars:,}")
    logger.info(f"  ESTIMATED TOTAL TOKENS: {estimated_total_tokens:,}")
    logger.info(f"{'='*60}")
    
    # Save result
    import json
    out_path = data_dir / "_token_count.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved to {out_path}")
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count dataset tokens using Gemini API")
    parser.add_argument("--data-dir", default="data/arxiv_bulk/",
                        help="Directory containing text files")
    parser.add_argument("--sample-size", type=int, default=100,
                        help="Number of files to sample for counting")
    args = parser.parse_args()
    
    count_tokens_in_directory(Path(args.data_dir), args.sample_size)
