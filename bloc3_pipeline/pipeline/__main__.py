"""Command line interface. Processing uses only the Python standard library."""

import argparse
import json
import os
import sys
from pathlib import Path

from .common import atomic_json

DEFAULTS = {
    "batch_size": 500,
    "mode": "clean",
    "max_reject_rate": 0.005,
    "slow_batch_seconds": 5,
    "max_retries": 3,
    "retry_seconds": 1,
    "synthetic": False,
}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="OSINT pipeline, local demonstrator")
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("collect-ui", help="Interface locale de collecte TASS")
    local.add_argument("--state", default=".state-collection")
    local.add_argument("--port", type=int, default=18743)
    local.add_argument("--corpus")
    local.add_argument("--open", action="store_true")
    local.add_argument("--request-interval", type=float, default=0.7)
    local.add_argument("--max-pages", type=int, default=250)
    local.add_argument("--max-reject-rate", type=float, default=0.2)
    local.add_argument("--slow-article-seconds", type=float, default=10)
    local.add_argument("--require-encrypted", action="store_true")
    for name in (
        "collect-access",
        "collect-rectify",
        "collect-erase",
        "collect-check-security",
        "collect-restore",
        "collect-migrate",
    ):
        command = sub.add_parser(name)
        command.add_argument("--state", default=".state-collection")
        if name in ("collect-access", "collect-rectify", "collect-erase"):
            command.add_argument("article_id")
            command.add_argument("--request-ref", required=True)
        if name == "collect-rectify":
            command.add_argument(
                "--changes", required=True, help="JSON privé contenant titre et/ou texte"
            )
        if name == "collect-check-security":
            command.add_argument("--require-encrypted", action="store_true")
        if name in ("collect-rectify", "collect-erase"):
            command.add_argument("--propagate-b2", action="store_true")
        if name == "collect-migrate":
            command.add_argument("--destination", required=True)
    for name in ("worker", "schedule"):
        command = sub.add_parser(name)
        command.add_argument("--config", required=True)
        if name == "schedule":
            command.add_argument("--cycles", type=int, default=1)
            command.add_argument("--interval", type=float, default=86400)
            command.add_argument("--first-delay", type=float, default=0)
    for name in ("status", "serve", "check-security", "export", "access", "erase"):
        command = sub.add_parser(name)
        command.add_argument("--state", default=".state")
        if name == "serve":
            command.add_argument("--port", type=int, default=18743)
        if name in ("access", "erase"):
            command.add_argument("article_id")
        if name == "erase":
            command.add_argument("--request-ref", required=True)
    args = parser.parse_args()
    if args.command == "collect-ui":
        from .collection.service import default_config, serve

        if (
            not 0.2 <= args.request_interval <= 60
            or not 1 <= args.max_pages <= 1000
            or not 0 <= args.max_reject_rate <= 1
            or args.slow_article_seconds <= 0
        ):
            parser.error("Cadence, limite de pagination ou seuil de rejet invalide")
        config = default_config(args.state, args.corpus)
        config.update(
            request_interval=args.request_interval,
            max_pages=args.max_pages,
            max_reject_rate=args.max_reject_rate,
            slow_article_seconds=args.slow_article_seconds,
            require_encrypted=args.require_encrypted,
        )
        serve(config, args.port, args.open)
    elif args.command.startswith("collect-"):
        from .collection import resilience, rights, security
        from .collection.service import default_config
        from .common import lock

        config = default_config(args.state)
        saved = Path(args.state) / "config.json"
        if saved.exists():
            config.update(json.loads(saved.read_text()))
        if args.command == "collect-access":
            result = rights.access(args.state, args.article_id, args.request_ref)
        elif args.command == "collect-check-security":
            result = security.check(args.state, args.require_encrypted)
        elif args.command == "collect-migrate":
            from .collection.volume import migrate

            result = migrate(args.state, args.destination)
        else:
            # No mutation or compaction can race an ingestion checkpoint. Restoration
            # additionally requires the HTTP server to be stopped.
            with lock(args.state, "collection-worker.lock"):
                if args.command == "collect-restore":
                    with lock(args.state, "collection-server.lock"):
                        result = resilience.restore(args.state, config)
                elif args.command == "collect-erase":
                    result = rights.erase(args.state, config, args.article_id, args.request_ref)
                else:
                    changes = json.loads(Path(args.changes).read_text())
                    result = rights.rectify(
                        args.state, config, args.article_id, changes, args.request_ref
                    )
                if args.command in ("collect-rectify", "collect-erase") and args.propagate_b2:
                    result["b2"] = rights.propagate_b2(
                        args.state,
                        config,
                        args.article_id,
                        args.request_ref,
                        args.command == "collect-erase",
                    )
        print(json.dumps(result, ensure_ascii=False))
    elif args.command in ("worker", "schedule"):
        path = Path(args.config).resolve()
        config = DEFAULTS | json.loads(path.read_text())
        if config["batch_size"] < 1 or not 0 <= config["max_reject_rate"] <= 1:
            parser.error("Invalid batch_size or reject threshold")
        if args.command == "worker":
            from .worker import run

            print(json.dumps(run(config), ensure_ascii=False), flush=True)
        else:
            from .scheduler import supervise

            # Resolve defaults for every worker without modifying the user's config.
            resolved = Path(config["state"]) / "resolved_config.json"
            atomic_json(resolved, config)
            return supervise(resolved, args.cycles, args.interval, args.first_delay)
    elif args.command in ("status", "serve", "check-security"):
        from .monitor import security_check, serve, snapshot

        if args.command == "serve":
            serve(args.state, args.port)
        elif args.command == "check-security":
            print(json.dumps({"initially_safe": security_check(args.state)}))
        else:
            print(json.dumps(snapshot(args.state), ensure_ascii=False, indent=2))
    elif args.command == "export":
        from .publish import published_path

        path, backend = published_path(args.state)
        print(json.dumps({"path": str(path), "backend": backend}))
    else:
        from .rights import access, erase

        if args.command == "access":
            print(json.dumps(access(args.state, args.article_id), ensure_ascii=False))
        else:
            erase(args.state, args.article_id, args.request_ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
