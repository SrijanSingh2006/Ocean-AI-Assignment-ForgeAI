"""Connect the private ForgeAI Studio site to the running workspace application."""

import argparse
import concurrent.futures
import getpass
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
RUN = re.compile(r"/api/runs/(?:people-ops|marine-supply|operations-lab|people-ops-revised|[a-f0-9]{12})(?:/(.*))?")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        return None


def fetch(url, method="GET", body=None, headers=None, timeout=20):
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, error.headers, error.read()


def allowed(method, target):
    path, separator, query = target.partition("?")
    if separator:
        match = RUN.fullmatch(path)
        return method == "GET" and bool(
            match and match[1] == "release-diff" and re.fullmatch(r"before=[a-f0-9]{32}&after=[a-f0-9]{32}", query)
        )
    if method == "GET" and path in {"/api/workspace", "/api/session", "/api/health", "/api/dashboard", "/api/runs", "/project-download"}:
        return True
    if method == "POST" and path in {"/api/runs", "/api/chat", "/api/confidence/calibration"}:
        return True
    match = RUN.fullmatch(path)
    if not match:
        return False
    suffix = match[1] or ""
    if method == "POST":
        return suffix in {"approve", "security", "models", "languages", "feedback", "impact", "releases"} or bool(
            re.fullmatch(r"conflicts/[a-f0-9]{16}|feedback/[a-f0-9]{32}/review|releases/[a-f0-9]{32}/(?:approve|activate|rollback)", suffix)
        )
    if method == "DELETE":
        return bool(re.fullmatch(r"traces/[a-f0-9]{32}", suffix))
    return method == "GET" and (
        suffix in {"", "download", "conflicts", "traces", "security", "models", "languages", "feedback", "impact", "releases", "deployment"}
        or bool(re.fullmatch(r"artifact/[a-z_]+\.(?:json|md)|traces/[a-f0-9]{32}", suffix))
    )


def resolve(origin, local, key, id_):
    url = origin + "/_forge/requests/" + id_
    status, metadata, incoming = fetch(url, headers=key)
    if status in {404, 409}:
        return
    if status != 200:
        raise RuntimeError(f"Claim was rejected with HTTP {status}")
    method = metadata.get("x-forge-method", "")
    path = metadata.get("x-forge-path", "")
    if not allowed(method, path):
        status, outgoing_headers = 400, {}
        outgoing = b'{"detail":"Unsupported ForgeAI operation"}'
    else:
        try:
            status, outgoing_headers, outgoing = fetch(
                local + path, method=method, body=incoming if method == "POST" else None,
                headers={"Content-Type": metadata.get("Content-Type", "application/octet-stream")},
                timeout=65,
            )
        except OSError:
            status, outgoing_headers = 502, {}
            outgoing = b'{"detail":"The ForgeAI app is restarting or unavailable. Try again."}'
    headers = {**key, "x-forge-status": str(status), "Content-Type": outgoing_headers.get("Content-Type", "application/json")}
    disposition = outgoing_headers.get("Content-Disposition")
    if disposition:
        headers["Content-Disposition"] = disposition
    for attempt in range(3):
        try:
            result, _, _ = fetch(url, method="PUT", body=outgoing, headers=headers)
            if result in {204, 404}:
                return
            if result < 500:
                raise RuntimeError(f"Workspace response rejected with HTTP {result}")
        except OSError:
            if attempt == 2:
                raise
        time.sleep(0.5 * (attempt + 1))
    raise RuntimeError("The workspace response could not be delivered")


def run(origin, local, token):
    auth = {"OAI-Sites-Authorization": "Bearer " + token, "x-forge-runtime": "1"}
    previous = {}
    active = {}
    online = False
    last_activity = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        while True:
            now = time.monotonic()
            for id_, future in list(active.items()):
                if not future.done():
                    continue
                try:
                    future.result()
                except (OSError, RuntimeError) as error:
                    print(f"ForgeAI request error: {error}", file=sys.stderr, flush=True)
                previous[id_] = now
                del active[id_]
            for id_, ended in list(previous.items()):
                if now - ended > 100:
                    del previous[id_]

            try:
                status, _, body = fetch(origin + "/_forge/queue", headers=auth, timeout=8)
                if status in {401, 403}:
                    raise SystemExit("The Site rejected its workspace service credential.")
                if status != 200:
                    raise RuntimeError(f"Queue returned HTTP {status}")
                ids = json.loads(body)["requests"]
                if not online:
                    print("ForgeAI workspace connected to the private live Site.", flush=True)
                    online = True
                for id_ in ids:
                    if UUID.fullmatch(id_) and id_ not in active and id_ not in previous and len(active) < 8:
                        active[id_] = pool.submit(resolve, origin, local, auth, id_)
                        last_activity = now
            except (OSError, ValueError, RuntimeError) as error:
                if online:
                    print(f"ForgeAI connection interrupted: {error}", file=sys.stderr, flush=True)
                online = False
            time.sleep(0.7 if active or now - last_activity < 55 else 2.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site")
    parser.add_argument("--port", type=int, default=8765, choices=range(1, 65536), metavar="1–65535")
    args = parser.parse_args()
    url = urllib.parse.urlsplit(args.site)
    if url.scheme != "https" or not url.hostname or not url.hostname.endswith(".chatgpt.site") or url.netloc != url.hostname:
        parser.error("Use the HTTPS origin of the private ChatGPT Site.")
    token = getpass.getpass("Site service credential: ")
    if not token:
        parser.error("The Site service credential is required.")
    try:
        run(f"https://{url.hostname}", f"http://127.0.0.1:{args.port}", token)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
