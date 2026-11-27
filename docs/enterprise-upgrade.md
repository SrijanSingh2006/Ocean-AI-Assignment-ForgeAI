# ForgeAI enterprise upgrade

## 1. Initial repository audit

The original checkout at `a10f5bf` passed eight tests before the upgrade. The application uses FastAPI, a shared Python factory and agent runner, optional Qwen through an OpenAI-compatible adapter, file-backed runs, and a vanilla JavaScript frontend.

| Area | Initial status |
| --- | --- |
| Assignment factory, guarded intake, definitions, 24-case evaluations, independent judge, targeted repairs, reports, CLI and browser chat | Implemented and verified against the existing suite |
| Prompt tournament, budgets, editable review, manual baseline, regression, four checked-in sample packs, theme controls | Implemented and verified against the existing tests and recorded artifacts |
| Groundability, tool verification, extraction, evaluation diversity, and observability | Partially implemented. Coverage is lexical, runtime traces are limited, and the model trace describes build calls |
| Blind evaluation, multilingual retrieval and verified replies, dedicated security checks, conflict resolution, confidence calibration, model tournament, feedback, impact analysis, enterprise authorization, OCR, releases, portable deployment | Missing as distinct workflows |
| External model quality, vision providers, and public deployment | Dependent on available infrastructure and representative evaluation datasets |

## Implementation sequence

- [x] Preserve default 24-case builds and add a stratified blind evaluation mode that runs only after optimization.
- [x] Add evidence conflict detection, confidence and abstention, and redacted execution traces on the shared runner.
- [x] Add explicit multilingual adapters, OCR, and model comparison with independent evidence checks.
- [x] Add defensive security conformance checks and opt-in workspace authorization at the API boundary.
- [x] Add feedback validation, impact analysis, immutable releases, and standalone deployment exports.
- [x] Expose working features in Studio, with explicit results for unavailable providers.
- [x] Run existing and new tests at each increment, replay samples, smoke-test a fresh export, and document the results.

## 2. Company assignment compliance

| Mandatory requirement | Status | Verification |
| --- | --- | --- |
| Intelligent Intake Interviewer | PASS | Intake identifies scope, audience and tone, recommends questions, and supports unattended or reviewed builds. The test suite exercises interview and budget behavior. |
| Groundability Guard | PARTIAL | The guard flags topics beyond the sources and abstains on insufficient runtime evidence. Intake matching is lexical and can miss synonyms or implicit support. |
| Automatic Agent Generator | PASS | Four original samples and a separate observatory brief produced runnable definitions. |
| Automatic Evaluation Generator | PASS | The default suite remains at 24 source-derived cases with answerable, cross-document, refusal and clarification cases. Blind mode has 32 before splitting. Tool and security checks run in additional targeted suites. |
| Independent Evaluation Judge | PASS | Python verifies returned quotes, source identity, decision, and expected facts independently of draft generation. |
| Critic–Optimizer Loop | PASS | All four sample replays progressed from 18/24 through 22/24 to 24/24. Tests confirm the loop accepts only improvements and preserves a completed result when time expires. |
| Honest Evaluation and Reporting | PASS | Run reports retain remaining failures, per-case findings, budgets, fallback, and separate regression and holdout results. |
| Runnable Generic Agent | PASS | The Python CLI and Studio accept generated definitions. The deployment check answered from frozen evidence in a fresh package. |
| Two Complete Demonstrations | PASS | People Operations and Marine Supply replayed on local Qwen. Sample briefs, source files and actual artifacts are committed. |

