# ForgeAI enterprise upgrade

## Baseline audit

The original checkout at `a10f5bf` passed eight tests before the upgrade. The application uses FastAPI, a shared Python factory and agent runner, optional Qwen through an OpenAI-compatible adapter, file-backed runs, and a vanilla JavaScript frontend.

| Area | Initial status |
| --- | --- |
| Assignment factory, guarded intake, definitions, 24-case evaluations, independent judge, targeted repairs, reports, CLI and browser chat | Implemented and verified against the existing suite |
| Prompt tournament, budgets, editable review, manual baseline, regression, four checked-in sample packs, theme controls | Implemented and verified against the existing tests and recorded artifacts |
| Groundability, tool verification, extraction, evaluation diversity, and observability | Partially implemented. Coverage is lexical, runtime traces are limited, and the model trace describes build calls |
| Blind evaluation, multilingual retrieval and verified replies, dedicated security checks, conflict resolution, confidence calibration, model tournament, feedback, impact analysis, enterprise authorization, OCR, releases, portable deployment | Missing as distinct workflows |
| External model quality, vision providers, and public deployment | Dependent on available infrastructure and representative evaluation datasets |

## Implementation sequence

- [ ] Preserve default 24-case builds and add a stratified blind evaluation mode that runs only after optimization.
- [ ] Add evidence conflict detection, confidence and abstention, and redacted execution traces on the shared runner.
- [ ] Add explicit multilingual adapters, OCR, and model comparison with independent evidence checks.
- [ ] Add defensive security conformance checks and opt-in workspace authorization at the API boundary.
- [ ] Add feedback validation, impact analysis, immutable releases, and standalone deployment exports.
- [ ] Expose working features in Studio, with explicit results for unavailable providers.
- [ ] Run existing and new tests at each increment, replay samples, smoke-test a fresh export, and document the results.
