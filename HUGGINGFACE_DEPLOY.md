# 🚀 Deploy to Hugging Face Spaces

**Status:** Ready for deployment  
**Setup Time:** 10 minutes  
**Cost:** Free (generous resources)  
**Memory:** 2GB+ (plenty for your system)

---

## 📋 **Step-by-Step Setup**

### **Step 1: Create Hugging Face Account**
1. Go to: https://huggingface.co
2. Sign up (free)
3. Go to: https://huggingface.co/spaces

---

### **Step 2: Create New Space**

1. Click **"Create new Space"** button
2. Fill in details:
   - **Space name:** `graphrag-inference-optimizer` (or your name)
   - **License:** MIT (or your choice)
   - **Space SDK:** `Docker`
   - **Space hardware:** `CPU basic` (free) or `CPU upgrade` (small cost)
   - **Private/Public:** Public (so judges can access)

3. Click **"Create Space"**

---

### **Step 3: Connect Your Repository**

After creating the space, you'll see setup instructions. Choose **Option 1: Git-based approach**:

```bash
cd /path/to/graphrag-hackathon

# Add HuggingFace remote
git remote add hf https://huggingface.co/spaces/[YOUR_USERNAME]/[SPACE_NAME]

# Push code to HuggingFace
git push hf main:main
```

**Note:** Replace `[YOUR_USERNAME]` and `[SPACE_NAME]` with your values.

---

### **Step 4: Add Environment Variables**

On the HuggingFace Space page:

1. Click **⚙️ Settings** (top right)
2. Go to **"Repository secrets"**
3. Add these secrets:
   ```
   TIGERGRAPH_HOST = tg-17b98dc4-8656-4f8d-bc0a-d30e8fdd5b27.tg-3452941248.i.tgcloud.io
   TIGERGRAPH_GRAPH = GraphRAGDemo
   TIGERGRAPH_USERNAME = dhruv1476
   TIGERGRAPH_PASSWORD = [your-password]
   TIGERGRAPH_SECRET = [your-secret]
   GOOGLE_API_KEY = [your-gemini-key]
   ```

4. Click **"Save"**

---

### **Step 5: Monitor Deployment**

1. Go back to Space page
2. Click **"Logs"** tab
3. Watch for:
   - ✅ "Building Docker image..."
   - ✅ "Installing dependencies..."
   - ✅ "Space is running at..."

**Typical time:** 5-10 minutes

---

### **Step 6: Access Your Space**

Once deployed, you'll get a URL like:
```
https://huggingface.co/spaces/[YOUR_USERNAME]/graphrag-inference-optimizer
```

**Share this link with judges!** 🎉

---

## 🎯 **What Judges Will See**

✅ Interactive dashboard at the Space URL  
✅ Can type queries and see 3-pipeline comparison  
✅ Token reduction metrics displayed  
✅ Works immediately, no setup needed  

---

## 📊 **Space Hardware Options**

| Hardware | Cost | Memory | Best For |
|----------|------|--------|----------|
| **CPU basic** | Free | 2GB | Perfect for demos |
| **CPU upgrade** | ~$3/mo | 4GB | Better performance |
| **T4 GPU** | ~$10/mo | 16GB | Fastest |

Start with **CPU basic** (free). Upgrade later if needed.

---

## 🔄 **Updating Your Space**

To update code after deployment:

```bash
# Make changes locally
git add .
git commit -m "Update code"

# Push to HuggingFace
git push hf main:main

# Space auto-redeploys!
```

---

## ✅ **Success Checklist**

- [ ] HuggingFace account created
- [ ] New Space created (Docker SDK)
- [ ] Repository pushed to HuggingFace
- [ ] Environment variables added to Secrets
- [ ] Space shows "Running" status
- [ ] Can access Space URL
- [ ] Dashboard loads
- [ ] Can run queries

---

## 💡 **Advantages Over Render**

✅ **Better memory management** (2GB free vs 512MB free)  
✅ **No build issues** (Docker handles it)  
✅ **Designed for ML demos** (perfect fit)  
✅ **Auto-redeploy** on git push  
✅ **Better for judges** (Spaces are trusted)  
✅ **Generous free tier** (no time limits)  

---

## 📞 **If Something Goes Wrong**

1. Check **Logs** tab in Space settings
2. Check **Build logs** for errors
3. Ensure all environment variables are set
4. Try rebuilding: Settings → Restart Space

---

**Ready to deploy? Let's go!** 🚀
