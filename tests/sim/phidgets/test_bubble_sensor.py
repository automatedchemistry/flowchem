"""Tests for PhidgetBubbleSensorSim and PhidgetPowerSource5VSim."""

import pytest

from flowchem.sim.devices.phidgets.bubble_sim import (
    PhidgetBubbleSensorSim,
    PhidgetPowerSource5VSim,
)

# ---------------------------------------------------------------------------
# PhidgetPowerSource5V
# ---------------------------------------------------------------------------


@pytest.fixture
async def power5v() -> PhidgetPowerSource5VSim:
    device = PhidgetPowerSource5VSim.from_config(name="test-5v")
    await device.initialize()
    return device


@pytest.fixture
def power_component(power5v):
    return power5v.components[0]


class TestPhidgetPowerSource5VSim:

    async def test_initializes_one_component(self, power5v):
        assert len(power5v.components) == 1

    async def test_is_attached(self, power5v):
        assert power5v.is_attached() is True

    async def test_initially_off(self, power5v):
        assert power5v.is_poweron() is False

    async def test_power_on(self, power5v):
        power5v.power_on()
        assert power5v.is_poweron() is True

    async def test_power_off(self, power5v):
        power5v.power_on()
        power5v.power_off()
        assert power5v.is_poweron() is False

    async def test_component_power_on(self, power_component, power5v):
        await power_component.power_on()
        assert power5v.is_poweron() is True

    async def test_component_power_off(self, power_component, power5v):
        await power_component.power_on()
        await power_component.power_off()
        assert power5v.is_poweron() is False

    async def test_manufacturer(self, power5v):
        assert power5v.device_info.manufacturer == "Phidget"


# ---------------------------------------------------------------------------
# PhidgetBubbleSensor
# ---------------------------------------------------------------------------


@pytest.fixture
async def bubble() -> PhidgetBubbleSensorSim:
    device = PhidgetBubbleSensorSim.from_config(name="test-bubble", data_interval=100)
    await device.initialize()
    return device


@pytest.fixture
def bubble_component(bubble):
    return bubble.components[0]


class TestPhidgetBubbleSensorSim:

    async def test_initializes_one_component(self, bubble):
        assert len(bubble.components) == 1

    async def test_is_attached(self, bubble):
        assert bubble.is_attached() is True

    async def test_read_voltage_default(self, bubble):
        assert bubble.read_voltage() == 0.0

    async def test_set_sim_voltage_and_read(self, bubble):
        bubble._sim_voltage = 2.5
        assert bubble.read_voltage() == 2.5

    async def test_intensity_conversion(self, bubble):
        bubble._sim_voltage = 2.5
        intensity = bubble.read_intensity()
        assert abs(intensity - 50.0) < 0.01  # 2.5 V * 20 = 50 %

    async def test_voltage_to_intensity_zero(self, bubble):
        assert bubble._voltage_to_intensity(0.0) == 0.0

    async def test_voltage_to_intensity_max(self, bubble):
        assert abs(bubble._voltage_to_intensity(5.0) - 100.0) < 0.01

    async def test_power_on(self, bubble):
        bubble.power_on()
        assert bubble._sim_power is True

    async def test_power_off(self, bubble):
        bubble.power_on()
        bubble.power_off()
        assert bubble._sim_power is False

    async def test_get_data_interval(self, bubble):
        assert bubble.get_dataInterval() == 100

    async def test_set_data_interval(self, bubble):
        bubble.set_dataInterval(500)
        assert bubble.get_dataInterval() == 500

    async def test_component_power_on(self, bubble_component, bubble):
        await bubble_component.power_on()
        assert bubble._sim_power is True

    async def test_component_power_off(self, bubble_component, bubble):
        await bubble_component.power_on()
        await bubble_component.power_off()
        assert bubble._sim_power is False

    async def test_component_read_voltage(self, bubble_component, bubble):
        bubble._sim_voltage = 1.0
        v = await bubble_component.read_voltage()
        assert abs(v - 1.0) < 0.001

    async def test_component_acquire_signal(self, bubble_component, bubble):
        bubble._sim_voltage = 1.0
        sig = await bubble_component.acquire_signal()
        assert abs(sig - 20.0) < 0.01  # 1.0 V * 20 = 20 %

    async def test_manufacturer(self, bubble):
        assert bubble.device_info.manufacturer == "Phidget"
