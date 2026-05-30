#!/usr/bin/env python3
import json
from evaluation.report_generator import generate_html_report

with open('results/benchmark_20260530_115007.json') as f:
    data = json.load(f)

generate_html_report(data, 'results/report_FINAL.html')
print('✅ Final HTML report generated with corrected metrics')
print(f"Pass Rate (GraphRAG): {data['summary']['llm_judge_pass_rate_graph']:.1f}%")
print(f"Judge Score: {data['summary']['avg_judge_score_graph']:.1f}/10")
print(f"Token Reduction: {data['summary']['avg_token_reduction_pct']:.1f}%")
