"""Immutable local releases, stable loopback gateway and verified rollback.

Processes survive the invoking terminal, but not a reboot. This is a local
demonstration target; it does not expose the service to the internet.
"""

import argparse
import contextlib
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .contracts import atomic_json, file_sha, utcnow


def request_json(port, path="/health"):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as response:
        return json.load(response)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_ready(process, port, token, path="/health"):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and process.poll() is None:
        try:
            data = request_json(port, path)
            if data.get("release_token") == token:
                return data
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    process.terminate()
    process.wait(timeout=10)
    raise RuntimeError("Local release failed readiness; see deployment logs")


def start_process(args, release, state, token):
    env = dict(
        os.environ,
        PYTHONPATH=str(release),
        OSINT_RELEASE_TOKEN=token,
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
    )
    with (state / f"process-{token}.log").open("ab") as log:
        return subprocess.Popen(
            [sys.executable, *args],
            cwd=release,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )


def gateway(state, port):
    """Read active pointer per request so a healthy backend can be switched atomically."""

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def forward(self):
            host = self.headers.get("Host", "")
            if host not in (f"127.0.0.1:{port}", f"localhost:{port}") or self.headers.get(
                "Origin"
            ) not in (None, f"http://{host}"):
                self.send_error(403)
                return
            if self.path == "/deployment-health" and self.command == "GET":
                body = json.dumps(
                    {"release_token": os.environ["OSINT_RELEASE_TOKEN"], "status": "gateway_ready"}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                if len(self.path) > 4096:
                    self.send_error(414)
                    return
                body = None
                headers = {}
                if self.command == "POST":
                    lengths = self.headers.get_all("Content-Length", [])
                    if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                        self.send_error(400)
                        return
                    length = int(lengths[0])
                    if not 0 < length <= 404096:
                        self.send_error(413)
                        return
                    body = self.rfile.read(length)
                    if len(body) != length:
                        self.send_error(400)
                        return
                    headers["Content-Type"] = self.headers.get("Content-Type", "")
                active = json.loads((state / "current.json").read_text())
                req = urllib.request.Request(
                    f"http://127.0.0.1:{active['backend_port']}{self.path}",
                    data=body,
                    headers=headers,
                    method=self.command,
                )
                try:
                    response = urllib.request.urlopen(req, timeout=15)
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    payload = response.read()
                    self.send_response(response.status)
                    for name in (
                        "Content-Type",
                        "Cache-Control",
                        "Content-Security-Policy",
                        "X-Content-Type-Options",
                    ):
                        if response.headers.get(name):
                            self.send_header(name, response.headers[name])
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
            except (OSError, ValueError, KeyError):
                self.send_error(503, "Local backend unavailable")

        do_GET = forward
        do_POST = forward

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


@contextlib.contextmanager
def locked(state):
    # Resolve an existing encrypted symlink; mkdir must fail if its volume is absent.
    state = Path(state).absolute()
    state.mkdir(parents=True, exist_ok=True)
    with (state / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield state


def owned_alive(entry):
    try:
        return request_json(entry["backend_port"]).get("release_token") == entry["release_token"]
    except (OSError, ValueError):
        return False


def stop_entry(entry):
    # Never signal a reused PID unless its live service presents our identity.
    if entry and owned_alive(entry):
        os.kill(entry["pid"], signal.SIGTERM)


def deploy(wheel, data, run, state, port=8766):
    started = time.perf_counter()
    wheel, data, run = (
        Path(wheel).resolve(strict=True),
        Path(data).resolve(strict=True),
        Path(run).resolve(strict=True),
    )
    with locked(state) as state:
        checksum = file_sha(wheel)
        release = state / "releases" / checksum
        if not (release / "installed.json").exists():
            if release.exists():
                raise ValueError("Incomplete release retained; inspect before retrying")
            release.mkdir(parents=True)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--no-compile",
                    "--target",
                    str(release),
                    str(wheel),
                ],
                capture_output=True,
                text=True,
            )
            (release / "install.log").write_text(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError("Wheel installation failed")
            atomic_json(release / "installed.json", {"wheel_sha256": checksum})
        pointer = state / "current.json"
        previous = json.loads(pointer.read_text()) if pointer.exists() else None
        backend_port, token = free_port(), uuid.uuid4().hex
        proc = start_process(
            [
                "-m",
                "osint_ner.cli",
                "serve",
                "--data",
                str(data),
                "--run",
                str(run),
                "--port",
                str(backend_port),
            ],
            release,
            state,
            token,
        )
        health = wait_ready(proc, backend_port, token)
        candidate = {
            "wheel_sha256": checksum,
            "release": str(release),
            "data": str(data),
            "run": str(run),
            "backend_port": backend_port,
            "release_token": token,
            "pid": proc.pid,
            "deployed_at": utcnow(),
            "model_sha256": health["model_sha256"],
            "previous": previous,
            "environment": "local_loopback_demo",
        }
        gateway_path = state / "gateway.json"
        gateway_info = json.loads(gateway_path.read_text()) if gateway_path.exists() else None
        if gateway_info:
            if gateway_info["port"] != port:
                stop_entry(candidate)
                raise ValueError("Gateway port changed; stop the existing deployment first")
            try:
                active = request_json(port, "/deployment-health")
            except OSError:
                active = {}
            if active.get("release_token") != gateway_info["release_token"]:
                gateway_info = None
        atomic_json(pointer, candidate)
        try:
            if not gateway_info:
                gateway_token = uuid.uuid4().hex
                process = start_process(
                    [
                        "-m",
                        "osint_ner.deployment",
                        "gateway",
                        "--state",
                        str(state),
                        "--port",
                        str(port),
                    ],
                    release,
                    state,
                    gateway_token,
                )
                wait_ready(process, port, gateway_token, "/deployment-health")
                gateway_info = {"pid": process.pid, "port": port, "release_token": gateway_token}
                atomic_json(gateway_path, gateway_info)
            routed = request_json(port)
            if routed.get("release_token") != token or not routed.get("prediction_ready"):
                raise RuntimeError("Gateway did not serve the new prediction model")
        except Exception:
            if previous:
                atomic_json(pointer, previous)
            else:
                pointer.unlink(missing_ok=True)
            stop_entry(candidate)
            raise
        # Keep one prior backend alive for immediate rollback; retire older ones.
        if previous:
            stop_entry(previous.get("previous"))
        event = {
            "action": "deployed",
            "at": utcnow(),
            "deployment": candidate,
            "health": routed,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "gateway_port": port,
            "model_promoted_to_production": False,
        }
        atomic_json(state / "last_operation.json", event)
        return event


def rollback(state):
    with locked(state) as state:
        current = json.loads((state / "current.json").read_text())
        previous = current.get("previous")
        if not previous or not owned_alive(previous):
            raise ValueError("Previous backend unavailable; redeploy its immutable wheel")
        gateway_info = json.loads((state / "gateway.json").read_text())
        atomic_json(state / "current.json", previous)
        try:
            health = request_json(gateway_info["port"])
            if health.get("release_token") != previous["release_token"]:
                raise RuntimeError("Rollback routing failed")
        except Exception:
            atomic_json(state / "current.json", current)
            raise
        stop_entry(current)
        event = {
            "action": "rollback",
            "at": utcnow(),
            "health": health,
            "restored_wheel_sha256": previous["wheel_sha256"],
        }
        atomic_json(state / "last_operation.json", event)
        return event


def stop(state):
    with locked(state) as state:
        pointer = state / "current.json"
        current = json.loads(pointer.read_text()) if pointer.exists() else None
        while current:
            stop_entry(current)
            current = current.get("previous")
        gateway_path = state / "gateway.json"
        if gateway_path.exists():
            info = json.loads(gateway_path.read_text())
            try:
                identity = request_json(info["port"], "/deployment-health")
                if identity.get("release_token") == info["release_token"]:
                    os.kill(info["pid"], signal.SIGTERM)
            except OSError:
                pass
            gateway_path.unlink()
        pointer.unlink(missing_ok=True)
        return {"action": "stopped", "at": utcnow()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("deploy", "rollback", "stop", "status", "gateway"))
    parser.add_argument("--state", required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--wheel")
    parser.add_argument("--data")
    parser.add_argument("--run")
    args = parser.parse_args()
    if args.action == "gateway":
        gateway(Path(args.state), args.port)
        return
    if args.action == "deploy":
        if not all((args.wheel, args.data, args.run)):
            parser.error("deploy requires --wheel, --data and --run")
        result = deploy(args.wheel, args.data, args.run, args.state, args.port)
    elif args.action == "rollback":
        result = rollback(args.state)
    elif args.action == "stop":
        result = stop(args.state)
    else:
        info = json.loads((Path(args.state) / "gateway.json").read_text())
        result = request_json(info["port"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
