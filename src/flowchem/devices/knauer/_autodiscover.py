"""Autodiscover Knauer devices on network."""
import asyncio
import queue
import socket
import sys
import time
from threading import Thread

import rich_click as click
from loguru import logger

from flowchem.devices.knauer.getmac import get_mac_address

__all__ = ["main", "autodiscover_knauer"]

Address = tuple[str, int]


class BroadcastProtocol(asyncio.DatagramProtocol):
    """See `https://gist.github.com/yluthu/4f785d4546057b49b56c`."""

    def __init__(self, target: Address, response_queue: queue.Queue):
        self.target = target
        self.loop = asyncio.get_event_loop()
        self._queue = response_queue

    def connection_made(self, transport: asyncio.transports.DatagramTransport):  # type: ignore
        """Send the magic broadcast package for autodiscovery."""
        sock = transport.get_extra_info("socket")  # type: socket.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # sets to broadcast
        transport.sendto(b"\x00\x01\x00\xf6", self.target)

    def datagram_received(self, data: bytes | str, addr: Address):
        """Add received data to queue."""
        logger.trace(f"Received data from {addr}")
        self._queue.put(addr[0])


async def get_device_type(ip_address: str) -> str:
    """Return either 'Pump', 'Valve' or 'Unknown'."""
    fut = asyncio.open_connection(host=ip_address, port=10001)
    try:
        reader, writer = await asyncio.wait_for(fut, timeout=3)
    except ConnectionError:
        return "ConnectionError"
    except asyncio.TimeoutError:
        if ip_address == "192.168.1.2":
            return "TimeoutError - Nice FlowIR that you have :D"
        return "TimeoutError"

    # Test Pump
    writer.write(b"HEADTYPE:?\n\r")
    reply = await reader.readuntil(separator=b"\r")
    if reply.startswith(b"HEADTYPE"):
        logger.debug(f"Device {ip_address} is a Pump")
        return "Pump"

    # Test Valve
    writer.write(b"T:?\n\r")
    reply = await reader.readuntil(separator=b"\r")
    if reply.startswith(b"VALVE"):
        logger.debug(f"Device {ip_address} is a Valve")
        return "Valve"

    return "Unknown"


def _get_local_ip() -> str:
    """Guess the most suitable local IP for autodiscovery."""
    # These are all the local IPs (different interfaces)
    machine_ips = [_[4][0] for _ in socket.getaddrinfo(socket.gethostname(), None)]

    # 192.168 subnet 1st priority
    if local_ip := next((ip for ip in machine_ips if ip.startswith("192.168.")), False):
        return local_ip  # type: ignore

    # 10.0 subnet 2nd priority
    if local_ip := next((ip for ip in machine_ips if ip.startswith("10.")), False):
        return local_ip  # type: ignore

    logger.warning(f"Could not reliably determine local IP!")
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


def autodiscover_knauer(source_ip: str = "") -> dict[str, str]:
    """
    Automatically find Knauer ethernet device on the network and returns the IP associated to each MAC address.

    Note that the MAC is the key here as it is the parameter used in configuration files.
    Knauer devices only support DHCP so static IPs are not an option.

    Args:
        source_ip: source IP for autodiscover (only relevant if multiple network interfaces are available!)
    Returns:
        List of tuples (IP, MAC, device_type), one per device replying to autodiscover
    """
    # Define source IP resolving local hostname.
    if not source_ip:
        source_ip = _get_local_ip()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    device_q: queue.Queue = queue.Queue()
    coro = loop.create_datagram_endpoint(
        lambda: BroadcastProtocol(("255.255.255.255", 30718), response_queue=device_q),
        local_addr=(source_ip, 28688),
    )
    loop.run_until_complete(coro)
    thread = Thread(target=loop.run_forever)
    thread.start()
    time.sleep(2)
    loop.call_soon_threadsafe(loop.stop)  # here
    thread.join()

    device_info = {}
    device_ip: str
    for device_ip in iter(device_q.get, None):
        # MAC address
        mac = get_mac_address(ip=device_ip)
        if mac:
            device_info[mac] = device_ip
    return device_info


@click.command()
def main():
    """Execute autodiscovery. This is the entry point of the `knauer-finder` CLI command."""
    # This is a bug of asyncio on Windows :|
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Autodiscover devices (dict mac as index, IP as value)
    logger.info("Starting detection")
    devices = autodiscover_knauer("192.168.1.114")

    for mac_address, ip in devices.items():
        logger.info(f"Determining device type for device at {ip} [{mac_address}]")
        # Device Type
        device_type = asyncio.run(get_device_type(ip))
        logger.info(f"Found a {device_type} on IP {ip}")

    if not devices:
        logger.info("No device found!")


if __name__ == "__main__":
    main()
