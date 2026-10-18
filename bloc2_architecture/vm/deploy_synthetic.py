"""Deploy only public code and generated fixtures inside the dedicated Bloc 2 VM."""

import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "memoire-osint-bloc2"
REMOTE = "/home/ubuntu/memoire-osint-bloc2"


def run(*args, **kwargs):
    return subprocess.run(["multipass", *args], check=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "verify"])
    parser.add_argument("--proofs", type=Path, required=True)
    args = parser.parse_args()
    args.proofs.mkdir(parents=True, exist_ok=True)
    if args.action == "deploy":
        names = [
            "docker-compose.yml",
            ".env.example",
            "scripts/setup.py",
            "scripts/postgres-entrypoint.sh",
            "scripts/mongo-entrypoint.sh",
            "vm/verify_stack.py",
        ]
        for directory in ["app", "sql", "mongo", "docs"]:
            names.extend(
                str(p.relative_to(ROOT))
                for p in (ROOT / directory).rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and (
                    p.suffix
                    in [".py", ".txt", ".sql", ".sh", ".json", ".js", ".conf", ".dbml"]
                    or p.name == "Dockerfile"
                )
            )
        names = sorted(set(names))
        with tempfile.TemporaryDirectory(prefix="osint-vm-public-") as temporary:
            bundle = Path(temporary) / "public-code.tar.gz"
            with tarfile.open(bundle, "w:gz") as archive:
                for name in names:
                    path = ROOT / name
                    if path.is_symlink() or any(
                        part.startswith(".")
                        for part in Path(name).parts
                        if part != ".env.example"
                    ):
                        raise ValueError(
                            "Only allowlisted public code may be transferred"
                        )
                    archive.add(path, arcname=name)
            manifest = {
                "scope": "Public code only; no corpus, existing secret, model, guide or video",
                "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
                "files": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    for name in names
                },
            }
            (args.proofs / "Manifest_deploiement.json").write_text(
                json.dumps(manifest, indent=2) + "\n"
            )
            # Refuse to alter a previous deployment, even if its data appears synthetic.
            run("exec", NAME, "--", "test", "!", "-e", REMOTE)
            run("transfer", str(bundle), NAME + ":public-code.tar.gz")
            script = f"""set -eu
umask 077
mkdir {REMOTE}
tar -xzf /home/ubuntu/public-code.tar.gz -C {REMOTE}
rm /home/ubuntu/public-code.tar.gz
cd {REMOTE}
find app sql mongo docs scripts vm -type d -exec chmod 755 {{}} +
find app sql mongo docs scripts vm -type f -exec chmod 644 {{}} +
python3 scripts/setup.py
mkdir -p Preuves
sudo chown 10001:10001 .state .data Preuves
sudo chmod 700 .state .data Preuves
sudo docker compose up -d --build --wait --wait-timeout 240 postgres mongo app
sudo docker compose run --rm --no-deps --user 10001:10001 ops python -m osint.cli ingest --synthetic 100
"""
            with (args.proofs / "Services_deploiement.log").open("w") as log:
                run(
                    "exec",
                    NAME,
                    "--",
                    "bash",
                    "-se",
                    input=script,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
    result = run(
        "exec",
        NAME,
        "--",
        "bash",
        "-lc",
        f"cd {REMOTE} && python3 vm/verify_stack.py",
        capture_output=True,
    )
    proof = json.loads(result.stdout)
    (args.proofs / "Verification_services.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(proof, ensure_ascii=False))


if __name__ == "__main__":
    main()
