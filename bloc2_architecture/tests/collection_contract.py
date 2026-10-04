"""Compare a collected export to SQL, decrypted Mongo and the derived index."""

import hashlib
import json
import sys
from datetime import timezone
from pathlib import Path

from osint.storage import INDEX, decrypt, es, mongo, pg

rows = json.loads(Path(sys.argv[1]).read_text())
db = mongo("reader")
with pg("reader") as sql:
    for row in rows:
        key = str(row["id"])
        date, checksum = sql.execute(
            "SELECT published_at,content_sha256 FROM articles WHERE article_id=%s",
            (key,),
        ).fetchone()
        assert date.timestamp() == row["date"]
        doc = db.documents.find_one({"_id": key})
        assert doc["content_sha256"] == checksum
        assert (
            doc["published_at"].replace(tzinfo=timezone.utc).timestamp() == row["date"]
        )
        plain = decrypt(doc["ciphertext"], key)
        for field in (
            "title",
            "url",
            "text",
            "text_sha256",
            "provenance",
            "revision_sha256",
            "offset_unit",
        ):
            assert plain[field] == row[field]
        assert hashlib.sha256(plain["text"].encode()).hexdigest() == row["text_sha256"]
        indexed = es("GET", INDEX + "/_doc/" + key)["_source"]
        assert indexed["content_sha256"] == checksum
        assert decrypt(indexed["ciphertext"], key) == plain
    total = sql.execute(
        "SELECT count(*) FROM articles WHERE synthetic=false"
    ).fetchone()[0]
report = {
    "collected_articles_checked": len(rows),
    "ids_dates_texts_hashes_provenance_offsets_match": True,
    "postgres_total": total,
    "mongo_total": db.documents.count_documents({"synthetic": False}),
    "elasticsearch_articles": es("GET", INDEX + "/_count")["count"],
    "historical_ner_mentions_retained": es("GET", "osint-entities-v1/_count")["count"],
    "ner_on_new_articles": "not_launched",
}
Path("/evidence/Contrat_collecte_TASS.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
