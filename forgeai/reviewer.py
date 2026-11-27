"""Public sample access. Owner workspaces and mutations stay behind authentication."""

from threading import BoundedSemaphore

from .privacy import Principal


CHAT_SLOTS = BoundedSemaphore(3)


def principal(demos):
    return Principal("public-reviewer", "public-review-demo", "reviewer", frozenset(demos))


def permits(method, path, run_match, demos):
    if method == "POST":
        return path == "/api/chat"
    if method not in {"GET", "HEAD"}:
        return False
    if not path.startswith("/api/"):
        return True
    if path in {"/api/session", "/api/health", "/api/workspace", "/api/dashboard", "/api/runs"}:
        return True
    return bool(run_match and run_match[1] in demos and (
        run_match[2] in {None, "/download", "/deployment", "/conflicts", "/security", "/languages", "/models"}
        or (run_match[2] or "").startswith("/artifact/")
    ))
