"""At most five real articles per rubric; retain only technical evidence, not text."""

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.collection.source import SECTIONS, Client, bounds, canonical, extract
from pipeline.common import now


def main():
    results = []
    for section in SECTIONS:
        errors = []
        client = Client(lambda kind, **fields: errors.append({"kind": kind, **fields}))
        start = time.perf_counter()
        try:
            section_id = client.initialize(section)
            page = client.discover(section_id, bounds("2026-10-03", "2026-10-03")[1] - 1, [])
            articles = []
            for item in page["newsList"][:5]:
                url = canonical("https://tass.com" + item["link"])
                stamp = time.perf_counter()
                markup = client.request(url)
                row = extract(markup, url, "bounded-final-verification")
                assert row["text_sha256"] == hashlib.sha256(row["text"].encode()).hexdigest()
                articles.append(
                    {
                        "id": row["id"],
                        "url": url,
                        "date": row["date"],
                        "text_chars": len(row["text"]),
                        "text_sha256": row["text_sha256"],
                        "seconds": round(time.perf_counter() - stamp, 3),
                    }
                )
            results.append(
                {
                    "section": section,
                    "section_id": section_id,
                    "articles": articles,
                    "seconds": round(time.perf_counter() - start, 3),
                    "network_events": errors,
                    "success": len(articles) == 5,
                }
            )
        except (OSError, ValueError, KeyError) as error:
            results.append(
                {
                    "section": section,
                    "success": False,
                    "error_type": type(error).__name__,
                    "network_events": errors,
                }
            )
    proof = {
        "at": now(),
        "type": "real network extraction, texts kept only in process memory",
        "maximum_articles_per_section": 5,
        "requested_end_day": "2026-10-03",
        "coverage_complete": False,
        "sections": results,
    }
    (ROOT / "Preuves/Collecte_TASS/Reseau_final.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    print(json.dumps({"sections": len(results), "successful": sum(r["success"] for r in results)}))
    if not all(r["success"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