| Optional requirement | Status | Verification |
| --- | --- | --- |
| Prompt tournament | PASS | Three prompt candidates run on the same development suite. Existing comparisons and tie behavior were preserved. |
| Token and latency budgets | PASS | Both controls are available in Studio and the CLI. Regression tests exercise early stopping and a time-limited repair. |
| Human checkpoint | PASS | The workspace pauses after intake, exposes source coverage and structured edits, and continues after authorized approval. |
| Factory versus hand-written baseline | PASS | The People Operations replay recorded factory 24/24 and hand-written 22/24 on the same suite. |
| Regression testing | PASS | The revised People Operations sample passed its new suite at 24/24. Three cases from the previous policy regressed and were reported separately. |
| UI and hosting | PASS | Chromium verified Studio locally. The owner-private deployment served the enterprise bundle, dashboard, chat citations, execution traces, and agent export. |

## 3. Additional features implemented

| Feature | Status | Implemented workflow |
| --- | --- | --- |
| Blind evaluation | PASS | Deterministic category-stratified split with distinct development and held-out cases. The optimizer never receives the holdout cases. Tests spy on scoring order and verify disjoint IDs. |
| Multilingual agent | PARTIAL | Script and code-mix detection, Unicode retrieval, optional embeddings and translator adapters, stable number and identifier checks, round-trip verification, language selector, and original citations. Hindi and Tamil still need a suitable validated provider. |
| Security conformance | PARTIAL | Static scanning and fixed offline checks for prompt boundaries, input validation, tool registration, and instruction-like sources. Coverage is limited to these controls and the checked patterns. |
| Document conflict intelligence | PARTIAL | Detects comparable numeric disagreements, presents source evidence, asks for clarification, and supports audited selection of the applicable source. Qualitative policy contradictions and richer revision arbitration remain open. |
| Agent flight recorder | PASS | Captures redacted retrieval and tool decisions, rejected candidates, selected passages, evidence score, timing, and final response. Staff can open the timeline, and admins can delete a trace. Retention applies on reads. |
| Confidence and abstention | PASS | Gives a deterministic score from coverage, valid evidence, supporting sources, and conflicts. Scores and OCR quality can trigger abstention. Calibration measures reliability and errors on disjoint labeled data. |
| Multi-model tournament | PARTIAL | Adapter profiles reuse the same suite, judge, and tool conditions. The leaderboard reports latency, quality, tokens and optional cost. A comparative live result requires several providers or a suite that activates model-assisted retrieval. Security and translation measurements have separate reports. |
| Feedback learning | PASS | The chat response records trace-linked feedback. An administrator can validate evidence and promote the case, inspect a scored repair suggestion, and run it in development or regression. |
| Document impact graph | PASS | Compares fingerprints and changed sections, links known passages and affected cases using stored provenance, and can run targeted and full regression. |
| Privacy and access control | PASS for local mode | Authentication, roles, per-workspace and per-agent access, access to the complete source collection, session and change audit, and pattern-based trace redaction. Production identity and distributed session storage are separate deployment work. |
| Multimodal documents | PARTIAL | Preserves native PDF, DOCX, CSV, Markdown and text extraction. Extracts text from scanned PDF pages, uploaded photos, and embedded DOCX images while retaining confidence and coordinates. Visual semantics and complex-layout interpretation remain open. |
| Releases and rollback | PASS | Freezes definitions, source files, checksums, indexed evidence, and available reports. Approval, activation, comparisons and rollback preserve earlier versions. The integration test restores the previous source text and answer. |
| Standalone deployment | PASS | Builds a ZIP with agent, sources, portable corpus index, tools, tests and reports where available, Python runner, HTTP API, dependency file, Dockerfile and Compose. Verified in a clean Python environment and a container. |

## 4. Files modified

