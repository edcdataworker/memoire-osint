"""Exercise an already-built image with explicitly synthetic, read-only artifacts."""

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [
        json.loads(line) for line in (args.artifacts / "inference.jsonl").read_text().splitlines()
    ]
    if not rows or not all(row.get("synthetic") for row in rows):
        parser.error("Only explicitly synthetic fixtures are accepted by this smoke test")
    name = "osint-bloc4-smoke-" + str(time.time_ns())
    result = {"synthetic": True, "checks": {}}
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--read-only",
            "--tmpfs",
            "/tmp:size=64m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--memory",
            "1g",
            "--cpus",
            "1",
            "-p",
            "127.0.0.1::8764",
            "--mount",
            f"type=bind,src={args.artifacts.resolve()},dst=/artifacts,readonly",
            "memoire-osint-bloc4:local",
        ],
        check=True,
        capture_output=True,
    )
    try:
        inspect = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
        port = inspect["NetworkSettings"]["Ports"]["8764/tcp"][0]["HostPort"]
        url = "http://127.0.0.1:" + port
        for attempt in range(60):
            try:
                health = json.load(urllib.request.urlopen(url + "/health", timeout=3))
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.5)
        else:
            raise RuntimeError("Container health timeout")
        assert inspect["Config"]["User"] == "10001:10001"
        assert inspect["HostConfig"]["ReadonlyRootfs"]
        assert all(m["RW"] is False for m in inspect["Mounts"] if m["Type"] == "bind")
        result["checks"]["non_root_readonly"] = True
        result["health"] = health
        request = urllib.request.Request(
            url + "/api/predict",
            data=json.dumps(
                {"text": "Synthetic exercise: NATO observed a Kalibr display."}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        prediction = json.load(urllib.request.urlopen(request, timeout=30))
        assert prediction["retention"] == "not_persisted"
        result["checks"]["prediction"] = True
        request = urllib.request.Request(url + "/health", headers={"Host": "untrusted.example"})
        try:
            urllib.request.urlopen(request, timeout=3)
            raise AssertionError("Untrusted Host accepted")
        except urllib.error.HTTPError as error:
            assert error.code == 403
        result["checks"]["host_rejection"] = True
        result["metrics"] = json.load(urllib.request.urlopen(url + "/api/metrics", timeout=3))
        result["image_id"] = inspect["Image"]
        result["limits"] = (
            "Local synthetic serving only; no TASS model quality or external production claim."
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=True, capture_output=True)


if __name__ == "__main__":
    main()
