from __future__ import annotations

import pytest

from flowchem.sim.devices.ni.ni6519_sim import NI6519Sim
from flowchem.components.technical.relay import Relay


@pytest.fixture(autouse=True)
def cleanup_relay_registry():
    yield
    Relay.INSTANCES.pop("sim-ni6519/relay", None)


@pytest.fixture
async def sim_ni6519() -> NI6519Sim:
    device = NI6519Sim.from_config(name="sim-ni6519")
    await device.initialize()
    return device


async def test_sim_initializes_components(sim_ni6519):
    assert [component.name for component in sim_ni6519.components] == [
        "relay",
        "digital-input",
    ]
    assert len(sim_ni6519.sim_output_task.writes) == 1


async def test_sim_output_and_input(sim_ni6519):
    relay = sim_ni6519.components[0]
    digital_input = sim_ni6519.components[1]

    assert await relay.power_on(channel=16) is True
    assert await relay.read_channel_set_point(channel=16) == 1

    sim_ni6519.sim_input_task.values[3] = True
    assert await digital_input.read(channel=4) == 1
