import { assets } from "./assets.js";

const encoded = new Uint8Array(0);
const requestPrefix = "requests/";
const responsePrefix = "responses/";
const claimPrefix = "claims/";
const lifetime = 85_000;
const uploadLimit = 90 * 1024 * 1024;

const json = (value, status = 200) => Response.json(value, { status, headers: { "Cache-Control": "no-store" } });
const problem = (detail, status) => json({ detail }, status);
const timer = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function apiOperation(method, target) {
  const [path, query, extra] = target.split("?");
  const run = path.match(/^\/api\/runs\/(people-ops|marine-supply|operations-lab|people-ops-revised|[a-f0-9]{12})(?:\/(.*))?$/);
  if (query !== undefined) {
    return extra === undefined && method === "GET" && run?.[2] === "release-diff"
      && /^before=[a-f0-9]{32}&after=[a-f0-9]{32}$/.test(query);
  }
  if (method === "GET" && ["/api/workspace", "/api/session", "/api/health", "/api/dashboard", "/api/runs", "/project-download"].includes(path)) return true;
  if (method === "POST" && ["/api/runs", "/api/chat", "/api/confidence/calibration"].includes(path)) return true;
  if (!run) return false;
  const suffix = run[2] || "";
  if (method === "POST") {
    return ["approve", "security", "models", "languages", "feedback", "impact", "releases"].includes(suffix)
      || /^(conflicts\/[a-f0-9]{16}|feedback\/[a-f0-9]{32}\/review|releases\/[a-f0-9]{32}\/(approve|activate|rollback))$/.test(suffix);
  }
  if (method === "DELETE") return /^traces\/[a-f0-9]{32}$/.test(suffix);
  return method === "GET" && (["", "download", "conflicts", "traces", "security", "models", "languages", "feedback", "impact", "releases", "deployment"].includes(suffix)
    || /^(artifact\/[a-z_]+\.(json|md)|traces\/[a-f0-9]{32})$/.test(suffix));
}

function staticAsset(path, method) {
  const asset = assets[path];
  if (!asset || !["GET", "HEAD"].includes(method)) return null;
  const headers = { "Content-Type": asset.contentType, "Cache-Control": "no-cache" };
  if (asset.filename) headers["Content-Disposition"] = `attachment; filename="${asset.filename}"`;
  return new Response(method === "HEAD" ? null : Uint8Array.from(atob(asset.base64), (char) => char.charCodeAt(0)), { headers });
}

function contentHeaders(record) {
  const headers = { "Cache-Control": "no-store" };
  for (const name of ["Content-Type", "Content-Disposition"]) {
    const value = record.httpMetadata?.[name === "Content-Type" ? "contentType" : "contentDisposition"];
    if (value) headers[name] = value;
  }
  return headers;
}

async function remove(bus, id) {
  await bus.delete([requestPrefix + id, responsePrefix + id, claimPrefix + id]);
}

async function relay(request, path, bus, context) {
  const id = crypto.randomUUID();
  const started = Date.now();
  const contentType = request.headers.get("Content-Type") || "application/octet-stream";
  const length = Number(request.headers.get("Content-Length"));
  if (length > uploadLimit) return problem("Submit at most 90 MB per build in hosted Studio.", 413);
  try {
    await bus.put(requestPrefix + id, request.body || encoded, {
      httpMetadata: { contentType },
      customMetadata: { method: request.method, path, created: String(started) },
    });
    while (Date.now() - started < lifetime - 8_000) {
      const outgoing = await bus.get(responsePrefix + id);
      if (outgoing) {
        const status = Number(outgoing.customMetadata?.status || 502);
        const headers = contentHeaders(outgoing);
        context.waitUntil(remove(bus, id).catch(() => {}));
        return new Response(status === 204 || status === 304 ? null : outgoing.body, { status, headers });
      }
      await timer(350);
    }
    return problem("The ForgeAI workspace did not respond. Keep the workspace running and try again.", 504);
  } catch (error) {
    console.error("ForgeAI relay failed", error.name);
    return problem("Hosted Studio could not reach its workspace queue.", 502);
  } finally {
    context.waitUntil(bus.delete(requestPrefix + id).catch(() => {}));
  }
}

async function bridge(request, path, bus, context) {
  if (request.headers.get("x-forge-runtime") !== "1" || request.headers.has("oai-authenticated-user-id")) {
    return problem("Not found", 404);
  }

  if (request.method === "GET" && path === "/_forge/queue") {
    const pending = await bus.list({ prefix: requestPrefix, limit: 30, include: ["customMetadata"] });
    const requests = [];
    for (const item of pending.objects) {
      const id = item.key.slice(requestPrefix.length);
      if (Date.now() - Number(item.customMetadata?.created || 0) > lifetime) {
        context.waitUntil(remove(bus, id).catch(() => {}));
      } else {
        requests.push(id);
      }
    }
    return json({ requests });
  }

  const match = path.match(/^\/_forge\/requests\/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$/);
  if (!match) return problem("Not found", 404);
  const id = match[1];
  const original = await bus.get(requestPrefix + id);
  if (!original) return problem("Request expired", 404);
  const meta = original.customMetadata || {};
  if (Date.now() - Number(meta.created) > lifetime || !apiOperation(meta.method, meta.path)) {
    await original.body.cancel();
    await remove(bus, id);
    return problem("Request expired", 404);
  }

  if (request.method === "GET") {
    const claim = await bus.put(claimPrefix + id, encoded, { onlyIf: { etagDoesNotMatch: "*" } });
    if (!claim) {
      await original.body.cancel();
      return problem("Request claimed", 409);
    }
    const headers = contentHeaders(original);
    headers["x-forge-method"] = meta.method;
    headers["x-forge-path"] = meta.path;
    return new Response(original.body, { headers });
  }

  await original.body.cancel();
  if (request.method === "PUT") {
    const claim = await bus.head(claimPrefix + id);
    const status = Number(request.headers.get("x-forge-status"));
    if (!claim || !Number.isInteger(status) || status < 200 || status > 599) return problem("Invalid result", 409);
    await bus.put(responsePrefix + id, request.body || encoded, {
      customMetadata: { status: String(status) },
      httpMetadata: {
        contentType: request.headers.get("Content-Type") || "application/octet-stream",
        contentDisposition: request.headers.get("Content-Disposition") || undefined,
      },
    });
    return new Response(null, { status: 204 });
  }
  return problem("Method not allowed", 405);
}

export default {
  async fetch(request, env, context) {
    const { pathname: path, search } = new URL(request.url);
    const asset = staticAsset(path, request.method);
    if (asset) return asset;
    if (path.startsWith("/_forge/")) {
      try {
        return await bridge(request, path, env.BUCKET, context);
      } catch (error) {
        console.error("ForgeAI queue failed", error.name);
        return problem("Workspace queue unavailable", 502);
      }
    }
    const target = path + search;
    if (apiOperation(request.method, target)) return relay(request, target, env.BUCKET, context);
    return problem("Not found", 404);
  },
};
