"""
Control module for Electronic Switch Box develop by MPIKG (Electronic Lab)

### Serial Commands to the box device

Port Befe helay

* These control the current state of the box’s 32 digital output lines, grouped into four “ports” (A, B, C, D).
* Each port is 16 bits wide (0–65535 decimal), and you can set or read them individually (a, b, c, d) or all at once (abcd).

| **Command** | **channel** | **Value**            | **return**           |
|-------------|-------------|----------------------|----------------------|
| set         | a           | 0-65535 Byte Decimal |                      |
| set         | b           | 0-65535 Byte Decimal |                      |
| set         | c           | 0-65535 Byte Decimal |                      |
| set         | d           | 0-65535 Byte Decimal |                      |
| set         | abcd        | 0-65535 Byte Decimal |                      |
| get         | a           |                      | 0-65535 Byte Decimal |
| get         | b           |                      | 0-65535 Byte Decimal |
| get         | c           |                      | 0-65535 Byte Decimal |
| get         | d           |                      | 0-65535 Byte Decimal |
| get         | abcd        |                      | 0-65535 Byte Decimal |

Example::
```shell
set a:65535  # Turns all 8 outputs in Port A ON
get b        # Reads the current 16-bit value of Port B
```

PortA Startwert
* These define the power-on default for each port (what state it should start in when the device is powered up or reset).\
* They are stored in the device’s memory.
* Same structure as the Port Commands table, but prefixed with start.

| **Command** | **channel** | **Value**            | **return**           |
|-------------|-------------|----------------------|----------------------|
| set         | starta      | 0-65535 Byte Decimal |                      |
| set         | startb      | 0-65535 Byte Decimal |                      |
| set         | startc      | 0-65535 Byte Decimal |                      |
| set         | startd      | 0-65535 Byte Decimal |                      |
| get         | starta      |                      | 0-65535 Byte Decimal |
| get         | startb      |                      | 0-65535 Byte Decimal |
| get         | startc      |                      | 0-65535 Byte Decimal |
| get         | startd      |                      | 0-65535 Byte Decimal |

Example::
```shell
set starta:65535
get startc
```

ADC (Analog-Digital) Commands

* Commands here are for analog outputs — setting a voltage from 0 to 10 V using a 12-bit value (0–4095).
* You can control each channel individually (x = 1–32).

| **Command** | **channel**   | **Value**      | **return** |
|-------------|---------------|----------------|------------|
| set         | dacx (x=1-32) | 0-4095 (0-10V) |            |
| get         | dacx (x=1-32) |                | 0-4095     |

DAC (Digital-Analog) Commands
* Commands read analog input voltages (0–5 V)
* Useful for monitoring sensor inputs connected to the box.

| **Command** | **channel** | **return** |
|-------------|-------------|------------|
| get         | dacx        | 0-5 Volt   |
| get         | dac0        | 0-5 Volt   |
| get         | dac1        | 0-5 Volt   |
| get         | dac2        | 0-5 Volt   |
| get         | dac3        | 0-5 Volt   |
| get         | dac4        | 0-5 Volt   |
| get         | dac5        | 0-5 Volt   |
| get         | dac6        | 0-5 Volt   |
| get         | dac7        | 0-5 Volt   |

Example::
```shell
set dac1:4095
get dac8
```

Special commands

Get version and help

| **Command** | **return** |
|-------------|------------|
| get         | ver        |
| help        |            |

"""
from __future__ import annotations

from pint.registry import Quantity

from flowchem.devices.custom.mpikg_switch_box_component import (
    SwitchBoxADC, SwitchBoxRelay, SwitchBoxDAC
)
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva

from dataclasses import dataclass, field
from loguru import logger
from enum import StrEnum
import aioserial
import asyncio


BEFE_RELE_BITS = 16
ADC_VOLTS = 5
DAC_BITS = 4096
DAC_VOLTS = 10

def bit_to_int(bits: list[int]) -> int:
    return int("".join(str(b) for b in bits), 2)

