"""Tests for HuberChillerSim."""

import pytest
from flowchem.sim.devices.huber.huber_sim import HuberChillerSim


@pytest.fixture
async def chiller() -> HuberChillerSim:
    device = HuberChillerSim.from_config(port="SIM", name="test-huber")
    await device.initialize()
    return device


@pytest.fixture
async def temp_ctrl(chiller):
    return chiller.components[0]


class TestHuberChillerSim:

    async def test_initializes_one_component(self, chiller):
        assert len(chiller.components) == 1

    async def test_serial_number_populated(self, chiller):
        assert chiller.device_info.serial_number != ""

    async def test_get_temperature_initial(self, chiller):
        temp = await chiller.get_temperature()
        assert abs(temp - 25.0) < 0.1

    async def test_set_temperature_updates_state(self, chiller):
        from flowchem import ureg

        await chiller.set_temperature(ureg.Quantity("10 °C"))
        temp = await chiller.get_temperature()
        assert abs(temp - 10.0) < 0.1

    async def test_set_temperature_negative(self, chiller):
        from flowchem import ureg

        await chiller.set_temperature(ureg.Quantity("-20 °C"))
        temp = await chiller.get_temperature()
        assert abs(temp - (-20.0)) < 0.1

    async def test_temperature_setpoint_readable(self, chiller):
        from flowchem import ureg

        await chiller.set_temperature(ureg.Quantity("30 °C"))
        sp = await chiller.get_temperature_setpoint()
        assert abs(sp - 30.0) < 0.1

    async def test_target_reached_after_set(self, chiller):
        from flowchem import ureg

        await chiller.set_temperature(ureg.Quantity("25 °C"))
        reached = await chiller.target_reached()
        assert reached is True

    async def test_temperature_limits_returned(self, chiller):
        t_min, t_max = await chiller.temperature_limits()
        assert t_min < t_max

    async def test_temperature_limits_match_config(self, chiller):
        t_min, t_max = await chiller.temperature_limits()
        assert t_min == -40.0
        assert t_max == 150.0

    async def test_component_get_temperature(self, temp_ctrl):
        temp = await temp_ctrl.get_temperature()
        assert isinstance(temp, float)

    async def test_component_set_temperature(self, temp_ctrl):
        result = await temp_ctrl.set_temperature("15 degC")
        from flowchem import ureg

        assert result == ureg.Quantity("15 degC")

    async def test_component_is_target_reached(self, temp_ctrl):
        await temp_ctrl.set_temperature("25 degC")
        reached = await temp_ctrl.is_target_reached()
        assert isinstance(reached, bool)

    async def test_component_power_on_off(self, temp_ctrl):
        await temp_ctrl.power_on()
        await temp_ctrl.power_off()  # no error expected

    async def test_custom_min_max_temp(self):
        device = HuberChillerSim.from_config(
            port="SIM", name="cold-huber", min_temp=-80.0, max_temp=80.0
        )
        await device.initialize()
        t_min, t_max = await device.temperature_limits()
        assert t_min == -80.0
        assert t_max == 80.0
