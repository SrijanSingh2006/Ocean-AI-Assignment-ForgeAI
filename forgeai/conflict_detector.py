"""Find comparable numeric claims with conflicting values and preserve their sources."""

from collections import defaultdict
from hashlib import sha256
import re

from .corpus import clean, terms

MEASURE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(calendar days?|working days?|business days?|days?|hours?|weeks?|months?|percent|%)(?!\w)",
    re.I,
)
SUBJECT = re.compile(r"^(.{2,90}?)\s+(?:is|are|equals?|lasts?|takes?|requires?)\s+(?:up to\s+)?$", re.I)
QUALIFIERS = {
    "carryover", "entitlement", "probation", "contractor", "permanent", "calendar", "working",
    "business", "sick", "remote", "expense", "reimbursement", "minimum", "maximum",
}
VERSION = re.compile(r"\b(?:20\d{2}[-_]\d{2}[-_]\d{2}|20\d{2}|v\d+(?:\.\d+)*)\b", re.I)


def numeric_conflicts(corpus):
    groups = defaultdict(list)
    for passage in corpus.passages:
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", passage["text"]):
            for measure in MEASURE.finditer(sentence):
                heading = passage["heading"]
                if heading == passage["title"]:
                    subject = SUBJECT.match(sentence[:measure.start()])
                    if subject is None:
                        continue
                    heading = subject[1]
                topic = sorted(set(terms(heading)))
                if not topic:
                    continue
                unit = measure[2].casefold().removesuffix("s")
                qualifiers = sorted(set(terms(sentence)) & QUALIFIERS)
                schedule = re.findall(r"(?:per|each|every)\s+(?:calendar\s+)?(?:day|week|month|year)", sentence.casefold())
                key = (" ".join(topic), unit, tuple(qualifiers), tuple(schedule))
                groups[key].append({
                    "passage_id": passage["id"], "document": passage["document"], "heading": heading,
                    "locator": passage["locator"], "statement": clean(sentence),
                    "value": float(measure[1]), "unit": unit,
                    "version_hint": next(iter(VERSION.findall(passage["document"])), None),
                })
    found = []
    for items in groups.values():
        if len({row["document"] for row in items}) < 2 or len({row["value"] for row in items}) < 2:
            continue
        identity = sorted((row["document"], row["statement"]) for row in items)
        digest = sha256(repr(identity).encode()).hexdigest()[:16]
        found.append({"id": digest, "type": "numeric_disagreement", "topic": items[0]["heading"],
                      "claims": items, "precedence": None})
    return sorted(found, key=lambda conflict: conflict["id"])


def resolve_conflicts(passages, corpus, conflicts, selections):
    by_passage = defaultdict(list)
    for conflict in conflicts:
        for claim in conflict["claims"]:
            by_passage[claim["passage_id"]].append(conflict)
    resolved = []
    for passage in passages:
        replacements = set()
        for conflict in by_passage.get(passage["id"], []):
            picked = selections.get(conflict["id"])
            ids = {claim["passage_id"] for claim in conflict["claims"]}
            if picked not in ids:
                return [], conflict
            replacements.add(picked)
        if len(replacements) > 1:
            return [], by_passage[passage["id"]][0]
        resolved.append(corpus.by_id[next(iter(replacements))] if replacements else passage)
    return resolved, None
