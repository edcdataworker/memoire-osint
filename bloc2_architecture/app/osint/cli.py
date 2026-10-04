"""Operational commands. Logs contain counts and identifiers, never credentials."""

import argparse
import fcntl
from datetime import timezone
import json
from pathlib import Path
import sys
import uuid

import requests
from .ingest import ingest
from .storage import (
    CA,
    INDEX,
    encrypt,
    es,
    mongo,
    pg,
    private_json,
    rectifications,
    secret,
    tombstones,
)


def status():
    with pg() as sql:
        counts = sql.execute(
            "SELECT synthetic,count(*) FROM articles GROUP BY synthetic ORDER BY synthetic"
        ).fetchall()
        runs = sql.execute(
            "SELECT run_id,kind,status,checkpoint,expected FROM runs ORDER BY started_at DESC LIMIT 8"
        ).fetchall()
        ssl = sql.execute(
            "SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"
        ).fetchone()
    db = mongo()
    result = {
        "articles_SQL": {str(k): v for k, v in counts},
        "documents_Mongo": db.documents.count_documents({}, hint="_id_"),
        "postgres_TLS": ssl,
        "runs": runs,
    }
    print(json.dumps(result, default=str, ensure_ascii=False))
    return result


def init_index():
    for role in ("writer", "reader"):
        privileges = (
            ["read", "write", "create_index", "view_index_metadata"]
            if role == "writer"
            else ["read", "view_index_metadata"]
        )
        es(
            "PUT",
            "_security/role/osint_" + role,
            {"indices": [{"names": ["osint-*"], "privileges": privileges}]},
            admin=True,
        )
        es(
            "PUT",
            "_security/user/osint_" + role,
            {"password": secret(role), "roles": ["osint_" + role]},
            admin=True,
        )
    es(
        "POST",
        "_security/user/kibana_system/_password",
        {"password": secret("kibana")},
        admin=True,
    )
    response = requests.get(
        f"https://elasticsearch:9200/{INDEX}",
        auth=("elastic", secret("elastic")),
        verify=CA,
        timeout=20,
    )
    if response.status_code == 404:
        es(
            "PUT",
            INDEX,
            {
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "dynamic": "strict",
                    "properties": {
                        "article_id": {"type": "keyword"},
                        "published_at": {"type": "date"},
                        "ciphertext": {"type": "text", "index": False},
                        "content_sha256": {"type": "keyword"},
                        "schema_version": {"type": "integer"},
                        "synthetic": {"type": "boolean"},
                    },
                },
            },
            admin=True,
        )
    else:
        response.raise_for_status()
    print('{"index_configuration":"ready"}')


def index_corpus():
    db, denied = mongo(), tombstones()
    total = 0
    # Only committed SQL IDs may be published. Mongo alone is not a commit signal.
    with pg() as sql:
        cursor = sql.cursor(name="index_cursor")
        cursor.execute(
            "SELECT article_id,content_sha256 FROM articles WHERE synthetic=false ORDER BY article_id"
        )
        while rows := cursor.fetchmany(500):
            expected = dict(rows)
            docs = db.documents.find({"_id": {"$in": list(expected)}})
            lines = []
            for doc in docs:
                key = doc["_id"]
                if key in denied:
                    continue
                if doc["content_sha256"] != expected[key]:
                    raise ValueError("Cross-store checksum mismatch")
                body = {
                    k: doc[k]
                    for k in (
                        "ciphertext",
                        "content_sha256",
                        "schema_version",
                        "synthetic",
                    )
                }
                body["article_id"] = key
                body["published_at"] = (
                    doc["published_at"].replace(tzinfo=timezone.utc).isoformat()
                )
                lines.extend(
                    [
                        json.dumps({"index": {"_index": INDEX, "_id": key}}),
                        json.dumps(body),
                    ]
                )
                total += 1
            if lines:
                result = requests.post(
                    "https://elasticsearch:9200/_bulk",
                    data="\n".join(lines) + "\n",
                    headers={"Content-Type": "application/x-ndjson"},
                    auth=("osint_writer", secret("writer")),
                    verify=CA,
                    timeout=60,
                )
                result.raise_for_status()
                if result.json().get("errors"):
                    raise ValueError("Bulk index partial failure")
    es("POST", INDEX + "/_refresh", admin=True)
    print(json.dumps({"indexed": total, "synthetic": False}))


