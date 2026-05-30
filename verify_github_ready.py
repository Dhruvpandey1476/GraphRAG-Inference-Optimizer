#!/usr/bin/env python3
"""
Verify GitHub repo is ready for submission before pushing
"""
import os
import json
from pathlib import Path

def check_repo():
    print("\n🔍 GitHub Submission Checklist\n" + "="*50)
    
    checks = {
        "✅ .env is git-ignored": not Path(".env").exists() or os.system("git check-ignore -q .env") == 0,
        "✅ .env.example exists": Path(".env.example").exists(),
        "✅ README.md updated": "data/sample_docs/" in Path("README.md").read_text(encoding="utf-8"),
        "✅ report_FINAL.html exists": Path("results/report_FINAL.html").exists(),
        "✅ WINNING_NARRATIVE.md exists": Path("WINNING_NARRATIVE.md").exists(),
        "✅ benchmark JSON exists": Path("results/benchmark_20260530_115007.json").exists(),
        "✅ requirements.txt exists": Path("requirements.txt").exists(),
        "✅ backend/ source code": Path("backend/api/server.py").exists(),
        "✅ frontend/ source code": Path("frontend/package.json").exists(),
        "✅ evaluation/ source code": Path("evaluation/benchmark.py").exists(),
    }
    
    # Check file sizes
    print("\n📊 Repository Size Check:")
    arxiv_bulk = Path("data/arxiv_bulk")
    if arxiv_bulk.exists():
        size_mb = sum(f.stat().st_size for f in arxiv_bulk.rglob("*") if f.is_file()) / 1_000_000
        print(f"   ⚠️  data/arxiv_bulk/: {size_mb:.1f} MB (should NOT push)")
        checks["❌ data/arxiv_bulk/ should be .gitignored"] = False
    else:
        print("   ✅ data/arxiv_bulk/: Already excluded")
        checks["✅ data/arxiv_bulk/ excluded"] = True
    
    # Print results
    print("\n📋 Status:")
    passed = 0
    failed = 0
    for check, status in checks.items():
        symbol = "✅" if status else "❌"
        print(f"   {symbol} {check}")
        if status:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"🎯 Result: {passed}/{len(checks)} checks passed\n")
    
    if failed == 0:
        print("✅ READY FOR GITHUB PUSH!\n")
        print("Next steps:")
        print("  1. git add .")
        print("  2. git commit -m 'GraphRAG Hackathon Round 2 Submission'")
        print("  3. git push origin main")
        return True
    else:
        print(f"⚠️  {failed} issues to fix before pushing\n")
        return False

if __name__ == "__main__":
    check_repo()
