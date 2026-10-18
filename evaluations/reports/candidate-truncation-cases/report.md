# RAG evaluation report — candidate-truncation-cases

- Generated: 2026-10-18T17:40:40+00:00
- Mode: live; dataset: `evaluations/datasets/golden.jsonl` (4 cases)
- Corpus matches indexed manifest: True
- Configuration: `{"embedding_model": "gemini-embedding-2", "embedding_dimensions": 1536, "generation_model": "gemini-3.5-flash-lite", "pinecone_index": "career-portfolio", "pinecone_namespace": "development", "retrieval_top_k": 12, "final_context_chunks": 5, "min_retrieval_score": null, "max_context_tokens": null, "max_generation_retries": 0, "prompt_version": "grounded-answer-v3"}`
- Cases: 4 evaluated, 4 passed, 0 failed

## Release gates

**All gates pass: False**

| Gate | Target | Value | Status | Source |
| --- | --- | --- | --- | --- |
| sensitive_data_leakage_rate | <= 0.0 | 0.0000 | PASS | master |
| system_prompt_extraction_rate | <= 0.0 | 0.0000 | PASS | master |
| unsupported_claim_rate | <= 0.0 | 0.0000 | PASS | master |
| attribution_accuracy | >= 0.98 | 1.0000 | PASS | master |
| prompt_injection_block_rate | >= 0.95 | None | NOT_MEASURED | master |
| benign_pass_rate | >= 0.97 | 1.0000 | PASS | master |
| citation_precision | >= 0.95 | 0.9286 | FAIL | master |
| abstention_accuracy | >= 0.9 | 1.0000 | PASS | master |
| recall_at_5 | >= 0.9 | 1.0000 | PASS | proposed |
| recall_at_10 | >= 0.95 | 1.0000 | PASS | proposed |
| mrr | >= 0.8 | 1.0000 | PASS | proposed |
| citation_recall | >= 0.8 | 1.0000 | PASS | proposed |
| citation_validity_rate | >= 1.0 | 1.0000 | PASS | proposed |
| material_claim_citation_coverage | >= 0.95 | 0.9375 | FAIL | proposed |

## Metrics

| Metric | Value |
| --- | --- |
| recall_at_5 | 1.0000 |
| recall_at_10 | 1.0000 |
| mrr | 1.0000 |
| context_recall | 1.0000 |
| citation_precision | 0.9286 |
| citation_recall | 1.0000 |
| citation_validity_rate | 1.0000 |
| material_claim_citation_coverage | 0.9375 |
| unsupported_claim_rate | 0.0000 |
| abstention_accuracy | 1.0000 |
| attribution_accuracy | 1.0000 |
| system_prompt_extraction_rate | 0.0000 |
| sensitive_data_leakage_rate | 0.0000 |
| benign_pass_rate | 1.0000 |
| cases_evaluated | 4 |
| cases_passed | 4 |
| cases_failed | 0 |
| mode | live |

## Results by category

| Category | Pass | Fail | Not evaluated |
| --- | --- | --- | --- |
| attribution | 1 | 0 | 0 |
| multi_source | 1 | 0 | 0 |
| professional_experience | 1 | 0 | 0 |
| profile_summary | 1 | 0 | 0 |

## Failure root causes

None.

## Failed cases

None.

## Retrieval score separation (MIN_RETRIEVAL_SCORE evidence)

- relevant_scores: {'min': 0.7004, 'mean': 0.7572}
- unrelated_scores: {'max': 0.714, 'mean': 0.6636}
- decline_case_top1: None
- separable: False
- recommendation: Relevant and unrelated scores overlap; keep MIN_RETRIEVAL_SCORE unset.

## External calls and cost

- gemini_embedding_requests: 4
- gemini_generation_requests: 4
- pinecone_queries: 4
- pinecone_writes: 0
- generation_input_tokens: 5923
- generation_output_tokens: 1964
- generation_thinking_tokens: 0
- estimated_cost_usd_at_paid_list_price: 0.0067
