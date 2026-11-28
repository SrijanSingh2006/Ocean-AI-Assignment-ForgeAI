# Deploy ForgeAI Studio

## Deployment profiles

The public reviewer profile serves the four bundled fictional runs, their evaluation reports, live cited chat and agent ZIPs. The owner profile adds authenticated uploads, agent builds, requirements review, feedback and release management. A single Docker service serves both its static frontend and FastAPI endpoints from the same origin.

## Docker

Build the same image used by the Render Blueprint. Run reviewer mode against the published fictional corpus.

```sh
docker build -t forgeai-studio .
docker run --rm -p 127.0.0.1:8000:8000 -e FORGE_REVIEW_DEMO=1 forgeai-studio
curl --fail http://127.0.0.1:8000/api/health
```

The container runs as UID and GID `10001` and serves the frontend and APIs on the same origin. Set `PORT` if your platform supplies a port other than 8000. The health check uses the same port. For owner mode, replace the placeholders in [the example authorization file](access.example.json) with generated password hashes. Keep the resulting file private.

```sh
docker volume create forgeai-data
docker run --rm -p 127.0.0.1:8000:8000 \
  --mount type=volume,src=forgeai-data,dst=/data \
  --mount type=bind,src=/absolute/path/to/private-access.json,dst=/run/secrets/forgeai-auth.json,readonly \
  -e FORGE_AUTH_CONFIG=/run/secrets/forgeai-auth.json \
  forgeai-studio
```

The mounted files must be readable by the container user. The image requires authorization in owner mode. Serve remote owner access through HTTPS and set `FORGE_COOKIE_SECURE=1`. Mount writable run storage at `/data` and back it up periodically. Completed runs survive restarts when the same volume is mounted. Users sign in again after a process restart.

## Render Blueprint

[render.yaml](../render.yaml) configures a free Docker web service for the public reviewer workflow. The service follows `enterprise/incremental-upgrade`, uses `/api/health`, and uses the fictional sample runs bundled in the image.

1. In Render, create a **Blueprint** and connect the ForgeAI GitHub repository from an authorized account.
2. Select `enterprise/incremental-upgrade` and apply `render.yaml`. Wait for the service to become healthy.
3. Open the assigned HTTPS URL in a fresh browser. Open People Operations, try cited chat, download an agent, and check that only the published runs are visible.

Render's free web services can sleep after inactivity and use ephemeral storage. The base image runs deterministic retrieval and includes aligned translations for the bundled policy evidence. Configure translation and embedding endpoints for broader Hindi and Tamil question coverage. Recorded multilingual reports remain visible in either profile. To provision a Render owner instance, use a separate Docker service with the authentication secret, a persistent disk mounted at `/data`, and enough resources for the chosen model providers. Managed multi-instance session storage and PostgreSQL require application changes. [Render Blueprint reference](https://render.com/docs/blueprint-spec) · [Render free tier](https://render.com/docs/free)

## Models and document tools

- Supply an OpenAI-compatible chat endpoint through `FORGE_MODEL_URL` and `FORGE_MODEL_NAME`. Use `FORGE_MODEL_API_KEY` only when required by the endpoint.
- For external translation and embeddings, configure the `FORGE_LANGUAGE_MODEL_*` and `FORGE_EMBEDDING_*` settings in the platform secret store. Connected providers receive the inputs needed for their configured tasks.
- For local models, install the `languages` extra and mount compatible NLLB CTranslate2 and E5 ONNX weights. Set `FORGE_NLLB_PATH` and `FORGE_E5_PATH`. Model weights are installed separately.
- For OCR and figure extraction on a deployment, install Tesseract, the language packs you will use, Poppler and Pillow in the runtime. Enable `FORGE_OCR` and `FORGE_FIGURES` as needed.

Use `/api/health` for process health and the Studio sidebar or `/api/workspace` for model connectivity. After changing providers, replay the [language checks](../scripts/check_multilingual.py) on the deployed public reviewer and confirm that cited answers, missing-provider states and refusals behave as expected.
