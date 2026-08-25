#!/usr/bin/env python3
"""Arranca un paquete nativo y comprueba que una instalación nueva esté vacía."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_health(url: str, process: subprocess.Popen[bytes], timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"El ejecutable terminó antes del health check: {process.returncode}")
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=1.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("ok") is True and payload.get("data", {}).get("status") == "ok":
                return payload
        except (OSError, UnicodeError, ValueError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"El health check no respondió a tiempo: {last_error}")


def business_counts(database: Path) -> dict[str, int]:
    connection = sqlite3.connect(database)
    try:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("teams", "adjustments", "matches")
        }
    finally:
        connection.close()


def smoke(executable: Path, *, expected_version: str, timeout: float) -> dict:
    executable = executable.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"No existe el ejecutable: {executable}")
    port = available_port()
    with tempfile.TemporaryDirectory(prefix="betplaycito-native-smoke-") as raw_directory:
        directory = Path(raw_directory)
        data_dir = directory / "datos"
        log_path = directory / "application.log"
        environment = os.environ.copy()
        environment["BETPLAYCITO_BACKUP_DIR"] = str(directory / "respaldos")
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                [
                    str(executable),
                    "--no-browser",
                    "--port",
                    str(port),
                    "--data-dir",
                    str(data_dir),
                    "--config",
                    str(directory / "config.json"),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            try:
                payload = wait_for_health(
                    f"http://127.0.0.1:{port}/api/health",
                    process,
                    timeout,
                )
                health = payload["data"]
                if health.get("version") != expected_version:
                    raise RuntimeError(
                        f"Versión inesperada: {health.get('version')} != {expected_version}"
                    )
                counts = business_counts(data_dir / "betplaycito.db")
                if counts != {"teams": 0, "adjustments": 0, "matches": 0}:
                    raise RuntimeError(f"La base nueva contiene datos de negocio: {counts}")
            except Exception as exc:
                log.flush()
                details = log_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(f"{exc}\n--- registro del ejecutable ---\n{details}") from exc
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
        return {"health": health, "business_rows": counts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--version", required=True, dest="expected_version")
    parser.add_argument("--timeout", type=float, default=30.0)
    arguments = parser.parse_args()
    result = smoke(
        arguments.executable,
        expected_version=arguments.expected_version,
        timeout=arguments.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
