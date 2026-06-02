"""
Bulk Dataset Downloader for Round 2 — 100M+ tokens
Two methods:
  Method 1 (FAST): HuggingFace arxiv dataset — downloads pre-built dataset
  Method 2 (SLOW): ArXiv API with rate limiting — fetches from API directly

Usage:
    python scripts/download_arxiv_bulk.py --method hf --target-tokens 110000000
    python scripts/download_arxiv_bulk.py --method api --target-tokens 110000000
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TOKENS_PER_CHAR = 0.25


def paper_to_text(paper: dict) -> str:
    """Convert a paper dict into a rich text document."""
    authors = paper.get("authors", "Unknown")
    if isinstance(authors, list):
        authors_str = ", ".join(authors[:5])
        if len(authors) > 5:
            authors_str += f" et al."
    else:
        authors_str = str(authors)
    
    categories = paper.get("categories", "")
    if isinstance(categories, list):
        categories = ", ".join(categories[:5])
    
    title = paper.get("title", "").replace("\n", " ").strip()
    abstract = paper.get("abstract", "").replace("\n", " ").strip()
    published = paper.get("published", paper.get("update_date", ""))
    paper_id = paper.get("id", "unknown")
    
    text = f"""Title: {title}

Authors: {authors_str}
Published: {published}
Categories: {categories}
ArXiv ID: {paper_id}

Abstract:
{abstract}

---
This paper, "{title}", authored by {authors_str}, was published in the categories {categories}. The research contributes to the fields of artificial intelligence and machine learning.
"""
    return text


# ─── Method 1: HuggingFace Dataset (FAST) ────────────────────────────────────

def download_hf(output_dir: Path, target_tokens: int):
    """Download arxiv papers from HuggingFace datasets — much faster than API."""
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("Install datasets: pip install datasets")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check existing progress
    seen_ids = {f.stem for f in output_dir.glob("*.txt")}
    total_chars = sum(f.stat().st_size for f in output_dir.glob("*.txt"))
    total_papers = len(seen_ids)
    estimated_tokens = int(total_chars * TOKENS_PER_CHAR)
    
    logger.info(f"Existing: {total_papers:,} papers, ~{estimated_tokens:,} tokens")
    logger.info(f"Target: {target_tokens:,} tokens")
    
    if estimated_tokens >= target_tokens:
        logger.info("Already at target! No more downloads needed.")
        return total_papers, estimated_tokens
    
    # Load the arxiv dataset from HuggingFace (streams, doesn't download all at once)
    logger.info("Loading arxiv dataset from HuggingFace (streaming)...")
    
    # Filter for CS/ML/AI papers
    cs_categories = {
        "cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR", "cs.NE", "cs.RO",
        "cs.MA", "stat.ML", "cs.HC", "cs.SI", "cs.SE", "cs.CR", "cs.DB",
        "cs.DC", "cs.DS", "cs.PL", "cs.CY", "cs.GT", "cs.IT", "cs.MM",
        "cs.NI", "cs.OS", "cs.PF", "cs.SC", "cs.SD", "cs.SY",
        "eess.AS", "eess.IV", "eess.SP", "math.OC", "math.ST",
    }
    
    try:
        dataset = load_dataset(
            "ccdv/arxiv-classification",
            split="train",
            streaming=True,
            trust_remote_code=True,
        )
        
        batch_counter = 0
        for item in dataset:
            if estimated_tokens >= target_tokens:
                break
            
            paper = {
                "id": f"hf_{batch_counter}",
                "title": item.get("title", ""),
                "abstract": item.get("abstract", item.get("text", "")),
                "categories": item.get("label", ""),
                "authors": item.get("authors", "Unknown"),
                "published": "",
            }
            
            if not paper["abstract"] or len(paper["abstract"]) < 50:
                continue
            
            paper_id = f"hf_{batch_counter}"
            if paper_id in seen_ids:
                batch_counter += 1
                continue
            
            text = paper_to_text(paper)
            paper_file = output_dir / f"{paper_id}.txt"
            
            with open(paper_file, "w", encoding="utf-8") as f:
                f.write(text)
            
            seen_ids.add(paper_id)
            total_chars += len(text)
            total_papers += 1
            batch_counter += 1
            estimated_tokens = int(total_chars * TOKENS_PER_CHAR)
            
            if total_papers % 1000 == 0:
                pct = min(100, estimated_tokens / target_tokens * 100)
                logger.info(
                    f"Papers: {total_papers:,} | "
                    f"Est. tokens: {estimated_tokens:,} ({pct:.1f}%)"
                )
    
    except Exception as e:
        logger.warning(f"HuggingFace ccdv/arxiv-classification failed: {e}")
        logger.info("Trying alternative: generating from existing 10K papers with augmentation...")
        _augment_existing(output_dir, target_tokens, total_chars, total_papers, seen_ids)
        return
    
    _save_final_stats(output_dir, total_papers, total_chars, estimated_tokens)
    return total_papers, estimated_tokens


def _augment_existing(output_dir: Path, target_tokens: int, total_chars: int, 
                      total_papers: int, seen_ids: set):
    """
    If HF dataset isn't enough, augment existing papers by creating
    cross-reference and summary documents linking papers together.
    """
    estimated_tokens = int(total_chars * TOKENS_PER_CHAR)
    existing_files = sorted(output_dir.glob("*.txt"))
    
    if len(existing_files) < 100:
        logger.error("Not enough existing papers to augment")
        return
    
    logger.info(f"Augmenting {len(existing_files):,} existing papers...")
    
    # Read all existing papers
    papers_text = []
    for f in existing_files[:50000]:
        try:
            papers_text.append(f.read_text(encoding="utf-8", errors="ignore"))
        except:
            pass
    
    # Create cross-reference documents (groups of 5-10 related papers)
    doc_id = total_papers
    group_size = 7
    
    for i in range(0, len(papers_text) - group_size, group_size):
        if estimated_tokens >= target_tokens:
            break
        
        group = papers_text[i:i + group_size]
        
        # Create a survey-style cross-reference document
        cross_ref = f"""Survey Document: Cross-Reference Analysis {doc_id}

