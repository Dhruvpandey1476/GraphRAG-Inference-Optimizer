# 🎯 Quick Start: Deploy Your GraphRAG System in 10 Minutes

## For Judges/Reviewers: How to Deploy & Test

### ⏱️ Timeline
```
5 min  → Get free API keys
5 min  → Deploy on Render
DONE   → Get your own live instance
```

---

## Step 1️⃣: Get Free API Keys (5 minutes)

### Gemini API (2 minutes)
1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Copy the key (looks like: `AIzaSyD...`)

### TigerGraph Cloud (3 minutes)
1. Go to https://tgcloud.io
2. Sign up (free account)
3. Create new solution
4. Wait for deployment
5. Copy credentials:
   - Host (https://xxx.i.tgcloud.io:443)
   - Username & password

**Cost**: $0 (completely free tier)

---

## Step 2️⃣: Deploy on Render.com (5 minutes)

### Backend
1. Go to https://render.com
2. Sign up with GitHub
3. New Web Service → connect repo
4. **Build**: `pip install -r requirements.txt`
5. **Start**: `uvicorn backend.api.server:app --host 0.0.0.0 --port 8000`
6. **Environment Variables** (from Step 1):
   ```
   GEMINI_API_KEY = your_key
   TIGERGRAPH_HOST = your_host
   TIGERGRAPH_USERNAME = your_username
   TIGERGRAPH_PASSWORD = your_password
   TIGERGRAPH_GRAPH_NAME = Demo
   ```
7. Deploy ✓

### Frontend
1. New Static Site → connect repo
2. **Build**: `cd frontend && npm install && npm run build`
3. **Directory**: `frontend/dist`
4. Deploy ✓

**Cost**: $0 (completely free tier)

---

## Step 3️⃣: Test Your Instance

### Backend Health
```bash
curl https://your-service.onrender.com/health
```

### Frontend
Open: `https://your-frontend.onrender.com`

### Run a Query
```bash
curl -X POST https://your-service.onrender.com/query/compare \
  -H "Content-Type: application/json" \
  -d '{"question": "What is GraphRAG?", "ground_truth": ""}'
```

---

## 🎉 Done!

You now have a **completely independent instance** running with:
- ✅ Your own API keys (no shared secrets)
- ✅ Live dashboard
- ✅ Benchmark comparison
- ✅ Zero cost
- ✅ No dependencies on anyone else

---

## 📖 Full Documentation

For detailed instructions, see:
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Full setup guide
- [API_KEYS_DEPLOYMENT_FAQ.md](API_KEYS_DEPLOYMENT_FAQ.md) - API key strategy
- [README_COMPREHENSIVE.md](README_COMPREHENSIVE.md) - Technical details

---

## ❓ Troubleshooting

### "TigerGraph Connection Failed"
→ Check TIGERGRAPH_HOST, username, password in Render dashboard

### "Gemini API Error"
→ Verify GEMINI_API_KEY is correct (AIzaSyD...)

### "Frontend can't reach backend"
→ Check frontend config has correct backend URL

### Need help?
→ See DEPLOYMENT_GUIDE.md troubleshooting section

---

## Why This Works

✅ **Secure**: No API keys shared publicly
✅ **Free**: Both hosting and API keys
✅ **Independent**: Your own live instance
✅ **Scalable**: Anyone can deploy this way
✅ **Professional**: Industry-standard approach

---

**Questions?** Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 📖
