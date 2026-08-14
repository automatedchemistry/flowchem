"""Control module for the Vapourtec eBPR."""

from __future__ import annotations

from collections import namedtuple

import aioserial
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vapourtec.ebpr_component_control import EBPRPressureControl
from flowchem.utils.exceptions import InvalidConfigurationError

try:
    # noinspection PyUnresolvedReferences
    from flowchem_vapourtec import VapourtecEBPRCommands

    HAS_VAPOURTEC_COMMANDS = True
except ImportError:
    HAS_VAPOURTEC_COMMANDS = False


class EBPR(FlowchemDevice):
    """Vapourtec eBPR back pressure regulator control class."""

    DEFAULT_CONFIG = {
        "timeout": 1.0,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    Status = namedtuple("Status", "control_on, temperature, pressure, setpoint, duty")

    def __init__(self, name: str = "", **config) -> None:
        super().__init__(name)

        if not HAS_VAPOURTEC_COMMANDS:
            msg = (
                "You tried to use a Vapourtec device but the relevant commands are missing!"
                "Unfortunately, we cannot publish those as they were provided under NDA."
                "Contact Vapourtec for further assistance."
            )
            raise InvalidConfigurationError(msg)

        self.cmd = VapourtecEBPRCommands()

        # Merge default settings, including serial, with provided ones.
        configuration = EBPR.DEFAULT_CONFIG | config
        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as ex:
            msg = f"Cannot connect to the eBPR on the port <{config.get('port')}>"
            raise InvalidConfigurationError(msg) from ex

        self.device_info = DeviceInfo(
            manufacturer="Vapourtec",
            model="eBPR",
        )

    async def initialize(self):
        """Ensure connection."""
        self.device_info.version = await self.version()
        logger.info(f"Connected with eBPR version {self.device_info.version}")
        self.components.append(EBPRPressureControl("pressure", self))

    async def _write(self, command: str):
        """Write a command to the eBPR."""
        cmd = command + "\r\n"
        await self._serial.write_async(cmd.encode("ascii"))
        logger.debug(f"Sent command: {command!r}")

    async def _read_reply(self) -> str:
        """Read the eBPR reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.debug(f"Reply received: {reply_string.decode('ascii').rstrip()}")
        return reply_string.decode("ascii")

    async def write_and_read_reply(self, command: str) -> str:
        """Send a command to the eBPR, read the reply and return it."""
        self._serial.reset_input_buffer()
        await self._write(command)
        response = await self._read_reply()

        if not response:
            msg = "No response received from eBPR!"
            raise InvalidConfigurationError(msg)

        return response.rstrip()

    async def version(self):
        """Get firmware version."""
        return await self.write_and_read_reply(self.cmd.VERSION)

    async def get_status(self) -> Status:
        """Get status: control state, temperature, pressure (bar), set point (mbar), duty."""
        raw = await self.write_and_read_reply(self.cmd.GET_STATUS)
        control_on, temperature, pressure, setpoint, duty = (
            v.strip() for v in raw.split(",")
        )
        return EBPR.Status(control_on == "1", temperature, pressure, setpoint, duty)

    async def get_pressure(self) -> float:
        """Get the current pressure in bar."""
        return float((await self.get_status()).pressure)

    async def set_pressure(self, pressure_mbar: float):
        """Set the pressure set point in mbar."""
        cmd = self.cmd.SET_PRESSURE.format(pressure_mbar=round(pressure_mbar))
        await self.write_and_read_reply(cmd)

    async def power_on(self):
        """Turn on pressure control."""
        await self.write_and_read_reply(self.cmd.POWER_ON)

    async def power_off(self):
        """Turn off pressure control."""
        await self.write_and_read_reply(self.cmd.POWER_OFF)
