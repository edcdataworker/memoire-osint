"""Explicit fictional-source adapter for recording the real collector UI locally."""

import json
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.collection.service import Controller, serve
from pipeline.collection.source import bounds
from pipeline.collection.worker import execute


class FixtureSource:
    def initialize(self, section):
        return 4953

    def discover(self, section, cursor, excluded):
        stamp = bounds("2023-11-26", "2023-11-26")[0] + 43200
        return {
            "newsList": [{"id": i, "date": stamp, "link": f"/defense/{i}"} for i in range(1, 6)],
            "lastTime": stamp,
        }

    def request(self, url):
        time.sleep(1)
        identifier = int(url.rsplit("/", 1)[1])
        metadata = {
            "@type": "NewsArticle",
            "headline": f"Article fictif {identifier} : équipement de démonstration",
            "datePublished": "2023-11-26T12:00:00Z",
        }
        return (
            '<script type="application/ld+json">'
            + json.dumps(metadata)
            + '</script><div class="text-content"><div class="text-block"><p>Texte fictif pour vérifier le collecteur. Aucune affirmation journalistique ni donnée personnelle réelle.</p></div></div>'
        )


class FixtureController(Controller):
    def supervise(self, key):
        original = subprocess.Popen

        def spawn(arguments, **options):
            if "pipeline.collection.worker" in arguments:
                arguments = [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "worker",
                    arguments[-2],
                    arguments[-1],
                ]
            return original(arguments, **options)

        with patch("pipeline.collection.service.subprocess.Popen", side_effect=spawn):
            return super().supervise(key)


if __name__ == "__main__":
    if sys.argv[1] == "worker":
        config = json.loads(Path(sys.argv[2]).read_text())
        raise SystemExit(execute(config["state"], sys.argv[3], config, FixtureSource()))
    state = Path(sys.argv[1]).resolve()
    config = {"state": str(state), "tombstone_files": [], "max_pages": 3}
    with patch("pipeline.collection.service.Controller", FixtureController):
        serve(config, int(sys.argv[2]) if len(sys.argv) > 2 else 18744)
