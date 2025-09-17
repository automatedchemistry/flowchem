"""Vacuubrand CVC3000 control."""
import asyncio

import aioserial
import pint
from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.vacuubrand.cvc3000_pressure_control import CVC3000PressureControl
from flowchem.devices.vacuubrand.constants import ProcessStatus
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import dario, jakob, wei_hsin


class CVC3000(FlowchemDevice):
    """
    Control class for the Vacuubrand CVC3000 vacuum controller.

    This class provides methods to interface with and control the Vacuubrand CVC3000 vacuum controller via serial
    commands. It includes functionalities for setting and getting pressure, controlling motor speed, and querying
    the device status.

    Attributes:
    -----------
    DEFAULT_CONFIG : dict
        Default configuration parameters for the serial connection.
    _serial : aioserial.AioSerial
        The serial interface used to communicate with the device.
    _device_sn : int
        The serial number of the device (initialized as None).
    device_info : DeviceInfo
        Metadata and configuration details about the device.

    Methods:
    --------
    from_config(cls, port: str, name: str = None, **serial_kwargs) -> CVC3000:
        Create an instance from configuration parameters.
    initialize(self) -> None:
        Initialize the connection with the device and configure it.
    _send_command_and_read_reply(self, command: str) -> str:
        Send a command to the device and read the reply.
    version(self) -> str:
        Retrieve the version of the CVC3000 device.
    set_pressure(self, pressure: pint.Quantity) -> None:
        Set the pressure on the device.
    get_pressure(self) -> float:
        Get the current pressure from the device.
    motor_speed(self, speed: int) -> None:
        Set the motor speed on the device (0 to 100%).
    status(self) -> ProcessStatus:
        Get the current process status from the device.
    """

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 19200,  # Supports 2400-19200
        "parity": aioserial.PARITY_NONE,  # Other values possible via config
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(
        self,
        aio: aioserial.AioSerial,
        name="",
    ) -> None:
        """
        Initialize the CVC3000 device controller.

        Parameters:
        -----------
        aio : aioserial.AioSerial
            The serial interface for communication with the CVC3000.
        name : str
            The name assigned to the device instance.
        """
        super().__init__(name)
        self._serial = aio
        self._device_sn: int = None  # type: ignore

        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Vacuubrand",
            model="CVC3000",
        )

    @classmethod
    def from_config(cls, port, name=None, **serial_kwargs):
        """
        Create an instance from configuration parameters.

        Used by server to initialize obj from config.

        Only required parameter is 'port'. Optional 'loop' + others (see AioSerial())

        Parameters:
        -----------
        port : str
            The port to which the CVC3000 is connected.
        name : str, optional
            The name assigned to the device instance (default is None).
        **serial_kwargs : dict
            Additional keyword arguments for configuring the serial interface.

        Returns:
        --------
        CVC3000
            An instance of the CVC3000 class.

        Raises:
        -------
        InvalidConfigurationError
            If the serial connection cannot be established.
        """
        # Merge default settings, including serial, with provided ones.
        configuration = CVC3000.DEFAULT_CONFIG | serial_kwargs

        try:
            serial_object = aioserial.AioSerial(port, **configuration)
        except (OSError, aioserial.SerialException) as serial_exception:
            raise InvalidConfigurationError(
                f"Cannot connect to the CVC3000 on the port <{port}>"
            ) from serial_exception

        return cls(serial_object, name)

    async def initialize(self):
        """
        Initialize the connection with the device and configure it.

        This includes setting the device mode, saving configuration, enabling remote control,
        and configuring output settings.

        Raises:
        -------
        InvalidConfigurationError
            If no version reply is received from the CVC3000.
        """
        self.device_info.version = await self.version()
        if not self.device_info.version:
            raise InvalidConfigurationError("No reply received from CVC3000!")

        # Set to CVC3000 mode and save
        await self._send_command_and_read_reply("CVC 3")
        await self._send_command_and_read_reply("STORE")
        # Get reply to set commands
        await self._send_command_and_read_reply("ECHO 1")
        # Remote control
        await self._send_command_and_read_reply("REMOTE 1")
        # mbar, no autostart, no beep, venting auto
        await self._send_command_and_read_reply("OUT_CFG 00001")
        await self.motor_speed(100)

        logger.debug(f"Connected with CVC3000 version {self.device_info.version}")

        self.components.append(CVC3000PressureControl("pressure-control", self))

    async def _send_command_and_read_reply(self, command: str) -> str:
        """
        Send a command to the device and read the reply.

        Parameters:
        -----------
        command : str
            The command string to be transmitted.

        Returns:
        --------
        str
            The reply received from the device.

        Notes:
        ------
        If no reply is received within the timeout period, an error is logged.
        """
        await self._serial.write_async(command.encode("ascii") + b"\r\n")
        logger.debug(f"Command `{command}` sent!")

        # Receive reply and return it after decoding
        try:
            reply = await asyncio.wait_for(self._serial.readline_async(), 2)
        except asyncio.TimeoutError:
            logger.error("No reply received! Unsupported command?")
            return ""

        await asyncio.sleep(0.1)  # Max rate 10 commands/s as per manual

        logger.debug(f"Reply received: {reply}")
        return reply.decode("ascii")

    async def version(self):
        """
        Retrieve the version of the CVC3000 device.

        Returns:
        --------
        str
            The version of the device, or None if the version could not be retrieved.
        """
        raw_version = await self._send_command_and_read_reply("IN_VER")
        # raw_version = CVC 3000 VX.YY
        try:
            return raw_version.split()[-1]
        except IndexError:
            return None

    async def set_pressure(self, pressure: pint.Quantity):
        """
        Set the pressure on the device.

        Parameters:
        -----------
        pressure : pint.Quantity
            The target pressure to be set, expressed in units compatible with the device (e.g., mbar).
        """
        mbar = int(pressure.m_as("mbar"))
        await self._send_command_and_read_reply(f"OUT_SP_1 {mbar}")

    async def get_pressure(self):
        """
        Get the current pressure from the device.

        Returns:
        --------
        float
            The current pressure in mbar.
        """
        pressure_text = await self._send_command_and_read_reply("IN_PV_1")
        return float(pressure_text.split()[0])

    async def motor_speed(self, speed):
        """
        Set the motor speed on the device.

        Parameters:
        -----------
        speed : int
            The target motor speed percentage (0-100%).
        """
        return await self._send_command_and_read_reply(f"OUT_SP_2 {speed}")

    async def status(self) -> ProcessStatus:
        """
        Get the current process status from the device.

        Returns:
        --------
        ProcessStatus
            The status of the device process.
        """
        raw_status = await self._send_command_and_read_reply("IN_STAT")
        # Sometimes fails on first call
        if not raw_status:
            raw_status = await self._send_command_and_read_reply("IN_STAT")
        return ProcessStatus.from_reply(raw_status)
