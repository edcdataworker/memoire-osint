"""Bounded live polling drill, separate encrypted state and metadata-only evidence."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.collection import security, store
from pipeline.collection.continuous import ContinuousCollector
from pipeline.collection.service import Controller, default_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encrypted-parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent = args.encrypted_parent.resolve(strict=True)
    if not security.encrypted_volume(parent):
        parser.error("Un volume chiffré effectivement monté est requis.")
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="live-poll-drill-", dir=parent) as directory:
        state = Path(directory)
        config = default_config(state)
        config.update(corpus=None, max_pages=2, request_interval=1.0, require_encrypted=True)
        controller = Controller(config)
        poll = ContinuousCollector(controller, {"max_cycles": 3, "limit": 5,
            "interval_seconds": 60, "max_failures": 1, "retry_seconds": 15})
        start = time.monotonic()
        samples = []
        try:
            while time.monotonic() - start < 600:
                poll.tick()
                snapshot = poll.snapshot()
                if snapshot['completed'] > len(samples):
                    job = store.job(state, snapshot['last_job'])
                    samples.append({"cycle": snapshot['completed'], "status": job['status'],
                        "coverage": job['coverage'], "counts": job['counts'],
                        "duration_seconds": round(snapshot['last_duration'], 3),
                        "trigger_lag_seconds": round(snapshot['last_lag'], 3)})
                if snapshot['status'] in ('finished', 'failed', 'quality_blocked', 'paused'):
                    break
                time.sleep(0.2)
        finally:
            controller.stop_server.set()
            deadline = time.monotonic() + 60
            while controller.active and time.monotonic() < deadline:
                time.sleep(0.2)
            if controller.active:
                raise RuntimeError("Worker still active; retain encrypted state for investigation")
        with store.read_database(state) as db:
            rows = db.execute('SELECT count(*) FROM heads').fetchone()[0]
        events = [json.loads(x) for x in (state/'events.jsonl').read_text().splitlines()]
        alerts = [e.get('code') for e in events if e.get('kind',e.get('event')) == 'alert']
        proof = {"at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Trois cycles réseau TASS, cinq articles maximum par cycle, état isolé chiffré supprimé après arrêt",
            "synthetic_source": False, "cycles": samples, "completed": len(samples),
            "status": poll.snapshot()['status'], "distinct_articles": rows,
            "interval_seconds": 60, "alert_codes": alerts,
            "duration_seconds": round(time.monotonic()-start,3),
            "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "limitations": ["Pas de collecte permanente", "Couverture bornée, non exhaustive",
                "Durée de cycle distincte du délai de publication TASS", "Aucun import Bloc 2 ni NER Bloc 4 déclenché"]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(proof, ensure_ascii=False))
        if len(samples) != 3:
            raise RuntimeError("Live polling drill incomplete; consult metadata evidence")


if __name__ == '__main__':
    main()
