"""CLI endpoints with explicit errors and nonzero exit status."""

import argparse
import json
import sys
from pathlib import Path
from .contracts import atomic_json, read_records, write_records


def main():
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="command", required=True)
    x = commands.add_parser("prepare")
    x.add_argument("--corpus", required=True)
    x.add_argument("--output", required=True)
    x = commands.add_parser("train")
    x.add_argument("--train", required=True)
    x.add_argument("--dev", required=True)
    x.add_argument("--output", required=True)
    x.add_argument("--epochs", type=int, default=6)
    x = commands.add_parser("infer")
    x.add_argument("--run", required=True)
    x.add_argument("--input", required=True)
    x.add_argument("--output", required=True)
    x.add_argument("--limit", type=int, default=0)
    x.add_argument("--exclusions")
    x = commands.add_parser("evaluate")
    x.add_argument("--run", required=True)
    x.add_argument("--reference", required=True)
    x.add_argument("--manifest", required=True)
    x.add_argument("--output", required=True)
    x = commands.add_parser("watch")
    x.add_argument("--train", required=True)
    x.add_argument("--dev", required=True)
    x.add_argument("--state", required=True)
    x.add_argument("--cycles", type=int, default=1)
    x.add_argument("--interval", type=float, default=60)
    x.add_argument("--demo", action="store_true")
    x.add_argument("--epochs", type=int, default=3)
    x = commands.add_parser("monitor")
    x.add_argument("--reference", required=True)
    x.add_argument("--current", required=True)
    x.add_argument("--output", required=True)
    x = commands.add_parser("export-es")
    x.add_argument("--input", required=True)
    x.add_argument("--output", required=True)
    x.add_argument("--exclusions")
    x = commands.add_parser("serve")
    x.add_argument("--data", required=True)
    x.add_argument("--run", required=True)
    x.add_argument("--port", type=int, default=8764)
    x = commands.add_parser("erase")
    x.add_argument("--input", required=True)
    x.add_argument("--article-id", required=True)
    x.add_argument("--output", required=True)
    x.add_argument("--log", required=True)
    a = p.parse_args()
    try:
        if a.command == "prepare":
            from .data import prepare

            result = prepare(a.corpus, a.output)
        elif a.command == "train":
            from .model import train

            result = train(a.train, a.dev, a.output, a.epochs)
        elif a.command == "infer":
            from .model import Predictor
            from .export import exclusions

            excluded = exclusions(a.exclusions)
            rows = [r for r in read_records(a.input) if str(r["id"]) not in excluded]
            if a.limit:
                rows = rows[: a.limit]
            predictor = Predictor(a.run)

            # Bounded batches avoid materializing all prediction documents.
            def batches():
                for i in range(0, len(rows), 32):
                    yield from predictor.predict(rows[i : i + 32])

            write_records(a.output, batches())
            result = {
                "documents": len(rows),
                "output": str(Path(a.output).resolve()),
                "excluded_ids": len(excluded),
                "quality_status": "unvalidated_demo",
            }
        elif a.command == "evaluate":
            from .model import evaluate

            result = evaluate(a.run, a.reference, a.manifest)
            atomic_json(a.output, result)
        elif a.command == "watch":
            from .automation import watch

            result = watch(a.train, a.dev, a.state, a.cycles, a.interval, a.demo, a.epochs)
        elif a.command == "monitor":
            from .monitor import monitor

            result = monitor(
                list(read_records(a.reference)), list(read_records(a.current)), a.output
            )
        elif a.command == "export-es":
            from .export import export_bulk

            result = export_bulk(a.input, a.output, a.exclusions)
        elif a.command == "erase":
            from .export import erase

            result = erase(a.input, a.article_id, a.output, a.log)
        elif a.command == "serve":
            from .server import serve

            serve(a.data, a.run, a.port)
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(
            json.dumps({"error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
