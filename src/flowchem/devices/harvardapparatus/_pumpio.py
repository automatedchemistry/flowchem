import asyncio
from dataclasses import dataclass
from enum import Enum

import aioserial
from loguru import logger

from flowchem.utils.exceptions import DeviceError, InvalidConfigurationError


class PumpStatus(Enum):
    """Possible pump statuses, as defined by the reply prompt."""

    IDLE = ":"
    INFUSING = ">"
    WITHDRAWING = "<"
    TARGET_REACHED = "T"
    STALLED = "*"


@dataclass
class Protocol11Command:
    """Class representing a pump command."""

    command: str
    pump_address: int
    arguments: str


class HarvardApparatusPumpIO:
    """Setup with serial parameters, low level IO."""

    DEFAULT_CONFIG = {"timeout": 0.1, "baudrate": 115200}

    def __init__(self, port: str, **kwargs) -> None:
        # Merge default settings, including serial, with provided ones.
        configuration = dict(HarvardApparatusPumpIO.DEFAULT_CONFIG, **kwargs)

        self.lock = asyncio.Lock()

        try:
            self._serial = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            logger.error(f"Cannot connect to the Pump on the port <{port}> issue:{serial_exception}")
            raise InvalidConfigurationError(
                f"Cannot connect to the Pump on the port <{port}>"
            ) from serial_exception

    async def _write(self, command: Protocol11Command):
        """Write a command to the pump."""
        command_msg = f"{command.pump_address}{command.command} {command.arguments}\r\n"

        try:
            await self._serial.write_async(command_msg.encode("ascii"))
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError from serial_exception
        logger.debug(f"Sent {command_msg!r}!")

    async def _read_reply(self) -> list[str]:
        """Read the pump reply from serial communication."""
        reply_string = []

        for line in await self._serial.readlines_async():
            reply_string.append(line.decode("ascii").strip())
            logger.debug(f"Received {line!r}!")

        # First line is usually empty, but some prompts such as T* actually leak into this line sometimes.
        reply_string.pop(0)
        return [x for x in reply_string if x]  # remove empty strings from reply_string

    @staticmethod
    def parse_response_line(line: str) -> tuple[int, PumpStatus, str]:
        """Split a received line in its components: address, prompt and reply body."""
        assert len(line) >= 3
        pump_address, status = int(line[0:2]), PumpStatus(line[2:3])

        # Target reached is the only two-character status
        if status is PumpStatus.TARGET_REACHED:
            return pump_address, status, line[4:]
        return pump_address, status, line[3:]

    @staticmethod
    def parse_response(
        response: list[str],
    ) -> tuple[list[int], list[PumpStatus], list[str]]:
        """Aggregate address prompt and reply body from all the reply lines and return them."""
        parsed_lines = list(map(HarvardApparatusPumpIO.parse_response_line, response))
        return zip(*parsed_lines, strict=True)  # type: ignore

    @staticmethod
    def check_for_errors(response_line, command_sent):
        """Further response parsing, checks for error messages."""
        error_string = (
            "Command error",
            "Unknown command",
            "Argument error",
            "Out of range",
        )
        if any(e in response_line for e in error_string):
            logger.error(
                f"Error for command {command_sent} on pump {command_sent.pump_address}!"
                f"Reply: {response_line}",
            )
            raise DeviceError("Command error")

    async def write_and_read_reply(
        self,
        command: Protocol11Command,
        return_parsed: bool = True,
    ) -> list[str]:
        """Send a command to the pump, read the replies and return it, optionally parsed.

        If unparsed reply is a List[str] with raw replies.
        If parsed reply is a List[str] w/ reply body (address and prompt removed from each line).
        """
        async with self.lock:
            self._serial.reset_input_buffer()
            await self._write(command)
            response = await self._read_reply()

        if not response:
            logger.error("No reply received from pump!")
            raise InvalidConfigurationError(
                "No response received. Is the address right?"
            )

        pump_address, status, parsed_response = self.parse_response(response)

        # All the replies came from the target pump
        assert all(address == command.pump_address for address in pump_address)

        # No stall reply is present
        if PumpStatus.STALLED in status:
            logger.error("Pump stalled!")
            raise DeviceError("Pump stalled! Press display on pump to clear error :(")

        # Check for error in the last response line
        self.check_for_errors(response_line=response[-1], command_sent=command)
        return parsed_response if return_parsed else response

    def autodiscover_address(self) -> int:
        """Autodiscover pump address based on response received."""
        self._serial.write(b"\r\n")
        self._serial.readline()
        prompt = self._serial.readline()
        valid_status = [status.value for status in PumpStatus]
        address = 0 if prompt[0:2].decode() in valid_status else int(prompt[0:2])
        logger.debug(f"Address detected as {address}")
        return address
