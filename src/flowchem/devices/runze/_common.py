"""Shared low-level protocol primitives for Runze devices.

Runze's SV-06 multiposition valve and Smart SY-01 syringe pump both speak the
same binary framed serial protocol: a `CC` header, one address byte, one
function-code byte, a 2-byte little-endian parameter, a `DD` end byte and a
2-byte cumulative-sum checksum. This module hosts that shared frame builder
and serial IO so both device drivers -- and any mix of them multi-dropped on
the same RS-485 line -- reuse a single serial connection per COM port.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable

import serial
from loguru import logger

from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError

# Response status codes shared by every Runze device (valve or pump); see the
# vendor's Smart SY-01/SV-06 manuals' "Response Status" table.
STATUS_MESSAGES = {
    "00": "Normal status",
    "01": "Frame error",
    "02": "Parameter error",
    "03": "Optocoupler error",
    "04": "Motor busy",
    "05": "Motor stalled",
    "06": "Unknown location",
    "fe": "Task being executed",
    "ff": "Unknown error",
}
# Reply frame length in bytes for both standard and factory commands (the
# manual documents factory-command replies as 8 bytes too, same as standard).
REPLY_FRAME_BYTES = 8


@dataclass
class RunzeCommand:
    """A command frame for Runze's binary protocol (shared by valves and pumps)."""

    address: int  # Slave address
    function_code: str  # Function code based on the command type
    parameter: int = 0  # Parameters corresponding to the function code
    is_factory_command: bool = False  # Flag to indicate if this is a factory command

    password: str = "FFEEBBAA"
    FRAME_HEADER: str = "CC"
    FRAME_END: str = "DD"

    def compile(self) -> str:
        if not self.is_factory_command:
            # Standard command format: 8 bytes
            base_command = (
                f"{self.FRAME_HEADER}"
                f"{self.address:02X}"
                f"{self.function_code}"
                f"{self.parameter & 0xFF:02X}"  # Low byte of parameter
                f"{(self.parameter >> 8) & 0xFF:02X}"  # High byte of parameter
                f"{self.FRAME_END}"  # Frame End
            )
            checksum = (
                sum(
                    int(base_command[i : i + 2], 16)
                    for i in range(0, len(base_command), 2)
                )
                & 0xFFFF
            )
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"  # Low byte of checksum
                f"{(checksum >> 8) & 0xFF:02X}"  # High byte of checksum
            )
        else:
            # Factory command format: 14 bytes
            base_command = (
                f"{self.FRAME_HEADER}"
                f"{self.address:02X}"
                f"{self.function_code}"
                f"{self.password}"
                f"{self.parameter:02X}000000"
                f"{self.FRAME_END}"
            )
            checksum = (
                sum(
                    int(base_command[i : i + 2], 16)
                    for i in range(0, len(base_command), 2)
                )
                & 0xFFFF
            )
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"
                f"{(checksum >> 8) & 0xFF:02X}"
            )

        return compiled_command


class RunzeSerialIO:
    """Serial parameters and low-level IO for Runze's binary protocol.

    Shared by any Runze device (valve or pump) configured on the same port;
    see `get_shared_runze_io` for the registry that enforces one connection
    per port across device classes.
    """

    DEFAULT_CONFIG = {
        # The manual specs <1s response time, but real hardware has been observed
        # to occasionally miss that window on a quick, otherwise-successful
        # command (confirmed transient: an identical retry succeeded immediately) --
        # padded to 3s to absorb that without raising InvalidConfigurationError.
        "timeout": 3,
        "baudrate": 57600,  # The corresponding baudrate can be set through a factory command
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
        "bytesize": serial.EIGHTBITS,
    }

    def __init__(self, port: serial.Serial) -> None:
        """Initialize serial port for a Runze device."""
        self._serial = port
        # A write+read exchange is dispatched to this single dedicated thread
        # as one atomic call (see `_write_and_read_sync`), rather than using
        # `aioserial`'s async read/write (each backed by its OWN separate
        # single-worker executor thread). That two-threads-per-port design
        # measured an ~80% silent-failure rate on real hardware here (12/15
        # dropped replies on a plain status query, reproduced with aioserial
        # in isolation, no driver logic involved) -- apparently pyserial's
        # Windows backend doesn't tolerate a read and a write for the same
        # port happening from two different OS threads. Keeping every
        # exchange on one thread, write immediately followed by read exactly
        # like a synchronous script would, scored 31/31 with zero failures
        # (including moves that failed every time through aioserial).
        self._io_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    @classmethod
    def from_config(cls, config):
        """Create RunzeSerialIO from config."""
        # Combine the default configuration with the user provided configuration
        configuration = RunzeSerialIO.DEFAULT_CONFIG | config

        try:
            serial_object = serial.Serial(**configuration)
        except serial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the device on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)

    def _write_and_read_sync(
        self, command_bytes: bytes, read_timeout: float | None
    ) -> bytes:
        """Reset the input buffer, write, and read exactly one reply frame --
        entirely synchronous, meant to run on `_io_executor`'s single thread
        so a given exchange never splits its write and read across two OS
        threads (see the note in `__init__`).
        """
        self._serial.reset_input_buffer()
        original_timeout = self._serial.timeout
        if read_timeout is not None:
            self._serial.timeout = read_timeout
        try:
            self._serial.write(command_bytes)
            return self._serial.read(REPLY_FRAME_BYTES)
        finally:
            if read_timeout is not None:
                self._serial.timeout = original_timeout

    async def write_and_read_reply_async(
        self,
        command: RunzeCommand,
        raise_errors: bool = True,
        read_timeout: float | None = None,
    ) -> tuple[str, str]:
        """Send a command to the device, read the reply and return it, optionally parsed.

        `read_timeout`, if given, temporarily overrides the connection's serial
        read timeout for this call only, then restores it. Needed because some
        commands (e.g. a plunger move) can legitimately take far longer to
        complete and reply than a status query does.
        """
        command_bytes = bytes.fromhex(f"{command.compile()}\r")
        loop = asyncio.get_running_loop()
        reply_bytes = await loop.run_in_executor(
            self._io_executor, self._write_and_read_sync, command_bytes, read_timeout
        )
        response = reply_bytes.hex()
        if not response:
            raise InvalidConfigurationError(
                f"No response received from device! "
                f"Maybe wrong device address? (Set to {command.address})"
            )
        return self.parse_response(response=response, raise_errors=raise_errors)

    @staticmethod
    def parse_response(response: str, raise_errors: bool = True) -> tuple[str, str]:
        """Split a received frame in its components: status, parameter.

        The parameter field (`B3,B4` in the manual) is a 2-byte
        little-endian value -- both bytes are combined here (previously only
        the low byte was read, silently truncating any value >= 256, which
        corrupts position reads almost immediately into any real pump move).
        """
        status = response[4:6]
        param_low, param_high = response[6:8], response[8:10]
        parameters = param_high + param_low

        etx = response[10:12]
        if etx and etx.lower() != "dd":
            logger.warning(
                f"Reply frame end byte was '{etx}', expected 'dd' -- "
                f"the response may be misaligned: {response}"
            )

        status_string = STATUS_MESSAGES.get(status, "Unknown status code")
        # Check if the status indicates an error
        if status in ("01", "02", "03", "04", "05", "06", "fe", "ff"):
            if raise_errors:
                logger.error(f"{status_string} (Status code: {status})")
                raise DeviceError(
                    f"{status_string} - Check command syntax or device status!"
                )
        return status, parameters


