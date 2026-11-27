# Shore-Based Operations Staff Assistant · Factory report

Final score **24/24 (100.0%)**. All generated cases passed.

Runtime mode **local_model**. Model **qwen2.5-0.5b**. 3481 tokens accounted for. Elapsed 97.2 s.

## Scorecards

| Stage | Passed | Score |
| --- | ---: | ---: |
| Baseline | 18/24 | 75.0% |
| Iteration 1 | 22/24 | 91.7% |
| Iteration 2 | 24/24 | 100.0% |

## Remaining failures

Every case in this generated suite passed. The score measures this suite and corpus only.

## Groundability and ingestion

No explicit unsupported topics or extraction warnings were detected.

## Evaluation limits

The suite covers 16 unique evidence passages and accepts 1 validated model paraphrases.
An independent deterministic judge checks status, verbatim citations, document identity and expected fact spans. There is no candidate ordering or answer-length reward, and no model evaluates its own wording.
Tests use the supplied documents. Lexical retrieval and span matching can miss valid paraphrases. External network calls are excluded from the generated suite. A low-diversity corpus produces repetitive anchors.
Model proposals are constrained by deterministic checks. model_trace.json records successful, invalid, and budget-skipped calls.

## Run budget

Active time 93.45/120 seconds. Model tokens 3481/12000. Requirements review took 3.71 seconds outside the active budget.

## Prompt tournament

Winner **Grounded default**. Every scored candidate used the same generated suite. Ties keep the earlier candidate.

| Candidate | Passed | Score |
| --- | ---: | ---: |
| Grounded default | 18/24 | 75.0% |
| Exact evidence | 18/24 | 75.0% |
| Task coverage | 18/24 | 75.0% |

## Blind evaluation

**8/8** held-out questions passed on the same corpus with held-out questions.
These cases were scored after all repairs and did not select the final definition.

## Security conformance

4/4 fixed checks passed.
0 instruction-like source findings are recorded in security.json.