| Area | Files and purpose |
| --- | --- |
| Shared runtime changes | `factory.py`, `corpus.py`, `registry.py`, `model.py`, `cli.py`, and `web.py` keep existing entry points and connect runtime evidence, configuration, OCR, authorization and CLI flags. |
| New runtime modules | `blind_eval.py`, `multilingual.py`, `embeddings.py`, `ocr.py`, `conflict_detector.py`, `confidence.py`, `security.py`, `flight_recorder.py`, and `privacy.py` handle the shared evaluation and answer boundaries. |
| New operations modules | `enterprise_api.py`, `model_tournament.py`, `feedback.py`, `impact.py`, `versioning.py`, and `deployment.py` implement authorized workflows and export. |
| Studio | `static/enterprise.js` adds the live dashboard and engineering controls. `app.js`, `index.html` and `style.css` connect navigation, settings, chat, and accessible presentation to the API. |
| Private hosting | `hosting/` contains the Worker, workspace connector, and packager for the deployed browser and API relay. |
| Tests and evidence | Nine new Python test modules cover enterprise behavior. `scripts/check-enterprise-ui.mjs` drives a real Chromium session. New synthetic artifacts and screenshots are under `demos/enterprise-evidence` and `docs/screenshots`. |
| Storage | SQLite tables for feedback and releases initialize on first use. Existing file-based runs still load, and their data requires no migration. New release snapshots coexist with existing reports. |
| Dependencies | Python’s SQLite is built in. Pillow was added to the test extra for image fixtures. Tesseract and Poppler are optional system tools. The browser smoke test uses Node.js and Chromium, with no npm test dependency. |

No tracked files were removed. Use `git diff --name-status a10f5bf..HEAD` for the per-file inventory.

## 5. Test results

| Check | Actual result |
| --- | --- |
| Existing suite before changes | 8 passed |
| Original suite at final verification | 8 passed |
| New tests at final verification | 24 passed |
| Total | **32 passed, 0 failed, 0 skipped** |
| Integration and API | Real build, conflict resolution, grounded chat, feedback promotion, application of release permissions, release activation, rollback, and export. |
| Browser | Chromium built a demo and used the holdout report, conformance controls, language report, release approval and activation, export, sourced chat, feedback, trace and dashboard. It exercised the theme toggle, saved preference, system mode, mobile drawer, keyboard input and reduced motion. No uncaught page exceptions were captured. |
| OCR | Real scanned PDF and DOCX with an embedded image retained the extracted text, identifying locator and pixel coordinates. |
| Security and privacy | Fixed synthetic corpus checks passed. Workspace and source restrictions, trace redaction, compact credential redaction, and expired reads passed. |
| Local language replay | English 2/2 scored and passed. Hindi 0/2 scored, both unverified. Tamil 0/2 scored, both unavailable. |
| Blind scoring | People Operations 24/24 development and 8/8 blind. Independent observatory brief and corpus 24/24 development and 8/8 blind. |
| Single live model profile | One responsive Qwen profile scored the 24-case People Operations suite entirely on deterministic retrieval. The report made no model recommendation. |

## 6. Actual working verification

