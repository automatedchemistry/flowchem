"""
Module for communication with Autosampler.
"""

# For future: go through graph, acquire mac addresses, check which IPs these have and setup communication.
# To initialise the appropriate device on the IP, use class name like on chemputer


import logging
import socket
from enum import Enum, auto

try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS.knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False

# from pint import UnitRegistry
# finding the AS is not trivial with autodiscover, it also only is one device


class ASError(Exception):
    pass


class CommunicationError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class CommandOrValueError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class ASBusyError(ASError):
    """AS is currently busy but will accept your command at another point of time"""
    pass


class CommandModus(Enum):
    SET = auto()
    GET_PROGRAMMED = auto()
    GET_ACTUAL = auto()

#TODO do not decode reply before digestion, leave in binary
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
                    chunk = s.recv(1024)
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


class KnauerAS(ASEthernetDevice):
    """
    Class to control Knauer or basically any Spark Holland AS.
    """
    AS_ID = 61
    def __init__(self,ip_address,  autosampler_id = None, port=ASEthernetDevice.TCP_PORT, buffersize=ASEthernetDevice.BUFFER_SIZE):

        super().__init__(ip_address, buffersize, port)
        # get statuses, that is basically syringe syize, volumes, platetype

        self.autosampler_id = autosampler_id if autosampler_id else KnauerAS.AS_ID

    def _construct_communication_string(self, command: CommandStructure, modus: str, *args: int or str, **kwargs: str)->str:
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

    def _query(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)

        query_reply = self._parse_query_reply(reply, message)
        return query_reply

    def _parse_setting_reply(self, reply):
        # reply needs to be binary string
        from NDA_knauer_AS.knauer_AS import CommunicationFlags

        if reply == CommunicationFlags.ACKNOWLEDGE.value:
            return True
        elif reply == CommunicationFlags.TRY_AGAIN.value:
            raise ASBusyError
        elif reply == CommunicationFlags.NOT_ACKNOWLEDGE.value:
            raise CommandOrValueError
        # this is only the case with replies on queries
        else:
            raise ASError(f"The reply is {reply} and does not fit the expected reply for value setting")

    def _parse_query_reply(self, reply, as_command)->int:
        from NDA_knauer_AS.knauer_AS import ReplyStructure, KnauerASCommands
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
        # todo: this removes
            if len(as_val.decode().lstrip("0")) > 0:
                return int(as_val.decode().lstrip("0"))
            else:
                return int(as_val.decode()[-1:])
            # check the device ID against current device id, check that reply is on send request
        # TODO check if reply is on query
        else:
            raise ASError(f"AS reply did not fit any of the known patterns, reply is: {reply_stripped}")

    def _set_get_value(self, command:CommandStructure, parameter:int or None=None, reply_mapping: None or Enum = None)->int:
        if parameter:
            command_string = self._construct_communication_string(command, "SET", parameter)
            return self._set(command_string)
        else:
            command_string = self._construct_communication_string(command, "GET_PROGRAMMED")
            reply = self._query(command_string)
            if reply_mapping:
                return reply_mapping(reply).name
            else:
                return reply

    def measure_tray_temperature(self):
        command_string = self._construct_communication_string(TrayTemperatureCommand, "GET_ACTUAL")
        return int(self.autosampler_query(command_string))

    def get_setpoint_tray_temperature(self):
        command_string = self._construct_communication_string(TrayTemperatureCommand, "GET_PROGRAMMED")
        return int(self.autosampler_query(command_string))

    def set_tray_temperature(self, setpoint: int):
        command_string = self._construct_communication_string(TrayTemperatureCommand, "SET", setpoint)
        return self.autosampler_set(command_string)


    def tubing_volume(self, volume: None or int = None):
        TubingVolumeCommand

    def tray_cooling(self, onoff: str):
        command_string = self._construct_communication_string(TrayCoolingCommand, "SET", onoff)
        return self.autosampler_set(command_string)


    def syringe_volume(self):
        SyringeVolumeCommand
    def syringe_speed(self):
        SyringeSpeedCommand

    def syringe_valve(self):
        SwitchSyringeValveCommand
    def injector_valve(self):
        SwitchInjectorValveCommand

    def compressor(self):
        SwitchCompressorCommand

    def aspirate(self):
        AspirateCommand

    def get_status(self):
        RequestStatusCommand

    def dispense(self):
        DispenseCommand

    def fill_transport(self):
        FillTransportCommand

    def connect_to_sample(self):
        MoveTrayCommand
        NeedleHorizontalCommand
        MoveNeedleVerticalCommand

    def disconnect_sample(self):
        MoveTrayCommand
        NeedleHorizontalCommand
        MoveNeedleVerticalCommand
    def loop_volume(self):
        LoopVolumeCommand
    def flush_volume(self):
        FlushVolumeCommand
    def headspace(self):
        HeadSpaceCommand
    def initial_wash(self):
        InitialWashCommand
    def injection_volume(self):
        InjectionVolumeCommand
    def move_syringe(self):
        MoveSyringeCommand

if __name__ == "__main__":
    pass