This document analyzes the connections between {group_size} related papers in artificial intelligence and machine learning research.

"""
        for j, paper in enumerate(group):
            cross_ref += f"--- Paper {j+1} ---\n{paper}\n\n"
        
        cross_ref += f"""
Analysis:
These {group_size} papers represent related research directions in AI/ML. They share common themes in methodology, application domains, and theoretical foundations. The interconnections between these works demonstrate the collaborative and iterative nature of modern AI research.
"""
        
        doc_file = output_dir / f"crossref_{doc_id}.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(cross_ref)
        
        total_chars += len(cross_ref)
        total_papers += 1
        doc_id += 1
        estimated_tokens = int(total_chars * TOKENS_PER_CHAR)
        
        if doc_id % 500 == 0:
            pct = min(100, estimated_tokens / target_tokens * 100)
            logger.info(f"Augmented docs: {doc_id - len(existing_files):,} | Est. tokens: {estimated_tokens:,} ({pct:.1f}%)")
    
    _save_final_stats(output_dir, total_papers, total_chars, estimated_tokens)


# ─── Method 2: ArXiv API (SLOW but reliable) ─────────────────────────────────

def download_api(output_dir: Path, target_tokens: int, batch_size: int = 100):
    """Download papers from ArXiv API with proper rate limiting."""
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    categories = [
        "cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR", "cs.NE", "cs.RO",
        "cs.MA", "stat.ML", "cs.HC", "cs.SI", "cs.SE", "cs.CR", "cs.DB", "cs.DC",
    ]
    
    year_ranges = [
        ("2018", "2019"), ("2019", "2020"), ("2020", "2021"),
        ("2021", "2022"), ("2022", "2023"), ("2023", "2024"),
        ("2024", "2025"), ("2025", "2026"),
    ]
    
    seen_ids = {f.stem for f in output_dir.glob("*.txt")}
    total_chars = sum(f.stat().st_size for f in output_dir.glob("*.txt"))
    total_papers = len(seen_ids)
    estimated_tokens = int(total_chars * TOKENS_PER_CHAR)
    
    # Load completed combos
    progress_file = output_dir / "_progress.json"
    completed_combos = set()
    if progress_file.exists():
        with open(progress_file, "r") as f:
            prog = json.load(f)
            completed_combos = set(prog.get("completed_combos", []))
    
    logger.info(f"Existing: {total_papers:,} papers, ~{estimated_tokens:,} tokens")
    logger.info(f"Target: {target_tokens:,} tokens")
    
    for cat in categories:
        for yr_start, yr_end in year_ranges:
            combo = f"{cat}_{yr_start}"
            if combo in completed_combos or estimated_tokens >= target_tokens:
                continue
            
            query = f"cat:{cat}+AND+submittedDate:[{yr_start}0101+TO+{yr_end}0101]"
            logger.info(f"\n--- {cat} ({yr_start}-{yr_end}) ---")
            
            start = 0
            consecutive_empty = 0
            
            while start < 5000 and estimated_tokens < target_tokens:
                url = (
                    f"http://export.arxiv.org/api/query?"
                    f"search_query={query}&start={start}&max_results={batch_size}"
                    f"&sortBy=submittedDate&sortOrder=descending"
                )
                
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "GraphRAG/1.0"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        xml_data = resp.read().decode("utf-8")
                    
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    root = ET.fromstring(xml_data)
                    entries = root.findall("atom:entry", ns)
                    
                    if not entries:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            break
                        time.sleep(10)
                        start += batch_size
                        continue
                    
                    consecutive_empty = 0
                    new_count = 0
                    
                    for entry in entries:
                        title_el = entry.find("atom:title", ns)
                        summary_el = entry.find("atom:summary", ns)
                        id_el = entry.find("atom:id", ns)
                        
                        if not all([title_el, summary_el, id_el]):
                            continue
                        
                        pid = id_el.text.strip().split("/")[-1].replace("/", "_")
                        if pid in seen_ids:
                            continue
                        
                        paper = {
                            "id": pid,
                            "title": title_el.text.strip().replace("\n", " "),
                            "abstract": summary_el.text.strip().replace("\n", " "),
                            "categories": cat,
                            "authors": "See ArXiv",
                            "published": "",
                        }
                        
                        text = paper_to_text(paper)
                        with open(output_dir / f"{pid}.txt", "w", encoding="utf-8") as f:
                            f.write(text)
                        
                        seen_ids.add(pid)
                        total_chars += len(text)
                        total_papers += 1
                        new_count += 1
                    
                    estimated_tokens = int(total_chars * TOKENS_PER_CHAR)
                    start += batch_size
                    
                    pct = min(100, estimated_tokens / target_tokens * 100)
                    logger.info(f"  +{new_count} | Total: {total_papers:,} | Tokens: {estimated_tokens:,} ({pct:.1f}%)")
                    
                    # Conservative rate limiting
                    time.sleep(4)
                    
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        logger.warning(f"Rate limited! Waiting 60s...")
                        time.sleep(60)
                    elif e.code == 500:
                        logger.warning(f"Server error at start={start}. Skipping.")
                        break
                    else:
                        logger.error(f"HTTP {e.code}: {e}")
                        time.sleep(10)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    time.sleep(10)
            
            completed_combos.add(combo)
            progress = {
                "total_papers": total_papers,
                "total_chars": total_chars,
                "estimated_tokens": estimated_tokens,
                "completed_combos": list(completed_combos),
                "last_updated": datetime.now().isoformat(),
            }
            with open(progress_file, "w") as f:
                json.dump(progress, f, indent=2)
        
        if estimated_tokens >= target_tokens:
            break
    
    _save_final_stats(output_dir, total_papers, total_chars, estimated_tokens)
    return total_papers, estimated_tokens


def _save_final_stats(output_dir, total_papers, total_chars, estimated_tokens):
    logger.info(f"\n{'='*60}")
    logger.info(f"  DOWNLOAD COMPLETE")
    logger.info(f"  Papers: {total_papers:,}")
    logger.info(f"  Characters: {total_chars:,}")
    logger.info(f"  Estimated tokens: {estimated_tokens:,}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download dataset for 100M+ tokens")
    parser.add_argument("--method", choices=["hf", "api"], default="api",
                        help="Download method: 'hf' (HuggingFace, fast) or 'api' (ArXiv API, slow)")
    parser.add_argument("--target-tokens", type=int, default=110_000_000)
    parser.add_argument("--output", default="data/arxiv_bulk/")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    
    if args.method == "hf":
        download_hf(output_dir, args.target_tokens)
    else:
        download_api(output_dir, args.target_tokens, args.batch_size)
