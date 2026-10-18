"""Exercise actual immutable wheels and local processes on synthetic data only."""

import argparse
import json
import shutil
import threading
import time
from pathlib import Path

from osint_ner.contracts import atomic_json, utcnow
from osint_ner.deployment import deploy, request_json, rollback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--proofs", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18766)
    args = parser.parse_args()
    state = args.state.absolute()
    service = state / "service"
    samples = []
    finished = threading.Event()

    def probe():
        while not finished.is_set():
            started = time.perf_counter()
            try:
                health = request_json(args.port)
                samples.append(
                    {
                        "ok": health["prediction_ready"],
                        "version": health["version"],
                        "seconds": time.perf_counter() - started,
                    }
                )
            except (OSError, ValueError) as error:
                samples.append({"ok": False, "error": type(error).__name__})
            finished.wait(0.02)

    before = request_json(args.port)
    thread = threading.Thread(target=probe, daemon=True)
    thread.start()
    try:
        update = deploy(
            args.wheel, state / "inference.jsonl", state / "runs/baseline", service, args.port
        )
        rolled = rollback(service)
        assert rolled["health"]["release_token"] == before["release_token"]
        bad_run = state / "bad-model-fixture"
        if not bad_run.exists():
            shutil.copytree(state / "runs/baseline", bad_run)
        meta = json.loads((bad_run / "training.json").read_text())
        meta["model_sha256"] = "intentional-synthetic-checksum-failure"
        atomic_json(bad_run / "training.json", meta)
        failure = None
        try:
            deploy(args.wheel, state / "inference.jsonl", bad_run, service, args.port)
        except RuntimeError as error:
            failure = str(error)
        assert failure is not None
        assert request_json(args.port)["release_token"] == before["release_token"]
        final = deploy(
            args.wheel, state / "inference.jsonl", state / "runs/baseline", service, args.port
        )
        time.sleep(0.3)
    finally:
        finished.set()
        thread.join()
    report = {
        "at": utcnow(),
        "scope": "synthetic_fixture_only",
        "update": update,
        "rollback": rolled,
        "failed_candidate_rejected": failure,
        "previous_service_preserved_on_failure": True,
        "final": final,
        "health_probes": len(samples),
        "failed_probes": sum(not s["ok"] for s in samples),
        "max_probe_seconds": max(s.get("seconds", 0) for s in samples),
        "limitation": "Observed local window only; no uptime SLA, reboot recovery or external production",
    }
    atomic_json(args.proofs / "Verification_livraison.json", report)
    assert report["failed_probes"] == 0
    print(
        json.dumps(
            {k: report[k] for k in ("health_probes", "failed_probes", "failed_candidate_rejected")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