def int_to_bit_list(value: int, length: int = 16) -> list[int]:
    bits = list(map(int, bin(value)[2:]))  # convert to binary string, strip "0b", then to list of ints
    if length is not None:  # pad with leading zeros if length is given
        bits = [0] * (length - len(bits)) + bits
    return bits


class SwitchBoxException(Exception):
    """ General Switch Box exception """
    pass


class InvalidConfiguration(SwitchBoxException):
    """ Used for failure in the serial communication """
    pass


class InfRequest(StrEnum):
    GET = "get"
    SET = "set"


class VariableType(StrEnum):

    VERSION = "ver"

    # ------  ADC/DAC Commands  ------
    ADC = "adc"
    DAC = "dac"  # (0-4095)(0-10V)


class BefrelayPorts(StrEnum):
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
class SwitchBoxBeferelayCommand:
    """ Class representing a box command for Beferelay Ports and its expected reply """
    request: InfRequest = InfRequest.SET
    port: str = BefrelayPorts.A.value
    bits_command: int = 0
    bits_command_list: list[int] = field(default_factory=list)
    reply_lines: int = 1

    def compile(self) -> bytes:
        command = ""
        if self.request == InfRequest.SET:
            if self.port == BefrelayPorts.ABCD:
                command = f"{self.request} {self.port}:"
                for bits in self.bits_command_list:
                    command += f"{bits},"
                command = command[:-1]
            else:
                command = f"{self.request} {self.port}:{self.bits_command}"
        elif self.request == InfRequest.GET:
            command = f"{self.request} {self.port}"
        return f"{command}\r".encode()


@dataclass
class SwitchBoxGeneralCommand:
    """ Class representing a box command ADC/DAC Commands and its expected reply """
    channel: int | str = 0
    request: InfRequest = InfRequest.SET
    variable: VariableType = VariableType.ADC
    reply_lines: int = 1
    value: int = 0

    def compile(self)->bytes:
        """
        Create actual command byte by prepending box address to command.
        """
        if self.request == InfRequest.SET:
            if self.variable in {VariableType.ADC, VariableType.DAC}:
                command = f"{self.request} {self.variable}{self.channel}:{self.value}"
            else:
                command = f"{self.request} {self.variable}:{self.value}"
        else:
            if self.variable in {VariableType.ADC, VariableType.DAC}:
                command = f"{self.request} {self.variable}{self.channel}"
            else:
                command = f"{self.request} {self.variable}"
        return f"{command}\r".encode()


class SwitchBoxIO:
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
        """Create SwitchBoxIO from config."""
        # Merge default serial settings with provided ones.
        configuration = dict(SwitchBoxIO.DEFAULT_CONFIG, **serial_kwargs)

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfiguration(
                f"Could not open serial port {port} with configuration {configuration}"
            ) from serial_exception

        return cls(serial_object)

    async def _write(self, command: SwitchBoxGeneralCommand | SwitchBoxBeferelayCommand):
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
            # Stripping newlines etc. allows to skip empty lines and clean output
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
        self, command: SwitchBoxGeneralCommand | SwitchBoxBeferelayCommand
    ) -> str:
        """ Main SwitchBoxIO method. Sends a command to the box, reads the replies and returns it, optionally parsed """
        async with self.lock:
            self.reset_buffer()
            await self._write(command)
            response = await self._read_reply(command)

        if not response:
            raise InvalidConfiguration(
                "No response received from box, check port address!"
            )
        if response.startswith("ERROR"):
            logger.error(f"Error in the command '{command}' sent to the Switch Box")
        return response


