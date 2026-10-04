"""Synthetic fixtures test provenance mechanisms, never review real TASS data."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from osint_ner.contracts import article, write_records
from osint_ner.human_review import ReviewStore, make_handler
from osint_ner.model import evaluate


@pytest.fixture
def store(tmp_path):
    row = article(
        {
            "id": 1,
            "text": "😀 Kalibr.",
            "title": "Synthetic fixture",
            "url": "https://example.org/1",
            "split": "test",
            "group_id": "heldout",
            "annotation_status": "ai_proposed_pending_human",
            "entities": [{"start": 2, "end": 8, "label": "WEAPON"}],
        }
    )
    ref, manifest = tmp_path / "reference.jsonl", tmp_path / "manifest.jsonl"
    write_records(ref, [row])
    write_records(manifest, [row])
    return ReviewStore(ref, manifest, tmp_path / "review", tmp_path / "unused-model")


def payload(store, attest=False):
    row = store.original[0]
    return {
        "id": row["id"],
        "text_sha256": row["text_sha256"],
        "entities": row["entities"],
        "reviewer": "Test automatique sur fixture synthétique",
        "review_note": "",
        "attest": attest,
    }


def test_open_and_draft_cannot_produce_human_score(store):
    assert store.snapshot()["reviewed"] == 0
    with pytest.raises(ValueError, match="Revue incomplète"):
        store.evaluate()
    store.save(payload(store))
    assert list(store.directory.glob("reference_humaine.jsonl"))
    assert store.export().read_text() == ""
    with pytest.raises(ValueError, match="Revue incomplète"):
        store.evaluate()


def test_explicit_fixture_attestation_persists_and_draft_revokes_it(store):
    store.save(payload(store, True))
    assert store.snapshot()["reviewed"] == 1
    reopened = ReviewStore(store.reference, store.manifest, store.directory, store.run)
    assert reopened.snapshot()["reviewed"] == 1
    store.save(payload(store, False))
    assert store.snapshot()["reviewed"] == 0
    assert store.export().read_text() == ""


@pytest.mark.parametrize(
    "change",
    [
        {"reviewer": "   ", "attest": True},
        {"text_sha256": "wrong"},
        {"entities": [{"start": 0, "end": 2, "label": "PERSON"}]},
        {"entities": [{"start": 2, "end": 8, "label": "WEAPON", "text": "incorrect"}]},
    ],
)
def test_rejects_forged_identity_bad_spans_and_empty_name(store, change):
    with pytest.raises(ValueError):
        store.save({**payload(store), **change})
    assert store.snapshot()["reviewed"] == 0


def test_quality_rejects_forged_test_group_before_loading_model(store):
    store.save(payload(store, True))
    row = next(iter(json.loads(line) for line in store.export().read_text().splitlines()))
    row["group_id"] = "forged"
    write_records(store.directory / "forged.jsonl", [row])
    with pytest.raises(ValueError, match="outside frozen"):
        evaluate(store.run, store.directory / "forged.jsonl", store.manifest)


def test_http_rejects_cross_origin_and_incomplete_evaluation(store, tmp_path):
    template = tmp_path / "page.html"
    template.write_text("synthetic page")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store, template, "fixture-token"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        state = json.loads(urllib.request.urlopen(url + "/api/state").read())
        assert state["reviewed"] == 0
        for origin, expected in [("https://example.org", 403), (url, 400)]:
            request = urllib.request.Request(
                url + "/api/evaluate",
                data=b"{}",
                headers={
                    "Origin": origin,
                    "X-Review-Token": "fixture-token",
                    "Content-Type": "application/json",
                },
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(request)
            assert exc.value.code == expected
        assert store.snapshot()["reviewed"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
