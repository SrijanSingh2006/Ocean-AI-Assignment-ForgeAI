"""Optional OpenAI-compatible embedding retrieval for configured multilingual models."""

import json
import math
import os
from urllib.request import Request, urlopen


class Embeddings:
    def __init__(self, url, model, api_key=None):
        self.url = url.rstrip("/")
        self.model = model
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def encode(self, texts):
        request = Request(self.url + "/embeddings", headers=self.headers,
                          data=json.dumps({"model": self.model, "input": texts}).encode())
        with urlopen(request, timeout=5) as response:
            rows = sorted(json.load(response)["data"], key=lambda row: row["index"])
        if [row["index"] for row in rows] != list(range(len(texts))):
            raise ValueError("Embedding response is incomplete.")
        vectors = []
        for row in rows:
            vector = row["embedding"]
            norm = math.sqrt(sum(value * value for value in vector))
            if not norm or not math.isfinite(norm):
                raise ValueError("Provider returned an invalid embedding.")
            vectors.append([value / norm for value in vector])
        if len({len(vector) for vector in vectors}) != 1:
            raise ValueError("Embedding dimensions differ.")
        return vectors

    def search(self, query, corpus, eligible, limit=3):
        passages = [p for p in corpus.passages if eligible is None or p["id"] in eligible]
        if not passages or len(passages) > 128:
            return []
        try:
            vectors = self.encode([query] + [p["text"][:1400] for p in passages])
        except (OSError, ValueError, KeyError, TypeError, OverflowError, RuntimeError):
            return []
        match = [(similarity, similarity, passage) for vector, passage in zip(vectors[1:], passages)
                 if (similarity := min(1.0, sum(a * b for a, b in zip(vector, vectors[0])))) >= 0.72]
        return sorted(match, key=lambda hit: (-hit[0], hit[2]["id"]))[:limit]


def configured_embeddings():
    url, name = os.getenv("FORGE_EMBEDDING_URL"), os.getenv("FORGE_EMBEDDING_MODEL")
    if url and name:
        return Embeddings(url, name, os.getenv("FORGE_EMBEDDING_API_KEY"))
    if folder := os.getenv("FORGE_E5_PATH"):
        from .local_language import local_embeddings
        return local_embeddings(folder)
    return None
