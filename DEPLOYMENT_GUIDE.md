# 🚀 Free Deployment Guide for GraphRAG

Deploy this system **completely free** with your own API keys. No credit card required for hosting.

---

## ⏱️ Time Required: 15 minutes

---

## Step 1: Get Free API Keys (5 min)

### 1.1 Google Gemini API

1. Go to https://ai.google.dev/
2. Click **"Get API Key"**
3. Click **"Create API key in new project"**
4. Select your Google account (or create new one - free)
5. Copy the API key (looks like: `AIzaSyD...`)

**Free Tier**: 60 requests/minute, ideal for testing

### 1.2 TigerGraph Cloud

1. Go to https://tgcloud.io
2. Click **"Sign Up"** (free tier available)
3. Create new solution:
   - Graph Engine: TigerGraph 4.2
   - Cloud: AWS/GCP (choose closest to you)
   - Size: Small (free tier)
4. Wait 2-3 minutes for deployment
5. Copy these credentials:
   - **Host**: `https://xxx.i.tgcloud.io:443`
   - **Username**: (shown in console)
   - **Password**: (you set this)
   - **Graph Name**: `Demo` (or custom)

**Free Tier**: 1 GB storage, perfect for 113M+ token dataset

---

## Step 2: Prepare Repository (2 min)

### 2.1 Fork Repository
1. Go to your fork/clone of this project
2. Ensure it's public on GitHub (so Render can access it)

### 2.2 Create `.env.example` in root
Already included! Shows what keys are needed.

### 2.3 Update `.gitignore` (Safety First!)
Make sure `.env` is ignored:
```
.env
.env.local
*.env
secrets/
```

---

## Step 3: Deploy on Render.com (Free) (8 min)

**Why Render?**
- ✅ No credit card required
- ✅ Free tier with auto-sleep (great for demos)
- ✅ GitHub integration
- ✅ Environment variables support

### 3.1 Sign Up
1. Go to https://render.com
2. Click **"Sign up with GitHub"**
3. Authorize your GitHub account
4. Complete setup (no payment needed)

### 3.2 Deploy Backend

1. Dashboard → **"New +"** → **"Web Service"**
2. **"Connect to GitHub"** and select your graphrag repo
3. Fill in:
   - **Name**: `graphrag-backend`
   - **Runtime**: Python 3.9
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.api.server:app --host 0.0.0.0 --port 8000`
   - **Plan**: **Free** (auto-sleeps after 15 min)

4. **Environment Variables** - Click "Add Environment Variable":
   ```
   GEMINI_API_KEY = AIzaSyD... (your key from Step 1.1)
   TIGERGRAPH_HOST = https://xxx.i.tgcloud.io:443
   TIGERGRAPH_USERNAME = your_username
   TIGERGRAPH_PASSWORD = your_password
   TIGERGRAPH_GRAPH_NAME = Demo
   ```

5. Click **"Create Web Service"**
6. Wait 3-5 minutes for deployment
7. You'll get a URL: `https://graphrag-backend.onrender.com`

### 3.3 Deploy Frontend

1. Dashboard → **"New +"** → **"Static Site"**
2. Connect your repo again
3. Fill in:
   - **Name**: `graphrag-frontend`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`

4. Click **"Create Static Site"**
5. Get frontend URL: `https://graphrag-frontend.onrender.com`

### 3.4 Connect Frontend to Backend

1. Edit frontend to use backend URL:
   - File: `frontend/src/config.js` (or `.env`)
   - Set: `VITE_BACKEND_URL=https://graphrag-backend.onrender.com`

2. Re-deploy frontend (push changes or use Render UI)

---

## Step 4: Alternative Platforms (Pick One)

### Railway.app (Free $5 credit/month)

```bash
1. Sign up: https://railway.app
2. New Project → GitHub (select repo)
3. Add services:
   - Backend on port 8000
   - Frontend as static site
4. Set environment variables in dashboard
5. Deploy
```

