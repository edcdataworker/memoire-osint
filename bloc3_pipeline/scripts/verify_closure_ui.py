"""Record an isolated fictional collection and offline recovery using the real UI."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "Preuves/Collecte_TASS"
STATE = ROOT / ".demo-cloture-definitive"
URL = "http://127.0.0.1:18745"
BROWSER = os.environ["AGENT_BROWSER"]


def browser(*args):
    return subprocess.check_output([BROWSER, "--session", "memoire-cloture", *args], text=True)


def request(path, data=None, headers=None):
    req = urllib.request.Request(
        URL + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def wait(predicate, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            status = request("/api/status")[1]
            if predicate(status):
                return status
        except OSError:
            pass
        time.sleep(0.15)
    raise RuntimeError("Fixture did not reach expected state")


def start_server(log):
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/demo_collection_fixture.py"), str(STATE), "18745"],
        cwd=ROOT,
        stdout=log,
        stderr=log,
    )
    wait(lambda s: not s["read_only"])
    return process


def main():
    with socket.socket() as available:
        available.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        available.bind(("127.0.0.1", 18745))
    if STATE.exists():
        raise RuntimeError("Use a fresh isolated fixture directory")
    with (PROOF / "UI_fixture.log").open("w") as log:
        server = start_server(log)
        try:
            browser("set", "viewport", "1440", "1000")
            browser("record", "start", str(PROOF / "Demonstration_cloture.webm"), URL)
            browser("open", URL)
            browser(
                "eval",
                'document.querySelector(".eyebrow").textContent="1. Collecte de cinq articles fictifs"; for(const id of ["start","end"]){const e=document.getElementById(id);e.value="2023-11-26";e.dispatchEvent(new Event("change",{bubbles:true}));} document.getElementById("limit").value="5"; document.getElementById("collect-form").requestSubmit()',
            )
            wait(lambda s: s["jobs"] and s["jobs"][0]["processed"] >= 1)
            browser("eval", 'document.querySelector("[data-action=stop]").click()')
            wait(lambda s: s["jobs"][0]["status"] == "paused")
            time.sleep(1)
            browser("eval", 'document.querySelector("[data-action=resume]").click()')
            completed = wait(lambda s: s["jobs"][0]["status"] == "complete")
            time.sleep(1)
            browser("screenshot", str(PROOF / "Cloture_suivi.png"))
            browser("eval", 'document.querySelector("[data-action=corpus]").click()')
            time.sleep(1)
            browser("eval", 'document.querySelector("[data-article]").click()')
            time.sleep(1)
            browser("screenshot", str(PROOF / "Cloture_article.png"))
            browser("eval", 'document.getElementById("article-dialog").close()')
            browser(
                "eval",
                'document.querySelector("[data-tab=collecte]").click();document.querySelector(".eyebrow").textContent="2. Exercice fictif : perte du catalogue principal"',
            )
            (STATE / "collection.sqlite").rename(STATE / "incident-original.sqlite")
            fallback = wait(lambda s: s["read_only"])
            time.sleep(2)
            browser("screenshot", str(PROOF / "Cloture_secours.png"))
            csrf = request("/api/config")[1]["csrf"]
            params = {"section": "defense", "start": "2023-11-26", "end": "2023-11-26", "limit": 5}
            report = {
                "mirror_backend": fallback["backend"] == "mirror",
                "mirror_read_only": fallback["read_only"],
                "mirror_date": fallback["mirror_at"],
                "security_incident_visible": any(
                    e.get("code") == "CATALOG_INTEGRITY" for e in fallback["events"]
                ),
            }
            headers = {"X-CSRF-Token": csrf, "Origin": URL, "Content-Type": "application/json"}
            for route in ("start", "resume", "ingest-b2"):
                report[route + "_blocked"] = request("/api/" + route, params, headers)[0] == 400
            report["fallback_export_five"] = (
                len(request("/api/export?section=defense&start=2023-11-26&end=2023-11-26")[1]) == 5
            )
            report["csrf_blocked"] = request("/api/start", params)[0] == 403
            report["host_blocked"] = (
                request("/api/status", headers={"Host": "hostile.example"})[0] == 403
            )
            report["article_readable"] = len(request("/api/article?id=1")[1]["revisions"]) == 1
            entries = [
                json.loads(line) for line in (STATE / "events.jsonl").read_text().splitlines()
            ]
            report["fallback_access_audited"] = any(
                e.get("event") == "article_access" and e.get("actor") for e in entries
            )
            assert all(v for v in report.values() if isinstance(v, bool)), report
            browser(
                "eval",
                'document.querySelector(".eyebrow").textContent="3. Serveur arrêté : restauration explicite et registres de droits"',
            )
            server.send_signal(signal.SIGINT)
            server.wait(timeout=10)
            restored = subprocess.run(
                [sys.executable, "-m", "pipeline", "collect-restore", "--state", str(STATE)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            report["offline_restored"] = '"restored": true' in restored.stdout
            time.sleep(2)
            server = start_server(log)
            wait(lambda s: s["articles"] == 5 and not s["read_only"])
            time.sleep(2)
            browser(
                "eval",
                'document.querySelector(".eyebrow").textContent="4. Catalogue restauré : consultation et collecte disponibles"',
            )
            browser("screenshot", str(PROOF / "Cloture_restauration.png"))
            time.sleep(2)
            browser("record", "stop")
            report.update(
                {
                    "fixture": "five fictional articles, real worker and HTTP service",
                    "job_id": completed["jobs"][0]["job_id"],
                    "rights_restore_tests": "Tests_cloture_final.log",
                    "oral_rehearsal_observed": False,
                }
            )
            (PROOF / "Verification_HTTP.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report))
        finally:
            if server.poll() is None:
                server.send_signal(signal.SIGINT)
                server.wait(timeout=10)


if __name__ == "__main__":
    main()
