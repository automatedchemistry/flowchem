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
import time
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
# Consecutive unanswered 0x4a polls tolerated by `await_completion` before
# giving up -- each one already costs a full serial read timeout.
MAX_MISSED_POLLS = 3


class RunzeCommunicationError(InvalidConfigurationError):
    """No complete, valid reply was received for a Runze exchange."""


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
                f"{base_command}{checksum & 0xFF:02X}{(checksum >> 8) & 0xFF:02X}"
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
        """Find a valid reply for this slave within one exchange deadline.

        Everything runs on `_io_executor`'s single thread, including frame
        recovery, so another slave's exchange cannot interrupt this one.
        """
        original_timeout = self._serial.timeout
        exchange_timeout = original_timeout if read_timeout is None else read_timeout
        deadline = (
            None if exchange_timeout is None else time.monotonic() + exchange_timeout
        )
        expected_address = command_bytes[1]
        context = (
            f"Runze address {expected_address}, command 0x{command_bytes[2]:02x}, "
            f"port {getattr(self._serial, 'port', '<unknown>')}"
        )
        buffer = bytearray()
        first_read = True
        try:
            self._serial.reset_input_buffer()
            while True:
                # A frame can be fragmented across reads, preceded by garbage,
                # or be a late reply from another slave on the shared bus.
                while buffer:
                    header = buffer.find(b"\xcc")
                    if header != 0:
                        discarded = len(buffer) if header < 0 else header
                        logger.warning(
                            f"{context}: discarding {discarded} bytes before a reply header: {buffer[:discarded].hex()}"
                        )
                        del buffer[:discarded]
                    if len(buffer) < REPLY_FRAME_BYTES:
                        break
                    frame = bytes(buffer[:REPLY_FRAME_BYTES])
                    try:
                        self._validate_reply_frame(frame)
                    except RunzeCommunicationError as error:
                        logger.warning(f"{context}: discarding invalid reply: {error}")
                        # Search again one byte later: a new frame may start
                        # inside a corrupted candidate's eight-byte window.
                        del buffer[0]
                        continue
                    if frame[1] != expected_address:
                        logger.warning(
                            f"{context}: discarding reply for address {frame[1]}: {frame.hex()}"
                        )
                        del buffer[:REPLY_FRAME_BYTES]
                        continue
                    return frame

                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 and not first_read:
                        break
                    # timeout=0 retains one nonblocking read attempt. Every
                    # other finite exchange shares the original time budget.
                    if remaining <= 0 and exchange_timeout != 0:
                        break
                    self._serial.timeout = max(0.0, remaining)
                else:
                    self._serial.timeout = None
                if first_read:
                    # On Windows, setting timeout reconfigures the COM port.
                    # Do it before TX: reconfiguration immediately after a
                    # write can interrupt the command on FTDI adapters.
                    self._serial.write(command_bytes)
                first_read = False
                reply = self._serial.read(max(1, REPLY_FRAME_BYTES - len(buffer)))
                if not reply:
                    break
                buffer.extend(reply)

            suffix = f" Partial reply: {buffer.hex()}." if buffer else ""
            raise RunzeCommunicationError(
                f"No valid reply received from {context}; completion is unknown.{suffix}"
            )
        finally:
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
        return self.parse_response(
            response=reply_bytes.hex(),
            raise_errors=raise_errors,
            expected_address=command.address,
        )

    @staticmethod
    def _validate_reply_frame(
        frame: bytes, expected_address: int | None = None
    ) -> None:
        """Validate framing and checksum before interpreting a reply's status."""
        if len(frame) != REPLY_FRAME_BYTES:
            raise RunzeCommunicationError(
                f"Expected {REPLY_FRAME_BYTES} reply bytes, received {len(frame)}: {frame.hex()}"
            )
        if frame[0] != 0xCC or frame[5] != 0xDD:
            raise RunzeCommunicationError(f"Invalid reply header/end: {frame.hex()}")
        expected_checksum = sum(frame[:6]) & 0xFFFF
        if int.from_bytes(frame[6:8], "little") != expected_checksum:
            raise RunzeCommunicationError(f"Invalid reply checksum: {frame.hex()}")
        if expected_address is not None and frame[1] != expected_address:
            raise RunzeCommunicationError(
                f"Reply address {frame[1]} does not match address {expected_address}: {frame.hex()}"
            )

    @staticmethod
    def parse_response(
        response: str,
        raise_errors: bool = True,
        expected_address: int | None = None,
    ) -> tuple[str, str]:
        """Split a received frame in its components: status, parameter.

        The parameter field (`B3,B4` in the manual) is a 2-byte
        little-endian value -- both bytes are combined here (previously only
        the low byte was read, silently truncating any value >= 256, which
        corrupts position reads almost immediately into any real pump move).
        """
        try:
            frame = bytes.fromhex(response)
        except ValueError as error:
            raise RunzeCommunicationError(
                f"Invalid hexadecimal reply: {response}"
            ) from error
        RunzeSerialIO._validate_reply_frame(frame, expected_address)
        # Reply byte 2 is a status, not an echo of the command code. The
        # protocol has no transaction identifier for matching same-slave replies.
        status = f"{frame[2]:02x}"
        parameters = f"{int.from_bytes(frame[3:5], 'little'):04x}"

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
    max_missed_polls: int | None = MAX_MISSED_POLLS,
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

    `max_missed_polls=None` retries unavailable status replies until `max_wait`
    expires; otherwise consecutive misses are also bounded by that count.
    """
    try:
        status, parameters = await send_fn()
    except RunzeCommunicationError as error:
        logger.warning(f"Command reply unavailable; completion is unknown: {error}")
        if raise_errors:
            raise
        return "ff", "0000"
    return await await_completion(
        status,
        parameters,
        poll_status_fn,
        raise_errors,
        poll_interval,
        max_wait,
        max_missed_polls,
    )


async def await_completion(
    status: str,
    parameters: str,
    poll_status_fn: Callable[[], Awaitable[str]],
    raise_errors: bool = True,
    poll_interval: float = 0.2,
    max_wait: float = 60.0,
    max_missed_polls: int | None = MAX_MISSED_POLLS,
) -> tuple[str, str]:
    """Second half of `send_and_await_completion`, for a reply already in hand.

    Polls `poll_status_fn` (0x4a) while `status` is `fe`/`04`, then raises or
    rejects exactly like `send_and_await_completion`. Split out for callers
    that must first decide for themselves whether a command's initial reply
    means "accepted, still running" -- see `RunzeSyringePump._send_move_and_wait`.

    The deadline includes status exchanges and serial-bus waits. An already
    running poll may finish after it and still confirm completion; a new poll
    is never started after expiry.
    """
    deadline = time.monotonic() + max_wait
    missed_polls = 0
    last_communication_error: RunzeCommunicationError | None = None
    while status in ("fe", "04"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(poll_interval, remaining))
        if time.monotonic() >= deadline:
            break
        try:
            status = await poll_status_fn()
        except RunzeCommunicationError as error:
            # Only read-only status queries are retried. Never resend a
            # movement whose missing reply leaves its execution uncertain.
            missed_polls += 1
            last_communication_error = error
            count = (
                str(missed_polls)
                if max_missed_polls is None
                else f"{missed_polls}/{max_missed_polls}"
            )
            logger.warning(
                f"Status reply unavailable ({count}); completion is unknown: {error}"
            )
            if max_missed_polls is not None and missed_polls >= max_missed_polls:
                if raise_errors:
                    raise
                return status, parameters
            continue
        missed_polls = 0
        last_communication_error = None

    if status == "00":
        return status, parameters

    if last_communication_error is not None:
        message = (
            f"Completion could not be confirmed within {max_wait:g}s; "
            f"last motor status was {status}: {last_communication_error}"
        )
        logger.warning(message)
        if raise_errors:
            raise RunzeCommunicationError(message) from last_communication_error
        return status, parameters

    message = STATUS_MESSAGES.get(status, "Unknown status code")
    if raise_errors:
        logger.error(f"{message} (Status code: {status})")
        raise DeviceError(f"{message} - Check command syntax or device status!")
    # raise_errors=False means the caller expects/tolerates this outcome (e.g.
    # detect_valve_type probing candidate port counts one by one) -- logging
    # at ERROR here would misreport routine, by-design rejections as failures.
    logger.debug(f"{message} (Status code: {status})")
    return status, parameters
