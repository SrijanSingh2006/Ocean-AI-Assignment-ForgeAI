# Marine Procurement Coordinators Assistant · Factory report

Final score **24/24 (100.0%)**. All generated cases passed.

Runtime mode **local_model**. Model **qwen2.5-0.5b**. 1717 tokens accounted for. Elapsed 5.8 s.

## Scorecards

| Stage | Passed | Score |
| --- | ---: | ---: |
| Baseline | 17/24 | 70.8% |
| Iteration 1 | 21/24 | 87.5% |
| Iteration 2 | 23/24 | 95.8% |
| Iteration 3 | 24/24 | 100.0% |

## Remaining failures

Every case in this generated suite passed. The score measures this suite and corpus only.

## Groundability and ingestion

- **emergency air freight**. No passage has sufficient vocabulary overlap to verify this requested topic. The agent refuses this topic.

## Evaluation limits

The suite covers 15 unique evidence passages and accepts 0 validated model paraphrases.
An independent deterministic judge checks status, verbatim citations, document identity and expected fact spans. There is no candidate ordering or answer-length reward, and no model evaluates its own wording.
Tests use the supplied documents. Lexical retrieval and span matching can miss valid paraphrases. External network calls are excluded from the generated suite. A low-diversity corpus produces repetitive anchors.
Model proposals are constrained by deterministic checks. model_trace.json records successful, invalid, and budget-skipped calls.
