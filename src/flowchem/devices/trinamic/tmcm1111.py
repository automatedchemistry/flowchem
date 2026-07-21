"""Control a TMCM-1111 StepRocker as a linear fraction collector."""

from __future__ import annotations

from typing import Self

from flowchem.devices.trinamic.tmcl import (
    TMCL_FRAME_SIZE,
    TMCL_STATUS_MESSAGES,
    MVPType,
    RFSType,
    TMCLCommandNumber,
    TMCLReply,
    TMCLRequest,
    TMCLSerialIO,
    decode_tmcl_reply,
    tmcl_checksum,
)
from flowchem.devices.trinamic.tmcm1111_component import TMCM1111FractionCollector
from flowchem.devices.trinamic.tmcm_base import AxisParameter, TMCMStepRockerBase

__all__ = [
    "TMCL_FRAME_SIZE",
    "TMCL_STATUS_MESSAGES",
    "AxisParameter",
    "MVPType",
    "RFSType",
    "TMCLCommandNumber",
    "TMCLReply",
    "TMCLRequest",
    "TMCM1111",
    "TMCM1111IO",
    "TMCM1111_MOTOR",
    "decode_tmcl_reply",
    "tmcl_checksum",
]

# Backward-compatible aliases: the TMCL transport and single-motor constant
# are now shared across the whole StepRocker family (see tmcl.py /
# tmcm_base.py), but existing code/tests import them from this module.
TMCM1111IO = TMCLSerialIO
TMCM1111_MOTOR = 0


class TMCM1111(TMCMStepRockerBase):
    """TMCM-1111 single-axis controller (TMC4361-based) used as a linear fraction collector."""

    MODEL_NAME = "1111"
    MODEL_DISPLAY_NAME = "TMCM-1111 StepRocker"
    COMPONENT_CLASS = TMCM1111FractionCollector
    # Confirmed in the TMCM-1111 TMCL firmware manual (axis parameter table,
    # p. 106): "Reverse the rotation direction of the motor shaft."
    REVERSE_SHAFT_PARAM = 251

    @classmethod
    def from_config(
        cls,
        port: str,
        positions: dict[str, int],
        address: int = 1,
        name: str = "",
        home_position: str = "",
        home_on_initialize: bool = False,
        reference_search_mode: int | None = 1,
        reference_search_speed: int | None = 51200,
        reference_switch_speed: int | None = 4096,
        reverse_shaft: bool | None = True,
        max_positioning_speed: int | None = 51200,
        max_acceleration: int | None = 500000,
        **serial_kwargs,
    ) -> Self:
        """Create a TMCM-1111 from Flowchem TOML configuration.

        Unlike the shared base class, these kwargs default to concrete values
        rather than None, so they're visible as a reference here instead of
        only in the docs. They mirror the specific board calibrated against
        real hardware in this project (reference_search_mode=1 with
        reverse_shaft=True gives a clean, switch-triggered home; the speeds
        are working example magnitudes) - verify/override every one of them
        for a different physical unit or rail, especially reverse_shaft,
        which is a per-board quirk rather than a per-model constant. Each
        still accepts None explicitly too, matching the base class, which
        means "leave this axis parameter untouched" rather than "use 0".
        """
        return super().from_config(
            port=port,
            positions=positions,
            address=address,
            name=name,
            home_position=home_position,
            home_on_initialize=home_on_initialize,
            reference_search_mode=reference_search_mode,
            reference_search_speed=reference_search_speed,
            reference_switch_speed=reference_switch_speed,
            reverse_shaft=reverse_shaft,
            max_positioning_speed=max_positioning_speed,
            max_acceleration=max_acceleration,
            **serial_kwargs,
        )
