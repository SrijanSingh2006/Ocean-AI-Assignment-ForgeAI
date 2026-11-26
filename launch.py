"""Prepare this checkout and launch ForgeAI Studio."""

import argparse
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WEB_HOST = "127.0.0.1"


def responds(url, timeout=0.7):
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def prepare_python():
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("Creating the ForgeAI Python environment…", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)
    marker = VENV / "forgeai-install.toml"
    manifest = (ROOT / "pyproject.toml").read_bytes()
    if not marker.exists() or marker.read_bytes() != manifest:
        print("Installing ForgeAI and its dependencies…", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "-e", "."], cwd=ROOT, check=True)
        marker.write_bytes(manifest)
    return python


def start_model():
    model_url = os.getenv("FORGE_MODEL_URL", "http://127.0.0.1:8089/v1").rstrip("/")
    if responds(model_url + "/models"):
        return None
    can_download = sys.platform.startswith("linux") and platform.machine() == "x86_64"
    if not can_download or model_url != "http://127.0.0.1:8089/v1":
        raise RuntimeError("Start the local model server described in README.md, then run the launcher again.")
    script = ROOT / "scripts" / "local-model.sh"
    print("Starting Qwen. The first run downloads about 491 MB of model weights.", flush=True)
    process = subprocess.Popen(["bash", str(script)], cwd=ROOT)
    try:
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if responds(model_url + "/models"):
                return process
            if process.poll() is not None:
                raise RuntimeError(f"The Qwen server exited with code {process.returncode}.")
            time.sleep(1)
        raise RuntimeError("The model server did not become ready within ten minutes.")
    except BaseException:
        stop(process)
        raise


def free_port(preferred):
    for port in range(preferred, min(65536, preferred + 20)):
        with socket.socket() as probe:
            try:
                probe.bind((WEB_HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free port nearby. Pass --port followed by another port number.")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def open_when_ready(url, service):
    for _ in range(80):
        if service.poll() is not None:
            return
        if responds(url):
            webbrowser.open(url)
            return
        time.sleep(0.25)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-model", action="store_true", help="Start Qwen before launching Studio")
    parser.add_argument("--no-browser", action="store_true", help="Print the address without opening a browser")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("ForgeAI needs Python 3.10 or newer.")
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535.")
    model = service = None
    try:
        python = prepare_python()
        if args.with_model:
            model = start_model()
        port = free_port(args.port)
        url = f"http://{WEB_HOST}:{port}"
        print(f"ForgeAI Studio · {url}", flush=True)
        service = subprocess.Popen([str(python), "-m", "forgeai", "serve", "--port", str(port)], cwd=ROOT)
        if not args.no_browser:
            threading.Thread(target=open_when_ready, args=(url, service), daemon=True).start()
        return service.wait()
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ForgeAI launcher: {error}", file=sys.stderr)
        return 1
    finally:
        stop(service)
        stop(model)


if __name__ == "__main__":
    sys.exit(main())
