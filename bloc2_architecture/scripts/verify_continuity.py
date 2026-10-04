"""Exercise local OSINT read continuity; restore services even if an assertion fails."""

import argparse
import json
import time
import urllib.error

from verify_lifecycle import ROOT, get, run


def main(article_id):
    original = get("/api/article?id=" + article_id)
    assert original["mode"] == "primary"
    # Ensure the derived index is available before stopping either authority.
    run(
        "run",
        "--rm",
        "-T",
        "ops",
        "python",
        "-c",
        "from osint.storage import es,INDEX;es('GET',INDEX+'/_count')",
    )
    results = []
    try:
        run("stop", "postgres", "mongo")
        start = time.perf_counter()
        degraded = get("/api/article?id=" + article_id)
        assert degraded["mode"] == "degraded_index_snapshot"
        assert degraded["article"] == original["article"]
        results.append(
            {
                "test": "SQL and Mongo stopped; identical article served from index",
                "passed": True,
                "mode": degraded["mode"],
                "seconds": time.perf_counter() - start,
            }
        )
        ledger = json.loads((ROOT / ".state/erasures.json").read_text())
        for key in ledger:
            try:
                get("/api/article?id=" + key)
                raise AssertionError("Erased article visible")
            except urllib.error.HTTPError as error:
                assert error.code == 404
        results.append(
            {
                "test": "erasure ledger masks articles during primary outage",
                "passed": True,
                "identifiers_checked": len(ledger),
            }
        )
        run("start", "postgres", "mongo")
        for _ in range(40):
            try:
                restored = get("/api/article?id=" + article_id)
                if restored["mode"] == "primary":
                    break
            except Exception:
                pass
            time.sleep(1)
        assert restored["mode"] == "primary"
        assert restored["article"] == original["article"]
        results.append({"test": "primary reads restored after restart", "passed": True})
        run("stop", "elasticsearch")
        independent = get("/api/article?id=" + article_id)
        assert independent == original
        results.append(
            {"test": "Elasticsearch stopped; primary path unaffected", "passed": True}
        )
    finally:
        run("start", "postgres", "mongo", "elasticsearch")
    (ROOT / "Preuves/continuity.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--article-id", default="2035207")
    main(parser.parse_args().article_id)
