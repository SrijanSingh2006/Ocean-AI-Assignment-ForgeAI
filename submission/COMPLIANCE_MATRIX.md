# OceanAI assignment compliance

| Mandatory requirement | Implementation and verification | Status |
| --- | --- | --- |
| 1. Intake interviewer | [Factory intake](../forgeai/factory.py) and Studio review extract scope, audience, tone, and clarification. Browser and integration checks cover uploaded documents and edited approval. | PASS |
| 2. Groundability guard | Intake lists gaps and unreadable sources. Lexical evidence or a strong, distinct semantic match is required. The new aquarium audit flagged employee mortgage rates and the generated agent excluded the topic. Broader semantic relationships remain limited. | VERIFIED ON TESTED CORPORA |
| 3. Agent generator | [Factory definition](../forgeai/factory.py) records scope, audience, prompt, source inventory, tool permissions, retrieval, and output contract. The CLI and export load the same definition. | PASS |
| 4. Evaluation generator | Creates 20 or more evidence-anchored cases with answerable, cross-document, ambiguous and refusal categories. The fresh aquarium run produced 24 development and 8 separate holdout cases. Languages, tools and charts have additional focused tests. | PASS |
| 5. Automated judge | Independently verifies passage IDs, file, heading, locator, exact quote, expected facts and decision status. The final audit added a regression check for the wrong page number. | PASS |
| 6. Critic and optimizer | Up to three same-suite repairs with configuration differences, gains, accept/revert, and timing. Blind ordering and regression tests pass. | PASS |
| 7. Honest quality report | [Measured run evidence](reports/) preserves scorecards, failures, requirements, gaps, citations, usage, and stopping reason. | PASS |
| 8. Runnable agent | Browser chat, CLI, FastAPI, cited retrieval, tools and standalone export. The recording shows the sourced leave policy. | PASS |
| 9. Two demonstrations | [People Operations and Marine Procurement](../demos/) retain sources and recorded runs. Warehouse Tools and Revised People Operations remain available. | PASS |

| Optional requirement | Implementation and UI evidence | Status |
| --- | --- | --- |
| Prompt tournament | The **Comparisons** tab shows three candidates graded on the same suite. | PASS |
| Budget enforcement | The factory exposes token and latency budgets. Run logs show gains, timing and per-token efficiency when the provider supplies usage. | PASS |
| Human checkpoint | **Review requirements** pauses generation and allows edits. The video shows the workflow. | PASS |
| Factory vs human baseline | **Comparisons** on People Operations includes the same-suite manual baseline and gained and lost cases. | PASS |
| Regression mode | The revised sample and impact workflow identify affected cases and retain historical scores. | PASS |
| UI and hosting | The hosted Studio supports the owner workflow. The public reviewer app was verified without sign-in for sample chat and agent export. | PASS |

[Factory and judge](../forgeai/factory.py) · [Unseen-corpus results](reports/unseen-audit.json) · [Extended feature acceptance](FEATURE_MATRIX.md) · [Test and deployment evidence](TEST_REPORT.md)
