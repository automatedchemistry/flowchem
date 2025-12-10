# ruff: noqa: F403, F405
"""
Knauer Autosampler Control Module
=================================

This module provides an interface to control the Knauer Autosampler AS 6.1L via either Serial or Ethernet communication.
It enables users to interact with the device by sending and receiving commands, configuring parameters like tray temperature,
syringe volume, and controlling the movement of the needle and valves.

Core Features
-------------
- Support for both serial (RS-232) and TCP/IP communication.
- Full command construction and parsing for Knauer Autosampler protocol.
- Error handling and status querying from the Autosampler.
- High-level async control of tray movement, sample aspiration/dispensing, and valve positioning.

Main Components
---------------
- `KnauerAutosampler`: Main class that encapsulates the Autosampler logic. Exposes methods to set/get parameters,
  initialize the device, and perform key operations like aspiration and dispensing.
- `ASEthernetDevice`: TCP communication wrapper to interact with the Autosampler over Ethernet.
- `ASSerialDevice`: Serial communication wrapper using `aioserial` for asynchronous operation.
- `send_until_acknowledged`: Decorator that retries sending a command until acknowledged or a timeout occurs.
- `ErrorCodes`, `CommandModus`: Enums for command interpretation and error decoding.
- Custom exceptions (`ASError`, `CommunicationError`, etc.) to represent protocol-specific issues.

Dependencies
------------
- `asyncio`, `aioserial`: For asynchronous I/O communication.
- `pint`, `flowchem`: For unit handling and device integration.
- `loguru`: For logging events and error reporting.
"""
from enum import Enum, auto
from loguru import logger
import aioserial

import asyncio
from typing import Type
import functools
import time
import pint
from flowchem import ureg

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import jakob, samuel_saraiva, miguel
from flowchem.devices.knauer.knauer_autosampler_component import (
    AutosamplerGantry3D,
    AutosamplerPump,
    AutosamplerSyringeValve,
    AutosamplerInjectionValve,
)

try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS.knauer_AS import * # This won't trigger F403 or F405 now

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False


class ErrorCodes(Enum):
    ERROR_0 = "No Error."
    ERROR_294 = "Home sensor not reached."
    ERROR_295 = "Deviation of more than +/- 2 mm towards home."
    ERROR_296 = "Home sensor not de-activated."
    ERROR_297 = "Home sensor activated when not expected."
    ERROR_298 = "Tray position is unknown."
    ERROR_303 = "Horizontal: needle position is unknown."
    ERROR_304 = "Horizontal: home sensor not reached."
    ERROR_306 = "Horizontal: home sensor not de-activated."
    ERROR_307 = "Horizontal: home sensor activated when not expected."
    ERROR_312 = "Vertical: needle position is unknown."
    ERROR_313 = "Vertical: home sensor not reached."
    ERROR_315 = "Vertical: home sensor not de-activated."
    ERROR_317 = "Vertical: stripper did not detect plate (or wash/waste)."
    ERROR_318 = "Vertical: stripper stuck."
    ERROR_319 = "Vertical: The sample needle arm is at an invalid position."
    ERROR_324 = "Syringe valve did not find destination position."
    ERROR_330 = "Syringe home sensor not reached."
    ERROR_331 = "Syringe home sensor not de-activated."
    ERROR_334 = "Syringe position is unknown."
    ERROR_335 = "Syringe rotation error."
    ERROR_340 = "Destination position not reached."
    ERROR_341 = "Wear-out limit reached."
    ERROR_342 = "Illegal sensor readout."
    ERROR_347 = "Temperature above 48°C at cooling ON."
    ERROR_280 = "EEPROM write error."
    ERROR_282 = "EEPROM error in settings."
    ERROR_283 = "EEPROM error in adjustments."
    ERROR_284 = "EEPROM error in log counter."
    ERROR_290 = "Error occurred during initialization, the Alias cannot start."


class ASError(Exception):
    pass


class CommunicationError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class CommandOrValueError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class ASFailureError(ASError):
    """AS failed to execute command"""
    pass


