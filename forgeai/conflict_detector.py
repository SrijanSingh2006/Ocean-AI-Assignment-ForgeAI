"""Compare documented policy claims while keeping their scope and provenance."""

from collections import defaultdict
from datetime import datetime
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


EFFECTIVE_DATE = re.compile(
    r"\b(effective(?:\s+(?:on|from))?|takes effect(?:\s+on)?|expires?(?:\s+on)?|ends?(?:\s+on)?)"
    r"\s+(\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})\b",
    re.I,
)
MODAL = re.compile(
    r"\b(must not|may not|cannot|can[’']t|(?:is|are) not (?:allowed|permitted) to|"
    r"(?:is|are) prohibited from|(?:is|are) (?:allowed|permitted) to|"
    r"(?:is|are) required to|must|may|can)\b", re.I,
)
CONDITION = re.compile(r"\b(only if|unless|when|if|except|provided that)\b", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
EQUIVALENTS = {"staff": "employee", "employees": "employee", "remotely": "remote", "working": "work",
               "submit": "file", "submitting": "file", "vendor": "supplier"}


def policy_words(text):
    normalized = re.sub(r"\b[a-z]+\b", lambda match: EQUIVALENTS.get(match[0], match[0]), text.lower())
    return tuple(sorted(set(terms(normalized))))


def calendar_date(value):
    for pattern in ("%Y-%m-%d", "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value.replace(",", ""), pattern).date().isoformat()
        except ValueError:
            continue
    return None


def policy_claims(passage):
    topic = policy_words(passage["heading"])
    if not topic:
        return
    for sentence in SENTENCE.split(passage["text"]):
        condition = CONDITION.search(sentence)
        scoped = policy_words(sentence[condition.start():]) if condition else ()
        before_condition = sentence[:condition.start()] if condition else sentence
        if effective := EFFECTIVE_DATE.search(before_condition):
            verb, raw = effective.groups()
            day = calendar_date(raw)
            if day and passage["heading"] != passage["title"]:
                scope = policy_words(before_condition[:effective.start()])
                kind = "expiration_date" if verb.lower().startswith(("end", "expir")) else "effective_date"
                yield (kind, topic, scope, scoped), day, "date", sentence
            continue
        if modal := MODAL.search(before_condition):
            subject = policy_words(before_condition[:modal.start()])
            action = policy_words(before_condition[modal.end():])
            if not subject or not action:
                continue
            word = modal[0].casefold().replace("’", "'")
            negative = " not" in word or word in {"cannot", "can't"} or "prohibited" in word
            kind = "conditional_policy" if condition else "permission"
            yield (kind, topic, subject, action, scoped), "prohibited" if negative else "permitted", "rule", sentence


def document_conflicts(corpus):
    groups = defaultdict(list)
    for passage in corpus.passages:
        for key, value, unit, sentence in policy_claims(passage):
            groups[key].append({
                "passage_id": passage["id"], "document": passage["document"],
                "heading": passage["heading"], "locator": passage["locator"], "statement": clean(sentence),
                "value": value, "unit": unit,
                "version_hint": next(iter(VERSION.findall(passage["document"])), None),
            })
    found = numeric_conflicts(corpus)
    for key, claims in groups.items():
        if len({row["document"] for row in claims}) < 2 or len({row["value"] for row in claims}) < 2:
            continue
        kind = key[0]
        identity = sorted((row["document"], row["statement"]) for row in claims)
        digest = sha256(repr((kind, identity)).encode()).hexdigest()[:16]
        found.append({"id": digest, "type": kind, "topic": claims[0]["heading"], "claims": claims,
                      "precedence": None, "severity": "review_required",
                      "basis": "Comparable normalized topic, subject and scope with different documented outcomes"})
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
