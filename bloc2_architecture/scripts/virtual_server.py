"""Plan or provision a dedicated local Multipass VM without transferring project data."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "memoire-osint-bloc2"
COMMAND = [
    "multipass",
    "launch",
    "24.04",
    "--name",
    NAME,
    "--cpus",
    "4",
    "--memory",
    "8G",
    "--disk",
    "30G",
    "--cloud-init",
    str(ROOT / "vm/cloud-init.yaml"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "up", "verify"))
    args = parser.parse_args()
    config = json.loads((ROOT / "vm/cloud-init.yaml").read_text().split("\n", 1)[1])
    if args.action == "plan":
        print(
            json.dumps(
                {
                    "provider_available": bool(shutil.which("multipass")),
                    "command": COMMAND,
                    "cloud_init": config,
                    "data_transfer": False,
                    "deployment_demonstrated": False,
                },
                indent=2,
            )
        )
        return
    if not shutil.which("multipass"):
        parser.error(
            "Multipass absent. Installer le fournisseur puis relancer ; aucun serveur créé."
        )
    if args.action == "up":
        inventory = subprocess.run(
            ["multipass", "list", "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
        )
        if any(vm["name"] == NAME for vm in json.loads(inventory.stdout)["list"]):
            parser.error(
                "Instance existante conservée. Utiliser verify ; aucun remplacement automatique."
            )
        subprocess.run(COMMAND, check=True)
    subprocess.run(
        ["multipass", "exec", NAME, "--", "cloud-init", "status", "--wait"], check=True
    )
    subprocess.run(
        ["multipass", "exec", NAME, "--", "sudo", "docker", "info"], check=True
    )
    subprocess.run(["multipass", "info", NAME, "--format", "json"], check=True)


if __name__ == "__main__":
    main()