### Replit (Quick Prototype)

```bash
1. Go to https://replit.com
2. Click "Import from GitHub" → select repo
3. Create .env file with your keys
4. Run: uvicorn backend.api.server:app --reload
5. Share Replit link with anyone
```

### Heroku Alternative (Free tiers ended - paid only)
Not recommended, use Render or Railway instead.

---

## Step 5: Verify Deployment

### Check Backend is Running
```bash
curl https://graphrag-backend.onrender.com/health
```

Should return:
```json
{
  "status": "ok",
  "tigergraph_connected": true,
  "pipelines_ready": true
}
```

### Test Query Endpoint
```bash
curl -X POST https://graphrag-backend.onrender.com/query/compare \
  -H "Content-Type: application/json" \
  -d '{"question": "What is GraphRAG?", "ground_truth": ""}'
```

### Access Frontend
Open: `https://graphrag-frontend.onrender.com`

---

## 💰 Cost Analysis

| Service | Free Tier | Cost | Notes |
|---------|-----------|------|-------|
| **Render Backend** | Yes | $0 | Auto-sleeps after 15 min |
| **Render Frontend** | Yes | $0 | Always active |
| **Gemini API** | 60 req/min | $0-3/month* | 1M tokens = $0.075 |
| **TigerGraph** | 1 GB | $0-50/month* | Perfect for datasets <1GB |
| **Total** | **$0** | **$0-5/month*** | *Optional paid upgrades |

**Free Forever**: Yes, as long as you stay within free tier limits!

---

## 🔒 Security Best Practices

✅ **DO:**
- Store `.env` locally only (git-ignored)
- Use environment variables in deployment
- Keep `.env.example` public (shows format, not values)
- Rotate API keys quarterly

❌ **DON'T:**
- Commit `.env` to GitHub
- Share API keys in issues/PRs
- Use same key for dev and prod
- Commit API keys anywhere

---

## 🐛 Troubleshooting

### "TigerGraph Connection Failed"
```
✓ Check TIGERGRAPH_HOST is correct (https://...)
✓ Verify username/password are correct
✓ Ensure graph solution is running in TigerGraph Cloud
✓ Check firewall allows outbound to TigerGraph
```

### "Gemini API Error"
```
✓ Verify API key is correct (AIzaSyD...)
✓ Check you're not exceeding 60 req/min limit
✓ Ensure API key has "Generative Language API" enabled
```

### "Port 8000 Already in Use"
```bash
# Use different port
uvicorn backend.api.server:app --port 8001
```

### "Frontend Can't Reach Backend"
```
✓ Check BACKEND_URL in frontend config
✓ Verify backend is actually deployed and healthy
✓ Check CORS headers in backend/api/server.py
```

---

## 📞 Getting Help

**Common Issues:**
- TigerGraph: Check [docs.tigergraph.com](https://docs.tigergraph.com)
- Gemini: Check [ai.google.dev/docs](https://ai.google.dev/docs)
- Render: Check [render.com/docs](https://render.com/docs)
- FastAPI: Check [fastapi.tiangolo.com](https://fastapi.tiangolo.com)

**Community:**
- Open GitHub issue for bugs
- Tag `@TigerGraph` if TigerGraph-specific

---

## 📊 Scaling to Production

Once deployed successfully, upgrade:

1. **Render**: Upgrade to paid tier (runs 24/7)
2. **TigerGraph**: Increase storage to accommodate larger datasets
3. **Gemini**: Monitor costs, consider batch processing
4. **Database**: Add PostgreSQL for query caching (5 GB free tier)

---

## ✨ You're Done!

Your GraphRAG system is now live and accessible to anyone. Share the frontend URL and watch it process queries in real-time! 🎉

**Next Steps:**
- [ ] Test with sample queries
- [ ] Share with teammates/judges
- [ ] Monitor costs in Render/Railway dashboards
- [ ] Iterate based on feedback
- [ ] Submit to hackathon!
