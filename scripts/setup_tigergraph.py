#!/usr/bin/env python3
"""
Script: Setup TigerGraph schema and install queries.
Run once before ingesting documents.

Usage: python scripts/setup_tigergraph.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.graph.tigergraph_client import TigerGraphClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("🔧 Setting up TigerGraph schema...")

    client = TigerGraphClient()
    try:
        client.connect()
        logger.info("✅ Connected to TigerGraph")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        logger.error("Make sure your .env file has the correct TigerGraph credentials.")
        sys.exit(1)

    try:
        result = client.create_schema()
        logger.info(f"✅ Schema created successfully")
    except Exception as e:
        logger.warning(f"Schema creation returned: {e}")
        logger.info("(This may be expected if schema already exists)")

    logger.info("\n✅ TigerGraph setup complete!")
    logger.info("Next step: python scripts/ingest_documents.py --data data/sample_docs/")


if __name__ == "__main__":
    main()