class ASBusyError(ASError):
    """AS is currently busy but will accept your command at another point of time"""
    pass


class CommandModus(Enum):
    SET = auto()
    GET_PROGRAMMED = auto()
    GET_ACTUAL = auto()


def send_until_acknowledged(max_reaction_time=15):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            remaining_time = max_reaction_time
            start_time = time.time()
            while remaining_time > 0:
                try:
                    # Await the decorated async function
                    result = await func(*args, **kwargs)
                    return result
                except ASBusyError:
                    # If the device is busy, wait and retry
                    elapsed_time = time.time() - start_time
                    remaining_time = 10 - elapsed_time
            raise ASError("Maximum reaction time exceeded")
        return wrapper
    return decorator


class ASEthernetDevice:
    TCP_PORT = 2101
    BUFFER_SIZE = 1024

    def __init__(self, ip_address, buffersize=None, tcp_port=None):
        self.ip_address = str(ip_address)
        self.port = tcp_port if tcp_port else ASEthernetDevice.TCP_PORT
        self.buffersize = buffersize if buffersize else ASEthernetDevice.BUFFER_SIZE


    async def _send_and_receive(self, message: str):
        try:
            # Open a connection
            reader, writer = await asyncio.open_connection(self.ip_address, self.port)

            # Send the message
            writer.write(message.encode())
            await writer.drain()

            # Receive the reply in chunks
            reply = b""
            while True:
                chunk = await reader.read(ASEthernetDevice.BUFFER_SIZE)
                if not chunk:
                    break
                reply += chunk
                try:
                    CommunicationFlags(chunk)  # type: ignore
                    break
                except ValueError:
                    pass
                if CommunicationFlags.MESSAGE_END.value in chunk:  # type: ignore
                    break

            writer.close()
            await writer.wait_closed() # Close the connection

            return reply

        except asyncio.TimeoutError:
            logger.error(f"No connection possible to device with IP {self.ip_address}")
            raise ConnectionError(
                f"No Connection possible to device with IP address {self.ip_address}"
            )


class ASSerialDevice:
    """Setup and manage communication for Knauer Autosampler."""

    DEFAULT_SERIAL_CONFIG = {
        "timeout": 1,  # Timeout in seconds
        "baudrate": 9600,  # Fixed baudrate
        "bytesize": aioserial.EIGHTBITS,  # Data: 8 bits (fixed)
        "parity": aioserial.PARITY_NONE,  # Parity: None (fixed)
        "stopbits": aioserial.STOPBITS_ONE  # Stopbits: 1 (fixed)
    }

    def __init__(self, port: str | None = None, **kwargs):
        if not port:
            logger.error("A valid port must be specified for Serial communication")
            raise ValueError("A valid port must be specified for Serial communication.")
        configuration = dict(ASSerialDevice.DEFAULT_SERIAL_CONFIG, **kwargs)
        try:
            self._serial = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as serial_exception:
            logger.error(f"Cannot connect to the Autosampler on the port <{port}>")
            raise ValueError(f"Cannot connect to the Autosampler on the port <{port}>") from serial_exception
        self._lock = asyncio.Lock()

    async def _send_and_receive(self, message: str) -> bytes:
        """Send and receive messages over Serial communication."""
        async with self._lock:
            self._serial.reset_input_buffer()
            logger.debug(f"Sending message to Serial: {message}")
            await self._serial.write_async(message.encode("ascii"))

            reply = await self._serial.readline_async()
            logger.debug(f"Received reply from Serial: {reply}")
            return reply


