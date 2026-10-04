"""Exact-match entity scoring: label AND both boundaries must agree."""

from .contracts import LABELS, validate_spans


def score(gold, predicted):
    if len(gold) != len(predicted):
        raise ValueError("Unequal number of reference and prediction documents")
    counts = {label: {"tp": 0, "fp": 0, "fn": 0} for label in LABELS}
    errors = []
    for ref, pred in zip(gold, predicted):
        if str(ref["id"]) != str(pred["id"]) or ref["text_sha256"] != pred["text_sha256"]:
            raise ValueError("Reference and prediction identity mismatch")
        truth = {
            (e["start"], e["end"], e["label"]) for e in validate_spans(ref["text"], ref["entities"])
        }
        guess = {
            (e["start"], e["end"], e["label"])
            for e in validate_spans(ref["text"], pred["entities"])
        }
        for label in LABELS:
            t, g = {e for e in truth if e[2] == label}, {e for e in guess if e[2] == label}
            counts[label]["tp"] += len(t & g)
            counts[label]["fp"] += len(g - t)
            counts[label]["fn"] += len(t - g)
        for kind, values in (("false_positive", guess - truth), ("false_negative", truth - guess)):
            for start, end, label in sorted(values):
                errors.append(
                    {
                        "id": ref["id"],
                        "type": kind,
                        "start": start,
                        "end": end,
                        "label": label,
                        "text": ref["text"][start:end],
                    }
                )

    def summarize(c):
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        return {
            **c,
            "support": tp + fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        }

    return {
        "global": summarize({k: sum(c[k] for c in counts.values()) for k in ("tp", "fp", "fn")}),
        "per_label": {k: summarize(c) for k, c in counts.items()},
        "errors": errors,
        "documents": len(gold),
        "definition": "Exact spans and labels, micro global; undefined denominators are null",
    }


def require_reviewed(rows):
    if not rows:
        raise ValueError("No human-reviewed reference available")
    for r in rows:
        if (
            r.get("annotation_status") != "human_reviewed"
            or not isinstance(r.get("reviewer"), str)
            or not r["reviewer"].strip()
            or not isinstance(r.get("reviewed_at"), str)
            or not r["reviewed_at"].strip()
        ):
            raise ValueError("Every reference needs explicit human review provenance")
        if r.get("split") != "test":
            raise ValueError("Quality evaluation only accepts reserved test articles")
        validate_spans(r["text"], r["entities"])
