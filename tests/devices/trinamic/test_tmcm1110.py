from __future__ import annotations

import pytest

from flowchem.devices.trinamic.tmcl import TMCLCommandNumber, TMCLRequest
from flowchem.devices.trinamic.tmcm1110 import (
    pps_to_tmc429_velocity,
    tmc429_velocity_to_pps,
)
from flowchem.devices.trinamic.tmcm_base import AxisParameter
from flowchem.sim.devices.trinamic.tmcm1110_sim import (
    SimulatedTMCM1110IO,
    TMCM1110Sim,
)
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError


def test_tmcl_request_encoding_matches_manual_sap_example():
    """SAP 4, 0, 1000 (set max. positioning speed to 1000 [int]) from the manual."""
    request = TMCLRequest(
        address=1,
        command=int(TMCLCommandNumber.SAP),
        command_type=4,
        motor=0,
        value=1000,
    )

    assert request.to_bytes() == bytes.fromhex("01 05 04 00 00 00 03 e8 f5")


def test_pps_to_tmc429_velocity_matches_manual_worked_example():
    # Manual example (inverse direction): v_int=1678, pulse_divisor=3 -> ~51208.5pps.
    assert tmc429_velocity_to_pps(1678, pulse_divisor=3) == pytest.approx(51208.5, abs=0.5)
    # Round-tripping that same pps value back should recover the same v_int.
    assert pps_to_tmc429_velocity(51208, pulse_divisor=3) == 1678


def test_pps_to_tmc429_velocity_rejects_out_of_range_result():
    with pytest.raises(ValueError, match="does not fit the TMC429 velocity range"):
        pps_to_tmc429_velocity(10_000_000, pulse_divisor=0)


def test_requires_positions():
    with pytest.raises(InvalidConfigurationError, match="at least one named position"):
        TMCM1110Sim.from_config(positions={})


async def test_sim_initializes_fraction_collector_component():
    device = TMCM1110Sim.from_config(
        name="collector",
        positions={"waste": 0, "vial_1": 12000},
    )
    await device.initialize()

    assert len(device.components) == 1
    assert device.components[0].name == "fraction-collector"


async def test_named_position_move_and_position_readback():
    device = TMCM1110Sim.from_config(positions={"waste": 0, "vial_1": 12000})
    await device.initialize()
    collector = device.components[0]

    assert await collector.set_position("vial_1") is True
    assert await collector.get_position() == "vial_1"
    assert await collector.target_reached() is True


async def test_raw_position_move_returns_raw_when_not_named():
    device = TMCM1110Sim.from_config(positions={"waste": 0, "vial_1": 12000})
    await device.initialize()
    collector = device.components[0]

    assert await collector.set_position("42") is True
    assert await collector.get_position() == 42


async def test_home_converts_pps_to_tmc429_internal_units():
    # The sim's pulse divisor (axis parameter #154) defaults to 0 (never
    # explicitly SAP'd), so the expected internal-unit value below is
    # computed with pulse_divisor=0 to match.
    device = TMCM1110Sim.from_config(
        positions={"waste": 0, "vial_1": 12000},
        home_position="waste",
        reference_search_mode=1,
        reference_search_speed=2000,
        reference_switch_speed=200,
    )
    await device.initialize()

    assert await device.home() is True
    assert device.sim_io.axis_parameters[int(AxisParameter.REFERENCE_SEARCH_MODE)] == 1
    assert device.sim_io.axis_parameters[
        int(AxisParameter.REFERENCE_SEARCH_SPEED)
    ] == pps_to_tmc429_velocity(2000, pulse_divisor=0)
    assert device.sim_io.axis_parameters[
        int(AxisParameter.REFERENCE_SWITCH_SPEED)
    ] == pps_to_tmc429_velocity(200, pulse_divisor=0)
    assert await device.get_position() == "waste"


async def test_limit_states_are_exposed():
    sim_io = SimulatedTMCM1110IO()
    sim_io.axis_parameters[int(AxisParameter.LEFT_LIMIT_SWITCH_STATE)] = 1
    device = TMCM1110Sim.from_config(positions={"waste": 0})
    device.tmcm_io = sim_io
    await device.initialize()

    assert await device.components[0].limits() == {
        "home": False,
        "right": False,
        "left": True,
    }


async def test_initialize_raises_on_confirmed_model_mismatch():
    """A TMCM1110 configured but wired to a board reporting a 1111 firmware string."""
    device = TMCM1110Sim.from_config(positions={"waste": 0}, name="collector")

    async def wrong_model_reply(request, read_length):
        return b"1111V113"

    device.tmcm_io.request_raw = wrong_model_reply

    with pytest.raises(DeviceError, match="TMCM-1111"):
        await device.initialize()
