"""Audit selected sets for exact/group leakage and near-duplicate shingle overlap."""

from pathlib import Path
from itertools import combinations
from osint_ner.contracts import read_records, atomic_json
from osint_ner.data import canonical

root = Path(__file__).resolve().parents[1]
batches = {
    s: list(read_records(root / ".state/data" / f"{name}.jsonl"))
    for s, name in [("train", "train"), ("dev", "dev"), ("test", "review_queue")]
}


def shingles(text):
    tokens = canonical(text).split()
    return {tuple(tokens[i : i + 3]) for i in range(max(1, len(tokens) - 2))}


features = {str(r["id"]): shingles(r["text"]) for batch in batches.values() for r in batch}
violations = []
comparisons = 0
maximum = 0
for sa, sb in combinations(batches, 2):
    for a in batches[sa]:
        for b in batches[sb]:
            comparisons += 1
            x, y = features[str(a["id"])], features[str(b["id"])]
            similarity = len(x & y) / len(x | y) if x | y else 0
            maximum = max(maximum, similarity)
            if (
                a["group_id"] == b["group_id"]
                or a["text_sha256"] == b["text_sha256"]
                or similarity >= 0.8
            ):
                violations.append(
                    {"a": a["id"], "b": b["id"], "sets": [sa, sb], "jaccard_3_tokens": similarity}
                )
result = {
    "comparisons": comparisons,
    "near_duplicate_threshold": 0.8,
    "max_cross_split_jaccard": maximum,
    "violations": violations,
    "scope": "Selected train/dev/review queue, exhaustive pair comparisons. Does not guarantee semantic independence or eliminate same-event similarity.",
}
atomic_json(root / "Preuves/split_audit.json", result)
print(result)
if violations:
    raise SystemExit(2)
