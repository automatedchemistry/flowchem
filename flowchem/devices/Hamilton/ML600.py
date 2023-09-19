"""
This module is used to control Hamilton ML600 syringe pump via the protocol1/RNO+.
"""

from __future__ import annotations

import io
import string
import time
import warnings

import serial
import logging
import threading
from enum import IntEnum
from dataclasses import dataclass
from typing import Union, Tuple, Optional
from serial import PARITY_EVEN, SEVENBITS, STOPBITS_ONE
from threading import Thread


class ML600Exception(Exception):
    """ General pump exception """

    pass


class InvalidConfiguration(ML600Exception):
    """ Used for failure in the serial communication """

    pass


class InvalidArgument(ML600Exception):
    """ A valid command was followed by an invalid command_value, usually out of accepted range """

    pass


@dataclass
class Protocol1CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """

    command: str
    optional_parameter: str = ""
    execute_command: bool = True

    def to_pump(
        self, address: int, command_value: str = "", argument_value: str = ""
    ) -> Protocol1Command:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        return Protocol1Command(
            target_pump_num=address,
            command=self.command,
            optional_parameter=self.optional_parameter,
            command_value=command_value,
            argument_value=argument_value,
            execute_command=self.execute_command,
        )


@dataclass
class Protocol1Command(Protocol1CommandTemplate):
    """ Class representing a pump command and its expected reply """

    # TODO move these two vars elsewhere!
    # ':' is used for broadcast within the daisy chain.
    PUMP_ADDRESS = {
        pump_num: address
        for (pump_num, address) in enumerate(string.ascii_lowercase[:16], start=1)
    }
    # # i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}

    target_pump_num: Optional[int] = 1
    command_value: Optional[str] = None
    argument_value: Optional[str] = None

    def compile(self, command_string: Optional = None) -> str:
        """
        Create actual command byte by prepending pump address to command and appending executing command.
        """
        assert self.target_pump_num in range(1, 17)
        if not command_string:
            command_string = self._compile()

        command_string = f"{self.PUMP_ADDRESS[self.target_pump_num]}" \
                         f"{command_string}"

        if self.execute_command is True:
            command_string += "R"

        return command_string + "\r"

    def _compile(self) -> str:
        """
        Create command string for individual pump. from that, up to two commands can be compiled, by appending pump address and adding run value
        """
        if not self.command_value:
            self.command_value = ""

        compiled_command = (
            f"{self.command}{self.command_value}"
        )
        if self.argument_value:
            compiled_command += f"{self.optional_parameter}{self.argument_value}"
        # Add execution flag at the end

        return compiled_command


class HamiltonPumpIO:
    """ Setup with serial parameters, low level IO"""

    ACKNOWLEDGE = chr(6)
    NEGATIVE_ACKNOWLEDGE = chr(21)

    def __init__(
        self,
        port: Union[int, str],
        baud_rate: int = 9600,
        hw_initialization: bool = True,
    ):
        """
        Initialize communication on the serial port where the pumps are located and initialize them
        Args:
            port: Serial port identifier
            baud_rate: Well, the baud rate :D
            hw_initialization: Whether each pumps has to be initialized. Note that this might be undesired!
        """
        if baud_rate not in serial.serialutil.SerialBase.BAUDRATES:
            raise InvalidConfiguration(f"Invalid baud rate provided {baud_rate}!")

        if isinstance(port, int):
            port = f"COM{port}"

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.lock = threading.Lock()

        try:
            # noinspection PyPep8
            self._serial = serial.Serial(
                port=port,
                baudrate=baud_rate,
                parity=PARITY_EVEN,
                stopbits=STOPBITS_ONE,
                bytesize=SEVENBITS,
                timeout=0.1,
            )  # type: Union[serial.serialposix.Serial, serial.serialwin32.Serial]
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration(
                f"Check serial port availability! [{port}]"
            ) from e

        # noinspection PyTypeChecker
        self.sio = io.TextIOWrapper(
            buffer=io.BufferedRWPair(self._serial, self._serial),
            line_buffering=True,
            newline="\r",
        )

        # This has to be run after each power cycle to assign addresses to pumps
        self.num_pump_connected = self._assign_pump_address()
        if hw_initialization:
            self._hw_init()

    def _assign_pump_address(self) -> int:
        """
        To be run on init, auto assign addresses to pumps based on their position on the daisy chain!
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        self._write("1a\r")
        reply = self._read_reply()
        if reply and reply[:1] == "1":
            # reply[1:2] should be the address of the last pump. However, this does not work reliably.
            # So here we enumerate the pumps explicitly instead
            last_pump = 0
            for pump_num, address in Protocol1Command.PUMP_ADDRESS.items():
                self._write(f"{address}UR\r")
                if "NV01" in self._read_reply():
                    last_pump = pump_num
                else:
                    break
            self.logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
            return int(last_pump)
        else:
            raise InvalidConfiguration(f"No pump available on {self._serial.port}")

    def _hw_init(self):
        """ Send to all pumps the HW initialization command (i.e. homing) """
        self._write(":XR\r")  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

    def _write(self, command: str):
        """ Writes a command to the pump """
        self.logger.debug(f"Sending {repr(command)}")
        try:
            self.sio.write(command)
        except serial.serialutil.SerialException as e:
            raise InvalidConfiguration from e

    def _read_reply(self) -> str:
        """ Reads the pump reply from serial communication """
        reply_string = self.sio.readline()
        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def parse_response(self, response: str) -> Tuple[bool, str]:
        """ Split a received line in its components: success, reply """
        if response[:1] == HamiltonPumpIO.ACKNOWLEDGE:
            self.logger.debug("Positive acknowledge received")
            success = True
        elif response[:1] == HamiltonPumpIO.NEGATIVE_ACKNOWLEDGE:
            self.logger.debug("Negative acknowledge received")
            success = False
        else:
            raise ML600Exception(f"This should not happen. Invalid reply: {response}!")

        return success, response[1:].rstrip()

    def reset_buffer(self):
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        try:
            self._serial.reset_input_buffer()
        except serial.PortNotOpenError as e:
            raise InvalidConfiguration from e

    def write_and_read_reply(self, command: list[Protocol1Command] or Protocol1Command) -> str:
        """ Main HamiltonPumpIO method.
        Sends a command to the pump, read the replies and returns it, optionally parsed """
        command_compiled = ""
        with self.lock:
            self.reset_buffer()
            if type(command) != list:
                command = [command]
            for com in command:
                command_compiled += com._compile()
            com_comp = com.compile(command_compiled)
            self._write(com.compile(command_compiled))
            response = self._read_reply()

        if not response:
            raise InvalidConfiguration(
                f"No response received from pump, check pump address! "
                f"(Currently set to {command[0].target_pump_num})"
            )

        # Parse reply
        success, parsed_response = self.parse_response(response)

        assert success is True  # :)
        return parsed_response

    @property
    def name(self) -> Optional[str]:
        """ This is used to provide a nice-looking default name to pumps based on their serial connection. """
        try:
            return self._serial.name
        except AttributeError:
            return None


