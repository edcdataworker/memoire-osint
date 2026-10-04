"""Record an actual browser session while scheduled synthetic recovery and real import run."""

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.__main__ import DEFAULTS
from pipeline.common import atomic_json, now

BROWSER = "/Users/ed/Desktop/Mémoire/02_Bloc_2_Architecture/.construction/browser/node_modules/.bin/agent-browser"
STATE = ROOT / (".demo-" + str(time.time_ns()))
STATE.mkdir(exist_ok=True)


def browser(*args):
    subprocess.run([BROWSER, "--session", "osint-bloc3", *args], check=True, cwd=ROOT)


source = STATE / "synthetic.json"
source.write_text(
    json.dumps(
        [
            {
                "id": f"video-{i}",
                "date": 1700000000 + i,
                "title": f"Synthetic article {i}",
                "text": f"Synthetic article {i}: fictional Drone-X equipment.",
                "url": f"https://example.invalid/video/{i}",
            }
            for i in range(80)
        ]
    )
)
synthetic = DEFAULTS | {
    "source": str(source),
    "state": str(STATE),
    "synthetic": True,
    "batch_size": 10,
    "test_kill_at_record": 24,
    "test_batch_delay_seconds": 1,
    "retry_seconds": 3,
}
real = DEFAULTS | {
    "source": str(ROOT.parent / "00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json"),
    "state": str(STATE),
    "batch_size": 1000,
    "test_batch_delay_seconds": 0.3,
}
atomic_json(STATE / "synthetic-config.json", synthetic)
atomic_json(STATE / "real-config.json", real)
with (ROOT / "Preuves" / "Video_monitor.log").open("w") as log:
    server = subprocess.Popen(
        [sys.executable, "-m", "pipeline", "serve", "--state", str(STATE), "--port", "18743"],
        cwd=ROOT,
        stdout=log,
        stderr=log,
    )
    try:
        import urllib.request

        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:18743/status", timeout=1).read()
                break
            except OSError:
                time.sleep(0.1)
        browser("open", "http://127.0.0.1:18743")
        browser("set", "viewport", "1440", "1000")
        browser("wait", "--fn", "document.querySelector('#at').textContent.startsWith('Observé')")
        browser("snapshot")
        browser("record", "start", str(ROOT / "Preuves" / "Capture_pipeline.webm"))
        start = now()
        with (ROOT / "Preuves" / "Video_execution.jsonl").open("w") as output:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pipeline",
                    "schedule",
                    "--config",
                    str(STATE / "synthetic-config.json"),
                    "--first-delay",
                    "2",
                ],
                cwd=ROOT,
                stdout=output,
                stderr=output,
                check=True,
            )
            browser("screenshot", str(ROOT / "Preuves" / "Capture_reprise.png"))
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pipeline",
                    "worker",
                    "--config",
                    str(STATE / "real-config.json"),
                ],
                cwd=ROOT,
                stdout=output,
                stderr=output,
                check=True,
            )
        time.sleep(3)
        browser("wait", "--fn", "document.querySelector('#at').textContent.startsWith('Observé')")
        browser("snapshot")
        browser("screenshot", str(ROOT / "Preuves" / "Capture_corpus.png"))
        browser("errors")
        browser("record", "stop")
        end = now()
        browser("close")
        atomic_json(
            ROOT / "Preuves" / "Video_description.json",
            {
                "started_at": start,
                "ended_at": end,
                "capture": "Actual browser recording, one continuous take, no narrative generated frames",
                "synthetic_records": 80,
                "crash_record_index": 24,
                "last_committed_checkpoint_before_crash": 20,
                "real_records": 21676,
                "slowdown_for_readability": "Synthetic 1 second per committed batch; real 0.3 seconds per batch. Not a benchmark.",
                "environment": "Local host, no external production deployment",
                "monitor_port": 18743,
                "server_stopped_after_capture": True,
            },
        )
    finally:
        server.terminate()
        server.wait(timeout=10)
