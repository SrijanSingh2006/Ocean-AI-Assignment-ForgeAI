"""Language identification and optional evidence-preserving translation."""

from collections import Counter
import os
import re
import unicodedata

from .model import LocalModel

LANGUAGES = {"en": "English", "hi": "Hindi", "ta": "Tamil"}
DEVANAGARI = re.compile(r"[\u0900-\u097f]")
TAMIL = re.compile(r"[\u0b80-\u0bff]")
LATIN = re.compile(r"[A-Za-z]{2,}")
ROMAN_HINDI = {"kya", "kitna", "kitne", "kaise", "chutti", "chhutti", "batao", "hain", "mujhe"}
ROMAN_TAMIL = {"enna", "eppadi", "evvalavu", "viduppu", "sollunga", "enakku"}
TOKEN = re.compile(r"\d+(?:[.,:/-]\d+)*|\b[A-Z]{2,}(?:-\d+)?\b")


def detect_language(text):
    words = {word.casefold() for word in LATIN.findall(text)}
    script = "ta" if TAMIL.search(text) else "hi" if DEVANAGARI.search(text) else None
    if script:
        return f"{script}-en" if words else script
    if words & ROMAN_HINDI:
        return "hi-Latn"
    if words & ROMAN_TAMIL:
        return "ta-Latn"
    return "en"


def language_model():
    if folder := os.getenv("FORGE_NLLB_PATH"):
        from .local_language import LocalTranslation, local_embeddings
        embedding_path = os.getenv("FORGE_E5_PATH")
        return LocalTranslation(folder, local_embeddings(embedding_path) if embedding_path else None)
    name = os.getenv("FORGE_LANGUAGE_MODEL_NAME")
    if not name:
        return None
    return LocalModel(url=os.getenv("FORGE_LANGUAGE_MODEL_URL"), name=name,
                      api_key=os.getenv("FORGE_LANGUAGE_MODEL_API_KEY"))


def comparable_symbols(text):
    canonical = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    return Counter(TOKEN.findall(canonical))


def translate(text, target, model):
    if not model:
        return None
    output = model.ask("translate", {"text": text, "target_language": LANGUAGES[target]}, max_tokens=400).get("text")
    if not isinstance(output, str) or not 0 < len(output.strip()) <= 3000:
        return None
    translated = output.strip()
    if detect_language(translated).split("-")[0] != target:
        return None
    if comparable_symbols(text) != comparable_symbols(translated):
        return None
    return translated


def translated_answer(answer, source, target, model):
    if source == target:
        return answer
    translation = translate(answer, target, model)
    if not translation:
        return None
    roundtrip = translate(translation, source, model)
    if not roundtrip:
        return None

    def tokens(text):
        return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold())

    reviewed = tokens(roundtrip) == tokens(answer)
    if not reviewed and (equivalent := getattr(type(model), "equivalent", None)):
        reviewed = equivalent(model, answer, roundtrip)
    return translation if reviewed else None
