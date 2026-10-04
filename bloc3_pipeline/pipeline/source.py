"""Read JSON arrays incrementally or JSONL without loading the corpus in memory."""

import json
from pathlib import Path


def records(path):
    """Yield physical record index and value. Invalid JSONL is isolated as a reject."""
    path = Path(path)
    if path.suffix.lower() in (".jsonl", ".ndjson"):
        with path.open(encoding="utf-8") as stream:
            for index, line in enumerate(stream):
                try:
                    yield index, json.loads(line)
                except json.JSONDecodeError:
                    yield index, {"_parse_error": "invalid_jsonl"}
        return
    decoder = json.JSONDecoder()
    with path.open(encoding="utf-8") as stream:
        buffer, position, eof = "", 0, False

        def fill():
            nonlocal buffer, position, eof
            buffer = buffer[position:] + stream.read(65536)
            position = 0
            eof = not buffer or stream.tell() == path.stat().st_size

        def whitespace():
            nonlocal position
            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position < len(buffer) or eof:
                    return
                fill()

        fill()
        whitespace()
        if position >= len(buffer) or buffer[position] != "[":
            raise ValueError("JSON source must be an array")
        position += 1
        index = 0
        whitespace()
        if position < len(buffer) and buffer[position] == "]":
            position += 1
        else:
            while True:
                whitespace()
                while True:
                    try:
                        value, stop = decoder.raw_decode(buffer, position)
                        break
                    except json.JSONDecodeError:
                        if eof:
                            raise ValueError("Malformed JSON array") from None
                        fill()
                yield index, value
                index += 1
                position = stop
                whitespace()
                if position < len(buffer) and buffer[position] == "]":
                    position += 1
                    break
                if position >= len(buffer) or buffer[position] != ",":
                    raise ValueError("Expected comma between JSON records")
                position += 1
        whitespace()
        if position != len(buffer):
            raise ValueError("Trailing content after JSON array")
