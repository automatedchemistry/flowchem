"""
Integration tests for the flowchem-sim server.

The goal here is endpoint accessibility, not device-state validation:
start the sim server with ``test_config_sim.toml`` and exercise every
documented endpoint exposed for the configured devices.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import pytest
import requests

BASE = "http://127.0.0.1:8000"
CONFIG_FILE = Path(__file__).parent / "test_config_sim.toml"
READY_TIMEOUT = 45
REQUEST_TIMEOUT = 30

SAMPLE_QUERY_VALUES: dict[str, object] = {
    "bandwidth": 8,
    "channel": "1",
    "column": "a",
    "current": "1 A",
    "do_conversion": False,
    "flowrate": "1 ml/min",
    "injection_time": "100 ms",
    "int_time": 100,
    "method-name": "smoke-method",
    "method_name": "smoke-method",
    "output_dir": "PATH/TO/open_format_ms",
    "position": "1",
    "pressure": "1 bar",
    "protocol": "H",
    "queue_name": "next.txt",
    "rate": "1 ml/min",
    "rate_left": "1 ml/min",
    "rate_right": "1 ml/min",
    "row": 1,
    "run_duration": 0,
    "sample": "smoke-sample",
    "sample-name": "smoke-sample",
    "sample_name": "smoke-sample",
    "solvent": "CDCL3",
    "switch_to_low_after": "1 s",
    "target_volume": "1 ml",
    "temp": "25 degC",
    "temperature": "25 degC",
    "treated": True,
    "tray": "",
    "units": "bar",
    "values": "00000000",
    "voltage": "5 V",
    "volume": "1 ml",
    "wavelength": 254,
}


@pytest.fixture(scope="module")
def sim_server():
    """Start flowchem-sim with the integration-test config and wait until ready."""
    repo_root = Path(__file__).parent.parent.parent
    log_handle = tempfile.NamedTemporaryFile(
        mode="w+",
        encoding="utf-8",
        prefix="flowchem-sim-",
        suffix=".log",
        delete=False,
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "flowchem.sim", str(CONFIG_FILE)],
        cwd=repo_root,
        env=os.environ | {"PYTHONUNBUFFERED": "1"},
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.monotonic() + READY_TIMEOUT
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                log_handle.flush()
                raise RuntimeError(
                    "flowchem-sim exited before becoming ready.\n"
                    + Path(log_handle.name).read_text(encoding="utf-8")
                )

            try:
                response = requests.get(
                    f"{BASE}/openapi.json",
                    timeout=1,
                    allow_redirects=True,
                )
            except requests.RequestException:
                time.sleep(0.5)
                continue

            if response.status_code == 200:
                break

            time.sleep(0.5)
        else:
            raise RuntimeError("flowchem-sim did not become ready within 45 seconds.")

    except Exception:
        process.terminate()
        process.wait(timeout=10)
        log_handle.flush()
        log_handle.close()
        raise

    yield

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    finally:
        log_handle.close()
        try:
            Path(log_handle.name).unlink(missing_ok=True)
        except PermissionError:
            pass


def configured_device_names() -> list[str]:
    """Return the device names declared in the sim integration config."""
    parsed = tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return list(parsed.get("device", {}).keys())


def request_json(path: str) -> Any:
    """GET a JSON endpoint and return the decoded payload."""
    response = requests.get(f"{BASE}{path}", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def operation_params(
    path: str, method: str, spec: dict[str, Any]
) -> tuple[dict[str, Any], Any]:
    """Build a valid smoke-test request from OpenAPI metadata and a few safe samples."""
    params: dict[str, Any] = {}
    json_body = None

    if method == "put" and path.endswith("/monitor_position"):
        params["position"] = str(request_json(path))
        return params, json_body

    if method == "put" and path.endswith("/position"):
        params["connect"] = json.dumps(request_json(path))
        return params, json_body

    if path == "/sim-spinsolve/nmr-control/user-data" and method == "put":
        return params, {"control_software": "flowchem", "sample": "smoke"}

    local_values = dict(SAMPLE_QUERY_VALUES)
    if path.endswith("/needle_position"):
        local_values["position"] = "WASTE"
    elif path.endswith("/set_x_position"):
        local_values["position"] = 1
    elif path.endswith("/set_y_position"):
        local_values["position"] = "a"
    elif path.endswith("/set_z_position"):
        local_values["position"] = "UP"

    for parameter in spec.get("parameters", []):
        name = parameter["name"]
        default = parameter.get("schema", {}).get("default")
        if name in local_values:
            params[name] = local_values[name]
        elif parameter.get("required", False) or default is not None:
            params[name] = default

    return params, json_body


def iter_configured_operations(
    openapi: dict[str, Any],
) -> list[tuple[str, str, dict[str, Any]]]:
    """List all OpenAPI operations that belong to devices in test_config_sim.toml."""
    operations: list[tuple[str, str, dict[str, Any]]] = []
    for device_name in configured_device_names():
        prefix = f"/{device_name}/"
        for path, path_item in sorted(openapi["paths"].items()):
            if path.startswith(prefix):
                for method, spec in sorted(path_item.items()):
                    operations.append((method, path, spec))
    return operations


class TestSimServerEndpointAccessibility:
    """Smoke-test only that configured sim endpoints are reachable."""

    def test_server_root_redirects(self, sim_server):
        response = requests.get(
            f"{BASE}/", timeout=REQUEST_TIMEOUT, allow_redirects=True
        )
        assert response.status_code == 200

    def test_configured_device_roots_are_reachable(self, sim_server):
        failures: list[str] = []
        for device_name in configured_device_names():
            response = requests.get(f"{BASE}/{device_name}/", timeout=REQUEST_TIMEOUT)
            if response.status_code >= 400:
                failures.append(
                    f"GET /{device_name}/ -> {response.status_code}: {response.text}"
                )

        assert not failures, "\n".join(failures)

    def test_all_documented_device_endpoints_are_accessible(self, sim_server):
        openapi = request_json("/openapi.json")
        failures: list[str] = []

        for method, path, spec in iter_configured_operations(openapi):
            params, json_body = operation_params(path, method, spec)
            try:
                response = requests.request(
                    method.upper(),
                    f"{BASE}{path}",
                    params=params or None,
                    json=json_body,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                failures.append(f"{method.upper()} {path} -> request failed: {exc}")
                continue

            if response.status_code >= 400:
                body = response.text[:300]
                failures.append(
                    f"{method.upper()} {path} -> {response.status_code} "
                    f"(params={params}, json={json_body}): {body}"
                )

        assert not failures, "\n".join(failures)
