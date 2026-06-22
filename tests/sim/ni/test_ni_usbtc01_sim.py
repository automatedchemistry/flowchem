from __future__ import annotations

import pytest

from flowchem.sim.devices.ni.ni_usbtc01_sim import NIUSBTC01Sim


@pytest.fixture
async def sim_tc01() -> NIUSBTC01Sim:
    device = NIUSBTC01Sim.from_config(name="sim-ni-tc01")
    await device.initialize()
    return device


async def test_sim_initializes_temperature_component(sim_tc01):
    assert [c.name for c in sim_tc01.components] == ["temperature"]


async def test_sim_reads_default_temperature(sim_tc01):
    temp = await sim_tc01.read_temperature()
    assert temp == 25.0


async def test_sim_temperature_can_be_set(sim_tc01):
    sim_tc01.sim_task.temperature = 42.5
    temp = await sim_tc01.read_temperature()
    assert temp == 42.5


async def test_sim_component_endpoint(sim_tc01):
    sensor = sim_tc01.components[0]
    sim_tc01.sim_task.temperature = 100.0
    assert await sensor.get_temperature() == 100.0
