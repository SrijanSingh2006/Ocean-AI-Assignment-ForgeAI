"""ForgeAI command line: build, chat, replay, and serve."""

import argparse
import sys
from pathlib import Path

from .corpus import Corpus
from .embeddings import configured_embeddings
from .factory import Agent, read_json, run_factory
from .model import LocalModel, ROOT
from .multilingual import language_model


def interview(requirements):
    for gap in requirements["groundability_gaps"]:
        print(f'Coverage gap: {gap["topic"]}', file=sys.stderr)
    answers = {}
    for item in requirements["questions"]:
        suffix = f' [{item["default"]}]' if item["default"] else ""
        try:
            value = input(f'{item["text"]}{suffix} ').strip()
        except EOFError:
            break
        if value:
            answers[item["id"]] = value
    return answers


def render_answer(result):
    print(f'\n{result["status"].upper()} · {result["answer"]}')
    for citation in result["citations"]:
        print(f'  [{citation["passage_id"]}] {citation["document"]} · {citation["heading"]} · {citation["locator"]}')
    if result["tool"]:
        print(f'  Tool: {result["tool"]}')


def main():
    parser = argparse.ArgumentParser(prog="forgeai", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="Build and evaluate an agent")
    brief = build.add_mutually_exclusive_group(required=True)
    brief.add_argument("--brief")
    brief.add_argument("--brief-file", type=Path)
    build.add_argument("--docs", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--iterations", type=int, default=3)
    build.add_argument("--token-budget", type=int, default=12_000)
    build.add_argument("--latency-budget", type=int, default=120, help="Seconds of active build time")
    build.add_argument("--blind", action="store_true", help="Score held-out questions after development repairs")
    build.add_argument("--unseen-corpus", action="store_true", help="Label a requester-supplied new corpus and run blind evaluation")
    build.add_argument("--security-audit", action="store_true", help="Run fixed defensive conformance checks")
    build.add_argument("--minimum-confidence", type=float, default=0, help="Minimum heuristic evidence score (0 to 1)")
    build.add_argument("--no-tournament", action="store_true")
    build.add_argument("--baseline-definition", type=Path, help="Hand-written agent to compare")
    build.add_argument("--interview", action="store_true")
    build.add_argument("--no-model", action="store_true")
    build.add_argument("--regression-evals", type=Path)

    chat = commands.add_parser("chat", help="Load any generated definition")
    chat.add_argument("--definition", type=Path, required=True)
    chat.add_argument("--docs", type=Path, required=True)
    chat.add_argument("--ask")
    chat.add_argument("--language", choices=("auto", "en", "hi", "ta"), default="auto")
    chat.add_argument("--no-model", action="store_true")

    demo = commands.add_parser("demo", help="Reproduce both committed demonstrations")
    demo.add_argument("--out", type=Path, default=Path(".runs/demos"))
    demo.add_argument("--no-model", action="store_true")
    demo.add_argument("--all-samples", action="store_true", help="Include warehouse tools and policy regression")

    server = commands.add_parser("serve", help="Start the web workspace")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            import uvicorn

            uvicorn.run("forgeai.web:app", host=args.host, port=args.port)
            return
        model = LocalModel(enabled=not args.no_model, token_budget=getattr(args, "token_budget", 12_000))
        if args.command == "build":
            value = args.brief_file.read_text(encoding="utf-8") if args.brief_file else args.brief
            prior_run = args.regression_evals.with_name("run.json") if args.regression_evals else None
            result = run_factory(
                value, args.docs, args.out, model=model, max_iterations=args.iterations,
                interview=interview if args.interview else None,
                progress=lambda stage, text: print(f"[{stage}] {text}", file=sys.stderr, flush=True),
                regression_cases=read_json(args.regression_evals) if args.regression_evals else None,
                prior_results=read_json(prior_run).get("results") if prior_run and prior_run.is_file() else None,
                manual_baseline=read_json(args.baseline_definition) if args.baseline_definition else None,
                tournament=not args.no_tournament, latency_budget=args.latency_budget,
                blind=args.blind, unseen_corpus=args.unseen_corpus, security_audit=args.security_audit,
                minimum_confidence=args.minimum_confidence,
            )
            print(f'{result["definition"]["name"]}: {result["scorecard"]["passed"]}/{result["scorecard"]["total"]} · {args.out}')
        elif args.command == "demo":
            names = ["people-ops", "marine-supply"]
            if args.all_samples:
                names.extend(["operations-lab", "people-ops-revised"])
            prior = None
            for name in names:
                root = ROOT / "demos" / name
                baseline = root / "manual-baseline.json"
                regression = prior if name == "people-ops-revised" else None
                result = run_factory(
                    (root / "brief.txt").read_text(), root / "documents", args.out / name,
                    model=LocalModel(enabled=not args.no_model),
                    progress=lambda stage, text: print(f"[{stage}] {text}", flush=True),
                    manual_baseline=read_json(baseline) if baseline.is_file() else None,
                    regression_cases=regression["evals"] if regression else None,
                    prior_results=regression["results"] if regression else None,
                )
                if name == "people-ops":
                    prior = result
                print(f'{name}: {result["scorecard"]["score"]}% · {result["model"]["mode"]}', flush=True)
        elif args.command == "chat":
            definition = read_json(args.definition)
            retrieval = definition["retrieval"]
            corpus = Corpus.load(args.docs, retrieval["chunk_words"], retrieval["overlap_words"])
            agent = Agent(definition, corpus, model, translator=None if args.no_model else language_model(),
                          embeddings=None if args.no_model else configured_embeddings())
            if args.ask:
                render_answer(agent.answer(args.ask, requested_language=args.language))
                return
            print(f'{definition["name"]} · type /exit to quit')
            while True:
                try:
                    question = input("\nYou > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if question == "/exit":
                    break
                if question:
                    render_answer(agent.answer(question, requested_language=args.language))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"forgeai: {exc}\n")
