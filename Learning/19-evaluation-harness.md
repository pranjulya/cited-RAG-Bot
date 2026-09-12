# Phase 19 — Evaluation Harness

## Why evaluate retrieval separately from generation

If Recall@K is low, the model never saw the page. Fixing the prompt will not help. If Recall@K is high and answers are still wrong, the fault is later: rerank, budget, generation, or citation. Layered metrics stop us from swapping models for a retrieval bug.

## Recall@K vs MRR vs nDCG

Recall@K: did any/all relevant chunks appear in the top K? First-stage goal. MRR: where is the first relevant hit? nDCG: graded position of all relevant hits. Hybrid retrieval should be judged on recall first; rerank on MRR/nDCG.

## LLM-as-judge

Semantic citation correctness and faithfulness may use a judge later. Judges need a versioned prompt, a recorded model name, and calibration against human labels. They do not replace deterministic citation validity (`E#` in the request map).
