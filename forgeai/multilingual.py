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
ROMAN_HINDI = {"kya", "kitna", "kitni", "kitne", "kaise", "chutti", "chhutti", "batao", "mujhe"}
ROMAN_TAMIL = {"enna", "eppadi", "evvalavu", "ethanai", "eththanai", "viduppu", "sollunga", "enakku"}
TOKEN = re.compile(r"\d+(?:[.,:/-]\d+)*|\b[A-Z]{2,}(?:-\d+)?\b")
ROMAN_QUERY_WORDS = {
    "hi-Latn": {
        "kitna": "how much", "kitni": "how much", "kitne": "how many", "kya": "what", "kab": "when",
        "kaise": "how", "chutti": "leave", "chhutti": "leave", "din": "days", "saal": "year",
        "milta": "receive", "milti": "receive", "milte": "receive", "hai": "is", "hain": "are",
        "mujhe": "me", "batao": "tell", "ko": "to", "ke": "of", "liye": "for", "mein": "in",
    },
    "ta-Latn": {
        "evvalavu": "how much", "ethanai": "how many", "eththanai": "how many", "enna": "what",
        "eppadi": "how", "eppo": "when", "viduppu": "leave", "naal": "days", "naatkal": "days",
        "enakku": "me", "sollunga": "tell", "kidaikkum": "receive", "kidaikum": "receive",
    },
}
PAID_LEAVE = re.compile(
    r"\b(?:(?P<count>\d+) )?(?P<pay>paid|unpaid) "
    r"(?P<leave>(?:(?:annual|sick|parental|compassionate) )?leave(?: days)?|"
    r"vacation(?: days)?|time off|(?:working )?days)\b", re.I,
)
PAY_STATUS = {
    "en": (r"\b(?:paid|with (?:pay|wages|salary))\b", r"\b(?:unpaid|without (?:pay|wages|salary))\b"),
    "hi": (r"सवेतन|सशुल्क|वेतन सहित|वेतन के साथ|म[ज़ज]+दूरी (?:वाली|के साथ)|भुगतान किया जाता",
           r"अवैतनिक|बिना वेतन|अवकाश अवैतनिक"),
    "ta": (r"ஊதியத்துடன்|சம்பளத்துடன்|ஊதிய விடு|ஊதியம் வழங்க",
           r"ஊதியமில்லா|ஊதியம் இல்லா|சம்பளமில்லா|ஊதியம் இல்லாமல்"),
}


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


def detection_confidence(detected):
    if detected.endswith("-Latn"):
        return "heuristic"
    return "assumed" if detected == "en" else "script"


def normalize_roman_query(text, detected):
    words = ROMAN_QUERY_WORDS[detected]
    return re.sub(r"\b[A-Za-z]+\b", lambda match: words.get(match[0].casefold(), match[0]), text)


def express_leave_pay(match):
    leave = match["leave"]
    count = match["count"]
    if count and leave.casefold().endswith(("leave days", "vacation days")):
        leave = f"{count} days of {leave[:-5]}"
    elif count:
        leave = f"{count} {leave}"
    relation = "with" if match["pay"].casefold() == "paid" else "without"
    return f"{leave} {relation} pay"


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

    def tokens(text):
        return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold())

    def pay_status(text, language):
        return tuple(bool(re.search(pattern, text, re.I)) for pattern in PAY_STATUS[language])

    original_pay = pay_status(answer, source)
    prepared = PAID_LEAVE.sub(express_leave_pay, answer) if source == "en" else answer
    for candidate in dict.fromkeys((prepared, answer)):
        translation = translate(candidate, target, model)
        if not translation or original_pay != pay_status(translation, target):
            continue
        roundtrip = translate(translation, source, model)
        if not roundtrip or original_pay != pay_status(roundtrip, source):
            continue
        if tokens(roundtrip) in (tokens(answer), tokens(prepared)):
            return translation
        if (equivalent := getattr(type(model), "equivalent", None)) and equivalent(model, candidate, roundtrip):
            return translation
    return None
