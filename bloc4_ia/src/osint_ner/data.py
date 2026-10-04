"""Deterministic group split and clearly identified weak preannotation."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .contracts import article, atomic_json, digest, file_sha, read_records, write_records

PATTERNS = {
    "WEAPON": r"\b(?:S-400|S-300|Su-\d+(?:SM|S|M)?|MiG-\d+|Tu-\d+(?:M\d?)?|T-\d+(?:B\d?|M)?|Kalibr|Kinzhal|Iskander(?:-M)?|Burevestnik|Zircon|Oniks|HIMARS|Patriot|ATACMS|Lancet|Geran-\d+)\b",
    "MIL_UNIT": r"\b(?:(?:Northern|Black Sea|Baltic|Pacific) Fleet|(?:\d+(?:st|nd|rd|th)\s+)(?:(?:Guards|Motorized|Rifle|Tank|Airborne|Assault|Separate)\s+){0,4}(?:Brigade|Battalion|Regiment|Division|Army))\b",
    "MIL_ORG": r"\b(?:(?:Russian|Russia's|Ukrainian|US) (?:Defense Ministry|Ministry of Defense|Armed Forces)|General Staff|NATO|Pentagon|Russian Aerospace Forces)\b",
}


def weak_spans(text):
    found = []
    for label, pattern in PATTERNS.items():
        found.extend(
            {"start": m.start(), "end": m.end(), "label": label, "text": m.group()}
            for m in re.finditer(pattern, text, re.I)
        )
    # Longest match wins only for preannotation; humans can correct every boundary.
    selected = []
    for s in sorted(found, key=lambda x: (-(x["end"] - x["start"]), x["start"])):
        if all(s["end"] <= p["start"] or s["start"] >= p["end"] for p in selected):
            selected.append(s)
    return sorted(selected, key=lambda x: x["start"])


def canonical(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def group_split(rows):
    """Group exact/canonical text, source IDs, URLs and equal normalized titles.

    Conservative title grouping prevents duplicated dispatches crossing sets.
    Arbitrary paraphrases remain a documented residual risk; they need review.
    """
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        title = canonical(row.get("title", ""))
        keys = [
            ("text", digest(canonical(row["text"]))),
            ("id", str(row["id"])),
            ("url", row["url"]),
        ]
        if title:
            keys.append(("title", title))
        for key in keys:
            if key in seen:
                a, b = find(i), find(seen[key])
                parent[max(a, b)] = min(a, b)
            else:
                seen[key] = i
    members = defaultdict(list)
    for i, row in enumerate(rows):
        members[find(i)].append(row)
    for group in members.values():
        key = min(digest(canonical(r["text"])) for r in group)
        # Stable, corpus-order-independent assignment. New members can merge groups,
        # so each dataset version owns a frozen manifest and cannot reuse an old test.
        bucket = int(digest("osint-v1-seed42:" + key)[:8], 16) % 100
        split = "train" if bucket < 70 else "dev" if bucket < 85 else "test"
        for row in group:
            row.update(group_id=key, split=split)
    return rows


def prepare(corpus, output, train_size=240, dev_size=60, review_size=18):
    output = Path(output)
    rows = group_split([article(r) for r in read_records(corpus)])
    for row in rows:
        row["entities"] = weak_spans(row["text"])
        row["annotation_status"] = "weak_supervision_unreviewed"
    rows.sort(key=lambda r: digest(str(r["id"]) + ":42"))
    chosen = {}
    for split, n in (("train", train_size), ("dev", dev_size), ("test", review_size)):
        candidates = [
            r
            for r in rows
            if r["split"] == split and len(r["text"]) <= (1800 if split == "test" else 5000)
        ]
        bins = defaultdict(list)
        for row in candidates:
            labels = {e["label"] for e in row["entities"]}
            category = next(
                (label for label in ("MIL_UNIT", "WEAPON", "MIL_ORG") if label in labels),
                "negative",
            )
            bins[category].append(row)
        selected = []
        groups = set()
        while len(selected) < n and any(bins.values()):
            for category in ("MIL_UNIT", "WEAPON", "MIL_ORG", "negative"):
                if bins[category] and len(selected) < n:
                    r = bins[category].pop(0)
                    if r["group_id"] not in groups:
                        groups.add(r["group_id"])
                        selected.append(r)
        chosen[split] = selected
        write_records(
            output / ("review_queue.jsonl" if split == "test" else f"{split}.jsonl"), selected
        )
    split_ids = {s: {r["group_id"] for r in batch} for s, batch in chosen.items()}
    assert not any(
        split_ids[a] & split_ids[b]
        for a, b in (("train", "dev"), ("train", "test"), ("dev", "test"))
    )
    write_records(
        output / "split_manifest.jsonl",
        ({k: r[k] for k in ("id", "text_sha256", "group_id", "split")} for r in rows),
    )
    metadata = {
        "corpus_sha256": file_sha(corpus),
        "corpus_count": len(rows),
        "seed": 42,
        "split_counts": dict(Counter(r["split"] for r in rows)),
        "selection_counts": {k: len(v) for k, v in chosen.items()},
        "selected_entities": {
            k: dict(Counter(e["label"] for r in v for e in r["entities"]))
            for k, v in chosen.items()
        },
        "selected_negatives": {k: sum(not r["entities"] for r in v) for k, v in chosen.items()},
        "group_overlap": 0,
        "human_review_count": 0,
        "limitation": "Exact, canonical text, source URL/ID and normalized title groups excluded across splits; semantic paraphrases are not exhaustively detected.",
        "preannotation": "Local lexical rules, incomplete, not reference truth",
        "rule_sha256": digest(json.dumps(PATTERNS, sort_keys=True)),
    }
    atomic_json(output / "manifest.json", metadata)
    return metadata
