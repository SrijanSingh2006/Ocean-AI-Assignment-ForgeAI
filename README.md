# ForgeAI Studio

ForgeAI turns a one-paragraph brief and an unfamiliar document folder into a grounded Q&A agent. Each completed build includes a runnable definition, a generated evaluation suite, the full scoring history, accepted and rejected repairs, and a report with source gaps and residual failures.

## Run the web app

From the extracted project folder, with Python 3.10 or newer:

```sh
python launch.py
```

The launcher creates a project-local virtual environment, installs the dependencies, starts Studio, and opens it in your browser. Use `python launch.py --with-model` to start Qwen as part of the same command on Linux x86-64. An already-running compatible local model can be reused on any platform.

Load a sample project or enter your own brief and add documents. Enable **Review requirements** for the interview. Leave it disabled for an unattended run. Report tabs provide the requirements, evaluations, definition, and repair log. **Open chat** loads the generated definition and **Export run** downloads the outputs and source files.

For manual startup, install with `python -m pip install -e .` and run `python -m forgeai serve`. The default app address is `http://127.0.0.1:8000`.

### Enable the local model

The app runs with deterministic processing when the model is unavailable. Start the local model in a second terminal for model-assisted intake, generation, candidate evidence selection, and repair proposals. The committed demo artifacts were generated with the local model enabled.

On Linux x86-64:

```sh
./scripts/local-model.sh
```

The script downloads the official llama.cpp CPU build and Qwen2.5-0.5B-Instruct Q4_K_M weights (491 MB) on the first run. It verifies the model digest and listens on `127.0.0.1:8089`. The Studio runtime badge reflects model availability when the page loads.

On macOS, Windows, or Linux with [Ollama](https://ollama.com/), start Ollama, run `ollama pull qwen2.5:0.5b`, and set `FORGE_MODEL_URL=http://127.0.0.1:11434/v1` and `FORGE_MODEL_NAME=qwen2.5:0.5b` in the terminal launching ForgeAI. Other OpenAI-compatible local servers can use the same variables.

## Unattended and CLI use

```sh
python -m forgeai build --brief-file my-brief.txt --docs ./documents --out .runs/review
python -m forgeai chat --definition .runs/review/definition.json --docs ./documents
python -m forgeai demo --all-samples --out .runs/reproduced
```

For an interactive CLI interview, add `--interview`. Use `--ask "your question"` for single-turn CLI calls. Use `--no-model` for an explicitly deterministic run. `--iterations` accepts 0–3. Set `--token-budget` and `--latency-budget` to control model calls and active build time. The budget reserves a conservative token bound before each request and reports actual usage when available. Time spent waiting for requirements approval is excluded. An in-progress document parser can finish its current operation before the next deadline check. A repair with no score gain ends the loop. Use `--no-tournament` to score just the initial prompt and `--baseline-definition` to compare a hand-written definition.

To evaluate a changed corpus against a prior suite, add `--regression-evals .runs/review/evals.json` to the new build. In the web app, select **Set as regression baseline** in a completed run before loading the changed files. **Revised People Operations** selects the recorded original suite automatically. The comparison flags newly failing cases separately from existing failures.

### Input and tool examples

- PDF with a text layer, DOCX, CSV, Markdown, and UTF-8 TXT. The CLI supports recursive folders. The web app supports up to 30 files, 10 MB each.
- Supported topics are checked at intake. Include explicit phrases such as “Cover warranty claims and dockside delivery. Refuse customer payment information.” State the audience and requested tone.
- Catalogue lookups and arithmetic are enabled only when required by the brief. Try `Look up AF-310` or `Calculate 12 * 4.5` in the procurement demo.
- If the brief requires them, date and current weather are available via `What is today's date?` and `Weather at 18.94, 72.83`. Open-Meteo is the only runtime external tool and receives the typed coordinates on an explicit weather request.

## Sample packs and optional features

Select a pack in Studio, or download **Sample files** from the factory page. The standalone ZIP includes the source documents, brief, and check guide. [Sample guide](demos/SAMPLE_GUIDE.md)

- **Prompt tournament.** Three distinct system prompts are evaluated with the same source-derived suite. The report records scores, full candidate prompts, and the winner. Ties keep the earlier candidate.
- **Run budgets.** Set maximum model tokens and active seconds in Studio. The report records usage, the final stopping reason, and any optional evaluation skipped at the time limit.
- **Requirements review.** Approve the structured requirements or edit the scope, audience, tone, and answer/refusal topics. Edited topics are re-grounded before generation.
- **Hand-written comparison.** The People Operations pack includes a separately authored baseline agent. Both agents use the same documents, questions, and judge. The report lists case-level wins and losses.
- **Regression.** Re-run the old suite against updated sources. The revised People Operations pack changes two policy facts and includes a recorded regression report.
- **Web and hosting.** The factory and chat runner are available locally and through the owner-private hosted Studio while its Cloud workspace is running.

## Assignment evidence

| Area | Implementation |
| --- | --- |
| Intake and groundability | Structured requirements, up to five interviewer questions, scope and source coverage findings, and runtime exclusions for unsupported topics |
| Definition and runner | Declarative system prompt, document chunking, BM25 retrieval, selected tools, output schema, CLI and web chat |
| Evaluation | 24 source-derived cases per build, including source anchors, expected facts, cases to refuse, ambiguity, and cross-document questions when the corpus permits |
| Judge | Verifies source identity, exact citation text, fact spans, and expected status. This avoids position, self-preference, and verbosity rewards from an LLM judge |
| Optimizer | At most three patch attempts. Each patch targets a classified failure and is kept only if the score improves |
| Reporting and demos | Complete recorded evidence under `demos/people-ops/artifacts/` and `demos/marine-supply/artifacts/`; model and demo synthesis prompts under `prompts/` |

The baseline is intentionally economical: one passage, whole-query retrieval, and refusal when no usable topic is present. Repairs adjust only the relevant configuration fields after grading. The run retains the best measured definition and records every attempted patch. The evaluation suite stays fixed during repair.

Each demo contains `brief.txt`, its original `documents/`, and these evidence files under `artifacts/`:

- `requirements.json` with accepted topics, refusals, questions, and source gaps
- `initial_definition.json` and `definition.json`
- `evals.json` and `eval_results.json` with state, evidence, grading, and per-case outcomes for every attempt
- `iterations.json`, `scorecards.json`, `model_trace.json`, and `report.md`
- `tournament.json` and, where configured, `manual_comparison.json` or `regression.json`
- `run.json`, the aggregate used by the Studio

## Verification and limits

```sh
python -m pip install -e '.[test]'
python -m unittest discover -s tests -v
node --check static/app.js
```

The automated suite covers a separate exhibition-policy corpus, unsupported scope, targeted repairs, mutation regression, evidence integrity, document extraction, tools, and a multipart upload → review → build → chat → download flow through FastAPI. The recorded demos cover the local-model path.

Scores measure the generated suite for the supplied corpus. The optimizer and evaluation generator share that corpus, and a perfect score does not predict unseen-query accuracy. Lexical retrieval can miss paraphrases and source lists may expose incomplete topics. The response extracts verifiable passages, which can be wordier than a bespoke answer. Scanned-image PDFs need OCR before use. The web app is a single-user local workspace. Run data is persisted under `.runs/web/`, or the directory set with `FORGE_RUN_DIR`. Keep the service on loopback when using private documents.
