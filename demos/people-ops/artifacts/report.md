# Shore-Based Operations Staff Assistant · Factory report

Final score **24/24 (100.0%)**. All generated cases passed.

Runtime mode **local_model**. Model **qwen2.5-0.5b**. 2006 tokens accounted for. Elapsed 10.9 s.

## Scorecards

| Stage | Passed | Score |
| --- | ---: | ---: |
| Baseline | 18/24 | 75.0% |
| Iteration 1 | 22/24 | 91.7% |
| Iteration 2 | 24/24 | 100.0% |

## Remaining failures

Every case in this generated suite passed. The score measures this suite and corpus only.

## Groundability and ingestion

- **live vessel tracking coordinates**. No passage has sufficient vocabulary overlap to verify this requested topic. The agent refuses this topic.

## Evaluation limits

The suite covers 14 unique evidence passages and accepts 1 validated model paraphrases.
An independent deterministic judge checks status, verbatim citations, document identity and expected fact spans. There is no candidate ordering or answer-length reward, and no model evaluates its own wording.
Tests use the supplied documents. Lexical retrieval and span matching can miss valid paraphrases. External network calls are excluded from the generated suite. A low-diversity corpus produces repetitive anchors.
Model proposals are constrained by deterministic checks. model_trace.json records successful, invalid, and budget-skipped calls.
