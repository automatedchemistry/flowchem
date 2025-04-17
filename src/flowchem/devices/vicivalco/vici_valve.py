"""This module is used to control Vici Valco Universal Electronic Actuators."""
from __future__ import annotations

from dataclasses import dataclass

import aioserial
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vicivalco.vici_valve_component import ViciInjectionValve
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin


@dataclass
class ViciCommand:
    """This class represent a command. Its bytes() method is transmitted to the valve."""

    command: str
    valve_id: int | None = None
    value: str = ""
    reply_lines: int = 1

    def __str__(self) -> str:
        """Provide a string representation of the command used, nice for logs."""
        address = str(self.valve_id) if self.valve_id is not None else ""
        return f"{address}{self.command}{self.value}\r"

    def __bytes__(self) -> bytes:
        """Byte representation of the command used for serial communication."""
        return str(self).encode("ascii")


class ViciValcoValveIO:
    """Setup with serial parameters, low level IO."""

    DEFAULT_CONFIG = {
        "timeout": 0.5,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.Serial) -> None:
        """Initialize communication on the serial port where the valves are located and initialize them.

        Args:
        ----
            aio_port: aioserial.Serial() object
        """
        self._serial = aio_port

    @classmethod
    def from_config(cls, port, **serial_kwargs):
        """Create ViciValcoValveIO from config."""
        # Merge default serial settings with provided ones.
        configuration = dict(ViciValcoValveIO.DEFAULT_CONFIG, **serial_kwargs)

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Could not open serial port {port} with configuration {configuration}"
            ) from serial_exception

        return cls(serial_object)

    async def _read_reply(self, lines: int) -> str:
        """Read the valve reply from serial communication."""
        reply_string = ""
        for _ in range(lines):
            line = await self._serial.readline_async()
            reply_string += line.decode("ascii")

        if reply_string:
            logger.debug(f"Reply received: {reply_string}")
        else:
            logger.error("No response received from valve! Check valve address?")
            raise InvalidConfigurationError(
                "No response received from valve! Check valve address?"
            )

        return reply_string.rstrip()

    async def write_and_read_reply(self, command: ViciCommand) -> str:
        """Write command to valve and read reply."""
        # Make sure input buffer is empty
        self._serial.reset_input_buffer()
        logger.debug(f"Command {bytes(command)} sent!")
        # Send command
        await self._serial.write_async(bytes(command))

        if command.reply_lines == 0:
            return ""
        else:
            return await self._read_reply(command.reply_lines)

    @property
    def name(self) -> str:
        """Provide a nice-looking default name to valve based on its serial connection."""
        try:
            return self._serial.name
        except AttributeError:
            return ""


class ViciValve(FlowchemDevice):
    """ViciValco injection valves."""

    # This class variable is used for daisy chains (i.e. multiple valves on the same serial connection). Details below.
    _io_instances: set[ViciValcoValveIO] = set()
    # When several valves are daisy-chained on the same serial port, they need to all access the *same* Serial object,
    # because access to the serial port is exclusive by definition.
    # The mutable object _io_instances as class variable creates a shared state across all the instances.

    def __init__(
        self,
        valve_io: ViciValcoValveIO,
        name: str = "",
        address: int | None = None,
    ) -> None:
        """Create instance from an existing ViciValcoValveIO object. This allows dependency injection.

        See from_config() class method for config-based init.

        Args:
        ----
            valve_io: An ViciValcoValveIO w/ serial connection to the daisy chain w/ target valve.
            address: number of valve in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        self.valve_io = valve_io
        ViciValve._io_instances.add(self.valve_io)

        # The valve name is used for logs and error messages.
        self.name = name if name else f"Valve {self.valve_io.name}:{address}"
        super().__init__(name=name)  # type: ignore

        self.address = address
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Vici-Valco",
            model="Universal Valve Actuator",
        )

    @classmethod
    def from_config(
        cls,
        port: str,
        address: int,
        name: str = "",
        **serial_kwargs,
    ):
        """Create instances via provided parameters to enable programmatic instantiation."""
        existing_io = [v for v in ViciValve._io_instances if v._serial.port == port]

        # If no existing serial object are available for the port provided, create a new one
        valve_io = (
            existing_io.pop()
            if existing_io
            else ViciValcoValveIO.from_config(port, **serial_kwargs)
        )

        return cls(valve_io, address=address, name=name)

    async def initialize(self):
        """Must be called after init before anything else."""
        # Learning positions is only needed if the valve head has been reinstalled.
        await self.learn_positions()

        # Homing implies moving to position 1.
        await self.home()

        # Test connectivity by querying the valve's firmware version
        self.device_info.version = await self.version()
        logger.info(f"Connected to {self.name} - FW ver.: {self.device_info.version}!")

        # Add component
        self.components.append(ViciInjectionValve("injection-valve", self))

    async def learn_positions(self) -> None:
        """Initialize valve only, there is no reply -> reply_lines = 0."""
        learn = ViciCommand(valve_id=self.address, command="LRN", reply_lines=0)
        await self.valve_io.write_and_read_reply(learn)

    async def home(self) -> None:
        """Initialize valve only: Move to Home position."""
        home = ViciCommand(valve_id=self.address, command="HM", reply_lines=0)
        await self.valve_io.write_and_read_reply(home)

        # This seems necessary to make sure move is finished
        await self.get_raw_position()

    async def version(self) -> str:
        """Return the current firmware version reported by the valve."""
        version = ViciCommand(valve_id=self.address, command="VR", reply_lines=0)  #todo: put back to 5
        return await self.valve_io.write_and_read_reply(version)

    async def get_raw_position(self) -> str:
        """Represent the position of the valve."""
        current_pos = ViciCommand(valve_id=self.address, command="CP", reply_lines=0)
        return await self.valve_io.write_and_read_reply(current_pos)

    async def set_raw_position(self, position: str):
        """Set valve position."""
        valve_by_name_cw = ViciCommand(
            valve_id=self.address,
            command="GO",
            value=position,
            reply_lines=0,
        )
        await self.valve_io.write_and_read_reply(valve_by_name_cw)

    async def timed_toggle(self, injection_time: str):
        """Switch valve to a position for a given time."""
        delay = ureg.Quantity(injection_time).to("ms")
        set_delay = ViciCommand(
            valve_id=self.address,
            command="DT",
            value=delay.magnitude,
            reply_lines=0
        )
        await self.valve_io.write_and_read_reply(set_delay)

        time_toggle = ViciCommand(valve_id=self.address, command="TT", reply_lines=0)
        await self.valve_io.write_and_read_reply(time_toggle)


if __name__ == "__main__":
    import asyncio

    async def main():
        valve1 = ViciValve.from_config(port="COM20", address=0, name="test1")
        await valve1.initialize()
        await valve1.timed_toggle("2500 ms")
    asyncio.run(main())

    # Set position works with both strings and InjectionValvePosition
    #asyncio.run(valve1.set_raw_position("2"))
