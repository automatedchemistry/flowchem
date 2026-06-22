from __future__ import annotations

import pytest

from flowchem.devices.trinamic.tmcm1111 import (
    AxisParameter,
    TMCLCommandNumber,
    TMCLRequest,
    decode_tmcl_reply,
)
from flowchem.sim.devices.trinamic.tmcm1111_sim import SimulatedTMCM1111IO, TMCM1111Sim
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError


def test_tmcl_request_encoding_matches_manual_rfs_start_example():
    request = TMCLRequest(
        address=1,
        command=int(TMCLCommandNumber.RFS),
        command_type=0,
        motor=0,
        value=0,
    )

    assert request.to_bytes() == bytes.fromhex("01 0d 00 00 00 00 00 00 0e")


def test_decode_reply_validates_checksum():
    bad_frame = bytes.fromhex("02 01 64 06 00 00 00 01 00")

    with pytest.raises(DeviceError, match="checksum"):
        decode_tmcl_reply(bad_frame, expected_command=int(TMCLCommandNumber.GAP))


def test_decode_reply_rejects_error_status():
    frame_without_checksum = bytes.fromhex("02 01 02 06 00 00 00 00")
    frame = frame_without_checksum + bytes([sum(frame_without_checksum) & 0xFF])

    with pytest.raises(DeviceError, match="Invalid command"):
        decode_tmcl_reply(frame, expected_command=int(TMCLCommandNumber.GAP))


def test_requires_positions():
    with pytest.raises(InvalidConfigurationError, match="at least one named position"):
        TMCM1111Sim.from_config(positions={})


async def test_sim_initializes_fraction_collector_component():
    device = TMCM1111Sim.from_config(
        name="collector",
        positions={"waste": 0, "vial_1": 12000},
    )
    await device.initialize()

    assert len(device.components) == 1
    assert device.components[0].name == "fraction-collector"


async def test_named_position_move_and_position_readback():
    device = TMCM1111Sim.from_config(positions={"waste": 0, "vial_1": 12000})
    await device.initialize()
    collector = device.components[0]

    assert await collector.set_position("vial_1") is True
    assert await collector.get_position() == "vial_1"
    assert await collector.target_reached() is True


async def test_raw_position_move_returns_raw_when_not_named():
    device = TMCM1111Sim.from_config(positions={"waste": 0, "vial_1": 12000})
    await device.initialize()
    collector = device.components[0]

    assert await collector.set_position("42") is True
    assert await collector.get_position() == 42


async def test_home_applies_home_position_and_reference_settings():
    device = TMCM1111Sim.from_config(
        positions={"waste": 0, "vial_1": 12000},
        home_position="waste",
        reference_search_mode=1,
        reference_search_speed=51200,
        reference_switch_speed=4096,
    )
    await device.initialize()

    assert await device.home() is True
    assert device.sim_io.axis_parameters[int(AxisParameter.REFERENCE_SEARCH_MODE)] == 1
    assert (
        device.sim_io.axis_parameters[int(AxisParameter.REFERENCE_SEARCH_SPEED)]
        == 51200
    )
    assert (
        device.sim_io.axis_parameters[int(AxisParameter.REFERENCE_SWITCH_SPEED)] == 4096
    )
    assert await device.get_position() == "waste"


async def test_limit_states_are_exposed():
    sim_io = SimulatedTMCM1111IO()
    sim_io.axis_parameters[int(AxisParameter.LEFT_LIMIT_SWITCH_STATE)] = 1
    device = TMCM1111Sim.from_config(positions={"waste": 0})
    device.tmcm_io = sim_io
    await device.initialize()

    assert await device.components[0].limits() == {
        "home": False,
        "right": False,
        "left": True,
    }
