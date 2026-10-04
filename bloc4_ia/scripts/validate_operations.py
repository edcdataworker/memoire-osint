"""Run local model lifecycle demonstrations and preserve auditable evidence."""

import json
import shutil
from pathlib import Path
from osint_ner.automation import watch
from osint_ner.contracts import article, atomic_json, read_records, write_records, tree_sha, utcnow
from osint_ner.metrics import require_reviewed
from osint_ner.model import Predictor
from osint_ner.monitor import monitor
from osint_ner.registry import promote, rollback

root = Path(__file__).resolve().parents[1]
state = root / ".state/automation_demo"
scheduler = state / "scheduler"
train = list(read_records(root / ".state/data/train.jsonl"))
write_records(state / "train.jsonl", train[:25])
watch(
    state / "train.jsonl",
    state / "dev.jsonl",
    scheduler,
    cycles=1,
    interval=0.1,
    demo=True,
    epochs=2,
)
shutil.copyfile(scheduler / "events.jsonl", root / "Preuves/retraining_events.jsonl")
run = Path(json.loads((scheduler / "scheduler.json").read_text())["last_run"])
registry = root / ".state/model_registry"
first = promote(root / ".state/runs/baseline", registry, "demo")
second = promote(run, registry, "demo")
rolled = rollback(registry, "demo")
blocked = promote(root / ".state/runs/baseline", registry, "production")
atomic_json(
    root / "Preuves/promotion_rollback.json",
    {"first_demo": first, "second_demo": second, "rollback": rolled, "production": blocked},
)
reference = list(read_records(root / ".state/data/train.jsonl"))
current = list(read_records(root / ".state/inference.jsonl"))
monitor(reference, current, root / "Preuves/monitor_current.json")
monitor(
    [{"text": "a" * 500}] * 20,
    [{"text": "a" * 5000}] * 20,
    root / "Preuves/monitor_synthetic_shift.json",
)
# A malformed schema is rejected by the real data contract, not silently coerced.

schema_error = None
try:
    article({**train[0], "schema_version": 2})
except ValueError as exc:
    schema_error = str(exc)
p = Predictor(root / ".state/runs/baseline")
a = list(p.predict(current[:5]))
b = list(p.predict(current[:5]))
for batch in (a, b):
    for row in batch:
        row.pop("processed_at")
previous_model = root / ".state/runs/baseline_report_failed/model"
repro = {
    "same_environment_prediction_identity": a == b,
    "sample_count": 5,
    "baseline_sha256": p.meta["model_sha256"],
    "previous_training_model_sha256": tree_sha(previous_model) if previous_model.exists() else None,
    "note": "The first completed training produced a model but its report serialization failed. It is retained only to compare two actual seeded training artifacts, never as a successful end-to-end run.",
    "schema_version_2_error": schema_error,
    "at": utcnow(),
}
repro["same_environment_training_model_identity"] = (
    repro["baseline_sha256"] == repro["previous_training_model_sha256"]
)
atomic_json(root / "Preuves/reproducibility.json", repro)
try:
    require_reviewed(list(read_records(root / ".state/data/review_queue.jsonl")))
except ValueError as exc:
    atomic_json(
        root / "Preuves/quality_gate.json",
        {
            "status": "blocked",
            "reason": str(exc),
            "global": None,
            "per_label": {"WEAPON": None, "MIL_UNIT": None, "MIL_ORG": None},
        },
    )
print(json.dumps(repro, indent=2))
