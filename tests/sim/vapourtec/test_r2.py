"""Tests for R2Sim."""

import pytest
from flowchem.sim.devices.vapourtec.r2_sim import R2Sim


@pytest.fixture
async def r2() -> R2Sim:
    device = R2Sim.from_config(name="test-r2")
    await device.initialize()
    return device


@pytest.fixture
async def reactor(r2):
    return next(c for c in r2.components if c.name == "reactor-1")


class TestR2Sim:

    async def test_is_idle_before_set_temperature(self, reactor):
        assert await reactor.is_idle() is True

    async def test_is_idle_after_set_temperature(self, reactor):
        await reactor.set_temperature("50 degC")
        assert await reactor.is_idle() is True
