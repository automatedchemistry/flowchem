from __future__ import annotations

import pytest

from flowchem.devices.biochem.solenoid_valve import BioChemSolenoidValve
from flowchem.sim.devices.ni.ni9477_sim import NI9477Sim
from flowchem.components.technical.relay import Relay


@pytest.fixture(autouse=True)
def cleanup_relay_registry():
    yield
    Relay.INSTANCES.pop("sim-ni/relay", None)


@pytest.fixture
async def sim_ni9477() -> NI9477Sim:
    device = NI9477Sim.from_config(name="sim-ni")
    await device.initialize()
    return device


async def test_sim_initializes_relay_component(sim_ni9477):
    assert len(sim_ni9477.components) == 1
    assert sim_ni9477.components[0].name == "relay"
    assert len(sim_ni9477.sim_task.writes) == 1


async def test_sim_single_channel_on_off(sim_ni9477):
    relay = sim_ni9477.components[0]

    assert await relay.power_on(channel=32) is True
    assert await relay.read_channel_set_point(channel=32) == 1
    assert await relay.is_on(channel=32) is True

    assert await relay.power_off(channel=32) is True
    assert await relay.read_channel_set_point(channel=32) == 0
    assert await relay.is_on(channel=32) is False


async def test_sim_read_all_channels(sim_ni9477):
    relay = sim_ni9477.components[0]

    await relay.power_on(channel=2)
    states = await relay.read_channels_set_point()

    assert len(states) == 32
    assert states[1] == 1
    assert sum(states) == 1


async def test_sim_batch_set(sim_ni9477):
    relay = sim_ni9477.components[0]

    assert await relay.switch_multiple_channel("101") is True

    states = await relay.read_channels_set_point()
    assert states[:4] == [1, 0, 1, 0]


async def test_biochem_solenoid_can_use_sim_ni_relay(sim_ni9477):
    solenoid = BioChemSolenoidValve(
        name="valve",
        support_platform="sim-ni/relay",
        channel=1,
        normally_open=False,
    )
    await solenoid.initialize()

    await solenoid.open()
    assert await sim_ni9477.components[0].is_on(channel=1) is True
    assert await solenoid.is_open() is True

    await solenoid.close()
    assert await sim_ni9477.components[0].is_on(channel=1) is False
    assert await solenoid.is_open() is False
