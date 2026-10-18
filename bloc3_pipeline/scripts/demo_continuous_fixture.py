"""Run the actual HTTP collector on progressively arriving fictional articles."""

import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.collection.service import Controller, serve
from pipeline.collection.worker import execute
from pipeline.common import atomic_json


class FeedSource:
    def __init__(self, path):
        self.path = Path(path)

    def initialize(self, section):
        return 4953

    def discover(self, section, cursor, excluded):
        rows = json.loads(self.path.read_text())
        return {
            "newsList": [
                {"id": r["id"], "date": int(r["available_epoch"]), "link": f"/defense/{r['id']}"}
                for r in rows
                if str(r["id"]) not in {str(v) for v in excluded}
            ],
            "lastTime": min((int(r["available_epoch"]) for r in rows), default=cursor),
        }

    def request(self, url):
        row = next(
            r for r in json.loads(self.path.read_text()) if str(r["id"]) == url.rsplit("/", 1)[1]
        )
        metadata = {
            "@type": "NewsArticle",
            "headline": f"Article fictif en flux {row['id']}",
            "datePublished": datetime.fromtimestamp(
                row["available_epoch"], timezone.utc
            ).isoformat(),
        }
        return (
            '<script type="application/ld+json">'
            + json.dumps(metadata)
            + '</script><div class="text-content"><div class="text-block">'
            + "<p>Document fictif pour vérifier le flux. Aucun fait journalistique réel.</p></div></div>"
        )


class FeedController(Controller):
    def supervise(self, key):
        original = subprocess.Popen

        def spawn(arguments, **kwargs):
            if "pipeline.collection.worker" in arguments:
                arguments = [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "worker",
                    arguments[-2],
                    arguments[-1],
                ]
            return original(arguments, **kwargs)

        with patch("pipeline.collection.service.subprocess.Popen", side_effect=spawn):
            return super().supervise(key)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        config = json.loads(Path(sys.argv[2]).read_text())
        return execute(config["state"], sys.argv[3], config, FeedSource(config["fixture_feed"]))
    state = Path(sys.argv[1] if len(sys.argv) > 1 else ".demo-continuous").resolve()
    if state.exists():
        raise SystemExit("Choisir un nouveau dossier de démonstration fictive.")
    state.mkdir(parents=True, mode=0o700)
    feed = state / "fictional-feed.json"
    atomic_json(feed, [])

    def arrivals():
        rows = []
        for i in range(1, 4):
            time.sleep(0.7)
            rows.append({"id": 90000000 + i, "available_epoch": time.time()})
            atomic_json(feed, rows)

    config = {
        "state": str(state),
        "fixture_feed": str(feed),
        "tombstone_files": [],
        "max_pages": 3,
        "continuous": {"interval_seconds": 0.3, "max_cycles": 10},
    }
    threading.Thread(target=arrivals, daemon=True).start()
    with patch("pipeline.collection.service.Controller", FeedController):
        serve(config, int(sys.argv[2]) if len(sys.argv) > 2 else 18753)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
