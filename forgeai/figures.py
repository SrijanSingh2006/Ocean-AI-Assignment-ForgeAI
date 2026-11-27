"""Conservative extraction for labeled, vertical bar charts in raster figures."""

from collections import deque
import csv
import io
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


def enabled():
    return os.getenv("FORGE_FIGURES") == "1"


def rectangles(image):
    pixels = image.load()
    width, height = image.size
    colored = set()
    for y in range(height):
        for x in range(width):
            rgb = pixels[x, y]
            if max(rgb) - min(rgb) >= 65 and max(rgb) >= 80:
                colored.add((x, y))
    bars = []
    while colored:
        start = colored.pop()
        left = right = start[0]
        top = bottom = start[1]
        queue = deque([start])
        count = 0
        while queue:
            x, y = queue.popleft()
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            count += 1
            for candidate in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if candidate in colored:
                    colored.remove(candidate)
                    queue.append(candidate)
        w, h = right - left + 1, bottom - top + 1
        if w >= width * 0.025 and h >= height * 0.045 and count / (w * h) >= 0.82:
            bars.append((left, top, right, bottom))
    return sorted(bars)


def figure_words(image):
    with TemporaryDirectory() as folder:
        source = Path(folder) / "figure.png"
        image.save(source)
        data = subprocess.run(["tesseract", str(source), "stdout", "--psm", "11", "tsv"],
                              capture_output=True, text=True, encoding="utf-8", check=True, timeout=15)
    words = []
    for row in csv.DictReader(io.StringIO(data.stdout), delimiter="\t"):
        if row["level"] == "5" and row["text"].strip() and float(row["conf"]) >= 60:
            x, y = int(row["left"]), int(row["top"])
            w, h = int(row["width"]), int(row["height"])
            words.append((x + w / 2, y, y + h, row["text"].strip()))
    return words


def isolated_value(image, left, right, top):
    area = image.crop((max(0, left - 4), max(0, top - 58), min(image.width, right + 4), top))
    with TemporaryDirectory() as folder:
        path = Path(folder) / "value.png"
        area.save(path)
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789."],
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=6,
        ).stdout.strip()
    return {result} if re.fullmatch(r"\d{1,7}(?:\.\d{1,3})?", result) else set()


def extract_bar_chart(blob):
    from PIL import Image

    with Image.open(io.BytesIO(blob)) as source:
        width, height = source.size
        if width < 300 or height < 180 or width * height > 12_000_000:
            return None
        source.thumbnail((1050, 1050))
        image = source.convert("RGB")
    bars = rectangles(image)
    if not 2 <= len(bars) <= 12 or max(box[3] for box in bars) - min(box[3] for box in bars) > 4:
        return None
    words = figure_words(image)
    labels, values, scales = [], [], []
    for left, top, right, base in bars:
        center = (left + right) / 2
        near = [word for word in words if abs(word[0] - center) <= max(12, (right - left) / 2)]
        names = {word[3] for word in near if base < word[1] <= base + 75 and re.fullmatch(r"[A-Za-z][\w-]{1,24}", word[3])}
        printed = {word[3] for word in near if 0 <= top - word[2] <= 60 and re.fullmatch(r"\d{1,7}(?:\.\d{1,3})?", word[3])}
        if not printed:
            printed = isolated_value(image, left, right, top)
        if len(names) != 1 or len(printed) != 1:
            return None
        value = float(printed.pop())
        if value <= 0:
            return None
        labels.append(names.pop())
        values.append(value)
        scales.append((base - top + 1) / value)
    if len(set(labels)) != len(labels) or max(scales) / min(scales) > 1.14:
        return None
    def region(value):
        return ", ".join(label for label, metric in zip(labels, values) if metric == value)
    maximum, minimum = max(values), min(values)
    change = values[-1] - values[0]
    movement = "increased" if change > 0 else "decreased" if change < 0 else "stayed level"
    text = "Labeled vertical bar chart. " + " · ".join(f"{label}: {value:g}" for label, value in zip(labels, values))
    text += f". Highest (maximum): {region(maximum)} at {maximum:g}. Lowest (minimum): {region(minimum)} at {minimum:g}."
    text += f" Left-to-right trend: the final value {movement} by {abs(change):g} from {labels[0]} to {labels[-1]}."
    return text, {
        "method": "shape_and_ocr", "kind": "bar_chart", "confidence": 0.9,
        "values": [{"label": label, "value": value} for label, value in zip(labels, values)],
        "boxes": bars, "coordinate_unit": "analysis pixels", "analysis_size": image.size,
        "verification": "Printed values agreed with relative bar heights and a common baseline.",
    }
