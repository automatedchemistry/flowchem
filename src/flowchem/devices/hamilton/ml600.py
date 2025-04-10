"""Control Hamilton ML600 syringe pump via the protocol1/RNO+."""
from __future__ import annotations

import asyncio
import string
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aioserial
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.hamilton.ml600_pump import ML600Pump
from flowchem.devices.hamilton.ml600_valve import ML600LeftValve, ML600RightValve
from flowchem.utils.exceptions import InvalidConfigurationError, DeviceError
from flowchem.utils.people import dario, jakob, wei_hsin

if TYPE_CHECKING:
    import pint


# i.e. PUMP_ADDRESS = {1: 'a', 2: 'b', 3: 'c', 4: 'd', ..., 16: 'p'}
# Note ':' is used for broadcast within the daisy chain.
PUMP_ADDRESS = dict(enumerate(string.ascii_lowercase[:16], start=1))


@dataclass
class Protocol1Command:
    """Class representing a pump command and its expected reply."""

    command: str
    target_pump_num: int = 1
    target_component: str = ""
    command_value: str = ""
    optional_parameter: str = ""
    parameter_value: str = ""
    execution_command: str = "R"  # Execute

    def compile(self) -> str:
        """Create actual command byte by prepending pump address to command and appending executing command."""
        compiled_command = (
            f"{PUMP_ADDRESS[self.target_pump_num]}"
            f"{self.target_component}"
            f"{self.command}{self.command_value}"
        )

        if self.parameter_value:
            compiled_command += f"{self.optional_parameter}{self.parameter_value}"

        return compiled_command + self.execution_command