class SwitchBoxMPIKG(FlowchemDevice):
    INSTANCES: dict[str, SwitchBoxMPIKG] = {}
    """ Switch Box MPIKG module class """
    def __init__(
            self,
            box_io: SwitchBoxIO,
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
        switch_io = SwitchBoxIO.from_config(port, **serial_kwargs)

        return cls(box_io=switch_io, name=name)

    async def initialize(self):
        self.device_info.version = await self.box_io.write_and_read_reply(
            command=SwitchBoxGeneralCommand(request=InfRequest.GET,
                                            variable=VariableType.VERSION)
        )
        self.components.extend([
            SwitchBoxADC("adc", self),
            SwitchBoxDAC("dac", self),
            SwitchBoxRelay("relay", self)
        ])

        # Keep the instances accessible to the devices connected to it
        self.INSTANCES[self.name] = self

        logger.info(
            f"Connected to SwitchBoxMPIKG on port {self.box_io._serial.port}!")

    """ Port Befehle """

    async def set_relay_port(
            self,
            values: list[int],
            switch_to_low_after: float = -1,
            port: str = "a"
    ):
        """Set all 8 relay channels of a given port.

        Each channel can be set to:
          * 0 → off
          * 1 → half power (power1 only)
          * 2 → full power (power1 + power2)

        Args:
            values (list[int]): List of up to 8 integers (0, 1, or 2) defining
                channel states. Shorter lists are zero-padded.
            switch_to_low_after (float, optional): Time in seconds after which
                channels set to full power (2) will be reduced to half power (1).
                Default = -1 (disabled).
            port (str, optional): Port identifier ("a", "b", "c", "d").
                Default = "a".

        Returns:
            bool: True if the device acknowledged the command with "OK",
            False otherwise.
        """

        # verify values
        if port not in [p.value for p in BefrelayPorts]:
            logger.error("Values should be in [0, 1, 2]")
            return False
        if len(values) > 8:
            logger.error(f"Port only have 8 channels - It was provide {len(values)}!")
            return False
        while len(values) < 8:
            values.append(0)
        # verify port
        port = port.lower()
        if port not in BefrelayPorts:
            logger.error(f"There is not port {port} in device {self.name}!")
            return False

        """
        Bits are mapped as:
        bits_power1: [ch8, ch7, ch6, ch5, ch4, ch3, ch2, ch1]
        bits_power2: [ch8, ch7, ch6, ch5, ch4, ch3, ch2, ch1]
        """
        bits_power1 = [0] * int(BEFE_RELE_BITS / 2)  # channels 8 to 1
        bits_power2 = [0] * int(BEFE_RELE_BITS / 2)  # channels 8 to 1
        for i, v in enumerate(values):
            if v == 2:
                """ Full power """
                bits_power1[-(i + 1)] = 1
                bits_power2[-(i + 1)] = 1
            elif v == 1:
                bits_power1[-(i + 1)] = 1

        bits_command = bit_to_int(bits_power1+bits_power2)

        status = await self.box_io.write_and_read_reply(
            command=SwitchBoxBeferelayCommand(
                port=port,
                request=InfRequest.SET,
                bits_command=bits_command
            )
        )
        if not status.startswith("OK"):
            return False
        if switch_to_low_after > 0:
            for i, v in enumerate(values):
                if bits_power2[-(i + 1)] == 1:
                    bits_power2[-(i + 1)] = 0

        await asyncio.sleep(switch_to_low_after)

        bits_command = bit_to_int(bits_power1+bits_power2)
        status = await self.box_io.write_and_read_reply(
            command=SwitchBoxBeferelayCommand(
                port=port,
                request=InfRequest.SET,
                bits_command=bits_command)
        )
        return status.startswith("OK")

    async def set_relay_single_channel(
            self,
            channel: int,
            value: int = 2,
            keep_port_status = True,
            switch_to_low_after: float = -1
    ):
        """
        Set a single relay channel.

        Args:
            channel (int): Channel index [1–32].
            value (int, optional): Desired state (0=off, 1=half power, 2=full power).
                Default = 2.
            keep_port_status (bool, optional): If True, preserves the state of other
                channels in the same port. If False, all other channels are reset
                to 0. Default = True.
            switch_to_low_after (float, optional): If >0 and value=2 (full power),
                the channel is automatically reduced to 1 after the delay.
                Default = -1 (disabled).

        Returns:
            bool: True if the command succeeded, False otherwise.
        """
        status = await self.get_relay_channels()
        if 0 < channel <= 8:
            port, ch = "a", channel
        elif 8 < channel <= 16:
            port, ch = "b", channel - 8
        elif 16 < channel <= 24:
            port, ch = "c", channel - 16
        elif 24 < channel <= 32:
            port, ch = "d", channel - 24
        else:
            logger.error(f"There is not channel {channel} in device {self.name}!")
            return False

        values = status[port] if keep_port_status else [0] * 8
        values[ch - 1] = value

        if switch_to_low_after and value == 2:
            if await self.set_relay_port(values=values, port=port.lower()):
                values[ch - 1] = 1
                return await self.set_relay_port(values=values, port=port.lower())
            else:
                return False

        else:
            return await self.set_relay_port(values=values, port=port.lower())

    async def get_relay_channels(self):
        """
        Query the current relay status of all ports.

        Returns:
            dict[str, list[int]]: Mapping of port IDs ("a", "b", "c", "d") to
            lists of 8 integers (0, 1, 2) describing each channel state.
        """
        asw = await self.box_io.write_and_read_reply(
            command=SwitchBoxBeferelayCommand(port=BefrelayPorts.ABCD, request=InfRequest.GET)
        )
        asw = asw.replace(" ", "")
        result = {}
        for ports in asw.split(","):
            bits_command = int_to_bit_list(int(ports.split(":")[1]))
            result[ports.split(":")[0].lower()] = [a + b for a, b in zip(bits_command[:8], bits_command[8:])][::-1]
        return result

    """ ADC/DAC Commands """

    async def get_adc(self):
        """
            Read all ADC (Analog Digital Converter) channels.

        Returns:
            dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
            voltage values.
        """
        asw = await self.box_io.write_and_read_reply(
            command=SwitchBoxGeneralCommand(
                channel="x", request=InfRequest.GET, variable=VariableType.ADC)
        )
        asw = asw.replace(" ", "")
        result = {}
        for ports in asw.split(";"):
            value = float(ports.split(":")[1])
            result[ports.split(":")[0][1:]] = value
        return result

    async def get_dac(self, channel: int = 1, volts: bool = True):
        """
        Read the DAC output of a channel.

        Args:
            channel (int, optional): DAC channel index (1 or 2). Default = 1.
            volts (bool, optional): If True, return the value in volts.
                If False, return the raw integer value. Default = True.

        Returns:
            float | int: DAC output in volts (if volts=True) or raw bits (if volts=False).
        """
        asw = await self.box_io.write_and_read_reply(
            command=SwitchBoxGeneralCommand(channel=channel,
                                            request=InfRequest.GET,
                                            variable=VariableType.DAC)
        )
        bit = int(asw.split(':')[-1])
        if volts:
            return bit / DAC_BITS * DAC_VOLTS

    async def set_dac(self, value: Quantity, channel: int = 1) -> bool:
        """
        Set the DAC output voltage for a given channel.

        Args:
            value (Quantity): Target voltage as a Pint Quantity (e.g., `ureg("2.5 V")`).
            channel (int, optional): DAC channel index (1 or 2). Defaults to 1.

        Returns:
            bool:
                - True if the voltage command was successfully sent and acknowledged by the device.
                - False if the voltage is outside the valid range or if the device did not return "OK".

        Notes:
            - The voltage is converted to volts and must be strictly between 0 V and 5 V.
            - If the voltage is out of range, an error is logged.
        """
        volts = value.to('V').magnitude
        if not 0 < volts < 5:
            logger.error("The value set in the DAC should be between 0 and 5 V!")
            return False
        status = await self.box_io.write_and_read_reply(
            command=SwitchBoxGeneralCommand(
                channel=channel,
                request=InfRequest.SET,
                variable=VariableType.DAC,
                value=int(volts * DAC_BITS / DAC_VOLTS)
            )
        )
        return status.startswith("OK")