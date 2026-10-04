"""Synthetic fixtures verify mechanisms only, never estimate real NER quality."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from osint_ner.contracts import article, atomic_json, digest, validate_spans, write_records
from osint_ner.data import group_split, weak_spans
from osint_ner.export import erase, export_bulk
from osint_ner.metrics import require_reviewed, score
from osint_ner.monitor import monitor
from osint_ner.registry import gate
from osint_ner.server import make_handler


def record(text="Kalibr and NATO.", id=1):
    return article(
        {
            "id": id,
            "text": text,
            "title": "Synthetic fixture",
            "url": f"https://example.org/{id}",
            "date": 1735689600,
        }
    )


@pytest.mark.parametrize("text", ["", " ", None, 45, "a" * 100001, "x\x00y"])
def test_bad_text(text):
    with pytest.raises(ValueError):
        record(text)


def test_hash_and_schema_contract():
    r = record()
    with pytest.raises(ValueError):
        article({**r, "text": "changed"})
    with pytest.raises(ValueError):
        article({**r, "schema_version": 2})
    with pytest.raises(ValueError):
        article({**r, "url": "javascript:alert(1)"})
    with pytest.raises(ValueError):
        article({**r, "offset_unit": "utf16"})


def test_offsets_unicode_repeated():
    text = "😀 Kalibr and Kalibr."
    spans = weak_spans(text)
    assert [s["start"] for s in spans] == [2, 13]
    assert validate_spans(text, spans) == spans
    with pytest.raises(ValueError):
        validate_spans(text, spans + [spans[0]])


@pytest.mark.parametrize(
    "span",
    [
        dict(start=-1, end=2, label="WEAPON"),
        dict(start=0, end=80, label="WEAPON"),
        dict(start=0, end=6, label="PERSON"),
        dict(start=0, end=6, label="WEAPON", text="wrong"),
        dict(start=0.5, end=6, label="WEAPON"),
    ],
)
def test_invalid_spans(span):
    with pytest.raises(ValueError):
        validate_spans("Kalibr", [span])


def test_grouping_blocks_source_text_and_title_leakage():
    rows = [record("Kalibr.", 1), record("KALIBR!", 2), record("NATO.", 3), record("S-400.", 4)]
    rows[0]["title"] = "First title"
    rows[1]["title"] = "Other"
    rows[2]["title"] = "FIRST TITLE!"
    rows[3]["title"] = "Unique title"
    result = group_split(rows)
    assert len({r["group_id"] for r in result[:3]}) == 1
    assert len({r["split"] for r in result[:3]}) == 1
    rev = group_split(list(reversed([dict(r) for r in rows])))
    assert {r["id"]: r["split"] for r in result} == {r["id"]: r["split"] for r in rev}


def test_exact_metrics_known_answer_and_no_real_quality_claim():
    r = record()
    g = {**r, "entities": weak_spans(r["text"])}
    p = {**r, "entities": [g["entities"][0]]}
    m = score([g], [p])
    assert m["global"]["precision"] == 1
    assert m["global"]["recall"] == 0.5
    assert m["global"]["f1"] == pytest.approx(2 / 3)
    assert m["per_label"]["MIL_UNIT"]["f1"] is None
    assert len(m["errors"]) == 1
    with pytest.raises(ValueError):
        score([g], [{**p, "id": 2}])


def test_weak_labels_cannot_be_quality_reference():
    with pytest.raises(ValueError):
        require_reviewed(
            [{**record(), "entities": [], "annotation_status": "weak_supervision_unreviewed"}]
        )
    with pytest.raises(ValueError):
        require_reviewed([])


def test_drift_distinguishes_unavailable_quality(tmp_path):
    result = monitor([record("x" * 500)], [record("x" * 5000)], tmp_path / "monitor.json")
    assert result["distribution"]["alert"]
    assert result["distribution"]["js_divergence_bits"] == 1
    assert result["quality"]["f1_delta"] is None
    assert (tmp_path / "monitor.json.review-request.json").exists()


def test_quality_drift_reference_identity(tmp_path):
    r = record()
    q = {
        "reference_sha256": "fixture",
        "status": "human_reviewed_small_sample",
        "global": {"f1": 0.8},
    }
    other = {**q, "global": {"f1": 0.7}}
    result = monitor([r], [r], tmp_path / "m.json", q, other)
    assert result["quality"]["alert"] and not result["distribution"]["alert"]
    with pytest.raises(ValueError):
        monitor([r], [r], tmp_path / "x.json", q, {**other, "reference_sha256": "different"})


def test_production_gate_keeps_unvalidated_model_out():
    reasons = gate({"annotation_status": "weak_supervision_demo", "model_sha256": "demo"}, None)
    assert "missing_human_quality_reference" in reasons
    assert "training_annotations_not_human_reviewed" in reasons


def test_bulk_keeps_offsets_and_enforces_exclusions(tmp_path):
    r = record()
    r.update(
        entities=weak_spans(r["text"]),
        model_version="fixture",
        model_sha256="fixture",
        annotation_status="synthetic_fixture",
    )
    source = tmp_path / "input.jsonl"
    write_records(source, [r])
    out = tmp_path / "bulk.ndjson"
    result = export_bulk(source, out)
    lines = [json.loads(x) for x in out.read_text().splitlines()]
    assert result["mentions"] == 2
    assert lines[1]["text_sha256"] == digest(r["text"])
    excluded = tmp_path / "excluded.json"
    atomic_json(excluded, {"article_ids": [1]})
    assert export_bulk(source, out, excluded)["mentions"] == 0
    with pytest.raises(ValueError):
        export_bulk(source, out, index="osint-articles-v1")


def test_erasure_removes_source_and_inferences(tmp_path):
    source = tmp_path / "in.jsonl"
    write_records(source, [record(id=1), record(id=2)])
    out = tmp_path / "out.jsonl"
    event = erase(source, 1, out, tmp_path / "log.json")
    assert event["removed_records"] == 1
    assert json.loads(out.read_text())["id"] == 2
    assert event["model_retraining_required"]


@pytest.fixture
def server(tmp_path):
    r = record("<script>alert(1)</script> Kalibr.")
    r.update(entities=weak_spans(r["text"]), model_version="synthetic", model_sha256="x")
    data = tmp_path / "data.jsonl"
    write_records(data, [r])
    atomic_json(
        tmp_path / "training.json",
        {
            "model_version": "synthetic",
            "model_sha256": "x",
            "quality_metrics": None,
            "quality_status": "fixture",
        },
    )
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(data, tmp_path))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()
    thread.join()


def test_http_health_search_and_time_filter(server):
    health = json.load(urllib.request.urlopen(server + "/health"))
    assert health["status"] == "ok"
    assert health["quality_status"] == "fixture"
    summary = json.load(urllib.request.urlopen(server + "/api/summary?year=2025&q=Kalibr"))
    assert summary["documents"] == 1 and summary["mentions"] == 1
    assert json.load(urllib.request.urlopen(server + "/api/summary?year=2024"))["documents"] == 0
    with urllib.request.urlopen(server + "/") as r:
        assert "script-src 'self'" in r.headers["Content-Security-Policy"]
        assert b"alert(1)" not in r.read()


@pytest.mark.parametrize("path", ["/../../etc/passwd", "/api/article?id=999", "/unknown"])
def test_no_arbitrary_read(server, path):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + path)
    assert e.value.code == 404


def test_mutation_and_dns_rebinding_rejected(server):
    for req, expected in [
        (urllib.request.Request(server + "/", data=b"{}"), 405),
        (urllib.request.Request(server + "/", headers={"Host": "attacker.example"}), 403),
    ]:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == expected


def test_large_request_rejected(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + "/api/summary?q=" + "x" * 5000)
    assert e.value.code == 414


def test_real_spacy_roundtrip_on_synthetic_fixture(tmp_path):
    from osint_ner.model import train, Predictor

    a = record("Kalibr and NATO.", 100)
    b = record("NATO mentions Kalibr.", 200)
    a.update(entities=weak_spans(a["text"]), split="train", group_id="synthetic-train")
    b.update(entities=weak_spans(b["text"]), split="dev", group_id="synthetic-dev")
    tr, dev = tmp_path / "train.jsonl", tmp_path / "dev.jsonl"
    write_records(tr, [a])
    write_records(dev, [b])
    report = train(tr, dev, tmp_path / "run", epochs=1)
    assert report["quality_metrics"]["global"] is None
    assert isinstance(report["history"][0]["training_loss"], float)
    assert list(Predictor(tmp_path / "run").predict([b]))[0]["text"] == b["text"]
    a["schema_version"] = 2
    write_records(tr, [a])
    with pytest.raises(ValueError):
        train(tr, dev, tmp_path / "bad", epochs=1)


def test_scheduler_failure_is_not_success(tmp_path):
    from osint_ner.automation import watch

    with pytest.raises(ValueError, match="failed cycle"):
        watch(
            tmp_path / "missing-train.jsonl", tmp_path / "missing-dev.jsonl", tmp_path / "scheduler"
        )
    event = json.loads((tmp_path / "scheduler/alert.json").read_text())
    assert event["action"] == "failed"
    assert not (tmp_path / "scheduler/scheduler.json").exists()
    assert not (tmp_path / "scheduler/scheduler.lock").exists()


def test_scheduler_rejects_concurrent_lock(tmp_path):
    from osint_ner.automation import watch

    (tmp_path / "scheduler.lock").write_text("active fixture")
    with pytest.raises(FileExistsError):
        watch(tmp_path / "train.jsonl", tmp_path / "dev.jsonl", tmp_path)


def test_server_rejects_mixed_model_identity(tmp_path):
    r = record()
    r.update(entities=[], model_version="one", model_sha256="wrong")
    write_records(tmp_path / "data.jsonl", [r])
    atomic_json(tmp_path / "training.json", {"model_version": "one", "model_sha256": "right"})
    with pytest.raises(ValueError, match="identity mismatch"):
        make_handler(tmp_path / "data.jsonl", tmp_path)


def test_scheduler_records_unexpected_runtime_failure(tmp_path, monkeypatch):
    import osint_ner.automation as automation

    r = record()
    r.update(entities=[], split="train", group_id="fixture")
    write_records(tmp_path / "train.jsonl", [r])
    write_records(tmp_path / "dev.jsonl", [r])

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic training failure")

    monkeypatch.setattr(automation, "train", fail)
    with pytest.raises(ValueError, match="failed cycle"):
        automation.watch(
            tmp_path / "train.jsonl", tmp_path / "dev.jsonl", tmp_path / "state", demo=True
        )
    event = json.loads((tmp_path / "state/alert.json").read_text())
    assert event["error_type"] == "RuntimeError"
