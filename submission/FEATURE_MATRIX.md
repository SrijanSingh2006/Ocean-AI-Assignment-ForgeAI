# Signature feature acceptance

| Feature | Status | Implementation and observed acceptance |
| --- | --- | --- |
| Blind Evaluation Lab | PASS | Category-stratified development and holdout split, ordering checks, separate artifacts, and category and score gap indicators. |
| Multilingual intelligence | PARTIAL | Real NLLB and multilingual E5 adapters. Hindi and Tamil remote-work answers passed automated source checks. Other questions can abstain, and independent native-language review is pending. |
| Live model tournament | BLOCKED for two-provider acceptance | Configurable profiles, same-suite judging, usage, score and latency. A direct local Qwen call completed. The sample suite took the deterministic path. Two independent configured providers remain unverified. |
| Semantic document conflicts | PARTIAL | Numeric claims, dates, permissions and matching conditional scopes. Human-selected precedence can create a verified regression case. Broad policy contradictions and subtle scope overlap remain limited. |
| Chart and figure understanding | PARTIAL | Embedded bar charts use shape and label checks. A real PDF fixture answers maximum, minimum and trend questions with a figure citation. Other chart types and complex layouts still require review. |
| Defensive security conformance | PARTIAL | Covers fixed source checks, tool boundaries, workspace isolation, redaction and read-only guest requests. Scope is deterministic defensive testing. |
| Flight Recorder | PASS | Actual evidence, tool, verification and decision events, redaction, timings and retention. The recording opens a real trace. |
| Confidence and abstention | PARTIAL | Evidence and translation gates can answer, clarify or refuse. Disjoint labeled calibration reports work. Broad domain threshold validation remains open. |
| Feedback-driven learning | PASS | Chat feedback and authorized review, evidence validation, and inclusion in targeted regression are tested. |
| Document impact graph | PASS | File fingerprints and linked sections, passages, previous answers and evaluation cases. |
| Enterprise multi-tenancy | PARTIAL | Backend roles, workspace checks, scoped SQLite metadata and isolated sample access. Managed shared identity and PostgreSQL are pending. |
| OCR and document processing | PARTIAL | Text-layer and OCR provenance, DOCX inline images and tables, and verified labeled bars. Broader layouts and visual semantics remain open. |
| Version control | PASS for core workflow | Named releases with frozen sources and definitions, hashes, approvals, activation, diffs and rollback. |
| Standalone deployment | PASS | Agent definition, source evidence, runner, environment template and Docker support. Export tests and runtime evidence are retained. |

[Language measurements](reports/multilingual-live.json) · [Model run](reports/model-live.json) · [Chart answers](reports/figures-live.json)
