"""Benchmark configured model profiles on a fixed evaluation suite."""

import json
import os
import time

from .model import LatencyBudgetExceeded, LocalModel
from .multilingual import LANGUAGES, translate


def configured_profiles():
    raw = os.getenv("FORGE_MODEL_PROFILES", "[]")
    try:
        profiles = json.loads(raw)
    except ValueError as exc:
        raise ValueError("FORGE_MODEL_PROFILES must be a JSON array.") from exc
    if not isinstance(profiles, list) or len(profiles) > 5:
        raise ValueError("Configure at most five model profiles.")
    unique = set()
    for profile in profiles:
        if not isinstance(profile, dict) or not {"id", "url", "model"} <= profile.keys():
            raise ValueError("Each profile needs id, url, and model.")
        if profile["id"] in unique or not profile["url"].startswith(("http://", "https://")):
            raise ValueError("Model profile IDs must be unique and point to a compatible URL.")
        unique.add(profile["id"])
    return profiles


def compare_models(definition, corpus, cases, profiles, minimum_score=80, latency=55):
    from .factory import score_agent

    deadline = time.monotonic() + latency
    comparisons = []
    for profile in profiles:
        start = time.monotonic()
        model = LocalModel(url=profile["url"], name=profile["model"],
                           api_key=os.getenv(profile.get("api_key_env", "")))
        model.deadline = deadline
        entry = {"id": profile["id"], "model": model.name, "status": "unavailable"}
        if model.remaining_time() <= 0:
            entry["status"] = "latency_limit"
        elif model.probe():
            try:
                scored = score_agent(definition, corpus, cases, model, 0)
                count = len(scored["results"])
                replies = scored["results"]
                refused = [r for r in replies if r["checks"]["refused_when_expected"] is not None]
                model_used = any(call["status"] == "ok" for call in model.calls)
                entry.update(
                    status="scored", scorecard=scored["scorecard"], tokens=model.tokens,
                    model_used=model_used, qualifies=model_used and scored["scorecard"]["score"] >= minimum_score,
                    grounding=sum(r["checks"]["grounded"] for r in replies) / count,
                    correctness=sum(r["checks"]["correct"] for r in replies) / count,
                    refusal_accuracy=sum(r["checks"]["refused_when_expected"] for r in refused) / len(refused) if refused else None,
                )
                rate = profile.get("price_per_million_tokens")
                if isinstance(rate, (int, float)) and rate >= 0 and model.calls and all(c["status"] == "ok" and c["tokens"] for c in model.calls):
                    entry["cost"] = round(model.tokens * rate / 1_000_000, 8)
            except LatencyBudgetExceeded:
                entry["status"] = "latency_limit"
        entry["elapsed_seconds"] = round(time.monotonic() - start, 3)
        comparisons.append(entry)
    qualified = [row for row in comparisons if row.get("qualifies")]
    winner = min(qualified, key=lambda row: (-row["scorecard"]["score"], row["elapsed_seconds"], row["id"])) if qualified else None
    return {"minimum_score": minimum_score, "recommended": winner["id"] if winner else None, "models": comparisons}


def compare_languages(agent, cases, translator, latency=40):
    from .factory import judge

    seeds = [next((case for case in cases if case["expected_status"] == status), None)
             for status in ("answered", "refused")]
    if translator:
        translator.deadline = time.monotonic() + latency
    results = []
    for code in LANGUAGES:
        for case in (case for case in seeds if case):
            try:
                question = case["question"] if code == "en" else translate(case["question"], code, translator)
                if not question:
                    results.append({"language": code, "case_id": case["id"], "status": "unavailable"})
                    continue
                response = agent.answer(question, requested_language=code)
                if response.get("translation_status") == "unverified":
                    results.append({"language": code, "case_id": case["id"], "status": "unverified"})
                    continue
                canonical = response
                if response.get("translation_status") in {"source_localization", "verified_roundtrip"} and response["status"] == "answered":
                    joiner = "\n" if response.get("tool") == "csv_lookup" else "\n\n"
                    canonical = {**response, "answer": joiner.join(c["quote"] for c in response["citations"])}
                grade = judge(case, canonical, agent.corpus)
                results.append({"language": code, "case_id": case["id"], "status": "scored", "passed": grade["passed"],
                                "expected_status": case["expected_status"], "response": response})
            except LatencyBudgetExceeded:
                results.append({"language": code, "case_id": case["id"], "status": "latency_limit"})
    return {"languages": {
        code: {"passed": sum(bool(row.get("passed")) for row in results if row["language"] == code),
               "scored": sum(row["status"] == "scored" for row in results if row["language"] == code),
               "total": sum(row["language"] == code for row in results)}
        for code in LANGUAGES}, "results": results}
