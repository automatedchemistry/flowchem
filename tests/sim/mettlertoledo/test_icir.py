"""Tests for IcIRSim."""

import pytest
from flowchem.sim.devices.mettlertoledo.icir_sim import IcIRSim


@pytest.fixture
async def icir() -> IcIRSim:
    device = IcIRSim.from_config(name="test-icir")
    await device.initialize()
    return device


@pytest.fixture
async def icir_control(icir):
    return icir.components[0]


class TestIcIRSim:

    async def test_initializes_one_component(self, icir):
        assert len(icir.components) == 1

    async def test_is_idle_returns_true_before_experiment(self, icir_control):
        assert await icir_control.is_idle() is True

    async def test_is_idle_returns_true_even_after_start_experiment(self, icir_control):
        await icir_control.hw_device.start_experiment()
        assert await icir_control.is_idle() is True
