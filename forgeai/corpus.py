"""Read source files and build a reproducible sparse document index."""

import csv
import io
import math
import re
import subprocess
import unicodedata

from .multilingual import detect_language
from .model import LatencyBudgetExceeded
from . import figures, ocr
from collections import Counter
from pathlib import Path

SUPPORTED = {".md", ".txt", ".csv", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}
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
    normalized = unicodedata.normalize("NFC", text.casefold())
    if any(unicodedata.category(char).startswith("M") for char in normalized):
        words = []
        word = ""
        for index, char in enumerate(normalized):
            if char.isalnum() or (word and unicodedata.category(char).startswith("M")):
                word += char
            elif char in ".-" and word and index + 1 < len(normalized) and normalized[index + 1].isalnum():
                word += char
            elif word:
                words.append(word)
                word = ""
        if word:
            words.append(word)
    else:
        words = re.findall(r"[^\W_]+(?:[.-][^\W_]+)*", normalized)
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


def read_blocks(path, check_time=None):
    def recognized(image_or_pdf, locator, heading=None):
        heading = heading or title_for(name)
        try:
            blocks = list(image_or_pdf)
        except (OSError, subprocess.SubprocessError, ValueError):
            yield heading, "", locator, {}, {"warning": "OCR failed or the configured engine is unavailable."}
            return
        if not blocks:
            yield heading, "", locator, {}, {"warning": "OCR found no readable text."}
        for index, (body, details) in enumerate(blocks, 1):
            yield heading, body, f"{locator}, OCR block {index}", {}, details

    name = path.name
    suffix = path.suffix.lower()
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file exceeds 10 MB")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        for page_number, page in enumerate(reader.pages, 1):
            if check_time:
                check_time()
            text = page.extract_text() or ""
            locator = f"page {page_number}"
            if text.strip():
                yield from split_text(text, title_for(name), locator)
            elif ocr.enabled():
                yield from recognized(ocr.pdf_page_blocks(path, page_number), locator)
            if figures.enabled():
                for figure_number, key in enumerate(list(page.images.keys())[:8], 1):
                    if check_time:
                        check_time()
                    figure_locator = f"{locator}, figure {figure_number}"
                    try:
                        image = page.images[key]
                        result = figures.extract_bar_chart(image.data) if len(image.data) <= MAX_FILE_BYTES else None
                    except (OSError, subprocess.SubprocessError, ValueError, ImportError):
                        result = None
                    if result:
                        body, extraction = result
                        yield f"{title_for(name)} chart", body, figure_locator, {}, extraction
                    else:
                        yield title_for(name), "", figure_locator, {}, {"warning": "Figure values need manual verification."}
    elif suffix in {".png", ".jpg", ".jpeg"}:
        if ocr.enabled():
            yield from recognized(ocr.image_blocks(path), "image")
        else:
            yield title_for(name), "", "image", {}, {"warning": "Enable FORGE_OCR to read image sources."}
    elif suffix == ".docx":
        from docx import Document
        from docx.opc.constants import RELATIONSHIP_TYPE
        from docx.oxml.ns import qn
        from docx.text.paragraph import Paragraph

        doc = Document(path)
        heading = title_for(name)
        for number, entry in enumerate(doc.iter_inner_content(), 1):
            if check_time:
                check_time()
            if isinstance(entry, Paragraph):
                value = clean(entry.text)
                if value and entry.style and entry.style.name.startswith(("Heading", "Title")):
                    heading = value
                elif value:
                    yield heading, value, f"block {number}", {}
                if ocr.enabled():
                    for image_number, blip in enumerate(entry._element.xpath(".//a:blip"), 1):
                        relation = entry.part.rels.get(blip.get(qn("r:embed")))
                        if not relation or relation.is_external or relation.reltype != RELATIONSHIP_TYPE.IMAGE:
                            continue
                        if check_time:
                            check_time()
                        blob = relation.target_part.blob
                        locator = f"block {number}, image {image_number}"
                        if len(blob) > MAX_FILE_BYTES:
                            yield heading, "", locator, {}, {"warning": "An embedded image exceeds the OCR size limit."}
                            continue
                        yield from recognized(ocr.embedded_image_blocks(blob), locator, heading)
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
    def load(cls, folder, size=135, overlap=24, check_time=None):
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
            if check_time:
                check_time()
            provenance = path.relative_to(root).as_posix()
            try:
                blocks = list(read_blocks(path, check_time))
            except LatencyBudgetExceeded:
                raise
            except Exception as exc:
                warnings.append(f"{provenance}: {exc}")
                continue
            first = len(passages)
            for block_number, block in enumerate(blocks, 1):
                if check_time:
                    check_time()
                heading, body, locator, cells = block[:4]
                extraction = block[4] if len(block) > 4 else None
                if extraction and "warning" in extraction:
                    warnings.append(f"{provenance} {locator} · {extraction['warning']}")
                if extraction and extraction.get("confidence", 1) < 0.50:
                    warnings.append(f"{provenance} {locator} · low OCR confidence.")
                if not terms(body) or len(body) < 5:
                    continue
                segments = [body] if cells else windows(body, size, overlap)
                for segment_number, segment in enumerate(segments, 1):
                    passages.append({
                        "id": f"d{file_number:02}p{block_number:03}c{segment_number:02}",
                        "document": provenance, "title": title_for(path.name),
                        "heading": heading, "locator": f"{locator}, block {block_number}" if locator == "text" else locator,
                        "text": segment, "cells": cells, "language": detect_language(segment),
                    })
                    if extraction:
                        passages[-1]["extraction"] = extraction
            added = len(passages) - first
            if added:
                languages = sorted({passage["language"] for passage in passages[first:]})
                documents.append({"name": provenance, "format": path.suffix[1:].upper(), "passages": added,
                                  "languages": languages})
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
