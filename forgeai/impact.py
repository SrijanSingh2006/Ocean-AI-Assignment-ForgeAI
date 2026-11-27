"""Compare document snapshots and connect changed evidence to measured downstream impact."""

import hashlib
import json
import shutil
import tempfile
from collections import Counter, defaultdict, deque
from pathlib import Path

from .corpus import MAX_FILES, SUPPORTED, Corpus, clean
from .factory import score_agent


def source_files(root):
    """Return recursively supported source files, rejecting links outside the snapshot contract."""
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Source snapshot must be a document directory")
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() and (path.is_dir() or path.suffix.lower() in SUPPORTED):
            raise ValueError("Source snapshots cannot include symbolic links")
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            files[path.relative_to(root).as_posix()] = path
    if len(files) > MAX_FILES:
        raise ValueError(f"Use at most {MAX_FILES} source documents")
    return files


def _hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def fingerprints(root):
    return {name: _hash_file(path) for name, path in source_files(root).items()}


def _identifier(kind, *values):
    data = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode()
    return f"{kind}:{hashlib.sha256(data).hexdigest()[:24]}"


def _load(root, chunk, overlap):
    try:
        return Corpus.load(root, chunk, overlap)
    except ValueError as exc:
        if not str(exc).startswith("No readable passages"):
            raise
        return Corpus([], [], [str(exc)])


def _new_corpus(old, files, changed, chunk, overlap):
    """Parse changed sources and retain unchanged passage text with the new snapshot's locators."""
    changed = sorted(set(changed) & set(files), key=Path)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in changed:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(files[name], path)
        updated = _load(root, chunk, overlap) if changed else Corpus([], [])
    doc_numbers = {name: i for i, name in enumerate(files, 1)}
    reused = set(files) - set(changed)
    passages = [p for p in old.passages if p["document"] in reused] + updated.passages
    for i, p in enumerate(passages):
        passages[i] = {**p, "id": f"d{doc_numbers[p['document']]:02}{p['id'][3:]}"}
    documents = [d for d in old.documents if d["name"] in reused] + updated.documents
    warnings = [w for w in old.warnings if any(w.startswith(name + ":") for name in reused)]
    return Corpus(sorted(passages, key=lambda p: p["id"]),
                  sorted(documents, key=lambda d: Path(d["name"])), warnings + updated.warnings)


def _sections(corpus):
    sections = defaultdict(list)
    for passage in corpus.passages:
        sections[(passage["document"], clean(passage["heading"]).casefold())].append(passage)
    return sections


def _passage_changes(before, after):
    old_pending, new_pending = [], defaultdict(deque)
    for passage in after:
        new_pending[passage["text"]].append(passage)
    for passage in before:
        same = new_pending[passage["text"]]
        if same:
            same.popleft()
        else:
            old_pending.append(passage)
    by_locator = defaultdict(deque)
    for pending in new_pending.values():
        for passage in pending:
            by_locator[passage["locator"]].append(passage)
    changes = []
    for passage in old_pending:
        candidates = by_locator[passage["locator"]]
        replacement = candidates.popleft() if candidates else None
        changes.append((passage, replacement))
    changes.extend((None, p) for pending in by_locator.values() for p in pending)
    return changes


def _relationship_graph(before_sections, after_sections, changes):
    nodes, edges, evidence = {}, [], {}
    for snapshot, sections in (("before", before_sections), ("after", after_sections)):
        for (document, label), passages in sections.items():
            doc_id, section_id = _identifier("document", document), _identifier("section", document, label)
            nodes.setdefault(doc_id, {"id": doc_id, "kind": "document", "label": document})
            nodes.setdefault(section_id, {"id": section_id, "kind": "section", "label": passages[0]["heading"]})
            link = {"source": doc_id, "target": section_id, "relation": "contains"}
            if snapshot == "before" or (document, label) not in before_sections:
                edges.append(link)
            occurrences = Counter()
            for passage in passages:
                value = passage["text"]
                occurrences[value] += 1
                node_id = _identifier("passage", document, label, value, occurrences[value])
                if node_id not in nodes:
                    nodes[node_id] = {"id": node_id, "kind": "passage", "label": passage["locator"],
                                      "document": document, "heading": passage["heading"], "snapshots": []}
                    edges.append({"source": section_id, "target": node_id, "relation": "contains"})
                nodes[node_id]["snapshots"].append(snapshot)
                evidence[(snapshot, document, passage["id"])] = node_id
    for old, new in changes:
        names = []
        for phase, passage in (("before", old), ("after", new)):
            if passage:
                node_id = evidence[(phase, passage["document"], passage["id"])]
                nodes[node_id]["change"] = "modified" if old and new else ("added" if new else "deleted")
                names.append(node_id)
        if len(names) == 2 and names[0] != names[1]:
            edges.append({"source": names[0], "target": names[1], "relation": "changed_at_same_locator"})
    return nodes, edges, evidence