class HamiltonPumpIO:
    """Setup with serial parameters, low level IO."""

    ACKNOWLEDGE = chr(6)
    NEGATIVE_ACKNOWLEDGE = chr(21)
    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_ODD,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.SEVENBITS,
    }

    def __init__(self, aio_port: aioserial.Serial) -> None:
        """Initialize serial port, not pumps."""
        self._serial = aio_port
        self.num_pump_connected: int | None = (
            None  # Set by `HamiltonPumpIO.initialize()`
        )

    @classmethod
    def from_config(cls, config):
        """Create HamiltonPumpIO from config."""
        configuration = HamiltonPumpIO.DEFAULT_CONFIG | config

        try:
            serial_object = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the pump on the port <{configuration.get('port')}>"
            ) from serial_exception

        return cls(serial_object)

    async def initialize(self, hw_initialization: bool = True):
        """Ensure connection with pump and initialize it (if hw_initialization is True)."""
        self.num_pump_connected = await self._assign_pump_address()
        if hw_initialization:
            await self.all_hw_init()  # initialization take more than 8.5 sec for one instrument
            await asyncio.sleep(8)  # this might be necessary due to checking request_done sometime fail with "" return

    async def _assign_pump_address(self) -> int:
        """Auto assign pump addresses.

        To be run on init, auto assign addresses to pumps based on their position in the daisy chain.
        A custom command syntax with no addresses is used here so read and write has been rewritten
        """
        try:
            # the command for an unknown reason often replies wrongly on first attempt. therefore, this is done twice
            await self._write_async(b"1a\r")
            await self._read_reply_async()
            await self._write_async(b"1a\r")
        except aioserial.SerialException as e:
            raise InvalidConfigurationError from e

        reply = await self._read_reply_async()
        if not reply or reply[:1] != "1":
            raise InvalidConfigurationError(f"No pump found on {self._serial.port}")
        # reply[1:2] should be the address of the last pump. However, this does not work reliably.
        # So here we enumerate the pumps explicitly instead
        last_pump = 0
        for pump_num, address in PUMP_ADDRESS.items():
            await self._write_async(f"{address}UR\r".encode("ascii"))
            if "NV01" in await self._read_reply_async():
                last_pump = pump_num
            else:
                break
        logger.debug(f"Found {last_pump} pumps on {self._serial.port}!")
        return int(last_pump)

    async def all_hw_init(self):
        """Send to all pumps the HW initialization command (i.e. homing)."""
        await self._write_async(b":K\r")
        await self._write_async(b":V\r")
        await self._write_async(b":#SP2\r")
        await self._write_async(b":XR\r")  # Broadcast: initialize + execute
        # Note: no need to consume reply here because there is none (since we are using broadcast)

    async def _write_async(self, command: bytes):
        """Write a command to the pump."""
        await self._serial.write_async(command)
        logger.debug(f"Command {command!r} sent!")

    async def _read_reply_async(self) -> str:
        """Read the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.debug(f"Reply received: {reply_string}")
        return reply_string.decode("ascii")

    def _parse_response(self, response: str) -> str:
        """Split a received line in its components: status, reply."""
        status, reply = response[:1], response[1:]

        assert status in (self.ACKNOWLEDGE, self.NEGATIVE_ACKNOWLEDGE)
        if status == self.NEGATIVE_ACKNOWLEDGE:
            logger.warning("Negative acknowledge received")
            warnings.warn(
                "Negative acknowledge reply: check command syntax!",
                stacklevel=2,
            )

        return reply.rstrip()  # removes trailing <cr>

    def _translate_ascii_to_binary(self, reply: str):
        binary_representation = ''.join(format(byte, '08b') for byte in reply.encode('ascii'))[::-1]
        return binary_representation

        # binary_list = []
        # [binary_list.append(format(byte, '08b')[::-1]) for byte in reply.encode('ascii')]
        # all_status = binary_list[0]

    async def write_and_read_reply_async(self, command: Protocol1Command) -> str:
        """Send a command to the pump, read the replies and returns it, optionally parsed."""
        self._serial.reset_input_buffer()
        await self._write_async(f"{command.compile()}\r".encode("ascii"))
        response = await self._read_reply_async()

        if not response:
            raise InvalidConfigurationError(
                f"No response received from pump! "
                f"Maybe wrong pump address? (Set to {command.target_pump_num})"
            )

        return self._parse_response(response)


class ML600(FlowchemDevice):
    """ML600 implementation according to manufacturer docs. Tested on a 61501-01 (i.e. single syringe system).

    From manufacturer docs:
    To determine the volume dispensed per step the total syringe volume is divided by
    48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
    length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
    example to dispense 9 mL from a 10 mL syringe you would determine the number of
    steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
    """

    DEFAULT_CONFIG = {
        "default_infuse_rate": "1 ml/min",
        "default_withdraw_rate": "1 ml/min",
    }

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances: set[HamiltonPumpIO] = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy-chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).

    # Only Hamilton syringes are compatible w/ the ML600, and they come on a limited set of sizes. (Values in ml)
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
        syringe_volume: str,
        name: str,
        address: int = 1,
        **config,
    ) -> None:
        """Default constructor, needs an HamiltonPumpIO object. See from_config() class method for config-based init.

        Args:
        ----
            pump_io: An HamiltonPumpIO w/ serial connection to the daisy chain w/ target pump.
            syringe_volume: Volume of the syringe used, either a Quantity or number in ml.
            address: number of pump in array, 1 for first one, auto-assigned on init based on position.
            name: 'cause naming stuff is important.
        """
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Hamilton",
            model="ML600",
        )
        # HamiltonPumpIO
        self.pump_io = pump_io
        ML600._io_instances.add(self.pump_io)  # See above for details.

        # Pump address is the pump sequence number if in chain. Count starts at 1, default.
        self.address = int(address)

        # Syringe pumps only perform linear movement, and the volume displaced is function of the syringe loaded.
        try:
            # todo: set syringe_volume to a dict/str??
            self.syringe_volume = ureg.Quantity(syringe_volume)
        except AttributeError as attribute_error:
            logger.error(f"Invalid syringe volume {syringe_volume}!")
            raise InvalidConfigurationError(
                "Invalid syringe volume provided."
                "The syringe volume is a string with units! e.g. '5 ml'"
            ) from attribute_error

        if self.syringe_volume.m_as("ml") not in ML600.VALID_SYRINGE_VOLUME:
            raise InvalidConfigurationError(
                f"The specified syringe volume ({syringe_volume}) is invalid!\n"
                f"The volume (in ml) has to be one of {ML600.VALID_SYRINGE_VOLUME}"
            )

        self._steps_per_ml = ureg.Quantity(f"{48000 / self.syringe_volume} step")
        # self._offset_steps = 100  # Steps added to each absolute move command, to decrease wear and tear at volume = 0
        # self._max_vol = (48000 - self._offset_steps) * ureg.step / self._steps_per_ml
        # logger.warning(f"due to offset steps is {self._offset_steps}. the max_vol : {self._max_vol}")
        # This enables to configure on per-pump basis uncommon parameters
        self.config = ML600.DEFAULT_CONFIG | config
        self.dual_syringe = False

    @classmethod
    def from_config(cls, **config):
        """Create instances via config file."""
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of HamiltonPumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        pumpio = None
        for obj in ML600._io_instances:
            # noinspection PyProtectedMember
            if obj._serial.port == config.get("port"):
                pumpio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if pumpio is None:
            # Remove ML600-specific keys to only have HamiltonPumpIO's kwargs
            config_for_pumpio = {
                k: v
                for k, v in config.items()
                if k not in ("syringe_volume", "address", "name")
            }
            pumpio = HamiltonPumpIO.from_config(config_for_pumpio)

        return cls(
            pumpio,
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name", ""),
        )

    async def get_return_steps(self) -> int:
        """ Gives the defined return steps for syringe movement """
        reply = await self.send_command_and_read_reply(Protocol1Command(command="YQN"))
        return int(reply)

    async def set_return_steps(self, return_steps: int):
        """
        Return steps are used to compensate for the mechanical drive system backlash,
        independent of syringe size and default is 24 steps.
        The return step should be in # 0-1000 steps.
        """
        # waiting is necessary since this happens on (class) initialisation
        target_steps = str(int(return_steps))
        await self.wait_until_system_idle()  #todo: needs???
        await self.send_command_and_read_reply(Protocol1Command(
            command="YSN", command_value=target_steps))

    async def initialize(self, init_speed: str = "200 sec / stroke"):
        """Initialize pump and its components."""
        await self.pump_io.initialize()
        await self.wait_until_system_idle()
        # Test connectivity by querying the pump's firmware version
        self.device_info.version = await self.version()
        logger.info(
            f"Connected to Hamilton ML600 {self.name} - FW version: {self.device_info.version}!",
        )
        self.dual_syringe = not await self.is_single_syringe()
        await self.general_status_info()

        # Add device components
        if self.dual_syringe:
            self.components.extend([ML600Pump("left_pump", self, "B"), ML600Pump("right_pump", self, "C"),
                                    ML600LeftValve("left_valve", self), ML600RightValve("right_valve", self)])
        else:
            self.components.extend([ML600Pump("pump", self), ML600LeftValve("valve", self)])

    async def send_command_and_read_reply(self, command: Protocol1Command) -> str:
        """Send a command to the pump. Here we just add the right pump number."""
        command.target_pump_num = self.address
        return await self.pump_io.write_and_read_reply_async(command)

    def _validate_speed(self, speed: pint.Quantity | None) -> str:
        """Validate the speed.

        Given a speed (seconds/stroke) returns a valid value for it, and a warning if out of bounds.
        """
        # Validated speeds are used as command argument, with empty string being the default for None
        if speed is None:
            return ""

        # Alert if out of bounds but don't raise exceptions, according to general philosophy.
        # Target flow rate too high
        if speed < ureg.Quantity("2 sec/stroke"):
            speed = ureg.Quantity("2 sec/stroke")
            warnings.warn(
                f"Desired speed ({speed}) is unachievable!"
                f"Set to {self._seconds_per_stroke_to_flowrate(speed)}"
                f"Wrong units? A bigger syringe is needed?",
                stacklevel=2,
            )

        # Target flow rate too low
        if speed > ureg.Quantity("3692 sec/stroke"):
            speed = ureg.Quantity("3692 sec/stroke")
            warnings.warn(
                f"Desired speed ({speed}) is unachievable!"
                f"Set to {self._seconds_per_stroke_to_flowrate(speed)}"
                f"Wrong units? A smaller syringe is needed?",
                stacklevel=2,
            )

        return str(round(speed.m_as("sec / stroke")))

    async def initialize_pump(self, speed: pint.Quantity | None = None):
        """Initialize both syringe and valve. speed: 2-3692 in seconds/stroke"""
        init_pump = Protocol1Command(
            command="X",
            optional_parameter="S",
            parameter_value=self._validate_speed(speed),
        )
        return await self.send_command_and_read_reply(init_pump)

    async def initialize_valve(self):
        """Initialize valve only."""
        return await self.send_command_and_read_reply(Protocol1Command(command="LX"))

    async def initialize_syringe(self, speed: pint.Quantity | None = None):
        """Initialize syringe only. speed: 2-3692 in seconds/stroke"""
        init_syringe = Protocol1Command(
            command="X1",
            optional_parameter="S",
            parameter_value=self._validate_speed(speed),
        )
        return await self.send_command_and_read_reply(init_syringe)

    def _flowrate_to_seconds_per_stroke(self, flowrate: pint.Quantity):
        """Convert flow rates to steps per seconds.

        To determine the volume dispensed per step the total syringe volume is divided by
        48,000 steps. All Hamilton instrument syringes are designed with a 60 mm stroke
        length and the Microlab 600 is designed to move 60 mm in 48,000 steps. For
        example to dispense 9 mL from a 10 mL syringe you would determine the number of
        steps by multiplying 48000 steps (9 mL/10 mL) to get 43,200 steps.
        """
        flowrate_in_steps_sec = flowrate * self._steps_per_ml
        return (1 / flowrate_in_steps_sec).to("second/stroke")

    def _seconds_per_stroke_to_flowrate(self, second_per_stroke) -> float:
        """Convert seconds per stroke to flow rate."""
        flowrate = 1 / (second_per_stroke * self._steps_per_ml)
        return flowrate.to("ml/min")

    def _volume_to_step_position(self, volume: pint.Quantity) -> int:
        """Convert a volume to a step position."""
        # todo: different syringes
        # noinspection PyArgumentEqualDefault
        steps = volume * self._steps_per_ml
        return round(steps.m_as("steps"))

    async def get_current_volume(self, pump: str) -> pint.Quantity:
        """Return current syringe position in ml."""
        syringe_pos = await self.send_command_and_read_reply(
            Protocol1Command(command="YQP",target_component=pump),)

        current_steps = int(syringe_pos) * ureg.step
        return current_steps / self._steps_per_ml

    async def set_to_volume(self, target_volume: pint.Quantity, rate: pint.Quantity, pump: str):
        """Absolute move to target volume provided by set step position and speed."""
        # in pump component, it already checked the desired volume setting is possible to execute or not
        speed = self._flowrate_to_seconds_per_stroke(rate)  # in seconds/stroke
        set_speed = self._validate_speed(speed)  # check desired speed is possible to execute
        position = self._volume_to_step_position(target_volume)
        logger.debug(f"Pump {self.name} set to volume {target_volume} at speed {set_speed}")

        abs_move_cmd = Protocol1Command(
            command="M",
            optional_parameter="S",
            command_value=str(position),
            parameter_value=set_speed,
            target_component=pump
        )
        return await self.send_command_and_read_reply(abs_move_cmd)

    async def pause(self, pump: str):
        """Pause any running command."""
        return await self.send_command_and_read_reply(
            Protocol1Command(command="", target_component=pump, execution_command="K"),)

    async def resume(self, pump: str):
        """Resume any paused command."""
        return await self.send_command_and_read_reply(
            Protocol1Command(command="", target_component=pump, execution_command="$"),)

    async def stop(self, pump: str) -> bool:
        """Stop and abort any running command."""
        await self.pause(pump)
        await self.send_command_and_read_reply(
            Protocol1Command(command="", target_component=pump, execution_command="V"),)
        return True  # Todo: need?

    async def get_pump_status(self, pump: str = "") -> bool:
        """Ture means pump is busy. False means pump is idle."""
        checking_mapping = {"B": 1, "C": 3}
        pump = "B" if not pump else pump
        status = await self.system_status(checking_mapping[pump])
        logger.info(f"pump {pump} is busy: {status}")
        return status

    async def get_valve_status(self, valve: str = "") -> bool:
        """Ture means valve is busy. False means valve is idle."""
        checking_mapping = {"B": 0, "C": 2}
        valve = "B" if not valve else valve
        status = await self.system_status(checking_mapping[valve])
        logger.info(f"valve {valve} is busy: {status}")
        return status

    async def system_status(self, component: int = -1) -> bool | dict[str: bool]:
        """
        Represent the status of specific component. True means busy; False meaens idle.
        Return status of all parts of instrument in dictionary.
        """
        reply = await self.send_command_and_read_reply(
                Protocol1Command(command="T1", execution_command=""))
        all_status = ''.join(format(byte, '08b') for byte in reply.encode('ascii'))[::-1]
        # 1 is true and 0 is false according to the manual; but the real signal is opposite.
        if -1 < component < 5:
            return all_status[component] == "0"

        value_map = {0: "left_valve busy", 1: "left_pump busy",
                     2: "right_valve busy", 3: "right_pump busy",
                     4: "step_active busy", 5: "handprobe_active busy"}
        status = {}
        for key in value_map:
            logger.debug(f"{value_map[key]} : {all_status[key] == '0'}")
            status[value_map[key]] = all_status[key] == "0"
        return status

    async def general_status_info(self, component: int = -1) -> bool | dict[str: bool]:
        # todo: this command will reset the error of syntax and instrument, use others error monitoring method
        reply = await self.send_command_and_read_reply(
            Protocol1Command(command="E1", execution_command=""))
        binary_representation = ''.join(format(byte, '08b') for byte in reply.encode('ascii'))[::-1]

        if -1 < component < 5:
            # for specific component
            return binary_representation[component] == "1"

        value_map = {0: "instrument idle, command buffer isn't empty",
                     1: "syringe(s) busy",
                     2: "valve(s) busy",
                     3: "syntax error",
                     4: "valve or syringe error"}
        status = {}
        for key in value_map:
            status[value_map[key]] = binary_representation[key] == '1'
            logger.info(f"{value_map[key]} : {status[value_map[key]]}")

            if status[value_map[key]]:
                raise DeviceError((
                    f"{value_map[key]} shows {status[value_map[key]]}. Check! "
                ))
        return status

    async def wait_until_system_idle(self):
        """Return when no more commands are present in the pump buffer."""
        logger.debug(f"ML600 {self.name} wait until idle...")
        while not await self.is_system_idle():
            await asyncio.sleep(0.1)
        logger.debug(f"...ML600 {self.name} idle now!")

    async def is_system_idle(self) -> bool:
        """Check if the pump is idle (actually check if the last command has ended)."""
        return (
            await self.send_command_and_read_reply(
                Protocol1Command(command="F", execution_command="")) == "Y"
        )

    async def is_single_syringe(self) -> bool:
        """Determine if single or dual syringe"""
        is_single = await self.send_command_and_read_reply(
            Protocol1Command(command="H", execution_command=""),
        )
        if is_single == "N":
            return False
        elif is_single == "Y":
            return True
        else:
            raise InvalidConfigurationError("Neither single nor dual syringe - somethings wrong")

    async def version(self) -> str:
        """Return the current firmware version reported by the pump."""
        return await self.send_command_and_read_reply(Protocol1Command(command="U"))

    async def get_valve_angle(self, valve_code: str = "") -> int:
        """get the angle of the valve: 0-359 degrees"""
        reply = await self.send_command_and_read_reply(Protocol1Command(command="LQA", target_component=valve_code))
        return int(reply)

    async def set_valve_angle(self,
                              target_angle: int,
                              valve_code: str = "",
                              wait_for_movement_end: bool = True) -> int:
        """set the angle of the valve"""
        await self.send_command_and_read_reply(
            Protocol1Command(command="LA0", target_component=valve_code, command_value=str(target_angle))
        )
        logger.debug(f"{self.name} valve position set to {target_angle} degree")
        if wait_for_movement_end:
            while await self.get_valve_status(valve_code):
                await asyncio.sleep(0.1)
        return True

    async def get_valve_position(self, valve_code: str = "") -> str:
        """Represent the position of the valve: getter returns Enum, setter needs Enum."""
        # todo: set the dispense mode
        return await self.send_command_and_read_reply(Protocol1Command(command="LQP",  target_component=valve_code))

    async def set_valve_position(self,
                                 target_position: str,
                                 valve_code: str = "",
                                 wait_for_movement_end: bool = True,) -> bool:
        """Set valve position.

        wait_for_movement_end is defaulted to True as it is a common mistake not to wait...
        """
        # todo: set the dispense mode
        await self.send_command_and_read_reply(
            Protocol1Command(command="LP0", command_value=target_position, target_component=valve_code),
        )
        logger.debug(f"{self.name} valve position set to position {target_position}")
        if wait_for_movement_end:
            while await self.get_valve_status(valve_code):
                await asyncio.sleep(0.1)
        return True

async def main():
    conf = {
        "port": "COM11",
        "address": 1,
        "name": "test1",
        "syringe_volume": "5 mL",
    }
    pump1 = ML600.from_config(**conf)
    # await pump1.initialize()
    print(await pump1.get_valve_status())
    print(await pump1.get_valve_angle("B"))
    await pump1.set_valve_angle()

if __name__ == "__main__":
    # asyncio.run(main())

    conf = {
        "port": "COM11",
        "address": 1,
        "name": "test1",
        "syringe_volume": "5 mL",
    }
    ml600_devices = ML600.from_config(**conf)
    asyncio.run(ml600_devices.initialize())
    print(asyncio.run(ml600_devices.get_valve_status()))
    print(asyncio.run(ml600_devices.get_valve_angle("B")))
    asyncio.run(ml600_devices.set_valve_angle(270, "B"))
    pump, valve = ml600_devices.components
    print(asyncio.run(valve.get_position()))