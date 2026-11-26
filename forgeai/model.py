"""Small OpenAI-compatible local-model adapter with usage and failure accounting."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "http://127.0.0.1:8089/v1"
DEFAULT_MODEL = "qwen2.5-0.5b"


class LocalModel:
    def __init__(self, enabled=True, token_budget=12_000):
        self.enabled = enabled
        self.url = os.getenv("FORGE_MODEL_URL", DEFAULT_URL).rstrip("/")
        self.name = os.getenv("FORGE_MODEL_NAME", DEFAULT_MODEL)
        self.token_budget = token_budget
        self.calls = []
        self.tokens = 0
        self.unavailable = False

    def probe(self):
        if not self.enabled:
            return False
        try:
            with urlopen(self.url + "/models", timeout=1.5) as response:
                return bool(json.load(response).get("data"))
        except (OSError, ValueError):
            return False

    def ask(self, stage, payload, max_tokens=240, system=None):
        if not self.enabled or self.unavailable:
            return {}
        input_text = json.dumps(payload, ensure_ascii=False)
        instruction = system or (ROOT / "prompts" / f"{stage}.txt").read_text(encoding="utf-8")
        token_bound = len((input_text + instruction).encode("utf-8")) + max_tokens + 64
        if self.tokens + token_bound > self.token_budget:
            self.calls.append({"stage": stage, "status": "budget_skipped", "tokens": 0})
            return {}
        body = {
            "model": self.name,
            "messages": [{"role": "system", "content": instruction}, {"role": "user", "content": input_text}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "seed": 42,
            "max_tokens": max_tokens,
        }
        request = Request(
            self.url + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=40) as response:
                result = json.load(response)
            used = int(result.get("usage", {}).get("total_tokens", 0))
            self.tokens += used or token_bound
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("expected a JSON object")
            self.calls.append({"stage": stage, "status": "ok", "tokens": used, "output": parsed})
            return parsed
        except (OSError, HTTPError, URLError) as exc:
            self.unavailable = True
            self.calls.append({"stage": stage, "status": "unavailable", "detail": str(exc), "tokens": 0})
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            self.calls.append({"stage": stage, "status": "invalid_json", "detail": str(exc), "tokens": locals().get("used", 0)})
        return {}

    def summary(self):
        successful = sum(call["status"] == "ok" for call in self.calls)
        return {
            "name": self.name,
            "mode": "local_model" if successful else "deterministic",
            "tokens": self.tokens,
            "budget": self.token_budget,
            "calls": self.calls,
        }
