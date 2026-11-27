# Private Studio hosting

The Sites Worker serves the Studio frontend, sample files, and downloads. Its allowlisted API routes use a private R2 queue. The connector claims queued requests and forwards them to FastAPI over loopback. Qwen, run artifacts, feedback, and releases live in the Python workspace. The hosted Site uses owner-only access as its sign-in boundary. The local launcher is available to reviewers who clone the public repository.

## Package the Worker

Commit the source you want to deploy, then run the packager from the Git checkout with your own Sites project ID.

```bash
python hosting/build.py --project-id YOUR_SITE_PROJECT_ID
```

The archive at `.runs/site-deployment/forgeai-hosting.tar.gz` contains the hosting manifest and Worker module, including browser assets, fictional sample files, and a project download built from the same commit. Configure an owner-private Site with its `BUCKET` R2 binding. Publish the archive against the matching commit on that Site's configured source branch.

## Start the backend and connector

Run FastAPI in local mode inside the private workspace. In a separate terminal, connect it to the deployed Site. The connector prompts for the configured Site service credential and keeps it in process memory.

```bash
python -m forgeai serve --host 127.0.0.1 --port 8874
```

```bash
python hosting/connect.py https://YOUR_SITE.chatgpt.site --port 8874
```

Both processes need to stay active for builds, chat, evaluation, and agent export to work. Set `FORGE_OCR=1` before starting FastAPI if Tesseract and Poppler are installed. Start Qwen separately with `bash scripts/local-model.sh` for model-assisted workflows.

## Check the deployment

Open Studio using the Site owner's account. Check that the dashboard loads, ask the People Operations demo about annual leave, and open the answer's citation and execution trace. In the Engineering lab, **Releases and export** downloads the runnable agent ZIP. An HTTP 401 on the private URL indicates that the browser needs the owner's Site session.

Standalone agent deployments use the runner and Docker files in the exported ZIP. [Application README](../README.md#deploy-a-standalone-agent)

## Reviewer staging

Build with the reviewer variant to limit requests to sample reports, exports and bounded chat. Start the backend in a separate workspace with FORGE_REVIEW_DEMO=1. Set the Site's FORGE_RELAY_KEY as a secret and give that credential to the connector through its prompt.

```bash
python hosting/build.py --project-id YOUR_REVIEWER_PROJECT_ID --review-demo
FORGE_REVIEW_DEMO=1 python -m forgeai serve --host 127.0.0.1 --port 8878
```

In another terminal, connect the approved reviewer Site. Add --site-auth for owner-private staging and enter its service credential at the second prompt.

```bash
python hosting/connect.py https://YOUR_REVIEWER_SITE.chatgpt.site --port 8878 --review-demo
```

Review the published sample and access boundaries before changing its audience. [Deployment verification](../submission/DEPLOYMENT_REPORT.md)
