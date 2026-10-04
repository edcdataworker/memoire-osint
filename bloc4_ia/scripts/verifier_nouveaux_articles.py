"""Verify a five-article B3/B2/B4 sample and index its existing-model predictions.

Run in the B2 ops container. Input files contain private texts and must remain
on the encrypted volume. Output records counts, identifiers and hashes only.
This check measures integration, not NER accuracy or automatic orchestration.
"""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import time

import requests

from osint.storage import CA, decrypt, es, mongo, pg, secret, tombstones


def sha(value):
    return hashlib.sha256(value).hexdigest()


def reader_search(index, body):
    response = requests.post(
        "https://elasticsearch:9200/" + index + "/_search",
        auth=("osint_reader", secret("reader")),
        verify=CA,
        json=body,
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    assert not result.get("timed_out") and result["_shards"]["failed"] == 0
    return result


def verify(directory, output, write):
    directory = Path(directory)
    articles = json.loads((directory / "articles.json").read_text())
    source = {str(row["id"]): row for row in articles}
    assert 1 <= len(articles) == len(source) <= 5, "Expected at most five distinct articles"
    predictions = [json.loads(line) for line in (directory / "predictions.jsonl").read_text().splitlines()]
    assert {str(row["id"]) for row in predictions} == set(source)
    models = {row["model_sha256"] for row in predictions}
    assert len(models) == 1
    model_sha = next(iter(models))
    expected = {}
    for row in predictions:
        original = source[str(row["id"])]
        for key in ("text", "date", "title", "url", "text_sha256", "offset_unit", "schema_version"):
            assert row[key] == original[key], "Prediction source mismatch"
        assert sha(row["text"].encode()) == row["text_sha256"]
        previous_end = 0
        for entity in sorted(row["entities"], key=lambda value: value["start"]):
            assert entity["label"] in ("WEAPON", "MIL_UNIT", "MIL_ORG")
            assert type(entity["start"]) is int and type(entity["end"]) is int
            assert previous_end <= entity["start"] < entity["end"] <= len(row["text"])
            assert row["text"][entity["start"]:entity["end"]] == entity["text"]
            previous_end = entity["end"]
            key = sha(f"{row['id']}:{row['text_sha256']}:{row['model_sha256']}:{entity['start']}:{entity['end']}:{entity['label']}".encode())
            expected[key] = {
                "id": str(row["id"]), "date": row["date"], "url": row["url"],
                "text_sha256": row["text_sha256"], "model_version": row["model_version"],
                "model_sha256": model_sha, "annotation_status": row["annotation_status"],
                "entity": entity["text"], "label": entity["label"],
                "start": entity["start"], "end": entity["end"], "offset_unit": "unicode_codepoint",
            }
    bulk = (directory / "mentions.ndjson").read_bytes()
    lines = bulk.decode().splitlines()
    assert len(lines) == 2 * len(expected) and len(expected) <= 1000
    seen = set()
    for i in range(0, len(lines), 2):
        action, document = json.loads(lines[i]), json.loads(lines[i + 1])
        assert set(action) == {"index"} and action["index"]["_index"] == "osint-entities-v1"
        key = action["index"]["_id"]
        assert key not in seen and expected[key] == document
        seen.add(key)
    assert seen == set(expected)
    ids = sorted(source)
    query = {"bool": {"filter": [{"terms": {"id": ids}}, {"term": {"model_sha256": model_sha}}]}}
    others = {"bool": {"must_not": [{"terms": {"id": ids}}]}}
    started = time.perf_counter()
    # Match the rights/ingestion lock order used by B2 before the targeted write.
    with Path("/state/erasures.lock").open("a") as gate, pg("reader") as sql:
        fcntl.flock(gate, fcntl.LOCK_SH)
        assert sql.execute("SELECT pg_try_advisory_lock(420026)").fetchone()[0], "Retry after B2 ingestion"
        assert not set(ids).intersection(tombstones()), "Excluded article"
        rows = sql.execute(
            "SELECT article_id,content_sha256,published_at FROM articles WHERE article_id = ANY(%s)", (ids,)
        ).fetchall()
        assert {row[0] for row in rows} == set(ids)
        sql_values = {row[0]: row for row in rows}
        documents = list(mongo("reader").documents.find({"_id": {"$in": ids}}))
        assert {row["_id"] for row in documents} == set(ids)
        for document in documents:
            key = document["_id"]
            assert document["content_sha256"] == sql_values[key][1]
            payload = decrypt(document["ciphertext"], key)
            # B2 stores the ID in _id and the date in published_at, outside its encrypted payload.
            for field in ("text", "title", "url", "text_sha256", "schema_version", "offset_unit", "provenance"):
                assert payload[field] == source[key][field], "B2 payload differs from current B3 sample"
            assert sql_values[key][2].replace(tzinfo=timezone.utc).timestamp() == source[key]["date"]
            assert document["published_at"].replace(tzinfo=timezone.utc).timestamp() == source[key]["date"]
        article_hits = reader_search("osint-articles-v1", {"size": 5, "query": {"terms": {"article_id": ids}}})
        assert {hit["_source"]["article_id"] for hit in article_hits["hits"]["hits"]} == set(ids)
        for hit in article_hits["hits"]["hits"]:
            value = hit["_source"]
            assert value["content_sha256"] == sql_values[value["article_id"]][1]
        before_mapping = es("GET", "osint-articles-v1/_mapping")
        before_entities_mapping = es("GET", "osint-entities-v1/_mapping")
        before_total = es("GET", "osint-entities-v1/_count")["count"]
        before_other = es("POST", "osint-entities-v1/_count", {"query": others})["count"]
        before_sample = es("POST", "osint-entities-v1/_count", {"query": query})["count"]
        old_hits = reader_search("osint-entities-v1", {"size": 1000, "query": {"terms": {"id": ids}}})
        assert len(old_hits["hits"]["hits"]) <= len(expected)
        for hit in old_hits["hits"]["hits"]:
            assert hit["_id"] in expected and hit["_source"] == expected[hit["_id"]], "Stale mention: stop before write"
        if write and expected:
            response = requests.post(
                "https://elasticsearch:9200/_bulk?refresh=wait_for", data=bulk,
                headers={"Content-Type": "application/x-ndjson"},
                auth=("osint_writer", secret("writer")), verify=CA, timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            assert not result.get("errors") and len(result["items"]) == len(expected)
            assert all(200 <= item["index"]["status"] < 300 for item in result["items"])
        hits = reader_search("osint-entities-v1", {"size": 1000, "query": query})
        actual = {hit["_id"]: hit["_source"] for hit in hits["hits"]["hits"]}
        if write:
            assert actual == expected, "Reader readback differs from predicted mentions"
        after_total = es("GET", "osint-entities-v1/_count")["count"]
        after_other = es("POST", "osint-entities-v1/_count", {"query": others})["count"]
        assert before_other == after_other, "Unrelated mention count changed"
        assert es("GET", "osint-articles-v1/_mapping") == before_mapping
        assert es("GET", "osint-entities-v1/_mapping") == before_entities_mapping
        assert not set(ids).intersection(tombstones())
    report = {
        "at_utc": datetime.now(timezone.utc).isoformat(), "mode": "manual_targeted_indexing" if write else "read_only_preflight",
        "articles_checked": len(ids), "article_ids": ids,
        "model_version": predictions[0]["model_version"], "model_sha256": model_sha,
        "expected_mentions": len(expected), "reader_mentions": len(actual),
        "articles_with_mentions": len({row["id"] for row in expected.values()}),
        "b3_b2_ids_dates_text_hashes_provenance_match": True,
        "b4_complete_texts_and_unicode_offsets_match": True,
        "all_reader_documents_match_bulk": actual == expected,
        "exclusions_checked": True, "tls_verified": True,
        "b2_mapping_unchanged": True, "b4_mapping_unchanged": True,
        "sample_mentions_before": before_sample,
        "index_mentions_before": before_total, "index_mentions_after": after_total,
        "unrelated_mentions_before": before_other, "unrelated_mentions_after": after_other,
        "input_sha256": sha((directory / "articles.jsonl").read_bytes()),
        "predictions_sha256": sha((directory / "predictions.jsonl").read_bytes()), "bulk_sha256": sha(bulk),
        "seconds_storage_check_and_indexing": round(time.perf_counter() - started, 3),
        "model_retrained": False, "automatic_collection_trigger": False,
        "interpretation": "Integration and identity checks on five real articles; no accuracy score inferred.",
    }
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--index", action="store_true")
    args = parser.parse_args()
    verify(args.directory, args.output, args.index)
