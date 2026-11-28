# Verification and scope

The checks below document measured behavior for the application and its fictional corpora. The repository keeps the full sample build artifacts, source documents, and evaluation cases alongside the runnable code.

## Assignment coverage

| Requirement | Evidence |
| --- | --- |
| Intake interview and groundability | A brief and source inventory produce structured requirements and up to five optional questions. The unseen aquarium run flagged employee mortgage rates as unsupported. |
| Agent definition | Each build saves the scope, instructions, retrieval settings, permitted tools and response contract as portable JSON. |
| Evaluation generation and judge | The unseen run generated 24 development cases and eight separate holdout cases. Citation tests reject altered text, source identities and page locators. |
| Critic and optimizer | The same suite is rerun after targeted settings changes. Scorecards record the original score, candidate results, accepted changes and remaining failures. |
| Quality report | Each run saves the suite, results, scorecards, model usage, source gaps and stopping reason. |
| Runnable agent | The browser, CLI and standalone export use the shared agent runtime. |
| Two complete demonstrations | People Operations and Marine Procurement keep their briefs, files and recorded reports. Warehouse Tools and Revised People Operations exercise tools and regression. |

| Optional feature | Evidence |
| --- | --- |
| Prompt tournament | Three prompts are graded on the same suite in the People Operations report. |
| Budget enforcement | Builds accept token and latency limits and preserve a complete scorecard when they reach a limit. |
| Human checkpoint | An authorized reviewer can answer clarifying questions or edit the scope before generation. |
| Manual baseline | The People Operations comparison shows per-case differences against a hand-written definition. |
| Regression mode | The revised sample replays earlier cases after the policy changed. |
| Web interface and deployment | Factory, report, chat, release and export workflows were exercised in Chromium. Docker reviewer and authenticated owner modes were tested locally. |

## Recorded checks

| Check | Result |
| --- | --- |
| Python regression and integration tests | 40 passed. Includes auth boundaries, grounded judging, OCR, feedback, releases and snapshot integrity. |
| Unseen corpus | A fresh aquarium document collection passed 24/24 development and 8/8 holdout cases. Qwen completed 14 calls. |
| Multilingual reviewer replay | With NLLB and E5 configured, 19 cases passed across English, Hindi, Tamil, Romanized questions and script-English mixes. |
| English PDF upload | Eight questions passed across two policies and four forms of input. Responses retained the same source PDF page. |
| Browser | Validated build and review screens, light and dark themes, mobile navigation, blind evaluation, chat and original citations, feedback, trace viewing, and export. |
| Docker | Verified sample access, the platform port, protected owner builds, ZIP export, and workspace persistence across restart. |
| Public Render service | Verified all four sample reports and agent exports without sign-in, English, Hindi and Tamil cited replies, procurement refusal, download integrity, and restricted writes. Chromium verified the report tabs, language filter, citation expansion, theme persistence and mobile menu. [Live reviewer app](https://forgeai-reviewer.onrender.com/) |
| Runtime tools | Verified CSV lookup, arithmetic and the host date on Render. Open-Meteo returned live weather in a network-enabled workspace. The public tool registry explains the network requirement. |

[Unseen-corpus evidence](evidence/unseen-audit.json) · [Multilingual results](../demos/people-ops/artifacts/multilingual_results.json) · [Chart fixture](evidence/Regional%20Shipments.pdf) · [Chart results](evidence/figures-live.json) · [Model comparison evidence](evidence/model-live.json) · [UI screenshots](screenshots/)

## Additional features and limits

- **Blind evaluation, execution traces, feedback, document impact, releases and standalone export** have verified workflows. Version changes retain a frozen definition, source fingerprints and extracted passages. Feedback becomes a test case only after approval.
- **Multilingual answers** retain original citations and check identifiers, numbers and supported policy qualifiers. Review by independent native speakers and broader unseen corpora remains open.
- **Model comparison** supports multiple configured endpoints. The available live evidence covers one local Qwen provider, and a qualifying head-to-head run with a second provider remains open.
- **Conflicts, OCR and figures** cover matching policy claims, text and supported scanned documents, and labeled vertical bars. Broader conflict semantics, other chart types and complex layouts still require validation.
- **Confidence and conformance** report evidence checks, calibration from supplied labels, and fixed defensive tests. The confidence score is a heuristic unless calibrated on independent data.
- **Workspace isolation** uses roles, document permissions and restricted public sample access. The deployment uses single-process sessions and workspace files with SQLite metadata. Distributed identity, storage and managed database support remain open.

## Reproduce

~~~sh
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
python -m forgeai demo --all-samples --out .runs/reproduced
~~~

Install Tesseract and Poppler for the OCR and figure checks. To replay the language suite against a server with NLLB and E5 configured, run `PYTHONPATH=. python scripts/check_multilingual.py SERVER_URL`. The Docker and Render setup, including provider configuration and deployment limits, is documented separately. [Deployment guide](deployment.md)
