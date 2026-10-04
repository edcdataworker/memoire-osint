"""Authenticated local read service, with an explicit degraded-read path."""

import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import html
import json
import ssl
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from .storage import INDEX, decrypt, es, mongo, pg, secret, tombstones


def lookup(article_id):
    if article_id in tombstones():
        return None, "suppressed"
    try:
        with pg("reader") as sql:
            row = sql.execute(
                "SELECT content_sha256 FROM articles WHERE article_id=%s", (article_id,)
            ).fetchone()
        if not row:
            return None, "primary"
        doc = mongo("reader").documents.find_one({"_id": article_id})
        if not doc or doc["content_sha256"] != row[0]:
            raise ValueError("Cross-store mismatch")
        return decrypt(doc["ciphertext"], article_id), "primary"
    except Exception:
        item = es("GET", INDEX + "/_doc/" + article_id)
        doc = item["_source"]
        return decrypt(doc["ciphertext"], article_id), "degraded_index_snapshot"


def metrics():
    result = {
        "mode": "primary",
        "limitations": "Lecture locale, aucun modèle NER exécuté à ce stade.",
    }
    try:
        with pg("reader") as sql:
            result["articles"] = sql.execute(
                "SELECT count(*) FROM articles WHERE synthetic=false"
            ).fetchone()[0]
            result["synthetic"] = sql.execute(
                "SELECT count(*) FROM articles WHERE synthetic=true"
            ).fetchone()[0]
            result["runs"] = sql.execute(
                "SELECT kind,status,checkpoint,expected FROM runs ORDER BY started_at DESC LIMIT 5"
            ).fetchall()
        result["documents"] = mongo("reader").documents.count_documents({}, hint="_id_")
    except Exception:
        result = {
            "mode": "degraded_index_snapshot",
            "articles": es("GET", INDEX + "/_count")["count"],
            "limitations": "Dernier index disponible. Ingestion suspendue ; fraîcheur non garantie.",
        }
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, status, payload, content_type="application/json; charset=utf-8"):
        data = (
            payload.encode()
            if isinstance(payload, str)
            else json.dumps(payload, ensure_ascii=False, default=str).encode()
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return self.send(200, {"service": "up"})
        expected = (
            "Basic "
            + base64.b64encode(("analyste:" + secret("api_password")).encode()).decode()
        )
        if not hmac.compare_digest(self.headers.get("Authorization", ""), expected):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="OSINT"')
            self.end_headers()
            return
        try:
            if url.path == "/api/status":
                return self.send(200, metrics())
            if url.path == "/api/articles":
                query = parse_qs(url.query)
                try:
                    start = datetime.strptime(
                        query.get("start", [""])[0], "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    end = datetime.strptime(
                        query.get("end", [""])[0], "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc) + timedelta(days=1)
                    if start >= end:
                        raise ValueError()
                except ValueError:
                    return self.send(400, {"error": "Invalid UTC date interval"})
                denied = tombstones()
                with pg("reader") as sql:
                    rows = sql.execute(
                        "SELECT article_id,published_at,content_sha256 FROM articles WHERE synthetic=false AND published_at>=%s AND published_at<%s ORDER BY published_at DESC LIMIT 1000",
                        (start, end),
                    ).fetchall()
                return self.send(
                    200,
                    {
                        "timezone": "UTC",
                        "limit": 1000,
                        "articles": [
                            {
                                "id": row[0],
                                "published_at": row[1].isoformat(),
                                "content_sha256": row[2],
                            }
                            for row in rows
                            if row[0] not in denied
                        ],
                    },
                )
            if url.path in ("/api/article", "/article"):
                key = parse_qs(url.query).get("id", [""])[0]
                if not key or not all(c.isalnum() or c in "-_" for c in key):
                    return self.send(400, {"error": "Invalid identifier"})
                doc, mode = lookup(key)
                if url.path == "/article" and doc:
                    page = (
                        '<!doctype html><html lang="fr"><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        "<title>Article OSINT</title><style>body{font:20px Arial;"
                        "max-width:1000px;margin:45px auto;padding:24px;color:#152b39;"
                        "background:#f5f8fa}p{line-height:1.6;white-space:pre-wrap;"
                        "overflow-wrap:anywhere}a{color:#154f8a}</style>"
                        '<a href="/">Retour aux stockages</a><h1>Article source</h1>'
                        "<p>Mode de lecture : <b>" + html.escape(mode) + "</b></p>"
                        "<h2>" + html.escape(str(doc.get("title", ""))) + "</h2>"
                        "<p>Source : " + html.escape(str(doc.get("url", ""))) + "</p>"
                        "<p>" + html.escape(str(doc.get("text", ""))) + "</p></html>"
                    )
                    return self.send(200, page, "text/html; charset=utf-8")
                return self.send(200 if doc else 404, {"mode": mode, "article": doc})
            if url.path != "/":
                return self.send(404, {"error": "Not found"})
            result = metrics()
            pretty = html.escape(
                json.dumps(result, ensure_ascii=False, indent=2, default=str)
            )
            page = (
                """<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OSINT | Architecture</title>
            <style>body{font:19px Arial;max-width:1000px;margin:45px auto;padding:24px;color:#152b39;background:#f5f8fa}h1{font-size:38px}section{background:white;padding:24px;margin:24px 0;border:1px solid #b9cad4}pre{white-space:pre-wrap;font-size:18px;line-height:1.5}a{color:#154f8a}input,button{font:inherit;padding:12px;margin:6px 8px 6px 0}label{display:block}button{cursor:pointer}p{line-height:1.5}</style>
            <h1>Plateforme OSINT</h1><p>Bloc 2 · Architecture locale exécutée · Cellule de veille fictive</p>
            <section><h2>État des stockages</h2><pre>"""
                + pretty
                + """</pre><a href="/">Actualiser l’état</a></section>
            <section><h2>Retrouver un article</h2><form action="/article"><label for="id">Identifiant TASS</label><input id="id" name="id" value="2035207" required><button>Ouvrir la source stockée</button></form></section>
            <section><h2>Limites de cette démonstration</h2><p>Les essais de charge utilisent des documents synthétiques. Les textes sont chiffrés dans MongoDB et dans l’index dérivé. Le mode dégradé utilise le dernier index disponible. Cette machine unique ne protège pas contre une panne de l’hôte.</p><p>Aucun score NER ni résultat d’entités n’est inventé : le modèle sera traité au bloc 4.</p></section></html>"""
            )
            self.send(200, page, "text/html; charset=utf-8")
        except Exception:
            self.send(503, {"error": "Storage unavailable; retry later"})


def main():
    server = ThreadingHTTPServer(("0.0.0.0", 8443), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain("/run/secrets/api.crt", "/run/secrets/api.key")
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
