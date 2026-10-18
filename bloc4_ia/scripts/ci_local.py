"""Actual local build, tests, immutable wheel deploy, smoke and rollback probe."""

import hashlib
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PROOFS = ROOT / "Preuves"
DATA = ROOT / ".state/inference.jsonl"
RUN = ROOT / ".state/runs/baseline"


def command(args, name):
    started = time.perf_counter()
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    (PROOFS / f"ci_{name}.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name} failed with exit status {result.returncode}")
    return {
        "step": name,
        "exit_code": 0,
        "duration_seconds": round(time.perf_counter() - started, 3),
    }


def health(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
        return json.load(r)


def start_release(release, port, duration=30):
    token = uuid.uuid4().hex
    env = dict(
        os.environ,
        PYTHONPATH=str(release),
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        OSINT_RELEASE_TOKEN=token,
    )
    process = subprocess.Popen(
        [
            PYTHON,
            "-m",
            "osint_ner.cli",
            "serve",
            "--data",
            str(DATA),
            "--run",
            str(RUN),
            "--port",
            str(port),
        ],
        cwd=release,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Deployed service failed: " + process.stderr.read().decode()[:400])
        try:
            response = health(port)
            if response.get("release_token") == token and process.poll() is None:
                return process, response
            time.sleep(0.1)
        except OSError:
            time.sleep(0.1)
    process.terminate()
    raise RuntimeError("Deployed service did not become healthy")


def main():
    global PROOFS, DATA, RUN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=ROOT / ".state")
    parser.add_argument("--proofs", type=Path, default=ROOT / "Preuves")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--persistent", action="store_true")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    DATA, RUN, PROOFS = (
        args.data.resolve(strict=True),
        args.run.resolve(strict=True),
        args.proofs.absolute(),
    )
    PROOFS.mkdir(parents=True, exist_ok=True)
    args.state = args.state.absolute()
    args.state.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    steps = []
    for command_args, name in [
        ([PYTHON, "-m", "pip", "check"], "dependencies"),
        ([PYTHON, "-m", "ruff", "check", "src", "tests", "scripts"], "lint"),
        ([PYTHON, "-m", "pytest", "-q", f"--junitxml={PROOFS / 'ci_tests.xml'}"], "tests"),
        ([PYTHON, "-m", "build", "--wheel", "--no-isolation"], "build"),
    ]:
        steps.append(command(command_args, name))
    wheel = max((ROOT / "dist").glob("*.whl"), key=lambda p: p.stat().st_mtime)
    checksum = hashlib.sha256(wheel.read_bytes()).hexdigest()
    release = args.state / "releases" / checksum[:16]
    steps.append(
        command(
            [PYTHON, "-m", "pip", "install", "--no-deps", "--target", str(release), str(wheel)],
            "install_wheel",
        )
    )
    from osint_ner.contracts import atomic_json, utcnow

    pointer = args.state / "deploy/current.json"
    previous = json.loads(pointer.read_text()) if pointer.exists() else None
    proc, smoke = start_release(release, 8765)
    proc.terminate()
    proc.wait(timeout=10)
    deployed = {
        "wheel_sha256": checksum,
        "release": str(release),
        "deployed_at": utcnow(),
        "previous": previous,
    }
    atomic_json(pointer, deployed)
    rollback = None
    if previous:
        atomic_json(pointer, previous)
        proc, old_health = start_release(Path(previous["release"]), 8765)
        proc.terminate()
        proc.wait(timeout=10)
        rollback = {"restored_wheel_sha256": previous["wheel_sha256"], "health": old_health}
        atomic_json(pointer, deployed)
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    from watch_delivery import fingerprint

    source_paths = [
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
    report = {
        "environment": "github_actions_ephemeral_demo"
        if os.getenv("GITHUB_ACTIONS") == "true"
        else "local_loopback_demo",
        "executed_at": utcnow(),
        "source_commit": git.stdout.strip() or None,
        "source_tree_sha256": fingerprint(source_paths),
        "source_identity": "Working files identified by hash; commit alone does not describe uncommitted changes",
        "steps": steps,
        "deployment": deployed,
        "smoke": smoke,
        "rollback_probe": rollback,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "cloud_ci_executed": os.getenv("GITHUB_ACTIONS") == "true",
        "production_model_promoted": False,
        "continuity": "Service is started and stopped for smoke; no uninterrupted public service claim",
    }
    if args.persistent:
        from osint_ner.deployment import deploy

        report["persistent_deployment"] = deploy(
            wheel, DATA, RUN, args.state / "service", args.port
        )
        report["continuity"] = (
            "Stable loopback gateway; healthy backend switch; previous backend retained for rollback"
        )
    atomic_json(PROOFS / "ci_local.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
