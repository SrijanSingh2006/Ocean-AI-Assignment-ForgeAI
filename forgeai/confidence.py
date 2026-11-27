"""Observable evidence signals and evaluation against labeled validation examples."""

import math

BANDS = ((0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0))


def evidence_confidence(coverages, passages, corpus, conflict=False):
    coverage = min(coverages, default=0.0)
    valid = bool(passages) and all(p.get("id") in corpus.by_id for p in passages)
    distinct = len({p["document"] for p in passages})
    # A second source helps support coverage but does not prove independence.
    score = 0.75 * coverage + 0.20 * valid + 0.05 * min(distinct, 2) / 2
    return {
        "score": round(score if valid and not conflict else 0, 3),
        "kind": "heuristic",
        "coverage": round(coverage, 3), "verified_passages": valid,
        "source_count": distinct, "conflict": conflict,
    }


def calibration_report(training, validation):
    """Fit observed band frequencies on one set and measure them on a disjoint set."""
    if not training or not validation or {r["id"] for r in training} & {r["id"] for r in validation}:
        raise ValueError("Calibration needs separate, nonempty labeled datasets with disjoint case IDs.")
    rows = training + validation
    if any(type(r["correct"]) is not bool or not math.isfinite(r["score"]) or not 0 <= r["score"] <= 1 for r in rows):
        raise ValueError("Each calibration example needs a score in [0, 1] and a boolean outcome.")

    def band(score):
        return min(int(score * len(BANDS)), len(BANDS) - 1)

    all_rows = []
    errors = []
    for index, (lower, upper) in enumerate(BANDS):
        fit = [r for r in training if band(r["score"]) == index]
        check = [r for r in validation if band(r["score"]) == index]
        estimate = sum(r["correct"] for r in fit) / len(fit) if fit else None
        observed = sum(r["correct"] for r in check) / len(check) if check else None
        if estimate is not None:
            errors.extend((estimate - r["correct"]) ** 2 for r in check)
        all_rows.append({"lower": lower, "upper": upper, "training_count": len(fit), "validation_count": len(check),
                         "estimated_reliability": estimate, "observed_reliability": observed})

    accepted = [r for r in validation if r.get("status") == "answered"]
    refused = [r for r in validation if r.get("status") == "refused"]
    return {
        "bands": all_rows,
        "validation_examples": len(validation), "calibration_coverage": len(errors) / len(validation),
        "brier_score": sum(errors) / len(errors) if errors else None,
        "answer_coverage": len(accepted) / len(validation),
        "false_answer_rate": sum(not r["correct"] for r in accepted) / len(accepted) if accepted else None,
        "false_refusal_rate": sum(not r["correct"] for r in refused) / len(refused) if refused else None,
    }
