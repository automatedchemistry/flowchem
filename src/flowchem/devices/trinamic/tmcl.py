"""Generic TMCL (Trinamic Motion Control Language) direct-mode protocol.

Binary framing, checksum, reply decoding, and the serial transport are
identical across the whole StepRocker family (TMCM-1110, TMCM-1111, ...),
per both products' TMCL firmware manuals. Model-specific behaviour (axis
parameter units, reference-search capabilities, hardware identification)
lives in ``tmcm_base.py`` and each model's own module.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import aioserial
from loguru import logger

from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError

TMCL_FRAME_SIZE = 9


class TMCLCommandNumber(IntEnum):
    """TMCL command numbers used by the StepRocker driver family."""

    MST = 3
    MVP = 4
    SAP = 5
    GAP = 6
    RFS = 13
    # TMCL "control command", not a regular axis/global-parameter command:
    # type 0 requests a string-format reply, type 1 a binary-format one.
    GET_FIRMWARE_VERSION = 136


class MVPType(IntEnum):
    """TMCL MVP command types."""

    ABS = 0
    REL = 1


class RFSType(IntEnum):
    """TMCL RFS command types."""

    START = 0
    STOP = 1
    STATUS = 2


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
        raise DeviceError(
            f"TMCL reply must be {TMCL_FRAME_SIZE} bytes, got {len(frame)}."
        )
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
        raise DeviceError(
            f"TMCL command failed with status {reply.status}: {status_message}."
        )
    return reply


class TMCLSerialIO:
    """Low-level serial transport for TMCL direct mode, shared by the StepRocker family."""

    DEFAULT_CONFIG: dict[str, Any] = {
        "timeout": 1,
        "baudrate": 9600,
        "bytesize": aioserial.EIGHTBITS,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
    }

    def __init__(self, port: str, **kwargs) -> None:
        configuration = dict(TMCLSerialIO.DEFAULT_CONFIG, **kwargs)
        self.lock = asyncio.Lock()
        try:
            self._serial = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            logger.error(f"Cannot connect to the TMCM controller on port <{port}>.")
            raise InvalidConfigurationError(
                f"Cannot connect to the TMCM controller on port <{port}>."
            ) from serial_exception

    @classmethod
    def from_config(cls, port: str, **serial_kwargs) -> "TMCLSerialIO":
        """Create low-level serial I/O from TOML serial settings."""
        return cls(port, **serial_kwargs)

    async def write_and_read_reply(self, request: TMCLRequest) -> TMCLReply:
        """Send a TMCL request and return the validated reply."""
        frame = request.to_bytes()
        async with self.lock:
            self._serial.reset_input_buffer()
            await self._serial.write_async(frame)
            reply_frame = await self._serial.read_async(TMCL_FRAME_SIZE)
        logger.debug(f"TMCL sent {frame.hex()} received {reply_frame.hex()}")
        return decode_tmcl_reply(reply_frame, expected_command=request.command)

    async def request_raw(self, request: TMCLRequest, read_length: int) -> bytes:
        """Send a TMCL request and return up to ``read_length`` raw reply bytes.

        Used for TMCL control-command replies (e.g. get-firmware-version,
        type 0) whose "special reply format" is not a fixed 9-byte frame
        like normal TMCL replies. TRINAMIC's manuals don't document the
        exact byte layout of that special reply, so callers read generously
        and search/decode the raw bytes themselves instead of assuming a
        fixed width.
        """
        frame = request.to_bytes()
        async with self.lock:
            self._serial.reset_input_buffer()
            await self._serial.write_async(frame)
            reply = await self._serial.read_async(read_length)
        logger.debug(f"TMCL sent {frame.hex()} raw reply {reply.hex()}")
        return reply

    def close(self) -> None:
        """Close the underlying serial port."""
        try:
            self._serial.close()
        except AttributeError:
            return