- All four Qwen-assisted original builds replayed successfully. Each produced quality reports and CLI-compatible definitions. The baseline and three lost regression checks remain individually inspectable.
- The observatory build used a different brief and sources, including a CSV inventory. It produced a separate holdout report and a runnable agent. [Source fixtures and measured reports](../demos/enterprise-evidence/README.md)
- The People Operations browser run returned 22 days from `Leave-Handbook.md` and retained its original locator. The Operations Lab CLI returned 84 for `Calculate 12 * 7`.
- The enterprise API test detected conflicting leave allowances, recorded the admin's citation and reason, answered from the chosen 18-day source, activated a snapshot containing a 20-day policy, and restored the 18-day result on rollback.
- The browser submitted feedback against a real chat trace. The review tests validated anchors before promotion and scored a repair suggestion without automatically applying it.
- The exported agent answered from a clean Python installation and a container, with a health response and HTTP 401 for an unauthenticated chat when configured with a bearer token. The authenticated result cited the bundled handbook.
- The private hosted URL served the upgraded frontend and engineering endpoints. A hosted chat returned 22 days with the handbook citation and a linked execution trace. Hosted agent export returned the deployment ZIP. [Hosted Studio](https://forgeai-studio-project.blondebiscuit2.chatgpt.site/) · [Hosting source](../hosting/README.md)
- Browser captures show actual completed workflows. [Factory](screenshots/factory-light.jpg) · [Blind evaluation](screenshots/blind-results.jpg) · [Flight recorder](screenshots/execution-trace.jpg) · [Mobile dashboard](screenshots/dashboard-mobile.jpg)

## 7. Remaining limitations

- The local Qwen translator lacks verified coverage for the tested Hindi and Tamil prompts. Cross-language embeddings have controlled integration coverage and need a live deployment endpoint.
- The model tournament requires qualified provider contributions to recommend a winner. Benchmark coverage of several live providers, multilingual model quality and provider-dependent reliability remains open.
- Security measurement is scoped to offline conformance and static checks. Pattern-based trace redaction detects selected shapes such as email, phone, national ID and credential strings.
- Conflict support is limited to comparable numeric claims. OCR supports readable source text and native tables. Complex layout, chart and figure understanding remain open.
- Intake groundability uses vocabulary overlap. All reported evaluation scores describe the stated datasets. The confidence calibration example requires labeled data supplied by the operator.
- Workspace sessions are process-local. The current private hosted deployment relies on the Site owner's session and an active Python workspace. Shared multi-tenant hosting requires an external identity and session architecture, and suitable retention and management procedures.

## 8. Final completion matrix

| Capability | Status |
| --- | --- |
| Build, evaluate and improve agents with the original factory | PASS |
| Held-out evaluation and new-corpus replay | PASS |
| Evidence, traces, feedback, impact, releases and portable deployment | PASS |
| Multilingual and cross-language operation | PARTIAL |
| Security measurement and advanced conflict detection | PARTIAL |
| Multi-provider benchmarking and multimodal understanding | PARTIAL |
| Owner-private hosted Studio | PASS |
| Shared multi-tenant deployment | BLOCKED on deployment configuration |

## 9. Launch and test

From the repository root, install the project and start the integrated API and frontend.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m forgeai serve --host 127.0.0.1 --port 8874
```

Open `http://127.0.0.1:8874` for Studio or `http://127.0.0.1:8874/docs` for the OpenAPI explorer. On Windows PowerShell, activate the environment with `.\.venv\Scripts\Activate.ps1`. The convenience command `python launch.py --port 8874` prepares dependencies and opens Studio.

In a second terminal, start the optional local CPU model and then replay the demos and tests.

```bash
bash scripts/local-model.sh
```

```bash
python -m unittest discover -s tests -v
python -m forgeai demo --all-samples --out .runs/enterprise-replays
```

Install Tesseract and Poppler if you want the real OCR tests to run, and use `FORGE_OCR=1` to expose OCR in Studio. For screenshot and browser checks, start Studio on port 8874 with an isolated `FORGE_RUN_DIR` and with local authorization disabled. In separate terminals run the following commands using Node.js 22 or newer.

```bash
chromium --headless --remote-debugging-port=9227 --user-data-dir=.runs/chromium-qa about:blank
node scripts/check-enterprise-ui.mjs
```

The browser test writes screenshots and a synthetic agent ZIP to `.runs/ui-qa`. It builds and changes a disposable sample run.

## 10. Recruiter walkthrough

1. Start the model and Studio. Load People Operations, enable **Review requirements**, **Blind evaluation**, and **Security conformance**, and start a build.
2. Inspect source coverage, approve the requirements, and watch the factory select an agent. Compare baseline, repaired scores, prompt candidates, and the blind result.
3. Open chat and ask about annual leave, then open the citation. Ask an unsupported question to see a refusal. Submit feedback on a supported answer and inspect its trace in **Engineering lab**.
4. Review the feedback and open the security conformance report. Use the language selector and language evaluation to show what the configured provider can verify.
5. Build the revised People Operations sample with the original as its regression baseline. Analyze document impact to see the changed policy and affected cases.
6. Create, approve, and activate a release. Compare it with the prior release and roll back, then ask the same policy question to confirm the sources changed with the definition.
7. Export an agent, start its standalone HTTP service, and query the packaged snapshot. Build the observatory brief and CSV to show that the same factory works with different documents.
