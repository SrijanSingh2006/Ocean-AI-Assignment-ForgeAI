"""Authorized workflow routes for features that operate on completed runs."""

from contextlib import contextmanager
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import deployment, feedback, versioning, web
from .confidence import calibration_report
from .conflict_detector import document_conflicts
from .embeddings import configured_embeddings
from .factory import Agent, judge, read_json, write_json
from .flight_recorder import list_traces, read_trace as read_trace_file, redact, trace_path, trace_retention
from .impact import analyze_impact
from .model import LocalModel
from .model_tournament import compare_languages, compare_models, configured_profiles
from .multilingual import language_model
from .security import conformance_scorecard

router = APIRouter(prefix="/api")


class ConflictResolution(BaseModel):
    passage_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=500)


class FeedbackSubmission(BaseModel):
    trace_id: str = Field(min_length=32, max_length=32)
    category: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=1000)


class FeedbackReview(BaseModel):
    approve: bool
    expected_status: Literal["answered", "refused", "clarify"] | None = None
    anchors: list = Field(default_factory=list, max_length=20)
    suite: Literal["development", "regression"] = "regression"


class ImpactRequest(BaseModel):
    previous_run_id: str = Field(min_length=1, max_length=64)
    full_regression: bool = False


class ReleaseRequest(BaseModel):
    source_run_id: str | None = None
    label: str | None = Field(default=None, min_length=1, max_length=80)


class ModelComparison(BaseModel):
    minimum_score: float = Field(default=80, ge=0, le=100)


class CalibrationRequest(BaseModel):
    training: list[dict] = Field(min_length=1, max_length=1000)
    validation: list[dict] = Field(min_length=1, max_length=1000)


def feature_folder(request, run_id):
    principal = web.require_run(request, run_id)
    return web.RUNS / ".enterprise" / principal.workspace / run_id


def active_paths(request, run_id, version_id=None):
    store = feature_folder(request, run_id)
    releases = versioning.list_releases(store, run_id)
    version = version_id or next((row["id"] for row in releases if row["active"]), None)
    if version:
        try:
            artifacts, documents = versioning.release_paths(store, run_id, version)
        except (LookupError, ValueError) as exc:
            raise HTTPException(409, "The requested release snapshot is unavailable.") from exc
    else:
        artifacts, documents = web.completed(run_id)
    if not request.state.principal.allows_documents(web.source_names(documents)):
        raise HTTPException(404, "Run not found")
    return artifacts, documents, version


def optional_json(path, default):
    return read_json(path) if path.is_file() else default


def conflict_state(request, run_id):
    return feature_folder(request, run_id) / "conflict-resolutions.json"


@contextmanager
def snapshot_artifacts(request, run_id, artifacts, version):
    if version:
        yield artifacts
        return
    store = feature_folder(request, run_id)
    resolutions = optional_json(conflict_state(request, run_id), {"selections": {}})["selections"]
    attachments = {
        filename: store / filename for filename in ("security.json", "multilingual_results.json", "model_tournament.json")
        if (store / filename).is_file()
    }
    if not resolutions and not attachments:
        yield artifacts
        return
    with TemporaryDirectory() as temporary:
        folder = Path(temporary)
        for name in versioning.RELEASE_ARTIFACTS:
            source = artifacts / name
            if source.is_file():
                shutil.copyfile(source, folder / name)
        for name, source in attachments.items():
            shutil.copyfile(source, folder / name)
        if resolutions:
            path = folder / "definition.json"
            definition = read_json(path)
            definition["conflict_resolutions"] = resolutions
            write_json(path, definition)
        yield folder


def runtime(request, run_id, *, version_id=None, use_model=True):
    artifacts, documents, version = active_paths(request, run_id, version_id)
    definition = read_json(artifacts / "definition.json")
    corpus = versioning.load_snapshot_corpus(artifacts, documents, definition)
    resolved = optional_json(conflict_state(request, run_id), {"selections": {}, "history": []})
    translator = language_model()
    agent = Agent(definition, corpus, LocalModel() if use_model else None, use_model,
                  resolutions=None if version else resolved["selections"], translator=translator, embeddings=configured_embeddings() if use_model else None)
    return artifacts, agent, version, translator


