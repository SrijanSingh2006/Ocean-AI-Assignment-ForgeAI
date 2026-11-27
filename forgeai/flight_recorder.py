"""Redacted runtime events. No model prompts or private reasoning are recorded."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

IDENTIFIER = re.compile(r"[0-9a-f]{32}")
PII = (
    ("email", re.compile(r"\b[\w.%+-]+@[\w.-]+\.[a-z]{2,}\b", re.I)),
    ("national_id", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\w)")),
    ("credential", re.compile(r"\b(?:bearer\s+|(?:password|api[-_ ]?key|token)\s*[:=]\s*)[A-Za-z0-9_.+/=-]{6,}", re.I)),
)


def pii_categories(text):
    return [label for label, pattern in PII if pattern.search(text)]


def redact(value):
    if isinstance(value, str):
        for label, pattern in PII:
            value = pattern.sub(f"[redacted {label}]", value)
        return value
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


class FlightRecorder:
    def __init__(self, question, actor="local"):
        self.id = uuid4().hex
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.question = redact(question)
        self.actor = actor
        self.events = []
        self.previous = time.monotonic()

    def event(self, stage, **details):
        now = time.monotonic()
        self.events.append({"stage": stage, "elapsed_ms": round((now - self.previous) * 1000, 2), **redact(details)})
        self.previous = now

    def finish(self, response):
        citation_refs = [
            {key: citation[key] for key in ("passage_id", "document", "heading", "locator")}
            for citation in response["citations"]
        ]
        self.event("decision", status=response["status"], tool=response.get("tool"),
                   confidence=response.get("confidence"), citations=citation_refs)
        return {"id": self.id, "at": self.started_at, "actor": self.actor, "question": self.question,
                "status": response["status"], "answer": redact(response["answer"]), "events": self.events}


def trace_path(folder, identifier):
    if not IDENTIFIER.fullmatch(identifier):
        raise ValueError("Invalid trace ID.")
    return Path(folder) / f"{identifier}.json"


def trace_retention():
    days = int(os.getenv("FORGE_TRACE_RETENTION_DAYS", "30"))
    if not 1 <= days <= 365:
        raise ValueError("Invalid trace retention window.")
    return days


def cutoff_time(retention_days):
    return time.time() - timedelta(days=retention_days).total_seconds()


def read_trace(folder, identifier, retention_days=30):
    path = trace_path(folder, identifier)
    if path.stat().st_mtime < cutoff_time(retention_days):
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def store_trace(folder, record, retention_days=30):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cutoff = cutoff_time(retention_days)
    for path in folder.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
    target = trace_path(folder, record["id"])
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def list_traces(folder, limit=100, retention_days=30):
    cutoff = cutoff_time(retention_days)
    dated = []
    for path in Path(folder).glob("*.json"):
        try:
            modified = path.stat().st_mtime
        except FileNotFoundError:
            continue
        if modified >= cutoff:
            dated.append((modified, path))
    rows = []
    for _, path in sorted(dated, reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        rows.append({key: record[key] for key in ("id", "at", "actor", "question", "status")})
        if len(rows) >= limit:
            break
    return rows
