"""Create local credentials and TLS certificates; never print secret values."""

import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
SEC = ROOT / ".secrets"
SEC.mkdir(mode=0o700, exist_ok=True)
SEC.chmod(0o700)
for name in (
    "pg_admin",
    "writer",
    "reader",
    "mongo_admin",
    "elastic",
    "api_password",
    "pgadmin",
    "mongo_express",
    "portainer",
    "kibana",
):
    path = SEC / name
    if not path.exists():
        path.write_text(secrets.token_hex(24))
        path.chmod(
            0o644
        )  # Parent 0700; bind-mounted individually for non-root containers.
for name in ("data_key", "backup_key"):
    path = SEC / name
    if not path.exists():
        path.write_bytes(base64.b64encode(secrets.token_bytes(32)))
        path.chmod(0o644)


def openssl(*args):
    subprocess.run(
        ["openssl", *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if not (SEC / "ca.crt").exists():
    openssl(
        "req",
        "-x509",
        "-newkey",
        "rsa:3072",
        "-nodes",
        "-days",
        "365",
        "-keyout",
        str(SEC / "ca.key"),
        "-out",
        str(SEC / "ca.crt"),
        "-subj",
        "/CN=Memoire OSINT Local CA",
    )
for name in ("postgres", "mongo", "elasticsearch", "api", "kibana"):
    if (SEC / f"{name}.crt").exists():
        continue
    ext = SEC / f"{name}.ext"
    ext.write_text(
        f"subjectAltName=DNS:{name},DNS:localhost,IP:127.0.0.1\n"
        "extendedKeyUsage=serverAuth\n"
    )
    openssl(
        "req",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(SEC / f"{name}.key"),
        "-out",
        str(SEC / f"{name}.csr"),
        "-subj",
        f"/CN={name}",
    )
    openssl(
        "x509",
        "-req",
        "-days",
        "365",
        "-in",
        str(SEC / f"{name}.csr"),
        "-CA",
        str(SEC / "ca.crt"),
        "-CAkey",
        str(SEC / "ca.key"),
        "-CAcreateserial",
        "-out",
        str(SEC / f"{name}.crt"),
        "-extfile",
        str(ext),
    )
    (SEC / f"{name}.pem").write_bytes(
        (SEC / f"{name}.key").read_bytes() + (SEC / f"{name}.crt").read_bytes()
    )
for path in SEC.iterdir():
    path.chmod(0o600 if path.name == "ca.key" else 0o644)
if not Path(".env").exists():
    shutil.copyfile(".env.example", ".env")
    Path(".env").chmod(0o600)
for name in (".data", ".backups", ".state"):
    Path(name).mkdir(mode=0o700, exist_ok=True)
# Reader-only pgAdmin connection preconfigured. Password is entered interactively.
Path("docs/pgadmin-servers.json").write_text(
    json.dumps(
        {
            "Servers": {
                "1": {
                    "Name": "OSINT lecture TLS",
                    "Group": "Mémoire",
                    "Host": "postgres",
                    "Port": 5432,
                    "MaintenanceDB": "osint",
                    "Username": "osint_reader",
                    "SSLMode": "require",
                }
            }
        },
        indent=2,
    )
)
print("Configuration locale créée. Valeurs secrètes exclues du dossier de remise.")
