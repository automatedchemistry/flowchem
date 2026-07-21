from __future__ import annotations

import pytest

from flowchem.devices.trinamic.tmcm1111 import (
    TMCM1111,
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


async def test_reverse_shaft_not_touched_when_unconfigured():
    """Default (reverse_shaft=None) must not write axis parameter #251.

    Some 1111 units rotate opposite ways for the same reference_search_mode
    value relative to other StepRocker boards (a per-unit rotation-direction
    difference independent of which switch a mode targets); reverse_shaft
    lets a specific device correct for that without touching unaffected units.
    """
    device = TMCM1111Sim.from_config(positions={"waste": 0})
    await device.initialize()

    assert 251 not in device.sim_io.axis_parameters


async def test_reverse_shaft_applies_axis_parameter_when_configured():
    device = TMCM1111Sim.from_config(positions={"waste": 0}, reverse_shaft=True)
    await device.initialize()

    assert device.sim_io.axis_parameters[251] == 1


async def test_motion_parameters_not_touched_when_unconfigured():
    """MVP's own ramp parameters (#4/#5) must not be touched by default.

    These are separate from RFS's reference_search_speed/reference_switch_speed
    (#194/#195) and were never set by this driver before; a device that already
    has usable values loaded (e.g. from TMCL-IDE) should be left alone.
    """
    device = TMCM1111Sim.from_config(positions={"waste": 0})
    await device.initialize()

    assert int(AxisParameter.MAX_POSITIONING_SPEED) not in device.sim_io.axis_parameters
    assert int(AxisParameter.MAX_ACCELERATION) not in device.sim_io.axis_parameters


async def test_motion_parameters_applied_when_configured():
    device = TMCM1111Sim.from_config(
        positions={"waste": 0},
        max_positioning_speed=51200,
        max_acceleration=500000,
    )
    await device.initialize()

    assert (
        device.sim_io.axis_parameters[int(AxisParameter.MAX_POSITIONING_SPEED)] == 51200
    )
    assert device.sim_io.axis_parameters[int(AxisParameter.MAX_ACCELERATION)] == 500000


def test_from_config_applies_concrete_reference_defaults(monkeypatch):
    """TMCM1111's own from_config ships concrete defaults, unlike the shared base's None.

    reverse_shaft=True here specifically mirrors the physical board this was
    confirmed correct for on real hardware - it's a documented starting point,
    not a universally-safe value (see the class docstring / device docs).
    """
    monkeypatch.setattr(
        "flowchem.devices.trinamic.tmcm_base.TMCLSerialIO.from_config",
        lambda port, **kwargs: object(),
    )

    device = TMCM1111.from_config(port="COM_TEST", positions={"waste": 0})

    assert device.reference_search_mode == 1
    assert device.reference_search_speed == 51200
    assert device.reference_switch_speed == 4096
    assert device.reverse_shaft is True
    assert device.max_positioning_speed == 51200
    assert device.max_acceleration == 500000


def test_from_config_defaults_can_be_overridden(monkeypatch):
    monkeypatch.setattr(
        "flowchem.devices.trinamic.tmcm_base.TMCLSerialIO.from_config",
        lambda port, **kwargs: object(),
    )

    device = TMCM1111.from_config(
        port="COM_TEST",
        positions={"waste": 0},
        reverse_shaft=False,
        reference_search_mode=65,
    )

    assert device.reverse_shaft is False
    assert device.reference_search_mode == 65


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
