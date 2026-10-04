"""B2 revision and inclusive date API regression, on an isolated fixture identifier."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from osint.cli import erase
from osint.ingest import publish_batch
from osint.storage import CA, decrypt, mongo, pg, secret

key = "fixture-collection-" + uuid.uuid4().hex
run_id = uuid.uuid4()
db = mongo()
report = {}
with pg() as sql:
    sql.execute(
        "INSERT INTO runs(run_id,kind,source_sha256,status,expected) VALUES(%s,'fixture',%s,'running',2)",
        (run_id, "0" * 64),
    )
    sql.commit()
    first = {
        "id": key,
        "source_id": "tass",
        "published_at": datetime(2023, 11, 26, 12, tzinfo=timezone.utc),
        "payload": {
            "title": "Explicit fixture",
            "text": "Original version Ω",
            "url": "https://example.invalid/fixture",
        },
        "synthetic": False,
    }
    second = {**first, "payload": {**first["payload"], "text": "Revised version Ω"}}
    try:
        publish_batch(sql, db, [first], run_id, set())
        sql.commit()
        original = db.documents.find_one({"_id": key})
        publish_batch(sql, db, [second], run_id, set())
        sql.commit()
        publish_batch(sql, db, [second], run_id, set())
        sql.commit()
        archived = db.document_revisions.find_one({"article_id": key})
        assert decrypt(archived["ciphertext"], key) == first["payload"]
        assert (
            decrypt(db.documents.find_one({"_id": key})["ciphertext"], key)
            == second["payload"]
        )
        assert db.document_revisions.count_documents({"article_id": key}) == 1
        assert (
            sql.execute(
                "SELECT content_sha256 FROM article_revisions WHERE article_id=%s",
                (key,),
            ).fetchone()[0]
            == original["content_sha256"]
        )
        report.update(
            revision_conserved=True,
            replay_without_duplicate=True,
            archive_encrypted=True,
        )
        response = requests.get(
            "https://api:8443/api/articles?start=2023-11-26&end=2023-11-26",
            auth=("analyste", secret("api_password")),
            verify=CA,
            timeout=20,
        )
        response.raise_for_status()
        assert key in {r["id"] for r in response.json()["articles"]}
        outside = requests.get(
            "https://api:8443/api/articles?start=2023-11-27&end=2023-11-27",
            auth=("analyste", secret("api_password")),
            verify=CA,
            timeout=20,
        ).json()
        assert key not in {r["id"] for r in outside["articles"]}
        report["inclusive_dates"] = True
        erase(key)
        assert db.documents.find_one({"_id": key}) is None
        assert db.document_revisions.count_documents({"article_id": key}) == 0
        assert (
            sql.execute(
                "SELECT count(*) FROM article_revisions WHERE article_id=%s", (key,)
            ).fetchone()[0]
            == 0
        )
        publish_batch(sql, db, [second], run_id, {key})
        sql.commit()
        assert db.documents.find_one({"_id": key}) is None
        report["erasure_and_reimport_exclusion"] = True
    finally:
        db.documents.delete_one({"_id": key})
        db.document_revisions.delete_many({"article_id": key})
        sql.execute("DELETE FROM article_revisions WHERE article_id=%s", (key,))
        sql.execute("DELETE FROM articles WHERE article_id=%s", (key,))
        sql.execute("DELETE FROM runs WHERE run_id=%s", (run_id,))
        sql.commit()
Path("/evidence/Revisions_collecte_TASS.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
