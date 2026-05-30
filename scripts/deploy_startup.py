#!/usr/bin/env python3
"""
Deployment startup script for Render.com
Minimal initialization - just verify basics, don't block startup
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEPLOY_STARTUP")

try:
    logger.info("🚀 Starting GraphRAG deployment checks...")
    
    # Check minimal env vars
    required = ["TIGERGRAPH_HOST", "GOOGLE_API_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    
    if missing:
        logger.warning(f"⚠️  Missing: {', '.join(missing)}")
        logger.info("   (System will use demo mode)")
    else:
        logger.info("✅ All required env vars present")
    
    logger.info("✅ Startup checks passed - ready to serve!")
    
except Exception as e:
    logger.error(f"⚠️  Startup warning: {e}")
    logger.info("   Continuing anyway...")

sys.exit(0)

