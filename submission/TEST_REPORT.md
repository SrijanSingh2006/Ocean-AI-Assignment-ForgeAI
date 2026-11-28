# Test report

The starting suite passed 32 tests. The final audit reran the complete suite and added checks for weak semantic coverage and wrong citation locators. Earlier additions cover policy conflicts, an embedded PDF chart, guest access and multilingual integrity.

```bash
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
node --check static/app.js
node --check static/enterprise.js
node --check hosting/worker.mjs
```

Install Tesseract and Poppler for OCR tests. Add the optional languages extra and install NLLB and E5 separately for live multilingual tests. The [browser run instructions](../docs/enterprise-upgrade.md#9-launch-and-test) use Chromium and an isolated test workspace.

## Live evidence

- Three chart questions cite the verified embedded figure. [PDF fixture](fixtures/Regional%20Shipments.pdf) · [Results](reports/figures-live.json)
- The language suite checks annual leave, remote work, the training PDF, sick leave, travel, a revised policy, and out-of-scope refusal. It verifies the expected facts, language, source document, locator and exact evidence on each case. [Measurements](../demos/people-ops/artifacts/multilingual_results.json)
- Local Qwen completed a direct model call. The sample tournament used deterministic retrieval and qualified no model. [Model evidence](reports/model-live.json)
- Reviewer builds and Docker checks used separate fictional sample data. [Deployment report](DEPLOYMENT_REPORT.md)

## Final acceptance checks

| Check | Observed result |
| --- | --- |
| Python baseline | 32 passed, zero failures, zero skips |
| Python final | 40 passed, zero failures, zero skips |
| Multilingual reviewer replay | 19 passed across English, Hindi, Tamil, Romanized inputs, and script-English mixes. |
| Uploaded English HR PDF | 8 passed across two policies in English, Hindi, Tamil and Romanized Hindi. Replies cited the same source page across languages. |
| Unseen paid-leave translation | Hindi and Tamil retained the 14-day allowance and paid condition. A regression test rejects a translation that drops the paid condition. |
| Chromium workflow | Build, theme switching and persistence, blind score, defensive checks, chat and citations, feedback, release approval and activation, traces, ZIP export, dashboard, keyboard and responsive navigation |
| Chromium on the public deployment | Loaded all four samples without sign-in. Filtered the language report to five Tamil cases, selected Tamil as the answer preference, and opened the original English PDF citation. |
| Fresh unseen-corpus build | Aquarium policies without an operator checkpoint. Qwen made 14 successful calls. 24/24 development and 8/8 holdout cases passed. Intake flagged the unsupported mortgage topic. |
| Resolutions and release names | Approved conflict generated a verified regression case. Named release, activation and rollback passed the API workflow |
| Direct chat routes | The Marine Procurement link retained its requested agent after the page and run list loaded |
| Recorded build | 18/24 baseline, 22/24 after the first repair, 24/24 final, and 8/8 on the held-out cases |
| Recorded browser errors | No uncaught page errors. The final video uses individually verified Hindi and Tamil clips |
| Full Docker app | Reviewer chat and route restrictions verified. The image also served on a non-default platform port. An authorized owner build persisted across container restart and required re-authentication. |
| Render Blueprint | Validated against Render's published schema. Docker behavior was checked locally. A Render account connection is required to launch an instance. |
| Public reviewer application | HTTPS homepage, four fictional samples, cited chat and runnable agent ZIP verified without sign-in. Anonymous build and relay queue requests were rejected |
| Open gates | Independent native-language review of fresh translations, second live model provider, broader semantic and figure support |

[Recorded cases and outputs](reports/recorded-build/) · [Fresh unseen-corpus audit](reports/unseen-audit.json) · [Chromium smoke output](reports/chromium-smoke.txt) · [Current website screenshots](../docs/screenshots/)
