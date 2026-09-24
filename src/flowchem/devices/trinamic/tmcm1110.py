"""Control a TMCM-1110 StepRocker as a linear fraction collector."""

from __future__ import annotations

from typing import Self

from flowchem.devices.trinamic.tmcm1110_component import TMCM1110FractionCollector
from flowchem.devices.trinamic.tmcm_base import TMCMStepRockerBase

__all__ = [
    "TMCM1110",
    "pps2_to_tmc429_acceleration",
    "pps_to_tmc429_velocity",
    "tmc429_acceleration_to_pps2",
    "tmc429_velocity_to_pps",
]

# TMC429 clock and velocity-formula scaling factor, per the TMCM-1110 TMCL
# firmware manual section 6.1.1 ("Velocity Conversion").
_TMC429_CLOCK_HZ = 16_000_000
_VELOCITY_SCALE = 2048 * 32

# TMC429-specific axis parameters (not shared with the TMC4361-based
# TMCM-1111): the pulse divisor relates the dimensionless 0...2047 "internal
# unit" velocity register (axis parameters #2/#4/#194/#195) to real
# microsteps/second; the ramp divisor does the same for the acceleration
# register (axis parameter #5), per section 6.1.2 ("Acceleration Conversion").
_PULSE_DIVISOR_PARAM = 154
_RAMP_DIVISOR_PARAM = 153


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


def pps2_to_tmc429_acceleration(
    pps2: int, ramp_divisor: int, pulse_divisor: int
) -> int:
    """Convert a real-world acceleration (pps²) to a TMC429 acceleration register value.

    Inverse of the manual's conversion formula (section 6.1.2):

        a_pps = (16e6)**2 * a_int / 2**(ramp_divisor + pulse_divisor + 29)

    solved for a_int and rounded to the nearest integer.

    Raises
    ------
    ValueError
        If the result doesn't fit the TMC429's 0...2047 acceleration register
        range - adjust the ramp divisor (axis parameter #153), the pulse
        divisor (axis parameter #154), or the requested acceleration.
    """
    a_int = round(
        pps2 * (2 ** (ramp_divisor + pulse_divisor + 29)) / (_TMC429_CLOCK_HZ**2)
    )
    if not 0 <= a_int <= 2047:
        raise ValueError(
            f"{pps2} pps2 does not fit the TMC429 acceleration range (0-2047 "
            f"internal units) at ramp divisor {ramp_divisor} / pulse divisor "
            f"{pulse_divisor}; computed {a_int}. Adjust the ramp/pulse divisors "
            f"(axis parameters #153/#154) or the requested acceleration."
        )
    return a_int


def tmc429_acceleration_to_pps2(
    a_int: int, ramp_divisor: int, pulse_divisor: int
) -> float:
    """Convert a TMC429 acceleration register value to a real-world pps² acceleration.

    Forward direction of the same manual formula; kept alongside the inverse
    mainly so it can be validated against the manual's own worked example
    (a_int=100, ramp_divisor=7, pulse_divisor=3 -> ~46566pps2) in tests.
    """
    return (_TMC429_CLOCK_HZ**2) * a_int / (2 ** (ramp_divisor + pulse_divisor + 29))


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

    async def _encode_acceleration(self, pps2: int) -> int:
        """Convert a pps² value to the TMC429's dimensionless internal acceleration units.

        Reads the currently configured ramp and pulse divisors (axis
        parameters #153/#154) from the device rather than assuming defaults.
        """
        ramp_divisor = await self._gap(_RAMP_DIVISOR_PARAM)
        pulse_divisor = await self._gap(_PULSE_DIVISOR_PARAM)
        return pps2_to_tmc429_acceleration(pps2, ramp_divisor, pulse_divisor)

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
        reverse_shaft: bool | None = None,
        max_positioning_speed: int | None = 51200,
        max_acceleration: int | None = 500000,
        **serial_kwargs,
    ) -> Self:
        """Create a TMCM-1110 from Flowchem TOML configuration.

        Unlike the shared base class, these kwargs default to concrete values
        (given in real pps/pps² - converted to the TMC429's internal units
        automatically) rather than None, so they're visible as a reference
        here instead of only in the docs. They're working example magnitudes
        from this project's real-hardware testing, not universal constants -
        verify/override them for a different physical unit or rail. Each
        still accepts None explicitly too, matching the base class, which
        means "leave this axis parameter untouched" rather than "use 0".

        reverse_shaft is accepted (default None) purely for interface
        consistency with TMCM1111.from_config - it has no effect on the
        TMCM-1110, since axis parameter #251 ("Reverse shaft") doesn't exist
        on this model's axis parameter table.
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
