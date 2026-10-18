"""Record a captioned B2 demonstration, preserving the original video and corpus.

Uses an installed agent-browser binary supplied explicitly by the operator.
Stops only this Compose project's two authority stores and restores them in finally.
Authentication is read locally and never written in the evidence or command logs.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

from verify_lifecycle import get

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Preuves/Video_architecture_20261005"
SESSION = "b2-video-20261005"
ARTICLE = "2035207"
STYLE = """body{margin:8px auto!important;padding:18px!important;max-width:1180px!important}
h1{font-size:32px!important;margin:12px 0!important}h2{font-size:25px!important;margin:10px 0!important}
section{margin:14px 0!important;padding:18px!important}
pre{max-height:215px!important;overflow:auto!important;line-height:1.35!important}
p{margin:12px 0!important}input,button{padding:10px!important}
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    events = []

    def event(action, **details):
        events.append({"utc": datetime.now(timezone.utc).isoformat(), "action": action, **details})
        (OUT / "Execution.json").write_text(json.dumps(events, ensure_ascii=False, indent=2))
        print(action, flush=True)

    def compose(*words):
        r = subprocess.run(["docker", "compose", *words], cwd=ROOT, capture_output=True, text=True, timeout=90)
        if r.returncode:
            raise RuntimeError("Compose command failed: " + " ".join(words[:3]))
        return r.stdout

    def browser(*words, headers=False):
        command = [args.browser, "--session", SESSION, "--ignore-https-errors"]
        password = (ROOT / ".secrets/api_password").read_text().strip()
        authorization = "Basic " + base64.b64encode(("analyste:" + password).encode()).decode()
        if headers:
            browser("set", "credentials", "analyste", password)
        r = subprocess.run(command + list(words), capture_output=True, text=True, timeout=50)
        if r.returncode:
            # Do not include subprocess arguments: they can contain authentication.
            safe = (r.stderr + r.stdout)
            safe = safe.replace(password, "[redacted]").replace(authorization, "[redacted]")
            raise RuntimeError("Browser action failed: " + words[0] + ": " + safe[:600])
        return r.stdout

    def layout():
        browser("eval", "(()=>{let s=document.createElement('style');s.textContent=" + json.dumps(STYLE) + ";document.head.appendChild(s);return 'capture layout applied'})()")

    def statuses():
        lines = compose("ps", "-a", "--format", "json").splitlines()
        return [{k: x.get(k) for k in ("Service", "State", "Health")} for x in map(json.loads, lines) if x.get("Service") in {"app", "postgres", "mongo", "elasticsearch"}]

    def still(name):
        browser("screenshot", str(OUT / name))

    def record(label, expected_mode):
        browser("open", "https://localhost:18443/", headers=True)
        layout()
        browser("snapshot", "-i")
        browser("record", "start", str(OUT / (label + ".webm")))
        recording = True
        try:
            # Recording starts a fresh context; reapply origin-scoped authentication.
            browser("open", "https://localhost:18443/", headers=True)
            layout()
            # Verify the visible state, not just the separately queried API.
            visible = browser("get", "text", "body")
            if expected_mode not in visible:
                raise AssertionError("Unexpected visible storage state")
            event(label + "_dashboard", mode=expected_mode)
            still(label + "_dashboard.png")
            time.sleep(7)
            browser("snapshot", "-i")
            browser("find", "role", "button", "click", "--name", "Ouvrir la source stockée")
            layout()
            visible = browser("get", "text", "body")
            if expected_mode not in visible or original["article"]["title"] not in visible:
                raise AssertionError("Unexpected article visible in capture")
            current = get("/api/article?id=" + ARTICLE)
            assert current["mode"] == expected_mode
            assert current["article"] == original["article"]
            event(label + "_article", mode=current["mode"], identical_to_original=True)
            still(label + "_article.png")
            time.sleep(11)
            browser("record", "stop")
            recording = False
        finally:
            if recording:
                browser("record", "stop")

    before = get("/api/status")
    original = get("/api/article?id=" + ARTICLE)
    assert original["mode"] == "primary" and before["mode"] == "primary"
    initial_services = statuses()
    assert all(x["State"] == "running" for x in initial_services)
    event("preconditions_checked", counts=before, services=initial_services)

    # Query the actual reader clients in the existing container; no corpus mutation.
    code = """import json
from osint.storage import pg,mongo,es,INDEX
key='2035207'
with pg('reader') as c:
 row=c.execute('SELECT article_id,published_at,content_sha256 FROM articles WHERE article_id=%s',(key,)).fetchone()
 count=c.execute('SELECT count(*) FROM articles WHERE synthetic=false').fetchone()[0]
m=mongo('reader').documents.find_one({'_id':key})
e=es('GET',INDEX+'/_doc/'+key)
result={'article_id':key,'sql':{'article_id':row[0],'published_at':str(row[1]),'content_sha256':row[2],'count':count},'mongo':{'_id':m['_id'],'content_sha256':m['content_sha256'],'ciphertext_prefix':m['ciphertext'][:48]+'...','count':mongo('reader').documents.count_documents({})},'elasticsearch':{'_id':e['_id'],'content_sha256':e['_source']['content_sha256'],'count':es('GET',INDEX+'/_count')['count']}}
assert result['sql']['content_sha256']==result['mongo']['content_sha256']==result['elasticsearch']['content_sha256']
print(json.dumps(result,ensure_ascii=False))
"""
    stores = json.loads(compose("exec", "-T", "app", "python", "-c", code))
    (OUT / "Stockages.json").write_text(json.dumps(stores, ensure_ascii=False, indent=2))
    event("shared_id_and_hash_verified", article_id=ARTICLE)
    browser("set", "viewport", "1600", "700")
    try:
        record("01_normal", "primary")
        event("stopping_authority_stores", services=["postgres", "mongo"])
        compose("stop", "postgres", "mongo")
        stopped = statuses()
        assert all(x["State"] == "exited" for x in stopped if x["Service"] in {"postgres", "mongo"})
        event("authority_stores_stopped", services=stopped)
        (OUT / "Services_panne.json").write_text(json.dumps(stopped, ensure_ascii=False, indent=2))
        record("02_secours", "degraded_index_snapshot")
        event("restarting_authority_stores")
        compose("start", "postgres", "mongo")
        for _ in range(45):
            try:
                restored = get("/api/article?id=" + ARTICLE)
                if restored["mode"] == "primary":
                    break
            except Exception:
                pass
            time.sleep(1)
        assert restored["mode"] == "primary" and restored["article"] == original["article"]
        event("primary_reads_restored", identical_to_original=True, services=statuses())
        record("03_retabli", "primary")
    finally:
        compose("start", "postgres", "mongo")
        browser("close")
        event("cleanup_completed", services=statuses())

    after = get("/api/status")
    assert after["articles"] == before["articles"] and after["documents"] == before["documents"]
    assert get("/api/article?id=" + ARTICLE) == original
    event("final_integrity_checked", articles=after["articles"], documents=after["documents"])
    sources = {str(p.relative_to(ROOT)): digest(p) for p in [ROOT / "docker-compose.yml", ROOT / "app/osint/api.py", ROOT / "app/osint/storage.py", Path(__file__)]}
    metadata = {"date": datetime.now(timezone.utc).isoformat(), "article_id": ARTICLE, "recording_tool": browser("--version").strip(), "capture_layout": "Transient CSS only: compact margins and scrollable run history; no displayed data changed.", "scope": "Actual local browser capture and actual queries; same-Mac fallback; no production deployment or NER validation.", "sources_sha256": sources, "checks": {"same_article_normal_degraded_restored": True, "shared_id_and_content_hash": True, "corpus_counts_preserved": True}, "counts": stores}
    (OUT / "Capture.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
