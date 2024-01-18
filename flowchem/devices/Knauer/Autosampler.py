"""
Module for communication with Autosampler.
"""

# For future: go through graph, acquire mac addresses, check which IPs these have and setup communication.
# To initialise the appropriate device on the IP, use class name like on chemputer
import inspect
import logging
import socket
from enum import Enum, auto
from typing import Type
from time import sleep
import functools


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

# wrapper that executes for a maximum amount of time until positive reply received
def send_until_acknowledged(func, max_reaction_time = 10, time_between=0.01):
    @functools.wraps(func)
    def wrapper(*args, max_reaction_time=max_reaction_time, time_between=time_between, **kwargs, ):
        while True:
            try:
                return func(*args, **kwargs)
            except ASBusyError:
                # AS is rather fast so this sounds like a reasonable time
                sleep(time_between)
                max_reaction_time -= time_between
                if max_reaction_time <= 0:
                    raise ASError
    return wrapper

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
        self.initialize()
        self._external_aspirate = None
        self._external_dispense = None
        self._external_syringe_ready = None

    @property
    def external_syringe_aspirate(self):
        """
        Access external syringe aspirate function object
        Returns: external syringe aspirate function object

        """
        return self._external_aspirate

    @external_syringe_aspirate.setter
    def external_syringe_aspirate(self, aspirate):
        """
        Set the command for external syringe aspiration use. This will make all syringe commands use external syringe
        Args:
            aspirate: the function object for external syringe aspirate

        Returns: None

        """
        self._external_aspirate = aspirate

    @property
    def external_syringe_ready(self):
        """
        Access external syringe wait_until_ready function object
        Returns: external syringe wait_until_ready function object

        """
        return self._external_syringe_ready

    @external_syringe_ready.setter
    def external_syringe_ready(self, ready):
        """
        Set the command for external syringe wait_until_ready use. This will make all syringe commands use external syringe
        Args:
            aspirate: the function object for external wait_until_ready

        Returns: None

        """
        self._external_syringe_ready = ready

    @property
    def external_syringe_dispense(self):
        """
        Access external syringe dispense function object
        Returns: external dispense function object
        """
        return self._external_dispense

    @external_syringe_dispense.setter
    def external_syringe_dispense(self, dispense):
        """
        Set the command for external syringe dispense use. This will make all syringe commands use external syringe
        Args:
            aspirate: the function object for external syringe dispense

        Returns: None

        """
        self._external_dispense = dispense

    def _construct_communication_string(self, command: Type[CommandStructure], modus: str, *args: int or str, **kwargs: str)->str:
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
        """If get actuakl is set true, the actual value is queried, otherwise the programmed value is queried (default)"""
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

    def initialize(self):
        """
        Sets initial positions of components to assure reproducible startup
        Returns: None
        """
        # TODO home syringe, also external
        self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
        self.syringe_valve_position(SyringeValvePositions.WASTE.name)
        self.injector_valve_position(InjectorValvePositions.LOAD.name)


    def measure_tray_temperature(self):
        command_string = self._construct_communication_string(TrayTemperatureCommand, CommandModus.GET_ACTUAL.name)
        return int(self._query(command_string))

    def set_tray_temperature(self, setpoint: int = None):
        return self._set_get_value(TrayTemperatureCommand, setpoint)

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
        """LOW, NORMAL, HIGH"""
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
    def aspirate(self, volume):
        volume = int(round(volume, 3) * 1000)
        command_string = self._construct_communication_string(AspirateCommand, CommandModus.SET.name, volume)
        return self._set(command_string)

    def dispense(self, volume):
        volume = int(round(volume, 3) * 1000)
        command_string = self._construct_communication_string(DispenseCommand, CommandModus.SET.name, volume)
        return self._set(command_string)

    def move_syringe(self, position):
        command_string = self._construct_communication_string(MoveSyringeCommand, CommandModus.SET.name, position)
        return self._set(command_string)

    def get_status(self):
        command_string = self._construct_communication_string(RequestStatusCommand, CommandModus.GET_ACTUAL.name)
        reply = str(self._query(command_string))
        reply = (3-len(reply))*'0'+reply # zero pad from left to length == 3
        return ASStatus(reply).name

    def fill_transport(self, repetitions:int):
        command_string = self._construct_communication_string(FillTransportCommand, CommandModus.SET.name, repetitions)
        return self._set(command_string)

    #tested, if on is set it immeadiatly washed, if off is set it does nothing but refuses to wash sth else afterwards
    def initial_wash(self, port_to_wash:str, on_off: str):
        command_string = self._construct_communication_string(InitialWashCommand, CommandModus.SET.name, port_to_wash, on_off)
        return self._set(command_string)
    # move to row, singleplate not working (yet)
    # leftplate/rightplate does not have a function, at least if it is the same plates
    def _move_tray(self, tray_type: str, sample_position: str or int):
        command_string = self._construct_communication_string(MoveTrayCommand, CommandModus.SET.name, tray_type, sample_position)
        return self._set(command_string)

