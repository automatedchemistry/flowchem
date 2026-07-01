"""Tests for FlameOpticalSim."""

import pytest

from flowchem.sim.devices.oceanoptics.flame_sim import FlameOpticalSim


@pytest.fixture
async def flame() -> FlameOpticalSim:
    device = FlameOpticalSim.from_config(name="test-flame", serial_number="SIM-001")
    await device.initialize()
    return device


@pytest.fixture
def sensor(flame):
    return flame.components[0]


class TestFlameOpticalSim:

    async def test_initializes_one_component(self, flame):
        assert len(flame.components) == 1

    async def test_manufacturer(self, flame):
        assert flame.device_info.manufacturer == "oceanoptics"

    async def test_serial_number_from_config(self, flame):
        assert flame.device_info.serial_number == "SIM-001"

    async def test_get_wavelength_length(self, flame):
        wavelengths = await flame.get_wavelength()
        assert len(wavelengths) == flame.pixels

    async def test_get_intensity_normalized_range(self, flame):
        intensities = await flame.get_intensity(absolute=False)
        assert len(intensities) == flame.pixels
        assert all(0.0 <= value <= 1.0 for value in intensities)

    async def test_get_intensity_absolute_scale(self, flame):
        absolute = await flame.get_intensity(absolute=True)
        normalized = await flame.get_intensity(absolute=False)
        assert absolute[0] == pytest.approx(normalized[0] * flame.max_intensity)

    async def test_default_scans_to_average(self, flame):
        assert await flame.get_scans_to_average() == 1

    async def test_set_scans_to_average(self, flame):
        await flame.set_scans_to_average(4)
        assert await flame.get_scans_to_average() == 4

    async def test_set_scans_to_average_rejects_zero(self, flame):
        with pytest.raises(ValueError):
            await flame.set_scans_to_average(0)

    async def test_default_trigger_mode(self, flame):
        assert await flame.get_trigger_mode() is None

    async def test_set_trigger_mode(self, flame):
        await flame.set_trigger_mode(1)
        assert await flame.get_trigger_mode() == 1

    async def test_integration_time_clamped_to_limits(self, flame):
        low, high = flame.integration_time_micros_limits
        await flame.integration_time(low - 1000)
        assert flame._sim_integration_time_us == low
        await flame.integration_time(high + 1000)
        assert flame._sim_integration_time_us == high

    async def test_power_on_off(self, flame):
        await flame.power_on()
        assert flame._sim_powered is True
        await flame.power_off()
        assert flame._sim_powered is False

    async def test_component_get_wavelength(self, sensor, flame):
        wavelengths = await sensor.get_wavelength()
        assert len(wavelengths) == flame.pixels

    async def test_component_acquire_signal(self, sensor, flame):
        # GeneralSensor.acquire_signal defaults to absolute=True.
        signal = await sensor.acquire_signal()
        assert all(0.0 <= value <= flame.max_intensity for value in signal)

    async def test_component_set_scans_to_average(self, sensor, flame):
        await sensor.set_scans_to_average(3)
        assert await flame.get_scans_to_average() == 3

    async def test_component_set_trigger_mode(self, sensor, flame):
        await sensor.set_trigger_mode(2)
        assert await flame.get_trigger_mode() == 2

    async def test_component_power_on_off(self, sensor, flame):
        await sensor.power_on()
        assert flame._sim_powered is True
        await sensor.power_off()
        assert flame._sim_powered is False
