"""ForgeAI command line: build, chat, replay, and serve."""

import argparse
import sys
from pathlib import Path

from .corpus import Corpus
from .factory import Agent, read_json, run_factory
from .model import LocalModel, ROOT


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
    build.add_argument("--interview", action="store_true")
    build.add_argument("--no-model", action="store_true")
    build.add_argument("--regression-evals", type=Path)

    chat = commands.add_parser("chat", help="Load any generated definition")
    chat.add_argument("--definition", type=Path, required=True)
    chat.add_argument("--docs", type=Path, required=True)
    chat.add_argument("--ask")
    chat.add_argument("--no-model", action="store_true")

    demo = commands.add_parser("demo", help="Reproduce both committed demonstrations")
    demo.add_argument("--out", type=Path, default=Path(".runs/demos"))
    demo.add_argument("--no-model", action="store_true")

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
            result = run_factory(
                value, args.docs, args.out, model=model, max_iterations=args.iterations,
                interview=interview if args.interview else None,
                progress=lambda stage, text: print(f"[{stage}] {text}", file=sys.stderr, flush=True),
                regression_cases=read_json(args.regression_evals) if args.regression_evals else None,
            )
            print(f'{result["definition"]["name"]}: {result["scorecard"]["passed"]}/{result["scorecard"]["total"]} · {args.out}')
        elif args.command == "demo":
            for name in ("people-ops", "marine-supply"):
                root = ROOT / "demos" / name
                result = run_factory(
                    (root / "brief.txt").read_text(), root / "documents", args.out / name,
                    model=LocalModel(enabled=not args.no_model),
                    progress=lambda stage, text: print(f"[{stage}] {text}", flush=True),
                )
                print(f'{name}: {result["scorecard"]["score"]}% · {result["model"]["mode"]}', flush=True)
        elif args.command == "chat":
            definition = read_json(args.definition)
            retrieval = definition["retrieval"]
            corpus = Corpus.load(args.docs, retrieval["chunk_words"], retrieval["overlap_words"])
            agent = Agent(definition, corpus, model)
            if args.ask:
                render_answer(agent.answer(args.ask))
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
                    render_answer(agent.answer(question))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"forgeai: {exc}\n")
