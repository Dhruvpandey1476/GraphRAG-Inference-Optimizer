#!/usr/bin/env python3
"""
Script: Ingest documents into both Basic RAG (FAISS) and GraphRAG (TigerGraph).

Usage:
    python scripts/ingest_documents.py --data data/sample_docs/
    python scripts/ingest_documents.py --data /path/to/your/corpus/
"""

import sys
import json
import pickle
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env before importing any modules that use environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.graph.tigergraph_client import TigerGraphClient
from backend.graph.ingestion import DocumentIngestionPipeline, chunk_text
from backend.rag.basic_rag import BasicRAG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ingest_basic_rag(data_dir: str, faiss_path: str = "data/faiss_index.pkl"):
    """Build FAISS index for Basic RAG from raw documents."""
    logger.info("📦 Building FAISS index for Basic RAG...")

    rag = BasicRAG()
    path = Path(data_dir)
    files = list(path.glob("*.txt")) + list(path.glob("*.md"))
    
    all_chunks = []
    all_metadata = []

    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
        chunks = chunk_text(content)
        all_chunks.extend(chunks)
        all_metadata.extend([{"source": str(f), "file": f.name}] * len(chunks))
        logger.info(f"  {f.name}: {len(chunks)} chunks")

    rag.add_documents(all_chunks, all_metadata)

    # Save FAISS index for reuse
    with open(faiss_path, "wb") as f:
        pickle.dump({"index": rag.index, "chunks": rag.chunks, "metadata": rag.chunk_metadata}, f)
    logger.info(f"✅ FAISS index saved: {faiss_path} ({len(all_chunks)} total chunks)")
    return rag


def ingest_graph_rag(data_dir: str, tg_client: TigerGraphClient):
    """Ingest documents into TigerGraph knowledge graph."""
    logger.info("🕸️  Ingesting documents into TigerGraph...")

    pipeline = DocumentIngestionPipeline(tg_client)
    pipeline.ingest_directory(data_dir)

    stats = pipeline.get_stats()
    logger.info(f"\n✅ TigerGraph ingestion complete:")
    logger.info(f"   Docs processed:        {stats['docs_processed']}")
    logger.info(f"   Chunks created:        {stats['chunks_created']}")
    logger.info(f"   Entities extracted:    {stats['entities_extracted']}")
    logger.info(f"   Relationships created: {stats['relationships_extracted']}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAG pipelines")
    parser.add_argument("--data", default="data/sample_docs/", help="Directory with .txt/.md files")
    parser.add_argument("--skip-faiss", action="store_true", help="Skip FAISS index build")
    parser.add_argument("--skip-graph", action="store_true", help="Skip TigerGraph ingestion")
    parser.add_argument("--faiss-output", default="data/faiss_index.pkl", help="FAISS index output path")
    args = parser.parse_args()

    Path("data").mkdir(exist_ok=True)

    if not args.skip_faiss:
        ingest_basic_rag(args.data, args.faiss_output)

    if not args.skip_graph:
        try:
            tg = TigerGraphClient()
            tg.connect()
            ingest_graph_rag(args.data, tg)
        except Exception as e:
            logger.error(f"TigerGraph ingestion failed: {e}")
            logger.info("Hint: Run scripts/setup_tigergraph.py first, or check your .env credentials.")

    logger.info("\n🎉 Ingestion complete! Now run the server:")
    logger.info("   cd backend && uvicorn api.server:app --reload --port 8000")


if __name__ == "__main__":
    main()
