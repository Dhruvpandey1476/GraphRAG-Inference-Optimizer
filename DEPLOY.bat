@echo off
REM Quick Deploy to Render.com Script (Windows)
REM Run this after creating a Render.com account

echo.
echo 🚀 GraphRAG Production Deployment Helper
echo ==========================================
echo.
echo STEP 1: Check if everything is committed
git status
echo.
echo.
echo STEP 2: Go to Render Dashboard
echo    → https://dashboard.render.com
echo.
echo STEP 3: Click '+New' then select 'Web Service'
echo    → Authorize Render to access GitHub
echo    → Select 'graphrag-hackathon' repository
echo.
echo STEP 4: Configure deployment settings:
echo    ✓ Branch: Main
echo    ✓ Runtime: Python 3.11
echo    ✓ Build Command: (will auto-detect from render.yaml)
echo    ✓ Start Command: (will auto-detect from render.yaml)
echo    ✓ Plan: Free tier (or Standard for $7/month)
echo.
echo STEP 5: Click 'Create Web Service'
echo    → Render starts initial deploy
echo    → May fail (expected - missing env vars)
echo.
echo STEP 6: Add Environment Variables
echo    → Go to Settings tab → Environment
echo    → Add these variables:
echo.
echo    ENVIRONMENT=production
echo    LOG_LEVEL=info
echo    TIGERGRAPH_HOST=tg-17b98dc4-8656-4f8d-bc0a-d30e8fdd5b27.tg-3452941248.i.tgcloud.io
echo    TIGERGRAPH_GRAPH=GraphRAGDemo
echo    TIGERGRAPH_USERNAME=tigergraph
echo    TIGERGRAPH_PASSWORD=[YOUR-TIGERGRAPH-PASSWORD]
echo    TIGERGRAPH_SECRET=[YOUR-TIGERGRAPH-SECRET]
echo    GOOGLE_API_KEY=[YOUR-GEMINI-API-KEY]
echo    LLM_MODEL=gemini-2.0-flash
echo    EMBEDDING_MODEL=text-embedding-3-small
echo.
echo STEP 7: Save environment variables
echo    → Render auto-redeploys
echo    → Check Logs tab for progress
echo.
echo STEP 8: Wait for "Live" status
echo    → Usually takes 5-10 minutes
echo    → Check: https://graphrag-backend.render.com
echo.
echo STEP 9: Test the dashboard
echo    → See interactive 3-pipeline comparison
echo    → Run queries and view metrics
echo.
echo ✅ SUCCESS! Share with judges:
echo    https://graphrag-backend.render.com
echo.
echo 📊 Cost Summary:
echo    - Render: Free tier or $7/month Standard
echo    - Gemini: ~$0.00015 per query (or free credits)
echo    - TigerGraph: Already running (free tier)
echo.
pause
