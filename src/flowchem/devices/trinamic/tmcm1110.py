"""Control a TMCM-1110 StepRocker as a linear fraction collector."""

from __future__ import annotations

from flowchem.devices.trinamic.tmcm1110_component import TMCM1110FractionCollector
from flowchem.devices.trinamic.tmcm_base import TMCMStepRockerBase

__all__ = [
    "TMCM1110",
    "pps_to_tmc429_velocity",
    "tmc429_velocity_to_pps",
]

# TMC429 clock and velocity-formula scaling factor, per the TMCM-1110 TMCL
# firmware manual section 6.1.1 ("Velocity Conversion").
_TMC429_CLOCK_HZ = 16_000_000
_VELOCITY_SCALE = 2048 * 32

# TMC429-specific axis parameter (not shared with the TMC4361-based
# TMCM-1111): the pulse divisor that relates the dimensionless 0...2047
# "internal unit" velocity register to real microsteps/second.
_PULSE_DIVISOR_PARAM = 154


def pps_to_tmc429_velocity(pps: int, pulse_divisor: int) -> int:
    """Convert a real-world velocity (microsteps/second) to a TMC429 velocity register value.

    Inverse of the manual's conversion formula:

        v_pps = (16e6 * v_int) / (2**pulse_divisor * 2048 * 32)

    solved for v_int and rounded to the nearest integer.

    Raises
    ------
    ValueError
        If the result doesn't fit the TMC429's 0...2047 velocity register
        range - adjust the pulse divisor (axis parameter #154) or the
        requested speed.
    """
    v_int = round(pps * (2**pulse_divisor) * _VELOCITY_SCALE / _TMC429_CLOCK_HZ)
    if not 0 <= v_int <= 2047:
        raise ValueError(
            f"{pps} pps does not fit the TMC429 velocity range (0-2047 internal "
            f"units) at pulse divisor {pulse_divisor}; computed {v_int}. Adjust "
            f"the pulse divisor (axis parameter #154) or the requested speed."
        )
    return v_int


def tmc429_velocity_to_pps(v_int: int, pulse_divisor: int) -> float:
    """Convert a TMC429 velocity register value to a real-world pps velocity.

    Forward direction of the same manual formula; kept alongside the
    inverse mainly so it can be validated against the manual's own worked
    example (v_int=1678, pulse_divisor=3 -> ~51208.5pps) in tests.
    """
    return (_TMC429_CLOCK_HZ * v_int) / (2**pulse_divisor * _VELOCITY_SCALE)


class TMCM1110(TMCMStepRockerBase):
    """TMCM-1110 single-axis controller (TMC429-based) used as a linear fraction collector."""

    MODEL_NAME = "1110"
    MODEL_DISPLAY_NAME = "TMCM-1110 StepRocker"
    COMPONENT_CLASS = TMCM1110FractionCollector

    async def _encode_speed(self, pps: int) -> int:
        """Convert a pps value to the TMC429's dimensionless internal velocity units.

        Reads the currently configured pulse divisor (axis parameter #154)
        from the device so this respects whatever value is already set
        (e.g. via the TMCL-IDE) rather than assuming a default.
        """
        pulse_divisor = await self._gap(_PULSE_DIVISOR_PARAM)
        return pps_to_tmc429_velocity(pps, pulse_divisor)
