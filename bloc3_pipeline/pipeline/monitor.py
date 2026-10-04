"""Read-only local monitoring, with no article text exposed on the HTTP endpoint."""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .common import alert, event, now
from .state import connect


def snapshot(state):
    db = connect(state)
    try:
        runs = [
            dict(row) for row in db.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 10")
        ]
        for run in runs:
            run["rows_per_second"] = round(
                run["checkpoint"] / max(run["processing_s"], 0.000001), 2
            )
            run["freshness_seconds"] = round(
                (
                    datetime.now(timezone.utc) - datetime.fromisoformat(run["updated_at"])
                ).total_seconds(),
                2,
            )
        path = Path(state) / "alerts.jsonl"
        alerts = (
            [json.loads(line) for line in path.read_text().splitlines()[-12:]]
            if path.exists()
            else []
        )
        return {
            "observed_at": now(),
            "refresh_seconds": 1,
            "runs": runs,
            "alerts": alerts,
        }
    finally:
        db.close()


def security_check(state):
    """Detect overbroad local permissions; alert and restore the private directory mode."""
    path = Path(state)
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        alert(
            state,
            "SECURITY_PERMISSIONS",
            previous_mode=oct(mode),
            action="chmod_0700",
            qualification="technical_incident_requires_human_review",
        )
        path.chmod(0o700)
        return False
    event(state, "security_check_passed", directory_mode=oct(mode))
    return True


HTML = r"""<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pipeline OSINT : supervision locale</title><style>body{font:17px system-ui;background:#f2f5fa;color:#10263d;margin:36px}h1{font-size:34px}header{border-top:7px solid #167d8d;padding-top:12px}.cards{display:flex;gap:16px;flex-wrap:wrap}.card{background:white;border:1px solid #dce3eb;border-radius:12px;padding:18px;min-width:130px}.value{font-size:30px;font-weight:750;color:#006a78}table{background:white;width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #dce3eb;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:18px}small{color:#46566b}</style>
<header><p>MÉMOIRE OSINT · BLOC 3</p><h1>Suivi du pipeline de données</h1><p>Exécution locale réelle. Actualisation chaque seconde. Aucune annotation humaine attestée.</p></header><p id="at"></p><div class="cards" id="cards"></div><h2>Exécutions</h2><table><thead><tr><th>État</th><th>Lot validé</th><th>Acceptés</th><th>Rejets</th><th>Doublons</th><th>Tentatives</th><th>Type</th></tr></thead><tbody id="runs"></tbody></table><h2>Alertes locales</h2><pre id="alerts"></pre><small>Débit mesuré dans les transactions de traitement. Fraîcheur : temps depuis le dernier changement d’état. Les fichiers complets sont réservés à l’opérateur local.</small><script>
async function refresh(){const d=await(await fetch('/status')).json(); document.querySelector('#at').textContent='Observé à '+d.observed_at; const r=d.runs[0]||{}; document.querySelector('#cards').replaceChildren(...[['Articles lus',r.checkpoint||0],['Débit lignes/s',r.rows_per_second||0],['Fraîcheur (s)',r.freshness_seconds||0],['État',r.status||'En attente']].map(([label,value])=>{let a=document.createElement('div');a.className='card';let b=document.createElement('div');b.textContent=label;let c=document.createElement('div');c.className='value';c.textContent=value;a.append(b,c);return a}));document.querySelector('#runs').replaceChildren(...d.runs.map(r=>{let tr=document.createElement('tr');[r.status,r.checkpoint,r.accepted,r.rejected,r.duplicates,r.attempts,r.synthetic?'Synthétique':'Corpus TASS'].forEach(v=>{let td=document.createElement('td');td.textContent=v;tr.append(td)});return tr}));document.querySelector('#alerts').textContent=d.alerts.map(a=>a.at+' | '+a.code+' | '+JSON.stringify(a)).join('\n')||'Aucune alerte enregistrée';} refresh();setInterval(refresh,1000);</script></html>"""


def serve(state, port=18743):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/status"):
                self.send_error(404)
                return
            data = json.dumps(snapshot(state)).encode() if self.path == "/status" else HTML.encode()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json" if self.path == "/status" else "text/html; charset=utf-8",
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            pass

    event(state, "monitor_started", listen="127.0.0.1", port=port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
