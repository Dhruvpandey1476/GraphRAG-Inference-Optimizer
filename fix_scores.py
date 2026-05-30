#!/usr/bin/env python3
"""Fix judge scores from 0-1 scale to 1-10 scale"""
import json

# Read existing benchmark
with open('results/benchmark_20260530_115007.json') as f:
    data = json.load(f)

# Multiply all judge scores by 10
for query in data.get('per_query', []):
    query['basic_judge_score'] *= 10
    query['graph_judge_score'] *= 10
    query['llm_judge_score'] *= 10

# Update summary scores  
data['summary']['avg_judge_score_llm'] *= 10
data['summary']['avg_judge_score_basic'] *= 10
data['summary']['avg_judge_score_graph'] *= 10

# Write back
with open('results/benchmark_20260530_115007.json', 'w') as f:
    json.dump(data, f, indent=2)

print('✅ Benchmark JSON updated: scores now on 1-10 scale')
print(f"Updated LLM-Only: {data['summary']['avg_judge_score_llm']:.1f}/10")
print(f"Updated Basic RAG: {data['summary']['avg_judge_score_basic']:.1f}/10")
print(f"Updated GraphRAG: {data['summary']['avg_judge_score_graph']:.1f}/10")

# Regenerate HTML report
from evaluation.report_generator import generate_html_report
generate_html_report(data, 'results/report_FINAL_CORRECTED.html')
print('✅ HTML report regenerated with corrected scores')
