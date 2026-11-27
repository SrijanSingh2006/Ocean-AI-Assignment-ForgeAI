"""Optional OCR for image sources and PDF pages without a text layer."""

from collections import defaultdict
import csv
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory


def enabled():
    return os.getenv("FORGE_OCR", "0") == "1"


def available():
    return bool(shutil.which("tesseract"))


def image_blocks(path):
    language = os.getenv("FORGE_OCR_LANGUAGES", "eng")
    if not re.fullmatch(r"[a-z]{3}(?:\+[a-z]{3}){0,4}", language):
        raise ValueError("Use installed Tesseract language codes in FORGE_OCR_LANGUAGES.")
    if not available():
        raise ValueError("Tesseract is unavailable.")
    output = subprocess.run(
        ["tesseract", str(path), "stdout", "-l", language, "tsv"], capture_output=True,
        text=True, encoding="utf-8", check=True, timeout=20,
    )
    groups = defaultdict(list)
    for row in csv.DictReader(io.StringIO(output.stdout), delimiter="\t"):
        text = (row.get("text") or "").strip()
        if row.get("level") == "5" and text:
            groups[(row["block_num"], row["par_num"])].append(row)
    for block in groups.values():
        left = min(int(row["left"]) for row in block)
        top = min(int(row["top"]) for row in block)
        right = max(int(row["left"]) + int(row["width"]) for row in block)
        bottom = max(int(row["top"]) + int(row["height"]) for row in block)
        score = min(100.0, max(0.0, sum(float(row["conf"]) for row in block) / len(block)))
        yield " ".join(row["text"].strip() for row in block), {
            "method": "tesseract_ocr", "confidence": round(score / 100, 3),
            "box": [left, top, right, bottom], "coordinate_unit": "pixels",
        }


def pdf_page_blocks(path, page):
    if not shutil.which("pdftoppm"):
        raise ValueError("pdftoppm is required to rasterize scanned PDFs.")
    with TemporaryDirectory() as folder:
        output = Path(folder) / "page"
        subprocess.run(
            ["pdftoppm", "-f", str(page), "-l", str(page), "-r", "180",
             "-png", "-singlefile", str(path), str(output)],
            capture_output=True, check=True, timeout=15,
        )
        yield from image_blocks(output.with_suffix(".png"))
