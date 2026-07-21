"""Shared TMCL driver logic for the Trinamic/ADI TMCM-11x0 StepRocker family.

Axis-parameter *numbers* used here (target/actual position, position-reached
flag, home/limit switch states, reference-search mode/speeds) are identical
across the TMCM-1110 (TMC429-based) and TMCM-1111 (TMC4361-based) TMCL
firmware manuals. What differs between models is the *units* some of those
parameters hold (see ``_encode_speed``) and how the device identifies
itself, which is why those two points are the only hooks a subclass needs
to override.
"""

from __future__ import annotations

import asyncio
from enum import IntEnum
from typing import Any, ClassVar, Self

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.trinamic.tmcl import (
    MVPType,
    RFSType,
    TMCLCommandNumber,
    TMCLReply,
    TMCLRequest,
    TMCLSerialIO,
)
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError
from flowchem.utils.people import samuel_saraiva

_DEFAULT_MOTOR = 0

# Every StepRocker model flowchem supports, used by the best-effort hardware
# identification check in _verify_hardware_model. Add new models here.
_KNOWN_STEPROCKER_MODELS = ("1110", "1111")


class AxisParameter(IntEnum):
    """TMCM StepRocker axis parameters used by the fraction-collector API.

    These parameter *numbers* are confirmed identical on the TMCM-1110 and
    TMCM-1111 axis-parameter tables.
    """

    TARGET_POSITION = 0
    ACTUAL_POSITION = 1
    MAX_POSITIONING_SPEED = 4
    MAX_ACCELERATION = 5
    POSITION_REACHED = 8
    HOME_SWITCH_STATE = 9
    RIGHT_LIMIT_SWITCH_STATE = 10
    LEFT_LIMIT_SWITCH_STATE = 11
    REFERENCE_SEARCH_MODE = 193
    REFERENCE_SEARCH_SPEED = 194
    REFERENCE_SWITCH_SPEED = 195


