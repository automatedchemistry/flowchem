"""
Module for communication with Autosampler.
"""

# For future: go through graph, acquire mac addresses, check which IPs these have and setup communication.
# To initialise the appropriate device on the IP, use class name like on chemputer
import inspect
import json
import logging
import socket
from enum import Enum, auto
from typing import Type
from time import sleep
import functools
from threading import Thread
import pandas
from flowchem.units import flowchem_ureg
from rdkit.Chem import MolFromSmiles, MolToSmiles


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

def canonize_smiles(smiles:str):
    return MolToSmiles(MolFromSmiles(smiles))

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


class Vial:
    class _SpecialVial(Enum):
        CARRIER = "carrier"
        INERT_GAS = "gas"
        
    # TODO get the rounding issue of ureg right
    def __init__(self, substance, solvent:str or None, concentration: str, contained_volume:str, remaining_volume:str):
        self._remaining_volume = flowchem_ureg(remaining_volume)
        self._contained_volume = flowchem_ureg(contained_volume)
        self.substance = self._set_vial_content(substance) # todo get this canonical
        self.solvent = solvent
        self.concentration = flowchem_ureg(concentration)

    def extract_from_vial(self, volume:str):
        self._contained_volume -= flowchem_ureg(volume)
    
    @property
    def available_volume(self):
        return self._contained_volume-self._remaining_volume
        
    def _set_vial_content(self, substance):
        try:
            return canonize_smiles(substance)
        except Exception as e:
            if not str(e).startswith("Python argument types in"):
                raise e
            else:
                pass
            
        try:
            return self._SpecialVial(substance.lower()).name
        except KeyError as e:
            raise e

class TrayPosition:
    def __init__(self, side, row, column):
        self.side = side
        self.row = row
        self.column = column

    def valid_position(self):
        assert self.side.upper() is "LEFT" or self.side.upper() is "RIGHT"
        assert type(self.row) is int
        assert type(column) is str and len(column) is 1


    # basically, only acts a s container internally and to make substance access easy

