"""Run inside ops on the dedicated OSINT stack; do not target another project."""

import json
from pathlib import Path
import psycopg
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
from cryptography.exceptions import InvalidTag
from osint.storage import decrypt, mongo, pg, secret

results = []


def check(name, callback):
    callback()
    results.append({"test": name, "status": "passed"})


def reader_sql():
    with pg("reader") as c:
        try:
            c.execute("DELETE FROM articles WHERE article_id='__fixture__'")
        except psycopg.errors.InsufficientPrivilege:
            return
        raise AssertionError("Reader can delete")


def reader_mongo():
    try:
        mongo("reader").documents.delete_one({"_id": "__fixture__"})
    except OperationFailure as exc:
        assert exc.code == 13
        return
    raise AssertionError("Reader can delete")


def no_plaintext_sql():
    try:
        psycopg.connect(
            host="postgres",
            dbname="osint",
            user="osint_reader",
            password=secret("reader"),
            sslmode="disable",
            connect_timeout=3,
        )
    except psycopg.OperationalError:
        return
    raise AssertionError("Plaintext connection allowed")


def no_plaintext_mongo():
    try:
        MongoClient("mongo", serverSelectionTimeoutMS=2000).osint.documents.find_one()
    except ServerSelectionTimeoutError:
        return
    raise AssertionError("Plaintext Mongo allowed")


def foreign_key():
    with pg() as c:
        try:
            c.execute(
                "UPDATE articles SET source_id='unknown' WHERE article_id='2035207'"
            )
        except psycopg.errors.ForeignKeyViolation:
            return
        raise AssertionError("Missing FK protection")


def mongo_schema():
    try:
        mongo().documents.insert_one({"_id": "__invalid__", "ciphertext": "bad"})
    except OperationFailure as exc:
        assert exc.code == 121
        return
    raise AssertionError("Invalid document accepted")


def integrity():
    source = json.loads(Path("/data/corpus_clean.json").read_text())
    with pg() as c:
        data = dict(
            c.execute(
                "SELECT article_id,content_sha256 FROM articles WHERE synthetic=false"
            ).fetchall()
        )
    docs = list(mongo().documents.find({"synthetic": False}))
    assert len(source) == 21676
    assert len(data) == len(docs) >= len(source)
    assert all(d["content_sha256"] == data[d["_id"]] for d in docs)
    by_id = {str(x["id"]): x for x in source}
    assert set(by_id).issubset(data)
    for d in docs[::430]:
        plain = decrypt(d["ciphertext"], d["_id"])
        if d["_id"] in by_id:
            expected = {k: by_id[d["_id"]][k] for k in ("title", "text", "url")}
            versions = [plain] + [
                decrypt(v["ciphertext"], d["_id"])
                for v in mongo().document_revisions.find({"article_id": d["_id"]})
            ]
            assert any({k: v[k] for k in expected} == expected for v in versions)
        assert "text" not in d and "title" not in d


def authenticated_encryption():
    d = mongo().documents.find_one({"synthetic": False})
    try:
        decrypt(d["ciphertext"], "wrong-id")
    except InvalidTag:
        return
    raise AssertionError("Ciphertext not bound to ID")


for name, fn in [
    ("SQL reader cannot write", reader_sql),
    ("Mongo reader cannot write", reader_mongo),
    ("SQL rejects plaintext TCP", no_plaintext_sql),
    ("Mongo rejects plaintext TCP", no_plaintext_mongo),
    ("SQL enforces foreign key", foreign_key),
    ("Mongo validates required fields", mongo_schema),
    (
        "Historical corpus preserved, all cross-store hashes and decrypted samples",
        integrity,
    ),
    ("AES-GCM authenticates identifier", authenticated_encryption),
]:
    check(name, fn)
Path("/evidence/Integration_collecte_TASS.json").write_text(
    json.dumps(results, indent=2)
)
print(json.dumps(results))
