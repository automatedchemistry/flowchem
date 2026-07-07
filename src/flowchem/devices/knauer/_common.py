"""Module for communication with Knauer devices."""

import asyncio

from loguru import logger

from flowchem.utils.exceptions import InvalidConfigurationError

from .knauer_finder import autodiscover_knauer


class KnauerEthernetDevice:
    """Common base class for shared logic across Knauer pumps and valves."""

    TCP_PORT = 10001
    BUFFER_SIZE = 1024
    TIMEOUT = 3.0
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
            persistent_connection: keep a single long-lived TCP connection open
                (default) rather than opening/closing a fresh one per command.
        """
        self.persistent_connection = kwargs.pop("persistent_connection", True)
        super().__init__(**kwargs)

        # MAC address
        if mac_address:
            self.ip_address = self._ip_from_mac(mac_address.lower(), network=network)
        else:
            self.ip_address = ip_address

        # These will be set in initialize() when persistent_connection is True
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
                f"{self.__class__.__name__}:{self.name}\n"  # type: ignore
                f"Device with MAC address={mac_address} not found!\n"
                f"[Available: {available_devices}]"
            )
        return ip_address

    async def initialize(self):
        """Initialize connection.

        When persistent_connection is False, no long-lived reader/writer is
        kept around -- only connectivity is probed here, and each command
        opens/closes its own connection in ``_send_and_receive``.
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host=self.ip_address, port=self.TCP_PORT),
                timeout=self.TIMEOUT,
            )
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

        if self.persistent_connection:
            self._reader, self._writer = reader, writer
        else:
            writer.close()

    async def _send_and_receive(self, message: str) -> str:
        if not self.persistent_connection:
            return await self._send_and_receive_oneshot(message)

        async with self._lock:
            self._writer.write(message.encode("ascii") + self.eol)
            await self._writer.drain()
            logger.debug(f"WRITE >>> '{message}' ")
            reply = await self._reader.readuntil(separator=b"\r")
        logger.debug(f"READ <<< '{reply.decode().strip()}' ")
        return reply.decode("ascii").strip()

    async def _send_and_receive_oneshot(self, message: str) -> str:
        """Open a fresh connection, send ``message``, read the reply, then close.

        Used when persistent_connection is False, for devices whose long-lived
        socket is prone to going stale over the course of an experiment.
        """
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=self.ip_address, port=self.TCP_PORT),
            timeout=self.TIMEOUT,
        )
        try:
            writer.write(message.encode("ascii") + self.eol)
            await writer.drain()
            logger.debug(f"WRITE >>> '{message}' ")
            reply = await asyncio.wait_for(
                reader.readuntil(separator=b"\r"), timeout=self.TIMEOUT
            )
        finally:
            writer.close()
        logger.debug(f"READ <<< '{reply.decode().strip()}' ")
        return reply.decode("ascii").strip()
