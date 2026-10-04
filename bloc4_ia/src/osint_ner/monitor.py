"""Data distribution alerts are distinct from measured prediction quality."""

import math
from collections import Counter

from .contracts import atomic_json, utcnow


def distribution(rows):
    counts = Counter()
    for r in rows:
        size = len(r["text"])
        counts["short" if size < 1000 else "medium" if size < 3000 else "long"] += 1
    total = sum(counts.values())
    if not total:
        raise ValueError("Cannot monitor empty input")
    return {k: counts[k] / total for k in ("short", "medium", "long")}


def js_divergence(a, b):
    total = 0.0
    for key in set(a) | set(b):
        p, q = a.get(key, 0), b.get(key, 0)
        m = (p + q) / 2
        if p:
            total += p * math.log2(p / m) / 2
        if q:
            total += q * math.log2(q / m) / 2
    return total


def monitor(reference, current, output, quality_reference=None, quality_current=None):
    js = js_divergence(distribution(reference), distribution(current))
    data_alert = js > 0.1
    quality_delta = None
    if quality_reference is not None and quality_current is not None:
        if quality_reference["reference_sha256"] != quality_current["reference_sha256"]:
            raise ValueError("Quality comparisons require the same human reference")
        if (
            quality_reference.get("status") != "human_reviewed_small_sample"
            or quality_current.get("status") != "human_reviewed_small_sample"
        ):
            raise ValueError("Quality comparisons require human-reviewed metrics")
        quality_delta = quality_current["global"]["f1"] - quality_reference["global"]["f1"]
    quality_alert = quality_delta is not None and quality_delta < -0.05
    report = {
        "created_at": utcnow(),
        "reference_documents": len(reference),
        "current_documents": len(current),
        "distribution": {
            "feature": "complete article length: <1000 / <3000 / >=3000 codepoints",
            "reference": distribution(reference),
            "current": distribution(current),
            "js_divergence_bits": js,
            "threshold": 0.1,
            "alert": data_alert,
        },
        "quality": {
            "f1_delta": quality_delta,
            "threshold": -0.05,
            "alert": quality_alert,
            "status": "measured"
            if quality_delta is not None
            else "unavailable_without_human_reference",
        },
        "action": "queue_human_review_and_freeze_production_promotion"
        if data_alert or quality_alert
        else "observe",
        "threshold_rationale": "Project heuristics to flag substantial length-distribution change or 5-point quality decline, to calibrate on reviewed operations; not certification thresholds.",
    }
    atomic_json(output, report)
    if data_alert or quality_alert:
        atomic_json(
            str(output) + ".review-request.json",
            {
                "reason": report["action"],
                "created_at": utcnow(),
                "automatic_retraining": "requires new reviewed training data",
                "production_promotion_frozen": True,
            },
        )
    return report
