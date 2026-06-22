"""Tests for HeiConnectSim."""

import pytest
from flowchem.sim.devices.heidolph.hei_connect_sim import HeiConnectSim


@pytest.fixture
async def device() -> HeiConnectSim:
    dev = HeiConnectSim.from_config(port="COM_SIM", name="test-heidolph")
    await dev.initialize()
    return dev


@pytest.fixture
async def stirring(device):
    return device.components[0]  # HeiConnectStirringControl


@pytest.fixture
async def temp_ctrl(device):
    return device.components[1]  # HeiConnectTemperatureControl


@pytest.fixture
async def ctrl(device):
    return device.components[2]  # HeiConnectControl


class TestHeiConnectSim:

    async def test_initializes_three_components(self, device):
        assert len(device.components) == 3

    # Temperature control

    async def test_initial_temperature(self, temp_ctrl):
        temp = await temp_ctrl.get_temperature()
        assert abs(temp - 25.0) < 0.1

    async def test_set_temperature_updates_setpoint(self, temp_ctrl):
        await temp_ctrl.set_temperature("80 degC")
        sp = await temp_ctrl.get_temperature_setpoint()
        assert abs(sp - 80.0) < 0.1

    async def test_target_reached_after_power_on(self, temp_ctrl):
        await temp_ctrl.set_temperature("100 degC")
        await temp_ctrl.power_on()
        assert await temp_ctrl.is_target_reached()

    async def test_power_on_off_heating(self, temp_ctrl):
        await temp_ctrl.power_on()
        await temp_ctrl.power_off()

    async def test_heating_mode_default_fast(self, temp_ctrl):
        assert await temp_ctrl.get_heating_mode() == "fast"

    async def test_set_heating_mode_precise(self, temp_ctrl):
        await temp_ctrl.set_heating_mode("precise")
        assert await temp_ctrl.get_heating_mode() == "precise"

    async def test_temperature_control_mode_default_hotplate(self, temp_ctrl):
        assert await temp_ctrl.get_temperature_control_mode() == "hotplate"

    # Stirring control

    async def test_initial_speed_is_zero(self, stirring):
        assert await stirring.get_speed() == 0.0

    async def test_set_speed_updates_setpoint(self, stirring):
        await stirring.set_speed("200 rpm")
        assert abs(await stirring.get_speed_setpoint() - 200.0) < 1.0

    async def test_power_on_starts_stirring(self, stirring):
        await stirring.power_on()
        assert await stirring.is_on()

    async def test_power_off_stops_stirring(self, stirring):
        await stirring.power_on()
        await stirring.power_off()
        assert not await stirring.is_on()

    # Device control / status

    async def test_status_idle_is_remote_stop(self, ctrl):
        assert await ctrl.status() == "remote-stop"

    async def test_status_active_is_remote_start(self, device, ctrl):
        await device.components[0].power_on()
        assert await ctrl.status() == "remote-start"

    async def test_software_version_nonempty(self, ctrl):
        version = await ctrl.software_version()
        assert isinstance(version, str) and version
