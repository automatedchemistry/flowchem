""" Control module for Eletronic Switch Box develop by MPIKG (Eletronic Lab) """
from __future__ import annotations

from flowchem.devices.custom.mpikg_switch_box_component import SwicthBoxMPIKGComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva

from dataclasses import dataclass, field
from loguru import logger
from enum import StrEnum
import aioserial
import asyncio

from scipy.stats import variation

BEFE_RELE_BITS = 16
ADC_VOLTS = 5
DAC_BITS = 12
DAC_VOLTS = 10

def bit_to_int(bits: list[int]) -> int:
    return int("".join(str(b) for b in bits), 2)

def int_to_bit_list(value: int, length: int = 16) -> list[int]:
    bits = list(map(int, bin(value)[2:]))  # convert to binary string, strip "0b", then to list of ints
    if length is not None:  # pad with leading zeros if length is given
        bits = [0] * (length - len(bits)) + bits
    return bits


class SwicthBoxException(Exception):
    """ General Swicth Box exception """
    pass


class InvalidConfiguration(SwicthBoxException):
    """ Used for failure in the serial communication """
    pass


class InfRequest(StrEnum):
    GET = "get"
    SET = "set"


class VaribleType(StrEnum):
    # --------------------------------------------------<\r>
    # <\n>- help or ?         -> Show this page<\r>
    # <\n>- reset             -> reset the Device (softreset)<\r>
    # <\n><\r>
    # <\n>------    ADC/DAC Commands        ----------<\r>
    # <\n>- set dac1:x        -> set Dac1 (x:0-4095)(0-10V)<\r>
    # <\n>- set dac2:x        -> set Dac2 (x:0-4095)(0-10V)<\r>
    # <\n>- get dac1          -> get Dac1 value (0-4095)<\r>
    # <\n>- get dac2          -> get Dac2 value (0-4095)<\r>
    # <\n><\r>
    # <\n>--------------------------------------------<\r>
    # <\n>- get adcx          -> get ADC0..ADC7 value (0-5 Volt)<\r>
    # <\n>- get adc0          -> get ADC0 value (0-5 Volt)<\r>
    # <\n>- get adc1          -> get ADC1 value (0-5 Volt)<\r>
    # <\n>- get adc2          -> get ADC2 value (0-5 Volt)<\r>
    # <\n>- get adc3          -> get ADC3 value (0-5 Volt)<\r>
    # <\n>- get adc4          -> get ADC4 value (0-5 Volt)<\r>
    # <\n>- get adc5          -> get ADC5 value (0-5 Volt)<\r>
    # <\n>- get adc6          -> get ADC6 value (0-5 Volt)<\r>
    # <\n>- get adc7          -> get ADC7 value (0-5 Volt)<\r>
    # <\n><\r>
    # <\n>- get ver           -> Shows programversion<\r>
    # <\n>- test on           -> Hardware test ON<\r>
    # <\n>- test off          -> Hardware test OFF<\r>
    # <\n>----------------------------------------------

    VERSION = "ver"

    # ------  ADC/DAC Commands  ------
    ADC = "adc"
    DAC = "dac"  # (0-4095)(0-10V)


class BefhelePorts(StrEnum):
    # <\n>-------   Port Befehle   ----------------------<\r>
    # <\n>- set a:x           -> set PortA Byte Decimal(x:0-65535)<\r>
    # <\n>- set b:x           -> set PortB Byte Decimal(x:0-65535)<\r>
    # <\n>- set c:x           -> set PortC Byte Decimal(x:0-65535)<\r>
    # <\n>- set d:x           -> set PortD Byte Decimal(x:0-65535)<\r>
    # <\n>- set abcd:a,b,c,d  -> set Ports A,B,C und D<\r>
    # <\n>- get abcd          -> get Ports A,B,C und D<\r>
    # <\n>- get a             -> get PortA Byte Decimal<\r>
    # <\n>- get b             -> get PortB Byte Decimal<\r>
    # <\n>- get c             -> get PortC Byte Decimal<\r>
    # <\n>- get d             -> get PortD Byte Decimal<\r>
    # <\n>- set starta:x      -> set PortA Startwert (x:0-65535)<\r>
    # <\n>- set startb:x      -> set PortB Startwert (x:0-65535)<\r>
    # <\n>- set startc:x      -> set PortC Startwert (x:0-65535)<\r>
    # <\n>- set startd:x      -> set PortD Startwert (x:0-65535)<\r>
    # <\n>- get starta        -> get PortA Startwert Decimal<\r>
    # <\n>- get startb        -> get PortB Startwert Decimal<\r>
    # <\n>- get startc        -> get PortC Startwert Decimal<\r>
    # <\n>- get startd        -> get PortC Startwert Decimal<\r>
    # <\n><\r>
    # -------   Port Befehle   -------
    # PortX Byte Decimal(x:0-65535)
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    ABCD = "abcd"
    START_A = "starta"
    START_B = "startb"
    START_C = "startc"
    START_D = "startd"


