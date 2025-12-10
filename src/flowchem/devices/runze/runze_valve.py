"""Runze SV-06 multiposition distribution valve control."""

from enum import Enum
from dataclasses import dataclass
from loguru import logger
import aioserial

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.runze.runze_valve_component import (
    Runze6PortDistributionValve,
    Runze8PortDistributionValve,
    Runze10PortDistributionValve,
    Runze12PortDistributionValve,
    Runze16PortDistributionValve,
)
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import miguel
from flowchem.utils.exceptions import InvalidConfigurationError


class RunzeValveHeads(Enum):
    """5 different valve types can be used. 6, 8, 10, 12, 16 multi-position valves."""

    SIX_PORT_SIX_POSITION = "6"
    EIGHT_PORT_EIGHT_POSITION = "8"
    TEN_PORT_TEN_POSITION = "10"
    TWELVE_PORT_TWELVE_POSITION = "12"
    SIXTEEN_PORT_SIXTEEN_POSITION = "16"


@dataclass
class SV06Command:
    """Class representing a command for the SV-06 Multiport Selector Valve."""

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
                f"{self.parameter & 0xFF:02X}"             # Low byte of parameter
                f"{(self.parameter >> 8) & 0xFF:02X}"      # High byte of parameter
                f"{self.FRAME_END}"                        # Frame End
            )
            checksum = sum(int(base_command[i:i+2], 16) for i in range(0, len(base_command), 2)) & 0xFFFF
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"                   # Low byte of checksum
                f"{(checksum >> 8) & 0xFF:02X}"            # High byte of checksum
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
            checksum = sum(int(base_command[i:i+2], 16) for i in range(0, len(base_command), 2)) & 0xFFFF
            compiled_command = (
                f"{base_command}"
                f"{checksum & 0xFF:02X}"
                f"{(checksum >> 8) & 0xFF:02X}"
            )

        return compiled_command


