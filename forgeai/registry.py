"""Small, explicitly authorized set of typed runtime tools."""

import ast
import json
import math
import operator
import re
from datetime import date
from urllib.parse import urlencode
from urllib.request import urlopen

from .corpus import terms

WEATHER_NETWORK_REQUIRED = "Live weather requires a network-enabled workspace."

REGISTRY = {
    "csv_lookup": {"name": "CSV lookup", "description": "Find matching rows in uploaded CSV tables.", "example": "Look up AF-310"},
    "calculator": {"name": "Calculator", "description": "Evaluate arithmetic expressions locally.", "example": "Calculate 12 * 4.5"},
    "current_date": {"name": "Current date", "description": "Read the host's local calendar date.", "example": "What is today's date?"},
    "weather": {"name": "Open-Meteo", "description": "Read current conditions at supplied coordinates.", "example": "Weather at 18.94, 72.83"},
}


def select_tools(brief, corpus):
    text = brief.casefold()
    patterns = {
        "csv_lookup": r"\b(csv|catalog(?:ue)?|sku|part number|spreadsheet|look up|table lookup)\b",
        "calculator": r"\b(calculat\w*|arithmetic|multiply|compute|unit price|order totals?)\b",
        "current_date": r"\b(current date|today.s date|date today|calendar date)\b",
        "weather": r"\b(current weather|live weather|weather forecast|weather conditions|open.meteo)\b",
    }
    enabled = []
    for key, pattern in patterns.items():
        sentences = re.split(r"[.;\n]", text)
        matches = [s for s in sentences if re.search(pattern, s)]
        allowed = any(not re.search(r"\b(no|not|never|refuse|exclude|without|do not|don.t)\b.{0,36}" + pattern, s) for s in matches)
        if allowed and (key != "csv_lookup" or any(p["cells"] for p in corpus.passages)):
            enabled.append(key)
    return enabled


def calculate(expression):
    if len(expression) > 100 or not re.fullmatch(r"[\d. ()+*/%\-]+", expression):
        raise ValueError("Use numbers, parentheses, and arithmetic operators.")
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod}

    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            result = node.value
        elif isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
            value = evaluate(node.operand)
            result = value if isinstance(node.op, ast.UAdd) else -value
        elif isinstance(node, ast.BinOp) and type(node.op) in operations:
            result = operations[type(node.op)](evaluate(node.left), evaluate(node.right))
        else:
            raise ValueError("Only basic arithmetic is supported.")
        if not math.isfinite(result) or abs(result) > 10 ** 15:
            raise ValueError("Result exceeds the supported numeric range.")
        return result

    return evaluate(ast.parse(expression, mode="eval").body)


def dispatch(question, enabled, index, permit_network=True, accepted_ids=None):
    text = question.strip().rstrip("?")
    if "calculator" in enabled and (match := re.match(r"^(?:calculate|compute|what is)\s+([\d. ()+*/%\-]+)$", text, re.I)):
        try:
            result = calculate(match[1].strip())
        except (SyntaxError, ArithmeticError, ValueError) as exc:
            return "calculator", f"Calculation unavailable. {exc}", [], "error"
        return "calculator", f"{match[1].strip()} = {result:,}", [], "answered"
    if "current_date" in enabled and re.search(r"\b(today.s date|current date|date today)\b", text, re.I):
        return "current_date", f"Today's local date is {date.today().isoformat()}.", [], "answered"
    if "weather" in enabled and re.search(r"^(?:current |live )?weather\b", text, re.I):
        match = re.fullmatch(r"(?:current |live )?weather(?:\s+at)?\s+(-?\d{1,3}(?:\.\d+)?),\s*(-?\d{1,3}(?:\.\d+)?)", text, re.I)
        if not match:
            return "weather", "Enter latitude and longitude, for example: Weather at 18.94, 72.83.", [], "clarify"
        lat, lon = map(float, match.groups())
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return "weather", "Latitude must be in ±90° and longitude in ±180°.", [], "clarify"
        if not permit_network:
            return "weather", WEATHER_NETWORK_REQUIRED, [], "error"
        params = urlencode({"latitude": lat, "longitude": lon, "current": "temperature_2m,wind_speed_10m", "timezone": "auto"})
        try:
            with urlopen("https://api.open-meteo.com/v1/forecast?" + params, timeout=6) as response:
                current = json.load(response)["current"]
            value = f"Open-Meteo reports {current['temperature_2m']} °C and wind at {current['wind_speed_10m']} km/h at {current['time']} (local time)."
            return "weather", value, [], "answered"
        except (OSError, ValueError, KeyError):
            return "weather", "Open-Meteo did not return current conditions. Try again later.", [], "error"
    if "csv_lookup" in enabled and (match := re.match(r"^(?:look up|lookup|find sku|find part)\s+(.+)$", text, re.I)):
        query = match[1]
        wanted = set(terms(query))
        if not wanted:
            return "csv_lookup", "Enter a SKU, part number, or searchable product name.", [], "clarify"
        rows = {p["id"] for p in index.corpus.passages if p["cells"]}
        if accepted_ids is not None:
            rows &= accepted_ids
        results = index.search(query, 3, rows)
        passages = [p for _, coverage, p in results if coverage == 1]
        if passages:
            return "csv_lookup", "\n".join(p["text"] for p in passages), passages, "answered"
        return "csv_lookup", "I couldn't find a matching row in the supplied CSV files.", [], "refused"
    return None
