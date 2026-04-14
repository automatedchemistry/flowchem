"""Tests for CVC3000Sim."""

import pytest
from flowchem.sim.devices.vacuubrand.cvc3000_sim import CVC3000Sim
from flowchem import ureg


@pytest.fixture
async def cvc3000() -> CVC3000Sim:
    device = CVC3000Sim.from_config(port="SIM", name="test-cvc")
    await device.initialize()
    return device


@pytest.fixture
async def pressure_ctrl(cvc3000):
    return cvc3000.components[0]


class TestCVC3000Sim:

    async def test_initializes_one_component(self, cvc3000):
        assert len(cvc3000.components) == 1

    async def test_version_populated(self, cvc3000):
        assert "CVC" in cvc3000.device_info.version

    async def test_get_pressure_initial(self, cvc3000):
        p = await cvc3000.get_pressure()
        assert p > 0

    async def test_set_pressure_updates_setpoint(self, cvc3000):
        await cvc3000.set_pressure(ureg.Quantity("200 mbar"))
        assert abs(cvc3000._sim_setpoint - 200.0) < 0.1

    async def test_set_motor_speed(self, cvc3000):
        await cvc3000.motor_speed(80)
        assert cvc3000._sim_speed == 80

    async def test_status_returns_model(self, cvc3000):
        from flowchem.devices.vacuubrand.constants import ProcessStatus

        status = await cvc3000.status()
        assert isinstance(status, ProcessStatus)

    async def test_status_pump_on(self, cvc3000):
        status = await cvc3000.status()
        assert status.is_pump_on is True

    async def test_component_set_pressure(self, pressure_ctrl):
        await pressure_ctrl.set_pressure("300 mbar")
        assert abs(pressure_ctrl.hw_device._sim_setpoint - 300.0) < 0.1

    async def test_component_get_pressure(self, pressure_ctrl):
        p = await pressure_ctrl.get_pressure()
        assert isinstance(p, float)

    async def test_component_power_on_off(self, pressure_ctrl):
        await pressure_ctrl.power_on()
        await pressure_ctrl.power_off()

    async def test_version_method(self, cvc3000):
        ver = await cvc3000.version()
        assert "CVC" in ver
