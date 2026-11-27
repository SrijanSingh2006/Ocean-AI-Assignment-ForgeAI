"""Local FastAPI workspace and background build queue."""

import io
import os
import re
import shutil
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .corpus import MAX_FILES, MAX_FILE_BYTES, SUPPORTED, Corpus
from .factory import Agent, read_json, run_factory, write_json
from .model import LocalModel, ROOT
from .registry import REGISTRY
from . import feedback, ocr, privacy, reviewer
from .flight_recorder import FlightRecorder, store_trace, trace_retention

REVIEW_DEMO = os.getenv("FORGE_REVIEW_DEMO") == "1"
if not REVIEW_DEMO and os.getenv("FORGE_REQUIRE_AUTH") == "1" and not privacy.users():
    raise RuntimeError("Set up an access configuration before serving an authenticated deployment.")
app = FastAPI(title="ForgeAI", description="Agent factory and evidence workspace")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
RUNS = Path(os.getenv("FORGE_RUN_DIR", str(ROOT / ".runs" / "web"))).resolve()
DEMOS = {
    "people-ops": {"name": "People Operations", "kind": "Policy assistant", "icon": "users",
                   "description": "Shore-team leave, hybrid work, and travel policies.",
                   "example": "What does the Leave Handbook say about annual leave?"},
    "marine-supply": {"name": "Marine Procurement", "kind": "Catalog assistant", "icon": "box",
                       "description": "Spare parts, supplier terms, and dockside logistics.",
                       "example": "Look up AF-310"},
    "operations-lab": {"name": "Warehouse Tools", "kind": "Four-tool sample", "icon": "wrench",
                       "description": "Inventory, shipment CSVs, receiving, date, arithmetic, and weather.",
                       "example": "Look up BX-410"},
    "people-ops-revised": {"name": "Revised People Operations", "kind": "Regression sample", "icon": "history",
                          "description": "Revised leave allowance and expense submission deadlines.",
                          "example": "What does the Leave Handbook say about annual leave?", "regression": "people-ops"},
}
ARTIFACTS = (
    "report.md", "requirements.json", "definition.json", "initial_definition.json", "evals.json",
    "eval_results.json", "iterations.json", "scorecards.json", "model_trace.json", "regression.json", "run.json",
    "tournament.json", "manual_comparison.json", "blind_evals.json", "blind_results.json", "security.json",
)
QUEUE = ThreadPoolExecutor(max_workers=1, thread_name_prefix="forge")
LOCK = threading.RLock()
JOBS = {}
RUN_ROUTE = re.compile(r"/api/runs/([^/]+)(/.*)?$")


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


def source_names(folder):
    return [item.relative_to(folder).as_posix() for item in folder.rglob("*") if item.is_file()]


def can_access(principal, run_id):
    if principal.agents is not None and run_id not in principal.agents:
        return False
    if run_id in DEMOS:
        documents = demo_root(run_id) / "documents"
    else:
        if not re.fullmatch(r"[0-9a-f]{12}", run_id):
            return False
        root = RUNS / run_id
        try:
            metadata = read_json(root / "status.json")
        except (OSError, ValueError):
            return False
        if metadata.get("workspace", "local") != principal.workspace:
            return False
        documents = root / "documents"
    return principal.allows_documents(source_names(documents))


def require_run(request, run_id):
    principal = request.state.principal
    if principal is not privacy.LOCAL and not can_access(principal, run_id):
        raise HTTPException(404, "Run not found")
    return principal


