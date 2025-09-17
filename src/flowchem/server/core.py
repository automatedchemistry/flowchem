from __future__ import annotations
import asyncio
import enum
import threading
from io import BytesIO
from pathlib import Path
from typing import Any

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.server.configuration_parser import (
    instantiate_device_from_config,
    parse_config,
)
from flowchem.server.fastapi_server import FastAPIServer
from flowchem.server.zeroconf_server import ZeroconfServer


class _Flowchem(threading.local):
    """Container which makes a Flowchem instance available to the event loop."""

    fc: Flowchem | None = None


# Essentially a global pointer to flowchem as thread local
_fc = _Flowchem()


class CoreState(enum.Enum):
    """Represent the current state of Flowchem."""

    not_running = "NOT_RUNNING"
    starting = "STARTING"
    running = "RUNNING"
    stopping = "STOPPING"
    final_write = "FINAL_WRITE"
    stopped = "STOPPED"

    def __str__(self) -> str:
        """Return the event."""
        return self.value


class Flowchem:
    def __new__(cls) -> Flowchem:
        """Set the _fc thread local data."""
        fc = super().__new__(cls)
        _fc.fc = fc
        return fc

    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self._tasks: set[asyncio.Future[Any]] = set()
        self.config: dict[str, Any] = {}
        self.devices: list[FlowchemDevice] = []
        self.state: CoreState = CoreState.not_running
        self.exit_code: int = 0
        # If not None, use to signal end-of-loop
        self._stopped: asyncio.Event | None = None

        # mDNS server (Zeroconf)
        self.mdns = ZeroconfServer(self.port)

        # HTTP server (FastAPI)
        self.http = FastAPIServer(
            self.config.get("filename", ""),
            host=self.mdns.mdns_addresses[0],
            port=self.port,
        )

        # To be implemented
        # self.bus = EventBus(self)
        # self.states = StateMachine(self.bus, self.loop)

    @property
    def port(self):
        return self.config.get("port", 8000)

    async def setup(self, config: BytesIO | Path):
        self.config = parse_config(config)
        self.http.configuration_dict = self.config
        self.devices = instantiate_device_from_config(self.config)

        """Initialize connection to devices and create API endpoints."""
        logger.info("Initializing device connection(s)...")

        # Run `initialize` async method of all hw devices in parallel
        await asyncio.gather(*[dev.initialize() for dev in self.devices])
        logger.info("Device(s) connected")

        # Create entities for the configured devices.
        for device in self.devices:
            # Advertise devices as services via mDNS
            await self.mdns.add_device(name=device.name)
            # Add device API to HTTP server
            self.http.add_device(device)
        logger.info("Server component(s) loaded successfully!")


if __name__ == "__main__":
    import uvicorn

    async def main():
        flowchem = Flowchem()
        await flowchem.setup(
            BytesIO(b"""[device.test-device]\ntype = "FakeDevice"\n""")
        )

        config = uvicorn.Config(
            flowchem.http.app,
            port=flowchem.port,
            log_level="info",
            timeout_keep_alive=3600,
        )
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