class KnauerAutosampler(FlowchemDevice):
    """
    Interface for controlling the Knauer Autosampler AS 6.1L device.

    This class supports both Serial (via RS-232) and Ethernet (via TCP/IP) communication and exposes
    high-level methods to control hardware features such as syringe pumps, valves, gantry, and tray movement.

    Parameters
    ----------
    name : str | None
        Display name for the autosampler instance.
    ip_address : str
        IP address for Ethernet communication (mutually exclusive with `port`).
    autosampler_id : int | None
        Device ID used for command addressing.
    port : str | None
        Serial port name (e.g., 'COM3') for Serial communication (mutually exclusive with `ip_address`).
    _syringe_volume : str
        Syringe volume (e.g., '250 uL', '0.5 mL') to be validated and set.
    tray_type : str
        Type of sample tray used (must be one of the PlateTypes enum).
    **kwargs : dict
        Additional configuration options for the selected communication method.

    Attributes
    ----------
    io : ASEthernetDevice | ASSerialDevice
        Active communication handler depending on selected mode.
    components : list
        FlowChem component interfaces (pump, valves, gantry).
    device_info : DeviceInfo
        Metadata about the device (manufacturer, model, authors).

    Raises
    ------
    ValueError
        If communication mode, syringe volume, or tray type is invalid.
    NotImplementedError
        If a specific tray type is not supported yet.
    """
    def __init__(self,
                 name: str | None = None,
                 ip_address: str = "",
                 autosampler_id: int | None = None,
                 port: str | None = None,
                 _syringe_volume: str = "",
                 tray_type: str = "",
                 **kwargs,
                 ):
        # Ensure only one communication mode is set
        if ip_address and port:
            logger.error("Specify either ip_address (Ethernet) or port (Serial), not both.")
            raise ValueError("Specify either ip_address (Ethernet) or port (Serial), not both.")
        if not ip_address and not port:
            logger.error("Either ip_address or port must be specified for communication.")
            raise ValueError("Either ip_address or port must be specified for communication.")

        self.ip_address = ip_address
        self.port = port

        self.io: ASEthernetDevice | ASSerialDevice
        if self.ip_address:
            # Ethernet communication
            self.io = ASEthernetDevice(ip_address=self.ip_address, **kwargs)
            _syringe_volume_ = None
        elif self.port:
            # Serial communication
            self.io = ASSerialDevice(port=self.port, **kwargs)

            # Define valid syringe volumes (numerical values only)
            valid_syringe_volumes = {250, 500, 1000, 2500}

            try:
                if _syringe_volume:
                    _syringe_volume = ureg(_syringe_volume).to("microliters").magnitude
                    _syringe_volume_ = int(_syringe_volume)  # Ensure it's an integer
            except pint.errors.DimensionalityError as e:
                logger.error(f"Invalid syringe volume format: {_syringe_volume}. Use formats like '250 uL'.")
                raise ValueError(f"Invalid syringe volume format: {_syringe_volume}. Use formats like '250 uL'.") from e

            # Validate Syringe Volume
            if _syringe_volume_ and _syringe_volume_ not in valid_syringe_volumes:
                logger.error(f"Invalid syringe volume: {_syringe_volume}. Must be one of {valid_syringe_volumes}.")
                raise ValueError(f"Invalid syringe volume: {_syringe_volume}. Must be one of {valid_syringe_volumes}.")

        # Validate Tray Type
        tray_type = tray_type.upper()
        if tray_type in PlateTypes.__dict__.keys():  # type: ignore
            try:
                if PlateTypes[tray_type] == PlateTypes.SINGLE_TRAY_87:  # type: ignore
                    raise NotImplementedError("The tray type SINGLE_TRAY_87 is not yet implemented.")
            except KeyError as e:
                valid_plate_types = [i.name for i in PlateTypes]  # type: ignore
                raise Exception(
                    f"Invalid tray type. Please provide one of the following plate types: {valid_plate_types}") from e
        else:
            valid_plate_types = [i.name for i in PlateTypes]  # type: ignore
            logger.error(f"Invalid tray type: {tray_type}. Must be one of {valid_plate_types}.")
            raise ValueError(f"Invalid tray type: {tray_type}. Must be one of {valid_plate_types}.")

        #ASEthernetDevice.__init__(self, ip_address, **kwargs)

        super().__init__(name)
        self.autosampler_id = autosampler_id
        self.name = f"AutoSampler ID: {self.autosampler_id}" if name is None else name
        self.tray_type = tray_type
        self._syringe_volume = _syringe_volume_ if _syringe_volume_ else _syringe_volume
        self.device_info = DeviceInfo(
            authors=[jakob, miguel, samuel_saraiva],
            manufacturer="Knauer",
            model="Autosampler AS 6.1L"
        )

    async def _construct_communication_string(self,
                                              command: Type["CommandStructure"],  # type: ignore
                                              modus: str,
                                              *args: int | str,
                                              **kwargs: str) -> str:
        # input can be strings, is translated to enum internally -> enum no need to expose
        # if value cant be translated to enum, just through error with the available options
        command_class = command()
        modus = modus.upper()

        if modus == CommandModus.SET.name:
            command_class.set_values(*args, **kwargs)
            communication_string = command_class.return_setting_string()

        elif modus == CommandModus.GET_PROGRAMMED.name:
            communication_string = command_class.query_programmed()

        elif modus == CommandModus.GET_ACTUAL.name:
            communication_string = command_class.query_actual()

        else:
            raise CommandOrValueError(
                f"You set {modus} as command modus, however modus should be {CommandModus.SET.name},"
                f" {CommandModus.GET_ACTUAL.name}, {CommandModus.GET_PROGRAMMED.name} ")
        return f"{CommunicationFlags.MESSAGE_START.value.decode()}{self.autosampler_id}{ADDITIONAL_INFO}{communication_string}{CommunicationFlags.MESSAGE_END.value.decode()}"  # type: ignore

    @send_until_acknowledged(max_reaction_time=10)
    async def _set(self, message: str):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """

        reply = await self.io._send_and_receive(message)
        # this only checks that it was acknowledged
        await self._parse_setting_reply(reply)
        return True

    @send_until_acknowledged(max_reaction_time=10)
    async def _query(self, message: str):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = await self.io._send_and_receive(message)
        query_reply = await self._parse_query_reply(reply)
        return query_reply

    async def _parse_setting_reply(self, reply):
        # reply needs to be binary string

        if reply == CommunicationFlags.ACKNOWLEDGE.value:  # type: ignore
            return True
        elif reply == CommunicationFlags.TRY_AGAIN.value:  # type: ignore
            raise ASBusyError
        elif reply == CommunicationFlags.NOT_ACKNOWLEDGE.value:  # type: ignore
            raise CommandOrValueError
        # this is only the case with replies on queries
        else:
            raise ASError(f"The reply is {reply} and does not fit the expected reply for value setting")

    async def _parse_query_reply(self, reply) -> int:
        reply_start_char, reply_stripped, reply_end_char = (reply[:ReplyStructure.STX_END.value],  # type: ignore
                                                            reply[ReplyStructure.STX_END.value:ReplyStructure.ETX_START.value],  # type: ignore
                                                            reply[ReplyStructure.ETX_START.value:])  # type: ignore
        if reply_start_char != CommunicationFlags.MESSAGE_START.value or reply_end_char != CommunicationFlags.MESSAGE_END.value:  # type: ignore
            raise CommunicationError

        # basically, if the device gives an extended reply, length will be 14. This only matters for get commands
        if len(reply_stripped) == 14:
            # decompose further
            as_id = reply[ReplyStructure.STX_END.value:ReplyStructure.ID_END.value]  # type: ignore
            as_ai = reply[ReplyStructure.ID_END.value:ReplyStructure.AI_END.value]  # type: ignore
            as_pfc = reply[ReplyStructure.AI_END.value:ReplyStructure.PFC_END.value]  # type: ignore
            as_val = reply[ReplyStructure.PFC_END.value:ReplyStructure.VALUE_END.value]  # type: ignore
            # check if reply from requested device
            if int(as_id.decode()) != self.autosampler_id:
                logger.error(f"AS_AI reply {as_ai} and AS_PFC reply {as_pfc}!")
                raise ASError(f"ID of used AS is {self.autosampler_id}, but ID in reply is {as_id}")
            # if reply is only zeros, which can be, give back one 0 for interpretation
            if len(as_val.decode().lstrip("0")) > 0:
                return int(as_val.decode().lstrip("0"))
            else:
                return int(as_val.decode()[-1:])
            # check the device ID against current device id
        else:
            raise ASError(f"AutoSampler reply did not fit any of the known patterns, reply is: {reply_stripped}")

    async def _set_get_value(self,
                             command: Type["CommandStructure"],  # type: ignore
                             parameter: int | str | None = None,
                             reply_mapping: None | Type[Enum] = None, get_actual=False):
        """If get actual is set true, the actual value is queried, otherwise the programmed value is queried (default)"""
        if parameter:
            command_string = await self._construct_communication_string(command, CommandModus.SET.name, parameter)
            return await self._set(command_string)
        else:
            command_string = await self._construct_communication_string(command, CommandModus.GET_PROGRAMMED.name if not get_actual else CommandModus.GET_ACTUAL.name)
            reply = await self._query(command_string)
            if reply_mapping:
                return reply_mapping(reply).name
            else:
                return reply

    async def initialize(self):
        """Sets initial positions."""
        errors = await self.get_errors()
        if errors:
            logger.info(f"On init Error: {errors} was present")
        await self.reset_errors()
        # Sets initial positions of needle and valve
        await self._move_needle_vertical(NeedleVerticalPositions.UP.name)  # type: ignore
        await self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)  # type: ignore
        await self.syringe_valve_position(SyringeValvePositions.WASTE.name)  # type: ignore
        await self.injector_valve_position(InjectorValvePositions.LOAD.name)  # type: ignore

        logger.info('Knauer AutoSampler device was successfully initialized!')
        self.components.extend([
            AutosamplerGantry3D("gantry3D", self),
            AutosamplerPump("pump", self),
            AutosamplerSyringeValve("syringe_valve", self),
            AutosamplerInjectionValve("injection_valve", self),
        ])

    async def measure_tray_temperature(self):
        command_string = self._construct_communication_string(TrayTemperatureCommand, CommandModus.GET_ACTUAL.name)  # type: ignore
        return int(await self._query(command_string))

    async def set_tray_temperature(self, setpoint: int | None = None):
        return await self._set_get_value(TrayTemperatureCommand, setpoint)  # type: ignore

    async def tubing_volume(self, volume: None | int = None):
        return await self._set_get_value(TubingVolumeCommand, volume)  # type: ignore

    async def set_tray_temperature_control(self, onoff: str | None = None):
        return await self._set_get_value(TrayCoolingCommand, onoff, TrayCoolingCommand.on_off)  # type: ignore

    async def compressor(self, onoff: str | None = None):
        return await self._set_get_value(SwitchCompressorCommand, onoff, SwitchCompressorCommand.on_off, get_actual=True)  # type: ignore

    # does not do anything perceivable - hm
    async def headspace(self, onoff: str | None = None):
        return await self._set_get_value(HeadSpaceCommand, onoff, HeadSpaceCommand.on_off)  # type: ignore

    async def syringe_volume(self, volume: None | int = None):
        return await self._set_get_value(SyringeVolumeCommand, volume)  # type: ignore

    async def loop_volume(self, volume: None | int = None):
        return await self._set_get_value(LoopVolumeCommand, volume)  # type: ignore

    # tested, find out what this does/means
    async def flush_volume(self, volume: None | int = None):
        return await self._set_get_value(FlushVolumeCommand, volume)  # type: ignore

    # tested, query works
    # todo get setting to work
    async def injection_volume(self, volume: None | int = None):
        return await self._set_get_value(InjectionVolumeCommand, volume)  # type: ignore

    async def syringe_speed(self, speed: str | None = None):
        """
        LOW, NORMAL, HIGH
        This does NOT work on all models
        """
        return await self._set_get_value(SyringeSpeedCommand, speed, SyringeSpeedCommand.speed_enum)  # type: ignore

    async def _move_needle_horizontal(self, needle_position: str | None, plate: str | None = None, well: int | None = None):
        command_string = await self._construct_communication_string(NeedleHorizontalCommand, CommandModus.SET.name, needle_position, plate, well)  # type: ignore
        return await self._set(command_string)

    async def _move_needle_vertical(self, move_to: str):
        command_string = await self._construct_communication_string(MoveNeedleVerticalCommand, CommandModus.SET.name, move_to)  # type: ignore
        return await self._set(command_string)

    async def syringe_valve_position(self, port: str | None = None):
        # TODO check if this mapping offset can be fixed elegantly
        if port:
            command_string = await self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.SET.name, port)  # type: ignore
            return await self._set(command_string)
        else:
            command_string = await self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.GET_ACTUAL.name)  # type: ignore
            raw_reply = await self._query(command_string) - 1
            return SwitchSyringeValveCommand.syringe_valve_positions(raw_reply).name  # type: ignore

    async def injector_valve_position(self, port: str | None = None):
        return await self._set_get_value(SwitchInjectorValveCommand,  # type: ignore
                                         port,
                                         SwitchInjectorValveCommand.allowed_position,  # type: ignore
                                         get_actual=True)

    async def set_raw_position(self, position: str | None = None, target_component: str | None = None):
        match target_component:
            case "injection_valve":
                return await self.injector_valve_position(port=position)
            case "syringe_valve":
                return await self.syringe_valve_position(port=position)
            case _:
                raise RuntimeError("Unknown valve type")

    async def get_raw_position(self, target_component: str | None = None) -> str:
        match target_component:
            case "injection_valve":
                return await self.injector_valve_position(port=None)
            case "syringe_valve":
                return await self.syringe_valve_position(port=None)
            case _:
                raise RuntimeError("Unknown valve type")

    async def aspirate(self, volume: float, flow_rate: float | int | None = None):
        """
        aspirate with built in syringe if no external syringe is set to AutoSampler.
        Else use external syringe
        Args:
            volume: volume to aspirate in mL
            flow_rate: flow rate in mL/min. Only works on external syringe. If built-in syringe is used, use default value

        Returns: None

        """
        if flow_rate is not None:
            raise NotImplementedError("Built in syringe does not allow to control flow rate")
        volume = int(round(volume, 3) * 1000)
        command_string = await self._construct_communication_string(AspirateCommand, CommandModus.SET.name, volume)  # type: ignore
        return await self._set(command_string)

    async def dispense(self, volume, flow_rate=None):
        """
        dispense with built in syringe if no external syringe is set to AutoSampler.
        Else use external syringe
        Args:
            volume: volume to dispense in mL
            flow_rate: flow rate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if flow_rate is not None:
            raise NotImplementedError("Built in syringe does not allow to control flow rate")
        volume = int(round(volume, 3) * 1000)
        command_string = await self._construct_communication_string(DispenseCommand, CommandModus.SET.name, volume)  # type: ignore
        return await self._set(command_string)

    async def _move_tray(self, tray_type: str, sample_position: str | int):
        command_string = await self._construct_communication_string(MoveTrayCommand, CommandModus.SET.name, tray_type, sample_position)  # type: ignore
        return await self._set(command_string)

    async def get_errors(self):
        command_string = await self._construct_communication_string(GetErrorsCommand, CommandModus.GET_ACTUAL.name)  # type: ignore
        reply = str(await self._query(command_string))
        return ErrorCodes[f"ERROR_{reply}"].value

    async def reset_errors(self):
        command_string = await self._construct_communication_string(ResetErrorsCommand, CommandModus.SET.name)  # type: ignore
        await self._set(command_string)

    async def get_status(self):
        command_string = await self._construct_communication_string(RequestStatusCommand, CommandModus.GET_ACTUAL.name)  # type: ignore
        reply = str(await self._query(command_string))
        reply = (3-len(reply))*'0'+reply
        return ASStatus(reply).name  # type: ignore


if __name__ == "__main__":
    import asyncio

    AS = KnauerAutosampler(
        name="test-AS",
        #ip_address="192.168.10.114",
        port="COM3",
        autosampler_id=61,
        tray_type="TRAY_48_VIAL",
        _syringe_volume="0.25 mL",
    )

    async def execute_tasks(A_S):
        print(await A_S.get_errors())
        await A_S.reset_errors()
        print(await A_S.get_raw_position(target_component="syringe_valve"))
    asyncio.run(execute_tasks(AS))


