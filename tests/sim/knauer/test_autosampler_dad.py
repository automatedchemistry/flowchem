"""Tests for KnauerAutosamplerSim and KnauerDADSim."""

import pytest

from flowchem.sim.devices.knauer.autosampler_sim import KnauerAutosamplerSim
from flowchem.sim.devices.knauer.dad_sim import KnauerDADSim

# ---------------------------------------------------------------------------
# KnauerAutosampler
# ---------------------------------------------------------------------------


@pytest.fixture
async def autosampler() -> KnauerAutosamplerSim:
    device = KnauerAutosamplerSim.from_config(
        name="test-as",
        autosampler_id=61,
        tray_type="TRAY_48_VIAL",
    )
    await device.initialize()
    return device


@pytest.fixture
def gantry(autosampler):
    return next(c for c in autosampler.components if c.name == "gantry3D")


@pytest.fixture
def as_pump(autosampler):
    return next(c for c in autosampler.components if c.name == "pump")


@pytest.fixture
def syringe_valve(autosampler):
    return next(c for c in autosampler.components if c.name == "syringe_valve")


@pytest.fixture
def injection_valve(autosampler):
    return next(c for c in autosampler.components if c.name == "injection_valve")


class TestKnauerAutosamplerSim:

    async def test_initializes_four_components(self, autosampler):
        assert len(autosampler.components) == 4

    async def test_no_errors_initially(self, autosampler):
        err = await autosampler.get_errors()
        assert err == "No Error."

    async def test_reset_errors(self, autosampler):
        autosampler._sim_errors = "Some error"
        await autosampler.reset_errors()
        assert autosampler._sim_errors == "No Error."

    async def test_get_status(self, autosampler):
        status = await autosampler.get_status()
        assert isinstance(status, str)

    async def test_injection_valve_get_initial(self, autosampler):
        pos = await autosampler.injector_valve_position()
        assert pos == "LOAD"

    async def test_injection_valve_set(self, autosampler):
        pos = await autosampler.injector_valve_position(port="INJECT")
        assert pos == "INJECT"
        assert autosampler._sim_injection_valve == "INJECT"

    async def test_syringe_valve_get_initial(self, autosampler):
        pos = await autosampler.syringe_valve_position()
        assert pos == "WASTE"

    async def test_syringe_valve_set(self, autosampler):
        pos = await autosampler.syringe_valve_position(port="NEEDLE")
        assert pos == "NEEDLE"

    async def test_get_raw_position_injection(self, autosampler):
        result = await autosampler.get_raw_position(target_component="injection_valve")
        assert isinstance(result, str)

    async def test_get_raw_position_syringe(self, autosampler):
        result = await autosampler.get_raw_position(target_component="syringe_valve")
        assert isinstance(result, str)

    async def test_set_raw_position_injection(self, autosampler):
        await autosampler.set_raw_position(
            position="INJECT", target_component="injection_valve"
        )
        assert autosampler._sim_injection_valve == "INJECT"

    async def test_move_needle_vertical(self, autosampler):
        result = await autosampler._move_needle_vertical("DOWN")
        assert result is True
        assert autosampler._sim_needle_v == "DOWN"

    async def test_move_needle_horizontal(self, autosampler):
        result = await autosampler._move_needle_horizontal("WASH")
        assert result is True
        assert autosampler._sim_needle_h == "WASH"

    async def test_move_tray(self, autosampler):
        result = await autosampler._move_tray("TRAY_48_VIAL", 3)
        assert result is True
        assert autosampler._sim_tray == ("TRAY_48_VIAL", 3)

    async def test_aspirate_accumulates(self, autosampler):
        await autosampler.aspirate(0.1)
        await autosampler.aspirate(0.05)
        assert abs(autosampler._sim_aspirated_ul - 150.0) < 0.1

    async def test_dispense_accumulates(self, autosampler):
        await autosampler.dispense(0.2)
        assert abs(autosampler._sim_dispensed_ul - 200.0) < 0.1

    async def test_syringe_volume_get(self, autosampler):
        vol = await autosampler.syringe_volume()
        assert vol == 250

    async def test_syringe_volume_set(self, autosampler):
        await autosampler.syringe_volume(500)
        assert autosampler._syringe_volume == 500

    # --- component API ---

    async def test_gantry_reset_errors(self, gantry):
        result = await gantry.reset_errors()
        assert result is False  # no errors present

    async def test_gantry_set_z_position(self, gantry):
        result = await gantry.set_z_position("DOWN")
        assert result is True

    async def test_gantry_needle_position(self, gantry):
        result = await gantry.set_needle_position("WASH")
        assert result is True

    async def test_pump_infuse(self, as_pump):
        result = await as_pump.infuse(volume="0.1 mL")
        assert result is True

    async def test_pump_withdraw(self, as_pump):
        result = await as_pump.withdraw(volume="0.1 mL")
        assert result is True

    async def test_pump_is_withdrawing_capable(self, as_pump):
        assert as_pump.is_withdrawing_capable() is True

    async def test_injection_valve_component_get(self, injection_valve):
        pos = await injection_valve.get_monitor_position()
        assert isinstance(pos, str)

    async def test_injection_valve_component_set(self, injection_valve):
        await injection_valve.set_monitor_position("INJECT")

    async def test_syringe_valve_component_get(self, syringe_valve):
        pos = await syringe_valve.get_monitor_position()
        assert isinstance(pos, str)

    async def test_syringe_valve_component_set(self, syringe_valve):
        await syringe_valve.set_monitor_position("NEEDLE")


