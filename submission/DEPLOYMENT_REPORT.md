# Deployment report

| Component | Verified configuration |
| --- | --- |
| Frontend | ChatGPT Sites Worker serves Studio. The separate reviewer build exposes fictional results, real cited chat, and agent ZIPs. |
| Backend | FastAPI runs over loopback in the cloud workspace. A private relay forwards allowlisted requests through temporary R2 objects. |
| Scope | Four bundled sample runs. Mutations, private run identifiers and execution trace downloads are blocked. Guest questions do not enter persistent trace storage. |
| Health | GET /api/health works in the reviewer API and container. |
| Model | Local Qwen supports the owner factory. Local NLLB and E5 support compatible multilingual workflows. |
| Persistence | Workspace files and SQLite metadata. Container runs use a /data mount. The container kept a verified owner build after restart and required the user to sign in again. |
| Authentication | Site sign-in protects the owner workspace. The reviewer site accepts anonymous visitors and its backend relay requires a dedicated credential. Standalone Docker owner mode requires an authorization configuration. |
| Transport | Site HTTPS with same-origin requests. The cloud runtime binds to loopback behind the relay. |
| Public access | Anonymous HTTPS tests verified the reviewer homepage, four sample agents, cited chat, and a valid agent ZIP. The create-run route and relay queue rejected anonymous requests. |

The reviewer deployment needs an active cloud backend and connector. Shared PostgreSQL, distributed sessions and backup restoration need separate infrastructure.

The [Render Blueprint](../render.yaml) passed Render's published schema. Its Docker configuration was exercised with a non-default platform port. A Render instance still requires an authorized account connection. The verified URLs in this submission use Sites. [Deployment and configuration guide](../docs/deployment.md)

## Reproduce

```bash
docker build -t forgeai-studio .
docker run --rm -p 127.0.0.1:8878:8000 -e FORGE_REVIEW_DEMO=1 forgeai-studio
```

For an authenticated owner runtime, mount the authorization file and set FORGE_AUTH_CONFIG. Use a persistent volume for /data. When a managed network uses its own trusted package CA, pass it via the Docker build secret pip_ca. [Hosting setup](../hosting/README.md)
