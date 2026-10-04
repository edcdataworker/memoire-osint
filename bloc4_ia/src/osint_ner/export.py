"""Separate ES mention index and local erasure, never modify B2 mappings."""

import json
from pathlib import Path
from .contracts import digest, read_records, write_records, utcnow, atomic_json, validate_spans


def exclusions(path):
    if not path:
        return set()
    value = json.loads(Path(path).read_text())
    # B2 export is explicit: array of article ids or {article_ids:[...]}.
    if isinstance(value, dict):
        value = value["article_ids"]
    if not isinstance(value, list):
        raise ValueError("Exclusion registry must contain an article_ids array")
    return {str(v) for v in value}


def export_bulk(source, output, exclusion_path=None, index="osint-entities-v1"):
    if index != "osint-entities-v1":
        raise ValueError("Only the dedicated B4 index is allowed")
    excluded = exclusions(exclusion_path)
    count, articles = 0, 0
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w") as f:
        for row in read_records(source):
            if str(row["id"]) in excluded:
                continue
            articles += 1
            for e in validate_spans(row["text"], row["entities"]):
                key = digest(
                    f"{row['id']}:{row['text_sha256']}:{row['model_sha256']}:{e['start']}:{e['end']}:{e['label']}"
                )
                value = {
                    "id": str(row["id"]),
                    "date": row.get("date"),
                    "url": row["url"],
                    "text_sha256": row["text_sha256"],
                    "model_version": row["model_version"],
                    "model_sha256": row["model_sha256"],
                    "annotation_status": row["annotation_status"],
                    "entity": e["text"],
                    "label": e["label"],
                    "start": e["start"],
                    "end": e["end"],
                    "offset_unit": "unicode_codepoint",
                }
                f.write(json.dumps({"index": {"_index": index, "_id": key}}) + "\n")
                f.write(json.dumps(value, ensure_ascii=False) + "\n")
                count += 1
    temp.replace(path)
    return {
        "mentions": count,
        "articles": articles,
        "excluded_ids": len(excluded),
        "index": index,
        "indexing_status": "bulk_file_only_not_yet_sent",
    }


def erase(source, article_id, output, log_path):
    kept = []
    removed = 0
    for row in read_records(source):
        if str(row["id"]) == str(article_id):
            removed += 1
        else:
            kept.append(row)
    write_records(output, kept)
    event = {
        "at": utcnow(),
        "article_id": str(article_id),
        "removed_records": removed,
        "scope": "local export",
        "model_retraining_required": True,
        "followup": "Purge review data, training sets, source artifacts, snapshots and ES mentions; invalidate affected models through registry.",
    }
    atomic_json(log_path, event)
    return event