# ---------------------------------------------------------------------------
# KnauerDAD
# ---------------------------------------------------------------------------


@pytest.fixture
async def dad() -> KnauerDADSim:
    device = KnauerDADSim.from_config(name="test-dad")
    await device.initialize()
    return device


@pytest.fixture
def lamp_d2(dad):
    return next(c for c in dad.components if c.name == "d2")


@pytest.fixture
def lamp_hal(dad):
    return next(c for c in dad.components if c.name == "hal")


@pytest.fixture
def channel1(dad):
    return next(c for c in dad.components if c.name == "channel1")


class TestKnauerDADSim:

    async def test_initializes_six_components(self, dad):
        # 2 lamps + 4 channels
        assert len(dad.components) == 6

    async def test_serial_number(self, dad):
        sn = await dad.serial_num()
        assert "SIM" in sn

    async def test_identify(self, dad):
        info = await dad.identify()
        assert "KNAUER" in info

    async def test_status(self, dad):
        status = await dad.status()
        assert isinstance(status, str)

    async def test_get_wavelength_default(self, dad):
        wl = await dad.get_wavelength(1)
        assert wl == 254

    async def test_set_and_get_wavelength(self, dad):
        await dad.set_wavelength(1, 520)
        wl = await dad.get_wavelength(1)
        assert wl == 520

    async def test_read_signal_default(self, dad):
        sig = await dad.read_signal(1)
        assert sig == 0.0

    async def test_set_signal(self, dad):
        dad._sim_signals[1] = 5.5
        sig = await dad.read_signal(1)
        assert abs(sig - 5.5) < 0.01

    async def test_integration_time_get(self, dad):
        t = await dad.integration_time("?")
        assert t == 100

    async def test_integration_time_set(self, dad):
        await dad.integration_time(200)
        assert dad._sim_integ_time == 200

    async def test_bandwidth_get(self, dad):
        bw = await dad.bandwidth("?")
        assert bw == 8

    async def test_bandwidth_set(self, dad):
        await dad.bandwidth(12)
        assert dad._sim_bandwidth == 12

    async def test_lamp_d2_off_initially(self, dad):
        state = await dad.lamp("d2")
        assert state == "0"

    async def test_lamp_d2_on(self, dad):
        await dad.lamp("d2", "ON")
        assert dad._sim_lamps["d2"] == "1"

    async def test_lamp_d2_off(self, dad):
        dad._sim_lamps["d2"] = "1"
        await dad.lamp("d2", "OFF")
        assert dad._sim_lamps["d2"] == "0"

    async def test_lamp_component_power_on(self, lamp_d2, dad):
        await lamp_d2.power_on()
        assert dad._sim_lamps["d2"] == "1"  # verifiable via fixture below

    async def test_lamp_component_get(self, lamp_d2, dad):
        state = await lamp_d2.get_lamp()
        assert isinstance(state, str)

    async def test_channel_set_wavelength(self, channel1):
        await channel1.set_wavelength(480)

    async def test_channel_acquire_signal(self, channel1):
        sig = await channel1.acquire_signal()
        assert isinstance(sig, float)

    async def test_channel_set_integration_time(self, channel1):
        await channel1.set_integration_time(150)

    async def test_channel_set_bandwidth(self, channel1):
        await channel1.set_bandwidth(16)

    async def test_all_four_channels_reachable(self, dad):
        channels = [c for c in dad.components if c.name.startswith("channel")]
        assert len(channels) == 4
        for ch in channels:
            sig = await ch.acquire_signal()
            assert isinstance(sig, float)
