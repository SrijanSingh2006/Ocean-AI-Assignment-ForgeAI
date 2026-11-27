"""Partition a source-derived evaluation suite into development and holdout cases."""

import hashlib
from collections import defaultdict


def stratified_holdout(cases, seed="forgeai-v1"):
    groups = defaultdict(list)
    for case in cases:
        groups[case["category"]].append(case)
    target = round(len(cases) / 4)
    if target < 1 or len(groups) == len(cases):
        raise ValueError("Blind evaluation needs repeated question categories.")
    quotas = {key: 0 for key in groups}
    for _ in range(target):
        available = [key for key in groups if quotas[key] < len(groups[key]) - 1]
        if not available:
            break
        kind = max(available, key=lambda key: (len(groups[key]) / 4 - quotas[key], key))
        quotas[kind] += 1

    def fingerprint(case):
        return hashlib.sha256(f'{seed}\n{case["id"]}\n{case["question"]}'.encode()).digest()

    blind_ids = {
        case["id"] for kind, rows in groups.items()
        for case in sorted(rows, key=fingerprint)[:quotas[kind]]
    }
    development = [case for case in cases if case["id"] not in blind_ids]
    blind = [case for case in cases if case["id"] in blind_ids]
    return development, blind