def save_result(request, run_id, name, data):
    folder = feature_folder(request, run_id)
    folder.mkdir(parents=True, exist_ok=True)
    with web.LOCK:
        write_json(folder / name, data)
    return data


def operation_error(exc):
    return HTTPException(400 if isinstance(exc, ValueError) else 404, str(exc))


@router.get("/dashboard")
def dashboard(request: Request):
    runs = web.runs(request)
    completed_runs = [row for row in runs if not row["demo"] and row["status"] == "complete"]
    details = [read_json(web.completed(row["id"])[0] / "run.json") for row in completed_runs]
    results = [case for result in details for case in result["results"]]
    security = [result["security"] for result in details if result.get("security")]
    pending = []
    for row in completed_runs:
        pending.extend(feedback.list_feedback(feature_folder(request, row["id"]), run_id=row["id"], state="pending"))
    return {
        "generated_agents": len(completed_runs), "recorded_samples": sum(row["demo"] for row in runs),
        "evaluation_cases": len(results),
        "average_score": round(sum(r["scorecard"]["score"] for r in details) / len(details), 1) if details else None,
        "grounding_rate": round(sum(row["checks"]["grounded"] for row in results) / len(results), 3) if results else None,
        "security_checks": sum(row["total"] for row in security),
        "regression_failures": sum(len(r.get("regression", {}).get("changes", {}).get("lost", [])) for r in details),
        "pending_approvals": sum(r["status"] == "approval" for r in runs), "pending_feedback": len(pending),
        "recent": [row for row in runs if not row["demo"]][:10],
        "recent_failures": [{"case": row["id"], "failure": row["failure"]} for row in results if not row["passed"]][:10],
    }


@router.get("/runs/{run_id}/conflicts")
def conflicts(run_id: str, request: Request):
    _, agent, version, _ = runtime(request, run_id, use_model=False)
    state = optional_json(conflict_state(request, run_id), {"selections": {}, "history": []})
    if version:
        state["selections"] = agent.resolutions
    return {"conflicts": document_conflicts(agent.corpus), "active_version": version, **state}


@router.post("/runs/{run_id}/conflicts/{conflict_id}")
def resolve(run_id: str, conflict_id: str, review: ConflictResolution, request: Request):
    payload = conflicts(run_id, request)
    if payload["active_version"]:
        raise HTTPException(409, "This release is frozen. Resolve source conflicts in a new build.")
    conflict = next((item for item in payload["conflicts"] if item["id"] == conflict_id), None)
    if not conflict or review.passage_id not in {claim["passage_id"] for claim in conflict["claims"]}:
        raise HTTPException(422, "Choose a passage from this conflict.")
    with web.LOCK:
        state = optional_json(conflict_state(request, run_id), {"selections": {}, "history": []})
        previous = state["selections"].get(conflict_id)
        state["selections"][conflict_id] = review.passage_id
        state["history"].append({"conflict_id": conflict_id, "previous": previous, "passage_id": review.passage_id,
                                 "reason": redact(review.reason), "actor": request.state.principal.name, "at": web.now()})
        _, active, _, _ = runtime(request, run_id, use_model=False)
        claim = next(item for item in conflict["claims"] if item["passage_id"] == review.passage_id)
        case = {
            "id": f"C-{conflict_id}", "category": "conflict_resolution",
            "question": f"What does the policy say about {conflict['topic']}?", "expected_status": "answered",
            "expected_grounding": [{"document": claim["document"], "passage_id": claim["passage_id"],
                                    "key_facts": [claim["statement"]]}],
        }
        checker = Agent(active.definition, active.corpus, permit_network=False, resolutions=state["selections"])
        result = judge(case, checker.answer(case["question"]), active.corpus)
        state.setdefault("regression_cases", {})[conflict_id] = {"case": case, "verified": result["passed"]}
        return save_result(request, run_id, "conflict-resolutions.json", state)


@router.get("/runs/{run_id}/traces")
def traces(run_id: str, request: Request):
    try:
        retention_days = trace_retention()
    except ValueError as exc:
        raise HTTPException(503, "Trace retention settings are invalid.") from exc
    return list_traces(feature_folder(request, run_id) / "traces", retention_days=retention_days)