def erase(article_id):
    with Path("/state/erasures.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return erase_locked(article_id)


def erase_locked(article_id):
    # Durable local suppression ledger is consulted even when SQL is down.
    # No raw personal text is stored in the ledger. Backups must reapply this ledger.
    denied = tombstones() | {article_id}
    private_json("/state/erasures.json", sorted(denied))
    corrections = rectifications()
    if article_id in corrections:
        corrections.pop(article_id)
        private_json("/state/rectifications.json", corrections)
    with pg() as sql:
        if not sql.execute("SELECT pg_try_advisory_lock(420026)").fetchone()[0]:
            raise RuntimeError("Retry erasure after ingestion")
        sql.execute(
            "INSERT INTO erasures(article_id,request_id,status) VALUES(%s,%s,'pending') ON CONFLICT(article_id) DO UPDATE SET status='pending'",
            (article_id, uuid.uuid4()),
        )
        sql.commit()
        mongo().documents.delete_one({"_id": article_id})
        mongo().document_revisions.delete_many({"article_id": article_id})
        r = requests.delete(
            f"https://elasticsearch:9200/{INDEX}/_doc/{article_id}?refresh=true",
            auth=("osint_writer", secret("writer")),
            verify=CA,
            timeout=20,
        )
        if r.status_code not in (200, 404):
            r.raise_for_status()
        sql.execute("DELETE FROM article_revisions WHERE article_id=%s", (article_id,))
        sql.execute("DELETE FROM articles WHERE article_id=%s", (article_id,))
        sql.execute(
            "UPDATE erasures SET status='complete' WHERE article_id=%s", (article_id,)
        )
    invalidate_mentions(article_id)
    print(
        json.dumps(
            {"erased": article_id, "ledger": "persisted", "backup_replay": "required"}
        )
    )


def invalidate_mentions(article_id):
    response = requests.post(
        "https://elasticsearch:9200/osint-entities-v1/_delete_by_query?conflicts=proceed&refresh=true",
        auth=("osint_writer", secret("writer")),
        verify=CA,
        timeout=20,
        json={"query": {"term": {"id": article_id}}},
    )
    if response.status_code != 404:
        response.raise_for_status()


def rectify(path, request_ref):
    """Durable encrypted correction, then idempotent replay and stale-version purge."""
    import re

    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", request_ref):
        raise ValueError("Opaque request reference required")
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("Exactly one normalized corrected article required")
    row = rows[0]
    key = str(row["id"])
    if key in tombstones():
        raise ValueError("Erased article cannot be rectified")
    with Path("/state/erasures.lock").open("a") as gate:
        fcntl.flock(gate, fcntl.LOCK_EX)
        with pg() as sql:
            if not sql.execute("SELECT pg_try_advisory_lock(420026)").fetchone()[0]:
                raise RuntimeError("Retry after ingestion")
            if not sql.execute(
                "SELECT 1 FROM articles WHERE article_id=%s", (key,)
            ).fetchone():
                raise ValueError("Article absent")
            ciphertext, checksum = encrypt(row, key)
            values = rectifications()
            values[key] = {
                "ciphertext": ciphertext,
                "sha256": checksum,
                "request_ref": request_ref,
            }
            private_json("/state/rectifications.json", values)
        # Ingest acquires its own SQL advisory lock and consults the decision just stored.
        ingest(path)
        invalidate_mentions(key)
        doc = mongo().documents.find_one({"_id": key})
        es(
            "PUT",
            INDEX + "/_doc/" + key + "?refresh=true",
            {
                "article_id": key,
                "published_at": doc["published_at"]
                .replace(tzinfo=timezone.utc)
                .isoformat(),
                **{
                    k: doc[k]
                    for k in (
                        "ciphertext",
                        "content_sha256",
                        "schema_version",
                        "synthetic",
                    )
                },
            },
        )
    print(
        json.dumps(
            {
                "rectified": key,
                "request_ref": request_ref,
                "old_versions_purged": True,
                "stale_mentions_removed": True,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    ins = sub.add_parser("ingest")
    ins.add_argument("--file")
    ins.add_argument("--synthetic", type=int, default=0)
    ins.add_argument("--fail-after", type=int, default=0)
    ins.add_argument("--resume")
    for name in ("status", "init-index", "index"):
        sub.add_parser(name)
    e = sub.add_parser("erase")
    e.add_argument("id")
    correction = sub.add_parser("rectify")
    correction.add_argument("--file", required=True)
    correction.add_argument("--request-ref", required=True)
    args = parser.parse_args()
    if args.cmd == "ingest":
        ingest(args.file, args.synthetic, args.fail_after, args.resume)
    elif args.cmd == "status":
        status()
    elif args.cmd == "init-index":
        init_index()
    elif args.cmd == "index":
        index_corpus()
    elif args.cmd == "erase":
        erase(args.id)
    elif args.cmd == "rectify":
        rectify(args.file, args.request_ref)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error_type": type(exc).__name__,
                    "message": "Operation failed; preserve checkpoint and diagnose the service.",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)