class RunzeValveIO:
    """Setup with serial parameters, low-level IO for SV-06 Multiport Selector Valve."""

    DEFAULT_CONFIG = {
        "timeout": 1,
        "baudrate": 57600,  #The corresponding baudrate can be set through a factory command
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, aio_port: aioserial.AioSerial) -> None:
        """Initialize serial port for SV-06 valve."""
        self._serial = aio_port

    @classmethod
    def from_config(cls, config):
        """Create RunzeValveIO from config."""
        # Combine the default configuration with the user provided configuration
        configuration = RunzeValveIO.DEFAULT_CONFIG | config

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the valve on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)

    async def _write_async(self, command: bytes):
        """Write a command to the valve."""
        await self._serial.write_async(command)

    async def _read_reply_async(self) -> str:
        """Read the valve reply from serial communication."""
        reply_string = await self._serial.readline_async()
        return reply_string.hex()

    async def write_and_read_reply_async(self, command: SV06Command, raise_errors: bool = True) -> tuple[str,str]:
        """Send a command to the valve, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write_async(bytes.fromhex(f"{command.compile()}\r"))
        response = await self._read_reply_async()
        if not response:
            raise InvalidConfigurationError(
                f"No response received from valve! "
                f"Maybe wrong valve address? (Set to {command.address})"
            )
        return self.parse_response(response=response, raise_errors=raise_errors)

    @staticmethod
    def parse_response(response: str, raise_errors: bool = True) -> tuple[str,str]:
        """Split a received line in its components: status, reply."""
        status, parameters = response[4:6], response[6:8]

        status_strings = {
            "00": "Normal status",
            "01": "Frame error",
            "02": "Parameter error",
            "03": "Optocoupler error",
            "04": "Motor busy",
            "05": "Motor stalled",
            "06": "Unknown location",
            "fe": "Task being executed",
            "ff": "Unknown error"
        }

        status_string = status_strings.get(status, "Unknown status code")
        # Check if the status indicates an error
        if status in ("01", "02", "03","04", "05", "06", "fe", "ff"):
            if raise_errors:
                logger.error(f"{status_string} (Status code: {status})")
                raise DeviceError(
                    f"{status_string} - Check command syntax or device status!"
                )
        return status, parameters


class RunzeValve(FlowchemDevice):
    """
    Control Runze multi position valves.
    """
    _io_instances: set[RunzeValveIO] = set()

    def __init__(
        self,
        valve_io: RunzeValveIO,
        name: str,
        address: int = 1,
    ) -> None:
        super().__init__(name)

        # Create communication
        self.valve_io = valve_io
        RunzeValve._io_instances.add(self.valve_io)

        self.address = address

        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Runze",
            model="SV-06",
        )

    async def initialize(self):
        await super().initialize()

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        valve_component: FlowchemComponent
        match self.device_info.additional_info["valve-type"]:
            case RunzeValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Runze6PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.EIGHT_PORT_EIGHT_POSITION:
                valve_component = Runze8PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TEN_PORT_TEN_POSITION:
                valve_component = Runze10PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Runze12PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Runze16PortDistributionValve(
                    "distribution-valve", self
                )
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    async def get_valve_type(self):
        """Get valve type by testing possible port values."""  # There was no command for this

        possible_ports = [16, 12, 10, 8, 6]
        valve_type = None

        for value in possible_ports:
            success = await self.set_raw_position(str(value), raise_errors=False)

            if success:
                # Update the last successful value if the command succeeded
                valve_type = value
            else:
                if valve_type is None:
                    logger.error("Failed to recognize the valve type: no successful port value.")
                    raise ValueError("Unable to recognize the valve type. All port values failed.")
                break

        return RunzeValveHeads(str(valve_type))

    async def _send_command_and_read_reply(
            self,
            command: str,
            parameter: int = 0,
            raise_errors: bool = True,
            is_factory_command: bool =False,
    ):
        valve_command = SV06Command(
            function_code=command,
            address=self.address,
            parameter=parameter,
            is_factory_command=is_factory_command,
        )
        status, parameters = await self.valve_io.write_and_read_reply_async(valve_command, raise_errors)
        return status, parameters

    async def get_raw_position(self, raise_errors: bool = False) -> str:
        """Return current valve position, following valve nomenclature."""
        status, parameters = await self._send_command_and_read_reply(command="3e", raise_errors=raise_errors)
        if status == "00":
            logger.info(f"Current valve position is: {parameters}")
            return parameters
        else:
            logger.warning(f"Something is not working in the valve. "
                           f"Attempt to get raw position returned status: '{status}'.")
            return ""

    async def set_raw_position(self, position: str, raise_errors: bool = True) -> bool:
        """Set valve position, following valve nomenclature."""
        status, parameters = await self._send_command_and_read_reply(
            command="44",
            parameter=int(position),
            raise_errors=raise_errors)
        if status == "00":
            logger.info(f"Valve position set to: {parameters}")
            return True
        else:
            return False

    async def set_address(self, address: int) -> str:
        status, parameters = await self._send_command_and_read_reply(command="00", parameter=address, is_factory_command=True)
        if status == "00":
            self.address = address
        return status

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        valveio = None
        for obj in RunzeValve._io_instances:
            # noinspection PyProtectedMember
            if obj._serial.port == config.get("port"):
                valveio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if valveio is None:
            # Remove RunzeValve-specific keys to only have RunzeValveIO's configs
            config_for_valveio = {
                k: v
                for k, v in config.items()
                if k not in ("address", "name")
            }
            valveio = RunzeValveIO.from_config(config_for_valveio)

        return cls(
            valveio,
            address=config.get("address", 1),
            name=config.get("name", ""),
        )


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM5",
        "address": 1,
        "name": "runze_test",
    }
    v = RunzeValve.from_config(**conf)

    async def main(valve):
        """Test function."""
        await valve.initialize()
        #response = await valve.get_current_address()

    asyncio.run(main(v))