@app.middleware("http")
async def authorize(request, call_next):
    path = request.url.path.rstrip("/")
    if REVIEW_DEMO:
        if not reviewer.permits(request.method, path, RUN_ROUTE.fullmatch(path), DEMOS):
            return JSONResponse({"detail": "Only published sample workflows are available."}, status_code=403)
        request.state.principal = reviewer.principal(DEMOS)
        if request.method == "POST" and len(await request.body()) > 8192:
            return JSONResponse({"detail": "The question is too large."}, status_code=413)
        return await call_next(request)
    try:
        principal = privacy.current(request.cookies.get(privacy.COOKIE))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return JSONResponse({"detail": "The workspace authorization configuration is invalid."}, status_code=503)
    request.state.principal = principal
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and principal is not privacy.LOCAL:
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            return JSONResponse({"detail": "This session accepts requests from its own origin."}, status_code=403)
    if not path.startswith("/api/") or path in {"/api/session", "/api/health"}:
        return await call_next(request)
    if principal is None:
        return JSONResponse({"detail": "Sign in to continue."}, status_code=401)
    match = RUN_ROUTE.fullmatch(path)
    if principal is not privacy.LOCAL and match and not can_access(principal, match[1]):
        return JSONResponse({"detail": "Run not found"}, status_code=404)
    suffix = match[2] if match else None
    if not principal.staff and request.method == "GET" and (suffix or path == "/api/dashboard"):
        return JSONResponse({"detail": "This operation requires a reviewer or admin."}, status_code=403)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and principal.role != "admin":
        allowed = path == "/api/chat" or (request.method == "POST" and suffix == "/feedback")
        approval = request.method == "POST" and principal.can_approve and principal.role == "reviewer" and (
            suffix == "/approve" or bool(suffix and re.fullmatch(r"/releases/[^/]+/approve", suffix))
        )
        if not (allowed or approval):
            return JSONResponse({"detail": "This operation requires an authorized admin."}, status_code=403)
    response = await call_next(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 400 and principal is not privacy.LOCAL:
        RUNS.mkdir(parents=True, exist_ok=True)
        entry = {"at": now(), "workspace": principal.workspace, "actor": principal.name,
                 "method": request.method, "route": path, "status": response.status_code}
        with LOCK, (RUNS / ".audit.jsonl").open("a", encoding="utf-8") as audit:
            import json
            audit.write(json.dumps(entry) + "\n")
    return response


@app.get("/api/session")
def session_info(request: Request):
    principal = request.state.principal
    return {"required": not REVIEW_DEMO and principal is not privacy.LOCAL, "authenticated": principal is not None,
            "review_demo": REVIEW_DEMO,
            "role": principal.role if principal else None, "name": principal.name if principal else None,
            "can_approve": principal.can_approve if principal else False}


@app.post("/api/session")
def sign_in(credentials: Login, request: Request, response: Response):
    try:
        token = privacy.login(credentials.username, credentials.password, request.client.host if request.client else "local")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise HTTPException(400, "Authentication is not configured or is invalid.") from exc
    if not token:
        raise HTTPException(401, "Sign-in failed. Check credentials or try again later.")
    response.set_cookie(privacy.COOKIE, token, max_age=privacy.SESSION_SECONDS, httponly=True, samesite="strict",
                        secure=os.getenv("FORGE_COOKIE_SECURE") == "1")
    return {"authenticated": True}


@app.delete("/api/session")
def sign_out(request: Request, response: Response):
    privacy.logout(request.cookies.get(privacy.COOKIE))
    response.delete_cookie(privacy.COOKIE)
    return {"authenticated": False}


@app.get("/api/health")
def health():
    return {"status": "ok"}


class Approval(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    edits: dict[str, str] = Field(default_factory=dict)


class Message(BaseModel):
    run_id: str
    question: str = Field(min_length=1, max_length=2000)
    language: Literal["auto", "en", "hi", "ta"] = "auto"


def now():
    return datetime.now(timezone.utc).isoformat()


def demo_root(name):
    return ROOT / "demos" / name


def run_paths(run_id):
    if run_id in DEMOS:
        root = demo_root(run_id)
        return root / "artifacts", root / "documents"
    if not re.fullmatch(r"[0-9a-f]{12}", run_id):
        raise HTTPException(404, "Run not found")
    root = RUNS / run_id
    if not root.is_dir():
        raise HTTPException(404, "Run not found")
    return root / "artifacts", root / "documents"


def completed(run_id):
    artifacts, documents = run_paths(run_id)
    if not (artifacts / "run.json").is_file():
        raise HTTPException(409, "This run has not completed")
    return artifacts, documents


def update(run_id, **fields):
    with LOCK:
        job = JOBS[run_id]
        job["meta"].update(fields)
        write_json(RUNS / run_id / "status.json", job["meta"])


def manage_run(run_id, brief, iterations, with_model, checkpoint, previous, manual, tournament, token_budget,
               latency_budget, blind, unseen, security_audit, minimum_confidence, extra_cases):
    artifacts, documents = run_paths(run_id)
    update(run_id, status="running", stage="intake", detail="Reading sources")

    def progress(stage, detail):
        update(run_id, status="running", stage=stage, detail=detail)

    def approval(requirements):
        update(run_id, status="approval", stage="intake", detail="Review the requirements", review=requirements)
        job = JOBS[run_id]
        if not job["event"].wait(timeout=600):
            raise ValueError("Requirements review expired after ten minutes. Start a new run to continue.")
        return job["review_submission"]

    try:
        result = run_factory(
            brief, documents, artifacts, model=LocalModel(with_model, token_budget), max_iterations=iterations,
            interview=approval if checkpoint else None, progress=progress, tournament=tournament,
            latency_budget=latency_budget, regression_cases=previous.get("evals"),
            prior_results=previous.get("results"), manual_baseline=manual, blind=blind, unseen_corpus=unseen,
            security_audit=security_audit, minimum_confidence=minimum_confidence, extra_cases=extra_cases,
        )
        update(run_id, status="complete", stage="report", detail="All artifacts are ready",
               name=result["definition"]["name"], score=result["scorecard"]["score"], finished=now(), review=None)
    except Exception as exc:
        update(run_id, status="failed", detail=str(exc), finished=now(), review=None)
    finally:
        with LOCK:
            JOBS.pop(run_id, None)


def current_state(run_id):
    if run_id in DEMOS:
        root, _ = run_paths(run_id)
        path = root / "run.json"
        if not path.exists():
            raise HTTPException(404, "The recorded demo is unavailable")
        result = read_json(path)
        return {"id": run_id, "status": "complete", "stage": "report",
                "name": result["definition"]["name"], "score": result["scorecard"]["score"],
                "created": None, "demo": True}
    run_paths(run_id)
    with LOCK:
        if run_id in JOBS:
            return dict(JOBS[run_id]["meta"])
    path = RUNS / run_id / "status.json"
    if not path.exists():
        raise HTTPException(404, "Run state unavailable")
    state = read_json(path)
    if state["status"] in {"queued", "running", "approval"}:
        state.update(status="failed", detail="The workspace restarted before this run completed.")
    return state


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/project-download", include_in_schema=False)
def project_download():
    archive = io.BytesIO()
    paths = [ROOT / name for name in ("forgeai", "prompts", "static", "demos", "docs", "hosting", "scripts", "submission", "tests")]
    paths.extend(ROOT / name for name in ("README.md", "launch.py", "pyproject.toml", "package.json", ".gitignore", ".gitattributes"))
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for source in paths:
            entries = source.rglob("*") if source.is_dir() else [source]
            for item in entries:
                if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc":
                    package.write(item, "ForgeAI/" + item.relative_to(ROOT).as_posix())
    archive.seek(0)
    return StreamingResponse(archive, media_type="application/zip",
                             headers={"Content-Disposition": 'attachment; filename="ForgeAI.zip"'})


@app.get("/sample-documents", include_in_schema=False)
def sample_documents():
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        guide = ROOT / "demos" / "SAMPLE_GUIDE.md"
        archive.write(guide, "ForgeAI-samples/README.md")
        for key in DEMOS:
            root = demo_root(key)
            archive.write(root / "brief.txt", f"ForgeAI-samples/{key}/brief.txt")
            for item in (root / "documents").iterdir():
                if item.is_file() and item.suffix.lower() in SUPPORTED:
                    archive.write(item, f"ForgeAI-samples/{key}/documents/{item.name}")
    memory.seek(0)
    return StreamingResponse(memory, media_type="application/zip",
                             headers={"Content-Disposition": 'attachment; filename="ForgeAI-sample-documents.zip"'})


@app.get("/api/workspace")
def workspace():
    demos = []
    for key, info in DEMOS.items():
        root = demo_root(key)
        demos.append({"id": key, **info, "brief": (root / "brief.txt").read_text().strip(),
                      "files": sorted(p.name for p in (root / "documents").iterdir()),
                      "recorded": (root / "artifacts" / "run.json").exists()})
    return {"model_online": LocalModel().probe(), "model": LocalModel().name,
            "demos": demos, "tools": REGISTRY, "max_files": MAX_FILES, "max_file_bytes": MAX_FILE_BYTES,
            "ocr_enabled": ocr.enabled() and ocr.available()}


@app.get("/api/runs")
def runs(request: Request):
    entries = [current_state(key) for key in DEMOS if (demo_root(key) / "artifacts" / "run.json").is_file()]
    if not REVIEW_DEMO and RUNS.exists():
        own = []
        for item in RUNS.iterdir():
            if (item / "status.json").is_file():
                own.append(current_state(item.name))
        entries = sorted(own, key=lambda item: item["created"], reverse=True) + entries
    principal = request.state.principal
    return entries if principal is privacy.LOCAL else [entry for entry in entries if can_access(principal, entry["id"])]


@app.post("/api/runs", status_code=202)
async def launch(
    request: Request,
    brief: str = Form(...),
    iterations: int = Form(3),
    model: bool = Form(True),
    checkpoint: bool = Form(False),
    demo: str = Form(""),
    regression: str = Form(""),
    tournament: bool = Form(True),
    token_budget: int = Form(12_000, ge=0, le=60_000),
    latency_budget: int = Form(120, ge=1, le=600),
    blind: bool = Form(False),
    unseen_corpus: bool = Form(False),
    security_audit: bool = Form(False),
    minimum_confidence: float = Form(0, ge=0, le=1),
    files: list[UploadFile] | None = File(None),
):
    brief = brief.strip()
    if not brief or len(brief) > 4000:
        raise HTTPException(422, "Enter a brief between 1 and 4,000 characters")
    if not 0 <= iterations <= 3:
        raise HTTPException(422, "Select between zero and three repair iterations")
    if unseen_corpus and demo:
        raise HTTPException(422, "Use new uploaded documents for an unseen corpus.")
    if demo and demo not in DEMOS:
        raise HTTPException(422, "Unknown source collection")
    files = files or []
    if not files and not demo:
        raise HTTPException(422, "Add at least one document or choose a demo")
    if regression:
        require_run(request, regression)
    previous = read_json(completed(regression)[0] / "run.json") if regression else {}
    extra_cases = []
    if regression:
        store = enterprise_api.feature_folder(request, regression)
        reviewed = feedback.approved_cases(store, regression)
        previous["evals"] = previous["evals"] + reviewed
        extra_cases = feedback.approved_cases(store, regression, suite="development")
    manual_path = demo_root(demo) / "manual-baseline.json" if demo else None
    manual = read_json(manual_path) if manual_path and manual_path.is_file() else None
    original = sorted((demo_root(demo) / "documents").iterdir()) if demo else []
    principal = request.state.principal
    submitted_names = [item.name for item in original] + [Path((file.filename or "").replace("\\", "/")).name for file in files]
    if not principal.allows_documents(submitted_names):
        raise HTTPException(403, "This account cannot attach one or more source documents.")
    if len(files) + len(original) > MAX_FILES:
        raise HTTPException(422, f"Use at most {MAX_FILES} files")
    run_id = uuid.uuid4().hex[:12]
    root = RUNS / run_id
    folder = root / "documents"
    folder.mkdir(parents=True, exist_ok=False)
    try:
        for path in original:
            shutil.copy2(path, folder / path.name)
        for file in files:
            name = Path((file.filename or "").replace("\\", "/")).name
            if Path(name).suffix.lower() not in SUPPORTED or len(name) > 150:
                raise HTTPException(422, f"Unsupported file: {name}")
            target = folder / name
            if target.exists():
                raise HTTPException(422, f"Duplicate filename: {name}")
            value = await file.read(MAX_FILE_BYTES + 1)
            if len(value) > MAX_FILE_BYTES:
                raise HTTPException(422, f"{name} exceeds 10 MB")
            target.write_bytes(value)
    except Exception:
        shutil.rmtree(root)
        raise
    (root / "brief.txt").write_text(brief + "\n", encoding="utf-8")
    meta = {"id": run_id, "workspace": principal.workspace, "owner": principal.name, "status": "queued", "stage": "intake", "detail": "Waiting for the factory",
            "name": DEMOS[demo]["name"] if demo else "Custom agent", "created": now(), "demo": False}
    with LOCK:
        JOBS[run_id] = {"meta": meta, "event": threading.Event(), "review_submission": {}}
        write_json(root / "status.json", meta)
        initial = dict(meta)
    QUEUE.submit(manage_run, run_id, brief, iterations, model, checkpoint, previous,
                 manual, tournament, token_budget, latency_budget, blind, unseen_corpus, security_audit,
                 minimum_confidence, extra_cases)
    return initial


@app.get("/api/runs/{run_id}")
def show(run_id: str, request: Request):
    state = current_state(run_id)
    if state["status"] == "complete" and request.state.principal.staff:
        folder, _ = completed(run_id)
        state["result"] = read_json(folder / "run.json")
    return state


@app.post("/api/runs/{run_id}/approve")
def approve(run_id: str, approval: Approval):
    with LOCK:
        job = JOBS.get(run_id)
        if not job or job["meta"]["status"] != "approval" or job["event"].is_set():
            raise HTTPException(409, "This run is not awaiting review")
        job["review_submission"] = approval.model_dump()
        job["event"].set()
    return {"approved": True}


@app.get("/api/runs/{run_id}/artifact/{name}")
def artifact(run_id: str, name: str):
    folder, _ = completed(run_id)
    file = folder / name
    if name not in ARTIFACTS or not file.is_file():
        raise HTTPException(404, "Artifact not available")
    return FileResponse(file, filename=name)


@app.get("/api/runs/{run_id}/download")
def download(run_id: str):
    folder, documents = completed(run_id)
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in folder.iterdir():
            if item.name in ARTIFACTS:
                archive.write(item, "artifacts/" + item.name)
        for item in documents.rglob("*"):
            if item.is_file():
                archive.write(item, "documents/" + item.relative_to(documents).as_posix())
        brief = documents.parent / "brief.txt"
        if brief.is_file():
            archive.write(brief, "brief.txt")
    memory.seek(0)
    return StreamingResponse(memory, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="forgeai-{run_id}.zip"'})


@app.post("/api/chat")
def chat(message: Message, request: Request):
    if REVIEW_DEMO:
        require_run(request, message.run_id)
        if not reviewer.CHAT_SLOTS.acquire(blocking=False):
            raise HTTPException(429, "The demo is busy. Try again in a moment.")
        try:
            from .multilingual import language_model

            artifacts, documents = completed(message.run_id)
            definition = read_json(artifacts / "definition.json")
            retrieval = definition["retrieval"]
            corpus = Corpus.load(documents, retrieval["chunk_words"], retrieval["overlap_words"])
            agent = Agent(definition, corpus, permit_network=False, translator=language_model())
            return agent.answer(message.question, requested_language=message.language)
        finally:
            reviewer.CHAT_SLOTS.release()
    _, agent, version, _ = enterprise_api.runtime(request, message.run_id)
    principal = request.state.principal
    recorder = FlightRecorder(message.question, principal.name)
    response = agent.answer(message.question, recorder, message.language)
    record = recorder.finish(response)
    record["agent_version"] = version
    try:
        store_trace(enterprise_api.feature_folder(request, message.run_id) / "traces", record, trace_retention())
    except (OSError, ValueError):
        return {**response, "trace_status": "unavailable"}
    return {**response, "trace_id": record["id"], "agent_version": version}


from . import enterprise_api

app.include_router(enterprise_api.router)
