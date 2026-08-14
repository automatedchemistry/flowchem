"""Tests for EBPRSim."""

import pytest

from flowchem.devices.vapourtec.ebpr import EBPR
from flowchem.sim.devices.vapourtec.ebpr_sim import EBPRSim


@pytest.fixture
async def ebpr() -> EBPRSim:
    device = EBPRSim.from_config(name="test-ebpr")
    await device.initialize()
    return device


@pytest.fixture
async def pressure_ctrl(ebpr):
    return ebpr.components[0]


class TestEBPRSim:
    async def test_initializes_one_component(self, ebpr):
        assert len(ebpr.components) == 1

    async def test_version_populated(self, ebpr):
        assert "SIM" in ebpr.device_info.version

    async def test_version_method(self, ebpr):
        assert "SIM" in await ebpr.version()

    async def test_get_pressure_initial(self, ebpr):
        assert await ebpr.get_pressure() == 0.0

    async def test_set_pressure_updates_setpoint(self, ebpr):
        await ebpr.set_pressure(500.0)
        assert abs(ebpr._sim_setpoint_mbar - 500.0) < 0.1

    async def test_set_pressure_converges_measured_instantly(self, ebpr):
        await ebpr.set_pressure(500.0)
        assert abs(await ebpr.get_pressure() - 0.5) < 0.01

    async def test_status_returns_real_namedtuple_type(self, ebpr):
        status = await ebpr.get_status()
        assert isinstance(status, EBPR.Status)

    async def test_power_on_off(self, ebpr):
        await ebpr.power_on()
        assert (await ebpr.get_status()).control_on is True
        await ebpr.power_off()
        assert (await ebpr.get_status()).control_on is False

    # --- component API via the real, unmodified EBPRPressureControl ---

    async def test_component_set_pressure(self, pressure_ctrl):
        await pressure_ctrl.set_pressure("300 mbar")
        assert abs(pressure_ctrl.hw_device._sim_setpoint_mbar - 300.0) < 0.1

    async def test_component_set_pressure_default_unit_mbar(self, pressure_ctrl):
        await pressure_ctrl.set_pressure("250")
        assert abs(pressure_ctrl.hw_device._sim_setpoint_mbar - 250.0) < 0.1

    async def test_component_get_pressure(self, pressure_ctrl):
        assert isinstance(await pressure_ctrl.get_pressure(), float)

    async def test_component_is_target_reached_after_set(self, pressure_ctrl):
        await pressure_ctrl.set_pressure("400 mbar")
        assert await pressure_ctrl.is_target_reached() is True

    async def test_component_power_on_off(self, pressure_ctrl):
        await pressure_ctrl.power_on()
        await pressure_ctrl.power_off()
