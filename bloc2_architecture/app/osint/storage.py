"""TLS clients and authenticated encryption for textual payloads."""

import base64
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import psycopg
from pymongo import MongoClient
import requests

CA = "/run/secrets/ca.crt"
INDEX = "osint-articles-v1"


@lru_cache(maxsize=16)
def secret(name):
    return Path("/run/secrets", name).read_text().strip()


def pg(role=None, db="osint"):
    role = role or os.getenv("DB_ROLE", "writer")
    return psycopg.connect(
        host="postgres",
        dbname=db,
        user="osint_" + role,
        password=secret(role),
        sslmode="verify-full",
        sslrootcert=CA,
        connect_timeout=3,
    )


@lru_cache(maxsize=4)
def mongo(role=None):
    role = role or os.getenv("DB_ROLE", "writer")
    return MongoClient(
        "mongo",
        username="osint_" + role,
        password=secret(role),
        authSource="osint",
        tls=True,
        tlsCAFile=CA,
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=3000,
        socketTimeoutMS=300000 if role == "writer" else 30000,
    )["osint"]


def es(method, path, body=None, admin=False):
    role = os.getenv("DB_ROLE", "writer")
    auth = ("elastic", secret("elastic")) if admin else ("osint_" + role, secret(role))
    r = requests.request(
        method,
        "https://elasticsearch:9200/" + path,
        auth=auth,
        verify=CA,
        json=body,
        timeout=20,
    )
    r.raise_for_status()
    return r.json() if r.content else {}


def encrypt(payload, article_id):
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    nonce = os.urandom(12)
    data = AESGCM(base64.b64decode(secret("data_key"))).encrypt(
        nonce, raw, article_id.encode()
    )
    return base64.b64encode(nonce + data).decode(), hashlib.sha256(raw).hexdigest()


def decrypt(ciphertext, article_id):
    raw = base64.b64decode(ciphertext)
    plain = AESGCM(base64.b64decode(secret("data_key"))).decrypt(
        raw[:12], raw[12:], article_id.encode()
    )
    return json.loads(plain)


def tombstones():
    path = Path("/state/erasures.json")
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()))
