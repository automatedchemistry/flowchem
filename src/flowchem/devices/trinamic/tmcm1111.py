"""Control a TMCM-1111 StepRocker as a linear fraction collector."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import aioserial
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.trinamic.tmcm1111_component import TMCM1111FractionCollector
from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError
from flowchem.utils.people import samuel_saraiva

TMCL_FRAME_SIZE = 9
TMCM1111_MOTOR = 0


class TMCLCommandNumber(IntEnum):
    """TMCL command numbers used by the TMCM-1111 driver."""

    MST = 3
    MVP = 4
    SAP = 5
    GAP = 6
    RFS = 13


class MVPType(IntEnum):
    """TMCL MVP command types."""

    ABS = 0
    REL = 1


class RFSType(IntEnum):
    """TMCL RFS command types."""

    START = 0
    STOP = 1
    STATUS = 2


class AxisParameter(IntEnum):
    """TMCM-1111 axis parameters used by the fraction-collector API."""

    TARGET_POSITION = 0
    ACTUAL_POSITION = 1
    POSITION_REACHED = 8
    HOME_SWITCH_STATE = 9
    RIGHT_LIMIT_SWITCH_STATE = 10
    LEFT_LIMIT_SWITCH_STATE = 11
    REFERENCE_SEARCH_MODE = 193
    REFERENCE_SEARCH_SPEED = 194
    REFERENCE_SWITCH_SPEED = 195


TMCL_STATUS_MESSAGES = {
    1: "Wrong checksum",
    2: "Invalid command",
    3: "Wrong type",
    4: "Invalid value",
    5: "Configuration EEPROM locked",
    6: "Command not available",
    100: "OK",
    101: "Command loaded into TMCL program EEPROM",
    128: "Position reached event",
}


@dataclass(frozen=True)
class TMCLRequest:
    """One 9-byte TMCL direct-mode request."""

    address: int
    command: int
    command_type: int
    motor: int
    value: int = 0

    def to_bytes(self) -> bytes:
        """Encode request as a TMCL binary frame."""
        frame = bytes(
            [
                self.address & 0xFF,
                self.command & 0xFF,
                self.command_type & 0xFF,
                self.motor & 0xFF,
            ]
        ) + int(self.value).to_bytes(4, byteorder="big", signed=True)
        return frame + bytes([tmcl_checksum(frame)])


@dataclass(frozen=True)
class TMCLReply:
    """One decoded 9-byte TMCL direct-mode reply."""

    host_address: int
    target_address: int
    status: int
    command: int
    value: int


def tmcl_checksum(frame_without_checksum: bytes) -> int:
    """Return the TMCL checksum, defined as byte-sum modulo 256."""
    return sum(frame_without_checksum) & 0xFF


def decode_tmcl_reply(frame: bytes, expected_command: int | None = None) -> TMCLReply:
    """Decode and validate one TMCL reply frame."""
    if len(frame) != TMCL_FRAME_SIZE:
        raise DeviceError(f"TMCL reply must be {TMCL_FRAME_SIZE} bytes, got {len(frame)}.")
    if tmcl_checksum(frame[:-1]) != frame[-1]:
        raise DeviceError("TMCL reply checksum mismatch.")

    value = int.from_bytes(frame[4:8], byteorder="big", signed=True)
    reply = TMCLReply(
        host_address=frame[0],
        target_address=frame[1],
        status=frame[2],
        command=frame[3],
        value=value,
    )
    if expected_command is not None and reply.command != expected_command:
        raise DeviceError(
            f"TMCL reply command {reply.command} does not match expected command {expected_command}."
        )
    if reply.status != 100:
        status_message = TMCL_STATUS_MESSAGES.get(reply.status, "Unknown TMCL status")
        raise DeviceError(f"TMCL command failed with status {reply.status}: {status_message}.")
    return reply


class TMCM1111IO:
    """Low-level serial transport for TMCM-1111 TMCL direct mode."""

    DEFAULT_CONFIG: dict[str, Any] = {
        "timeout": 1,
        "baudrate": 9600,
        "bytesize": aioserial.EIGHTBITS,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
    }

    def __init__(self, port: str, **kwargs) -> None:
        configuration = dict(TMCM1111IO.DEFAULT_CONFIG, **kwargs)
        self.lock = asyncio.Lock()
        try:
            self._serial = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            logger.error(f"Cannot connect to the TMCM-1111 on port <{port}>.")
            raise InvalidConfigurationError(
                f"Cannot connect to the TMCM-1111 on port <{port}>."
            ) from serial_exception

    @classmethod
    def from_config(cls, port: str, **serial_kwargs) -> "TMCM1111IO":
        """Create low-level serial I/O from TOML serial settings."""
        return cls(port, **serial_kwargs)

    async def write_and_read_reply(self, request: TMCLRequest) -> TMCLReply:
        """Send a TMCL request and return the validated reply."""
        frame = request.to_bytes()
        async with self.lock:
            self._serial.reset_input_buffer()
            await self._serial.write_async(frame)
            reply_frame = await self._serial.read_async(TMCL_FRAME_SIZE)
        logger.debug(f"TMCM-1111 sent {frame.hex()} received {reply_frame.hex()}")
        return decode_tmcl_reply(reply_frame, expected_command=request.command)

    def close(self) -> None:
        """Close the underlying serial port."""
        try:
            self._serial.close()
        except AttributeError:
            return


class TMCM1111(FlowchemDevice):
    """TMCM-1111 single-axis controller used as a linear fraction collector."""

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
    ) -> None:
        super().__init__(name)
        if not positions:
            raise InvalidConfigurationError("TMCM1111 requires at least one named position.")
        self.tmcm_io = tmcm_io
        self.address = address
        self.positions = {str(position_name): int(steps) for position_name, steps in positions.items()}
        self.home_position = home_position
        self.home_on_initialize = home_on_initialize
        self.reference_search_mode = reference_search_mode
        self.reference_search_speed = reference_search_speed
        self.reference_switch_speed = reference_switch_speed

        if self.home_position and self.home_position not in self.positions:
            raise InvalidConfigurationError(
                f"home_position '{self.home_position}' is not present in configured positions."
            )

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Analog Devices / TRINAMIC",
            model="TMCM-1111 StepRocker",
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
        **serial_kwargs,
    ) -> "TMCM1111":
        """Create a TMCM1111 from Flowchem TOML configuration."""
        tmcm_io = TMCM1111IO.from_config(port, **serial_kwargs)
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
        )

    async def initialize(self) -> None:
        """Register the fraction collector component and optionally home the rail."""
        if self.home_on_initialize:
            await self.home(wait=True)
        self.components.append(TMCM1111FractionCollector("fraction-collector", self))
        logger.info(f"Connected to TMCM-1111 fraction collector '{self.name}'.")

    async def move_to_position(self, position: str | int) -> bool:
        """Move to a named configured position or raw microstep position."""
        target = self._position_to_steps(position)
        await self._mvp_abs(target)
        logger.info(f"TMCM-1111 '{self.name}' moving to {position} ({target} microsteps).")
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
            await self._sap(AxisParameter.REFERENCE_SEARCH_MODE, self.reference_search_mode)
        if self.reference_search_speed is not None:
            await self._sap(AxisParameter.REFERENCE_SEARCH_SPEED, self.reference_search_speed)
        if self.reference_switch_speed is not None:
            await self._sap(AxisParameter.REFERENCE_SWITCH_SPEED, self.reference_switch_speed)

    async def _wait_for_reference_search(self, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while await self.reference_search_active():
            if asyncio.get_running_loop().time() >= deadline:
                await self._rfs(RFSType.STOP)
                raise DeviceError("TMCM-1111 reference search timed out.")
            await asyncio.sleep(0.1)

    async def _apply_home_position(self) -> None:
        if self.home_position:
            await self._sap(AxisParameter.ACTUAL_POSITION, self.positions[self.home_position])

    async def _mvp_abs(self, target_position: int) -> TMCLReply:
        return await self._execute(
            TMCLCommandNumber.MVP,
            command_type=MVPType.ABS,
            value=target_position,
        )

    async def _sap(self, parameter: AxisParameter, value: int) -> TMCLReply:
        return await self._execute(
            TMCLCommandNumber.SAP,
            command_type=int(parameter),
            value=value,
        )

    async def _gap(self, parameter: AxisParameter) -> int:
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
        motor: int = TMCM1111_MOTOR,
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
                f"Unknown TMCM1111 position '{position}'. "
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