# Devices configured on the same `port` share one RunzeSerialIO, regardless of which
# device class (valve or pump) opened it first -- Runze valves and pumps are routinely
# multi-dropped together on a single RS-485 line, disambiguated only by address.
_shared_io_instances: dict[str, RunzeSerialIO] = {}


def get_shared_runze_io(port: str | None, io_config: dict) -> RunzeSerialIO:
    """Return the RunzeSerialIO for `port`, opening one only if none exists yet."""
    if port is None:
        raise InvalidConfigurationError(
            "Runze device configuration is missing a 'port' entry."
        )
    existing = _shared_io_instances.get(port)
    if existing is not None:
        return existing
    io = RunzeSerialIO.from_config(io_config)
    _shared_io_instances[port] = io
    return io


class RunzeValveHeads(Enum):
    """5 different valve types can be used. 6, 8, 10, 12, 16 multi-position valves."""

    SIX_PORT_SIX_POSITION = "6"
    EIGHT_PORT_EIGHT_POSITION = "8"
    TEN_PORT_TEN_POSITION = "10"
    TWELVE_PORT_TWELVE_POSITION = "12"
    SIXTEEN_PORT_SIXTEEN_POSITION = "16"


async def detect_valve_type(
    set_position_fn: Callable[..., Awaitable[bool]],
) -> RunzeValveHeads:
    """Detect the attached valve head by probing possible port counts.

    Shared by `RunzeValve` and `RunzeSyringePump`, whose built-in valve uses the
    identical 0x44 position command. `set_position_fn` is a
    `set_raw_position(position: str, raise_errors: bool) -> bool` coroutine.
    """
    # Probed largest-to-smallest: a candidate only succeeds if it's a valid
    # port number for the attached valve (i.e. <= its real port count), so
    # the FIRST success reached is the real count -- stop there. Anything
    # smaller would also report success (still a valid port on a bigger
    # valve), so continuing past the first hit would just overwrite the
    # correct answer with an undercount.
    possible_ports = [16, 12, 10, 8, 6]
    valve_type = None

    for value in possible_ports:
        success = await set_position_fn(str(value), raise_errors=False)
        if success:
            valve_type = value
            break

    if valve_type is None:
        logger.error("Failed to recognize the valve type: no successful port value.")
        raise ValueError("Unable to recognize the valve type. All port values failed.")

    return RunzeValveHeads(str(valve_type))


async def send_and_await_completion(
    send_fn: Callable[[], Awaitable[tuple[str, str]]],
    poll_status_fn: Callable[[], Awaitable[str]],
    raise_errors: bool = True,
    poll_interval: float = 0.2,
    max_wait: float = 60.0,
) -> tuple[str, str]:
    """Send a command and, if needed, poll until the device reports it done.

    Per the vendor manuals, `0x44` (valve move) and `0x45` (pump reset/home)
    may reply immediately with status `fe` ("task suspending") or `04`
    ("motor busy") rather than blocking until the physical move is
    complete -- completion must then be discovered separately by polling
    `0x4a` (motor status) until it returns `00`. This helper implements that
    documented `fe`/`04` -> poll `0x4a` -> `00` sequence so callers (valve and
    pump `set_raw_position`, pump `home`) don't have to duplicate it.

    `send_fn` and `poll_status_fn` must not raise on a non-`00` status --
    this helper needs to see `fe`/`04` to know to keep polling, so callers
    must invoke their underlying command with `raise_errors=False` and let
    this helper make the final raise/reject decision.
    """
    status, parameters = await send_fn()
    elapsed = 0.0
    while status in ("fe", "04") and elapsed < max_wait:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        status = await poll_status_fn()

    if status == "00":
        return status, parameters

    message = STATUS_MESSAGES.get(status, "Unknown status code")
    logger.error(f"{message} (Status code: {status})")
    if raise_errors:
        raise DeviceError(f"{message} - Check command syntax or device status!")
    return status, parameters
