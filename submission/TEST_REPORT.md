# Test report

The starting suite passed 32 tests. The new checks cover date and permission conflicts, a real embedded PDF chart, guest API restrictions and translation safety conditions.

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
- The real NLLB and E5 run produced cited Hindi and Tamil remote-work answers and abstention on less reliable cases. [Measurements](reports/multilingual-live.json)
- Local Qwen completed a direct model call. The sample tournament used deterministic retrieval and qualified no model. [Model evidence](reports/model-live.json)
- Reviewer builds and Docker checks used separate fictional sample data. [Deployment report](DEPLOYMENT_REPORT.md)

## Final acceptance checks

| Check | Observed result |
| --- | --- |
| Python baseline | 32 passed, zero failures, zero skips |
| Python final | 36 passed, zero failures, zero skips |
| Chromium workflow | Build, theme switching and persistence, blind score, defensive checks, chat and citations, feedback, release approval and activation, traces, ZIP export, dashboard, keyboard and responsive navigation |
| Resolutions and release names | Approved conflict generated a verified regression case. Named release, activation and rollback passed the API workflow |
| Direct chat routes | The Marine Procurement link retained its requested agent after the page and run list loaded |
| Recorded build | 18/24 baseline, 22/24 after the first repair, 24/24 final, and 8/8 on the held-out cases |
| Recorded browser errors | No uncaught page errors. The final video uses individually verified Hindi and Tamil clips |
| Full Docker app | Reviewer chat and route restrictions verified. An authorized owner build persisted across container restart and required re-authentication |
| Public reviewer application | HTTPS homepage, four fictional samples, cited chat and runnable agent ZIP verified without sign-in. Anonymous build and relay queue requests were rejected |
| Open gates | Independent native-language review, second live model provider, broader semantic and figure support |

[Recorded cases and outputs](reports/recorded-build/) · [Chromium smoke output](reports/chromium-smoke.txt) · [Screenshots](screenshots/)
