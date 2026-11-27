"""Persist feedback and promote reviewed source facts to repeatable evaluation cases."""

import copy
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .corpus import Index, clean, terms
from .factory import Agent, PATCHES, PATCH_ORDER, blocked, fact_for, judge, score_agent

CATEGORIES = {
    "helpful", "incorrect_answer", "missing_information", "wrong_citation",
    "incorrect_refusal", "inappropriate_response",
}
STATES = {"pending", "approved", "rejected"}
SUITES = {"development", "regression"}


def _connect(store):
    root = Path(store)
    root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(root / "feedback.sqlite3", timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL, created TEXT NOT NULL,
            state TEXT NOT NULL, suite TEXT, payload TEXT NOT NULL
        )"""
    )
    return connection


def _time():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field, limit, required=True):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError(f"{field} must be text of at most {limit} characters")
    return value.strip()


def _response(value):
    if not isinstance(value, dict) or value.get("status") not in {"answered", "refused", "clarify", "error"}:
        raise ValueError("A recorded agent response is required")
    citations = value.get("citations")
    if not isinstance(citations, list) or len(citations) > 20:
        raise ValueError("Invalid recorded citations")
    keys = ("passage_id", "document", "locator", "heading", "quote")
    if any(not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) for key in keys)
           for entry in citations):
        raise ValueError("Invalid recorded citations")
    return {
        "status": value["status"],
        "answer": _text(value.get("answer"), "Recorded answer", 100_000, required=False),
        "tool": value.get("tool") if isinstance(value.get("tool"), str) else None,
        "citations": [{key: entry[key] for key in keys} for entry in citations],
    }


def submit_feedback(store, *, run_id, question, response, category, comment="", agent_version=None, actor="local"):
    """Store feedback on an actual response supplied by an authorized server caller."""
    category = _text(category, "Category", 50).casefold().replace(" ", "_").replace("-", "_")
    if category not in CATEGORIES:
        raise ValueError("Unknown feedback category")
    entry = {
        "id": uuid.uuid4().hex, "run_id": _text(run_id, "Run ID", 128),
        "question": _text(question, "Question", 2000), "response": _response(response),
        "category": category, "comment": _text(comment, "Feedback comment", 2000, required=False),
        "agent_version": _text(agent_version, "Agent version", 128) if agent_version is not None else None,
        "actor": _text(actor, "Actor", 128), "created": _time(), "state": "pending",
    }
    with closing(_connect(store)) as db, db:
        db.execute(
            "INSERT INTO feedback (id, run_id, created, state, suite, payload) VALUES (?, ?, ?, ?, NULL, ?)",
            (entry["id"], entry["run_id"], entry["created"], entry["state"], json.dumps(entry, ensure_ascii=False)),
        )
    return entry


def list_feedback(store, *, run_id=None, state=None):
    if state is not None and state not in STATES:
        raise ValueError("Unknown feedback state")
    with closing(_connect(store)) as db:
        rows = db.execute(
            "SELECT payload FROM feedback WHERE (? IS NULL OR run_id = ?) AND (? IS NULL OR state = ?) "
            "ORDER BY created DESC, id DESC", (run_id, run_id, state, state),
        )
        return [json.loads(row["payload"]) for row in rows]


def _candidate(entry, corpus, definition, expected_status, anchors):
    if expected_status not in {"answered", "refused", "clarify"}:
        raise ValueError("The reviewer must supply an expected decision")
    question = entry["question"]
    if not isinstance(anchors, (list, tuple)) or len(anchors) > 8:
        raise ValueError("Supply at most eight evidence anchors")
    index = Index(corpus)
    denied = blocked(question, definition["denied_topics"])
    if expected_status == "answered":
        if denied or not anchors:
            raise ValueError("An answered case must have evidence and fall within the agent scope")
    elif anchors:
        raise ValueError("A refusal or clarification case cannot prescribe an answer citation")
    elif expected_status == "clarify" and len(set(terms(question))) > 1:
        raise ValueError("A clarification case must have an ambiguous topic")
    elif expected_status == "refused" and not denied and any(
        coverage >= 0.58 for _, coverage, _ in index.search(question, 4)
    ):
        raise ValueError("This question has strong source coverage, so a refusal needs a scope exclusion")

    grounding = []
    seen = set()
    for anchor in anchors:
        if isinstance(anchor, str):
            anchor = {"passage_id": anchor}
        if not isinstance(anchor, dict):
            raise ValueError("Invalid evidence anchor")
        key = _text(anchor.get("passage_id"), "Passage ID", 128)
        passage = corpus.by_id.get(key)
        if not passage or key in seen or not index.search(question, 1, {key}):
            raise ValueError("Each citation must identify a distinct source passage relevant to the question")
        facts = anchor.get("key_facts", fact_for(passage))
        if not isinstance(facts, (list, tuple)) or not 1 <= len(facts) <= 8:
            raise ValueError("Each citation needs one to eight source facts")
        facts = [clean(_text(fact, "Source fact", 3000)) for fact in facts]
        normalized = clean(passage["text"]).casefold()
        if any(len(fact) < 3 or fact.casefold() not in normalized or fact.casefold() in clean(question).casefold()
               for fact in facts):
            raise ValueError("Expected facts must be present in the source and absent from the question")
        grounding.append({"document": passage["document"], "passage_id": key, "key_facts": facts})
        seen.add(key)
    return {
        "id": "F-" + entry["id"], "category": "reviewed_feedback", "question": question,
        "expected_status": expected_status, "expected_grounding": grounding,
    }


def _repair(case, current, corpus, definition, prior_cases):
    for key in PATCH_ORDER.get(current["failure"], ()):
        section, changes, rationale = PATCHES[key]
        if all(definition[section].get(name) == value for name, value in changes.items()):
            continue
        candidate = copy.deepcopy(definition)
        candidate[section].update(changes)
        new_result = judge(case, Agent(candidate, corpus, permit_network=False).answer(case["question"]), corpus)
        if not new_result["passed"]:
            continue
        baseline = score_agent(definition, corpus, prior_cases, None, 0) if prior_cases else None
        regression = score_agent(candidate, corpus, prior_cases, None, 0) if prior_cases else None
        newly_failing = []
        if baseline:
            passed_before = {row["id"] for row in baseline["results"] if row["passed"]}
            newly_failing = [row["id"] for row in regression["results"] if row["id"] in passed_before and not row["passed"]]
        return {
            "patch": key, "section": section, "changes": changes, "reason": rationale,
            "feedback_result": new_result, "regression_before": baseline, "regression_after": regression,
            "newly_failing": newly_failing, "passes_regression_gate": bool(baseline) and not newly_failing,
        }
    return None


def review_feedback(store, feedback_id, *, approve, reviewer, corpus=None, definition=None,
                    expected_status=None, anchors=None, suite="regression", prior_cases=()):
    """Approve a grounded expected outcome, score it, and test a possible repair without activating it."""
    reviewer = _text(reviewer, "Reviewer", 128)
    with closing(_connect(store)) as db:
        row = db.execute("SELECT payload FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    if row is None:
        raise LookupError("Feedback entry not found")
    entry = json.loads(row["payload"])
    if entry["state"] != "pending":
        raise ValueError("Feedback already reviewed")
    entry.update(state="approved" if approve else "rejected", reviewer=reviewer, reviewed=_time())
    if approve:
        if corpus is None or definition is None or suite not in SUITES:
            raise ValueError("Approval requires a current corpus, definition, and valid evaluation suite")
        case = _candidate(entry, corpus, definition, expected_status, [] if anchors is None else anchors)
        result = judge(case, Agent(definition, corpus, permit_network=False).answer(case["question"]), corpus)
        entry.update(suite=suite, case=case, evaluation=result,
                     suggested_repair=_repair(case, result, corpus, definition, prior_cases))
    with closing(_connect(store)) as db, db:
        updated = db.execute(
            "UPDATE feedback SET state = ?, suite = ?, payload = ? WHERE id = ? AND state = 'pending'",
            (entry["state"], entry.get("suite"), json.dumps(entry, ensure_ascii=False), feedback_id),
        )
        if updated.rowcount != 1:
            raise ValueError("Feedback already reviewed")
    return entry


def approved_cases(store, run_id, *, suite="regression"):
    if suite not in SUITES:
        raise ValueError("Unknown evaluation suite")
    with closing(_connect(store)) as db:
        rows = db.execute(
            "SELECT payload FROM feedback WHERE run_id = ? AND state = 'approved' AND suite = ? ORDER BY created, id",
            (run_id, suite),
        )
        return [json.loads(row["payload"])["case"] for row in rows]
