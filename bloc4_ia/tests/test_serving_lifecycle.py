"""Temporary synthetic fixtures test serving and lifecycle, not real NER quality."""

import json
import shutil
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from osint_ner.contracts import article, atomic_json, digest, write_records
from osint_ner.model import Predictor, train
from osint_ner.server import make_handler


@pytest.fixture(scope="module")
def synthetic_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic-serving")
    rows = []
    for index, (split, text) in enumerate(
        [
            ("train", "Kalibr and NATO."),
            ("dev", "NATO mentions Kalibr."),
        ]
    ):
        row = article({"id": index, "text": text, "url": "https://example.invalid/fixture"})
        row.update(split=split, group_id=split, entities=[])
        write_records(root / f"{split}.jsonl", [row])
        rows.append(row)
    train(root / "train.jsonl", root / "dev.jsonl", root / "run", epochs=1)
    predictions = list(Predictor(root / "run").predict(rows))
    write_records(root / "predictions.jsonl", predictions)
    return root


@pytest.fixture
def serving(synthetic_run):
    srv = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(
            synthetic_run / "predictions.jsonl",
            synthetic_run / "run",
            Predictor(synthetic_run / "run"),
        ),
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()
    thread.join()


def post(url, value, headers=None):
    return urllib.request.urlopen(
        urllib.request.Request(
            url + "/api/predict",
            data=json.dumps(value).encode(),
            headers=headers or {"Content-Type": "application/json"},
        ),
        timeout=15,
    )


def test_prediction_uses_loaded_spacy_and_preserves_unicode(serving):
    text = "😀 A new text mentioning NATO and Kalibr."
    with post(serving, {"text": text}) as response:
        data = json.load(response)
    health = json.load(urllib.request.urlopen(serving + "/health"))
    assert data["text"] == text
    assert data["text_sha256"] == digest(text)
    assert data["model_sha256"] == health["model_sha256"]
    assert data["retention"] == "not_persisted"
    assert data["duration_seconds"] >= 0
    for entity in data["entities"]:
        assert text[entity["start"] : entity["end"]] == entity["text"]
    metrics = json.load(urllib.request.urlopen(serving + "/api/metrics"))["prediction"]
    assert metrics["successes"] == 1 and metrics["last_characters"] == len(text)
    assert "text" not in metrics


@pytest.mark.parametrize(
    "value",
    [
        {"text": ""},
        {"text": 12},
        {"text": "x" * 100001},
        ["not an object"],
        {"text": "ok", "run": "/tmp"},
    ],
)
def test_prediction_rejects_bad_contract(serving, value):
    with pytest.raises(urllib.error.HTTPError) as exc:
        post(serving, value)
    assert exc.value.code == 400


def test_prediction_rejects_cross_origin_and_wrong_mime(serving):
    for headers, code in [
        ({"Content-Type": "text/plain"}, 415),
        ({"Content-Type": "application/json", "Origin": "https://evil.invalid"}, 403),
    ]:
        with pytest.raises(urllib.error.HTTPError) as exc:
            post(serving, {"text": "Kalibr"}, headers)
        assert exc.value.code == code


def test_concurrent_prediction_is_bounded(synthetic_run):
    entered, release = threading.Event(), threading.Event()
    actual = Predictor(synthetic_run / "run")

    class SlowFixture:
        def predict(self, rows):
            entered.set()
            release.wait(timeout=5)
            yield from actual.predict(rows)

    srv = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(synthetic_run / "predictions.jsonl", synthetic_run / "run", SlowFixture()),
    )
    server_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{srv.server_port}"
    result = []

    def first_request():
        with post(url, {"text": "Synthetic slow input"}) as response:
            result.append(response.status)

    worker = threading.Thread(target=first_request)
    worker.start()
    try:
        assert entered.wait(timeout=5)
        with pytest.raises(urllib.error.HTTPError) as exc:
            post(url, {"text": "Concurrent synthetic input"})
        assert exc.value.code == 429
    finally:
        release.set()
        worker.join(timeout=10)
        srv.shutdown()
        srv.server_close()
        server_thread.join()
    assert result == [200]