# TODO create a Tray class
class Tray:
    # needs to contain mapping of what is where
    # needs to supply function of reading and writing how much is left where
    def __init__(self, tray_type, persistant_storage:str):
        #todo set a path for continuous storing of layout
        self.tray_type = tray_type
        self.persistant = persistant_storage
        self.available_vials:DataFrame = self.load_submitted()
        self._layout=["Content", "Side", "Column", "Row", "Solvent", "Concentration", "ContainedVolume", "RemainingVolume"]

    def load_submitted(self):
        # create the layout in excel -> makes usage easy
        try:
            return pandas.read_excel(self.persistant)
        except FileNotFoundErrore(f"Fill out excel file under {self.persistant}.") as e:
            self.create_blank(self.persistant)
            raise e

    def check_validity(self):
        # check if base objects are valid, eg valid position or valid smiles and also not yet occupied#
        pass
    # todo vial object and position should become a dataframe

    def load_entry(self, index:int) -> [Vial, TrayPosition]:
        # return vial for updating volume, return TrayPosiition to go there, via Tray update the json
        # get position and substance from dataframe, do based on index
        entry=self.available_vials.loc[index]
        return Vial(entry["Content"], entry["Solvent"],entry["Concentration"],entry["ContainedVolume"],entry["RemainingVolume"]), TrayPosition(entry["Side"], entry["Row"], entry["Column"])

    def find_vial(self, contains, min_volume: str="0 mL")->int:
        # todo check
        lowest_vol = self.available_vials.loc[self.available_vials["Content"] == contains & (self.available_vials["ConntainedVolume"]-self.available_vials["RemainingVolume"])>flowchem_ureg(min_volume)]["ContainedVolume"].idxmin()
        return  lowest_vol

    # this is mostly for updating volume
    def modify_entry(self, index, column, new_value):
        # modify entry, based on index
        self.available_vials.at[index, column] = new_value

    # constantly update the json file
    def save_current(self):
        self.create_output_path(file_ending="json")
        # todo just overwrite? thats the current file
        with open(write_to, "w") as f:
            json.dump(self.available_vials,f)
            
    def save_output(self):
        self.create_output_path(extended_file_name="_out")
        self.available_vials.to_excel(write_to)
        
    def create_output_path(self, extended_file_name = None, file_ending = None):
        output_name, output_ending = Path(self.persistant).name.split(".")
        write_to = Path(self.persistant).parent / Path(f"{output_name}{extended_file_name if extended_file_name else ''}.{file_ending if file_ending else output_ending}")
        return write_to

    def create_blank(self, path):
        if Path(path).exists():
            raise FileExistsError
        pandas.DataFrame(columns=self._layout).to_excel(path)


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
        self._external_syringe_home = None

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

    @property
    def external_syringe_home(self):
        """
        Access external syringe home function object
        Returns: external home function object
        """
        return self._external_syringe_home

    @external_syringe_home.setter
    def external_syringe_home(self, home):
        """
        Set the command for external syringe home use. This will make all syringe commands use external syringe
        Args:
            aspirate: the function object for external syringe home

        Returns: None

        """
        self._external_syringe_home = home

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
        if not self.external_syringe_aspirate:
            if flow_rate is not None:
                raise NotImplementedError("Buildt in syringe does not allow to control flowrate")
            volume = int(round(volume, 3) * 1000)
            command_string = self._construct_communication_string(AspirateCommand, CommandModus.SET.name, volume)
            return self._set(command_string)
        else:
            assert self.external_syringe_dispense is not None and self.external_syringe_ready is not None, "Make sure to set all necessary commands for external syringe"
            self.external_syringe_aspirate(volume, flow_rate)
            self.external_syringe_ready()

    def dispense(self, volume, flow_rate=None):
        """
        dispense with buildt in syringe if no external syringe is set to autosampler.
        Else use extrernal syringe
        Args:
            volume: volume to dispense in mL
            flow_rate: flowrate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if not self.external_syringe_dispense:
            if flow_rate is not None:
                raise NotImplementedError("Buildt in syringe does not allow to control flowrate")
            volume = int(round(volume, 3) * 1000)
            command_string = self._construct_communication_string(DispenseCommand, CommandModus.SET.name, volume)
            return self._set(command_string)
        else:
            assert self.external_syringe_aspirate is not None and self.external_syringe_ready is not None, "Make sure to set all necessary commands for external syringe"
            self.external_syringe_dispense(volume, flow_rate)
            self.external_syringe_ready()

    def move_syringe(self, position):
        if self.external_syringe_aspirate or self.external_syringe_dispense:
            # todo
            if position.upper() == "HOME":
                self.external_syringe_home()
            else:
                raise NotImplementedError("Only works for buildt in syringe")
        command_string = self._construct_communication_string(MoveSyringeCommand, CommandModus.SET.name, position)
        return self._set(command_string)

    def get_status(self):
        command_string = self._construct_communication_string(RequestStatusCommand, CommandModus.GET_ACTUAL.name)
        reply = str(self._query(command_string))
        reply = (3-len(reply))*'0'+reply # zero pad from left to length == 3
        return ASStatus(reply).name

    def fill_transport(self, repetitions:int):
        # todo what does that do again? high level needle wash?
        if self.external_syringe_aspirate or self.external_syringe_dispense:
            raise NotImplementedError("Only works for buildt in syringe")
        command_string = self._construct_communication_string(FillTransportCommand, CommandModus.SET.name, repetitions)
        return self._set(command_string)

    #tested, if on is set it immeadiatly washed, if off is set it does nothing but refuses to wash sth else afterwards
    def initial_wash(self, port_to_wash:str, on_off: str):
        if self.external_syringe_aspirate or self.external_syringe_dispense:
            raise NotImplementedError("Only works for buildt in syringe")
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

    def wait_until_ready(self, wait_for_syringe = True):
        """
        Wait for AS to be done
        Args:
            wait_for_syringe: If True (default), also the external syringe will be waited for. 
                            If False it can run in background 

        Returns: None

        """
        # todo wait for external syringe ready as well
        while True:
            if self.get_status() == ASStatus.NOT_RUNNING.name:
                break
            # if theres external syringe, wait for it to get ready
            if self._external_syringe_ready is not None and wait_for_syringe == True:
                self._external_syringe_ready()
            # AS is rather fast so this sounds like a reasonable time
            sleep(0.01)



    def connect_to_position(self, traytype: str, side: str or None, column:str or None, row: int or None):
        # TODO check why move tray needs parameter of side
        traytype = traytype.upper()
        if traytype in PlateTypes.__dict__.keys():
            general_position=False
            try:
                if PlateTypes[traytype] == PlateTypes.SINGLE_TRAY_87:
                    raise NotImplementedError
            except KeyError as e:
                raise Exception(f"Please provide one of following plate types: {[i.name for i in PlateTypes]}") from e
            # column is a letter, to convert to correct number use buildt-in, a gives 0 here
            column_int = ord(column.upper()) - 64
            print(f"You've selected the column {column_int}, counting starts at 1.")
            # now check if that works for selected tray:
            assert PlateTypes[traytype].value[0] >= column_int and PlateTypes[traytype].value[1] >= row
            self._move_tray(side, row)
            self._move_needle_horizontal(NeedleHorizontalPosition.PLATE.name, plate=side, well=column_int)
        elif traytype in NeedleHorizontalPosition.__dict__.keys():
            self._move_needle_horizontal(NeedleHorizontalPosition[traytype].name)
        else:
            raise NotImplementedError
        self._move_needle_vertical(NeedleVerticalPositions.DOWN.name)

# it would be reaonable to get all from needle to loop, with piercing inert gas vial
    def disconnect_sample(self, move_plate = False):
        self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        if move_plate:
            self._move_tray(SelectPlatePosition.NO_PLATE.name, TrayPositions.HOME.name)
            self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
            
    def fill_wash_reservoir(self, volume:float=0.2, flow_rate:float = None):
        self.syringe_valve_position(SyringeValvePositions.WASH.name)
        pump_thread = Thread(target=self.aspirate, args=[volume, flow_rate])
        pump_thread.start()
        self.connect_to_position("wash",None,None,None)
        while pump_thread.is_alive():
            sleep(0.1)
        # this is just used to connect the syringe to sample
        self.pick_up_sample(volume_sample=0,flow_rate=flow_rate)
        # empty syringe into reservoir
        self.dispense(volume, flow_rate * 10 if flow_rate else flow_rate)
        self.disconnect_sample()
        
    def empty_wash_reservoir(self, volume:float=0.2, flow_rate:float = None):
        # empty reservoir with syringe
        self.connect_to_position("wash",None,None,None)
        self.pick_up_sample(volume_sample=volume, flow_rate=flow_rate)
        # go up and move to waste
        self.disconnect_sample()

    def wash_needle(self, volume:float=0.2, times:int=3, flow_rate:float = None):
        """
        Fill neelde with solvent and then wash it.
        Args:
            volume: 0.2 mL is a reasonable value
            times:
            flow_rate:

        Returns: None

        """

        for i in range(times):
            # do wash reservoir fill
            #   fill syringe here and go to right position
            self.fill_wash_reservoir(volume=volume, flow_rate=flow_rate)
            self.empty_wash_reservoir(volume=volume, flow_rate=flow_rate)
            self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
            self._move_needle_vertical(NeedleVerticalPositions.DOWN.name)
            # dispense to waste and go up
            self.dispense(volume, flow_rate*10 if flow_rate else flow_rate)
            self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        
        # fill here, and eject, without needle wash!
        self.syringe_valve_position(SyringeValvePositions.WASH.name)
        pump_thread = Thread(target=self.aspirate, args=[volume, flow_rate])
        pump_thread.start()
        self.injector_valve_position(InjectorValvePositions.INJECT.name)
        self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
        self._move_needle_vertical(NeedleVerticalPositions.DOWN.name)
        while pump_thread.is_alive():
            sleep(0.1)
        # eject directly to waste
        self.syringe_valve_position(SyringeValvePositions.NEEDLE.name)
        self.dispense(volume, flow_rate*10 if flow_rate else flow_rate)
        self._move_needle_vertical(NeedleVerticalPositions.UP.name)


    def pick_up_sample(self, volume_sample, volume_buffer=0, flow_rate=None):

        if volume_buffer:
            self.syringe_valve_position(SyringeValvePositions.WASH.name)
            self.aspirate(volume_buffer, flow_rate)
        self.injector_valve_position(InjectorValvePositions.INJECT.name)
        self.syringe_valve_position(SyringeValvePositions.NEEDLE.name)
        # todo was 0.1
        self.aspirate(volume_sample, flow_rate)

    def wash_system(self, times:int=3, flow_rate=None, volume:float = 0.250, dispense_to:str="needle"):
        """

        Args:
            times: How often to wash
            flow_rate: Which flowrate to wash with. Only works with external syringe, otherwise use default value
            volume: washing volume in mL
            dispense_to: Where to dispense the washing fluid to - so which path to clean.

        Returns: None

        """
        #washing loop, ejecting through needle!
        legal_arguments = ["needle", "outside", "waste"]
        if dispense_to not in legal_arguments:
            raise NotImplementedError(f"Dispense to can only take following values {legal_arguments}.")
        self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
        for i in range(times):
            self.syringe_valve_position(SyringeValvePositions.WASH.name)
            self.aspirate(volume, flow_rate)
            if dispense_to == legal_arguments[0]:
                self.syringe_valve_position(SyringeValvePositions.NEEDLE.name)
                self.injector_valve_position(InjectorValvePositions.INJECT.name)
                self._move_needle_vertical(NeedleVerticalPositions.DOWN.name)
            elif dispense_to == legal_arguments[1]:
                self.syringe_valve_position(SyringeValvePositions.NEEDLE.name)
                self.injector_valve_position(InjectorValvePositions.LOAD.name)
            elif dispense_to == legal_arguments[2]:
                self.syringe_valve_position(SyringeValvePositions.WASTE.name)
            self.dispense(volume, flow_rate*10 if flow_rate else flow_rate)
            self._move_needle_vertical(NeedleVerticalPositions.UP.name)

    def dispense_sample(self, volume:float, dead_volume=0.050, flow_rate=None):
        """
        Dispense Sample in buffer tube to device connected to AS
        Args:
            volume: Volume to dispense in mL
            dead_volume: Dead volume to dispense additionally
            flow_rate: Flowrate, only works w external syringe
            
        Returns: None
        
        """
        self.syringe_valve_position(SyringeValvePositions.NEEDLE.name)
        self.injector_valve_position(InjectorValvePositions.LOAD.name)
        self.dispense(volume+dead_volume, flow_rate)

if __name__ == "__main__":
    pass