"""Opt-in local authentication and workspace principals."""

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from threading import RLock
import time

COOKIE = "forgeai_session"
SESSION_SECONDS = 8 * 60 * 60
ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")
ROLES = {"admin", "reviewer", "user"}
LOCK = RLock()
SESSIONS = {}
ATTEMPTS = {}


@dataclass(frozen=True)
class Principal:
    name: str
    workspace: str
    role: str
    agents: frozenset | None = None
    documents: frozenset | None = None
    can_approve: bool = False

    @property
    def staff(self):
        return self.role in {"admin", "reviewer"}

    def allows_documents(self, names):
        return self.documents is None or set(names) <= self.documents


LOCAL = Principal("local", "local", "admin", can_approve=True)


def password_hash(password):
    if not 8 <= len(password) <= 256:
        raise ValueError("Passwords need between 8 and 256 characters.")
    salt = secrets.token_hex(16)
    rounds = 310_000
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), rounds).hex()
    return f"pbkdf2_sha256${rounds}${salt}${value}"


def verify_password(password, encoded):
    try:
        scheme, rounds, salt, expected = encoded.split("$")
        rounds = int(rounds)
        if scheme != "pbkdf2_sha256" or not 100_000 <= rounds <= 1_000_000:
            return False
        salt = bytes.fromhex(salt)
        if len(salt) < 16 or len(expected) != 64 or len(password) > 256:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError, TypeError):
        return False


def users():
    config = os.getenv("FORGE_AUTH_CONFIG")
    if not config:
        return None
    data = json.loads(Path(config).read_text(encoding="utf-8"))
    if not isinstance(data.get("users"), dict) or not data["users"]:
        raise ValueError("The authorization configuration needs at least one user.")
    return data["users"]


def user_principal(name, row):
    identifiers = (name, row["workspace"])
    if any(not ID.fullmatch(value) or value in {".", ".."} for value in identifiers) or row["role"] not in ROLES:
        raise ValueError("Invalid user, workspace, or role in authorization configuration.")
    agents = row.get("agents")
    documents = row.get("documents")
    return Principal(name, row["workspace"], row["role"], frozenset(agents) if agents is not None else None,
                     frozenset(documents) if documents is not None else None, bool(row.get("can_approve")))


def login(name, password, origin):
    mappings = users()
    if mappings is None:
        raise ValueError("Authentication is disabled in this local workspace.")
    now = time.monotonic()
    with LOCK:
        for key, (_, until) in list(ATTEMPTS.items()):
            if until <= now:
                del ATTEMPTS[key]
        attempts, expiry = ATTEMPTS.get(origin, (0, now + 300))
        if attempts >= 8:
            return None
        ATTEMPTS[origin] = (attempts + 1, expiry)
    row = mappings.get(name, {})
    if not verify_password(password, row.get("password_hash", "")):
        return None
    user_principal(name, row)
    token = secrets.token_urlsafe(32)
    with LOCK:
        ATTEMPTS.pop(origin, None)
        for key, (_, until, _) in list(SESSIONS.items()):
            if until <= now:
                del SESSIONS[key]
        SESSIONS[digest(token)] = (name, now + SESSION_SECONDS, row["password_hash"])
    return token


def digest(token):
    return hashlib.sha256(token.encode()).digest()


def current(token):
    mappings = users()
    if mappings is None:
        return LOCAL
    if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    with LOCK:
        entry = SESSIONS.get(digest(token))
    if not entry:
        return None
    name, expires, credential = entry
    row = mappings.get(name, {})
    if expires < time.monotonic() or row.get("password_hash") != credential:
        logout(token)
        return None
    return user_principal(name, row)


def logout(token):
    if token:
        with LOCK:
            SESSIONS.pop(digest(token), None)
