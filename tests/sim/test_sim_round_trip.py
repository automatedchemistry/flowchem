"""A simulated device must read back what was set.

Each case PUTs a value through the HTTP API and GETs it back from the same component.
Devices come from ``test_config_sim.toml`` and are served in-process by the same
``FastAPIServer`` that flowchem-sim uses, so no port or subprocess is needed.
"""

import tomllib
from pathlib import Path

import httpx
import pytest

from flowchem.devices.list_known_device_type import autodiscover_device_classes
from flowchem.server.configuration_parser import parse_device
from flowchem.server.fastapi_server import FastAPIServer
from flowchem.sim.registry import build_sim_device_mapper

CONFIG = tomllib.loads(
    (Path(__file__).parent / "test_config_sim.toml").read_text(encoding="utf-8")
)["device"]
SIM_DEVICE_CLASSES = build_sim_device_mapper(autodiscover_device_classes())

# (device, component, PUT route and query, GET route and query, expected reading)
# A ``None`` PUT reads the start-up state. Values differ from the start-up state on purpose.
CASES = [
    # Temperature
    (
        "sim-huber",
        "temperature-control",
        ("temperature", {"temp": "-8.7 °C"}),
        ("temperature", {}),
        -8.7,
    ),
    (
        "sim-huber",
        "temperature-control",
        ("temperature", {"temp": "-8.7 °C"}),
        ("temperature-setpoint", {}),
        -8.7,
    ),
    (
        "sim-huber",
        "temperature-control",
        ("temperature", {"temp": "20.5"}),
        ("temperature", {}),
        20.5,
    ),
    (
        "sim-huber",
        "temperature-control",
        ("temperature", {"temp": "0 °C"}),
        ("target-reached", {}),
        True,
    ),
    (
        "sim-huber",
        "temperature-control",
        ("temperature", {"temp": "0 °C"}),
        ("is-idle", {}),
        True,
    ),
    (
        "sim-heidolph",
        "temperature-control",
        ("temperature", {"temp": "80 °C"}),
        ("temperature", {}),
        80.0,
    ),
    (
        "sim-heidolph",
        "temperature-control",
        ("temperature", {"temp": "80 °C"}),
        ("temperature-setpoint", {}),
        80.0,
    ),
    (
        "sim-r4",
        "reactor1",
        ("temperature", {"temp": "60.5 °C"}),
        ("temperature", {}),
        60.5,
    ),
    (
        "sim-r4",
        "reactor1",
        ("temperature", {"temp": "60.5 °C"}),
        ("temperature-setpoint", {}),
        60.5,
    ),
    (
        "sim-peltier",
        "temperature_control",
        ("temperature", {"temperature": "300 K"}),
        ("temperature", {}),
        26.85,
    ),
    (
        "sim-peltier",
        "temperature_control",
        ("temperature", {"temperature": "300 K"}),
        ("temperature-setpoint", {}),
        26.85,
    ),
    # Stirring. The measured speed stays 0 until stirring is switched on, because the
    # Heidolph driver reports is-on as "speed > 0" (see tests/sim/heidolph).
    (
        "sim-heidolph",
        "stirring-control",
        ("speed", {"speed": "300 rpm"}),
        ("speed-setpoint", {}),
        300.0,
    ),
    ("sim-heidolph", "stirring-control", ("power-on", {}), ("is-on", {}), True),
    # Pressure and flow
    (
        "sim-cvc3000",
        "pressure-control",
        ("pressure", {"pressure": "200 mbar"}),
        ("pressure", {}),
        200.0,
    ),
    (
        "sim-cvc3000",
        "pressure-control",
        ("pressure", {"pressure": "200 mbar"}),
        ("target-reached", {}),
        True,
    ),
    (
        "sim-ebpr",
        "pressure",
        ("pressure", {"pressure": "2 bar"}),
        ("pressure", {}),
        2.0,
    ),
    (
        "sim-epc",
        "EPC",
        ("set-pressure", {"pressure": "2.5 bar"}),
        ("get-pressure", {}),
        2.5,
    ),
    (
        "sim-epc",
        "EPC",
        ("set-pressure", {"pressure": "2.5 bar"}),
        ("read-pressure", {"units": "mbar"}),
        2500.0,
    ),
    (
        "sim-mfc",
        "MFC",
        ("set-flow-rate", {"flowrate": "3.5 ml/min"}),
        ("get-flow-rate", {}),
        3.5,
    ),
    # Power supply
    (
        "sim-manson",
        "power-control",
        ("voltage", {"voltage": "12.5 V"}),
        ("voltage", {}),
        12.5,
    ),
    (
        "sim-manson",
        "power-control",
        ("current", {"current": "1.5 A"}),
        ("current", {}),
        1.5,
    ),
    # Relays and analog outputs
    (
        "sim-switchbox",
        "relay-A",
        ("power-on", {"channel": "3"}),
        ("channel_set_point", {"channel": "3"}),
        2,
    ),
    (
        "sim-switchbox",
        "relay-B",
        ("power-on", {"channel": "10"}),
        ("channel_set_point", {"channel": "10"}),
        2,
    ),
    (
        "sim-switchbox",
        "relay-B",
        ("power-on", {"channel": "10"}),
        ("is-on", {"channel": "10"}),
        True,
    ),
    (
        "sim-switchbox",
        "dac",
        ("set", {"channel": "1", "value": "2.5 V"}),
        ("read", {"channel": "1"}),
        2.5,
    ),
    (
        "sim-ni",
        "relay",
        ("power-on", {"channel": "2"}),
        ("is-on", {"channel": "2"}),
        True,
    ),
    (
        "sim-ni6519",
        "relay",
        ("power-on", {"channel": "2"}),
        ("is-on", {"channel": "2"}),
        True,
    ),
    (
        "sim-nidaq-analog",
        "dac",
        ("set", {"channel": "1", "value": "2.5 V"}),
        ("read", {"channel": "1"}),
        2.5,
    ),
    # Valves
    (
        "sim-knauer-valve",
        "distribution-valve",
        ("monitor_position", {"position": "4"}),
        ("monitor_position", {}),
        "4",
    ),
    (
        "sim-knauer-injection",
        "injection-valve",
        None,
        ("monitor_position", {}),
        "LOAD",
    ),
    (
        "sim-knauer-injection",
        "injection-valve",
        ("monitor_position", {"position": "inject"}),
        ("monitor_position", {}),
        "INJECT",
    ),
    (
        "sim-runze",
        "distribution-valve",
        ("monitor_position", {"position": "4"}),
        ("monitor_position", {}),
        "4",
    ),
    ("sim-solenoid", "valve", ("close", {}), ("is_open", {}), False),
    ("sim-ni-solenoid", "valve", ("open", {}), ("is_open", {}), True),
    ("sim-solenoid-2way", "valve", ("open", {}), ("is_open", {}), True),
]


def _case_id(case) -> str:
    device, component, put, get, expected = case
    action = put[0] if put else "start-up"
    return f"{device}/{component} {action} -> {get[0]}={expected}"


@pytest.mark.parametrize(
    ("device", "component", "put", "get", "expected"),
    CASES,
    ids=[_case_id(case) for case in CASES],
)
async def test_get_returns_what_was_set(device, component, put, get, expected):
    sim_device = parse_device((device, dict(CONFIG[device])), SIM_DEVICE_CLASSES)
    await sim_device.initialize()
    server = FastAPIServer()
    server.add_device(sim_device)
    root = f"/{device}/{component}/"

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://sim") as client:
        if put is not None:
            put_path, put_query = put
            response = await client.put(root + put_path, params=put_query)
            assert response.status_code == 200, response.text
        get_path, get_query = get
        response = await client.get(root + get_path, params=get_query)
        assert response.status_code == 200, response.text

    reading = response.json()
    if isinstance(expected, float):
        assert reading == pytest.approx(expected, abs=0.001)
    else:
        assert reading == expected
