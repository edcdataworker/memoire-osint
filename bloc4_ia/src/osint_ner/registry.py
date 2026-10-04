"""Atomic local promotion with explicit environment and reversible history."""

import json
from pathlib import Path

from .contracts import LABELS, atomic_json, tree_sha, utcnow


def gate(meta, quality, minimum_docs=100, minimum_support=20):
    reasons = []
    if meta.get("annotation_status") != "human_reviewed_training":
        reasons.append("training_annotations_not_human_reviewed")
    if not quality or quality.get("status") != "human_reviewed_small_sample":
        reasons.append("missing_human_quality_reference")
        return reasons
    if quality.get("model_sha256") != meta["model_sha256"]:
        reasons.append("quality_model_checksum_mismatch")
    if quality.get("documents", 0) < minimum_docs:
        reasons.append("insufficient_test_documents")
    if (quality.get("global", {}).get("f1") or 0) < 0.70:
        reasons.append("global_f1_below_project_threshold")
    for label in LABELS:
        m = quality.get("per_label", {}).get(label, {})
        if m.get("support", 0) < minimum_support or (m.get("recall") or 0) < 0.50:
            reasons.append(f"insufficient_support_or_recall:{label}")
    return reasons


def promote(run, registry, environment="production", quality=None, frozen=False):
    run, registry = Path(run).resolve(), Path(registry)
    meta = json.loads((run / "training.json").read_text())
    if tree_sha(run / "model") != meta["model_sha256"]:
        raise ValueError("Corrupt model cannot be promoted")
    if environment not in ("demo", "production"):
        raise ValueError("Unknown environment")
    reasons = gate(meta, quality) if environment == "production" else []
    if frozen and environment == "production":
        reasons.append("drift_freeze")
    event = {
        "created_at": utcnow(),
        "environment": environment,
        "candidate": str(run),
        "model_sha256": meta["model_sha256"],
        "accepted": not reasons,
        "reasons": reasons,
    }
    registry.mkdir(parents=True, exist_ok=True)
    if not reasons:
        pointer = registry / f"{environment}.json"
        previous = json.loads(pointer.read_text()) if pointer.exists() else None
        atomic_json(pointer, {**event, "previous": previous})
    with (registry / "events.jsonl").open("a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def rollback(registry, environment="demo"):
    pointer = Path(registry) / f"{environment}.json"
    current = json.loads(pointer.read_text())
    previous = current.get("previous")
    if not previous:
        raise ValueError("No previous version to roll back to")
    if tree_sha(Path(previous["candidate"]) / "model") != previous["model_sha256"]:
        raise ValueError("Rollback target is corrupt")
    atomic_json(pointer, previous)
    return {
        "rolled_back_at": utcnow(),
        "from": current["model_sha256"],
        "to": previous["model_sha256"],
    }
