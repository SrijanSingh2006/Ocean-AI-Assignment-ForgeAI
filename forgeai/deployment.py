"""Export an authorized agent snapshot with its sources and an isolated API runner."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

from .corpus import MAX_FILE_BYTES
from .factory import Agent, read_json
from .impact import fingerprints, source_files
from .model import ROOT
from .registry import REGISTRY
from .versioning import load_snapshot_corpus

EVIDENCE_FILES = (
    "evals.json", "eval_results.json", "scorecards.json", "iterations.json", "report.md",
    "security.json", "security_scorecard.json", "security_report.json",
    "regression.json", "multilingual_results.json",
)
REQUIREMENTS = """fastapi>=0.115,<1
uvicorn>=0.30,<1
pypdf>=5,<7
python-docx>=1.1,<2
"""
DOCKERFILE = """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=pip_ca \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi; \
    python -m pip install --no-cache-dir -r requirements.txt
COPY --chown=10001:10001 . .
USER 10001
EXPOSE 8000
CMD ["python", "runner.py", "--host", "0.0.0.0"]
"""
COMPOSE = """services:
  agent:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      FORGE_DEPLOY_TOKEN: ${FORGE_DEPLOY_TOKEN:-}
      FORGE_DEPLOY_MODEL: ${FORGE_DEPLOY_MODEL:-0}
      FORGE_DEPLOY_NETWORK: ${FORGE_DEPLOY_NETWORK:-0}
      FORGE_MODEL_URL: ${FORGE_MODEL_URL:-http://127.0.0.1:8089/v1}
      FORGE_MODEL_NAME: ${FORGE_MODEL_NAME:-qwen2.5-0.5b}
"""
ENV_EXAMPLE = """FORGE_DEPLOY_TOKEN=
FORGE_DEPLOY_MODEL=0
FORGE_DEPLOY_NETWORK=0
FORGE_MODEL_URL=http://127.0.0.1:8089/v1
FORGE_MODEL_NAME=qwen2.5-0.5b
"""
README = """# ForgeAI agent snapshot

This package contains the frozen agent definition, its source documents, the
common runner, configured tools, source hashes, and available evaluation evidence.

## Run locally

Use Python 3.10 or newer. From this folder:

```sh
python -m pip install -r requirements.txt
python runner.py
```

The API binds to the local machine at port 8000. View its interactive contract
at http://127.0.0.1:8000/docs. Send a request with:

```sh
curl http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \\
  -d '{"question":"Where is the relevant policy documented?"}'
```

For one local query, run `python runner.py --ask "Where is the relevant policy documented?"`.

## Container

Run `docker compose up --build` and visit http://127.0.0.1:8000/docs.
The Compose port maps to loopback. A model server in a different container or
on the host needs a reachable model URL.

If dependency downloads require a custom certificate authority, supply the
trusted CA bundle as a transient BuildKit secret during the image build.

```sh
docker build --secret id=pip_ca,src=/path/to/ca-bundle.pem -t forgeai-agent .
docker run --rm -p 127.0.0.1:8000:8000 forgeai-agent
```

## Runtime configuration

Set environment variables directly or through your deployment's secret
configuration. `.env.example` documents the supported names. Keep actual
credentials outside exported packages. Set a strong `FORGE_DEPLOY_TOKEN` before
exposing this service through an authenticated TLS reverse proxy. When configured,
requests to the chat endpoint need the `Authorization: Bearer <token>` header.
The token protects all access to this single agent and its citations, so grant it
only to users authorized for the included documents.

Lexical retrieval works with local dependencies. Set `FORGE_DEPLOY_MODEL=1`
and configure an OpenAI-compatible model server for optional model-assisted
evidence selection. Set `FORGE_DEPLOY_NETWORK=1` to permit the already-selected
weather tool to contact its data provider. Enable an external service only when
the deployment can share the data that service needs.

## Evidence and limits

Consult `reports/` for the committed evaluation dataset, available results and
scorecards, and security assessment status. The package verifies source hashes
and the index hash before it accepts questions. An OCR-based build carries its
extracted passages and coordinates, so the fixed snapshot can answer from
that evidence in a runtime without OCR binaries.
"""
RUNNER = '''"""Serve a single ForgeAI deployment snapshot."""

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from forgeai.corpus import Corpus
from forgeai.factory import Agent, read_json
from forgeai.impact import fingerprints
from forgeai.model import LocalModel

ROOT = Path(__file__).resolve().parent
configuration = read_json(ROOT / "runner-config.json")
definition = read_json(ROOT / configuration["definition"])
manifest = read_json(ROOT / configuration["manifest"])
tools = read_json(ROOT / configuration["tools"])
documents = ROOT / configuration["documents"]
if fingerprints(documents) != manifest["sources"]:
    raise RuntimeError("Deployment source fingerprints do not match the manifest")
if sorted(definition["tools"]) != sorted(tools):
    raise RuntimeError("Deployment tool configuration does not match the definition")
index_data = (ROOT / configuration["index"]).read_bytes()
if hashlib.sha256(index_data).hexdigest() != manifest["index_sha256"]:
    raise RuntimeError("Deployment index fingerprint does not match the manifest")
frozen = json.loads(index_data)
corpus = Corpus(frozen["passages"], frozen["documents"], frozen["warnings"])
app = FastAPI(title=definition["name"])


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


def answer(question):
    if not question.strip():
        raise ValueError("Enter a question")
    return Agent(
        definition, corpus, LocalModel() if os.getenv("FORGE_DEPLOY_MODEL") == "1" else None,
        permit_network=os.getenv("FORGE_DEPLOY_NETWORK") == "1",
    ).answer(question)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(payload: Question, authorization: str = Header(default="")):
    token = os.getenv("FORGE_DEPLOY_TOKEN")
    if token and not hmac.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
        raise HTTPException(401, "Agent access token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        return answer(payload.question)
    except ValueError as exc:
        raise HTTPException(422, "Enter a valid question") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--ask")
    arguments = parser.parse_args()
    if arguments.ask is not None:
        print(json.dumps(answer(arguments.ask), ensure_ascii=False, indent=2))
    else:
        import uvicorn
        uvicorn.run(app, host=arguments.host, port=arguments.port)


if __name__ == "__main__":
    main()
'''


def _json(archive, name, value):
    archive.writestr(name, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def build_deployment(artifacts, documents, *, allowed_documents=None, source_root=None):
    """Export the complete snapshot or deny when the caller lacks access to an included source."""
    artifacts, documents = Path(artifacts), Path(documents)
    source_root = Path(source_root) if source_root is not None else ROOT
    if not artifacts.is_dir() or artifacts.is_symlink():
        raise ValueError("A completed artifact directory is required")
    sources = source_files(documents)
    if allowed_documents is not None and not set(sources).issubset(set(allowed_documents)):
        raise PermissionError("Deployment export needs access to every source in the agent snapshot")
    if any(path.stat().st_size > MAX_FILE_BYTES for path in sources.values()):
        raise ValueError("Deployment document exceeds the file size limit")
    definition_path = artifacts / "definition.json"
    if not definition_path.is_file() or definition_path.is_symlink():
        raise ValueError("A completed regular definition file is required")
    definition = read_json(definition_path)
    corpus = load_snapshot_corpus(artifacts, documents, definition)
    Agent(definition, corpus)
    source_hashes = fingerprints(documents)
    index_data = json.dumps(
        {"passages": corpus.passages, "documents": corpus.documents, "warnings": corpus.warnings},
        separators=(",", ":"), ensure_ascii=False,
    ).encode()

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        _json(archive, "definition.json", definition)
        _json(archive, "tools.json", {tool: REGISTRY[tool] for tool in definition["tools"]})
        _json(archive, "manifest.json", {"schema_version": 1, "agent": definition["name"], "sources": source_hashes,
                                         "index_sha256": hashlib.sha256(index_data).hexdigest()})
        _json(archive, "runner-config.json", {"definition": "definition.json", "documents": "documents",
                                              "tools": "tools.json", "manifest": "manifest.json",
                                              "index": "indexed-corpus.json"})
        archive.writestr("indexed-corpus.json", index_data)
        for name, path in sources.items():
            archive.write(path, "documents/" + name)
        models = [(source_root / "forgeai", "*.py"), (source_root / "prompts", "*.txt")]
        for folder, pattern in models:
            if not folder.is_dir() or folder.is_symlink():
                raise ValueError(f"Deployment runner directory is missing: {folder.name}")
            excluded = {"web.py", "cli.py", "__main__.py", "deployment.py"}
            for path in sorted(folder.glob(pattern)):
                if path.is_file() and not path.is_symlink() and path.name not in excluded:
                    archive.write(path, f"{folder.name}/{path.name}")
        included = []
        for name in EVIDENCE_FILES:
            path = artifacts / name
            if path.is_file() and not path.is_symlink():
                archive.write(path, "reports/" + name)
                included.append(name)
        security = [name for name in included if name.startswith("security")]
        _json(archive, "reports/evidence-manifest.json", {
            "files": included, "security": {"status": "recorded" if security else "unavailable", "files": security},
        })
        archive.writestr("runner.py", RUNNER)
        archive.writestr("requirements.txt", REQUIREMENTS)
        archive.writestr("Dockerfile", DOCKERFILE)
        archive.writestr("compose.yaml", COMPOSE)
        archive.writestr(".env.example", ENV_EXAMPLE)
        archive.writestr(".dockerignore", ".env\n.venv/\n__pycache__/\n*.pyc\n")
        archive.writestr("README.md", README)
    if fingerprints(documents) != source_hashes:
        raise ValueError("Source files changed while creating the deployment package")
    output.seek(0)
    return output
