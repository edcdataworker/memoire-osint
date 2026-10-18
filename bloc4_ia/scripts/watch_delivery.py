"""Poll source fingerprints and run build, tests and persistent local delivery."""

import argparse
import fcntl
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from osint_ner.contracts import atomic_json, utcnow

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(paths):
    checksum = hashlib.sha256()
    for source in sorted(paths):
        files = sorted(source.rglob("*")) if source.is_dir() else [source]
        for path in files:
            if (
                not path.is_file()
                or path.suffix == ".pyc"
                or any(
                    part == "__pycache__" or part == ".DS_Store" or part.endswith(".egg-info")
                    for part in path.relative_to(ROOT).parts
                )
            ):
                continue
            checksum.update(str(path.relative_to(ROOT)).encode())
            checksum.update(path.read_bytes())
    return checksum.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--proofs", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    if args.cycles < 1 or args.interval < 0:
        parser.error("Positive cycles and nonnegative interval required")
    args.state = args.state.absolute()
    args.proofs = args.proofs.absolute()
    args.state.mkdir(parents=True, exist_ok=True)
    args.proofs.mkdir(parents=True, exist_ok=True)
    paths = [
        ROOT / name
        for name in (
            "src",
            "scripts",
            "tests",
            "config",
            ".github",
            "pyproject.toml",
            "requirements.lock.txt",
        )
    ]
    status_path = args.state / "delivery_watch.json"
    with (args.state / "delivery_watch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for cycle in range(args.cycles):
            current = fingerprint(paths)
            previous = json.loads(status_path.read_text()) if status_path.exists() else {}
            event = {"at": utcnow(), "source_sha256": current, "cycle": cycle}
            if previous.get("source_sha256") == current:
                event["action"] = "unchanged_skip"
            else:
                command = [
                    sys.executable,
                    str(ROOT / "scripts/ci_local.py"),
                    "--state",
                    str(args.state),
                    "--proofs",
                    str(args.proofs),
                    "--data",
                    str(args.data.absolute()),
                    "--run",
                    str(args.run.absolute()),
                    "--persistent",
                    "--port",
                    str(args.port),
                ]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                (args.proofs / "delivery_watch.log").write_text(result.stdout + result.stderr)
                event.update(
                    action="delivered" if result.returncode == 0 else "failed",
                    exit_code=result.returncode,
                )
                if result.returncode == 0:
                    atomic_json(status_path, event)
            with (args.proofs / "delivery_watch_events.jsonl").open("a") as log:
                log.write(json.dumps(event) + "\n")
            print(json.dumps(event), flush=True)
            if event["action"] == "failed":
                raise SystemExit("Delivery failed; the previous service remains selected")
            if cycle + 1 < args.cycles:
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
