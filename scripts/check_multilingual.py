"""Replay the People Operations language acceptance cases against a running Studio."""

import argparse
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

from forgeai.corpus import Corpus
from forgeai.factory import read_json
from forgeai.multilingual import comparable_symbols, detect_language


ROOT = Path(__file__).resolve().parents[1]
TOPICS = {
    "annual-leave": ("Annual leave", {
        "en": ("What does the policy say about annual leave?", ["22", "five days", "31 March"]),
        "hi": ("वार्षिक छुट्टी कितनी मिलती है?", ["22", "अधिकतम पाँच", "31 मार्च", "अगले वर्ष"]),
        "ta": ("வருடாந்திர விடுப்பு எத்தனை நாட்கள் கிடைக்கும்?", ["22", "அதிகபட்சம் ஐந்து", "மார்ச் 31", "அடுத்த ஆண்டு"]),
        "hi-Latn": ("Annual leave kitne din hai?", ["22", "अधिकतम पाँच", "31 मार्च"]),
        "ta-Latn": ("Annual leave evvalavu naal?", ["22", "அதிகபட்சம் ஐந்து", "மார்ச் 31"]),
    }),
    "hybrid-work": ("Remote work", {
        "en": ("What does the policy say about remote work?", ["up to two days", "each week", "team lead"]),
        "hi": ("दूर से काम करने की नीति क्या है?", ["अधिकतम दो दिन", "हर सप्ताह", "टीम प्रमुख"]),
        "ta": ("தொலைதூர வேலைக் கொள்கை என்ன?", ["அதிகபட்சம் இரண்டு", "வாரத்துக்கு", "குழுத் தலைவர்"]),
    }),
    "training-pdf": ("Training Benefit", {
        "en": ("What is the training allowance for accredited courses?", ["EUR 350", "annually", "PeopleHub", "before paying"]),
        "hi": ("प्रशिक्षण के लिए कितना भत्ता मिलता है?", ["EUR 350", "सालाना", "PeopleHub", "भुगतान करने से पहले"]),
        "ta": ("பயிற்சி உதவித்தொகைக்கு விண்ணப்பிக்க அதிகபட்சம் எவ்வளவு?", ["EUR 350", "ஆண்டுக்கு", "PeopleHub", "முன்"]),
        "hi-Latn": ("Training allowance kitna milta hai?", ["EUR 350", "सालाना", "PeopleHub"]),
    }),
    "sick-leave": ("Sick leave", {
        "hi-en": ("Sick leave में manager को कब बताना है?", ["09:30 बजे से पहले", "तीन कार्यदिवसों के बाद"]),
    }),
    "travel": ("Travel reimbursements", {
        "ta-en": ("Travel reimbursement எத்தனை நாட்களுக்குள் submit செய்ய வேண்டும்?", ["30", "திரும்பிய", "ரசீதை"]),
    }),
    "unsupported": (None, {
        "en": ("What is the income tax filing deadline?", []),
        "hi": ("व्यक्तिगत चिकित्सा निदान कैसे करें?", []),
        "ta": ("எனக்கு வீட்டு கடன் வட்டி விகிதம் என்ன?", []),
    }),
}


def chat(origin, run, question, language):
    body = json.dumps({"run_id": run, "question": question, "language": language})
    return json.loads(subprocess.check_output([
        "curl", "--fail-with-body", "--silent", "--show-error", "--max-time", "75",
        "-H", "Content-Type: application/json", "--data-binary", body, f"{origin}/api/chat",
    ]))


def corpus_for(run):
    demo = ROOT / "demos" / run
    retrieval = read_json(demo / "artifacts" / "definition.json")["retrieval"]
    return Corpus.load(demo / "documents", retrieval["chunk_words"], retrieval["overlap_words"])


def check_case(origin, case_id, code, question, facts, passage, run="people-ops", preference="auto"):
    response = chat(origin, run, question, preference)
    citations = response["citations"]
    expected_language = code.split("-")[0]
    checks = {
        "status": response["status"] == ("answered" if passage else "refused"),
        "language": detect_language(response["answer"]).split("-")[0] == expected_language,
        "detection": response.get("detected_language", "en") == (
            detect_language(question) if preference != "auto" else code
        ),
        "original_evidence": len(citations) == 1 and all(
            citations[0][field] == passage[key]
            for field, key in (("passage_id", "id"), ("document", "document"), ("heading", "heading"),
                               ("locator", "locator"), ("quote", "text"))
        ) if passage else not citations,
        "symbols": not passage or comparable_symbols(response["answer"]) == comparable_symbols(passage["text"]),
        "fact_anchors": all(fact in response["answer"] for fact in facts),
    }
    return {"case_id": case_id, "language": code, "question": question, "status": "scored",
            "passed": all(checks.values()), "checks": checks, "response": response}


def evaluate(origin):
    people = {p["heading"]: p for p in corpus_for("people-ops").passages}
    results = []
    for topic, (heading, cases) in TOPICS.items():
        for code, (question, facts) in cases.items():
            results.append(check_case(origin, topic, code, question, facts, people.get(heading)))
    question = TOPICS["training-pdf"][1]["en"][0]
    results.append(check_case(origin, "explicit-tamil", "ta", question, ["EUR 350", "PeopleHub"],
                              people["Training Benefit"], preference="ta"))
    revised = next(p for p in corpus_for("people-ops-revised").passages if p["heading"] == "Annual leave")
    results.append(check_case(origin, "revised-allowance", "hi", "वार्षिक छुट्टी कितनी मिलती है?",
                              ["25", "अधिकतम पाँच", "31 मार्च"], revised, run="people-ops-revised"))
    groups = {}
    for row in results:
        group = groups.setdefault(row["language"], {"passed": 0, "scored": 0, "total": 0})
        group["passed"] += row["passed"]
        group["scored"] += 1
        group["total"] += 1
    return {
        "review": "Automated source and fact checks on fictional policies. Independent native-language review is pending.",
        "providers": ["NLLB-200 distilled 600M", "multilingual E5-small", "aligned fictional policy sources"],
        "languages": groups, "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    origin = args.origin.rstrip("/")
    if urlsplit(origin).scheme not in {"http", "https"}:
        parser.error("Provide an HTTP or HTTPS Studio origin")
    report = evaluate(origin)
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in report["results"]:
        print(f"{'PASS' if row['passed'] else 'FAIL'}  {row['language']:8} {row['case_id']} {row['checks']}")
    return 0 if all(row["passed"] for row in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