@dataclass
class SwitchBoxBefehleCommand:
    """ Class representing a box command for Befehele Ports and its expected reply """
    request: InfRequest = InfRequest.SET
    port: BefhelePorts = BefhelePorts.A
    bitsnumber: int = 0
    bitsnumber_list: list[int] = field(default_factory=list)

    def compile(self) -> bytes:
        if self.request == InfRequest.SET:
            if self.port == BefhelePorts.ABCD:
                command = f"{self.request} {self.port}:"
                for bits in self.bitsnumber_list:
                    command += f"{bits},"
                command = command[:-1]
            else:
                command = f"{self.request} {self.port}:{self.bitsnumber}"
        elif self.request == InfRequest.GET:
            command = f"{self.request} {self.port}"
        return f"{command}\r".encode()


@dataclass
class SwitchBoxGeneralCommand:
    """ Class representing a box command ADC/DAC Commands and its expected reply """
    channel: int = 0
    request: InfRequest = InfRequest.SET
    variable: VaribleType = VaribleType.ADC
    reply_lines: int = 1
    value: int = 0

    def compile(self)->bytes:
        """
        Create actual command byte by prepending box address to command.
        """
        if self.request == InfRequest.SET:
            if self.variable in {VaribleType.ADC, VaribleType.DAC}:
                command = f"{self.request} {self.variable}{self.channel}:{self.value}"
            else:
                command = f"{self.request} {self.variable}:{self.value}"
        else:
            if self.variable in {VaribleType.ADC, VaribleType.DAC}:
                command = f"{self.request} {self.variable}{self.channel}"
            else:
                command = f"{self.request} {self.variable}"
        return f"{command}\r".encode()