# plate
    # , no_plate is not working
    def _move_needle_horizontal(self, needle_position:str, plate: str = None, well: int = None):
        command_string = self._construct_communication_string(NeedleHorizontalCommand, CommandModus.SET.name, needle_position, plate, well)
        return self._set(command_string)

    def _move_needle_vertical(self, move_to: str):
        command_string = self._construct_communication_string(MoveNeedleVerticalCommand, CommandModus.SET.name, move_to)
        return self._set(command_string)

    # todo make this a decorator and just retry until acknowledge
    def wait_until_ready(self):
        while True:
            if self.get_status() == ASStatus.NOT_RUNNING.name:
                break
            # AS is rather fast so this sounds like a reasonable time
            sleep(0.01)



    def connect_to_sample(self, traytype: str, side: str, column:str, row: int):
        # TODO check why move tray needs parameter of side
        traytype = traytype.upper()
        try:
            if PlateTypes[traytype] == PlateTypes.SINGLE_TRAY_87:
                raise NotImplementedError
        except KeyError as e:
            raise Exception(f"Please provide one of following plate types: {[i.name for i in PlateTypes]}") from e
        # column is a letter, to convert to correct number use buildt-in, a gives 0 here
        column_int = ord(column.upper())-64
        print(f"You've selected the column {column_int}, counting starts at 1.")
        # now check if that works for selected tray:
        assert PlateTypes[traytype].value[0] >= column_int and PlateTypes[traytype].value[1] >= row

        self._move_tray(side, row)
        self._move_needle_horizontal(NeedleHorizontalPosition.PLATE.name, plate=side, well=column_int)
        self._move_needle_vertical(NeedleVerticalPositions.DOWN.name)

# it would be reaonable to get all from needle to loop, with piercing inert gas vial
    def disconnect_sample(self):

        self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        self._move_tray(SelectPlatePosition.NO_PLATE.name, TrayPositions.HOME.name)
        self._move_needle_horizontal(NeedleHorizontalPosition.WASH.name)

    def pick_up_sample(self, volume_sample, volume_buffer=0, syr_asp = None):

        if volume_buffer:
            self.syringe_valve_position("wash")
            if syr_asp == None:
                self.aspirate(volume_buffer)
            else:
                syr_asp(volume_buffer, 1)
        self.injector_valve_position("inject")
        self.syringe_valve_position("needle")
        if syr_asp == None:
            self.aspirate(volume_sample)
        else:
            syr_asp(volume_sample, 0.1)


    def wash_system(self, wash="needle", times:int=3, syringe_asp = None, asp_value = 0.250, syringe_disp = None, disp_value = 0.250):
        #washing loop, ejecting through needle!
        for i in range(times):
            self.syringe_valve_position("wash")
            if not syringe_asp:
                self.aspirate(asp_value)
            else:
                syringe_asp(asp_value, 1)  
            self.syringe_valve_position("needle")
            if wash == "needle":
                self.injector_valve_position("inject")
            else:
                self.injector_valve_position("load")
            if not syringe_disp:
                self.dispense(disp_value)
            else:
                syringe_disp(disp_value, 1)

    def dispense_sample(self, volume, dead_volume=0.050, syr_disp = None):

        self.syringe_valve_position("needle")
        self.injector_valve_position("load")
        if syr_disp == None:
            self.dispense(volume+dead_volume)
        else:
            syr_disp(volume+dead_volume)

if __name__ == "__main__":
    pass