def read_trace(request, run_id, trace_id):
    try:
        return read_trace_file(feature_folder(request, run_id) / "traces", trace_id, trace_retention())
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(404, "Trace not found") from exc


@router.get("/runs/{run_id}/traces/{trace_id}")
def trace(run_id: str, trace_id: str, request: Request):
    return read_trace(request, run_id, trace_id)


@router.delete("/runs/{run_id}/traces/{trace_id}")
def delete_trace(run_id: str, trace_id: str, request: Request):
    read_trace(request, run_id, trace_id)
    trace_path(feature_folder(request, run_id) / "traces", trace_id).unlink(missing_ok=True)
    return {"deleted": True}


@router.get("/runs/{run_id}/security")
def security(run_id: str, request: Request):
    artifacts, _, _ = active_paths(request, run_id)
    default = optional_json(artifacts / "security.json", {"status": "not_run"})
    return optional_json(feature_folder(request, run_id) / "security.json", default)


@router.post("/runs/{run_id}/security")
def check_security(run_id: str, request: Request):
    _, agent, _, _ = runtime(request, run_id, use_model=False)
    return save_result(request, run_id, "security.json", conformance_scorecard(agent))


@router.get("/runs/{run_id}/models")
def models(run_id: str, request: Request):
    return optional_json(feature_folder(request, run_id) / "model_tournament.json", {"status": "not_run"})


@router.post("/runs/{run_id}/models")
def benchmark_models(run_id: str, selection: ModelComparison, request: Request):
    artifacts, agent, _, _ = runtime(request, run_id, use_model=False)
    try:
        profiles = configured_profiles()
    except ValueError as exc:
        raise operation_error(exc) from exc
    if not profiles:
        profiles = [{"id": "local", "url": LocalModel().url, "model": LocalModel().name}]
    result = compare_models(agent.definition, agent.corpus, read_json(artifacts / "evals.json"), profiles,
                            minimum_score=selection.minimum_score)
    return save_result(request, run_id, "model_tournament.json", result)


@router.get("/runs/{run_id}/languages")
def languages(run_id: str, request: Request):
    return optional_json(feature_folder(request, run_id) / "multilingual_results.json", {"status": "not_run"})


@router.post("/runs/{run_id}/languages")
def benchmark_languages(run_id: str, request: Request):
    artifacts, agent, _, translator = runtime(request, run_id, use_model=False)
    return save_result(request, run_id, "multilingual_results.json", compare_languages(agent, read_json(artifacts / "evals.json"), translator))


@router.post("/confidence/calibration")
def calibrate(request_data: CalibrationRequest):
    try:
        return calibration_report(request_data.training, request_data.validation)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "Provide disjoint labeled rows with id, score, correct, and status.") from exc


@router.get("/runs/{run_id}/feedback")
def feedback_queue(run_id: str, request: Request):
    return feedback.list_feedback(feature_folder(request, run_id), run_id=run_id)


@router.post("/runs/{run_id}/feedback")
def submit_feedback(run_id: str, payload: FeedbackSubmission, request: Request):
    record = read_trace(request, run_id, payload.trace_id)
    principal = request.state.principal
    if record["actor"] != principal.name:
        raise HTTPException(404, "Trace not found")
    _, agent, version, _ = runtime(request, run_id, version_id=record.get("agent_version"), use_model=False)
    decision = record["events"][-1]
    citations = [{**citation, "quote": redact(agent.corpus.by_id[citation["passage_id"]]["text"])}
                 for citation in decision["citations"] if citation["passage_id"] in agent.corpus.by_id]
    response = {"answer": record["answer"], "status": record["status"], "tool": decision["tool"], "citations": citations}
    try:
        return feedback.submit_feedback(feature_folder(request, run_id), run_id=run_id, question=record["question"],
                                        response=response, category=payload.category, comment=redact(payload.comment),
                                        agent_version=version, actor=principal.name)
    except (ValueError, LookupError) as exc:
        raise operation_error(exc) from exc


