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
    if args.command in ("worker", "schedule"):
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
