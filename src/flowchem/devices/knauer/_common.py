"""Module for communication with Knauer devices."""
import asyncio
from asyncio import Lock
import aioserial

from loguru import logger

from flowchem.utils.exceptions import InvalidConfigurationError

from .knauer_finder import autodiscover_knauer


class KnauerEthernetDevice:
    """Common base class for shared logic across Knauer pumps and valves."""

    TCP_PORT = 10001
    BUFFER_SIZE = 1024
    _id_counter = 0

    def __init__(self, ip_address, mac_address, network="", **kwargs):
        """Knauer Ethernet Device - either pump or valve.

        If a MAC address is given, it is used to autodiscover the IP address.
        Otherwise, the IP address must be given.

        Note that for configuration files, the MAC address is preferred as it is static.

        Args:
        ----
            ip_address: device IP address (only 1 of either IP or MAC address is needed)
            mac_address: device MAC address (only 1 of either IP or MAC address is needed)
            name: name of device (optional)
        """
        super().__init__(**kwargs)

        # MAC address
        if mac_address:
            self.ip_address = self._ip_from_mac(mac_address.lower(), network=network)
        else:
            self.ip_address = ip_address

        # These will be set in initialize()
        self._reader: asyncio.StreamReader = None  # type: ignore
        self._writer: asyncio.StreamWriter = None  # type: ignore

        # Note: the pump requires "\n\r" as EOL, the valves "\r\n"! So this is set by the subclasses
        self.eol = b""

        # Lock communication between write and read reply
        self._lock = asyncio.Lock()

    def _ip_from_mac(self, mac_address: str, network="") -> str:
        """Get IP from MAC."""
        # Autodiscover IP from MAC address
        available_devices = autodiscover_knauer(network)
        # IP if found, None otherwise
        ip_address = available_devices.get(mac_address)
        if ip_address is None:
            raise InvalidConfigurationError(
                # f"{self.__class__.__name__}:{self.name}\n"  # type: ignore
                f"Device with MAC address={mac_address} not found!\n"
                f"[Available: {available_devices}]"
            )
        return ip_address

    async def initialize(self):
        """Initialize connection."""
        # Future used to set shorter timeout than default
        future = asyncio.open_connection(host=self.ip_address, port=10001)
        try:
            self._reader, self._writer = await asyncio.wait_for(future, timeout=3)
        except OSError as connection_error:
            logger.exception(connection_error)
            raise InvalidConfigurationError(
                f"Cannot open connection with device {self.__class__.__name__} at IP={self.ip_address}"
            ) from connection_error
        except asyncio.TimeoutError as timeout_error:
            logger.exception(timeout_error)
            raise InvalidConfigurationError(
                f"No reply from device {self.__class__.__name__} at IP={self.ip_address}"
            ) from timeout_error

    async def _send_and_receive(self, message: str) -> str:
        async with self._lock:
            self._writer.write(message.encode("ascii") + self.eol)
            await self._writer.drain()
            logger.debug(f"WRITE >>> '{message}' ")
            reply = await self._reader.readuntil(separator=b"\r")
        logger.debug(f"READ <<< '{reply.decode().strip()}' ")
        return reply.decode("ascii").strip()


class KnauerSerialDevice:

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 9600,
        "parity": aioserial.PARITY_NONE,
        "stopbits": aioserial.STOPBITS_ONE,
        "bytesize": aioserial.EIGHTBITS,
    }

    def __init__(self, serial_port, **kwargs):

        super().__init__(**kwargs)
        self.port = serial_port
        # Merge default settings, including serial, with provided ones.
        # configuration = KnauerSerialDevice.DEFAULT_CONFIG | serial_port
        KnauerSerialDevice.DEFAULT_CONFIG["port"] = serial_port
        configuration = KnauerSerialDevice.DEFAULT_CONFIG

        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as ex:
            raise InvalidConfigurationError(
                f"Cannot connect to the Knauer Device on the port <{serial_port}>"
            ) from ex

        # Note: the pump requires "\n\r" as EOL, the valves "\r\n"! So this is set by the subclasses
        self.eol = b""

        # Lock communication between write and read reply
        self._serial_lock = Lock()

    async def _write(self, command: str):
        """Write a command to the pump."""
        logger.debug(f"run eol: {self.eol}")
        await self._serial.write_async(command.encode("ascii") + self.eol)
        logger.debug(f"Sent command: {command!r}")

    async def _read_reply(self) -> str:
        """Read the pump reply from serial communication."""
        reply_string = await self._serial.readline_async()
        logger.debug(f"Reply received: {reply_string.decode('ascii').rstrip()}")
        return reply_string.decode("ascii")

    async def _send_and_receive(self, command: str) -> str:
        """Send a command to the pump, read the replies and return it, optionally parsed."""
        self._serial.reset_input_buffer()  # Clear input buffer, discarding all that is in the buffer.
        async with self._serial_lock:
            await self._write(command)
            logger.debug(f"Command {command} sent!")

            failure = 0
            while True:
                response = await self._read_reply()
                if not response:
                    failure += 1
                    logger.warning(f"{failure} time of failure!")
                    logger.error(f"Command {command} is not working")
                    await asyncio.sleep(0.2)
                    self._serial.reset_input_buffer()
                    await self._write(command)
                    # Allows 4 failures...
                    if failure > 3:
                        raise InvalidConfigurationError(
                            "No response received from KnauerDevices!"
                        )
                else:
                    break

        logger.debug(f"Reply received: {response}")
        return response.rstrip()

    async def initialize(self):
        """Ensure connection."""
        pass

class KnauerDevice:
    def __init__(self, serial_port, ip_address, mac_address, network="", **kwargs):

        if serial_port:
            self.connection = KnauerSerialDevice(serial_port,  **kwargs)
        else:
            self.connection = KnauerEthernetDevice(ip_address, mac_address, network, **kwargs)

    def __getattr__(self, name):
        if hasattr(self.connection, name):
            return getattr(self.connection, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute'{name}'")