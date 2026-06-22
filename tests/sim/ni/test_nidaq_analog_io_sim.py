from __future__ import annotations

import pytest

from flowchem.sim.devices.ni.nidaq_analog_io_sim import NIDAQAnalogIOSim


@pytest.fixture
async def sim_analog_io() -> NIDAQAnalogIOSim:
    device = NIDAQAnalogIOSim.from_config(name="sim-analog")
    await device.initialize()
    return device


async def test_sim_initializes_adc_and_dac(sim_analog_io):
    assert [component.name for component in sim_analog_io.components] == ["adc", "dac"]


async def test_sim_adc_and_dac(sim_analog_io):
    adc = sim_analog_io.components[0]
    dac = sim_analog_io.components[1]

    sim_analog_io.sim_adc_task.values[0] = 1.5
    assert await adc.read(channel="1") == 1.5
    assert await dac.set(channel="1", value="3 V") is True
    assert await dac.read(channel="1") == 3.0
