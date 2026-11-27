"""Package the committed ForgeAI Studio source as an owner-private Sites Worker."""

import argparse
import base64
import io
import json
import mimetypes
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import zipfile


ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    "people-operations-report.md": "people-ops",
    "marine-procurement-report.md": "marine-supply",
    "warehouse-tools-report.md": "operations-lab",
    "policy-regression-report.md": "people-ops-revised",
}


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=check)


def source_bundle(commit):
    with TemporaryDirectory() as directory:
        bundle = Path(directory) / "ForgeAI.bundle"
        head = git("symbolic-ref", "--quiet", "HEAD", check=False)
        branches = [head.stdout.decode().strip()] if head.returncode == 0 else []
        if git("rev-parse", "HEAD").stdout.decode().strip() != commit:
            raise ValueError("HEAD changed during packaging. Run the build again.")
        git("bundle", "create", str(bundle), "HEAD", *branches)
        if commit not in git("bundle", "list-heads", str(bundle)).stdout.decode():
            raise ValueError("The Git bundle does not contain the packaged commit.")
        return bundle.read_bytes()


def source_samples(source):
    samples = io.BytesIO()
    packs = {slug: f"demos/{slug}" for slug in REPORTS.values()}
    packs["observatory"] = "demos/enterprise-evidence/observatory"
    with zipfile.ZipFile(samples, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ForgeAI-samples/README.md", source.read("ForgeAI/demos/SAMPLE_GUIDE.md"))
        for name, folder in packs.items():
            root = f"ForgeAI/{folder}/"
            for path in source.namelist():
                tail = path.removeprefix(root)
                if tail != path and not path.endswith("/") and (tail == "brief.txt" or tail.startswith("documents/")):
                    archive.writestr(f"ForgeAI-samples/{name}/{tail}", source.read(path))
    return samples.getvalue()


def worker_assets(source_zip, bundle):
    data = {
        "/ForgeAI.zip": source_zip,
        "/ForgeAI.bundle": bundle,
    }
    with zipfile.ZipFile(io.BytesIO(source_zip)) as source:
        data["/"] = source.read("ForgeAI/static/index.html")
        data["/downloads"] = source.read("ForgeAI/hosting/downloads/index.html")
        data["/style.css"] = source.read("ForgeAI/hosting/downloads/style.css")
        data["/sample-documents"] = source_samples(source)
        for path in source.namelist():
            if path.startswith("ForgeAI/static/") and not path.endswith("/"):
                data[path.removeprefix("ForgeAI")] = source.read(path)
        for name in ("forge-hero.webp", "forge-icon.svg"):
            data["/" + name] = data["/static/" + name]
        for filename, slug in REPORTS.items():
            data["/" + filename] = source.read(f"ForgeAI/demos/{slug}/artifacts/report.md")
        return data, source.read("ForgeAI/hosting/worker.mjs").decode()


def asset_record(path, content):
    filename = "ForgeAI-sample-documents.zip" if path == "/sample-documents" else path.rsplit("/", 1)[1]
    content_type = "text/html; charset=utf-8" if path in {"/", "/downloads"} else mimetypes.guess_type(filename)[0]
    record = {
        "base64": base64.b64encode(content).decode(),
        "contentType": content_type or "application/octet-stream",
    }
    if filename.endswith((".zip", ".bundle", ".md")):
        record["filename"] = filename
    return record


def add_bytes(archive, path, content):
    entry = tarfile.TarInfo(path)
    entry.size = len(content)
    archive.addfile(entry, io.BytesIO(content))


def package(project_id, destination, review_demo=False):
    commit = git("rev-parse", "HEAD").stdout.decode().strip()
    source_zip = git("archive", "--format=zip", "--prefix=ForgeAI/", commit).stdout
    assets, worker = worker_assets(source_zip, source_bundle(commit))
    encoded = json.dumps({path: asset_record(path, content) for path, content in assets.items()}, separators=(",", ":"))
    entrypoint = 'import { assets } from "./assets.js";'
    if not worker.startswith(entrypoint):
        raise ValueError("The Worker entry point must import its generated assets.")
    worker = worker.replace(entrypoint, f"const assets = {encoded};", 1)
    if review_demo:
        worker = worker.replace("const reviewerOnly = false;", "const reviewerOnly = true;", 1)
    manifest = {"project_id": project_id, "r2": "BUCKET"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        add_bytes(archive, ".openai/hosting.json", json.dumps(manifest, indent=2).encode())
        add_bytes(archive, "dist/server/index.js", worker.encode())
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True, help="ID of your owner-private Sites project")
    parser.add_argument("--out", type=Path, default=ROOT / ".runs" / "site-deployment" / "forgeai-hosting.tar.gz")
    parser.add_argument("--review-demo", action="store_true", help="Restrict the public site to fictional sample runs")
    args = parser.parse_args()
    commit = package(args.project_id, args.out, args.review_demo)
    print(f"Packaged {commit} into {args.out}")


if __name__ == "__main__":
    main()
