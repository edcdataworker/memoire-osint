"""Shared B3/B4 contract: preserve original text and Unicode codepoint offsets."""

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

LABELS = ("WEAPON", "MIL_UNIT", "MIL_ORG")
MAX_TEXT = 100_000


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_sha(path):
    """Hash paths and contents to identify the complete serialized model."""
    h = hashlib.sha256()
    for p in sorted(Path(path).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def read_records(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if line.strip():
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON line {n}") from e
    else:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("Expected JSON array")
        yield from rows


def write_records(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def article(row):
    if not isinstance(row, dict):
        raise ValueError("Article must be an object")
    if row.get("schema_version", 1) != 1:
        raise ValueError("Unsupported schema_version")
    if row.get("offset_unit", "unicode_codepoint") != "unicode_codepoint":
        raise ValueError("Unsupported offset unit")
    text = row.get("text", row.get("body_text"))
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("Text must contain 1 to 100000 characters")
    if "\x00" in text:
        raise ValueError("NUL is forbidden")
    source_id = row.get("id", row.get("article_id"))
    if not isinstance(source_id, (str, int)) or isinstance(source_id, bool):
        raise ValueError("Missing article identifier")
    url = row.get("url", "")
    if not isinstance(url, str) or urlparse(url).scheme not in ("http", "https"):
        raise ValueError("Source URL must be HTTP(S)")
    actual_hash = digest(text)
    if row.get("text_sha256", row.get("content_sha256", actual_hash)) != actual_hash:
        raise ValueError("Text hash mismatch: no renormalization after B3")
    date = row.get("date")
    if date is not None and (
        not isinstance(date, (int, float))
        or isinstance(date, bool)
        or not math.isfinite(date)
        or not 0 <= date <= 4102444800
    ):
        raise ValueError("Date must be epoch seconds or null")
    return {
        **row,
        "id": source_id,
        "text": text,
        "text_sha256": actual_hash,
        "schema_version": 1,
        "offset_unit": "unicode_codepoint",
        "date": date,
    }


def validate_spans(text, spans):
    previous_end = 0
    for span in sorted(spans, key=lambda s: s["start"]):
        start, end, label = span["start"], span["end"], span["label"]
        if type(start) is not int or type(end) is not int:
            raise ValueError("Offsets must be integers")
        if not 0 <= start < end <= len(text) or start < previous_end or label not in LABELS:
            raise ValueError("Invalid, overlapping or unsupported span")
        if span.get("text", text[start:end]) != text[start:end]:
            raise ValueError("Span surface does not match source")
        previous_end = end
    return sorted(spans, key=lambda s: s["start"])
