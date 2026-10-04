"""Explicit input contract and minimal cleaning before any annotation."""

import hashlib
import math
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

NORMALIZATION_VERSION = "tass-minimal-v1"


def clean_text(text):
    """Reproduce recovered N04 cleaning exactly; never apply this after annotation."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", re.sub(r"\s+", " ", text)).strip()


def normalize(item, source_sha256, index, run_id, mode="clean"):
    if not isinstance(item, dict) or item.get("_parse_error"):
        raise ValueError("invalid_record")
    identifier = item.get("id")
    if (
        isinstance(identifier, bool)
        or not isinstance(identifier, (str, int))
        or not str(identifier).strip()
    ):
        raise ValueError("invalid_id")
    timestamp = item.get("date")
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, (int, float))
        or not math.isfinite(timestamp)
    ):
        raise ValueError("invalid_date")
    try:
        readable = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        raise ValueError("invalid_date") from None
    title, text = item.get("title") or "", item.get("text")
    if not isinstance(title, str):
        raise ValueError("invalid_title")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty_text")
    original_text = text
    if mode == "raw":
        text = clean_text(text)
    elif clean_text(text) != text:
        raise ValueError("clean_contract_violation")
    if not text:
        raise ValueError("empty_text")
    url = item.get("url")
    if mode == "raw" and not url:
        url = "https://tass.com" + str(item.get("link", ""))
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("invalid_url")
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # IDs and epoch values retain their source JSON type; SQLite keys use str(id).
    return {
        "id": identifier,
        "date": timestamp,
        "date_readable": readable,
        "title": title.strip(),
        "text": text,
        "url": url,
        "source_id": "tass",
        "schema_version": 1,
        "text_sha256": text_hash,
        "offset_unit": "unicode_codepoint",
        "provenance": {
            "source_sha256": source_sha256,
            "source_record_index": index,
            "pipeline_run_id": run_id,
            "normalization_version": NORMALIZATION_VERSION,
            "input_mode": mode,
            "raw_text_sha256": hashlib.sha256(original_text.encode()).hexdigest(),
            "text_changed": original_text != text,
        },
    }
