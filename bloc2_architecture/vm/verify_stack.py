"""Read-only checks for the dedicated VM's synthetic Bloc 2 deployment."""

import base64
import json
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def request(path, authenticated=True):
    query = urllib.request.Request("https://localhost:18443" + path)
    if authenticated:
        password = (ROOT / ".secrets/api_password").read_text().strip()
        query.add_header(
            "Authorization",
            "Basic " + base64.b64encode(("analyste:" + password).encode()).decode(),
        )
    context = ssl.create_default_context(cafile=str(ROOT / ".secrets/ca.crt"))
    with urllib.request.urlopen(query, context=context, timeout=15) as response:
        return json.load(response)


def main():
    health = request("/health", False)
    assert health["service"] == "up"
    try:
        request("/api/status", False)
        raise AssertionError("Unauthenticated request was accepted")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    status = request("/api/status")
    assert status["mode"] == "primary"
    assert (
        status["articles"] == 0
        and status["synthetic"] == 100
        and status["documents"] == 100
    )
    article = request("/api/article?id=synthetic-000000000")
    assert article["mode"] == "primary"
    assert article["article"]["title"] == "Synthetic record 0"
    assert article["article"]["url"] == "https://example.invalid/synthetic"
    sql_tls = subprocess.check_output(
        [
            "sudo",
            "docker",
            "compose",
            "exec",
            "-T",
            "app",
            "python",
            "-c",
            "import json; from osint.storage import pg; c=pg(); print(json.dumps(c.execute('SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()))",
        ],
        cwd=ROOT,
        text=True,
    )
    tls = json.loads(sql_tls)
    assert tls[0] is True
    print(
        json.dumps(
            {
                "scope": "VM dédiée, 100 documents synthétiques, aucun corpus TASS",
                "checks": {
                    "https_health": True,
                    "unauthenticated_rejected": True,
                    "sql_mongo_counts": True,
                    "authenticated_article_roundtrip": True,
                    "postgres_tls": True,
                },
                "status": status,
                "postgres_tls": tls,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
