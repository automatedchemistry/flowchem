"""Knauer pump control."""
import asyncio
import warnings
from enum import Enum

import pint
from loguru import logger

from flowchem import ureg
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.knauer._common import KnauerEthernetDevice
from flowchem.devices.knauer.azura_compact_pump import AzuraCompactPump
from flowchem.devices.knauer.azura_compact_sensor import AzuraCompactSensor
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import dario, jakob, wei_hsin

FLOW = "FLOW"  # 0-50000 µL/min, int only!
HEADTYPE = "HEADTYPE"  # 10, 50 ml. Value refers to the highest flow rate in ml/min
PMIN10 = "PMIN10"  # 0-400 in 0.1 MPa, use to avoid running dry
PMIN50 = "PMIN50"  # 0-150 in 0.1 MPa, use to avoid running dry
PMAX10 = "PMAX10"  # 0-400 in 0.1 MPa, chosen automatically by selecting pump head
PMAX50 = "PMAX50"  # 0-150 in 0.1 MPa, chosen automatically by selecting pump head
IMIN10 = "IMIN10"  # 0-100 minimum motor current
IMIN50 = "IMIN50"  # 0-100 minimum motor current
STARTLEVEL = "STARTLEVEL"  # 0, 1 configures start. 0 -> only start pump when shorted to GND, 1 -> always allow start
ERRIO = "ERRIO"  # 0, 1 write/read error in/output ??? sets errio either 1 or 0, reports errio:ok
STARTMODE = "STARTMODE"  # 0, 1; 0=pause pump after switch on, 1=start immediately with previous set flow rate
ADJ10 = "ADJ10"  # 100-2000
ADJ50 = "ADJ50"  # 100-2000
CORR10 = "CORR10"  # 0-300
CORR50 = "CORR50"  # 0-300
EXTFLOW = "EXTFLOW?"
IMOTOR = "IMOTOR"  # motor current in relative units 0-100
PRESSURE = "PRESSURE?"  # reads the pressure in 0.1 MPa
ERRORS = "ERRORS"  # displays last 5 error codes
EXTCONTR = "EXTCONTR"  # allows flow control via analog input
LOCAL = "LOCAL"  # no parameter, releases pump to manual control
REMOTE = "REMOTE"  # manual param input prevented
PUMP_ON = "ON"  # starts flow
PUMP_OFF = "OFF"  # stops flow


class AzuraPumpHeads(Enum):
    """Two Pump heads are available for the Azura: 50 mL/min and 10 mL/min."""

    FLOWRATE_FIFTY_ML = 50
    FLOWRATE_TEN_ML = 10


