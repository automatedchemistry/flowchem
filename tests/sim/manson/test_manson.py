"""Tests for MansonPowerSupplySim."""

import pytest
from flowchem.sim.devices.manson.manson_sim import MansonPowerSupplySim


@pytest.fixture
async def manson() -> MansonPowerSupplySim:
    device = MansonPowerSupplySim.from_config(port="SIM", name="test-manson")
    await device.initialize()
    return device


@pytest.fixture
async def power_ctrl(manson):
    return manson.components[0]


class TestMansonPowerSupplySim:

    async def test_initializes_one_component(self, manson):
        assert len(manson.components) == 1

    async def test_model_populated(self, manson):
        assert "HCS" in manson.device_info.model

    async def test_get_info_returns_model(self, manson):
        model = await manson.get_info()
        assert "HCS-3102" in model

    async def test_output_on(self, manson):
        result = await manson.output_on()
        assert result is True
        assert manson._sim_on is True

    async def test_output_off(self, manson):
        await manson.output_on()
        result = await manson.output_off()
        assert result is True
        assert manson._sim_on is False

    async def test_set_voltage(self, manson):
        result = await manson.set_voltage("12 V")
        assert result is True
        assert abs(manson._sim_voltage - 12.0) < 0.1

    async def test_set_current(self, manson):
        result = await manson.set_current("2 A")
        assert result is True
        assert abs(manson._sim_current - 2.0) < 0.1

    async def test_get_output_voltage(self, manson):
        await manson.set_voltage("5 V")
        v = await manson.get_output_voltage()
        assert abs(v - 5.0) < 0.1

    async def test_get_output_current(self, manson):
        await manson.set_current("1 A")
        c = await manson.get_output_current()
        assert abs(c - 1.0) < 0.1

    async def test_get_output_mode(self, manson):
        mode = await manson.get_output_mode()
        assert mode in ("CC", "CV", "NN")

    async def test_get_max_returns_tuple(self, manson):
        max_v, max_c = await manson.get_max()
        assert "V" in max_v
        assert "A" in max_c

    async def test_get_setting_returns_tuple(self, manson):
        v_str, c_str = await manson.get_setting()
        assert len(v_str) > 0

    async def test_get_all_preset(self, manson):
        presets = await manson.get_all_preset()
        assert len(presets) == 3

    async def test_component_get_voltage(self, power_ctrl):
        v = await power_ctrl.get_voltage()
        assert isinstance(v, float)

    async def test_component_get_current(self, power_ctrl):
        c = await power_ctrl.get_current()
        assert isinstance(c, float)

    async def test_component_set_voltage(self, power_ctrl):
        await power_ctrl.set_voltage("10 V")
        assert abs(power_ctrl.hw_device._sim_voltage - 10.0) < 0.1

    async def test_component_power_on(self, power_ctrl):
        await power_ctrl.power_on()
        assert power_ctrl.hw_device._sim_on is True

    async def test_component_power_off(self, power_ctrl):
        await power_ctrl.power_on()
        await power_ctrl.power_off()
        assert power_ctrl.hw_device._sim_on is False
