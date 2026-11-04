"""The configuration file has to keep working with flowchem-sim, whatever else the user adds to it."""

import tomllib
from pathlib import Path

import pytest

from flowchem.devices.list_known_device_type import autodiscover_device_classes
from flowchem.server.configuration_parser import parse_device
from flowchem.sim.registry import build_sim_device_mapper

CONFIG = tomllib.loads(
    (Path(__file__).parent / "test_config_sim.toml").read_text(encoding="utf-8")
)["device"]
SIM_DEVICE_CLASSES = build_sim_device_mapper(autodiscover_device_classes())


@pytest.mark.parametrize("device_name", CONFIG)
def test_sim_device_ignores_extra_settings_and_keeps_the_id(device_name):
    settings = {
        **CONFIG[device_name],
        "unknown_setting": 1,
        "name": "another-name",
        "id": "UNIT-1",
    }

    device = parse_device((device_name, settings), SIM_DEVICE_CLASSES)

    assert device.name == device_name
    assert device.device_info.id == "UNIT-1"


def test_sim_only_setting_still_reaches_the_simulated_device():
    settings = {"type": "RunzeValve", "port": "COM_SIM", "num_ports": 12}

    device = parse_device(("valve", settings), SIM_DEVICE_CLASSES)

    assert device.sim_io._sim_num_ports == 12
