"""Prepare an explicitly synthetic, disposable CI deployment dataset."""

from pathlib import Path

from osint_ner.contracts import article, digest, write_records
from osint_ner.data import weak_spans
from osint_ner.model import Predictor, train

ROOT = Path(__file__).resolve().parents[1]


def examples(split, count):
    rows = []
    for index in range(count):
        text = (
            f"Synthetic fictional exercise {split} {index}: "
            "NATO and the 12th Guards Rifle Brigade observed a Kalibr display."
        )
        row = article(
            {
                "id": f"ci-{split}-{index}",
                "date": 1735689600 + index,
                "title": f"Synthetic CI fixture {split} {index}",
                "text": text,
                "url": f"https://example.invalid/ci/{split}/{index}",
            }
        )
        row.update(
            entities=weak_spans(text),
            split=split,
            group_id=digest(text),
            annotation_status="synthetic_weak_fixture_unreviewed",
            synthetic=True,
        )
        rows.append(row)
    return rows


def main():
    state = ROOT / ".state"
    run = state / "runs/baseline"
    if run.exists():
        raise SystemExit("Use a clean disposable checkout; existing runs are preserved")
    train_rows, dev_rows = examples("train", 16), examples("dev", 4)
    train_file, dev_file = state / "ci/train.jsonl", state / "ci/dev.jsonl"
    write_records(train_file, train_rows)
    write_records(dev_file, dev_rows)
    (ROOT / "Preuves").mkdir(exist_ok=True)
    train(train_file, dev_file, run, epochs=2, seed=42)
    write_records(state / "inference.jsonl", Predictor(run).predict(dev_rows))
    print("Synthetic CI fixture ready. No TASS data; no human quality claim.")


if __name__ == "__main__":
    main()

