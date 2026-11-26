# ForgeAI sample documents

All sources and records in these packs are fictional.

| Pack | Contents | What to check |
| --- | --- | --- |
| People Operations | Leave, hybrid work and travel Markdown, a text-layer PDF, and DOCX onboarding | Ingestion with page/block citations, policy Q&A, unsupported requests, prompt tournament, and side-by-side hand-written comparison |
| Marine Procurement | Part catalogue, supplier availability and purchase basket CSVs, supplier terms and dockside Markdown | SKU and order lookups, purchase arithmetic, a cross-document answer, and a procurement refusal |
| Warehouse Tools | Inventory and shipment status CSVs, receiving procedures TXT | All four runtime tools, a missing identifier, grounded Q&A, and payroll refusal |
| Revised People Operations | Same filenames with revised leave and travel policies | Set the original People Operations run as regression baseline and load the revised pack |

## Quick checks

- In People Operations, ask about **annual leave**. The original handbook specifies **22 paid days**. Ask who verifies onboarding access to test DOCX citations. Ask about the training allowance to test the PDF.
- In Marine Procurement, ask **Look up AF-310**, **Look up PB-102**, and **Calculate 3 * 46.50**. Expected total **139.5 EUR** from the figures supplied. **Look up AF-999** should return a missing-row refusal.
- In Warehouse Tools, ask **Look up BX-410**, **Look up SH-083**, **Calculate 5 * 4.80**, **What is today's date?**, and **Weather at 18.94, 72.83**. Current date and weather vary. The latter calls Open-Meteo.
- Enable **Review requirements**, edit a field, then approve. The factory rechecks any edited topics against your sources.
- Enable **Prompt tournament** and open **Comparisons** in the completed report. The shortlisted prompts share a generated evaluation set and judge.
- Set a smaller token budget to exercise deterministic fallback. A run can retain its best complete evaluation if the time limit interrupts further work.
- Use the revised pack with the original People Operations baseline. The source changed to **25 paid days** and **45 days for expense submissions**. The regression report should flag stale expected facts while the newly generated evaluation describes the revised rules.