@router.post("/runs/{run_id}/feedback/{feedback_id}/review")
def review_feedback(run_id: str, feedback_id: str, payload: FeedbackReview, request: Request):
    artifacts, agent, _, _ = runtime(request, run_id, use_model=False)
    try:
        return feedback.review_feedback(
            feature_folder(request, run_id), feedback_id, approve=payload.approve, reviewer=request.state.principal.name,
            corpus=agent.corpus, definition=agent.definition, expected_status=payload.expected_status, anchors=payload.anchors,
            suite=payload.suite, prior_cases=read_json(artifacts / "evals.json"),
        )
    except (ValueError, LookupError) as exc:
        raise operation_error(exc) from exc


@router.get("/runs/{run_id}/impact")
def impact(run_id: str, request: Request):
    return optional_json(feature_folder(request, run_id) / "impact.json", {"status": "not_run"})


@router.post("/runs/{run_id}/impact")
def analyze(run_id: str, comparison: ImpactRequest, request: Request):
    before, previous_docs, _ = active_paths(request, comparison.previous_run_id)
    current, current_docs, _ = active_paths(request, run_id)
    _, previous_agent, _, _ = runtime(request, comparison.previous_run_id, use_model=False)
    prior_answers = []
    for summary in traces(comparison.previous_run_id, request):
        candidate = read_trace(request, comparison.previous_run_id, summary["id"])
        refs = candidate["events"][-1]["citations"]
        refs = [{**ref, "quote": previous_agent.corpus.by_id[ref["passage_id"]]["text"]}
                for ref in refs if ref["passage_id"] in previous_agent.corpus.by_id
                and ref["document"] == previous_agent.corpus.by_id[ref["passage_id"]]["document"]]
        if refs and not candidate.get("agent_version"):
            prior_answers.append({"id": candidate["id"], "agent_id": comparison.previous_run_id, "citations": refs})
    report = analyze_impact(previous_docs, current_docs, prior_cases=read_json(before / "evals.json"),
                            prior_answers=prior_answers, agent_id=run_id, definition=read_json(current / "definition.json"),
                            full_regression=comparison.full_regression)
    return save_result(request, run_id, "impact.json", report)


@router.get("/runs/{run_id}/releases")
def releases(run_id: str, request: Request):
    store = feature_folder(request, run_id)
    return {"versions": versioning.list_releases(store, run_id), "history": versioning.release_history(store, run_id)}


@router.post("/runs/{run_id}/releases")
def create_release(run_id: str, payload: ReleaseRequest, request: Request):
    source_id = payload.source_run_id or run_id
    artifacts, documents, version = active_paths(request, source_id)
    try:
        with snapshot_artifacts(request, source_id, artifacts, version) as snapshot:
            return versioning.create_release(feature_folder(request, run_id), run_id, snapshot, documents,
                                             actor=request.state.principal.name,
                                             label=redact(payload.label) if payload.label is not None else None)
    except (ValueError, LookupError) as exc:
        raise operation_error(exc) from exc


@router.post("/runs/{run_id}/releases/{version_id}/{operation}")
def change_release(run_id: str, version_id: str, operation: Literal["approve", "activate", "rollback"], request: Request):
    active_paths(request, run_id, version_id)
    function = {"approve": versioning.approve_release, "activate": versioning.activate_release,
                "rollback": versioning.rollback_release}[operation]
    try:
        return function(feature_folder(request, run_id), run_id, version_id, actor=request.state.principal.name)
    except (ValueError, LookupError) as exc:
        raise operation_error(exc) from exc


@router.get("/runs/{run_id}/release-diff")
def compare_releases(run_id: str, before: str, after: str, request: Request):
    active_paths(request, run_id, before)
    active_paths(request, run_id, after)
    try:
        return versioning.compare_releases(feature_folder(request, run_id), run_id, before, after)
    except (ValueError, LookupError) as exc:
        raise operation_error(exc) from exc


@router.get("/runs/{run_id}/deployment")
def package(run_id: str, request: Request):
    artifacts, documents, version = active_paths(request, run_id)
    try:
        with snapshot_artifacts(request, run_id, artifacts, version) as snapshot:
            archive = deployment.build_deployment(snapshot, documents, allowed_documents=request.state.principal.documents)
    except (ValueError, LookupError, PermissionError) as exc:
        raise HTTPException(409, "The selected release could not be exported.") from exc
    return StreamingResponse(archive, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="forgeai-agent-{version or run_id}.zip"'})
