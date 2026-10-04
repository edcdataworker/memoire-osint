"""Publish immutable releases only after quality passes, with a local redundant copy."""

import json
from pathlib import Path

from .common import atomic_json, event, now, private_dir, sha256


def publish(db, state, run_id):
    state = Path(state)
    release = private_dir(state / "published" / run_id)
    mirror = private_dir(state / "mirror" / run_id)
    # sqlite iteration is bounded; the export uses disk staging, not an in-memory corpus.
    hashes, count = {}, 0
    for name, array in [("articles.jsonl", False), ("articles.json", True)]:
        temporary = release / ("." + name + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            if array:
                stream.write("[\n")
            count = 0
            query = """SELECT payload FROM articles WHERE run_id=?
                       AND article_id NOT IN (SELECT article_id FROM tombstones)
                       ORDER BY record_index"""
            for row in db.execute(query, (run_id,)):
                if array and count:
                    stream.write(",\n")
                stream.write(row["payload"] + ("" if array else "\n"))
                count += 1
            if array:
                stream.write("\n]\n")
            stream.flush()
            import os

            os.fsync(stream.fileno())
        temporary.replace(release / name)
        hashes[name] = sha256(release / name)
        # A second pathname protects against loss of a release file, not host/disk loss.
        import shutil

        with (
            (release / name).open("rb") as source,
            (mirror / name).open("wb") as target,
        ):
            shutil.copyfileobj(source, target, 1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        if sha256(mirror / name) != hashes[name]:
            raise OSError("mirror_verification_failed")
    manifest = {
        "run_id": run_id,
        "published_at": now(),
        "articles": count,
        "sha256": hashes,
        "quality_passed": True,
        "jsonl": str((release / "articles.jsonl").resolve()),
        "json": str((release / "articles.json").resolve()),
        "mirror_jsonl": str((mirror / "articles.jsonl").resolve()),
    }
    atomic_json(release / "manifest.json", manifest)
    atomic_json(mirror / "manifest.json", manifest)
    # This is the only publication switch. An incomplete release never replaces current.
    atomic_json(state / "current.json", manifest)
    event(state, "published", run_id=run_id, articles=count)
    return manifest


def published_path(state, kind="jsonl"):
    """Integrity-checked read with failover to the last committed local mirror."""
    state = Path(state)
    manifest = json.loads((state / "current.json").read_text())
    name = "articles." + kind
    primary = Path(manifest[kind])
    if primary.exists() and sha256(primary) == manifest["sha256"][name]:
        return primary, "primary"
    mirror = state / "mirror" / manifest["run_id"] / name
    if mirror.exists() and sha256(mirror) == manifest["sha256"][name]:
        event(state, "read_failover", run_id=manifest["run_id"])
        return mirror, "mirror"
    raise OSError("No verified publication available")
