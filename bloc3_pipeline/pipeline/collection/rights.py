"""Operator rights workflow. Durable decisions override future recollection."""

import hashlib
import json
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from ..common import atomic_bytes, atomic_json, now
from ..transform import normalize
from . import resilience, store


def ledger(state):
    path = Path(state) / "rights.json"
    return json.loads(path.read_text()) if path.exists() else {"erased": [], "corrections": {}}


def reference(value):
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", value):
        raise ValueError("Utiliser une référence de dossier opaque (sans coordonnées).")
    return value


def access(state, identifier, request_ref):
    reference(request_ref)
    denied = store.external_denied(state)
    with store.read_database(state) as db:
        rows = db.execute(
            "SELECT payload FROM revisions WHERE article_id=? ORDER BY collected DESC",
            (str(identifier),),
        ).fetchall()
    values = (
        []
        if str(identifier) in denied
        else list(store.visible_rows(state, (json.loads(r[0]) for r in rows)))
    )
    audit(
        state,
        "rights_access",
        article_id=str(identifier),
        request_ref=request_ref,
        matches=len(values),
    )
    return {"article_id": str(identifier), "revisions": values}


def audit(state, kind, **fields):
    fields.setdefault("result", "success")
    try:
        resilience.require_primary(state)
        store.emit(state, None, kind, **fields)
    except (OSError, ValueError, sqlite3.Error):
        from ..common import event

        event(state, kind, **fields)


def rewrite_exports(state, decisions):
    """Purge managed snapshots; downloaded external copies need coordination."""
    for path in (Path(state) / "exports").glob("*/manifest.json"):
        manifest = json.loads(path.read_text())
        data = json.loads((path.parent / "articles.json").read_text())
        values = []
        for row in data:
            key = str(row["id"])
            if key in decisions["erased"]:
                continue
            if key in decisions["corrections"]:
                row = decisions["corrections"][key]["row"]
                row = {**row, "revision_sha256": store.revision(row)}
            values.append(row)
        atomic_json(path.parent / "articles.json", values)
        atomic_bytes(
            path.parent / "articles.jsonl",
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in values).encode(),
        )
        manifest.update(
            articles=len(values),
            rights_applied_at=now(),
            sha256={
                kind: store.sha256(path.parent / ("articles." + kind)) for kind in ("json", "jsonl")
            },
        )
        atomic_json(path, manifest)
        current = Path(state) / "current.json"
        if (
            current.exists()
            and json.loads(current.read_text())["export_id"] == manifest["export_id"]
        ):
            atomic_json(current, manifest)


def reapply(state, config):
    decisions = ledger(state)
    store.sync_denied(state, config)
    with store.database(state) as db, db:
        for key, decision in decisions["corrections"].items():
            if key in decisions["erased"]:
                continue
            db.execute("DELETE FROM heads WHERE article_id=?", (key,))
            db.execute("DELETE FROM revisions WHERE article_id=?", (key,))
            db.execute("UPDATE tasks SET payload=NULL,status='filtered' WHERE article_id=?", (key,))
            row = decision["row"]
            db.execute(
                "INSERT INTO corrections VALUES(?,?) ON CONFLICT(article_id) DO UPDATE SET payload=excluded.payload",
                (key, json.dumps(row, ensure_ascii=False)),
            )
            store.put(db, row)
        for key in decisions["erased"]:
            db.execute("DELETE FROM corrections WHERE article_id=?", (key,))
    rewrite_exports(state, decisions)


def rectify(state, config, identifier, changes, request_ref):
    resilience.require_primary(state)
    reference(request_ref)
    if set(changes) - {"text", "title"} or not changes:
        raise ValueError("Seuls titre et texte peuvent être rectifiés.")
    key = str(identifier)
    values = access(state, key, request_ref)["revisions"]
    if not values:
        raise ValueError("Article absent ou supprimé.")
    item = {**values[0], **changes}
    fingerprint = hashlib.sha256(json.dumps(changes, sort_keys=True).encode()).hexdigest()
    row = normalize(item, fingerprint, 0, "rights-" + request_ref, "raw")
    row["provenance"].update(rectification_ref=request_ref, rectified_at=now())
    decisions = ledger(state)
    decisions["corrections"][key] = {"row": row, "request_ref": request_ref}
    atomic_json(Path(state) / "rights.json", decisions)
    reapply(state, config)
    resilience.compact(state)
    resilience.refresh(state)
    audit(
        state,
        "rights_rectified",
        article_id=key,
        request_ref=request_ref,
        revision=store.revision(row),
        external_coordination="required",
    )
    return {"article_id": key, "rectified": True, "revision": store.revision(row)}


def erase(state, config, identifier, request_ref):
    resilience.require_primary(state)
    reference(request_ref)
    key = str(identifier)
    decisions = ledger(state)
    decisions["erased"] = sorted(set(decisions["erased"]) | {key})
    decisions["corrections"].pop(key, None)
    atomic_json(Path(state) / "rights.json", decisions)
    reapply(state, config)
    resilience.compact(state)
    resilience.refresh(state)
    audit(
        state,
        "rights_erased",
        article_id=key,
        request_ref=request_ref,
        external_coordination="required",
    )
    return {"article_id": key, "erased": True, "external_coordination": "required"}


def propagate_b2(state, config, identifier, request_ref, erased=False):
    """Explicit, repeatable cross-store operation. Failed propagation stays visible."""
    key = str(identifier)
    pending = {"article_id": key, "request_ref": request_ref, "status": "pending", "at": now()}
    path = Path(state) / "rights-propagation.json"
    atomic_json(path, pending)
    try:
        with tempfile.TemporaryDirectory(dir=state, prefix="rights-") as directory:
            prefix = [
                "docker",
                "compose",
                "run",
                "--rm",
                "-T",
                "--volume",
                directory + ":/rights:ro",
                "ops",
            ]
            if erased:
                command = prefix + ["python", "-m", "osint.cli", "erase", key]
            else:
                row = ledger(state)["corrections"][key]["row"]
                atomic_json(Path(directory) / "corrected.json", [row])
                command = prefix + [
                    "python",
                    "-m",
                    "osint.cli",
                    "rectify",
                    "--file",
                    "/rights/corrected.json",
                    "--request-ref",
                    request_ref,
                ]
            with (Path(state) / "b2-rights.log").open("a") as log:
                result = subprocess.run(
                    command, cwd=config["b2_root"], stdout=log, stderr=log, timeout=120
                )
            if result.returncode:
                raise OSError("Propagation B2 incomplète ; consulter le journal privé et rejouer.")
        pending.update(status="complete", at=now())
        atomic_json(path, pending)
        audit(state, "rights_b2_propagated", article_id=key, request_ref=request_ref)
        return {"status": "complete", "annotations_and_external_copies": "coordinated separately"}
    except (OSError, subprocess.SubprocessError):
        pending.update(status="failed", at=now())
        atomic_json(path, pending)
        raise
