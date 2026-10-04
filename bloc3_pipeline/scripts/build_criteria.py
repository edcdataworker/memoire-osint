"""Validate exact Bloc 3 criteria and rebuild the candid assessment."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / "docs/criteres_exacts_Bloc3.json").read_text())
assessment = json.loads((ROOT / "docs/criteres_evaluation_Bloc3.json").read_text())
assert len(source) == len(assessment) == 33
for original, current in zip(source, assessment, strict=True):
    for field in ("id", "source", "critere_exact"):
        assert original[field] == current[field]
    if original["oral"]:
        assert current["statut"] == "prévu", "Observe a personal rehearsal first"
(ROOT / "Correspondance_criteres_Bloc3.json").write_text(
    json.dumps(assessment, ensure_ascii=False, indent=2) + "\n"
)
