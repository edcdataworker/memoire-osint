from pathlib import Path
import json
from osint_ner.contracts import read_records

root = Path(__file__).resolve().parents[1]
rows = list(read_records(root / ".state/data/review_queue.jsonl"))
# Escape HTML parser terminators inside embedded untrusted source strings.
payload = (
    json.dumps(rows, ensure_ascii=False)
    .replace("<", "\\u003c")
    .replace(">", "\\u003e")
    .replace("&", "\\u0026")
)
template = (root / "web/review_template.html").read_text()
(root / "Revue_annotations_locale.html").write_text(template.replace("__DATA__", payload))
print(root / "Revue_annotations_locale.html")