class ML600Commands:
    """ Just a collection of commands. Grouped here to ease future, unlikely, changes. """

    PAUSE = Protocol1CommandTemplate(command="K", execute_command=False)
    RESUME = Protocol1CommandTemplate(command="$", execute_command=False)
    CLEAR_BUFFER = Protocol1CommandTemplate(command="V", execute_command=False)

    STATUS = Protocol1CommandTemplate(command="U")
    INIT_ALL = Protocol1CommandTemplate(command="X", optional_parameter="S")
    INIT_VALVE_ONLY = Protocol1CommandTemplate(command="LX")
    INIT_SYRINGE_ONLY = Protocol1CommandTemplate(command="X1", optional_parameter="S")

    # only works for pumps with two syringe drivers
    SET_VALVE_CONTINUOUS_DISPENSE = Protocol1CommandTemplate(command="LST19")
    # if there are two drivers, both sides can be selected
    SELECT_LEFT_SYRINGE = Protocol1CommandTemplate(command="B")
    SELECT_RIGHT_SYRINGE = Protocol1CommandTemplate(command="C")

    # SYRINGE POSITION
    PICKUP = Protocol1CommandTemplate(command="P", optional_parameter="S")
    DELIVER = Protocol1CommandTemplate(command="D", optional_parameter="S")
    ABSOLUTE_MOVE = Protocol1CommandTemplate(command="M", optional_parameter="S")

    # VALVE POSITION
    VALVE_TO_INLET = Protocol1CommandTemplate(command="I")
    VALVE_TO_OUTLET = Protocol1CommandTemplate(command="O")
    VALVE_TO_WASH = Protocol1CommandTemplate(command="W")
    VALVE_BY_NAME_CW = Protocol1CommandTemplate(command="LP0")
    VALVE_BY_NAME_CCW = Protocol1CommandTemplate(command="LP1")
    VALVE_BY_ANGLE_CW = Protocol1CommandTemplate(command="LA0")
    VALVE_BY_ANGLE_CCW = Protocol1CommandTemplate(command="LA1")

    # STATUS REQUEST
    # INFORMATION REQUEST -- these all returns Y/N/* where * means busy
    REQUEST_DONE = Protocol1CommandTemplate(command="F")
    SYRINGE_HAS_ERROR = Protocol1CommandTemplate(command="Z")
    VALVE_HAS_ERROR = Protocol1CommandTemplate(command="G")
    IS_SINGLE_SYRINGE = Protocol1CommandTemplate(command="H")
    # STATUS REQUEST  - these have complex responses, see relevant methods for details.
    STATUS_REQUEST = Protocol1CommandTemplate(command="E1")
    ERROR_REQUEST = Protocol1CommandTemplate(command="E2")
    TIMER_REQUEST = Protocol1CommandTemplate(command="E3")
    BUSY_STATUS = Protocol1CommandTemplate(command="T1")
    ERROR_STATUS = Protocol1CommandTemplate(command="T2")
    # PARAMETER REQUEST
    SYRINGE_DEFAULT_SPEED = Protocol1CommandTemplate(
        command="YQS"
    )  # 2-3692 seconds per stroke
    CURRENT_SYRINGE_POSITION = Protocol1CommandTemplate(command="YQP")  # 0-52800 steps
    SYRINGE_DEFAULT_BACKOFF = Protocol1CommandTemplate(command="YQP")  # 0-1000 steps
    CURRENT_VALVE_POSITION = Protocol1CommandTemplate(
        command="LQP"
    )  # 1-8 (see docs, Table 3.2.2)
    GET_RETURN_STEPS = Protocol1CommandTemplate(command="YQN")  # 0-1000 steps
    # PARAMETER CHANGE
    SET_RETURN_STEPS = Protocol1CommandTemplate(command="YSN")  # 0-1000
    # VALVE REQUEST
    VALVE_ANGLE = Protocol1CommandTemplate(command="LQA")  # 0-359 degrees
    VALVE_CONFIGURATION = Protocol1CommandTemplate(
        command="YQS"
    )  # 11-20 (see docs, Table 3.2.2)
    #Set valve speed
    SET_VALVE_SPEED = Protocol1CommandTemplate(command="LSF")  # 15-720 degrees per sec
    #Set valve speed
    GET_VALVE_SPEED = Protocol1CommandTemplate(command="LQF")
    # TIMER REQUEST
    TIMER_DELAY = Protocol1CommandTemplate(command="<T")  # 0–99999999 ms
    # FIRMWARE REQUEST
    FIRMWARE_VERSION = Protocol1CommandTemplate(
        command="U"
    )  # xxii.jj.k (ii major, jj minor, k revision)