def _old_link(entries, old, evidence, *, quotes=False):
    """Use recorded source references only when the original document and evidence can be verified."""
    sources = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        passage = old.by_id.get(entry.get("passage_id"))
        if not passage or passage["document"] != entry.get("document"):
            continue
        if quotes and entry.get("quote") != passage["text"]:
            continue
        if not quotes and any(
            clean(fact).casefold() not in clean(passage["text"]).casefold() for fact in entry.get("key_facts", [])
        ):
            continue
        sources.append(evidence[("before", passage["document"], passage["id"])])
    return sorted(set(sources))


def analyze_impact(old_documents, new_documents, *, prior_cases=(), prior_answers=(), agent_id=None,
                   definition=None, full_regression=False):
    """Hash inputs, reuse unchanged extraction, and score retained cases on updated sources."""
    old_files, new_files = source_files(old_documents), source_files(new_documents)
    before = {name: _hash_file(path) for name, path in old_files.items()}
    after = {name: _hash_file(path) for name, path in new_files.items()}
    document_changes = []
    for name in sorted(set(before) | set(after)):
        old_hash, new_hash = before.get(name), after.get(name)
        if old_hash != new_hash:
            document_changes.append({"document": name, "kind": "modified" if old_hash and new_hash else
                                     ("added" if new_hash else "deleted"), "before": old_hash, "after": new_hash})
    changed = {row["document"] for row in document_changes}
    retrieval = (definition or {}).get("retrieval", {})
    chunk, overlap = retrieval.get("chunk_words", 135), retrieval.get("overlap_words", 24)
    old = _load(old_documents, chunk, overlap)
    new = _new_corpus(old, new_files, changed, chunk, overlap)
    old_sections, new_sections = _sections(old), _sections(new)
    section_changes, passage_changes = [], []
    for document, label in sorted(set(old_sections) | set(new_sections)):
        section = (document, label)
        old_passages, new_passages = old_sections.get(section, []), new_sections.get(section, [])
        pairs = _passage_changes(old_passages, new_passages)
        if pairs:
            section_changes.append({
                "id": _identifier("section", document, label), "document": document,
                "heading": (new_passages or old_passages)[0]["heading"],
                "kind": "modified" if old_passages and new_passages else ("added" if new_passages else "deleted"),
            })
            passage_changes.extend(pairs)
    nodes, edges, evidence = _relationship_graph(old_sections, new_sections, passage_changes)
    changed_passages = {node["id"] for node in nodes.values() if node.get("change")}
    impacted_cases, cases_by_id = [], {}
    for case in prior_cases:
        node_id = _identifier("case", case["id"])
        cases_by_id[case["id"]] = node_id
        nodes[node_id] = {"id": node_id, "kind": "case", "label": case["id"]}
        sources = _old_link(case.get("expected_grounding", []), old, evidence)
        edges.extend({"source": source, "target": node_id, "relation": "expected_grounding"} for source in sources)
        if changed_passages.intersection(sources):
            impacted_cases.append(case["id"])
    impacted_answers, impacted_agents = [], set()
    for answer in prior_answers:
        answer_id = answer.get("id", answer.get("trace_id"))
        if not isinstance(answer_id, str):
            continue
        node_id = _identifier("answer", answer_id)
        nodes[node_id] = {"id": node_id, "kind": "answer", "label": answer_id}
        response = answer.get("response", answer)
        sources = _old_link(response.get("citations", []), old, evidence, quotes=True)
        edges.extend({"source": source, "target": node_id, "relation": "cited_evidence"} for source in sources)
        case_node = cases_by_id.get(answer.get("case_id"))
        if case_node:
            edges.append({"source": case_node, "target": node_id, "relation": "evaluated_response"})
        if changed_passages.intersection(sources):
            impacted_answers.append(answer_id)
            if answer.get("agent_id"):
                impacted_agents.add(answer["agent_id"])
    if changed and agent_id:
        impacted_agents.add(agent_id)
    results = {
        "fingerprints": {"before": before, "after": after},
        "changes": {
            "documents": document_changes, "sections": section_changes,
            "passages": [node for node in nodes.values() if node["id"] in changed_passages],
        },
        "graph": {"nodes": list(nodes.values()), "edges": edges},
        "impacted_cases": impacted_cases, "impacted_answers": impacted_answers,
        "impacted_agents": sorted(impacted_agents),
        "reindexed_documents": sorted(changed & set(new_files)),
        "reused_documents": sorted(set(new_files) - changed),
        "ingestion_warnings": new.warnings,
    }
    selected = [case for case in prior_cases if case["id"] in impacted_cases]
    if definition and new.passages:
        if selected:
            results["targeted_regression"] = score_agent(definition, new, selected, None, 0)
        if full_regression and prior_cases:
            results["full_regression"] = score_agent(definition, new, prior_cases, None, 0)
    elif (selected or (full_regression and prior_cases)) and definition:
        results["regression_unavailable"] = "Updated snapshot contains no readable passages"
    return results
