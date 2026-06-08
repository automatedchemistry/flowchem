"""Zeroconf (mDNS) server."""

import uuid

from loguru import logger
from zeroconf import (
    IPVersion,
    NonUniqueNameException,
    ServiceInfo,
    Zeroconf,
    get_all_addresses,
)


class ZeroconfServer:
    """Server to advertise Flowchem devices via zero configuration networking."""

    def __init__(self, port: int = 8000) -> None:
        # Server properties
        self.port = port
        self.server = Zeroconf(ip_version=IPVersion.V4Only)

        # Get list of host addresses
        self.mdns_addresses = [
            ip
            for ip in get_all_addresses()  # Get all local IP
            if ip not in ("127.0.0.1", "0.0.0.0")
            and not ip.startswith("169.254")  # Remove invalid IPs
        ]
        if not self.mdns_addresses:
            self.mdns_addresses.append("127.0.0.1")

        logger.info(f"Zeroconf server up, broadcasting on IPs: {self.mdns_addresses}")

    async def add_device(self, name: str) -> None:
        """Add device to the server."""
        properties = {
            "path": rf"http://{self.mdns_addresses[0]}:{self.port}/{name}/",
            "id": f"{name}:{uuid.uuid4()}".replace(" ", ""),
        }

        # LabThing service
        service_info = ServiceInfo(
            type_="_labthing._tcp.local.",
            name=name + "._labthing._tcp.local.",
            port=self.port,
            properties=properties,
            parsed_addresses=self.mdns_addresses,
        )

        try:
            await self.server.async_register_service(service_info)
        except NonUniqueNameException as name_error:
            msg = (
                f"Cannot initialize zeroconf service for '{name}'"
                f"The same name is already in use: you cannot run flowchem twice for the same device!"
            )
            raise RuntimeError(msg) from name_error
        logger.debug(f"Device {name} registered as Zeroconf service!")


if __name__ == "__main__":
    test = ZeroconfServer()
    print("Press Enter to exit.")
    input()
