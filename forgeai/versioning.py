"""Create immutable, approved releases with separate activation and audit records."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .corpus import MAX_FILE_BYTES, Corpus
from .factory import Agent, read_json, write_json
from .impact import fingerprints, source_files

RELEASE_ARTIFACTS = (
    "definition.json", "initial_definition.json", "requirements.json", "evals.json",
    "eval_results.json", "scorecards.json", "iterations.json", "model_trace.json",
    "tournament.json", "regression.json", "manual_comparison.json", "report.md", "run.json",
    "blind_evals.json", "blind_cases.json", "blind_results.json", "security.json",
    "security_scorecard.json", "multilingual.json", "multilingual_results.json",
    "conflicts.json", "model_tournament.json", "indexed-corpus.json",
)


def _connect(store):
    root = Path(store)
    root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(root / "releases.sqlite3", timeout=10)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """CREATE TABLE IF NOT EXISTS releases (
            agent TEXT NOT NULL, id TEXT NOT NULL, number INTEGER NOT NULL,
            state TEXT NOT NULL, metadata TEXT NOT NULL, PRIMARY KEY (agent, id), UNIQUE (agent, number)
        );
        CREATE TABLE IF NOT EXISTS active (
            agent TEXT PRIMARY KEY, release_id TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS release_events (
            seq INTEGER PRIMARY KEY, agent TEXT NOT NULL, release_id TEXT NOT NULL,
            action TEXT NOT NULL, actor TEXT NOT NULL, event_time TEXT NOT NULL, previous_id TEXT
        );"""
    )
    return connection


def _time():
    return datetime.now(timezone.utc).isoformat()


def _agent_id(agent):
    if not isinstance(agent, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", agent):
        raise ValueError("Invalid agent ID")
    return agent


def _actor(actor):
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 128:
        raise ValueError("Invalid release actor")
    return actor.strip()


def _lookup(db, agent, version):
    if not isinstance(version, str) or not re.fullmatch(r"[a-f0-9]{32}", version):
        raise LookupError("Release not found")
    row = db.execute("SELECT * FROM releases WHERE agent = ? AND id = ?", (agent, version)).fetchone()
    if row is None:
        raise LookupError("Release not found")
    return row


def _active(db, agent):
    row = db.execute("SELECT release_id FROM active WHERE agent = ?", (agent,)).fetchone()
    return row["release_id"] if row else None


def _event(db, agent, version, action, actor, previous=None):
    db.execute(
        "INSERT INTO release_events (agent, release_id, action, actor, event_time, previous_id) "
        "VALUES (?, ?, ?, ?, ?, ?)", (agent, version, action, actor, _time(), previous),
    )


def _summary(row, active):
    return {**json.loads(row["metadata"]), "state": row["state"], "active": row["id"] == active}


def _artifact_fingerprints(folder):
    values = {}
    for name in RELEASE_ARTIFACTS:
        path = folder / name
        if path.is_symlink():
            raise ValueError("Release artifacts cannot contain symbolic links")
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            values[name] = digest.hexdigest()
    return values


def _export_metadata(folder, definition):
    run_path = folder / "run.json"
    run = read_json(run_path) if run_path.is_file() else {}
    model = run.get("model") or {}
    score = run.get("scorecard")
    scorecards = folder / "scorecards.json"
    if not score and scorecards.is_file():
        score = read_json(scorecards).get("final")

    def report(keys, files):
        for key in keys:
            if run.get(key) is not None:
                return run[key]
        for name in files:
            path = folder / name
            if path.is_file():
                return read_json(path)
        return None

    return {
        "name": definition.get("name"),
        "model": {key: model[key] for key in ("name", "mode", "budget", "tokens") if key in model},
        "retrieval": definition["retrieval"], "tools": definition["tools"],
        "evaluation": score,
        "security": report(("security", "security_scorecard"), ("security.json", "security_scorecard.json")),
        "multilingual": report(("multilingual", "multilingual_results", "languages"),
                               ("multilingual.json", "multilingual_results.json")),
    }


def create_release(store, agent_id, artifacts, documents, *, actor="local"):
    """Copy the definition, source files and measured artifacts into a new pending release."""
    agent, actor = _agent_id(agent_id), _actor(actor)
    artifacts = Path(artifacts)
    documents = source_files(documents)
    if not artifacts.is_dir() or artifacts.is_symlink() or not documents:
        raise ValueError("A completed agent and its source documents are required")
    parent = Path(store) / "snapshots" / agent
    parent.mkdir(parents=True, exist_ok=True)
    version = uuid.uuid4().hex
    destination = parent / version
    with tempfile.TemporaryDirectory(dir=parent) as directory:
        stage = Path(directory) / "snapshot"
        staged_artifacts, staged_documents = stage / "artifacts", stage / "documents"
        staged_artifacts.mkdir(parents=True)
        staged_documents.mkdir()
        for name in _artifact_fingerprints(artifacts):
            shutil.copyfile(artifacts / name, staged_artifacts / name)
        definition_path = staged_artifacts / "definition.json"
        if not definition_path.exists():
            raise ValueError("A completed agent definition is required")
        definition = read_json(definition_path)
        for name, source in documents.items():
            if source.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("Release document exceeds the file size limit")
            target = staged_documents / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        retrieval = definition["retrieval"]
        corpus = Corpus.load(staged_documents, retrieval["chunk_words"], retrieval["overlap_words"])
        Agent(definition, corpus)
        write_json(staged_artifacts / "indexed-corpus.json", {
            "passages": corpus.passages, "documents": corpus.documents, "warnings": corpus.warnings,
        })
        metadata = {
            "id": version, "agent_id": agent, "created": _time(), "created_by": actor,
            "sources": fingerprints(staged_documents), "artifacts": _artifact_fingerprints(staged_artifacts),
            **_export_metadata(staged_artifacts, definition),
        }
        try:
            with closing(_connect(store)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                number = db.execute("SELECT COALESCE(MAX(number), 0) + 1 AS n FROM releases WHERE agent = ?",
                                    (agent,)).fetchone()["n"]
                metadata["number"] = number
                os.replace(stage, destination)
                db.execute("INSERT INTO releases VALUES (?, ?, ?, 'pending', ?)",
                           (agent, version, number, json.dumps(metadata, ensure_ascii=False)))
                _event(db, agent, version, "created", actor)
        except Exception:
            if destination.exists():
                shutil.rmtree(destination)
            raise
    return {**metadata, "state": "pending", "active": False}


def list_releases(store, agent_id):
    agent = _agent_id(agent_id)
    with closing(_connect(store)) as db:
        active = _active(db, agent)
        rows = db.execute("SELECT * FROM releases WHERE agent = ? ORDER BY number DESC", (agent,)).fetchall()
        return [_summary(row, active) for row in rows]


def release_history(store, agent_id):
    agent = _agent_id(agent_id)
    with closing(_connect(store)) as db:
        rows = db.execute(
            "SELECT release_id, action, actor, event_time, previous_id FROM release_events "
            "WHERE agent = ? ORDER BY seq", (agent,),
        )
        return [dict(row) for row in rows]


def _paths(store, agent, row):
    root = Path(store) / "snapshots" / agent / row["id"]
    artifacts, documents = root / "artifacts", root / "documents"
    metadata = json.loads(row["metadata"])
    if not artifacts.is_dir() or not documents.is_dir() or root.is_symlink() or artifacts.is_symlink():
        raise ValueError("Release snapshot is unavailable")
    if _artifact_fingerprints(artifacts) != metadata["artifacts"] or fingerprints(documents) != metadata["sources"]:
        raise ValueError("Release snapshot integrity check failed")
    return artifacts, documents


def approve_release(store, agent_id, version_id, *, actor="local"):
    agent, actor = _agent_id(agent_id), _actor(actor)
    with closing(_connect(store)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = _lookup(db, agent, version_id)
        if row["state"] != "pending":
            raise ValueError("Only a pending release can be approved")
        _paths(store, agent, row)
        metadata = json.loads(row["metadata"])
        metadata.update(approved=_time(), approved_by=actor)
        db.execute("UPDATE releases SET state = 'approved', metadata = ? WHERE agent = ? AND id = ?",
                   (json.dumps(metadata, ensure_ascii=False), agent, version_id))
        _event(db, agent, version_id, "approved", actor)
        return {**metadata, "state": "approved", "active": False}


def _select_release(store, agent, version, actor, operation):
    with closing(_connect(store)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row, previous = _lookup(db, agent, version), _active(db, agent)
        if row["state"] != "approved":
            raise ValueError("Only an approved release can become active")
        if operation == "rollback":
            if previous is None or row["number"] >= _lookup(db, agent, previous)["number"]:
                raise ValueError("Rollback requires an earlier approved release")
        _paths(store, agent, row)
        db.execute("INSERT INTO active VALUES (?, ?) ON CONFLICT(agent) DO UPDATE SET release_id=excluded.release_id",
                   (agent, version))
        _event(db, agent, version, operation, actor, previous)
        return _summary(row, version)


def activate_release(store, agent_id, version_id, *, actor="local"):
    return _select_release(store, _agent_id(agent_id), version_id, _actor(actor), "activated")


def rollback_release(store, agent_id, version_id, *, actor="local"):
    return _select_release(store, _agent_id(agent_id), version_id, _actor(actor), "rollback")


def release_paths(store, agent_id, version_id=None):
    """Resolve and verify the definition and source snapshot for an explicit or active release."""
    agent = _agent_id(agent_id)
    with closing(_connect(store)) as db:
        row = _lookup(db, agent, version_id if version_id is not None else _active(db, agent))
    return _paths(store, agent, row)


def load_snapshot_corpus(artifacts, documents, definition):
    """Use an extracted index from an already-verified release or parse ordinary run sources."""
    index = Path(artifacts) / "indexed-corpus.json"
    if index.is_symlink():
        raise ValueError("Release indexes cannot contain symbolic links")
    if index.is_file():
        frozen = read_json(index)
        return Corpus(frozen["passages"], frozen["documents"], frozen["warnings"])
    retrieval = definition["retrieval"]
    return Corpus.load(documents, retrieval["chunk_words"], retrieval["overlap_words"])


def compare_releases(store, agent_id, before_id, after_id):
    agent = _agent_id(agent_id)
    with closing(_connect(store)) as db:
        active = _active(db, agent)
        before, after = _lookup(db, agent, before_id), _lookup(db, agent, after_id)
    left, right = _summary(before, active), _summary(after, active)
    left_definition = read_json(_paths(store, agent, before)[0] / "definition.json")
    right_definition = read_json(_paths(store, agent, after)[0] / "definition.json")
    changes = [key for key in sorted(left_definition.keys() | right_definition.keys())
               if left_definition.get(key) != right_definition.get(key)]
    old, new = left["sources"], right["sources"]
    return {
        "before": left, "after": right, "changed_fields": changes,
        "sources": {
            "added": sorted(new.keys() - old.keys()),
            "deleted": sorted(old.keys() - new.keys()),
            "modified": sorted(name for name in old.keys() & new.keys() if old[name] != new[name]),
        },
        "score_before": left["evaluation"], "score_after": right["evaluation"],
    }