class TMCMStepRockerBase(FlowchemDevice):
    """Shared single-axis TMCL driver, used as a linear fraction collector."""

    #: Model number as it appears in the firmware version string, e.g. "1111".
    MODEL_NAME: ClassVar[str]
    #: Human-readable model name, e.g. "TMCM-1111 StepRocker".
    MODEL_DISPLAY_NAME: ClassVar[str]
    #: FlowchemComponent subclass registered on initialize().
    COMPONENT_CLASS: ClassVar[type[FlowchemComponent]]
    #: Axis parameter number for "reverse shaft" (reverses which physical
    #: rotation direction the board treats as positive, independent of which
    #: switch a reference-search mode watches). Confirmed as #251 on the
    #: TMCM-1111; None (unsupported/unknown) by default so models that don't
    #: define it simply skip the read-back/apply logic in initialize().
    REVERSE_SHAFT_PARAM: ClassVar[int | None] = None

    def __init__(
        self,
        tmcm_io: Any,
        positions: dict[str, int],
        address: int = 1,
        name: str = "",
        home_position: str = "",
        home_on_initialize: bool = False,
        reference_search_mode: int | None = None,
        reference_search_speed: int | None = None,
        reference_switch_speed: int | None = None,
        reverse_shaft: bool | None = None,
        max_positioning_speed: int | None = None,
        max_acceleration: int | None = None,
    ) -> None:
        super().__init__(name)
        if not positions:
            raise InvalidConfigurationError(
                f"{type(self).__name__} requires at least one named position."
            )
        self.tmcm_io = tmcm_io
        self.address = address
        self.positions = {
            str(position_name): int(steps) for position_name, steps in positions.items()
        }
        self.home_position = home_position
        self.home_on_initialize = home_on_initialize
        self.reference_search_mode = reference_search_mode
        self.reference_search_speed = reference_search_speed
        self.reference_switch_speed = reference_switch_speed
        self.reverse_shaft = reverse_shaft
        self.max_positioning_speed = max_positioning_speed
        self.max_acceleration = max_acceleration

        if self.home_position and self.home_position not in self.positions:
            raise InvalidConfigurationError(
                f"home_position '{self.home_position}' is not present in configured positions."
            )

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Analog Devices / TRINAMIC",
            model=self.MODEL_DISPLAY_NAME,
            additional_info={
                "address": address,
                "positions": self.positions,
            },
        )

    @classmethod
    def from_config(
        cls,
        port: str,
        positions: dict[str, int],
        address: int = 1,
        name: str = "",
        home_position: str = "",
        home_on_initialize: bool = False,
        reference_search_mode: int | None = None,
        reference_search_speed: int | None = None,
        reference_switch_speed: int | None = None,
        reverse_shaft: bool | None = None,
        max_positioning_speed: int | None = None,
        max_acceleration: int | None = None,
        **serial_kwargs,
    ) -> Self:
        """Create a StepRocker device from Flowchem TOML configuration."""
        tmcm_io = TMCLSerialIO.from_config(port, **serial_kwargs)
        return cls(
            tmcm_io=tmcm_io,
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
        )

    async def initialize(self) -> None:
        """Verify the hardware model, register the component, and optionally home."""
        await self._verify_hardware_model()
        await self._configure_reverse_shaft()
        await self._configure_motion_parameters()
        if self.home_on_initialize:
            await self.home(wait=True)
        self.components.append(self.COMPONENT_CLASS("fraction-collector", self))
        logger.info(
            f"Connected to {self.MODEL_DISPLAY_NAME} fraction collector '{self.name}'."
        )

    async def _configure_reverse_shaft(self) -> None:
        """Log and optionally set the model's "reverse shaft" axis parameter.

        Rotation direction and reference-search switch selection can be
        independently inverted per physical unit (e.g. two boards of the
        same model can rotate opposite ways for the same reference_search_mode
        value). This parameter (axis parameter #251 on the TMCM-1111) fixes
        the rotation-direction half of that without touching which switch a
        mode targets. Always logs the board's current value so it's visible
        without a separate diagnostic script; only writes it if reverse_shaft
        was explicitly configured.
        """
        param = type(self).REVERSE_SHAFT_PARAM
        if param is None:
            return
        current = await self._gap(param)
        logger.info(
            f"{self.MODEL_DISPLAY_NAME} '{self.name}' reverse_shaft (axis parameter "
            f"#{param}) currently reads {current}."
        )
        if self.reverse_shaft is not None:
            await self._sap(param, int(self.reverse_shaft))
            logger.info(
                f"Set reverse_shaft (axis parameter #{param}) to {int(self.reverse_shaft)}."
            )

    async def _configure_motion_parameters(self) -> None:
        """Set MVP's own ramp parameters (axis parameters #4/#5), if configured.

        MVP (the "move to position" command behind PUT /position) is governed
        by its own maximum positioning speed (#4) and maximum acceleration
        (#5) - entirely separate from RFS's reference_search_speed/
        reference_switch_speed (#194/#195). Flowchem never set these before,
        which is easy to miss because it works fine as long as the board
        already has usable values loaded (e.g. from a previous TMCL-IDE
        session) - but axis parameters are volatile SRAM, so a power cycle
        resets them, and MVP then silently computes a valid target with zero
        velocity (no motion, no error) while RFS keeps working normally since
        it has its own explicitly-configured speed parameters.
        """
        if self.max_positioning_speed is not None:
            await self._sap(
                AxisParameter.MAX_POSITIONING_SPEED,
                await self._encode_speed(self.max_positioning_speed),
            )
        if self.max_acceleration is not None:
            await self._sap(
                AxisParameter.MAX_ACCELERATION,
                await self._encode_acceleration(self.max_acceleration),
            )

    async def move_to_position(self, position: str | int) -> bool:
        """Move to a named configured position or raw microstep position."""
        target = self._position_to_steps(position)
        await self._mvp_abs(target)
        logger.info(
            f"{self.MODEL_DISPLAY_NAME} '{self.name}' moving to {position} ({target} microsteps)."
        )
        return True

    async def get_position(self) -> str | int:
        """Return exact named position when possible, otherwise raw microsteps."""
        actual_position = await self.get_actual_position()
        for name, steps in self.positions.items():
            if steps == actual_position:
                return name
        return actual_position

    def available_positions(self) -> dict[str, int]:
        """Return configured named positions."""
        return self.positions.copy()

    async def get_actual_position(self) -> int:
        """Return the TMCM actual position in microsteps."""
        return await self._gap(AxisParameter.ACTUAL_POSITION)

    async def is_target_reached(self) -> bool:
        """Return whether the TMCM position reached flag is set."""
        return bool(await self._gap(AxisParameter.POSITION_REACHED))

    async def get_limits(self) -> dict[str, bool]:
        """Return logical switch states for home and rail limits."""
        return {
            "home": bool(await self._gap(AxisParameter.HOME_SWITCH_STATE)),
            "right": bool(await self._gap(AxisParameter.RIGHT_LIMIT_SWITCH_STATE)),
            "left": bool(await self._gap(AxisParameter.LEFT_LIMIT_SWITCH_STATE)),
        }

    async def stop(self) -> bool:
        """Stop motor motion."""
        await self._execute(TMCLCommandNumber.MST)
        return True

    async def home(self, wait: bool = True, timeout: float = 60) -> bool:
        """Start the TMCM reference-search routine and optionally wait for completion."""
        await self._configure_reference_search()
        await self._rfs(RFSType.START)
        if wait:
            await self._wait_for_reference_search(timeout=timeout)
            await self._apply_home_position()
        return True

    async def reference_search_active(self) -> bool:
        """Return whether the TMCM reference-search state machine is active."""
        reply = await self._rfs(RFSType.STATUS)
        return reply.value != 0

    async def _configure_reference_search(self) -> None:
        if self.reference_search_mode is not None:
            await self._sap(
                AxisParameter.REFERENCE_SEARCH_MODE, self.reference_search_mode
            )
        if self.reference_search_speed is not None:
            await self._sap(
                AxisParameter.REFERENCE_SEARCH_SPEED,
                await self._encode_speed(self.reference_search_speed),
            )
        if self.reference_switch_speed is not None:
            await self._sap(
                AxisParameter.REFERENCE_SWITCH_SPEED,
                await self._encode_speed(self.reference_switch_speed),
            )

    async def _encode_speed(self, pps: int) -> int:
        """Convert a pps value to whatever units axis parameters #194/#195 expect.

        Identity by default: TMC4361-based controllers (e.g. TMCM-1111)
        accept real microsteps-per-second directly. TMC429-based
        controllers (e.g. TMCM-1110) override this to convert to their
        dimensionless internal velocity units.
        """
        return pps

    async def _encode_acceleration(self, pps2: int) -> int:
        """Convert a pps² value to whatever units axis parameter #5 expects.

        Identity by default (TMC4361-based controllers, e.g. TMCM-1111, accept
        real pps² directly). TMC429-based controllers (e.g. TMCM-1110) use a
        different conversion than _encode_speed - a separate ramp divisor
        (axis parameter #153), not just the pulse divisor - so this is a
        distinct hook rather than reusing _encode_speed.
        """
        return pps2

    async def _verify_hardware_model(self) -> None:
        """Best-effort check that the connected board matches the configured model.

        TMCL control command 136 (get firmware version), type 0, returns a
        "special reply" string that is expected to embed the module number
        (e.g. "1110V113"), per common TRINAMIC/ADI TMCL convention - but
        neither the TMCM-1110 nor the TMCM-1111 manual documents its exact
        byte layout, so this reads a generous number of raw bytes and
        searches them for a known model token rather than assuming a fixed
        width. Firmware version *numbers* overlap between the 1110 and 1111
        product lines (both currently ship "V1.13"), so the binary-format
        reply (type 1) cannot distinguish the two models - only the string
        reply, if it carries the module number, can. Any failure to
        read/parse is logged and treated as inconclusive rather than fatal;
        a confirmed mismatch (a different known model's token found, and
        not our own) raises DeviceError.

        This mechanism has not been verified against real TMCM-1110 /
        TMCM-1111 hardware or TRINAMIC's official host source - treat the
        exact byte layout assumption as unconfirmed until checked.
        """
        try:
            raw = await self.tmcm_io.request_raw(
                TMCLRequest(
                    address=self.address,
                    command=int(TMCLCommandNumber.GET_FIRMWARE_VERSION),
                    command_type=0,
                    motor=0,
                    value=0,
                ),
                read_length=32,
            )
            text = raw.decode("ascii", errors="ignore")
        except Exception as exc:  # noqa: BLE001 - non-fatal by design, see docstring
            logger.warning(
                f"Could not read a firmware version string from '{self.name}' to verify "
                f"the hardware model ({exc}); proceeding without verification."
            )
            return

        if self.MODEL_NAME in text:
            return

        mismatched_model = next(
            (
                model
                for model in _KNOWN_STEPROCKER_MODELS
                if model != self.MODEL_NAME and model in text
            ),
            None,
        )
        if mismatched_model is not None:
            raise DeviceError(
                f"Device at '{self.name}' reports firmware string {text!r}, which looks "
                f"like a TMCM-{mismatched_model} rather than the configured "
                f"TMCM-{self.MODEL_NAME}. Check the wiring/port assignment or the "
                f"device `type` in the TOML config."
            )

        logger.warning(
            f"Could not confirm the hardware model from firmware string {text!r} for "
            f"'{self.name}' (expected it to contain '{self.MODEL_NAME}'); proceeding "
            f"without verification."
        )

    async def _wait_for_reference_search(self, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while await self.reference_search_active():
            if asyncio.get_running_loop().time() >= deadline:
                await self._rfs(RFSType.STOP)
                raise DeviceError(
                    f"{self.MODEL_DISPLAY_NAME} reference search timed out."
                )
            await asyncio.sleep(0.1)

    async def _apply_home_position(self) -> None:
        if self.home_position:
            await self._sap(
                AxisParameter.ACTUAL_POSITION, self.positions[self.home_position]
            )

    async def _mvp_abs(self, target_position: int) -> TMCLReply:
        return await self._execute(
            TMCLCommandNumber.MVP,
            command_type=MVPType.ABS,
            value=target_position,
        )

    async def _sap(self, parameter: AxisParameter | int, value: int) -> TMCLReply:
        return await self._execute(
            TMCLCommandNumber.SAP,
            command_type=int(parameter),
            value=value,
        )

    async def _gap(self, parameter: AxisParameter | int) -> int:
        reply = await self._execute(
            TMCLCommandNumber.GAP,
            command_type=int(parameter),
        )
        return reply.value

    async def _rfs(self, rfs_type: RFSType) -> TMCLReply:
        return await self._execute(TMCLCommandNumber.RFS, command_type=int(rfs_type))

    async def _execute(
        self,
        command: TMCLCommandNumber,
        command_type: int = 0,
        motor: int = _DEFAULT_MOTOR,
        value: int = 0,
    ) -> TMCLReply:
        request = TMCLRequest(
            address=self.address,
            command=int(command),
            command_type=command_type,
            motor=motor,
            value=value,
        )
        return await self.tmcm_io.write_and_read_reply(request)

    def _position_to_steps(self, position: str | int) -> int:
        if isinstance(position, str) and position in self.positions:
            return self.positions[position]
        try:
            return int(position)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Unknown {type(self).__name__} position '{position}'. "
                f"Use one of {list(self.positions)} or a raw integer microstep position."
            ) from error

    def close(self) -> None:
        """Close the underlying serial port."""
        try:
            self.tmcm_io.close()
        except AttributeError:
            return

    def __del__(self) -> None:
        self.close()
