"""Read source files and build a reproducible sparse document index."""

import csv
import io
import math
import re
from collections import Counter
from pathlib import Path

SUPPORTED = {".md", ".txt", ".csv", ".pdf", ".docx"}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 30
STOP = set("""
a an and are as at be by can could did do does for from give had has have how i in is it its
me my of on or our please say should tell than that the their them there these they this to
was were what when where which who will with would you your about according document documented
find described known need wants want must help provide covers question questions answer
answers available details handle include assistant users user staff using use only source sources
separately information policy policies guide handbook can cannot answerable explain
""".split())


def clean(text):
    return " ".join(text.split())


def terms(text):
    words = re.findall(r"[^\W_]+(?:[.-][^\W_]+)*", text.casefold())
    return [
        word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word
        for word in words if word not in STOP and (len(word) > 1 or word.isdigit())
    ]


def title_for(name):
    return clean(re.sub(r"[_-]", " ", Path(name).stem)).title()


def split_text(text, base, locator):
    heading = base
    buffer = []
    blocks = []

    def flush():
        if buffer:
            body = clean(" ".join(buffer))
            if body:
                blocks.append((heading, body, locator, {}))
            buffer.clear()

    for line in text.splitlines():
        candidate = line.strip()
        match = re.match(r"^#{1,6}\s+(.+)$", candidate)
        if match:
            flush()
            heading = clean(match[1].strip("# "))
        elif not candidate:
            flush()
        else:
            buffer.append(candidate)
    flush()
    return blocks


def read_blocks(path):
    name = path.name
    suffix = path.suffix.lower()
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file exceeds 10 MB")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        for page_number, page in enumerate(reader.pages, 1):
            yield from split_text(page.extract_text() or "", title_for(name), f"page {page_number}")
    elif suffix == ".docx":
        from docx import Document
        from docx.text.paragraph import Paragraph

        doc = Document(path)
        heading = title_for(name)
        for number, entry in enumerate(doc.iter_inner_content(), 1):
            if isinstance(entry, Paragraph):
                value = clean(entry.text)
                if not value:
                    continue
                if entry.style and entry.style.name.startswith(("Heading", "Title")):
                    heading = value
                    continue
                yield heading, value, f"block {number}", {}
            else:
                rows = [[clean(cell.text) for cell in row.cells] for row in entry.rows]
                if len(rows) > 1:
                    for row_number, row in enumerate(rows[1:], 2):
                        value = " · ".join(f"{key}: {val}" for key, val in zip(rows[0], row) if val)
                        if value:
                            yield heading, value, f"table {number}, row {row_number}", {}
                elif rows and any(rows[0]):
                    yield heading, " · ".join(filter(None, rows[0])), f"table {number}", {}
    else:
        value = path.read_text(encoding="utf-8-sig")
        if suffix == ".csv":
            sample = value[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = "excel"
            for number, row in enumerate(csv.DictReader(io.StringIO(value), dialect=dialect), 2):
                cells = {clean(k): clean(v) for k, v in row.items() if k and isinstance(v, str) and v.strip()}
                if not cells:
                    continue
                first = list(cells.values())[:2]
                heading = " ".join(first)
                body = " · ".join(f"{key}: {val}" for key, val in cells.items())
                yield heading, body, f"row {number}", cells
        else:
            yield from split_text(value, title_for(name), "text")


def windows(text, size, overlap):
    words = text.split()
    start = 0
    while start < len(words):
        yield " ".join(words[start:start + size])
        if start + size >= len(words):
            break
        start += size - overlap


class Corpus:
    def __init__(self, passages, documents, warnings=None):
        self.passages = passages
        self.documents = documents
        self.warnings = warnings or []
        self.by_id = {p["id"]: p for p in passages}

    @classmethod
    def load(cls, folder, size=135, overlap=24):
        if not 0 <= overlap < size <= 1000:
            raise ValueError("Chunking must satisfy 0 <= overlap < size <= 1000")
        root = Path(folder)
        if not root.is_dir():
            raise ValueError(f"Document folder does not exist: {folder}")
        passages, documents, warnings = [], [], []
        paths = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)
        if len(paths) > MAX_FILES:
            raise ValueError(f"Use at most {MAX_FILES} supported documents per run")
        for file_number, path in enumerate(paths, 1):
            provenance = path.relative_to(root).as_posix()
            try:
                blocks = list(read_blocks(path))
            except Exception as exc:
                warnings.append(f"{provenance}: {exc}")
                continue
            first = len(passages)
            for block_number, (heading, body, locator, cells) in enumerate(blocks, 1):
                if not terms(body) or len(body) < 5:
                    continue
                segments = [body] if cells else windows(body, size, overlap)
                for segment_number, segment in enumerate(segments, 1):
                    passages.append({
                        "id": f"d{file_number:02}p{block_number:03}c{segment_number:02}",
                        "document": provenance, "title": title_for(path.name),
                        "heading": heading, "locator": f"{locator}, block {block_number}" if locator == "text" else locator,
                        "text": segment, "cells": cells,
                    })
            added = len(passages) - first
            if added:
                documents.append({"name": provenance, "format": path.suffix[1:].upper(), "passages": added})
            else:
                warnings.append(f"{provenance}: no extractable text; scanned PDF pages need OCR first.")
        if not passages:
            raise ValueError("No readable passages. Add a text-based PDF, DOCX, CSV, Markdown, or TXT file.")
        return cls(passages, documents, warnings)


class Index:
    def __init__(self, corpus, heading_weight=0.9):
        self.corpus = corpus
        self.heading_weight = heading_weight
        self.body = [Counter(terms(p["text"])) for p in corpus.passages]
        self.head = [set(terms(p["heading"] + " " + p["title"])) for p in corpus.passages]
        frequency = Counter(word for body, head in zip(self.body, self.head) for word in set(body) | head)
        total = len(self.body)
        self.idf = {word: math.log(1 + (total - count + 0.5) / (count + 0.5)) for word, count in frequency.items()}
        self.average = max(1, sum(map(Counter.total, self.body)) / total)

    def search(self, query, limit=8, accepted_ids=None):
        words = set(terms(query))
        if not words:
            return []
        results = []
        for passage, counts, head in zip(self.corpus.passages, self.body, self.head):
            if accepted_ids is not None and passage["id"] not in accepted_ids:
                continue
            hits = words.intersection(set(counts) | head)
            if not hits:
                continue
            length = counts.total()
            score = 0.0
            for word in sorted(hits):
                freq = counts[word]
                norm = freq + 1.2 * (0.25 + 0.75 * length / self.average)
                weight = 2.2 * freq / norm
                if word in head:
                    weight += self.heading_weight
                score += self.idf[word] * weight
            coverage = len(hits) / len(words)
            results.append((score, coverage, passage))
        return sorted(results, key=lambda item: (-item[0], -item[1], item[2]["id"]))[:limit]


def least_duplicate(passages):
    seen = set()
    distinct = []
    for passage in passages:
        key = clean(passage["text"]).casefold()
        if key not in seen:
            seen.add(key)
            distinct.append(passage)
    return distinct
