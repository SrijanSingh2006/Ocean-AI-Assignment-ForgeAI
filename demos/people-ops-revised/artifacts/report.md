# Shore-Based Operations Staff Assistant · Factory report

Final score **24/24 (100.0%)**. All generated cases passed.

Runtime mode **local_model**. Model **qwen2.5-0.5b**. 4029 tokens accounted for. Elapsed 14.2 s.

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

## Run budget

Active time 14.23/120 seconds. Model tokens 4029/12000. Requirements review took 0.00 seconds outside the active budget.

## Prompt tournament

Winner **Grounded default**. Every scored candidate used the same generated suite. Ties keep the earlier candidate.

| Candidate | Passed | Score |
| --- | ---: | ---: |
| Grounded default | 18/24 | 75.0% |
| Exact evidence | 18/24 | 75.0% |
| Task coverage | 18/24 | 75.0% |

## Regression against prior suite

21/24 prior cases passed.
- Newly failing · E05, E11, E14
- Newly passing · None
- **E05 · retrieval miss**. What does Leave Handbook document about Annual leave?
  - Prior fact now missing from Leave-Handbook.md: Permanent shore employees receive 22 paid annual leave days per calendar year.
- **E11 · retrieval miss**. What does Travel And Expenses document about Travel reimbursements?
  - Prior fact now missing from Travel-and-Expenses.md: Submit travel reimbursements in the expense portal within 30 calendar days of returning.
- **E14 · retrieval miss**. For Hybrid Work Guide, what is documented about Remote work, and separately, for Leave Handbook, what is documented about Annual leave?
  - Prior fact now missing from Leave-Handbook.md: Permanent shore employees receive 22 paid annual leave days per calendar year.