class SwicthBoxIO:
    """ Setup with serial parameters, low level IO"""

    DEFAULT_CONFIG = {
        "timeout": 1,
        "baudrate": 57600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    # noinspection PyPep8
    def __init__(self, aio_port: aioserial.Serial):
        """Initialize communication on the serial port where the Box is connected.

        Args:
        ----
            aio_port: aioserial.Serial() object
        """
        self.lock = asyncio.Lock()
        self._serial = aio_port

    @classmethod
    def from_config(cls, port, **serial_kwargs):
        """Create SwicthBoxIO from config."""
        # Merge default serial settings with provided ones.
        configuration = dict(SwicthBoxIO.DEFAULT_CONFIG, **serial_kwargs)

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfiguration(
                f"Could not open serial port {port} with configuration {configuration}"
            ) from serial_exception

        return cls(serial_object)

    async def _write(self, command: SwitchBoxCommand):
        """ Writes a command to the box """
        command_compiled = command.compile()
        logger.debug(f"Sending {command_compiled!r}")
        try:
            await self._serial.write_async(command_compiled)
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

    async def _read_reply(self, command) -> str:
        """ Reads the box reply from serial communication """
        logger.debug(
            f"I am going to read {command.reply_lines} line for this command (+prompt)"
        )
        reply_string = ""

        for line_num in range(
            command.reply_lines + 2
        ):  # +1 for leading newline character in reply + 1 for prompt
            chunk = await self._serial.readline_async(200)
            logger.debug(f"Read line: {repr(chunk)} ")
            chunk = chunk.decode("ascii")
            # Stripping newlines etc allows to skip empty lines and clean output
            chunk = chunk.strip()

            if chunk:
                reply_string += chunk

        logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        try:
            self._serial.reset_input_buffer()
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e

    async def write_and_read_reply(
        self, command: SwitchBoxCommand
    ) -> str:
        """ Main SwicthBocIO method. Sends a command to the box, read the replies and returns it, optionally parsed """
        async with self.lock:
            self.reset_buffer()
            await self._write(command)
            response = await self._read_reply(command)

        if not response:
            raise InvalidConfiguration(
                "No response received from box, check port address!"
            )
        if response.startswith("ERROR"):
            logger.error(f"Error in the command '{command}' sent to the Swicth Box")
        return response


class SwitchBoxMPIKG(FlowchemDevice):
    """ Swicth Box MPIKG module class """
    def __init__(
            self,
            box_io: SwicthBoxIO,
            name: str = ""
    ) -> None:
        super().__init__(name)
        self.box_io = box_io
        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Custom",
            model="Custom",
        )

    @classmethod
    def from_config(
            cls,
            port: str,
            name: str = "",
            **serial_kwargs,
    ):
        swicth_io = SwicthBoxIO.from_config(port, **serial_kwargs)

        return cls(box_io=swicth_io, name=name)

    async def initialize(self):
        self.device_info.version = await self.box_io.write_and_read_reply(
            command=SwitchBoxCommand(request=InfRequest.GET,
                                     variable=VaribleType.VERSION)
        )
        self.components.append(SwicthBoxMPIKGComponent("box", self))
        logger.info(
            f"Connected to SwitchBoxMPIKG on port {self.box_io._serial.port}!")

    """ Port Befehle """

    async def set_hele_port(
            self,
            values: list[int],
            switch_to_low_after: float = -1,
            port: str = "a"
    ):

        # verify values
        if any(c not in [0, 1, 2] for c in values):
            logger.error("Values should be in [0, 1, 2]")
            return False
        if len(values) > 8:
            logger.error(f"Port only have 8 channels - It was provide {len(values)}!")
            return False
        while len(values) < 8:
            values.append(0)
        # verify port
        port = port.lower()
        if port not in BefhelePorts:
            logger.error(f"There is not port {port} in device {self.name}!")
            return False

        bits = [0] * BEFE_RELE_BITS  # channes 1 to 8
        for i, v in enumerate(values):
            if v == 2:
                """ Full power """
                bits[-(i - 1) - 8] = 1
                bits[-(i - 1)] = 1
            else:
                bits[-(i - 1) - 8] = v
                bits[-(i - 1)] = 0

        bitcommand = bit_to_int(bits)

        status = await self.box_io.write_and_read_reply(
            command=SwitchBoxBefehleCommand(port=port, request=InfRequest.SET, bitsnumber=bitcommand)
        )
        if not status.startswith("OK"):
            return False
        if switch_to_low_after > 0:
            for i, v in enumerate(values):
                if bits[-(i - 1) - 8] == 1:
                    bits[-(i - 1)] = 0

        asyncio.sleep(switch_to_low_after)

        bitcommand = bit_to_int(bits)
        status = await self.box_io.write_and_read_reply(
            command=SwitchBoxBefehleCommand(port=port, request=InfRequest.SET, bitsnumber=bitcommand)
        )
        return status.startswith("OK")

    async def set_hele_single_channel(
            self,
            channel: int,
            value: int = 2,
            keep_port_status = True,
            switch_to_low_after: float = -1
    ):
        channels = [i + 1 for i in range(8)]
        status = await self.get_hele_channel()
        if 0 < channel / 8 < 1:
            port = "A"
            ch = channel
        elif 1 < channel / 8 < 2:
            port = "B"
            ch = channel
        elif 1 < channel / 8 < 2:
            port = "C"
            ch = channel
        elif 1 < channel / 8 < 2:
            port = "D"
            ch = channel
        else:
            logger.error(f"There is not channel {channel} in device {self.name}!")
            return False

    async def get_hele_channel(self):
        asw = await self.box_io.write_and_read_reply(
            command=SwitchBoxCommand(port=BefhelePorts.ABCD, request=InfRequest.GET)
        )
        asw.replace(" ", "")
        result = {}
        for ports in asw.split(","):
            bitcommand = int_to_bit_list(int(ports.split(":")[1]))
            result[ports.split(":")[0].lower()] = bitcommand[:8] + bitcommand[8:]

    """ ADC/DAC Commands """

    async def get_adc(self):
        """ Analog  Digital Command """
        asw = await self.box_io.write_and_read_reply(
            command=SwitchBoxGeneralCommand(
                channel="x", request=InfRequest.GET, variable=VaribleType.ADC)
        )
        asw.replace(" ", "")
        result = {}
        for ports in asw.split(";"):
            bitcommand = int_to_bit_list(float(ports.split(":")[1]))
            result[ports.split(":")[0][1:].lower()] = bitcommand[:8] + bitcommand[8:]
        return result

    async def get_dac(self, channel: int = 1, volts: bool = True):
        asw = await self.box_io.write_and_read_reply(
            command=SwitchBoxGeneralCommand(channel=channel,
                                     request=InfRequest.GET,
                                     variable=VaribleType.DAC)
        )
        bit = int(asw.split(':')[-1])
        if volts:
            return DAC_BITS / bit * DAC_VOLTS

    async def set_dac(self, channel: int = 0, volts: float = 5):
        status = await self.box_io.write_and_read_reply(
            command=SwitchBoxCommand(channel=channel,
                                     request=InfRequest.SET,
                                     variable=VaribleType.DAC,
                                     value=int(value * DAC_BITS / DAC_VOLTS))
        )
        return status.startswith("OK")


if __name__ == "__main__":
    box = SwitchBoxMPIKG.from_config(port="COM8")

    async def main():
        """Test function."""
        await box.initialize()
        print(box.device_info.version)
        await box.set_channel(channel=1, value=True)
        value = await box.get_channel(channel=1)
        print(value)

    asyncio.run(main())