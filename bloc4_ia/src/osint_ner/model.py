"""CPU spaCy training and source-preserving batch inference."""

import json
import platform
import random
import time
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.training import Example
from spacy.util import fix_random_seed, minibatch, compile_infix_regex

from .contracts import (
    LABELS,
    article,
    atomic_json,
    file_sha,
    read_records,
    tree_sha,
    utcnow,
    validate_spans,
)
from .metrics import require_reviewed, score


def examples(nlp, rows):
    result = []
    for r in rows:
        spans = validate_spans(r["text"], r["entities"])
        doc = nlp.make_doc(r["text"])
        for s in spans:
            if doc.char_span(s["start"], s["end"], alignment_mode="strict") is None:
                raise ValueError(f"Unaligned annotation in article {r['id']}")
        result.append(
            Example.from_dict(
                doc, {"entities": [(s["start"], s["end"], s["label"]) for s in spans]}
            )
        )
    return result


def train(data_path, dev_path, output, epochs=6, seed=42):
    start = time.perf_counter()
    output = Path(output)
    if output.exists():
        raise ValueError("Model output already exists; preserve immutable runs")
    train_rows = [article(r) for r in read_records(data_path)]
    dev_rows = [article(r) for r in read_records(dev_path)]
    if any(r.get("split") != "train" for r in train_rows) or any(
        r.get("split") != "dev" for r in dev_rows
    ):
        raise ValueError("Train/dev must use their frozen manifest partitions")
    if not train_rows or not dev_rows:
        raise ValueError("Train and dev must both contain examples")
    if {r["group_id"] for r in train_rows} & {r["group_id"] for r in dev_rows}:
        raise ValueError("Train/dev group leakage")
    spacy.require_cpu()
    fix_random_seed(seed)
    nlp = spacy.blank("en")
    # Some source articles omit spaces after punctuation, e.g. ATACMS),The.
    # Split punctuation explicitly without altering a single source character.
    nlp.tokenizer.infix_finditer = compile_infix_regex(
        list(nlp.Defaults.infixes) + [r"[(),]"]
    ).finditer
    ner = nlp.add_pipe("ner")
    for label in LABELS:
        ner.add_label(label)
    train_examples, dev_examples = examples(nlp, train_rows), examples(nlp, dev_rows)
    optimizer = nlp.initialize(lambda: train_examples)
    history = []
    rng = random.Random(seed)
    for epoch in range(epochs):
        rng.shuffle(train_examples)
        losses = {}
        for batch in minibatch(train_examples, size=16):
            nlp.update(batch, sgd=optimizer, drop=0.2, losses=losses)
        history.append({"epoch": epoch + 1, "training_loss": float(losses["ner"])})
    version = "weak-" + file_sha(data_path)[:10] + f"-s{seed}-e{epochs}"
    nlp.meta.update(
        name="osint_ner_weak_demo",
        version="0.1.0",
        description="Weak supervision demonstration; no validated accuracy",
    )
    output.mkdir(parents=True)
    nlp.to_disk(output / "model")
    for name, batch in (("train", train_examples), ("dev", dev_examples)):
        DocBin(docs=[ex.reference for ex in batch], store_user_data=True).to_disk(
            output / f"{name}.spacy"
        )
    report = {
        "model_version": version,
        "model_sha256": tree_sha(output / "model"),
        "spacy_version": spacy.__version__,
        "python_version": platform.python_version(),
        "initialization": "spacy.blank('en'); random weights; no transfer learning",
        "seed": seed,
        "epochs": epochs,
        "dropout": 0.2,
        "batch_size": 16,
        "train_sha256": file_sha(data_path),
        "dev_sha256": file_sha(dev_path),
        "train_documents": len(train_rows),
        "dev_documents": len(dev_rows),
        "annotation_status": "human_reviewed_training"
        if all(
            r.get("annotation_status") == "human_reviewed"
            and r.get("reviewer")
            and r.get("reviewed_at")
            for r in train_rows
        )
        else "weak_supervision_demo",
        "history": history,
        "training_groups": sorted({r["group_id"] for r in train_rows}),
        "dev_groups": sorted({r["group_id"] for r in dev_rows}),
        "duration_seconds": round(time.perf_counter() - start, 3),
        "created_at": utcnow(),
        "quality_metrics": {"global": None, "per_label": {label: None for label in LABELS}},
        "quality_status": "unavailable_without_independent_human_reference",
        "selection": "Fixed epochs; no quality selection using same-rule dev labels",
    }
    atomic_json(output / "training.json", report)
    return report


class Predictor:
    def __init__(self, run):
        self.run = Path(run)
        self.meta = json.loads((self.run / "training.json").read_text())
        actual = tree_sha(self.run / "model")
        if actual != self.meta["model_sha256"]:
            raise ValueError("Model checksum mismatch")
        self.nlp = spacy.load(self.run / "model")
        self.nlp.max_length = 100_001

    def predict(self, rows):
        rows = [article(r) for r in rows]
        for r, doc in zip(
            rows, self.nlp.pipe((r["text"] for r in rows), batch_size=16, n_process=1)
        ):
            spans = [
                {"text": e.text, "label": e.label_, "start": e.start_char, "end": e.end_char}
                for e in doc.ents
            ]
            validate_spans(r["text"], spans)
            yield {
                **r,
                "entities": spans,
                "model_version": self.meta["model_version"],
                "model_sha256": self.meta["model_sha256"],
                "annotation_status": "weak_supervision_demo",
                "processed_at": utcnow(),
                "inference_scope": "complete_text",
            }


def evaluate(run, reference_path, manifest_path):
    rows = [article(r) for r in read_records(reference_path)]
    require_reviewed(rows)
    if len({str(r["id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate article identifiers in quality reference")
    manifest = {str(r["id"]): r for r in read_records(manifest_path)}
    for r in rows:
        original = manifest.get(str(r["id"]))
        if (
            not original
            or original["split"] != "test"
            or original["text_sha256"] != r["text_sha256"]
            or original.get("group_id") != r.get("group_id")
        ):
            raise ValueError("Reference is outside frozen held-out manifest")
    predictor = Predictor(run)
    used = set(predictor.meta.get("training_groups", [])) | set(
        predictor.meta.get("dev_groups", [])
    )
    if any(r["group_id"] in used for r in rows):
        raise ValueError("Test reference overlaps model training or dev groups")
    result = score(rows, list(predictor.predict(rows)))
    return {
        **result,
        "reference_sha256": file_sha(reference_path),
        "model_sha256": predictor.meta["model_sha256"],
        "model_version": predictor.meta["model_version"],
        "status": "human_reviewed_small_sample",
        "limitation": "Convenience sample with assisted preannotation; selection and anchoring bias, insufficient for production claims",
    }
