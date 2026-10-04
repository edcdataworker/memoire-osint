"""Lifecycle exercises on the OSINT stack only; run after load tests."""

import json
from pathlib import Path
import subprocess
import time
import urllib.request
import ssl
import base64
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "Preuves"


def run(*args, check=True):
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
    )
    return result


def ops(code):
    return run("run", "--rm", "-T", "ops", "python", "-c", code).stdout.strip()


def get(path, authenticated=True):
    request = urllib.request.Request("https://localhost:18443" + path)
    if authenticated:
        password = (ROOT / ".secrets/api_password").read_text().strip()
        request.add_header(
            "Authorization",
            "Basic " + base64.b64encode(("analyste:" + password).encode()).decode(),
        )
    context = ssl.create_default_context(cafile=str(ROOT / ".secrets/ca.crt"))
    with urllib.request.urlopen(request, context=context, timeout=45) as response:
        return json.loads(response.read())


def main():
    results = []
    try:
        get("/api/status", False)
        raise AssertionError("Unauthenticated access allowed")
    except urllib.error.HTTPError as error:
        assert error.code == 401
        results.append({"test": "HTTP authentication required", "passed": True})
    durations = []
    for _ in range(10):
        start = time.perf_counter()
        a = get("/api/article?id=2035207")
        durations.append(time.perf_counter() - start)
        assert a["mode"] == "primary"
    results.append(
        {
            "test": "article lookup on retained corpus",
            "passed": True,
            "seconds": durations,
        }
    )
    original = a["article"]
    # Record final counts before removing only generated synthetic rows.
    (E / "status_before_lifecycle.json").write_text(
        run("run", "--rm", "-T", "ops", "python", "-m", "osint.cli", "status").stdout
    )
    ops(
        "from osint.storage import pg,mongo; c=pg(); c.execute('DELETE FROM articles WHERE synthetic=true');c.commit();mongo().documents.delete_many({'synthetic':True})"
    )
    # A controlled failure validates checkpoint logic without deleting the corpus.
    interrupted = run(
        "run",
        "--rm",
        "-T",
        "ops",
        "python",
        "-m",
        "osint.cli",
        "ingest",
        "--synthetic",
        "12000",
        "--fail-after",
        "4000",
        check=False,
    )
    assert interrupted.returncode != 0
    first = json.loads(interrupted.stdout.splitlines()[0])
    run_id = first["run_id"]
    recovered = run(
        "run",
        "--rm",
        "-T",
        "ops",
        "python",
        "-m",
        "osint.cli",
        "ingest",
        "--synthetic",
        "12000",
        "--resume",
        run_id,
    )
    lines = [json.loads(x) for x in recovered.stdout.splitlines()]
    assert lines[0]["offset"] == 4000 and lines[-1]["processed"] == 12000
    results.append(
        {
            "test": "controlled interruption and resume",
            "passed": True,
            "resume_offset": 4000,
            "expected": 12000,
            "run_id": run_id,
            "actual_process_kill": False,
        }
    )
    ops(
        "from osint.storage import pg,mongo; c=pg(); c.execute('DELETE FROM articles WHERE synthetic=true');c.commit();mongo().documents.delete_many({'synthetic':True})"
    )
    # Persisted volumes survive container recreation with no volume deletion.
    run("up", "-d", "--force-recreate", "postgres", "mongo")
    for _ in range(40):
        try:
            result = get("/api/article?id=2035207")
            if result["mode"] == "primary":
                break
        except Exception:
            pass
        time.sleep(1)
    assert result["article"] == original and result["mode"] == "primary"
    results.append({"test": "container recreation preserves corpus", "passed": True})
    fixture_id = "test-erasure-" + uuid.uuid4().hex
    fixture = [
        {
            "id": fixture_id,
            "date": 1760000000,
            "title": "Fictitious rights exercise",
            "text": "Synthetic person-free test text",
            "url": "https://example.invalid/fixture",
            "language": "en",
            "extra_metadata": {"purpose": "test"},
        }
    ]
    (ROOT / ".data/privacy_fixture.json").write_text(json.dumps(fixture))
    run(
        "run",
        "--rm",
        "-T",
        "ops",
        "python",
        "-m",
        "osint.cli",
        "ingest",
        "--file",
        "/data/privacy_fixture.json",
    )
    run("run", "--rm", "-T", "ops", "python", "-m", "osint.cli", "index")
    result = get("/api/article?id=" + fixture_id)
    assert result["article"]["extra_metadata"] == {"purpose": "test"}
    results.append({"test": "optional nested JSON fields retained", "passed": True})
    # Backup now contains the fixture, so a subsequent deletion must be reapplied on restore.
    exe = sys.executable
    subprocess.run(
        [exe, "scripts/backup_restore.py", "backup"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    run(
        "run",
        "--rm",
        "-T",
        "ops",
        "python",
        "-m",
        "osint.cli",
        "erase",
        fixture_id,
    )
    try:
        get("/api/article?id=" + fixture_id)
        raise AssertionError("Erased document visible")
    except urllib.error.HTTPError as error:
        assert error.code == 404
    run(
        "run",
        "--rm",
        "-T",
        "ops",
        "python",
        "-m",
        "osint.cli",
        "ingest",
        "--file",
        "/data/privacy_fixture.json",
    )
    assert (
        ops(
            "from osint.storage import mongo;print(mongo().documents.count_documents({'_id':"
            + repr(fixture_id)
            + "}))"
        )
        == "0"
    )
    # Check the stores directly: a 404 from the API alone could only prove masking.
    code = (
        "from osint.storage import pg,mongo,es,INDEX;import requests;key="
        + repr(fixture_id)
        + ";c=pg();assert c.execute('SELECT count(*) FROM articles WHERE article_id=%s',(key,)).fetchone()[0]==0;"
        "assert mongo().documents.count_documents({'_id':key})==0\n"
        "try:es('GET',INDEX+'/_doc/'+key);raise AssertionError('fixture visible')\n"
        "except requests.HTTPError as e:assert e.response.status_code==404"
    )
    ops(code)
    last = json.loads((E / "backup.json").read_text())["backup"]
    subprocess.run(
        [
            exe,
            "scripts/backup_restore.py",
            "restore-test",
            str(ROOT / ".backups" / last),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    restored = json.loads((E / "restore.json").read_text())
    assert restored["postgres_rows"] == 21676 and restored["reapplied_erasures"] >= 1
    results.append(
        {
            "test": "erasure across 3 stores, reingestion and backup restore",
            "passed": True,
            "fixture": fixture_id,
            "restored_articles": 21676,
        }
    )
    results.append(
        {
            "test": "primary article preserved after exercises",
            "passed": get("/api/article?id=2035207")["article"] == original,
        }
    )
    (E / "lifecycle.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


if __name__ == "__main__":
    main()