class ML600:
    """" ML600 implementation according to docs. Tested on 61501-01 (single syringe).

    From docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """

    class ValvePositionName(IntEnum):
        """ Maps valve position to the corresponding number """

        POSITION_1 = 1
        # POSITION_2 = 2
        POSITION_3 = 3
        INPUT = 9  # 9 is default inlet, i.e. 1
        OUTPUT = 10  # 10 is default outlet, i.e. 3
        WASH = 11  # 11 is default wash, i.e. undefined

    VALID_SYRINGE_VOLUME = {
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        25.0,
        50.0,
    }

    def __init__(
        self,
        pump_io: HamiltonPumpIO,
        syringe_volume: float,
        address: int = 1,
        name: str = None,
    ):
        """

        Args:
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump
            syringe_volume: Volume of the syringe used, in ml
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important
        """
        self.pump_io = pump_io
        self.name = f"Pump {self.pump_io.name}:{address}" if name is None else name
        self.address: int = address
        if syringe_volume not in ML600.VALID_SYRINGE_VOLUME:
            raise InvalidConfiguration(
                f"The specified syringe volume ({syringe_volume}) does not seem to be valid!\n"
                f"The volume in ml has to be one of {ML600.VALID_SYRINGE_VOLUME}"
            )
        self.syringe_volume = syringe_volume
        self.steps_per_ml = 48000 / self.syringe_volume
        self.offset_steps = 24 # Steps added to each absolute move command, to decrease wear and tear at volume = 0, 24 is manual default

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by HamiltonPumpIO
        self.log.info(
            f"Connected to pump '{self.name}'  FW version: {self.firmware_version}!"
        )

    def send_command_and_read_reply(
        self,
        command_template: Protocol1CommandTemplate,
        command_value="",
        argument_value="",
    ) -> str:
        """ Sends a command based on its template and return the corresponding reply as str """
        return self.pump_io.write_and_read_reply(
            command_template.to_pump(self.address, command_value, argument_value)
        )

    def create_single_command(
            self,
            command_template: Protocol1CommandTemplate,
            command_value="",
            argument_value="",
    ) -> Protocol1Command:
        # if this holds a list of dictionaries, that specify
        """ This creates a single command of which a list (so multiple commands) can be sent to device. Just hand a
        list of multiple so created commands to """

        x = command_template.to_pump(self.address, command_value, argument_value)
        return x

    def send_multiple_commands(self, list_of_commands: [Protocol1Command]) -> str:
        return self.pump_io.write_and_read_reply(list_of_commands)

    def initialize_pump(self, speed: int = None):
        """
        Initialize both syringe and valve
        speed: 2-3692 is in seconds/stroke
        """
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(
                ML600Commands.INIT_ALL, argument_value=str(speed)
            )
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_ALL)

    def initialize_valve(self):
        """
        Initialize valve only
        """
        return self.send_command_and_read_reply(ML600Commands.INIT_VALVE_ONLY)

    def initialize_syringe(self, speed: int = None):
        """
        Initialize syringe only
        speed: 2-3692 is in seconds/stroke
        """
        if speed:
            assert 2 < speed < 3692
            return self.send_command_and_read_reply(
                ML600Commands.INIT_SYRINGE_ONLY, argument_value=str(speed)
            )
        else:
            return self.send_command_and_read_reply(ML600Commands.INIT_SYRINGE_ONLY)

    def flowrate_to_seconds_per_stroke(self, flowrate_in_ml_min: float):
        """
        Convert flow rates in ml/min to steps per seconds

        To determine the volume dispensed per step the total syringe volume is divided by
        48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
        length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
        example to dispense 9 mL from a 10 mL syringe you would determine the number of
        steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
        """
        assert flowrate_in_ml_min > 0
        flowrate_in_ml_sec = flowrate_in_ml_min / 60
        flowrate_in_steps_sec = flowrate_in_ml_sec * self.steps_per_ml
        seconds_per_stroke = round(48000 / flowrate_in_steps_sec)
        assert 2 <= seconds_per_stroke <= 3692
        return round(seconds_per_stroke)

    def _volume_to_step(self, volume_in_ml: float) -> int:
        return round(volume_in_ml * self.steps_per_ml) + self.offset_steps

    def _to_step_position(self, position: int, speed: int = ""):
        """ Absolute move to step position """
        return self.send_command_and_read_reply(
            ML600Commands.ABSOLUTE_MOVE, str(position), str(speed)
        )

    def to_volume(self, volume_in_ml: float, speed: int = ""):
        """ Absolute move to volume, so no matter what volume is now, it will move to this volume.
        This is bad for dosing, but good for general pumping"""
        self._to_step_position(self._volume_to_step(volume_in_ml), speed)
        self.log.debug(
            f"Pump {self.name} set to volume {volume_in_ml} at speed {speed}"
        )

    def pause(self):
        """ Pause any running command """
        return self.send_command_and_read_reply(ML600Commands.PAUSE)

    def resume(self):
        """ Resume any paused command """
        return self.send_command_and_read_reply(ML600Commands.RESUME)

    def stop(self):
        """ Stops and abort any running command """
        self.pause()
        return self.send_command_and_read_reply(ML600Commands.CLEAR_BUFFER)

    def wait_until_idle(self):
        """ Returns when no more commands are present in the pump buffer. """
        self.log.debug(f"Pump {self.name} wait until idle")
        while self.is_busy:
            time.sleep(0.001)

    @property
    def version(self) -> str:
        """ Returns the current firmware version reported by the pump """
        return self.send_command_and_read_reply(ML600Commands.STATUS)

    @property
    def is_idle(self) -> bool:
        """ Checks if the pump is idle (not really, actually check if the last command has ended) """
        return self.send_command_and_read_reply(ML600Commands.REQUEST_DONE) == "Y"

    @property
    def is_busy(self) -> bool:
        """ Not idle """
        return not self.is_idle

    @property
    def firmware_version(self) -> str:
        """ Return firmware version """
        return self.send_command_and_read_reply(ML600Commands.FIRMWARE_VERSION)

    @property
    def valve_position(self) -> ValvePositionName:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum """
        return ML600.ValvePositionName(
            int(self.send_command_and_read_reply(ML600Commands.CURRENT_VALVE_POSITION))
        )

    @valve_position.setter
    def valve_position(self, target_position: ValvePositionName):
        self.log.debug(f"{self.name} valve position set to {target_position.name}")
        self.send_command_and_read_reply(
            ML600Commands.VALVE_BY_NAME_CW, command_value=str(int(target_position))
        )
        self.wait_until_idle()

    @property
    def return_steps(self) -> int:
        """ Represent the position of the valve: getter returns Enum, setter needs Enum """
        return int(self.send_command_and_read_reply(ML600Commands.GET_RETURN_STEPS))

    @return_steps.setter
    def return_steps(self, target_steps: int):
        self.send_command_and_read_reply(
            ML600Commands.SET_RETURN_STEPS, command_value=str(int(target_steps))
        )

    def syringe_position(self):
        current_steps = (
            int(
                self.send_command_and_read_reply(ML600Commands.CURRENT_SYRINGE_POSITION)
            ) - self.offset_steps
        )
        return current_steps / self.steps_per_ml

    def _absolute_syringe_move(self, volume, flow_rate):
        """ Absolute move to volume, so no matter what volume is now, it will move to this volume.
        This is bad for dosing, but good for general pumping"""
        speed = self.flowrate_to_seconds_per_stroke(flow_rate)
        position = self._volume_to_step(volume)
        return self.create_single_command(ML600Commands.ABSOLUTE_MOVE, str(position), str(speed))

    def _relative_syringe_pickup(self, volume, flow_rate):
        """ relative volume pickup, Syringe will aspire a certain volume.
        This is good for dosing."""
        speed = self.flowrate_to_seconds_per_stroke(flow_rate)
        position = self._volume_to_step(volume)
        return self.create_single_command(ML600Commands.PICKUP, str(position), str(speed))

    def _relative_syringe_dispense(self, volume, flow_rate):
        """ relative volume dispense, Syringe will deliver a certain volume.
                This is good for dosing."""
        speed = self.flowrate_to_seconds_per_stroke(flow_rate)
        position = self._volume_to_step(volume)
        return self.create_single_command(ML600Commands.DELIVER, str(position), str(speed))

    def _orchestrated_pickup(self, volume, flowrate):
        """ pickup by moving valves and moving syringe to absolute volume"""
        fill_syringe = [self.create_single_command(ML600Commands.VALVE_TO_INLET),
                        self._absolute_syringe_move(volume, flowrate),
                        self.create_single_command(ML600Commands.VALVE_TO_OUTLET), ]
        return fill_syringe

    def pickup(self, volume, speed):
        """actually dispatch command. Use for moving valves and pick up solution"""
        self.send_multiple_commands(self._orchestrated_pickup(volume, speed))

    def _orchestrated_deliver(self, volume, speed_out):
        """deliver by moving valves and deliver solution"""
        deliver_from_syringe = [self.create_single_command(ML600Commands.VALVE_TO_OUTLET),
                                self._absolute_syringe_move(volume, speed_out),
                                self.create_single_command(ML600Commands.VALVE_TO_INLET), ]
        return deliver_from_syringe

    def deliver(self, volume, speed):
        """actually dispatch command. Use for moving valves and deliver up solution"""
        self.send_multiple_commands(self._orchestrated_deliver(volume, speed))

    def _fill_left_empty_right(self, delivery_speed):
        """ refills left syringe and deliuvers required flowrate from right"""
        # todo ensure it is double syringe
        self.wait_until_idle()
        single = self.send_command_and_read_reply(ML600Commands.IS_SINGLE_SYRINGE)
        assert single == 'N', f"Sorry, only works for dual syringes. answer is {single}"
        return self.send_multiple_commands([self.create_single_command(ML600Commands.SELECT_LEFT_SYRINGE),
                                            *self._orchestrated_pickup(self.syringe_volume, 2 * delivery_speed),
                                            self.create_single_command(ML600Commands.SELECT_RIGHT_SYRINGE),
                                            *self._orchestrated_deliver(0, delivery_speed)])

    def _empty_left_fill_right(self, delivery_speed):
        """ pump from left syringe at double speed and refill right syringe"""
        self.wait_until_idle()
        single = self.send_command_and_read_reply(ML600Commands.IS_SINGLE_SYRINGE)
        assert single == 'N', f"Sorry, only works for dual syringes. answer is {single}"
        return self.send_multiple_commands([self.create_single_command(ML600Commands.SELECT_LEFT_SYRINGE),
                                            *self._orchestrated_deliver(0, 2 * delivery_speed),
                                            self.create_single_command(ML600Commands.SELECT_RIGHT_SYRINGE),
                                            *self._orchestrated_pickup(0.5 * self.syringe_volume, delivery_speed)])

    def continuous_delivery(self, delivery_speed, volume_to_deliver):
        """ delivers continuoulsy at requested speed, be aware that there are short breaks due to valve switching"""
        self.wait_until_idle()
        single = self.send_command_and_read_reply(ML600Commands.IS_SINGLE_SYRINGE)
        assert single == 'N', f"Sorry, only works for dual syringes. answer is {single}"
        # make sure valves are set correctly for continuous dispense
        self.send_command_and_read_reply(ML600Commands.SET_VALVE_CONTINUOUS_DISPENSE)
        self.wait_until_idle()
        # set valve speed to as high as possible - thereby phases without pumping become short
        self.send_command_and_read_reply(ML600Commands.SET_VALVE_SPEED, command_value=720)
        self.wait_until_idle()
        # initialise counter
        volume_delivered = 0

        # check if the requested flowrate is actually doable at a reasonable accuracy and continuity
        single = self.flowrate_to_seconds_per_stroke(delivery_speed)
        double = self.flowrate_to_seconds_per_stroke(2 * delivery_speed)
        offset = (double - single) / single - 0.5
        if offset > 0.01:
            self.log.warning(f"The offset between your two syringes is {offset}, this should be 0 or very small."
                             f"consider using different syringe size for that flowrate and be aware that your flow will"
                             f"not be steady.")
        actual_flowrate = 60 * self.syringe_volume / single
        self.log.info(f"Your actual flow is {actual_flowrate}. Offset is due to rounding.")

        self._fill_left_empty_right(1)
        # idea is - along with HPLC pump:
        # 1) fill left, right syringe is empty ad does not move
        # while True:
        # 2) fill right syringe half-way, empty left completely, at double speed
        # 3) fill left at double speed, empty right at normAL, timing will be accurate since double volume mkoves at double speed
        while volume_delivered < volume_to_deliver:
            self.wait_until_idle()
            self._empty_left_fill_right(delivery_speed)
            self.wait_until_idle()
            self._fill_left_empty_right(delivery_speed)
            volume_delivered += self.syringe_volume

    # convenience function
    def refill_syringe(self, volume: float = None, flow_rate: float = 0, invert_input_output = False):
        self.log.debug('refilling syringe')
        # inverting input and output allows for initialization and correct finding of the 0 position when the desired
        # path has backpressure. additionally, solution that would normally go to waste (via reactor) is put back to
        # storage
        if not volume:
            volume = self.syringe_volume
        if invert_input_output:
            self.valve_position=self.ValvePositionName.OUTPUT
        else:
            self.valve_position=self.ValvePositionName.INPUT
        self.to_volume(volume, self.flowrate_to_seconds_per_stroke(flow_rate))

    # convenience function
    def deliver_from_syringe(self, flow_rate: float, volume: float = 0, invert_input_output = False):
        # inverting input and output allows for initialization and correct finding of the 0 position when the desired
        # path has backpressure. additionally, solution that would normally go to waste (via reactor) is put back to
        # storage
        self.log.debug('pumping from syringe')
        if invert_input_output:
            self.valve_position=self.ValvePositionName.INPUT
        else:
            self.valve_position=self.ValvePositionName.OUTPUT
        self.to_volume(volume, self.flowrate_to_seconds_per_stroke(flow_rate))


class TwoPumpAssembly(Thread):
    """
    Thread to control two pumps and have them generating a continuous flow.
    Note that the pumps should not be accessed directly when used in a TwoPumpAssembly!

    Notes: this needs to start a thread owned by the instance to control the pumps.
    The async version of this being possibly simpler w/ tasks and callback :)
    """

    def __init__(
        self, pump1: ML600, pump2: ML600, target_flowrate: float, init_seconds: int = 10
    ):
        super(TwoPumpAssembly, self).__init__()
        self._p1 = pump1
        self._p2 = pump2
        self.daemon = True
        self.cancelled = threading.Event()
        self._flowrate = target_flowrate
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        # How many seconds per stroke for first filling? application dependent, as fast as possible, but not too much.
        self.init_secs = init_seconds

        # While in principle possible, using syringes of different volumes is discouraged, hence...
        assert (
            pump1.syringe_volume == pump2.syringe_volume
        ), "Syringes w/ equal volume are needed for continuous flow!"
        # self._p1.initialize_pump()
        # self._p2.initialize_pump()

    @property
    def flowrate(self):
        return self._flowrate

    @flowrate.setter
    def flowrate(self, target_flowrate):
        if target_flowrate == 0:
            warnings.warn(
                "Cannot set flowrate to 0! Pump stopped instead, restart previous flowrate with resume!"
            )
            self.cancel()
        else:
            self._flowrate = target_flowrate

        # This will stop current movement, make wait_for_both_pumps() return and move on w/ updated speed
        self._p1.stop()
        self._p2.stop()

    def wait_for_both_pumps(self):
        """ Custom waiting method to wait a shorter time than normal (for better sync) """
        while self._p1.is_busy or self._p2.is_busy:
            time.sleep(0.01)  # 10ms sounds reasonable to me
        self.log.debug("Pumps ready!")

    def _speed(self):
        speed = self._p1.flowrate_to_seconds_per_stroke(self._flowrate)
        self.log.debug(f"Speed calculated as {speed}")
        return speed

    def execute_stroke(
        self, pump_full: ML600, pump_empty: ML600, speed_s_per_stroke: int
    ):
        # Logic is a bit complex here to ensure pause-less pumping
        # This needs the pump that withdraws to move faster than the pumping one. no way around.

        # First start pumping with the full syringe already prepared
        pump_full.to_volume(0, speed=speed_s_per_stroke)
        self.log.debug("Pumping...")
        # Then start refilling the empty one
        pump_empty.valve_position = pump_empty.ValvePositionName.INPUT
        # And do that fast so that we finish refill before the pumping is over
        pump_empty.to_volume(pump_empty.syringe_volume, speed=speed_s_per_stroke - 5)
        pump_empty.wait_until_idle()
        # This allows us to set the reight pump position on the pump that was empty (not full and ready for next cycle)
        pump_empty.valve_position = pump_empty.ValvePositionName.OUTPUT
        pump_full.wait_until_idle()

    def run(self):
        """Overloaded Thread.run, runs the update
        method once per every 10 milliseconds."""
        # First initialize with init_secs speed...
        self._p1.to_volume(self._p1.syringe_volume, speed=self.init_secs)
        self._p1.wait_until_idle()
        self._p1.valve_position = self._p1.ValvePositionName.OUTPUT
        self.log.info("Pumps initialized for continuous pumping!")

        while True:
            while not self.cancelled.is_set():
                self.execute_stroke(
                    self._p1, self._p2, speed_s_per_stroke=self._speed()
                )
                self.execute_stroke(
                    self._p2, self._p1, speed_s_per_stroke=self._speed()
                )

    def cancel(self):
        """ Cancel continuous-pumping assembly """
        self.cancelled.set()
        self._p1.stop()
        self._p2.stop()

    def resume(self):
        """ Resume continuous-pumping assembly """
        self.cancelled.clear()

    def stop_and_return_solution_to_container(self):
        """ Let´s not waste our precious stock solutions ;) """
        self.cancel()
        self.log.info(
            "Returning the solution currently loaded in the syringes back to the inlet.\n"
            "Make sure the container is not removed yet!"
        )
        # Valve to input
        self._p1.valve_position = self._p1.ValvePositionName.INPUT
        self._p2.valve_position = self._p2.ValvePositionName.INPUT
        self.wait_for_both_pumps()
        # Volume to 0 with the init speed (supposedly safe for this application)
        self._p1.to_volume(0, speed=self.init_secs)
        self._p2.to_volume(0, speed=self.init_secs)
        self.wait_for_both_pumps()
        self.log.info("Pump flushing completed!")


if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger(__name__ + ".TwoPumpAssembly")
    log.setLevel(logging.DEBUG)
    log = logging.getLogger(__name__ + ".ML600")
    log.setLevel(logging.DEBUG)
    pump_connection = HamiltonPumpIO(41)
    test1 = ML600(pump_connection, syringe_volume=5, address=1)
    test2 = ML600(pump_connection, syringe_volume=5, address=2)
    metapump = TwoPumpAssembly(test1, test2, target_flowrate=15, init_seconds=20)
    metapump.start()
    input()