# noinspection DuplicatedCode
class AzuraCompact(KnauerEthernetDevice, FlowchemDevice):
    """
    Control module for Knauer Azura Compact pumps.

    This class handles the initialization, control, and communication with the Knauer Azura Compact pumps.
    It includes methods to set and get parameters such as flow rate, pressure, and pump head type.
    The class supports asynchronous operations to ensure non-blocking communication with the device.

    Attributes:
        ip_address (str): The IP address of the pump.
        mac_address (str): The MAC address of the pump.
        max_pressure (str): Maximum pressure limit for the pump.
        min_pressure (str): Minimum pressure limit for the pump.

    Methods:
        initialize(): Initialize connection and configure the pump.
        error_present(reply: str) -> bool: Check if there are errors in the device's reply.
        create_and_send_command(message, setpoint: int | None = None, setpoint_range: tuple | None = None): Create and
        send a command to the pump.
        get_headtype() -> AzuraPumpHeads: Return the pump's head type.
        set_headtype(head_type: AzuraPumpHeads): Set the pump's head type.
        get_flow_rate() -> float: Get the current flow rate in ml/min.
        set_flow_rate(rate: pint.Quantity): Set the flow rate.
        get_minimum_pressure(): Get the minimum pressure setting.
        set_minimum_pressure(value: str = "0 bar"): Set the minimum pressure.
        get_maximum_pressure() -> str: Get the maximum pressure setting.
        set_maximum_pressure(value: str): Set the maximum pressure.
        set_minimum_motor_current(setpoint=None): Set the minimum motor current.
        is_start_in_required(): Check if START IN is required for the pump to operate.
        require_start_in(value: bool = True): Configure START IN requirement.
        is_autostart_enabled(): Check if autostart is enabled.
        enable_autostart(value: bool = True): Enable or disable autostart.
        get_adjusting_factor(): Get the adjusting factor.
        set_adjusting_factor(setpoint: int | None = None): Set the adjusting factor.
        get_correction_factor(): Get the correction factor.
        set_correction_factor(setpoint=None): Set the correction factor.
        read_pressure() -> pint.Quantity: Read the current pressure from the sensor.
        read_extflow() -> float: Read the external flow rate from analog input.
        read_errors() -> list[int]: Read the last 5 error codes.
        read_motor_current(): Read the motor current in percent.
        infuse(): Start the pump.
        stop(): Stop the pump.
        is_running(): Check if the pump is running.
        set_local(state: bool = True): Relinquish remote control.
        remote_control(state: bool = True): Enable or disable remote control.
        is_analog_control_enabled(): Check if analog control is enabled.
        enable_analog_control(value: bool): Enable or disable external flow control via analog input.
    """

    def __init__(
        self,
        ip_address=None,
        mac_address=None,
        max_pressure: str = "",
        min_pressure: str = "",
        **kwargs,
    ):
        super().__init__(ip_address, mac_address, **kwargs)
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="knauer",
            model="Azura Compact",
        )
        self.eol = b"\n\r"

        # All the following are set upon initialize()
        self.max_allowed_pressure = 0
        self.max_allowed_flow = 0
        self._headtype = None
        self._running: bool = None  # type: ignore
        self._pressure_max = max_pressure
        self._pressure_min = min_pressure

        self.rate = ureg.parse_expression("0 ml/min")

    async def initialize(self):
        """Initialize connection."""
        # Here the magic happens...
        await super().initialize()

        # Here it is checked that the device is a pump and not a valve
        await self.get_headtype()
        # Place pump in remote control
        await self.remote_control()
        # Also ensure rest state is not pumping.
        await self.stop()

        if self._pressure_max:
            await self.set_maximum_pressure(self._pressure_max)
        if self._pressure_min:
            await self.set_minimum_pressure(self._pressure_min)

        # Set Pump and Sensor components.
        self.components.extend(
            [AzuraCompactPump("pump", self), AzuraCompactSensor("pressure", self)]
        )

    @staticmethod
    def error_present(reply: str) -> bool:
        """Return True if there are errors, False otherwise. Warns for errors."""
        # ERRORS: is the expected answer to read_errors()
        if not reply.startswith("ERROR") or reply.startswith("ERRORS:"):
            return False

        if "ERROR:1" in reply:
            warnings.warn("Invalid message sent to device.\n", stacklevel=2)

        elif "ERROR:2" in reply:
            warnings.warn(
                "Setpoint refused by device.\n" "Refer to manual for allowed values.\n",
                stacklevel=2,
            )
        else:
            warnings.warn("Unspecified error detected!")
        return True

    async def _transmit_and_parse_reply(self, message: str) -> str:
        """Send command and receive reply.

        Deals with all communication based stuff and checks that the valve is of expected type.
        :param message:
        :return: reply: str
        """
        reply = await self._send_and_receive(message)
        if self.error_present(reply):
            return ""

        # Setpoint ok
        if ":OK" in reply:
            logger.debug("setpoint successfully set!")
            return "OK"

        # Replies to 'VALUE?' are in the format 'VALUE:'
        if message[:-1] in reply:
            logger.debug(f"setpoint successfully acquired, value={reply}")
            # Last value after colon
            return reply.split(":")[-1]

        # No reply
        if not reply:
            warnings.warn("No reply received")
            return ""

        warnings.warn(f"Unrecognized reply: {reply}")
        return reply

    async def create_and_send_command(
        self,
        message,
        setpoint: int | None = None,
        setpoint_range: tuple | None = None,
    ):
        """Create and sends a message from the command.

        If setpoint is given, then the command is appended with :value
        If not setpoint is given, a "?" is added for getter syntax

        e.g. message = "HEADTYPE"
        no setpoint -> sends "HEADTYPE?"
        w/ setpoint -> sends "HEADTYPE:<setpoint_value>"
        """
        # GETTER
        if setpoint is None:
            return await self._transmit_and_parse_reply(message + "?")

        # SETTER with range
        if setpoint_range:
            if setpoint in range(*setpoint_range):
                return await self._transmit_and_parse_reply(
                    message + ":" + str(setpoint),
                )

            warnings.warn(
                f"The setpoint provided {setpoint} is not valid for the command "
                f"{message}!\n Accepted range is: {setpoint_range}.\n"
                f"Command ignored",
            )
            return ""

        # SETTER w/o range
        return await self._transmit_and_parse_reply(message + ":" + str(setpoint))

    @property
    def _headtype(self):
        """Return internal head type. Use `set_headtype()` to change in pump."""
        return self.__headtype

    @_headtype.setter
    def _headtype(self, htype):
        self.__headtype = htype

        if htype == AzuraPumpHeads.FLOWRATE_TEN_ML:
            self.max_allowed_pressure, self.max_allowed_flow = 400, 10000
        elif htype == AzuraPumpHeads.FLOWRATE_FIFTY_ML:
            self.max_allowed_pressure, self.max_allowed_flow = 150, 50000

    async def get_headtype(self) -> AzuraPumpHeads:
        """Return pump's head type."""
        head_type_id = await self.create_and_send_command(HEADTYPE)
        try:
            headtype = AzuraPumpHeads(int(head_type_id))
            # Sets internal property (changes max flowrate etc.)
            self._headtype = headtype
        except ValueError as value_error:
            raise DeviceError(
                "It seems you're trying instantiate an unknown device/unknown pump type as Knauer Pump.\n"
                "Only Knauer Azura Compact is supported"
            ) from value_error
        logger.debug(f"Head type of pump {self.ip_address} is {headtype}")

        return headtype

    async def set_headtype(self, head_type: AzuraPumpHeads):
        """Set pump's head type."""
        await self.create_and_send_command(HEADTYPE, setpoint=head_type.value)
        # Update internal property (changes max flowrate etc.)
        self._headtype = head_type
        logger.debug(f"Head type set to {head_type}")

    async def get_flow_rate(self) -> float:
        """Get flow rate in ml/min."""
        flow_value = await self.create_and_send_command(FLOW)
        flowrate = ureg.Quantity(f"{flow_value} ul/min")
        logger.debug(f"Current flow rate is {flowrate}")
        return flowrate.m_as("ml/min")

    async def set_flow_rate(self, rate: pint.Quantity):
        """Set flow rate.

        Args:
        ----
            rate (str): value with units
        """
        await self.create_and_send_command(
            FLOW,
            setpoint=round(rate.m_as("ul/min")),
            setpoint_range=(0, self.max_allowed_flow + 1),
        )
        logger.info(f"Flow set to {rate}")

    async def get_minimum_pressure(self):
        """Get minimum pressure. The pump stops if the measured P is lower than this."""
        command = PMIN10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMIN50
        p_min = await self.create_and_send_command(command) * ureg.bar
        return str(p_min)

    async def set_minimum_pressure(self, value: str = "0 bar"):
        """Set minimum pressure. The pump stops if the measured P is lower than this."""
        pressure = ureg.Quantity(value)
        command = PMIN10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMIN50
        await self.create_and_send_command(
            command,
            setpoint=round(pressure.m_as("bar")),
            setpoint_range=(0, self.max_allowed_pressure + 1),
        )
        logger.info(f"Minimum pressure set to {pressure}")

    async def get_maximum_pressure(self) -> str:
        """Get maximum pressure. The pumps stop if the measured P is higher than this."""
        command = PMAX10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMAX50
        p_max = await self.create_and_send_command(command) * ureg.bar
        return str(p_max)

    async def set_maximum_pressure(self, value: str):
        """Set maximum pressure. The pumps stop if the measured P is higher than this."""
        pressure = ureg.Quantity(value)
        command = PMAX10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMAX50
        await self.create_and_send_command(
            command,
            setpoint=round(pressure.m_as("bar")),
            setpoint_range=(0, self.max_allowed_pressure + 1),
        )
        logger.info(f"Maximum pressure set to {pressure}")

    async def set_minimum_motor_current(self, setpoint=None):
        """Set minimum motor current."""
        command = IMIN10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else IMIN50

        reply = await self.create_and_send_command(
            command,
            setpoint=setpoint,
            setpoint_range=(0, 101),
        )
        logger.debug(f"Minimum motor current set to {setpoint}, returns {reply}")

    async def is_start_in_required(self):
        """Check state of START IN. See require_start_in() for details."""
        runlevel = await self.create_and_send_command(STARTLEVEL)
        return not bool(int(runlevel))

    async def require_start_in(self, value: bool = True):
        """Configure START IN. If required, the pump starts only if the STARTIN pin is shortened to GND.

        True = Pump starts the flow at short circuit contact only. (Start In <> Ground). [0]
        False = Pump starts the flow without a short circuit contact. (Start In <> Ground). [1]
        """
        setpoint = int(not value)
        await self.create_and_send_command(STARTLEVEL, setpoint=setpoint)
        logger.debug(f"Start in required set to {value}")

    async def is_autostart_enabled(self):
        """Return the default behaviour of the pump upon power on."""
        reply = await self.create_and_send_command(STARTMODE)
        return bool(int(reply))

    async def enable_autostart(self, value: bool = True):
        """Set the default behaviour of the pump upon power on.

        :param value: False: pause pump after switch on. True: start pumping with previous flow rate at startup
        :return: device message
        """
        await self.create_and_send_command(STARTMODE, setpoint=int(value))
        logger.debug(f"Autostart set to {value}")

    async def get_adjusting_factor(self):
        """Get the adjust parameter. Not clear what it is."""
        command = ADJ10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = await self.create_and_send_command(command)
        return int(reply)

    async def set_adjusting_factor(self, setpoint: int | None = None):
        """Set the adjust parameter. Not clear what it is."""
        command = ADJ10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = await self.create_and_send_command(
            command,
            setpoint=setpoint,
            setpoint_range=(0, 2001),
        )
        logger.debug(f"Adjusting factor of set to {setpoint}, returns {reply}")

    async def get_correction_factor(self):
        """Get the correction factor. Not clear what it is."""
        command = CORR10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else CORR50
        return int(await self.create_and_send_command(command))

    async def set_correction_factor(self, setpoint=None):
        """Set the correction factor. Not clear what it is."""
        command = CORR10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else CORR50
        reply = await self.create_and_send_command(
            command,
            setpoint=setpoint,
            setpoint_range=(0, 301),
        )
        logger.debug(f"Correction factor set to {setpoint}, returns {reply}")

    async def read_pressure(self) -> pint.Quantity:
        """Return pressure if the pump has a pressure sensor."""
        return int(await self._transmit_and_parse_reply(PRESSURE)) * 0.1 * ureg.bar

    async def read_extflow(self) -> float:
        """Read the set flowrate from analog in."""
        ext_flow = await self._transmit_and_parse_reply(EXTFLOW)
        logger.debug(f"Extflow reading returns {ext_flow}")
        return float(ext_flow)

    async def read_errors(self) -> list[int]:
        """Return the last 5 errors."""
        last_5_errors = await self.create_and_send_command(ERRORS)
        logger.debug(f"Error reading returns {last_5_errors}")
        return [int(err_code) for err_code in last_5_errors.split(",")]

    async def read_motor_current(self):
        """Return motor current, relative in percent 0-100."""
        current_percent = int(await self.create_and_send_command(IMOTOR))
        logger.debug(f"Motor current reading returns {current_percent} %")
        return current_percent

    async def infuse(self):
        """Start running pump at the given rate."""
        await self._transmit_and_parse_reply(PUMP_ON)
        self._running = True
        logger.info("Pump started!")
        return True

    async def stop(self):
        """Stop flow."""
        await self._transmit_and_parse_reply(PUMP_OFF)
        self._running = False
        logger.info("Pump stopped")

    def is_running(self):
        """Get pump state."""
        return self._running

    async def set_local(self, state: bool = True):
        """Relinquish remote control."""
        await self.create_and_send_command(LOCAL, setpoint=int(state))
        logger.debug(f"Local control set to {state}")

    async def remote_control(self, state: bool = True):
        """Set remote control on or off."""
        if state:
            await self.create_and_send_command(REMOTE, setpoint=1)
        else:
            await self.create_and_send_command(LOCAL, setpoint=1)
        logger.debug(f"Remote control set to {state}")

    async def is_analog_control_enabled(self):
        """Return the status of the external flow control via analog input."""
        reply = await self.create_and_send_command(EXTCONTR)
        return bool(int(reply))

    async def enable_analog_control(self, value: bool):
        """External flow control via analog input.

        False = prevents external flow control. [0]
        True = allows the flow rate control via analog input 0 - 10V (10ml: 1 V = 1 ml/min, 50ml: 1 V = 5 ml/min). [1]
        """
        await self.create_and_send_command(EXTCONTR, setpoint=int(value))
        logger.debug(f"External control set to {value}")


if __name__ == "__main__":
    # This is a bug of asyncio on Windows :|
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    p = AzuraCompact(ip_address="192.168.1.119")

    async def main(pump: AzuraCompact):
        """Test function."""
        await pump.initialize()
        c = pump.components
        print(c)
        pc: AzuraCompactPump = c[0]  # type:ignore
        print(pc)
        print(await pc.infuse(rate="0.1 ml/min"))
        await pump.set_flow_rate(ureg.Quantity("0.1 ml/min"))
        await pump.infuse()
        await asyncio.sleep(5)
        await pump.stop()
        print(await pc.is_pumping())

    asyncio.run(main(p))
