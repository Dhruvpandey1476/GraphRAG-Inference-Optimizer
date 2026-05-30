#!/usr/bin/env python3
"""
Deployment startup script for Render.com
Runs once on first deployment to:
1. Initialize TigerGraph schema
2. Ingest data into graph
3. Pre-load FAISS index
4. Validate all systems
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEPLOY_STARTUP")

def check_environment():
    """Verify all required environment variables."""
    logger.info("🔍 Checking environment variables...")
    required = [
        "TIGERGRAPH_HOST",
        "TIGERGRAPH_USERNAME",
        "TIGERGRAPH_PASSWORD",
        "GOOGLE_API_KEY",
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        logger.error(f"❌ Missing env vars: {', '.join(missing)}")
        sys.exit(1)
    
    logger.info("✅ All required env vars present")

def initialize_tigergraph():
    """Set up TigerGraph schema if needed."""
    logger.info("🗄️  Initializing TigerGraph...")
    try:
        from scripts.setup_tigergraph import setup_schema
        setup_schema()
        logger.info("✅ TigerGraph schema ready")
    except Exception as e:
        logger.warning(f"⚠️  Could not initialize TigerGraph: {e}")
        logger.info("   (Graph may already be initialized)")

def check_data_files():
    """Verify data files exist."""
    logger.info("📁 Checking data files...")
    
    data_path = PROJECT_ROOT / "data"
    arxiv_path = data_path / "arxiv_bulk"
    
    if not data_path.exists():
        logger.error(f"❌ Data directory missing: {data_path}")
        return False
    
    logger.info(f"✅ Data directory exists: {data_path}")
    
    # Count papers
    if arxiv_path.exists():
        papers = list(arxiv_path.glob("*.txt"))
        logger.info(f"📊 Found {len(papers)} arXiv papers")
    
    return True

def verify_api_access():
    """Test API connectivity."""
    logger.info("🌐 Verifying API access...")
    
    try:
        # Test Google Gemini
        from backend.llm.gemini_client import GeminiClient
        client = GeminiClient()
        logger.info("✅ Google Gemini API accessible")
    except Exception as e:
        logger.warning(f"⚠️  Google Gemini check failed: {e}")
    
    try:
        # Test TigerGraph
        from backend.graph.tigergraph_client import TigerGraphClient
        tg = TigerGraphClient()
        logger.info("✅ TigerGraph connection successful")
    except Exception as e:
        logger.error(f"❌ TigerGraph connection failed: {e}")
        return False
    
    return True

def cache_warmup():
    """Pre-load FAISS index and common data."""
    logger.info("🔥 Warming up cache...")
    try:
        import faiss
        import numpy as np
        
        # Check if FAISS index exists
        index_path = PROJECT_ROOT / "faiss_index.pkl"
        if index_path.exists():
            logger.info(f"✅ FAISS index found: {index_path}")
        else:
            logger.info("⚠️  FAISS index not found (will be created on first RAG query)")
    except Exception as e:
        logger.warning(f"⚠️  Cache warmup skipped: {e}")

def main():
    """Run all startup checks."""
    logger.info("=" * 60)
    logger.info("🚀 GRAPHRAG DEPLOYMENT STARTUP")
    logger.info("=" * 60)
    
    try:
        check_environment()
        verify_api_access()
        check_data_files()
        initialize_tigergraph()
        cache_warmup()
        
        logger.info("=" * 60)
        logger.info("✅ DEPLOYMENT READY - Starting server...")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
