from enum import Enum, auto
from loguru import logger
import logging
import asyncio
from typing import Type, List
import functools
import time

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import jakob, Samuel_Saraiva, miguel
from flowchem.devices.knauer._common import KnauerEthernetDevice
from flowchem.devices.knauer.knauer_autosampler_component import (
    AutosamplerCNC,
    AutosamplerPump,
    AutosamplerSyringeValve,
    AutosamplerInjectionValve,
)

try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS.knauer_AS import *

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

class ASEthernetDevice:
    TCP_PORT = 2101
    BUFFER_SIZE = 1024

    def __init__(self, ip_address, buffersize=None, tcp_port=None):
        self.ip_address = str(ip_address)
        self.port = tcp_port if tcp_port else ASEthernetDevice.TCP_PORT
        self.buffersize = buffersize if buffersize else ASEthernetDevice.BUFFER_SIZE

        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.DEBUG,
        )

    def _send_and_receive(self, message: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.ip_address, self.port))

                s.send(message.encode())
                reply = b""
                while True:
                    chunk = s.recv(ASEthernetDevice.BUFFER_SIZE)
                    reply += chunk
                    try:
                        CommunicationFlags(chunk)
                        break
                    except ValueError:
                        pass
                    if CommunicationFlags.MESSAGE_END.value in chunk:
                        break
            return reply
        except socket.timeout:
            logging.error(f"No connection possible to device with IP {self.ip_address}")
            raise ConnectionError(
                f"No Connection possible to device with ip_address {self.ip_address}"
            )



    def __init__(self,
                 name: str = None,
                 ip_address: str = "",
                 autosampler_id: int = 0,
                 syringe_volume: str = "0.99 ml",
                 tray_type: str = "TRAY_48_VIAL",
                 **kwargs,
                 ):
        ASEthernetDevice.__init__(self, ip_address, **kwargs)
        FlowchemDevice.__init__(self, name=name)
        self.autosampler_id = autosampler_id
        self.name = f"AutoSampler ID: {self.autosampler_id}" if name is None else name
        self.tray_type = tray_type
        self.syringe_volume = syringe_volume
        self.device_info = DeviceInfo(
            authors=[jakob, miguel, Samuel_Saraiva],
            maintainers=[jakob, miguel, Samuel_Saraiva],
            manufacturer="Knauer",
            model="Autosampler AS 6.1L"
        )

    def _construct_communication_string(self, command: Type[CommandStructure], modus: str, *args: int or str,
                                        **kwargs: str) -> str:
        # input can be strings, is translated to enum internally -> enum no need to expsoe
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
            raise CommandOrValueError(f"You set {modus} as command modus, however modus should be {CommandModus.SET.name}, {CommandModus.GET_ACTUAL.name}, {CommandModus.GET_PROGRAMMED.name} ")
        return f"{CommunicationFlags.MESSAGE_START.value.decode()}{self.autosampler_id}" \
               f"{ADDITIONAL_INFO}{communication_string}" \
               f"{CommunicationFlags.MESSAGE_END.value.decode()}"

    @send_until_acknowledged
    def _set(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)
        # this only checks that it was acknowledged
        self._parse_setting_reply(reply)

    @send_until_acknowledged
    def _query(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)

        query_reply = self._parse_query_reply(reply)
        return query_reply

    def _parse_setting_reply(self, reply):
        # reply needs to be binary string

        if reply == CommunicationFlags.ACKNOWLEDGE.value:
            return True
        elif reply == CommunicationFlags.TRY_AGAIN.value:
            raise ASBusyError
        elif len(reply) == 4 and int(reply[0]) == 1:
            # this means the AS has error I think
            error = self.get_errors()
            # TODO access enum
            self.reset_errors()
            raise ASFailureError("Error in setting: ", error)
        elif reply == CommunicationFlags.NOT_ACKNOWLEDGE.value:
            raise CommandOrValueError
        # this is only the case with replies on queries
        else:
            raise ASError(f"The reply is {reply} and does not fit the expected reply for value setting")

    def _parse_query_reply(self, reply)->int:
        reply_start_char, reply_stripped, reply_end_char = reply[:ReplyStructure.STX_END.value], \
                                                           reply[
                                                           ReplyStructure.STX_END.value:ReplyStructure.ETX_START.value], \
                                                           reply[ReplyStructure.ETX_START.value:]
        if reply_start_char != CommunicationFlags.MESSAGE_START.value or reply_end_char != CommunicationFlags.MESSAGE_END.value:
            raise CommunicationError


        # basically, if the device gives an extended reply, length will be 14. This only matters for get commands
        if len(reply_stripped) == 14:
        # decompose further
            as_id = reply[ReplyStructure.STX_END.value:ReplyStructure.ID_END.value]
            as_ai = reply[ReplyStructure.ID_END.value:ReplyStructure.AI_END.value]
            as_pfc = reply[ReplyStructure.AI_END.value:ReplyStructure.PFC_END.value]
            as_val = reply[ReplyStructure.PFC_END.value:ReplyStructure.VALUE_END.value]
            # check if reply from requested device
            if int(as_id.decode()) != self.autosampler_id:
                raise ASError(f"ID of used AS is {self.autosampler_id}, but ID in reply is as_id")
            # if reply is only zeros, which can be, give back one 0 for interpretion
            if len(as_val.decode().lstrip("0")) > 0:
                return int(as_val.decode().lstrip("0"))
            else:
                return int(as_val.decode()[-1:])
            # check the device ID against current device id
        else:
            raise ASError(f"AS reply did not fit any of the known patterns, reply is: {reply_stripped}")

    def _set_get_value(self, command:Type[CommandStructure], parameter:int or None=None, reply_mapping: None or Type[Enum] = None, get_actual = False):
        """If get actual is set true, the actual value is queried, otherwise the programmed value is queried (default)"""
        if parameter:
            command_string = self._construct_communication_string(command, CommandModus.SET.name, parameter)
            return self._set(command_string)
        else:
            command_string = self._construct_communication_string(command, CommandModus.GET_PROGRAMMED.name if not get_actual else CommandModus.GET_ACTUAL.name)
            reply = self._query(command_string)
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
        await self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        await self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
        await self.syringe_valve_position(SyringeValvePositions.WASTE.name)
        await self.injector_valve_position(InjectorValvePositions.LOAD.name)

    def tubing_volume(self, volume: None or int = None):
        return self._set_get_value(TubingVolumeCommand, volume)

    def set_tray_temperature_control(self, onoff: str = None):
        return self._set_get_value(TrayCoolingCommand, onoff, TrayCoolingCommand.on_off)

    def compressor(self, onoff: str = None):
        return self._set_get_value(SwitchCompressorCommand, onoff, SwitchCompressorCommand.on_off, get_actual=True)

    # does not do anything perceivable - hm
    def headspace(self, onoff: str = None):
        return self._set_get_value(HeadSpaceCommand, onoff, HeadSpaceCommand.on_off)

    def syringe_volume(self, volume: None or int = None):
        return self._set_get_value(SyringeVolumeCommand, volume)
    
    def loop_volume(self, volume: None or int = None):
        return self._set_get_value(LoopVolumeCommand, volume)
    #tested, find out what this does/means
    def flush_volume(self, volume: None or int = None):
        return self._set_get_value(FlushVolumeCommand, volume)
    # tested, query works
    # todo get setting to work
    def injection_volume(self, volume: None or int = None):
        return self._set_get_value(InjectionVolumeCommand, volume)
        
    def syringe_speed(self, speed: str = None):
        """
        LOW, NORMAL, HIGH
        This does NOT work on all models
        """
        return self._set_get_value(SyringeSpeedCommand, speed, SyringeSpeedCommand.speed_enum)

    #tested
    def syringe_valve_position(self, port:str = None):
        # TODO check if this mapping offset can be fixed elegantly
        if port:
            command_string = self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.SET.name, port)
            return self._set(command_string)
        else:
            command_string = self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.GET_ACTUAL.name)
            raw_reply = self._query(command_string) - 1
            return SwitchSyringeValveCommand.syringe_valve_positions(raw_reply).name

    # tested
    def injector_valve_position(self, port:str = None):
        return self._set_get_value(SwitchInjectorValveCommand, port, SwitchInjectorValveCommand.allowed_position, get_actual=True)
    
    def needle_vertical_offset(self, offset: float = None):
        return self._set_get_value(VerticalNeedleOffsetCommand, offset)

    #tested
    # this is additive, it moves syr relatively
    def aspirate(self, volume:float, flow_rate:float or int=None):
        """
        aspirate with buildt in syringe if no external syringe is set to autosampler.
        Else use extrernal syringe
        Args:
            volume: volume to aspirate in mL
            flow_rate: flowrate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if flow_rate is not None:
            raise NotImplementedError("Built in syringe does not allow to control flow rate")
        volume = int(round(volume, 3) * 1000)
        command_string = self._construct_communication_string(AspirateCommand, CommandModus.SET.name, volume)
        return await self._set(command_string)

    async def dispense(self, volume, flow_rate=None):
        """
        dispense with buildt in syringe if no external syringe is set to autosampler.
        Else use external syringe
        Args:
            volume: volume to dispense in mL
            flow_rate: flowrate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if flow_rate is not None:
            raise NotImplementedError("Built in syringe does not allow to control flow rate")
        volume = int(round(volume, 3) * 1000)
        command_string = self._construct_communication_string(DispenseCommand, CommandModus.SET.name, volume)
        return await self._set(command_string)

    def move_syringe(self, position):
        if self.external_syringe_aspirate or self.external_syringe_dispense:
            # todo
            if position.upper() == "HOME":
                self.external_syringe_home(2)
            else:
                raise NotImplementedError("Only works for buildt in syringe")
        else:
            command_string = self._construct_communication_string(MoveSyringeCommand, CommandModus.SET.name, position)
            return self._set(command_string)

    def get_errors(self):
        command_string = self._construct_communication_string(GetErrorsCommand, CommandModus.GET_ACTUAL.name)
        reply = str(self._query(command_string))
        return ErrorCodes[f"ERROR_{reply}"].value

    def reset_errors(self):
        command_string = self._construct_communication_string(ResetErrorsCommand, CommandModus.SET.name)
        self._set(command_string)

    def get_status(self):
        command_string = self._construct_communication_string(RequestStatusCommand, CommandModus.GET_ACTUAL.name)
        reply = str(self._query(command_string))
        reply = (3-len(reply))*'0'+reply # zero pad from left to length == 3
        if len(reply) == 4:
            if reply[0] == '1':
                # this means there is an Error
                error_code = self.get_errors()
                self.reset_errors()
                raise ASFailureError(f"Error code {error_code} occured when checking for status")
        return ASStatus(reply).name



if __name__ == "__main__":
    pass