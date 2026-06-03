# 🎯 DEMO DAY MASTERFILE - EVERYTHING YOU NEED

## PRE-DEMO CHECKLIST (Do 30 minutes before)

### System Checks
- [ ] Venv activated: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned; .\venv\Scripts\Activate.ps1`
- [ ] Backend running: `cd backend && uvicorn api.server:app --host 0.0.0.0 --port 8001`
- [ ] Frontend ready: `cd frontend && npm run dev` (or just access localhost:8001)
- [ ] Dashboard accessible: http://localhost:8001 ✅
- [ ] All 3 pipelines showing results: LLM-Only, Basic RAG, GraphRAG
- [ ] Sample query pre-loaded and ready to run

### Files Open & Ready
- [ ] DEMO_SCRIPT_WINNING.md - For full talking points
- [ ] DEMO_QUICK_REFERENCE.md - For quick lookups
- [ ] PRESENTATION_SLIDES.md - For slide outline
- [ ] docs/BENCHMARK_REPORT_VISUAL.html - To show judges (open in browser)
- [ ] docs/ARCHITECTURE_DIAGRAM.txt - For visual reference
- [ ] results/benchmark_20260602_193344.json - To show real data

### Network & Display
- [ ] Stable internet connection
- [ ] Screen resolution suitable for showing dashboard
- [ ] Test keyboard input (for running queries)
- [ ] Sound working (if presenting video demo)

### Backup Plans
- [ ] Screenshot of dashboard (in case connection drops)
- [ ] Pre-recorded demo video (as backup)
- [ ] PDF of benchmark results (if can't open files)
- [ ] Talking points memorized (don't rely 100% on notes)

---

## DEMO DAY FLOW (5 minutes + Q&A)

### OPENING (15 seconds)
```
"Every dollar a company spends on LLM APIs, they're spending it twice. 
Once on the model, once on tokens. We found a way to cut that cost by 84%.
We built it on TigerGraph."
```
→ **File:** DEMO_SCRIPT_WINNING.md (Opening section)

### THE PROBLEM (45 seconds)
- Show dashboard
- Point to 3 pipelines
- Highlight: LLM-Only vs Basic RAG vs GraphRAG
- "1,424 tokens is the industry standard. We got it to 199."

→ **File:** DEMO_QUICK_REFERENCE.md (The Problem)

### THE INSIGHT (30 seconds)
- "Text is redundant. Graphs are not."
- Show docs/ARCHITECTURE_DIAGRAM.txt
- Explain: Basic RAG retrieves 5 chunks (same fact 5 ways) vs GraphRAG (structured facts)

→ **File:** PRESENTATION_SLIDES.md (Slide 3)

### THE ARCHITECTURE (60 seconds)
- Walk through 4 steps on screen
- Show dashboard architecture or docs/ARCHITECTURE_DIAGRAM.txt
- Highlight: Entity Extraction → Graph Traversal → Serialization → Answer Generation

→ **File:** docs/ARCHITECTURE_DIAGRAM.txt

### BENCHMARK RESULTS (90 seconds)
- **OPEN: docs/BENCHMARK_REPORT_VISUAL.html in browser**
- Point to each metric:
  - 84.1% token reduction ✅
  - 80.2% cost reduction ✅
  - 35% latency improvement ✅
  - 8.08/10 judge score (fair) ✅
  - 90% pass rate ✅
- "All three pipelines tested fairly. Same queries, same hardware."

→ **File:** docs/BENCHMARK_REPORT_VISUAL.html

### LIVE DEMO (60 seconds)
- **Dashboard at http://localhost:8001**
- Type sample query: "How does BERT differ from GPT?"
- Show all 3 pipeline results
- Point out: "199 tokens vs 1,424. Same quality. 6x fewer tokens."

→ **Dashboard:** localhost:8001

### SCALE & IMPACT (30 seconds)
- "$136,145 annual savings at 1M queries/day"
- "For GPT-4 or Claude: multiply by 10-20x = $1.36M-$2.72M"
- "This is institutional cost savings."

→ **File:** DEMO_QUICK_REFERENCE.md (Scale Impact)

### CLOSING (30 seconds)
- "Structured knowledge beats raw text."
- "Graphs enable better reasoning."
- "TigerGraph makes it fast and affordable."
- "This is production-grade GraphRAG."
- "Thank you."

→ **File:** PRESENTATION_SLIDES.md (Slide 13)

---

## TALKING POINTS QUICK LOOKUP

### If Judges Ask About...

**...Token Reduction?**
→ See: DEMO_QUICK_REFERENCE.md → "THREE KEY NUMBERS"

**...Quality/Judge Scores?**
→ See: PRESENTATION_SLIDES.md → "SLIDE 11: ANSWER QUALITY DEEP-DIVE"

**...Fairness?**
→ See: PRESENTATION_SLIDES.md → "SLIDE 8: FAIRNESS & CREDIBILITY"

**...Architecture?**
→ See: docs/ARCHITECTURE_DIAGRAM.txt or PRESENTATION_SLIDES.md → "SLIDE 4"

**...TigerGraph Choice?**
→ See: DEMO_QUICK_REFERENCE.md → "WHEN JUDGE ASKS ABOUT TIGERGRAPH"

**...Hallucinations?**
→ See: DEMO_QUICK_REFERENCE.md → "WHEN JUDGE ASKS ABOUT HALLUCINATIONS"

**...Generalization?**
→ See: DEMO_QUICK_REFERENCE.md → "WHEN JUDGE ASKS ABOUT GENERALIZATION"

**...Real Numbers?**
→ Open: results/benchmark_20260602_193344.json (live data)

---

## VISUALS TO SHOW

### Visual 1: Dashboard
- Location: http://localhost:8001
- Shows: 3 pipelines running in parallel, real-time metrics
- Use for: Demonstrating the system working live

### Visual 2: Architecture Diagram
- Location: docs/ARCHITECTURE_DIAGRAM.txt
- Shows: 4-step pipeline flow, entity extraction, graph traversal
- Use for: Explaining how GraphRAG works

### Visual 3: Benchmark Report
- Location: docs/BENCHMARK_REPORT_VISUAL.html
- Shows: All metrics in visual format, comparisons, scale impact
- Use for: Presenting results professionally

### Visual 4: Knowledge Graph Structure
- Location: docs/ARCHITECTURE_DIAGRAM.txt (Graph Structure section)
- Shows: Entities and relationships in graph
- Use for: Explaining knowledge graph richness

---

## KEY NUMBERS TO MEMORIZE

**Keep these ready for instant recall:**

- **84.1%** - Token reduction (1,424 → 199)
- **80.2%** - Cost reduction ($0.000448 → $0.000075)
- **199** - GraphRAG tokens per query
- **8.08/10** - GraphRAG judge score
- **8.24/10** - Basic RAG judge score
- **0.16** - Judge score difference (fair!)
- **90%** - GraphRAG pass rate (≥7/10)
- **190+** - Domain entities in knowledge graph
- **1,553** - Relationships in graph
- **$136,145** - Annual savings @ 1M queries/day
- **<200ms** - Graph traversal time

---

## TIMING BREAKDOWN

| Section | Time | Start | End |
|---------|------|-------|-----|
| Opening | 15s | 0:00 | 0:15 |
| Problem | 45s | 0:15 | 1:00 |
| Insight | 30s | 1:00 | 1:30 |
| Architecture | 60s | 1:30 | 2:30 |
| Benchmarks | 90s | 2:30 | 4:00 |
| Live Demo | 60s | 4:00 | 5:00 |
| Scale & Closing | 60s | 5:00 | 6:00 |
| **Buffer** | **60s** | 6:00 | 7:00 |
| **Q&A** | **5+ min** | 7:00 | 12:00+ |

---

## WHAT NOT TO DO

❌ Don't read directly from notes (use them for reference)  
❌ Don't get lost in technical details (keep it business-focused)  
❌ Don't oversell quality (be honest about 8.08 vs 8.24)  
❌ Don't forget to mention fairness (judges respect integrity)  
❌ Don't rush the demo (let judges see it working)  
❌ Don't talk about future work until asked (focus on what you did)  
❌ Don't downplay the savings (it's your strongest point)  

---

## WHAT TO EMPHASIZE

✅ **Real problem solved** - Token costs are blocking LLM adoption  
✅ **Fair comparison** - We tested fairly and fixed baseline issues  
✅ **Production metrics** - Not just accuracy, but cost and latency too  
✅ **Proven by TigerGraph** - Multi-hop GSQL traversal enabled this  
✅ **Scale matters** - $136K → $1.36M annual savings  
✅ **Better reasoning** - BERTScore proves LLM reasons better with graphs  
✅ **Honest about tradeoffs** - 0.16 judge points lower is fair for 84% savings  

---

## JUDGE MINDSET FRAMEWORK

### What They Care About (Priority Order):
1. **Does it solve a real problem?** ✅ (Token costs are real)
2. **Is the solution innovative?** ✅ (Structured graphs vs text chunks)
3. **Are the results credible?** ✅ (Fair benchmarks, we fixed baseline issues)
4. **Can it scale?** ✅ ($136K savings proves it)
5. **Is it implemented well?** ✅ (Production dashboard, real system)
6. **Can the team execute?** ✅ (You built this. You know it.)

### Your Competitive Advantage:
- Most teams optimize for accuracy only
- You optimized for real-world constraints: cost + speed + quality
- Most teams don't mention fairness
- You fixed your baseline and still win
- Most teams use toy datasets
- You tested on 50 diverse queries

---

## FINAL REMINDERS

🎯 **Your story is simple:**
"Text is redundant. We use graphs instead. It's cheaper, faster, and the LLM reasons better."

💪 **You have all the proof:**
- Real benchmark (50 queries)
- Real system (running on localhost)
- Real savings ($136K at scale)
- Real numbers (all open-sourced)

🚀 **Delivery matters:**
- Start strong (make judges feel the problem)
- Show visuals (open architecture, benchmark report)
- Live demo (judges want proof)
- End with impact (institutional savings)

🏆 **You're ready to win.**

---

## FILES CHECKLIST

Essential files for demo day:

✅ DEMO_SCRIPT_WINNING.md (Full script, 10 minutes of content)  
✅ DEMO_QUICK_REFERENCE.md (Quick lookup during presentation)  
✅ PRESENTATION_SLIDES.md (Slide outline with talking points)  
✅ docs/ARCHITECTURE_DIAGRAM.txt (Visual architecture explanation)  
✅ docs/BENCHMARK_REPORT_VISUAL.html (Open in browser for judges)  
✅ results/benchmark_20260602_193344.json (Real benchmark data)  
✅ DEMO_DAY_MASTERFILE.md (This file)  

---

## QUICK START COMMANDS

```bash
# Activate environment
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1

# Start backend
cd backend
uvicorn api.server:app --host 0.0.0.0 --port 8001

# In new terminal: Start frontend (if needed)
cd frontend
npm run dev

# Dashboard will be at: http://localhost:8001
```

---

**LAST CHECK BEFORE DEMO:**

✅ All systems running  
✅ Dashboard accessible  
✅ Sample query ready  
✅ Files open and accessible  
✅ You know your key numbers  
✅ You're confident in your story  

**You've got this. 🚀 Go win the hackathon.**
