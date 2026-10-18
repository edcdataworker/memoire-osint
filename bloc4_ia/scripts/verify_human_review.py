"""Browser/API/data verification using synthetic articles, then read-only real UI."""

import os
import subprocess
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from osint_ner.contracts import article, write_records
from osint_ner.human_review import ReviewStore, make_handler

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="osint-review-synthetic-") as folder:
        base = Path(folder)
        rows = [
            article(
                {
                    "id": 900000000 + i,
                    "title": f"SYNTHETIC TEST ONLY {i}",
                    "text": f"😀 Kalibr. Article fictif de test {i}.",
                    "url": f"https://example.org/fixture-{i}",
                    "split": "test",
                    "group_id": f"synthetic-fixture-{i}",
                    "annotation_status": "ai_proposed_pending_human",
                    "entities": [{"start": 2, "end": 8, "label": "WEAPON", "text": "Kalibr"}],
                }
            )
            for i in range(3)
        ]
        write_records(base / "reference.jsonl", rows)
        write_records(base / "manifest.jsonl", rows)
        store = ReviewStore(
            base / "reference.jsonl",
            base / "manifest.jsonl",
            base / "progress",
            ROOT / ".state/runs/baseline",
        )
        server = ThreadingHTTPServer(
            ("127.0.0.1", 18767),
            make_handler(
                store, ROOT / "src/osint_ner/static/human_review.html", "synthetic-fixture-token"
            ),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            subprocess.run(
                [
                    "/Users/ed/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
                    str(ROOT / "scripts/verify_human_review.cjs"),
                ],
                check=True,
            )
            # The only automatic attestations and scores belong to these synthetic IDs.
            assert all(str(r["id"]).startswith("90000000") for r in store.snapshot()["articles"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    os.umask(0o077)
    main()
