"""SQLite is the local control/staging store, not the Bloc 2 business authority."""

import sqlite3

from .common import private_dir


def connect(state):
    db = sqlite3.connect(private_dir(state) / "pipeline.sqlite", timeout=2)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL, config_sha256 TEXT NOT NULL,
      source_name TEXT NOT NULL, status TEXT NOT NULL, checkpoint INTEGER NOT NULL DEFAULT 0,
      accepted INTEGER NOT NULL DEFAULT 0, rejected INTEGER NOT NULL DEFAULT 0,
      duplicates INTEGER NOT NULL DEFAULT 0, suppressed INTEGER NOT NULL DEFAULT 0,
      started_at TEXT NOT NULL, updated_at TEXT NOT NULL, processing_s REAL NOT NULL DEFAULT 0,
      attempts INTEGER NOT NULL DEFAULT 0, synthetic INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS articles (
      run_id TEXT NOT NULL REFERENCES runs(run_id), record_index INTEGER NOT NULL,
      article_id TEXT NOT NULL, text_sha256 TEXT NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(run_id, article_id), UNIQUE(run_id,text_sha256)
    );
    CREATE INDEX IF NOT EXISTS articles_run_order ON articles(run_id,record_index);
    CREATE TABLE IF NOT EXISTS rejects (
      run_id TEXT NOT NULL, record_index INTEGER NOT NULL, reason TEXT NOT NULL,
      PRIMARY KEY(run_id,record_index)
    );
    CREATE TABLE IF NOT EXISTS tombstones (
      article_id TEXT PRIMARY KEY, at TEXT NOT NULL, request_ref TEXT NOT NULL
    );
    """)
    return db
