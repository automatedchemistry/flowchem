"""Tests for R4HeaterSim."""

import pytest

from flowchem.sim.devices.vapourtec.r4_sim import R4HeaterSim
from flowchem.devices.vapourtec.r4_heater import R4Heater
from flowchem import ureg


@pytest.fixture
async def r4() -> R4HeaterSim:
    device = R4HeaterSim.from_config(name="test-r4")
    await device.initialize()
    return device


@pytest.fixture
def reactor1(r4):
    return next(c for c in r4.components if c.name == "reactor1")


@pytest.fixture
def reactor2(r4):
    return next(c for c in r4.components if c.name == "reactor2")


class TestR4HeaterSim:

    async def test_initializes_four_components(self, r4):
        assert len(r4.components) == 4

    async def test_component_names(self, r4):
        names = {c.name for c in r4.components}
        assert names == {"reactor1", "reactor2", "reactor3", "reactor4"}

    async def test_version(self, r4):
        ver = await r4.version()
        assert "SIM" in ver

    async def test_default_temperature(self, r4):
        t = await r4.get_temperature(0)
        assert abs(float(t) - 25.0) < 0.1

    async def test_set_temperature_channel_0(self, r4):
        await r4.set_temperature(0, ureg.Quantity("50 °C"))
        t = await r4.get_temperature(0)
        assert abs(float(t) - 50.0) < 0.1

    async def test_set_temperature_channel_3(self, r4):
        await r4.set_temperature(3, ureg.Quantity("-10 °C"))
        t = await r4.get_temperature(3)
        assert abs(float(t) - (-10.0)) < 0.1

    async def test_set_temperature_enables_channel(self, r4):
        await r4.set_temperature(1, ureg.Quantity("30 °C"))
        assert r4._sim_enabled[1] is True

    async def test_power_on(self, r4):
        await r4.power_on(2)
        assert r4._sim_enabled[2] is True

    async def test_power_off(self, r4):
        await r4.power_on(0)
        await r4.power_off(0)
        assert r4._sim_enabled[0] is False

    async def test_get_status_returns_namedtuple(self, r4):
        status = await r4.get_status(0)
        assert isinstance(status, R4Heater.ChannelStatus)

    async def test_get_status_state_is_stable(self, r4):
        status = await r4.get_status(0)
        assert status.state == "S"

    async def test_get_status_temperature_matches_sim(self, r4):
        await r4.set_temperature(0, ureg.Quantity("40 °C"))
        status = await r4.get_status(0)
        assert abs(float(status.temperature) - 40.0) < 0.1

    async def test_all_channels_independent(self, r4):
        await r4.set_temperature(0, ureg.Quantity("10 °C"))
        await r4.set_temperature(1, ureg.Quantity("20 °C"))
        await r4.set_temperature(2, ureg.Quantity("30 °C"))
        await r4.set_temperature(3, ureg.Quantity("40 °C"))
        assert abs(float(await r4.get_temperature(0)) - 10.0) < 0.1
        assert abs(float(await r4.get_temperature(1)) - 20.0) < 0.1
        assert abs(float(await r4.get_temperature(2)) - 30.0) < 0.1
        assert abs(float(await r4.get_temperature(3)) - 40.0) < 0.1

    # --- component API via R4HeaterChannelControl ---

    async def test_component_set_temperature(self, reactor1):
        await reactor1.set_temperature("60 °C")
        t = await reactor1.get_temperature()
        assert abs(float(t) - 60.0) < 0.1

    async def test_component_get_temperature(self, reactor1):
        t = await reactor1.get_temperature()
        assert isinstance(float(t), float)

    async def test_component_is_target_reached(self, reactor1):
        # Sim always returns state="S" (stable)
        reached = await reactor1.is_target_reached()
        assert reached is True

    async def test_component_power_on(self, reactor1, r4):
        await reactor1.power_on()
        assert r4._sim_enabled[0] is True

    async def test_component_power_off(self, reactor1, r4):
        await reactor1.power_on()
        await reactor1.power_off()
        assert r4._sim_enabled[0] is False

    async def test_reactor2_independent_of_reactor1(self, reactor1, reactor2, r4):
        await reactor1.set_temperature("70 °C")
        await reactor2.set_temperature("80 °C")
        assert abs(float(r4._sim_temps[0]) - 70.0) < 0.1
        assert abs(float(r4._sim_temps[1]) - 80.0) < 0.1

    async def test_custom_temp_limits(self):
        device = R4HeaterSim.from_config(name="hot-r4", min_temp=0.0, max_temp=300.0)
        await device.initialize()
        assert device._min_t == [0.0] * 4
        assert device._max_t == [300.0] * 4