def test_retraining_wires_evaluation_drift_and_gate(tmp_path, synthetic_run, monkeypatch):
    import osint_ner.automation as automation

    # These reviewer strings exist only in temporary synthetic test fixtures.
    for split in ("train", "dev"):
        row = json.loads((synthetic_run / f"{split}.jsonl").read_text())
        row.update(
            annotation_status="human_reviewed",
            reviewer="SYNTHETIC TEST ONLY",
            reviewed_at="2026-10-18T00:00:00Z",
        )
        write_records(tmp_path / f"{split}.jsonl", [row])
    write_records(tmp_path / "reference.jsonl", [{"fixture": True}])
    write_records(tmp_path / "manifest.jsonl", [{"fixture": True}])
    write_records(tmp_path / "current.jsonl", [{"text": "short synthetic input"}])

    def fixture_train(train_path, dev_path, output, epochs):
        shutil.copytree(synthetic_run / "run", output)
        meta = json.loads((output / "training.json").read_text())
        meta["annotation_status"] = "human_reviewed_training"
        atomic_json(output / "training.json", meta)
        return meta

    def fixture_evaluate(run, reference, manifest):
        run = Path(run)
        meta = json.loads((run / "training.json").read_text())
        return {
            "status": "human_reviewed_small_sample",
            "documents": 100,
            "reference_sha256": "synthetic-test-only",
            "model_sha256": meta["model_sha256"],
            "global": {"f1": 0.9},
            "per_label": {
                label: {"support": 30, "recall": 0.9} for label in ("WEAPON", "MIL_UNIT", "MIL_ORG")
            },
        }

    monkeypatch.setattr(automation, "train", fixture_train)
    monkeypatch.setattr(automation, "evaluate", fixture_evaluate)
    import osint_ner.deployment as deployment

    deliveries = []

    def fixture_delivery(wheel, data, run, state, port):
        rows = [json.loads(line) for line in Path(data).read_text().splitlines()]
        meta = json.loads((Path(run) / "training.json").read_text())
        assert all(row["model_sha256"] == meta["model_sha256"] for row in rows)
        deliveries.append(rows)
        return {"action": "synthetic_delivery_test", "model_sha256": meta["model_sha256"]}

    monkeypatch.setattr(deployment, "deploy", fixture_delivery)
    atomic_json(tmp_path / "exclusions.json", {"article_ids": []})
    atomic_json(
        tmp_path / "delivery.json",
        {
            "wheel": "synthetic-wheel-placeholder",
            "data_source": str(tmp_path / "train.jsonl"),
            "exclusions": str(tmp_path / "exclusions.json"),
            "state": str(tmp_path / "service"),
        },
    )
    args = (tmp_path / "train.jsonl", tmp_path / "dev.jsonl", tmp_path / "scheduler")
    options = dict(
        reference=tmp_path / "reference.jsonl",
        manifest=tmp_path / "manifest.jsonl",
        current=tmp_path / "current.jsonl",
        delivery=tmp_path / "delivery.json",
    )
    automation.watch(*args, **options)
    event = json.loads((tmp_path / "scheduler/events.jsonl").read_text().splitlines()[-1])
    assert event["production_promotion"]["accepted"]
    assert event["evaluation"]["reference_sha256"] == "synthetic-test-only"
    assert len(deliveries) == 1
    assert event["delivery"]["action"] == "synthetic_delivery_test"
    # A new, sharply shifted distribution must freeze promotion even with good scores.
    write_records(tmp_path / "current.jsonl", [{"text": "x" * 5000}])
    automation.watch(*args, **options)
    event = json.loads((tmp_path / "scheduler/events.jsonl").read_text().splitlines()[-1])
    assert event["monitoring"]["distribution"]["alert"]
    assert "drift_freeze" in event["production_promotion"]["reasons"]
    assert not event["production_promotion"]["accepted"]
    assert len(deliveries) == 1
    # A failed serving delivery restores the previous model-registry pointer.
    before = (tmp_path / "scheduler/registry/production.json").read_bytes()
    write_records(tmp_path / "current.jsonl", [{"text": "another short input"}])

    def failed_delivery(*args, **kwargs):
        raise RuntimeError("Synthetic delivery failure")

    monkeypatch.setattr(deployment, "deploy", failed_delivery)
    with pytest.raises(ValueError, match="failed cycle"):
        automation.watch(*args, **options)
    assert (tmp_path / "scheduler/registry/production.json").read_bytes() == before


def test_retraining_requires_reference_pair_and_reviewed_dev(tmp_path, synthetic_run):
    from osint_ner.automation import watch

    with pytest.raises(ValueError, match="both reference"):
        watch("unused", "unused", tmp_path, reference="only-reference")
    with pytest.raises(ValueError, match="failed cycle"):
        watch(synthetic_run / "train.jsonl", synthetic_run / "dev.jsonl", tmp_path / "state")
    assert not (tmp_path / "state/registry/production.json").exists()
